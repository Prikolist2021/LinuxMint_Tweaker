# -*- coding: utf-8 -*-
"""
Linux Tweaker — операции над системой.

Класс SystemOps выполняет все изменения в системе:
- базовые файловые операции с бэкапами и атомарной записью
- GRUB (add/set/remove параметров)
- systemd (службы, юниты)
- fstab (noatime, commit=)
- симлинки Steam
- .bashrc (aliases)
- автообновления (systemd timer)
- удаление пакетов через apt
- откаты всех операций
"""

import os
import re
import subprocess
import glob
import shutil
import pwd
from datetime import datetime

from .data import (
    COMMIT_MIN, COMMIT_MAX, COMMIT_DEFAULT,
    SWAPPINESS_MIN, SWAPPINESS_MAX,
    SWAPPINESS_DEFAULT_DISK, SWAPPINESS_DEFAULT_ZRAM,
    TMPFS_SIZE_DEFAULT, TMPFS_SIZE_REGEX,
    SUDO_TIMEOUT_APT, SUDO_TIMEOUT_GRUB, SUDO_TIMEOUT_INITRAMFS,
    SUDO_TIMEOUT_DEFAULT,
    TIMEOUT_QUICK,
    BACKUP_KEEP_LAST,
    MAX_MAP_COUNT_VALUES, MAX_MAP_COUNT_DEFAULT,
    SHUTDOWN_TIMEOUT_VALUES, SHUTDOWN_TIMEOUT_DEFAULT,
    SHUTDOWN_TIMEOUT_SYSTEM_DEFAULT,
    PIPEWIRE_PRESETS, PIPEWIRE_PRESET_DEFAULT,
)
from .helpers import (
    decode_bytes, lines_in, fs_supports_commit,
    zfs_in_use, zfs_packages_installed, zram_generator_present,
    estimate_packages_size,
    ZFS_UNITS,
)


class SystemOps:
    """Все системные операции с бэкапами и откатами."""

    def __init__(self, sudo, state, log, dry_run):
        self.sudo = sudo
        self.state = state
        self.log = log
        self.dry_run = dry_run
        self.grub_changed = False
        self.mount_items = []
        self.commit_targets = []
        self.backup_dir = os.path.join(state.user_home, "system-tuneup-backups")

    # ─── Бэкапы ─────────────────────────────────────────────────────────

    def _safe_backup_name(self, path):
        """Возвращает имя бэкапа с timestamp."""
        safe = path.lstrip("/").replace("/", "_")
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        return "%s.%s.bak" % (safe, ts)

    def _prune_backups(self, path):
        """Оставляет только последние BACKUP_KEEP_LAST бэкапов данного пути."""
        try:
            safe = path.lstrip("/").replace("/", "_")
            pattern = os.path.join(self.backup_dir, safe + ".*.bak")
            files = sorted(glob.glob(pattern),
                           key=lambda p: os.path.getmtime(p),
                           reverse=True)
            for old in files[BACKUP_KEEP_LAST:]:
                try:
                    os.remove(old)
                except Exception:
                    pass
        except Exception:
            pass

    def backup_file(self, path):
        """Создаёт бэкап файла. True — если бэкап создан или файла нет."""
        if self.dry_run:
            return True
        try:
            if not self.path_exists(path):
                return True
            content = self.read_file(path)
            if content is None:
                self.log("[WARN] cannot read %s for backup" % path, "warning")
                return False
            os.makedirs(self.backup_dir, exist_ok=True)
            try:
                os.chmod(self.backup_dir, 0o700)
            except Exception:
                pass
            bp = os.path.join(self.backup_dir, self._safe_backup_name(path))
            with open(bp, "w", encoding="utf-8") as f:
                f.write(content)
            try:
                os.chmod(bp, 0o600)
            except Exception:
                pass
            if self.state.user_name and self.state.user_name != "root":
                try:
                    pw = pwd.getpwnam(self.state.user_name)
                    os.chown(bp, pw.pw_uid, pw.pw_gid)
                except Exception:
                    pass
            self._prune_backups(path)
            self.log("[BACKUP] %s" % os.path.basename(bp), "info")
            return True
        except Exception as e:
            self.log("[WARN] backup %s: %s" % (path, e), "warning")
            return False

    # ─── Запуск команд ──────────────────────────────────────────────────

    def sudo_run(self, args, input=None, ok_msg=None, err_msg=None,
                 ignore_error=False, timeout=None, env=None):
        """Запуск команды через sudo (или напрямую, если root)."""
        if self.dry_run:
            self.log("[DRY RUN] " + " ".join(args), "warning")
            return True
        try:
            res = self.sudo.run(args, input=input, timeout=timeout, env=env,
                                log=lambda m: self.log(m, "info"))
        except PermissionError as e:
            self.log(str(e), "error")
            return False
        except subprocess.TimeoutExpired:
            self.log("Command timed out: " + " ".join(args), "error")
            return False
        except Exception as e:
            self.log("Command error: %s" % e, "error")
            return False
        if res.returncode == 0:
            if ok_msg:
                self.log(ok_msg, "success")
            return True
        if not ignore_error:
            err = decode_bytes(res.stderr).strip()
            msg = err_msg or "Command failed: " + " ".join(args)
            if err:
                self.log("[ERR] %s\n%s" % (msg, err), "error")
            else:
                self.log("[ERR] %s" % msg, "error")
        return False

    # ─── Файловые операции ──────────────────────────────────────────────

    def path_exists(self, path):
        if os.path.exists(path):
            return True
        try:
            return subprocess.run(["sudo", "-n", "test", "-e", path],
                                  capture_output=True,
                                  timeout=TIMEOUT_QUICK).returncode == 0
        except Exception:
            return False

    def read_file(self, path):
        """Читает файл (через sudo cat, или напрямую если не удалось)."""
        if not self.path_exists(path):
            return ""
        try:
            res = subprocess.run(["sudo", "-n", "cat", path],
                                 capture_output=True, timeout=TIMEOUT_QUICK)
            if res.returncode == 0:
                return decode_bytes(res.stdout)
        except Exception:
            pass
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None

    def atomic_write(self, path, content, chmod="644", owner=None, mkdir=False):
        """Пишет во временный файл и атомарно перемещает на место."""
        if self.dry_run:
            self.log("[DRY RUN] atomic write: %s" % path, "warning")
            return True
        if mkdir:
            d = os.path.dirname(path)
            if d:
                self.sudo_run(["mkdir", "-p", d], ignore_error=True)
        tmp = path + ".tmp-tweaker"
        try:
            try:
                res = self.sudo.run(["tee", tmp], input=content.encode())
            except PermissionError as e:
                self.log(str(e), "error")
                return False
            except Exception as e:
                self.log("Write error %s: %s" % (tmp, e), "error")
                return False
            if res.returncode != 0:
                self.log("Cannot write %s" % tmp, "error")
                self.sudo_run(["rm", "-f", tmp], ignore_error=True)
                return False
            if chmod:
                self.sudo_run(["chmod", chmod, tmp], ignore_error=True)
            if owner:
                self.sudo_run(["chown", owner, tmp], ignore_error=True)
            if not self.sudo_run(["mv", "-f", tmp, path],
                                 err_msg="Cannot move %s -> %s" % (tmp, path)):
                self.sudo_run(["rm", "-f", tmp], ignore_error=True)
                return False
            return True
        except Exception as e:
            self.log("atomic_write %s: %s" % (path, e), "error")
            self.sudo_run(["rm", "-f", tmp], ignore_error=True)
            return False

    def write_file(self, path, content, chmod="644", owner=None,
                   mkdir=False, backup=True):
        """Запись файла с бэкапом + атомарным сохранением."""
        if not backup:
            return self.atomic_write(path, content, chmod=chmod,
                                     owner=owner, mkdir=mkdir)
        ok_backup = self.backup_file(path)
        if not ok_backup:
            self.log("Backup failed for %s, write aborted" % path, "error")
            return False
        return self.atomic_write(path, content, chmod=chmod,
                                 owner=owner, mkdir=mkdir)

    def write_user_file(self, path, content, backup=True):
        """Пишет файл в домашнюю папку пользователя без sudo."""
        if self.dry_run:
            self.log("[DRY RUN] user write: %s" % path, "warning")
            return True
        try:
            d = os.path.dirname(path)
            if d:
                os.makedirs(d, exist_ok=True)
            if backup and os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as f:
                        old = f.read()
                    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                    bp = path + "." + ts + ".bak"
                    with open(bp, "w", encoding="utf-8") as f:
                        f.write(old)
                    self.log("[BACKUP] %s" % os.path.basename(bp), "info")
                except Exception as e:
                    self.log("[WARN] backup %s: %s" % (path, e), "warning")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            try:
                os.chmod(path, 0o644)
            except Exception:
                pass
            return True
        except Exception as e:
            self.log("User write error %s: %s" % (path, e), "error")
            return False

    def remove_user_file(self, path):
        """Удаляет файл в домашней папке без sudo."""
        if self.dry_run:
            self.log("[DRY RUN] user rm %s" % path, "warning")
            return True
        try:
            if os.path.exists(path):
                os.remove(path)
                self.log("✓ removed %s" % path, "success")
            return True
        except Exception as e:
            self.log("User remove error %s: %s" % (path, e), "error")
            return False

    def verify_fstab(self):
        """Проверяет /etc/fstab через findmnt --verify."""
        if self.dry_run:
            return True
        try:
            res = self.sudo.run(["findmnt", "--verify", "--verbose"],
                                timeout=SUDO_TIMEOUT_DEFAULT)
        except Exception as e:
            self.log("findmnt --verify error: %s" % e, "warning")
            return True
        if res.returncode != 0:
            err = (decode_bytes(res.stdout).strip() + " " +
                   decode_bytes(res.stderr).strip())
            self.log("fstab verify FAILED: %s" % err.strip(), "error")
            return False
        return True

    def ensure_line(self, path, line, pattern, chmod="644", mkdir=False):
        """Гарантирует наличие строки line в файле path по regex pattern."""
        if self.dry_run:
            self.log("[DRY RUN] %s: %s" % (path, line), "warning")
            return True
        content = self.read_file(path)
        if content is None:
            self.log("Cannot read %s" % path, "error")
            return False
        lines = lines_in(content)
        new_lines, replaced, changed = [], False, False
        try:
            rx = re.compile(pattern)
        except re.error:
            rx = re.compile(re.escape(line))
        for old in lines:
            if rx.match(old.strip()):
                if not replaced:
                    if old != line:
                        changed = True
                    new_lines.append(line)
                    replaced = True
                else:
                    changed = True
            else:
                new_lines.append(old)
        if not replaced:
            new_lines.append(line)
            changed = True
        if not changed:
            self.log("Already configured: %s" % path, "info")
            return True
        return self.write_file(path, "\n".join(new_lines) + "\n",
                               chmod=chmod, mkdir=mkdir, backup=True)

    # ─── systemd ────────────────────────────────────────────────────────

    def unit_exists(self, name):
        try:
            res = subprocess.run(["systemctl", "list-unit-files", name,
                                  "--no-legend", "--no-pager"],
                                 capture_output=True, timeout=TIMEOUT_QUICK)
            for line in decode_bytes(res.stdout).splitlines():
                parts = line.split()
                if parts and parts[0] == name:
                    return True
        except Exception:
            pass
        return False

    def service_enabled(self, name):
        if not self.unit_exists(name):
            return "not-found"
        try:
            res = subprocess.run(["systemctl", "is-enabled", name],
                                 capture_output=True, timeout=TIMEOUT_QUICK)
            return decode_bytes(res.stdout).strip() or "unknown"
        except Exception:
            return "unknown"

    def service_active(self, name):
        try:
            res = subprocess.run(["systemctl", "is-active", name],
                                 capture_output=True, timeout=TIMEOUT_QUICK)
            return decode_bytes(res.stdout).strip() or "unknown"
        except Exception:
            return "unknown"

    def _spices(self):
        """True, если установлен cinnamon-spice-updater."""
        if not self.state.cinnamon:
            return False
        if shutil.which("cinnamon-spice-updater"):
            return True
        return os.path.exists("/usr/bin/cinnamon-spice-updater")

    # ─── GRUB ───────────────────────────────────────────────────────────

    @staticmethod
    def _grub_key(param):
        """Возвращает ключ параметра ядра (до '=')."""
        return param.split("=")[0]

    def add_grub_params(self, params):
        """Добавляет параметры в GRUB. Заменяет старые значения по тому же ключу."""
        if self.dry_run:
            self.log("[DRY RUN] GRUB add: " + " ".join(params), "warning")
            return True
        path = "/etc/default/grub"
        content = self.read_file(path)
        if content is None:
            self.log("Cannot read %s" % path, "error")
            return False
        keys = {self._grub_key(p) for p in params}
        lines, found, changed = [], False, False
        for line in lines_in(content):
            m = re.match(r"^\s*GRUB_CMDLINE_LINUX_DEFAULT=(.*)$", line)
            if m:
                found = True
                raw = m.group(1).strip().strip('"').strip("'")
                old_parts = [p for p in raw.split() if p]
                kept = [p for p in old_parts if self._grub_key(p) not in keys]
                new_parts = kept + list(params)
                new_line = 'GRUB_CMDLINE_LINUX_DEFAULT="' + " ".join(new_parts) + '"'
                if old_parts != new_parts:
                    changed = True
                lines.append(new_line)
            else:
                lines.append(line)
        if not found:
            lines.append('GRUB_CMDLINE_LINUX_DEFAULT="' + " ".join(params) + '"')
            changed = True
        if not changed:
            self.log("GRUB already has params", "info")
            return True
        if not self.write_file(path, "\n".join(lines) + "\n", backup=True):
            return False
        self.grub_changed = True
        self.log("GRUB: params added", "success")
        return True

    def _grub_set_param(self, token):
        """Ставит один параметр в GRUB_CMDLINE_LINUX_DEFAULT (заменяя по ключу).
        Создаёт строку, если её нет."""
        if self.dry_run:
            self.log("[DRY RUN] GRUB set: %s" % token, "warning")
            return True
        path = "/etc/default/grub"
        content = self.read_file(path)
        if content is None:
            self.log("Cannot read %s" % path, "error")
            return False
        key = self._grub_key(token)
        lines, found, changed = [], False, False
        for line in lines_in(content):
            m = re.match(r"^\s*GRUB_CMDLINE_LINUX_DEFAULT=(.*)$", line)
            if m:
                found = True
                raw = m.group(1).strip().strip('"').strip("'")
                old_parts = [p for p in raw.split() if p]
                kept = [p for p in old_parts if self._grub_key(p) != key]
                new_parts = kept + [token]
                new_line = 'GRUB_CMDLINE_LINUX_DEFAULT="' + " ".join(new_parts) + '"'
                if old_parts != new_parts:
                    changed = True
                lines.append(new_line)
            else:
                lines.append(line)
        if not found:
            lines.append('GRUB_CMDLINE_LINUX_DEFAULT="' + token + '"')
            changed = True
        if not changed:
            self.log("GRUB already has %s" % token, "info")
            return True
        if not self.write_file(path, "\n".join(lines) + "\n", backup=True):
            return False
        self.grub_changed = True
        self.log("GRUB: %s set" % token, "success")
        return True

    def _remove_grub_params(self, params):
        """Удаляет параметры из GRUB по ключу."""
        if self.dry_run:
            self.log("[DRY RUN] GRUB remove: " + " ".join(params), "warning")
            return True
        path = "/etc/default/grub"
        content = self.read_file(path)
        if not content:
            self.log("GRUB not found", "warning")
            return False
        keys = {self._grub_key(p) for p in params}
        new_lines, changed = [], False
        for line in lines_in(content):
            m = re.match(r"^\s*GRUB_CMDLINE_LINUX_DEFAULT=(.*)$", line)
            if m:
                raw = m.group(1).strip().strip('"').strip("'")
                old_parts = [p for p in raw.split() if p]
                new_parts = [p for p in old_parts
                             if self._grub_key(p) not in keys]
                new_lines.append('GRUB_CMDLINE_LINUX_DEFAULT="' +
                                 " ".join(new_parts) + '"')
                if old_parts != new_parts:
                    changed = True
            else:
                new_lines.append(line)
        if not changed:
            self.log("GRUB params not found", "info")
            return True
        if not self.write_file(path, "\n".join(new_lines) + "\n", backup=True):
            return False
        self.grub_changed = True
        self.log("✓ GRUB params removed", "success")
        return True

    def finalize_grub(self):
        """Запускает update-grub, если GRUB менялся."""
        if not self.grub_changed:
            return
        if self.dry_run:
            self.log("[DRY RUN] update-grub", "warning")
            self.grub_changed = False
            return
        ug = shutil.which("update-grub")
        if not ug and os.path.exists("/usr/sbin/update-grub"):
            ug = "/usr/sbin/update-grub"
        gm = shutil.which("grub-mkconfig")
        if not gm and os.path.exists("/usr/sbin/grub-mkconfig"):
            gm = "/usr/sbin/grub-mkconfig"
        if ug:
            self.sudo_run([ug], ok_msg="GRUB updated",
                          err_msg="update-grub failed",
                          timeout=SUDO_TIMEOUT_GRUB)
        elif gm:
            self.sudo_run([gm, "-o", "/boot/grub/grub.cfg"],
                          ok_msg="GRUB updated",
                          err_msg="grub-mkconfig failed",
                          timeout=SUDO_TIMEOUT_GRUB)
        else:
            self.log("update-grub / grub-mkconfig not found", "warning")
        self.grub_changed = False

    # ─── apply: базовые твики ───────────────────────────────────────────

    def apply_journald(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] journald volatile 50M", "warning")
            return True
        path = "/etc/systemd/journald.conf"
        if not self.path_exists(path):
            content = ""
        else:
            content = self.read_file(path)
            if content is None:
                self.log("Cannot read %s" % path, "error")
                return False
        if (re.search(r"^\s*Storage\s*=\s*volatile\s*$", content, re.M)
                and re.search(r"^\s*RuntimeMaxUse\s*=\s*50M\s*$", content, re.M)):
            self.log("journald already configured", "info")
            return True
        out = []
        inserted = False
        for line in lines_in(content):
            if (re.match(r"^\s*(Storage|RuntimeMaxUse)\s*=", line)
                    and not line.lstrip().startswith("#")):
                out.append("# " + line)
                continue
            out.append(line)
            if re.match(r"^\s*\[Journal\]\s*$", line) and not inserted:
                out += ["Storage=volatile", "RuntimeMaxUse=50M"]
                inserted = True
        if not inserted:
            out = ["[Journal]", "Storage=volatile", "RuntimeMaxUse=50M"] + out
        if not self.write_file(path, "\n".join(out) + "\n", backup=True):
            return False
        if not self.sudo_run(["systemctl", "restart", "systemd-journald"],
                             ignore_error=True):
            self.log("journald written but restart failed", "warning")
        self.sudo_run(["journalctl", "--vacuum-size=200M",
                       "--vacuum-time=1months"], ignore_error=True)
        self.log("✓ journald → volatile (50M)", "success")
        return True

    def apply_audit(self, params=None):
        return self.add_grub_params(["audit=0"])

    def apply_raid(self, params=None):
        if self.state.has_raid:
            self.log("RAID detected, skipping", "warning")
            return None
        return self.add_grub_params(["raid=noautodetect"])

    def apply_nmi_watchdog(self, params=None):
        return self.add_grub_params(["nmi_watchdog=0"])

    def apply_itco_wdt(self, params=None):
        if not getattr(self.state, "is_intel", False):
            self.log("Not an Intel system, skipping", "warning")
            return None
        if not getattr(self.state, "has_itco_module", False):
            self.log("iTCO_wdt module not available, skipping", "warning")
            return None
        path = "/etc/modprobe.d/nmi-watchdog.conf"
        content = ("blacklist iTCO_wdt\n"
                   "blacklist iTCO_vendor_support\n"
                   "install iTCO_wdt /bin/false\n"
                   "install iTCO_vendor_support /bin/false\n")
        if not self.write_file(path, content, chmod="644", mkdir=True):
            return False
        self.log("✓ iTCO_wdt blacklisted (needs reboot)", "success")
        return True

    def rollback_itco_wdt(self, params=None):
        self._rm("/etc/modprobe.d/nmi-watchdog.conf")
        self.sudo_run(["modprobe", "-r", "iTCO_wdt"], ignore_error=True)
        self.log("✓ iTCO_wdt blacklist removed", "success")
        return True

    # ─── shutdown_timeout ───────────────────────────────────────────────

    def apply_shutdown_timeout(self, params=None):
        """Ставит DefaultTimeoutStartSec/StopSec в /etc/systemd/system.conf."""
        params = params or {}
        val = str(params.get("shutdown_timeout_value",
                             SHUTDOWN_TIMEOUT_DEFAULT)).strip()
        if val not in SHUTDOWN_TIMEOUT_VALUES:
            self.log("Bad shutdown timeout value: %s" % val, "error")
            return False
        if self.dry_run:
            self.log("[DRY RUN] shutdown timeout = %s" % val, "warning")
            return True
        path = "/etc/systemd/system.conf"
        content = self.read_file(path)
        if content is None:
            self.log("Cannot read %s" % path, "error")
            return False
        lines = lines_in(content)
        new_lines = []
        seen_start = seen_stop = False
        for line in lines:
            s = line.strip()
            if s.startswith("#DefaultTimeoutStartSec="):
                new_lines.append("DefaultTimeoutStartSec=%s" % val)
                seen_start = True
            elif s.startswith("#DefaultTimeoutStopSec="):
                new_lines.append("DefaultTimeoutStopSec=%s" % val)
                seen_stop = True
            elif re.match(r"^\s*DefaultTimeoutStartSec\s*=", line):
                new_lines.append("DefaultTimeoutStartSec=%s" % val)
                seen_start = True
            elif re.match(r"^\s*DefaultTimeoutStopSec\s*=", line):
                new_lines.append("DefaultTimeoutStopSec=%s" % val)
                seen_stop = True
            else:
                new_lines.append(line)
        if not seen_start:
            new_lines.append("DefaultTimeoutStartSec=%s" % val)
        if not seen_stop:
            new_lines.append("DefaultTimeoutStopSec=%s" % val)
        if not self.write_file(path, "\n".join(new_lines) + "\n", backup=True):
            return False
        self.sudo_run(["systemctl", "daemon-reexec"], ignore_error=True)
        self.log("✓ shutdown timeout set to %s" % val, "success")
        return True

    def rollback_shutdown_timeout(self, params=None):
        """Комментирует строки DefaultTimeout*Sec и ставит дефолт 90s."""
        path = "/etc/systemd/system.conf"
        content = self.read_file(path)
        if not content:
            self.log("File not found: %s" % path, "info")
            return True
        lines = lines_in(content)
        new_lines = []
        for line in lines:
            if re.match(r"^\s*DefaultTimeoutStartSec\s*=", line):
                new_lines.append("#DefaultTimeoutStartSec=%s"
                                 % SHUTDOWN_TIMEOUT_SYSTEM_DEFAULT)
            elif re.match(r"^\s*DefaultTimeoutStopSec\s*=", line):
                new_lines.append("#DefaultTimeoutStopSec=%s"
                                 % SHUTDOWN_TIMEOUT_SYSTEM_DEFAULT)
            else:
                new_lines.append(line)
        if not self.write_file(path, "\n".join(new_lines) + "\n", backup=True):
            return False
        self.sudo_run(["systemctl", "daemon-reexec"], ignore_error=True)
        self.log("✓ shutdown timeout reset to 90s", "success")
        return True

    # ─── ZFS ────────────────────────────────────────────────────────────

    def apply_zfs_services(self, params=None):
        if self.dry_run:
            for u in ZFS_UNITS:
                self.log("[DRY RUN] systemctl disable --now %s" % u, "warning")
                self.log("[DRY RUN] systemctl mask %s" % u, "warning")
            return True
        ok_any = False
        for u in ZFS_UNITS:
            if not self.unit_exists(u):
                continue
            self.sudo_run(["systemctl", "disable", "--now", u], ignore_error=True)
            if self.sudo_run(["systemctl", "mask", u], ignore_error=True):
                ok_any = True
        if ok_any:
            self.log("✓ ZFS services masked", "success")
        return ok_any

    def rollback_zfs_services(self, params=None):
        if self.dry_run:
            for u in ZFS_UNITS:
                self.log("[DRY RUN] systemctl unmask %s" % u, "warning")
                self.log("[DRY RUN] systemctl enable %s" % u, "warning")
            return True
        for u in ZFS_UNITS:
            if not self.unit_exists(u):
                continue
            self.sudo_run(["systemctl", "unmask", u], ignore_error=True)
            self.sudo_run(["systemctl", "enable", u], ignore_error=True)
        self.log("✓ ZFS services unmasked", "success")
        return True

    def apply_zfs_remove_packages(self, params=None):
        if zfs_in_use():
            self.log("ZFS is in use, aborting package removal", "error")
            return False
        if not zfs_packages_installed():
            self.log("ZFS packages not installed", "info")
            return True
        if self.dry_run:
            self.log("[DRY RUN] apt purge zfs-zed zfsutils-linux", "warning")
            return True
        env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
        if not self.sudo_run(
                ["apt-get", "purge", "-y", "zfs-zed", "zfsutils-linux"],
                err_msg="apt purge ZFS failed",
                timeout=SUDO_TIMEOUT_APT, env=env):
            return False
        self.sudo_run(["apt-get", "autoremove", "-y"], ignore_error=True,
                      timeout=SUDO_TIMEOUT_APT, env=env)
        if not self.sudo_run(["update-initramfs", "-u", "-k", "all"],
                             ignore_error=True,
                             timeout=SUDO_TIMEOUT_INITRAMFS):
            self.log("update-initramfs failed after ZFS removal", "warning")
        if not self.sudo_run(["update-grub"], ignore_error=True,
                             timeout=SUDO_TIMEOUT_GRUB):
            self.log("update-grub failed after ZFS removal", "warning")
        self.log("✓ ZFS packages removed", "success")
        return True

    def rollback_zfs_remove_packages(self, params=None):
        self.log("Rollback of ZFS package removal is not supported. "
                 "Run 'sudo apt install zfsutils-linux' manually.", "warning")
        return False

    # ─── GPU: CoreCtrl ──────────────────────────────────────────────────

    def _polkit_is_new(self):
        """True, если polkit поддерживает новый формат правил (.rules)."""
        try:
            res = subprocess.run(["pkaction", "--version"],
                                 capture_output=True, text=True,
                                 timeout=TIMEOUT_QUICK)
            m = re.search(r"(\d+)\.(\d+)", (res.stdout or "") + (res.stderr or ""))
            if m:
                return int(m.group(1)) > 0 or int(m.group(2)) >= 106
        except Exception:
            pass
        return os.path.isdir("/etc/polkit-1/rules.d")

    def apply_corectrl(self, params=None):
        params = params or {}
        group = params.get("corectrl_group", "").strip() or self.state.user_name
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", group):
            self.log("Bad group name: %s" % group, "error")
            return False
        if self.dry_run:
            self.log("[DRY RUN] CoreCtrl polkit rule for %s" % group, "warning")
            return True
        import grp
        try:
            grp.getgrnam(group)
        except KeyError:
            self.log("Group not found: %s" % group, "error")
            return False
        if self._polkit_is_new():
            content = ("polkit.addRule(function(action, subject) {\n"
                       '    if ((action.id == "org.corectrl.helper.init" ||\n'
                       '         action.id == "org.corectrl.helperkiller.init") &&\n'
                       "        subject.local == true && subject.active == true &&\n"
                       '        subject.isInGroup("' + group + '")) {\n'
                       "        return polkit.Result.YES;\n"
                       "    }\n"
                       "});\n")
            path = "/etc/polkit-1/rules.d/90-corectrl.rules"
        else:
            content = ("[User permissions]\nIdentity=unix-group:" + group + "\n"
                       "Action=org.corectrl.*\nResultActive=yes\n")
            path = "/etc/polkit-1/localauthority/50-local.d/90-corectrl.pkla"
        if self.write_file(path, content, chmod="644", mkdir=True):
            self.log("✓ CoreCtrl configured for %s" % group, "success")
            return True
        return False

    def rollback_corectrl(self, params=None):
        self._rm("/etc/polkit-1/rules.d/90-corectrl.rules")
        self._rm("/etc/polkit-1/localauthority/50-local.d/90-corectrl.pkla")
        self.log("✓ CoreCtrl rule removed", "success")
        return True

    # ─── GPU: GRUB-параметры ────────────────────────────────────────────

    def apply_ppfeaturemask(self, params=None):
        return self.add_grub_params(["amdgpu.ppfeaturemask=0xffffffff"])

    def apply_nvidia_modeset(self, params=None):
        return self.add_grub_params(["nvidia-drm.modeset=1"])

    def apply_vrr(self, params=None):
        if self.state.gpu not in ("AMD", "Unknown"):
            self.log("VRR is AMD-only", "warning")
            return None
        if self.dry_run:
            self.log("[DRY RUN] VRR config", "warning")
            return True
        content = ('Section "Device"\n    Identifier "AMD"\n    Driver "amdgpu"\n'
                   '    Option "VariableRefresh" "true"\nEndSection\n')
        if self.write_file("/etc/X11/xorg.conf.d/20-amdgpu.conf", content,
                           chmod="644", mkdir=True):
            self.log("✓ VRR/FreeSync enabled", "success")
            return True
        return False

    def apply_radv(self, params=None):
        return self.ensure_line("/etc/environment", "RADV_PERFTEST=sam",
                                r"^\s*RADV_PERFTEST=.*")

    def apply_mesa(self, params=None):
        return self.ensure_line("/etc/environment",
                                "MESA_SHADER_CACHE_MAX_SIZE=4G",
                                r"^\s*MESA_SHADER_CACHE_MAX_SIZE=.*")

    # ─── GPU: PipeWire (с пресетами) ────────────────────────────────────

    def apply_pipewire(self, params=None):
        params = params or {}
        if not self.state.pipewire_active:
            self.log("PipeWire not active, skipping", "warning")
            return None
        preset_key = params.get("pipewire_preset", PIPEWIRE_PRESET_DEFAULT)
        if preset_key not in PIPEWIRE_PRESETS:
            preset_key = PIPEWIRE_PRESET_DEFAULT
        p = PIPEWIRE_PRESETS[preset_key]
        d = os.path.join(self.state.user_home, ".config", "pipewire",
                         "pipewire.conf.d")
        path = os.path.join(d, "10-sound.conf")
        content = ("context.properties = {\n"
                   "    default.clock.min-quantum = %d\n"
                   "    default.clock.quantum = %d\n"
                   "    default.clock.max-quantum = %d\n"
                   "}\n" % (p["min"], p["quantum"], p["max"]))
        if not self.write_user_file(path, content, backup=True):
            return False
        self.log("✓ PipeWire configured (%s)" % preset_key, "success")
        return True

    # ─── Сеть: BBR ──────────────────────────────────────────────────────

    def apply_bbr(self, params=None):
        path = "/etc/sysctl.d/99-bbr.conf"
        content = ("net.core.default_qdisc=fq\n"
                   "net.ipv4.tcp_congestion_control=bbr\n")
        if not self.write_file(path, content, chmod="644", mkdir=True):
            return False
        self.sudo_run(["modprobe", "tcp_bbr"], ignore_error=True)
        if not os.path.exists("/sys/module/tcp_bbr"):
            self.log("tcp_bbr module not available in this kernel", "warning")
            return False
        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        try:
            r = subprocess.run(["sysctl", "-n",
                                "net.ipv4.tcp_congestion_control"],
                               capture_output=True, text=True,
                               timeout=TIMEOUT_QUICK)
            cur = r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            cur = ""
        if cur != "bbr":
            self.log("BBR written but not active (current: %s)"
                     % (cur or "?"), "warning")
            return False
        self.log("✓ TCP BBR enabled", "success")
        return True

    # ─── Память: swap ───────────────────────────────────────────────────

    def apply_swap(self, params=None):
        params = params or {}
        if not self.state.has_swap:
            self.log("No swap found, skipping", "warning")
            return None
        val = params.get("swap_value", "").strip()
        if not val:
            val = (SWAPPINESS_DEFAULT_ZRAM if self.state.swap_type == "zram"
                   else SWAPPINESS_DEFAULT_DISK)
        try:
            iv = int(val)
            if iv < SWAPPINESS_MIN or iv > SWAPPINESS_MAX:
                raise ValueError
        except ValueError:
            self.log("Bad swappiness: %s (%d-%d)"
                     % (val, SWAPPINESS_MIN, SWAPPINESS_MAX), "error")
            return False
        if self.dry_run:
            self.log("[DRY RUN] swappiness=%d" % iv, "warning")
            return True
        path = "/etc/sysctl.d/99-gaming-swap.conf"
        ex = self.read_file(path)
        if ex and re.search(r"^vm\.swappiness=%d$" % iv, ex, re.M):
            self.log("swappiness already %d" % iv, "info")
            return True
        if not self.write_file(path, "vm.swappiness=%d\n" % iv,
                               chmod="644", mkdir=True):
            return False
        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        try:
            r = subprocess.run(["sysctl", "-n", "vm.swappiness"],
                               capture_output=True, text=True,
                               timeout=TIMEOUT_QUICK)
            cur = r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            cur = ""
        if cur != str(iv):
            self.log("swappiness written but not active (current: %s)"
                     % (cur or "?"), "warning")
            return False
        self.log("✓ swappiness=%d" % iv, "success")
        return True

    # ─── Память: zram, zswap, THP ───────────────────────────────────────

    def apply_zram(self, params=None):
        if not zram_generator_present():
            self.log("zram-generator not installed", "warning")
            return None
        path = "/etc/systemd/zram-generator.conf"
        content = ("[zram0]\nzram-size = ram-size / 2\n"
                   "compression-algorithm = zstd\n")
        if self.write_file(path, content, chmod="644", mkdir=True):
            self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
            self.log("✓ zram configured (reboot to activate)", "success")
            return True
        return False

    def apply_zswap(self, params=None):
        if not self.state.has_swap:
            self.log("No swap found, zswap skipped", "warning")
            return None
        pl = ["zswap.enabled=1", "zswap.compressor=zstd"]
        if os.path.exists("/sys/module/z3fold"):
            pl.append("zswap.zpool=z3fold")
        return self.add_grub_params(pl)

    def apply_thp(self, params=None):
        params = params or {}
        val = params.get("thp_value", "madvise")
        return self._grub_set_param("transparent_hugepage=%s" % val)

    # ─── sysctl: кэш, NUMA, REISUB ──────────────────────────────────────

    def _sysctl_set(self, key, val):
        """Устанавливает sysctl-параметр в /etc/sysctl.d/99-gaming-sysctl.conf."""
        if self.dry_run:
            self.log("[DRY RUN] %s=%s" % (key, val), "warning")
            return True
        path = "/etc/sysctl.d/99-gaming-sysctl.conf"
        content = self.read_file(path) or ""
        rx = re.compile(r"^\s*%s\s*=" % re.escape(key))
        out, replaced = [], False
        for l in lines_in(content):
            if rx.match(l):
                out.append("%s=%s" % (key, val))
                replaced = True
            else:
                out.append(l)
        if not replaced:
            out.append("%s=%s" % (key, val))
        if not self.write_file(path, "\n".join(out) + "\n", chmod="644",
                               mkdir=True, backup=True):
            return False
        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        try:
            r = subprocess.run(["sysctl", "-n", key],
                               capture_output=True, text=True,
                               timeout=TIMEOUT_QUICK)
            cur = r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            cur = ""
        if cur != str(val):
            self.log("%s written but not active (current: %s); "
                     "another sysctl.d file may override it"
                     % (key, cur or "?"), "warning")
            return False
        self.log("✓ %s=%s" % (key, val), "success")
        return True

    def _sysctl_del(self, key, default):
        """Удаляет sysctl-параметр из 99-gaming-sysctl.conf и ставит default."""
        if self.dry_run:
            self.log("[DRY RUN] remove %s" % key, "warning")
            return True
        path = "/etc/sysctl.d/99-gaming-sysctl.conf"
        content = self.read_file(path) or ""
        rx = re.compile(r"^\s*%s\s*=" % re.escape(key))
        old = lines_in(content)
        out = [l for l in old if not rx.match(l)]
        if len(out) == len(old):
            self.log("%s not found in %s" % (key, path), "info")
        else:
            if not self.write_file(path, "\n".join(out) + "\n", backup=True):
                return False
        self.sudo_run(["sysctl", "-w", "%s=%s" % (key, default)],
                      ignore_error=True)
        self.log("✓ %s reverted to %s" % (key, default), "success")
        return True

    def apply_sysctl_cache(self, params=None):
        return self._sysctl_set("vm.vfs_cache_pressure", "50")

    def apply_sysctl_numa(self, params=None):
        return self._sysctl_set("kernel.numa_balancing", "0")

    def apply_reisub(self, params=None):
        path = "/etc/sysctl.d/99-sysrq.conf"
        content = "kernel.sysrq=244\n"
        if not self.write_file(path, content, chmod="644", mkdir=True):
            return False
        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        try:
            r = subprocess.run(["sysctl", "-n", "kernel.sysrq"],
                               capture_output=True, text=True,
                               timeout=TIMEOUT_QUICK)
            cur = r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            cur = ""
        if cur != "244":
            self.log("kernel.sysrq written but not active (current: %s)"
                     % (cur or "?"), "warning")
            return False
        self.log("✓ Magic SysRq (REISUB) enabled", "success")
        return True

    # ─── Игры: max_map_count, ntsync ────────────────────────────────────

    def apply_max_map_count(self, params=None):
        params = params or {}
        val = str(params.get("max_map_count_value",
                             MAX_MAP_COUNT_DEFAULT)).strip()
        if val not in MAX_MAP_COUNT_VALUES:
            self.log("Bad max_map_count value: %s" % val, "error")
            return False
        if self.dry_run:
            self.log("[DRY RUN] vm.max_map_count=%s" % val, "warning")
            return True
        path = "/etc/sysctl.d/99-gaming-mmap.conf"
        content = "vm.max_map_count=%s\n" % val
        if not self.write_file(path, content, chmod="644", mkdir=True):
            return False
        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        try:
            with open("/proc/sys/vm/max_map_count", "r") as f:
                cur = f.read().strip()
        except Exception:
            cur = ""
        if cur != val:
            self.log("max_map_count written but not active (current: %s)"
                     % (cur or "?"), "warning")
            return False
        self.log("✓ vm.max_map_count=%s" % val, "success")
        return True

    def rollback_max_map_count(self, params=None):
        self._rm("/etc/sysctl.d/99-gaming-mmap.conf")
        self.sudo_run(["sysctl", "-w", "vm.max_map_count=65530"],
                      ignore_error=True)
        self.log("✓ vm.max_map_count back to 65530", "success")
        return True

    def apply_ntsync(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] ntsync modules-load", "warning")
            return True
        if self.state.ntsync:
            self.log("ntsync already available", "info")
            return True
        if not self.write_file("/etc/modules-load.d/ntsync.conf", "ntsync\n",
                               chmod="644", mkdir=True):
            return False
        if not self.sudo_run(["modprobe", "ntsync"], ignore_error=True):
            self.log("ntsync module not loaded (needs kernel 6.14+)", "warning")
            return False
        if not os.path.exists("/dev/ntsync"):
            self.log("ntsync loaded but /dev/ntsync not present", "warning")
            return False
        self.log("✓ ntsync autoloaded", "success")
        return True

    # ─── Диски: tmpfs /tmp ──────────────────────────────────────────────

    def apply_tmpfs_tmp(self, params=None):
        params = params or {}
        size = str(params.get("tmpfs_size_value", TMPFS_SIZE_DEFAULT)).strip() \
            or TMPFS_SIZE_DEFAULT
        if not re.fullmatch(TMPFS_SIZE_REGEX, size):
            self.log("Bad tmpfs size: %s" % size, "error")
            return False
        if self.dry_run:
            self.log("[DRY RUN] /tmp tmpfs size=%s" % size, "warning")
            return True
        path = "/etc/fstab"
        content = self.read_file(path)
        if not content:
            self.log("Cannot read /etc/fstab", "error")
            return False
        rx = re.compile(r"^\s*tmpfs\s+/tmp\s+tmpfs\s")
        old_lines = lines_in(content)
        new_lines, replaced, changed = [], False, False
        for line in old_lines:
            if rx.match(line):
                new_line = ("tmpfs\t/tmp\ttmpfs\t"
                            "defaults,mode=1777,size=%s\t0 0" % size)
                if line.strip() != new_line:
                    changed = True
                new_lines.append(new_line)
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            new_lines.append("tmpfs\t/tmp\ttmpfs\t"
                             "defaults,mode=1777,size=%s\t0 0" % size)
            changed = True
        if not changed:
            self.log("/tmp tmpfs already configured with size %s" % size, "info")
            return True
        if not self.write_file(path, "\n".join(new_lines) + "\n", backup=True):
            return False
        if not self.verify_fstab():
            self.log("fstab verification failed — /tmp tmpfs may be unsafe",
                     "error")
            return False
        self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
        self.log("✓ /tmp in tmpfs configured (needs reboot)", "success")
        return True

    def rollback_tmpfs_tmp(self, params=None):
        path = "/etc/fstab"
        content = self.read_file(path)
        if not content:
            self.log("Cannot read /etc/fstab", "error")
            return False
        rx = re.compile(r"^\s*tmpfs\s+/tmp\s+tmpfs\s")
        old = lines_in(content)
        new = [l for l in old if not rx.match(l)]
        if len(new) == len(old):
            self.log("/tmp tmpfs not found in fstab", "info")
            return True
        if not self.write_file(path, "\n".join(new) + "\n", backup=True):
            return False
        if not self.verify_fstab():
            self.log("fstab verification failed after rollback", "error")
            return False
        self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
        self.log("✓ /tmp tmpfs removed (reboot to apply)", "success")
        return True

    # ─── Диски: ntfs3 ───────────────────────────────────────────────────

    def apply_ntfs3(self, params=None):
        if not getattr(self.state, "has_ntfs_partitions", False):
            self.log("No NTFS partitions found, skipping", "warning")
            return None
        if self.dry_run:
            self.log("[DRY RUN] ntfs3 unlock", "warning")
            return True
        path = "/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"
        if not self.path_exists(path):
            self.log("mint-blacklist-ntfs3.conf not found", "warning")
            return None
        content = self.read_file(path)
        if content is None:
            self.log("Cannot read %s" % path, "error")
            return False
        if not content.strip():
            self.log("File is empty, nothing to unlock", "info")
            return True
        if re.search(r"^\s*#\s*blacklist\s+ntfs3\s*$", content, re.M):
            self.log("ntfs3 already unlocked", "info")
            return True
        if re.search(r"^\s*blacklist\s+ntfs3\s*$", content, re.M):
            new = re.sub(r"^\s*blacklist\s+ntfs3\s*$", "# blacklist ntfs3",
                         content, flags=re.M)
            if self.write_file(path, new, backup=True):
                self.log("✓ ntfs3 unlocked", "success")
                return True
            return False
        self.log("blacklist ntfs3 not found", "warning")
        return None

    def rollback_ntfs3(self, params=None):
        path = "/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"
        content = self.read_file(path)
        if not content:
            self.log("File not found: %s" % path, "info")
            return True
        if re.search(r"^\s*blacklist\s+ntfs3\s*$", content, re.M):
            self.log("ntfs3 already blocked", "info")
            return True
        new = re.sub(r"^\s*#\s*blacklist\s+ntfs3\s*$", "blacklist ntfs3",
                     content, flags=re.M)
        if self.write_file(path, new, backup=True):
            self.log("✓ ntfs3 blocked again", "success")
            return True
        return False

    # ─── fstab: определение устройств и поиск строк ─────────────────────

    def _device_identifiers(self, dev):
        """Возвращает список идентификаторов: UUID=..., LABEL=..., PARTUUID=..."""
        idents = []
        try:
            res = subprocess.run(["lsblk", "-no", "UUID,LABEL,PARTUUID", dev],
                                 capture_output=True, text=True,
                                 timeout=TIMEOUT_QUICK)
            if res.returncode == 0:
                parts = res.stdout.strip().split(None, 2)
                if len(parts) >= 1 and parts[0]:
                    idents.append("UUID=%s" % parts[0])
                if len(parts) >= 2 and parts[1]:
                    idents.append("LABEL=%s" % parts[1])
                if len(parts) >= 3 and parts[2]:
                    idents.append("PARTUUID=%s" % parts[2])
        except Exception:
            pass
        return idents

    def _uuid_of(self, dev):
        """Возвращает UUID устройства (для совместимости)."""
        try:
            res = subprocess.run(["lsblk", "-no", "UUID", dev],
                                 capture_output=True, text=True,
                                 timeout=TIMEOUT_QUICK)
            return res.stdout.strip() if res.returncode == 0 else ""
        except Exception:
            return ""

    def _fstab_find(self, lines, mp, dev):
        """Ищет строку fstab по mp или по идентификатору устройства
        (UUID=, LABEL=, PARTUUID=). Возвращает (index, parts) или (None, None)."""
        idents = []
        if dev:
            idents = self._device_identifiers(dev)
        for i, line in enumerate(lines):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            f = s.split()
            if len(f) < 4:
                continue
            if f[1] == mp:
                return i, f
            if idents:
                first_lower = f[0].lower()
                for ident in idents:
                    if first_lower == ident.lower():
                        return i, f
        return None, None

    def _dev_of(self, mp):
        """Возвращает устройство для точки монтирования."""
        return next((it["dev"] for it in self.mount_items
                     if mp in it.get("mps", [])), None)

    def _fstype_of_mp(self, mp):
        """Возвращает ФС для точки монтирования."""
        for it in self.mount_items:
            if mp in it.get("mps", []):
                return it.get("fstype", "").lower()
        return ""

    # ─── fstab: правка noatime ──────────────────────────────────────────

    def _mount_opts_edit(self, mp, add=True):
        """Правит только noatime/nodiratime. commit= не трогает."""
        path = "/etc/fstab"
        content = self.read_file(path)
        if not content:
            self.log("Cannot read /etc/fstab", "error")
            return False
        dev = self._dev_of(mp)
        lines = lines_in(content)
        idx, parts = self._fstab_find(lines, mp, dev)
        if idx is None:
            self.log("%s not found in fstab — skipped" % mp, "warning")
            return None
        opts = parts[3].split(",")
        if add:
            if "noatime" not in opts:
                opts.append("noatime")
            else:
                self.log("fstab %s already has noatime" % mp, "info")
                return True
        else:
            filtered = [o for o in opts if o not in ("noatime", "nodiratime")]
            if filtered == opts:
                self.log("fstab %s has no noatime" % mp, "info")
                return True
            opts = filtered
        parts[3] = ",".join(opts)
        lines[idx] = "\t".join(parts)
        if not self.write_file(path, "\n".join(lines) + "\n", backup=True):
            return False
        if not self.verify_fstab():
            self.log("fstab verification failed after editing %s" % mp, "error")
            return False
        if add:
            self.log("✓ fstab %s: +noatime" % mp, "success")
        else:
            self.log("✓ fstab %s: noatime removed" % mp, "success")
        return True

    def apply_mount_opts(self, mps):
        if self.dry_run:
            for mp in mps:
                self.log("[DRY RUN] fstab %s +noatime" % mp, "warning")
            return True
        ok = True
        for mp in mps:
            r = self._mount_opts_edit(mp, True)
            if r is False:
                ok = False
        return ok

    def rollback_mount_opts(self, mps):
        if self.dry_run:
            for mp in mps:
                self.log("[DRY RUN] fstab %s -noatime" % mp, "warning")
            return True
        ok = True
        for mp in mps:
            r = self._mount_opts_edit(mp, False)
            if r is False:
                ok = False
        return ok

    # ─── fstab: правка commit= ──────────────────────────────────────────

    def _mount_commit_edit(self, mp, val, add=True):
        path = "/etc/fstab"
        fstype = self._fstype_of_mp(mp)
        if add and not fs_supports_commit(fstype):
            self.log("Skipped %s (%s): commit= is only valid for ext2/3/4"
                     % (mp, fstype or "unknown"), "warning")
            return None
        content = self.read_file(path)
        if not content:
            self.log("Cannot read /etc/fstab", "error")
            return False
        dev = self._dev_of(mp)
        lines = lines_in(content)
        idx, parts = self._fstab_find(lines, mp, dev)
        if idx is None:
            self.log("%s not found in fstab — skipped" % mp, "warning")
            return None
        opts = [o for o in parts[3].split(",") if not o.startswith("commit=")]
        if add:
            opts.append("commit=%s" % val)
        parts[3] = ",".join(opts)
        lines[idx] = "\t".join(parts)
        if not self.write_file(path, "\n".join(lines) + "\n", backup=True):
            return False
        if not self.verify_fstab():
            self.log("fstab verification failed after commit edit on %s" % mp,
                     "error")
            return False
        return True

    def apply_commit(self, params=None):
        params = params or {}
        val = str(params.get("commit_value", COMMIT_DEFAULT)).strip() \
            or COMMIT_DEFAULT
        try:
            iv = int(val)
            if iv < COMMIT_MIN or iv > COMMIT_MAX:
                raise ValueError
        except ValueError:
            self.log("Bad commit value: %s (%d-%d)"
                     % (val, COMMIT_MIN, COMMIT_MAX), "error")
            return False
        val = str(iv)
        targets = list(self.commit_targets)
        if not targets:
            self.log("commit=: no ext2/3/4 partitions selected", "warning")
            return None
        if self.dry_run:
            for mp in targets:
                self.log("[DRY RUN] fstab %s commit=%s" % (mp, val), "warning")
            return None
        ok = True
        applied_any = False
        for mp in targets:
            fstype = self._fstype_of_mp(mp)
            if not fs_supports_commit(fstype):
                self.log("Skipped %s (%s): commit= unsupported here"
                         % (mp, fstype or "unknown"), "warning")
                continue
            r = self._mount_commit_edit(mp, val, True)
            if r is True:
                applied_any = True
            elif r is False:
                ok = False
        if applied_any and ok:
            self.log("✓ fstab commit=%s applied" % val, "success")
        return ok

    def rollback_commit(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] fstab remove commit", "warning")
            return True
        targets = list(self.commit_targets)
        if not targets:
            return True
        ok = True
        for mp in targets:
            r = self._mount_commit_edit(mp, "", False)
            if r is False:
                ok = False
        if ok:
            self.log("✓ fstab commit removed", "success")
        return ok

    def _commit_value_for(self, mp):
        """Возвращает строку 'commit=NN' для точки монтирования или ''."""
        try:
            with open("/etc/fstab", "r", encoding="utf-8",
                      errors="replace") as f:
                content = f.read()
        except Exception:
            return ""
        for line in lines_in(content):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            f2 = s.split()
            if len(f2) >= 4 and f2[1] == mp:
                for opt in f2[3].split(","):
                    if opt.startswith("commit="):
                        return opt
                return ""
        return ""

    def _commit_applied(self):
        try:
            with open("/etc/fstab", "r", encoding="utf-8",
                      errors="replace") as f:
                content = f.read()
        except Exception:
            return False
        candidates = self.commit_targets or [
            mp for m in self.mount_items
            if fs_supports_commit(m.get("fstype", ""))
            for mp in m["mps"]]
        if not candidates:
            return False
        for mp in candidates:
            fstype = self._fstype_of_mp(mp)
            if not fs_supports_commit(fstype):
                continue
            for line in lines_in(content):
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                f2 = s.split()
                if len(f2) >= 4 and f2[1] == mp:
                    if any(o.startswith("commit=") for o in f2[3].split(",")):
                        return True
        return False

    # ─── Steam: симлинки compatdata ─────────────────────────────────────

    def apply_steam_links(self, libs):
        src = os.path.join(self.state.user_home, ".steam", "steam",
                           "steamapps", "compatdata")
        try:
            os.makedirs(src, exist_ok=True)
        except Exception as e:
            self.log("Cannot create %s: %s" % (src, e), "error")
            return False
        for lib in libs:
            dst = os.path.join(lib, "compatdata")
            if os.path.realpath(lib) == os.path.realpath(os.path.dirname(src)):
                continue
            if self.dry_run:
                self.log("[DRY RUN] ln -s %s -> %s" % (src, dst), "warning")
                continue
            try:
                if os.path.islink(dst):
                    os.remove(dst)
                elif os.path.isdir(dst):
                    self.log("Skipped: %s exists as data directory" % dst,
                             "warning")
                    continue
                elif os.path.exists(dst):
                    self.log("Skipped: %s exists" % dst, "warning")
                    continue
                os.symlink(src, dst)
                self.log("✓ symlink created: %s" % dst, "success")
            except Exception as e:
                self.log("Symlink error %s: %s" % (dst, e), "error")
        return True

    def rollback_steam_links(self, libs):
        for lib in libs:
            dst = os.path.join(lib, "compatdata")
            if self.dry_run:
                self.log("[DRY RUN] rm %s" % dst, "warning")
                continue
            try:
                if os.path.islink(dst):
                    os.remove(dst)
                    self.log("✓ symlink removed: %s" % dst, "success")
                else:
                    self.log("Not a symlink, untouched: %s" % dst, "info")
            except Exception as e:
                self.log("Remove error %s: %s" % (dst, e), "error")
        return True

    # ─── .bashrc: aliases ───────────────────────────────────────────────

    def apply_aliases(self, params=None):
        bashrc = os.path.join(self.state.user_home, ".bashrc")
        if self.dry_run:
            self.log("[DRY RUN] add commands to .bashrc", "warning")
            return True
        if not self.path_exists(bashrc):
            self.log(".bashrc not found: %s" % bashrc, "error")
            return False
        content = self.read_file(bashrc)
        if content is None:
            self.log("Cannot read .bashrc", "error")
            return False
        sm = "# >>> system-tuneup commands >>>"
        em = "# <<< system-tuneup commands <<<"
        without, skip = [], False
        for line in lines_in(content):
            if line.strip() == sm:
                skip = True
                continue
            if line.strip() == em:
                skip = False
                continue
            if not skip:
                without.append(line)
        names = ["upd", "upgr", "spices", "update_all", "inst", "remove",
                 "search", "info", "clean", "space", "fix", "mem", "serv",
                 "update_time"]
        np_ = "|".join(names)
        alias_rx = re.compile(r"^\s*alias\s+(" + np_ + r")=")
        func_rx = re.compile(r"^\s*(" + np_ + r")\s*\(\)\s*\{")
        cleaned, skip_fn, warned = [], False, False
        for line in without:
            if alias_rx.match(line):
                if not warned:
                    self.log("Existing user aliases with same names found "
                             "— left untouched outside tuneup block",
                             "warning")
                    warned = True
                cleaned.append(line)
                continue
            if func_rx.match(line):
                if not warned:
                    self.log("Existing user functions with same names found "
                             "— left untouched outside tuneup block",
                             "warning")
                    warned = True
                cleaned.append(line)
                if "}" in line:
                    continue
                skip_fn = True
                continue
            if skip_fn:
                cleaned.append(line)
                if line.strip().startswith("}"):
                    skip_fn = False
                continue
            if "system-tuneup" in line and line.strip().startswith("#"):
                continue
            cleaned.append(line)
        spices, has_fp = self._spices(), self.state.has_flatpak
        block = [sm, "# system-tuneup commands", ""]
        block += ["upd() {", '    echo "APT update..."',
                  "    sudo apt update", "}", ""]
        block += ["upgr() {", '    echo "APT upgrade..."',
                  "    sudo apt full-upgrade"]
        if has_fp:
            block.append('    echo "Flatpak update..."')
            if spices:
                block.append("    flatpak update && "
                             "cinnamon-spice-updater --update-all")
            else:
                block.append("    flatpak update")
        block += ["}", ""]
        if spices:
            block += ["spices() {", '    echo "Cinnamon spices update..."',
                      "    cinnamon-spice-updater --update-all", "}", ""]
        block += ["update_all() {",
                  "    sudo apt update && sudo apt full-upgrade -y"]
        if has_fp:
            block.append("    flatpak update -y")
        if spices:
            block.append("    cinnamon-spice-updater --update-all")
        block += ['    echo "Done."', "}", ""]
        block += ["# Extra commands (system-tuneup)",
                  'inst() { sudo apt install "$@"; }',
                  'remove() { sudo apt purge --autoremove "$@"; }',
                  'search() { apt search "$@"; }',
                  'info() { apt show "$@"; }', ""]
        block += ["clean() {",
                  "    sudo apt autoremove -y && sudo apt autoclean && "
                  "sudo apt clean", "}", ""]
        block += ["space() {", "    df -h /", "}", ""]
        block += ["fix() {", "    sudo apt --fix-broken install -y",
                  "    sudo dpkg --configure -a", "}", ""]
        block += ["mem() {", "    sync && sudo sh -c "
                  "'echo 3 > /proc/sys/vm/drop_caches' && free -h", "}", ""]
        block += ["serv() {",
                  "    systemctl list-unit-files --type=service | less",
                  "}", ""]
        block += ["update_time() {",
                  "    systemctl list-timers --no-pager 2>/dev/null | "
                  'grep -E "NEXT|upgrade|update|apt" || echo "No timers"',
                  "}", ""]
        block.append(em)
        while cleaned and cleaned[-1].strip() == "":
            cleaned.pop()
        new = "\n".join(cleaned + [""] + block) + "\n"
        if new == content:
            self.log("Commands already added", "info")
            return True
        if not self.write_file(bashrc, new, backup=True):
            return False
        if self.state.user_name and self.state.user_name != "root":
            self.sudo_run(["chown",
                           "%s:%s" % (self.state.user_name,
                                      self.state.user_name),
                           bashrc], ignore_error=True)
        self.log("✓ commands added to .bashrc", "success")
        return True

    # ─── Автообновления ─────────────────────────────────────────────────

    APT_DAILY_UNITS = [
        "apt-daily.timer",
        "apt-daily-upgrade.timer",
        "apt-daily.service",
        "apt-daily-upgrade.service",
        "unattended-upgrades.service",
        "mintupdate-automation-upgrade.timer",
        "mintupdate-automation-upgrade.service",
    ]

    def _mask_apt_daily(self):
        if self.dry_run:
            for u in self.APT_DAILY_UNITS:
                self.log("[DRY RUN] mask %s" % u, "warning")
            return True
        masked_any = False
        for u in self.APT_DAILY_UNITS:
            if not self.unit_exists(u):
                continue
            self.sudo_run(["systemctl", "disable", "--now", u],
                          ignore_error=True)
            if self.sudo_run(["systemctl", "mask", u], ignore_error=True):
                masked_any = True
        if masked_any:
            self.log("✓ apt-daily / unattended-upgrades masked", "success")
        return True

    def _unmask_apt_daily(self):
        if self.dry_run:
            for u in self.APT_DAILY_UNITS:
                self.log("[DRY RUN] unmask %s" % u, "warning")
            return True
        for u in self.APT_DAILY_UNITS:
            if not self.unit_exists(u):
                continue
            self.sudo_run(["systemctl", "unmask", u], ignore_error=True)
            self.sudo_run(["systemctl", "enable", u], ignore_error=True)
        self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
        self.log("✓ apt-daily / unattended-upgrades unmasked and enabled",
                 "success")
        return True

    def apply_autoupdate(self, params=None):
        params = params or {}
        sched = params.get("update_schedule", "Отключено")
        table = {
            "Ежедневно": ("*-*-* 18:30:00", "daily 18:30"),
            "Еженедельно (суббота)": ("Sat 18:30:00", "weekly Sat"),
            "2 раза в месяц (1 и 15)": ("*-*-1,15 18:30:00", "1st & 15th"),
            "Ежемесячно (1 число)": ("*-*-1 18:30:00", "monthly 1st"),
            "Daily": ("*-*-* 18:30:00", "daily 18:30"),
            "Weekly (Saturday)": ("Sat 18:30:00", "weekly Sat"),
            "Twice a month (1 & 15)": ("*-*-1,15 18:30:00", "1st & 15th"),
            "Monthly (1st)": ("*-*-1 18:30:00", "monthly 1st"),
            "Disabled": (None, None), "Отключено": (None, None),
        }
        svc = "/etc/systemd/system/biweekly-upgrade.service"
        tmr = "/etc/systemd/system/biweekly-upgrade.timer"
        exists = self.path_exists(tmr) or self.path_exists(svc)
        if sched in ("Отключено", "Disabled"):
            if not exists:
                self.log("Auto-update timer not found", "info")
                self._unmask_apt_daily()
                return True
            if self.dry_run:
                self.log("[DRY RUN] remove timer", "warning")
                return True
            self.sudo_run(
                ["systemctl", "disable", "--now", "biweekly-upgrade.timer"],
                ignore_error=True)
            self.sudo_run(["rm", "-f", svc, tmr], ignore_error=True)
            self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
            self._unmask_apt_daily()
            self.log("Auto-update timer removed", "success")
            return True
        if sched not in table:
            self.log("Unknown schedule: %s" % sched, "error")
            return False
        onc, desc = table[sched]
        spices = self._spices()
        cmd = ("DEBIAN_FRONTEND=noninteractive apt-get update && "
               "DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y")
        if self.state.has_flatpak:
            cmd += " && flatpak update -y"
        if spices:
            cmd += " && cinnamon-spice-updater --update-all"
        svc_c = ("[Unit]\nDescription=System upgrade (%s)\n\n[Service]\n"
                 "Type=oneshot\nExecStartPre=/bin/sleep 600\n"
                 "Environment=DEBIAN_FRONTEND=noninteractive\n"
                 "ExecStart=/usr/bin/bash -c \"%s\"\nUser=root\n" % (desc, cmd))
        tmr_c = ("[Unit]\nDescription=System upgrade timer (%s)\n\n[Timer]\n"
                 "OnCalendar=%s\nPersistent=true\n\n[Install]\n"
                 "WantedBy=timers.target\n" % (desc, onc))
        ex_svc = self.read_file(svc) or ""
        ex_tmr = self.read_file(tmr) or ""
        if exists and ex_svc == svc_c and ex_tmr == tmr_c:
            self.log("Timer already configured: %s" % desc, "info")
            if (self.service_enabled("biweekly-upgrade.timer") != "enabled"
                    and not self.dry_run):
                self.sudo_run(["systemctl", "daemon-reload"],
                              ignore_error=True)
                self.sudo_run(
                    ["systemctl", "enable", "--now", "biweekly-upgrade.timer"],
                    ignore_error=True)
            self._mask_apt_daily()
            return True
        if self.dry_run:
            self.log("[DRY RUN] create timer: %s" % desc, "warning")
            return True
        if not self.write_file(svc, svc_c, chmod="644", backup=True):
            return False
        if not self.write_file(tmr, tmr_c, chmod="644", backup=True):
            return False
        self._mask_apt_daily()
        self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
        self.sudo_run(["systemctl", "enable", "--now",
                       "biweekly-upgrade.timer"],
                      ok_msg="✓ timer created: %s" % desc,
                      err_msg="Cannot enable timer")
        return True

    def rollback_autoupdate(self, params=None):
        ok = self.apply_autoupdate({"update_schedule": "Отключено"})
        self._unmask_apt_daily()
        return ok

    # ─── Удаление приложений ────────────────────────────────────────────

    def apps_purge(self, pkgs):
        """Удаляет пакеты через apt purge + autoremove. Возвращает (ok, freed)."""
        if self.dry_run:
            self.log("[DRY RUN] apt purge " + " ".join(pkgs), "warning")
            return True, "?"
        freed = estimate_packages_size(pkgs)
        env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
        if not self.sudo_run(["apt-get", "purge", "-y"] + list(pkgs),
                             err_msg="apt purge failed",
                             timeout=SUDO_TIMEOUT_APT, env=env):
            return False, "?"
        self.sudo_run(["apt-get", "autoremove", "-y"], ignore_error=True,
                      timeout=SUDO_TIMEOUT_APT, env=env)
        return True, freed

    # ─── Вспомогательные: удаление файлов и строк ───────────────────────

    def _rm(self, path):
        """Удаляет файл (или путь) через sudo."""
        if self.dry_run:
            self.log("[DRY RUN] rm %s" % path, "warning")
            return True
        if not self.path_exists(path):
            self.log("File not found: %s" % path, "info")
            return True
        return self.sudo_run(["rm", "-f", path],
                             ok_msg="✓ removed %s" % path)

    def _remove_line(self, path, pattern):
        """Удаляет строки, соответствующие regex pattern, из файла path."""
        if self.dry_run:
            self.log("[DRY RUN] %s: remove %s" % (path, pattern), "warning")
            return True
        content = self.read_file(path)
        if not content:
            self.log("File not found: %s" % path, "info")
            return True
        rx = re.compile(pattern)
        old = lines_in(content)
        new = [l for l in old if not rx.match(l.strip())]
        if len(new) == len(old):
            self.log("Line not found in %s" % path, "info")
            return True
        return self.write_file(path, "\n".join(new) + "\n", backup=True)

    # ─── rollback: базовые твики ────────────────────────────────────────

    def rollback_journald(self, params=None):
        path = "/etc/systemd/journald.conf"
        safe = path.lstrip("/").replace("/", "_")
        pattern = os.path.join(self.backup_dir, safe + ".*.bak")
        candidates = sorted(glob.glob(pattern),
                            key=lambda p: os.path.getmtime(p),
                            reverse=True)
        if candidates:
            c = self.read_file(candidates[0])
            if c:
                self.write_file(path, c, backup=True)
                self.sudo_run(["systemctl", "restart", "systemd-journald"],
                              ignore_error=True)
                self.log("✓ journald restored from backup", "success")
                return True
        self._remove_line(path, r"^\s*Storage\s*=")
        self._remove_line(path, r"^\s*RuntimeMaxUse\s*=")
        self.sudo_run(["systemctl", "restart", "systemd-journald"],
                      ignore_error=True)
        self.log("✓ journald back to defaults", "success")
        return True

    def rollback_audit(self, params=None):
        return self._remove_grub_params(["audit=0"])

    def rollback_raid(self, params=None):
        return self._remove_grub_params(["raid=noautodetect"])

    def rollback_nmi_watchdog(self, params=None):
        return self._remove_grub_params(["nmi_watchdog=0"])

    def rollback_ppfeaturemask(self, params=None):
        return self._remove_grub_params(["amdgpu.ppfeaturemask=0xffffffff"])

    def rollback_nvidia_modeset(self, params=None):
        return self._remove_grub_params(["nvidia-drm.modeset=1"])

    def rollback_vrr(self, params=None):
        """Восстанавливает VRR-конфиг из свежего бэкапа, иначе удаляет."""
        path = "/etc/X11/xorg.conf.d/20-amdgpu.conf"
        if not self.path_exists(path):
            self.log("VRR config not found, nothing to rollback", "info")
            return True
        safe = path.lstrip("/").replace("/", "_")
        pattern = os.path.join(self.backup_dir, safe + ".*.bak")
        candidates = sorted(glob.glob(pattern),
                            key=lambda p: os.path.getmtime(p),
                            reverse=True)
        if candidates:
            c = self.read_file(candidates[0])
            if c:
                if self.write_file(path, c, backup=True):
                    self.log("✓ VRR config restored from backup", "success")
                    return True
        self._rm(path)
        self.log("✓ VRR config removed", "success")
        return True

    def rollback_radv(self, params=None):
        self._remove_line("/etc/environment", r"^\s*RADV_PERFTEST=.*")
        self.log("✓ RADV_PERFTEST removed", "success")
        return True

    def rollback_mesa(self, params=None):
        self._remove_line("/etc/environment",
                          r"^\s*MESA_SHADER_CACHE_MAX_SIZE=.*")
        self.log("✓ MESA cache removed", "success")
        return True

    def rollback_pipewire(self, params=None):
        path = os.path.join(self.state.user_home, ".config", "pipewire",
                            "pipewire.conf.d", "10-sound.conf")
        self.remove_user_file(path)
        self.log("✓ PipeWire config removed", "success")
        return True

    def rollback_bbr(self, params=None):
        self._rm("/etc/sysctl.d/99-bbr.conf")
        self.sudo_run(["sysctl", "-w",
                       "net.ipv4.tcp_congestion_control=cubic"],
                      ignore_error=True)
        self.sudo_run(["sysctl", "-w", "net.core.default_qdisc=pfifo_fast"],
                      ignore_error=True)
        self.log("✓ BBR and fq reverted", "success")
        return True

    def rollback_swap(self, params=None):
        self._rm("/etc/sysctl.d/99-gaming-swap.conf")
        self.sudo_run(["sysctl", "-w", "vm.swappiness=60"], ignore_error=True)
        self.log("✓ swappiness back to 60", "success")
        return True

    def rollback_zram(self, params=None):
        self._rm("/etc/systemd/zram-generator.conf")
        self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
        return True

    def rollback_zswap(self, params=None):
        return self._remove_grub_params(["zswap.enabled=1",
                                         "zswap.compressor=zstd",
                                         "zswap.zpool=z3fold"])

    def rollback_thp(self, params=None):
        return self._remove_grub_params(["transparent_hugepage=always",
                                         "transparent_hugepage=madvise",
                                         "transparent_hugepage=never"])

    def rollback_sysctl_cache(self, params=None):
        return self._sysctl_del("vm.vfs_cache_pressure", "100")

    def rollback_sysctl_numa(self, params=None):
        return self._sysctl_del("kernel.numa_balancing", "1")

    def rollback_reisub(self, params=None):
        self._rm("/etc/sysctl.d/99-sysrq.conf")
        self.sudo_run(["sysctl", "-w", "kernel.sysrq=176"], ignore_error=True)
        self.log("✓ kernel.sysrq back to 176", "success")
        return True

    def rollback_ntsync(self, params=None):
        self._rm("/etc/modules-load.d/ntsync.conf")
        self.log("✓ ntsync removed", "success")
        return True

    def rollback_aliases(self, params=None):
        bashrc = os.path.join(self.state.user_home, ".bashrc")
        content = self.read_file(bashrc)
        if not content:
            self.log(".bashrc not found", "info")
            return True
        sm = "# >>> system-tuneup commands >>>"
        em = "# <<< system-tuneup commands <<<"
        lines, skip = [], False
        for line in lines_in(content):
            if line.strip() == sm:
                skip = True
                continue
            if line.strip() == em:
                skip = False
                continue
            if not skip:
                lines.append(line)
        if len(lines) == len(lines_in(content)):
            self.log("Command block not found", "info")
            return True
        if not self.write_file(bashrc, "\n".join(lines) + "\n", backup=True):
            return False
        if self.state.user_name and self.state.user_name != "root":
            self.sudo_run(["chown",
                           "%s:%s" % (self.state.user_name,
                                      self.state.user_name),
                           bashrc], ignore_error=True)
        self.log("✓ commands removed from .bashrc", "success")
        return True      
