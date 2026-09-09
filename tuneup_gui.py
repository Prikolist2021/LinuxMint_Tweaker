#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
  SYSTEM TUNEUP GUI v0.1
  Графическая оболочка для тюнинга Linux Mint / Ubuntu / Debian
═══════════════════════════════════════════════════════════════════════════════
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog, filedialog

import subprocess
import os
import sys
import threading
import queue
import re
import pwd
import grp
import time
import shutil

APP_VERSION = "0.1"


# ─── ТЕМЫ ─────────────────────────────────────────────────────────────────────

THEMES = {
    "light": {
        "bg": "#f5f5f5",
        "fg": "#1e1e1e",
        "green": "#2e7d32",
        "yellow": "#f57f17",
        "red": "#c62828",
        "blue": "#1565c0",
        "orange": "#e65100",
        "gray": "#757575",
        "terminal_bg": "#ffffff",
        "terminal_fg": "#1e1e1e",
        "entry_bg": "#ffffff",
        "entry_fg": "#1e1e1e",
        "select_color": "#e0e0e0",
        "button_bg": "#e0e0e0",
        "button_fg": "#1e1e1e",
        "accent_bg": "#4caf50",
        "accent_fg": "#ffffff",
        "tree_bg": "#ffffff",
        "tree_fg": "#1e1e1e",
        "tree_heading_bg": "#e0e0e0",
        "tree_heading_fg": "#1e1e1e",
        "notebook_tab_bg": "#e0e0e0",
        "notebook_tab_selected": "#ffffff",
        "scrollbar_trough": "#e0e0e0",
        "scrollbar_slider": "#bdbdbd",
    },
    "dark": {
        "bg": "#1e1e1e",
        "fg": "#d4d4d4",
        "green": "#4ec9b0",
        "yellow": "#d7ba7d",
        "red": "#f44747",
        "blue": "#569cd6",
        "orange": "#ce9178",
        "gray": "#808080",
        "terminal_bg": "#0c0c0c",
        "terminal_fg": "#d4d4d4",
        "entry_bg": "#333333",
        "entry_fg": "#d4d4d4",
        "select_color": "#333333",
        "button_bg": "#444444",
        "button_fg": "#d4d4d4",
        "accent_bg": "#4ec9b0",
        "accent_fg": "#1e1e1e",
        "tree_bg": "#252525",
        "tree_fg": "#d4d4d4",
        "tree_heading_bg": "#333333",
        "tree_heading_fg": "#ffffff",
        "notebook_tab_bg": "#333333",
        "notebook_tab_selected": "#555555",
        "scrollbar_trough": "#2d2d2d",
        "scrollbar_slider": "#555555",
    },
}


# ─── РЕКОМЕНДУЕМЫЕ СЛУЖБЫ ────────────────────────────────────────────────────

SERVICES = [
    {"name": "avahi-daemon.service", "desc": "Сетевое обнаружение устройств"},
    {"name": "avahi-daemon.socket", "desc": "Сокет-активатор Avahi"},
    {"name": "cups-browsed.service", "desc": "Поиск сетевых принтеров"},
    {"name": "ModemManager.service", "desc": "Управление USB-модемами"},
    {"name": "openvpn.service", "desc": "Встроенный VPN-сервер"},
    {"name": "lvm2-monitor.service", "desc": "Мониторинг LVM-томов"},
    {"name": "switcheroo-control.service", "desc": "Переключение видеокарт"},
    {"name": "touchegg.service", "desc": "Жесты тачпада"},
    {"name": "zfs-zed.service", "desc": "Мониторинг ZFS"},
    {"name": "kerneloops.service", "desc": "Отчёты об ошибках ядра"},
]


# ─── УТИЛИТЫ ─────────────────────────────────────────────────────────────────

def decode_bytes(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


# ─── SUDO MANAGER ────────────────────────────────────────────────────────────

class SudoManager:
    def __init__(self):
        self.parent = None
        self.authenticated = False
        self._keepalive_running = False

    def set_parent(self, parent):
        self.parent = parent

    def _sudo_cached(self):
        try:
            res = subprocess.run(
                ["sudo", "-n", "true"], capture_output=True, timeout=3
            )
            return res.returncode == 0
        except Exception:
            return False

    def authenticate(self):
        if self._sudo_cached():
            self.authenticated = True
            self._start_keepalive()
            return True

        for attempt in range(1, 4):
            password = None
            try:
                password = simpledialog.askstring(
                    "Авторизация",
                    f"Введите пароль sudo (попытка {attempt} из 3):",
                    parent=self.parent,
                    show="*",
                )
                if password is None:
                    return False
                if not password:
                    messagebox.showwarning(
                        "Пароль", "Пароль не может быть пустым.",
                        parent=self.parent,
                    )
                    continue
                res = subprocess.run(
                    ["sudo", "-S", "-v"],
                    input=(password + "\n").encode(),
                    capture_output=True, timeout=15,
                )
                if res.returncode == 0:
                    self.authenticated = True
                    self._start_keepalive()
                    return True
                messagebox.showerror(
                    "Ошибка sudo",
                    "Неверный пароль или нет прав sudo.",
                    parent=self.parent,
                )
            except Exception as e:
                messagebox.showerror(
                    "Ошибка sudo", f"Не удалось выполнить sudo:\n{e}",
                    parent=self.parent,
                )
            finally:
                password = None
        return False

    def ensure(self):
        if self._sudo_cached():
            self.authenticated = True
            self._start_keepalive()
            return True
        return self.authenticate()

    def run(self, args, input=None):
        if not self._sudo_cached():
            raise PermissionError(
                "Сессия sudo истекла. Нажмите Применить заново."
            )
        return subprocess.run(
            ["sudo", "-n"] + list(args),
            input=input, capture_output=True, timeout=180,
        )

    def _start_keepalive(self):
        if self._keepalive_running:
            return
        self._keepalive_running = True

        def loop():
            try:
                while True:
                    time.sleep(50)
                    try:
                        if not self._sudo_cached():
                            break
                        subprocess.run(
                            ["sudo", "-n", "-v"],
                            capture_output=True, timeout=5,
                        )
                    except Exception:
                        pass
            finally:
                self._keepalive_running = False
                self.authenticated = False

        threading.Thread(target=loop, daemon=True).start()


# ─── СОСТОЯНИЕ СИСТЕМЫ ───────────────────────────────────────────────────────

class SystemState:
    def __init__(self):
        self.gpu = "Unknown"
        self.has_raid = False
        self.has_swap = False
        self.swap_type = ""
        self.ntsync = False
        self.cinnamon = False
        self.has_flatpak = False
        self.has_spice_updater = False
        self.user_name = "root"
        self.user_home = "/root"

    def detect(self):
        try:
            self.user_name = self._get_real_user()
        except Exception:
            self.user_name = "root"
        try:
            self.user_home = pwd.getpwnam(self.user_name).pw_dir
        except Exception:
            self.user_home = os.path.expanduser("~")

        try:
            res = subprocess.run(
                ["lspci"], capture_output=True, text=True, timeout=5
            )
            for line in res.stdout.lower().splitlines():
                if "vga" in line or "3d controller" in line:
                    if "amd" in line or "radeon" in line:
                        self.gpu = "AMD"; break
                    elif "nvidia" in line:
                        self.gpu = "NVIDIA"; break
                    elif "intel" in line:
                        self.gpu = "Intel"; break
        except Exception:
            pass

        try:
            if os.path.isfile("/proc/mdstat"):
                with open("/proc/mdstat", "r", encoding="utf-8", errors="replace") as f:
                    if re.search(r"^md\d+", f.read(), re.M):
                        self.has_raid = True
        except Exception:
            pass

        try:
            res = subprocess.run(
                ["lsblk", "-n", "-o", "TYPE"],
                capture_output=True, text=True, timeout=5,
            )
            if "raid" in res.stdout:
                self.has_raid = True
        except Exception:
            pass

        try:
            res = subprocess.run(
                ["swapon", "--show=TYPE", "--noheadings"],
                capture_output=True, text=True, timeout=5,
            )
            out = res.stdout.strip()
            if out:
                self.has_swap = True
                if "zram" in out:
                    self.swap_type = "zram"
                elif "partition" in out:
                    self.swap_type = "partition"
                else:
                    self.swap_type = "file"
        except Exception:
            pass

        self.ntsync = os.path.exists("/dev/ntsync")

        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session = os.environ.get("DESKTOP_SESSION", "").lower()
        if "cinnamon" in desktop or session == "cinnamon":
            self.cinnamon = True
        else:
            try:
                res = subprocess.run(
                    ["pgrep", "-x", "cinnamon"],
                    capture_output=True, timeout=3,
                )
                self.cinnamon = res.returncode == 0
            except Exception:
                pass

        self.has_flatpak = bool(shutil.which("flatpak"))
        self.has_spice_updater = bool(
            shutil.which("cinnamon-spice-updater")
            or os.path.exists("/usr/bin/cinnamon-spice-updater")
        )

    def _get_real_user(self):
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user and sudo_user != "root":
            return sudo_user
        pkexec_user = os.environ.get("PKEXEC_USER")
        if pkexec_user and pkexec_user != "root":
            return pkexec_user
        pkexec_uid = os.environ.get("PKEXEC_UID")
        if pkexec_uid:
            try:
                return pwd.getpwuid(int(pkexec_uid)).pw_name
            except Exception:
                pass
        if os.getuid() != 0:
            return pwd.getpwuid(os.getuid()).pw_name
        user_env = os.environ.get("USER")
        if user_env and user_env != "root":
            return user_env
        try:
            for pw in pwd.getpwall():
                if pw.pw_uid >= 1000 and pw.pw_name not in ("nobody", "nfsnobody"):
                    return pw.pw_name
        except Exception:
            pass
        return "root"


# ─── ОПЕРАЦИИ СИСТЕМЫ ────────────────────────────────────────────────────────

class SystemOps:
    def __init__(self, sudo, state, log, dry_run):
        self.sudo = sudo
        self.state = state
        self.log = log
        self.dry_run = dry_run
        self.grub_changed = False
        self.backup_dir = os.path.join(
            state.user_home, ".local", "share", "system-tuneup", "backups"
        )

    def backup_file(self, path):
        if self.dry_run:
            return
        try:
            if not self.path_exists(path):
                return
            os.makedirs(self.backup_dir, exist_ok=True)
            safe_name = path.lstrip("/").replace("/", "_")
            ts = time.strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"{safe_name}.{ts}.bak")
            content = self.read_file(path)
            if content is None:
                return
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(content)
            if self.state.user_name and self.state.user_name != "root":
                try:
                    pw = pwd.getpwnam(self.state.user_name)
                    os.chown(backup_path, pw.pw_uid, pw.pw_gid)
                except Exception:
                    pass
            backups = sorted(
                [f for f in os.listdir(self.backup_dir)
                 if f.startswith(safe_name) and f.endswith(".bak")],
                reverse=True,
            )
            for old in backups[5:]:
                try:
                    os.remove(os.path.join(self.backup_dir, old))
                except Exception:
                    pass
            self.log(f"[BACKUP] {os.path.basename(backup_path)}", "info")
        except Exception as e:
            self.log(f"[WARN] Бэкап {path}: {e}", "warning")

    def sudo_run(self, args, input=None, ok_msg=None, err_msg=None, ignore_error=False):
        if self.dry_run:
            self.log("[DRY RUN] " + " ".join(args), "warning")
            return True
        try:
            res = self.sudo.run(args, input=input)
        except PermissionError as e:
            self.log(str(e), "error")
            return False
        except Exception as e:
            self.log(f"Ошибка команды: {e}", "error")
            return False
        if res.returncode == 0:
            if ok_msg:
                self.log(ok_msg, "success")
            return True
        err = decode_bytes(res.stderr).strip()
        if not ignore_error:
            msg = err_msg or f"Ошибка: {' '.join(args)}"
            if err:
                self.log(f"[ERR] {msg}\n   {err}", "error")
            else:
                self.log(f"[ERR] {msg}", "error")
        else:
            if err and "already" not in err.lower() and "not found" not in err.lower():
                self.log(f"[WARN] {' '.join(args)}: {err[:120]}", "warning")
        return False

    def path_exists(self, path):
        if os.path.exists(path):
            return True
        try:
            res = subprocess.run(
                ["sudo", "-n", "test", "-e", path],
                capture_output=True, timeout=3,
            )
            return res.returncode == 0
        except Exception:
            return False

    def read_file(self, path):
        if not self.path_exists(path):
            return ""
        try:
            res = subprocess.run(
                ["sudo", "-n", "cat", path],
                capture_output=True, timeout=5,
            )
            if res.returncode == 0:
                return decode_bytes(res.stdout)
        except Exception:
            pass
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None

    def write_file(self, path, content, chmod="644", owner=None, mkdir=False, backup=True):
        if self.dry_run:
            self.log(f"[DRY RUN] Запись: {path}", "warning")
            return True
        if mkdir:
            d = os.path.dirname(path)
            if d:
                self.sudo_run(["mkdir", "-p", d], ignore_error=True)
        if backup:
            self.backup_file(path)
        try:
            res = self.sudo.run(["tee", path], input=content.encode())
        except PermissionError as e:
            self.log(str(e), "error")
            return False
        except Exception as e:
            self.log(f"Ошибка записи {path}: {e}", "error")
            return False
        if res.returncode != 0:
            self.log(f"Не удалось записать {path}", "error")
            return False
        if chmod:
            self.sudo_run(["chmod", chmod, path], ignore_error=True)
        if owner:
            self.sudo_run(["chown", owner, path], ignore_error=True)
        return True

    def ensure_line(self, path, line, pattern, chmod="644", owner=None, mkdir=False):
        if self.dry_run:
            self.log(f"[DRY RUN] {path}: {line}", "warning")
            return True
        content = self.read_file(path)
        if content is None:
            self.log(f"Не удалось прочитать {path}", "error")
            return False
        lines = content.splitlines()
        new_lines = []
        replaced = False
        changed = False
        try:
            rx = re.compile(pattern)
        except re.error:
            rx = re.compile(re.escape(line))
        for old_line in lines:
            if rx.match(old_line.strip()):
                if not replaced:
                    if old_line != line:
                        changed = True
                    new_lines.append(line)
                    replaced = True
                else:
                    changed = True
            else:
                new_lines.append(old_line)
        if not replaced:
            new_lines.append(line)
            changed = True
        if not changed:
            self.log(f"Уже настроено: {path}", "info")
            return True
        self.backup_file(path)
        return self.write_file(
            path, "\n".join(new_lines) + "\n",
            chmod=chmod, owner=owner, mkdir=mkdir, backup=False,
        )

    def unit_exists(self, name):
        try:
            res = subprocess.run(
                ["systemctl", "list-unit-files", name, "--no-legend", "--no-pager"],
                capture_output=True, timeout=5,
            )
            for line in decode_bytes(res.stdout).splitlines():
                parts = line.split()
                if parts and parts[0] == name:
                    return True
            return False
        except Exception:
            return False

    def service_enabled(self, name):
        if not self.unit_exists(name):
            return "not-found"
        try:
            res = subprocess.run(
                ["systemctl", "is-enabled", name],
                capture_output=True, timeout=5,
            )
            return decode_bytes(res.stdout).strip() or "unknown"
        except Exception:
            return "unknown"

    def service_active(self, name):
        try:
            res = subprocess.run(
                ["systemctl", "is-active", name],
                capture_output=True, timeout=5,
            )
            return decode_bytes(res.stdout).strip() or "unknown"
        except Exception:
            return "unknown"

    def _has_cinnamon_spices(self):
        return self.state.cinnamon and self.state.has_spice_updater

    def _has_flatpak(self):
        return self.state.has_flatpak

    def add_grub_params(self, params):
        if self.dry_run:
            self.log("[DRY RUN] GRUB: " + " ".join(params), "warning")
            return True
        path = "/etc/default/grub"
        if not self.path_exists(path):
            self.log(f"{path} не найден", "warning")
            return False
        content = self.read_file(path)
        if content is None:
            self.log(f"Не удалось прочитать {path}", "error")
            return False
        lines = content.splitlines()
        new_lines = []
        found = False
        changed = False
        for line in lines:
            m = re.match(r"^\s*GRUB_CMDLINE_LINUX_DEFAULT=(.*)$", line)
            if m:
                found = True
                raw = m.group(1).strip()
                if raw.startswith('"') and raw.endswith('"'):
                    val = raw[1:-1]
                elif raw.startswith("'") and raw.endswith("'"):
                    val = raw[1:-1]
                else:
                    val = raw.strip("\"'")
                parts = [p for p in val.split() if p]
                orig_parts = parts.copy()
                for param in params:
                    if param not in parts:
                        parts.append(param)
                if parts != orig_parts:
                    new_lines.append(f'GRUB_CMDLINE_LINUX_DEFAULT="{" ".join(parts)}"')
                    changed = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f'GRUB_CMDLINE_LINUX_DEFAULT="{" ".join(params)}"')
            changed = True
        if not changed:
            self.log("GRUB уже содержит нужные параметры", "info")
            return True
        self.backup_file(path)
        if self.write_file(path, "\n".join(new_lines) + "\n", backup=False):
            self.grub_changed = True
            self.log("GRUB: параметры добавлены", "success")
            return True
        return False

    def finalize_grub(self):
        if not self.grub_changed:
            return
        if self.dry_run:
            self.log("[DRY RUN] update-grub", "warning")
            return
        cmd = None
        if shutil.which("update-grub"):
            cmd = ["update-grub"]
        elif os.path.exists("/usr/sbin/update-grub"):
            cmd = ["/usr/sbin/update-grub"]
        elif shutil.which("grub-mkconfig"):
            cmd = ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"]
        elif os.path.exists("/usr/sbin/grub-mkconfig"):
            cmd = ["/usr/sbin/grub-mkconfig", "-o", "/boot/grub/grub.cfg"]
        if cmd:
            self.sudo_run(cmd, ok_msg="GRUB обновлён", err_msg="Ошибка GRUB")
        else:
            self.log("update-grub / grub-mkconfig не найдены", "warning")
        self.grub_changed = False

    # --- apply_* методы (сокращённые для компактности, логика идентична v2.2) ---

    def apply_rsyslog(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] disable --now + mask rsyslog", "warning"); return True
        enabled = self.service_enabled("rsyslog.service")
        if enabled in ("disabled", "masked", "not-found"):
            self.log("rsyslog уже отключён", "info"); return True
        ok1 = self.sudo_run(["systemctl", "disable", "--now", "rsyslog"], ignore_error=True)
        ok2 = self.sudo_run(["systemctl", "mask", "rsyslog"], ignore_error=True)
        if ok1 or ok2:
            self.log("[OK] rsyslog отключён", "success"); return True
        self.log("[ERR] Не удалось отключить rsyslog", "error"); return False

    def apply_journald(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] journald -> volatile", "warning"); return True
        path = "/etc/systemd/journald.conf"
        content = self.read_file(path)
        if content is None:
            self.log(f"Не удалось прочитать {path}", "error"); return False
        if (re.search(r"^\s*Storage\s*=\s*volatile\s*$", content, re.M)
                and re.search(r"^\s*RuntimeMaxUse\s*=\s*50M\s*$", content, re.M)):
            self.log("journald уже настроен", "info"); return True
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            if re.match(r"^\s*Storage\s*=", line) or re.match(r"^\s*RuntimeMaxUse\s*=", line):
                new_lines.append(line if line.lstrip().startswith("#") else "# " + line)
            else:
                new_lines.append(line)
        new_lines += ["Storage=volatile", "RuntimeMaxUse=50M"]
        self.backup_file(path)
        if not self.write_file(path, "\n".join(new_lines) + "\n", backup=False):
            return False
        self.sudo_run(["systemctl", "restart", "systemd-journald"], ignore_error=True)
        self.sudo_run(["journalctl", "--vacuum-size=200M", "--vacuum-time=1months"], ignore_error=True)
        self.log("[OK] journald -> volatile (50M)", "success"); return True

    def apply_audit(self, params=None):
        return self.add_grub_params(["audit=0"])

    def apply_raid(self, params=None):
        if self.state.has_raid:
            self.log("RAID обнаружен, пропуск", "warning"); return True
        return self.add_grub_params(["raid=noautodetect"])

    def apply_corectrl(self, params=None):
        params = params or {}
        group = params.get("corectrl_group", "sudo").strip() or "sudo"
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", group):
            self.log(f"Некорректная группа: {group}", "error"); return False
        if self.dry_run:
            self.log(f"[DRY RUN] CoreCtrl для {group}", "warning"); return True
        try:
            grp.getgrnam(group)
        except KeyError:
            self.log(f"Группа не найдена: {group}", "error"); return False
        path = "/etc/polkit-1/rules.d/90-corectrl.rules"
        if self.path_exists(path):
            self.log(f"[WARN] {path} будет перезаписан", "warning")
        content = f"""polkit.addRule(function(action, subject) {{
    if ((action.id == "org.corectrl.helper.init" ||
         action.id == "org.corectrl.helperkiller.init") &&
        subject.local == true && subject.active == true &&
        subject.isInGroup("{group}")) {{
        return polkit.Result.YES;
    }}
}});
"""
        if self.write_file(path, content, chmod="644", mkdir=True):
            self.log(f"[OK] CoreCtrl для {group}", "success"); return True
        return False

    def apply_ppfeaturemask(self, params=None):
        return self.add_grub_params(["amdgpu.ppfeaturemask=0xffffffff"])

    def apply_vrr(self, params=None):
        if self.state.gpu not in ("AMD", "Unknown"):
            self.log("VRR только для AMD", "warning"); return True
        if self.dry_run:
            self.log("[DRY RUN] VRR/FreeSync", "warning"); return True
        path = "/etc/X11/xorg.conf.d/20-amdgpu.conf"
        if self.path_exists(path):
            self.log(f"[WARN] {path} будет перезаписан", "warning")
        content = 'Section "Device"\n    Identifier "AMD"\n    Driver "amdgpu"\n    Option "VariableRefresh" "true"\nEndSection\n'
        if self.write_file(path, content, chmod="644", mkdir=True):
            self.log("[OK] VRR/FreeSync включён", "success"); return True
        return False

    def apply_pipewire(self, params=None):
        d = os.path.join(self.state.user_home, ".config", "pipewire", "pipewire.conf.d")
        path = os.path.join(d, "10-sound.conf")
        if self.dry_run:
            self.log(f"[DRY RUN] PipeWire: {path}", "warning"); return True
        if self.path_exists(path):
            self.log(f"[WARN] {path} будет перезаписан", "warning")
        content = "context.properties = {\n    default.clock.min-quantum = 512\n    default.clock.quantum = 4096\n    default.clock.max-quantum = 8192\n}\n"
        if not self.sudo_run(["mkdir", "-p", d], ignore_error=True):
            return False
        if not self.write_file(path, content, chmod="644"):
            return False
        if self.state.user_name and self.state.user_name != "root":
            self.sudo_run(
                ["chown", "-R", f"{self.state.user_name}:{self.state.user_name}",
                 os.path.join(self.state.user_home, ".config", "pipewire")],
                ignore_error=True,
            )
        self.log("[OK] PipeWire настроен", "success"); return True

    def apply_mesa(self, params=None):
        return self.ensure_line("/etc/environment", "MESA_SHADER_CACHE_MAX_SIZE=4G",
                                r"^\s*MESA_SHADER_CACHE_MAX_SIZE=.*")

    def apply_radv(self, params=None):
        return self.ensure_line("/etc/environment", "RADV_PERFTEST=sam",
                                r"^\s*RADV_PERFTEST=.*")

    def apply_swap(self, params=None):
        params = params or {}
        if not self.state.has_swap:
            self.log("Swap не найден, пропуск", "warning"); return True
        val = params.get("swap_value", "").strip()
        if not val:
            val = "150" if self.state.swap_type == "zram" else "10"
        try:
            int_val = int(val)
            if int_val < 0 or int_val > 200:
                raise ValueError
        except ValueError:
            self.log(f"Некорректный swappiness: {val}", "error"); return False
        if self.dry_run:
            self.log(f"[DRY RUN] swappiness={int_val}", "warning"); return True
        path = "/etc/sysctl.d/99-gaming-swap.conf"
        existing = self.read_file(path)
        if existing and re.search(rf"^vm\.swappiness={int_val}$", existing, re.M):
            self.log(f"swappiness уже {int_val}", "info"); return True
        if not self.write_file(path, f"vm.swappiness={int_val}\n", chmod="644", mkdir=True):
            return False
        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        self.log(f"[OK] swappiness={int_val}", "success"); return True

    def apply_sysctl(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] sysctl tuning", "warning"); return True
        path = "/etc/sysctl.d/99-gaming-sysctl.conf"
        existing = self.read_file(path)
        if existing:
            if (re.search(r"^vm\.vfs_cache_pressure=50$", existing, re.M)
                    and re.search(r"^kernel\.numa_balancing=0$", existing, re.M)):
                self.log("sysctl уже настроен", "info"); return True
        content = "vm.vfs_cache_pressure=50\nkernel.numa_balancing=0\n"
        if not self.write_file(path, content, chmod="644", mkdir=True):
            return False
        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        self.log("[OK] sysctl настроен", "success"); return True

    def apply_ntsync(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] ntsync", "warning"); return True
        if self.state.ntsync:
            self.log("ntsync уже доступен", "info"); return True
        path = "/etc/modules-load.d/ntsync.conf"
        if not self.write_file(path, "ntsync\n", chmod="644", mkdir=True):
            return False
        self.sudo_run(["modprobe", "ntsync"], ignore_error=True)
        self.log("[OK] ntsync в автозагрузке", "success"); return True

    def apply_ntfs3(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] ntfs3 unlock", "warning"); return True
        path = "/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"
        if not self.path_exists(path):
            self.log("mint-blacklist-ntfs3.conf не найден", "warning"); return True
        content = self.read_file(path)
        if content is None:
            self.log(f"Не удалось прочитать {path}", "error"); return False
        if re.search(r"^\s*#\s*blacklist\s+ntfs3\s*$", content, re.M):
            self.log("ntfs3 уже раскомментирован", "info"); return True
        if re.search(r"^\s*blacklist\s+ntfs3\s*$", content, re.M):
            self.backup_file(path)
            new_content = re.sub(r"^\s*blacklist\s+ntfs3\s*$", "# blacklist ntfs3", content, flags=re.M)
            if self.write_file(path, new_content, backup=False):
                self.log("[OK] ntfs3 раскомментирован", "success"); return True
            return False
        self.log("blacklist ntfs3 не найден", "warning"); return True

    def apply_aliases(self, params=None):
        bashrc = os.path.join(self.state.user_home, ".bashrc")
        if self.dry_run:
            self.log(f"[DRY RUN] Алиасы в {bashrc}", "warning"); return True
        if not self.path_exists(bashrc):
            self.log(f".bashrc не найден", "error"); return False
        content = self.read_file(bashrc)
        if content is None:
            self.log("Не удалось прочитать .bashrc", "error"); return False

        start_marker = "# >>> system-tuneup commands >>>"
        end_marker = "# <<< system-tuneup commands <<<"
        lines = content.splitlines()
        without_block = []
        skip = False
        for line in lines:
            if line.strip() == start_marker: skip = True; continue
            if line.strip() == end_marker: skip = False; continue
            if not skip: without_block.append(line)

        names = ["upd","upgr","spices","update_all","inst","remove","search","info","clean","space","fix","mem","serv","update_time"]
        alias_rx = re.compile(r"^\s*alias\s+(" + "|".join(names) + r")=")
        func_rx = re.compile(r"^\s*(" + "|".join(names) + r")\s*\(\)\s*\{")
        cleaned = []
        skip_fn = False
        for line in without_block:
            if alias_rx.match(line): continue
            if func_rx.match(line):
                if "}" in line: continue
                skip_fn = True; continue
            if skip_fn:
                if line.strip().startswith("}"): skip_fn = False
                continue
            if "system-tuneup" in line and line.strip().startswith("#"): continue
            cleaned.append(line)

        spices = self._has_cinnamon_spices()
        has_fp = self._has_flatpak()
        if not has_fp:
            self.log("[WARN] flatpak не найден", "warning")

        block = [start_marker, "# system-tuneup commands", ""]
        block += ["upd() {", '    echo "APT update..."', "    sudo apt update", "}", ""]
        block.append("upgr() {")
        block.append('    echo "APT upgrade..."')
        block.append("    sudo apt full-upgrade")
        if has_fp:
            block.append('    echo "Flatpak update..."')
            if spices:
                block.append("    flatpak update && cinnamon-spice-updater --update-all")
            else:
                block.append("    flatpak update")
        block += ["}", ""]
        if spices:
            block += ["spices() {", "    cinnamon-spice-updater --update-all", "}", ""]
        block.append("update_all() {")
        block.append("    sudo apt update && sudo apt full-upgrade -y")
        if has_fp:
            block.append("    flatpak update -y")
            if spices:
                block.append("    cinnamon-spice-updater --update-all")
        block += ['    echo "Done."', "}", ""]
        block += ['# Extra aliases', 'inst() { sudo apt install "$@"; }',
                   'remove() { sudo apt purge --autoremove "$@"; }',
                   'search() { apt search "$@"; }', 'info() { apt show "$@"; }']
        block.append(end_marker)

        while cleaned and cleaned[-1].strip() == "":
            cleaned.pop()
        new_content = "\n".join(cleaned + [""] + block) + "\n"
        if new_content == content:
            self.log("Алиасы уже добавлены", "info"); return True
        self.backup_file(bashrc)
        if not self.write_file(bashrc, new_content, backup=False):
            return False
        if self.state.user_name and self.state.user_name != "root":
            self.sudo_run(["chown", f"{self.state.user_name}:{self.state.user_name}", bashrc], ignore_error=True)
        self.log("[OK] Алиасы добавлены", "success"); return True

    def apply_autoupdate(self, params=None):
        params = params or {}
        schedule_ui = params.get("update_schedule", "Отключено")
        schedules = {
            "Ежедневно": ("*-*-* 18:30:00", "ежедневно в 18:30"),
            "Еженедельно (суббота)": ("Sat 18:30:00", "еженедельно по субботам"),
            "2 раза в месяц": ("*-*-1,15 18:30:00", "1 и 15 числа"),
            "Ежемесячно": ("*-*-1 18:30:00", "ежемесячно 1 числа"),
        }
        svc = "/etc/systemd/system/biweekly-upgrade.service"
        tmr = "/etc/systemd/system/biweekly-upgrade.timer"
        exists = self.path_exists(tmr) or self.path_exists(svc)

        if schedule_ui == "Отключено":
            if not exists:
                self.log("Таймер не найден", "info"); return True
            if self.dry_run:
                self.log("[DRY RUN] Удалить таймер", "warning"); return True
            self.sudo_run(["systemctl", "disable", "--now", "biweekly-upgrade.timer"], ignore_error=True)
            self.sudo_run(["rm", "-f", svc, tmr], ignore_error=True)
            self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
            self.log("[OK] Таймер удалён", "success"); return True

        if schedule_ui not in schedules:
            self.log(f"Неизвестное расписание: {schedule_ui}", "error"); return False
        oncalendar, desc = schedules[schedule_ui]
        spices = self._has_cinnamon_spices()
        has_fp = self._has_flatpak()
        full_cmd = "apt update && apt full-upgrade -y"
        if has_fp:
            full_cmd += " && flatpak update -y"
        if spices:
            full_cmd += " && cinnamon-spice-updater --update-all"

        svc_content = f'[Unit]\nDescription=System upgrade ({desc})\n\n[Service]\nType=oneshot\nExecStartPre=/bin/sleep 600\nExecStart=/usr/bin/bash -c "{full_cmd}"\nUser=root\n'
        tmr_content = f'[Unit]\nDescription=System upgrade timer ({desc})\n\n[Timer]\nOnCalendar={oncalendar}\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n'

        ex_svc = self.read_file(svc)
        ex_tmr = self.read_file(tmr)
        if exists and ex_svc == svc_content and ex_tmr == tmr_content:
            self.log(f"Таймер уже настроен: {desc}", "info")
            if self.service_enabled("biweekly-upgrade.timer") != "enabled":
                if not self.dry_run:
                    self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
                    self.sudo_run(["systemctl", "enable", "--now", "biweekly-upgrade.timer"], ignore_error=True)
            return True

        if self.dry_run:
            self.log(f"[DRY RUN] Создать таймер: {desc}", "warning"); return True
        self.sudo_run(["systemctl", "disable", "--now", "mintupdate-automation-upgrade.timer"], ignore_error=True)
        if not self.write_file(svc, svc_content, chmod="644"):
            return False
        if not self.write_file(tmr, tmr_content, chmod="644"):
            return False
        self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
        self.sudo_run(["systemctl", "enable", "--now", "biweekly-upgrade.timer"],
                       ok_msg=f"[OK] Таймер: {desc}", err_msg="Ошибка таймера")
        return True


# ─── ГЛАВНОЕ ПРИЛОЖЕНИЕ ──────────────────────────────────────────────────────

class TuneupApp:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.is_running = False
        self.current_theme = "light"

        self.dry_run_var = tk.BooleanVar(value="--dry-run" in sys.argv)

        self.sudo = SudoManager()
        self.sudo.set_parent(root)

        self.state = SystemState()
        self.state.detect()

        self.corectrl_group = tk.StringVar(value="sudo")
        self.swap_value = tk.StringVar(
            value="150" if self.state.swap_type == "zram" else "10"
        )
        self.update_schedule = tk.StringVar(value="Еженедельно (суббота)")

        self.options = self._create_options()
        self.option_widgets = {}

        # Определяем DPI для адаптации к HD-экранам
        self.dpi_scale = max(1.0, self.root.winfo_fpixels('1i') / 96.0)

        self.create_ui()
        self.apply_hardware_restrictions()
        self.update_title()

        self.root.after(100, self.process_queue)

        self.log("System Tuneup GUI запущен", "success")
        self.log(f"Версия: {APP_VERSION}", "info")
        self.log(f"GPU: {self.state.gpu}", "info")
        self.log(f"DPI scale: {self.dpi_scale:.2f}", "info")

        if self.dry_run_var.get():
            self.log("Режим: СУХОЙ ПРОГОН", "warning")

        if self.state.gpu == "Unknown":
            self.log("[WARN] GPU не определён. AMD-опции могут не работать.", "warning")

        if self.sudo._sudo_cached():
            self.log("Сессия sudo активна", "success")
        else:
            self.log("Для применения нужен пароль sudo", "warning")

        self.root.after(500, self.refresh_services)

    # ─── Тема ──────────────────────────────────────────────────────────────────

    def _scaled(self, px):
        """Масштабирует пиксели под DPI экрана."""
        return int(px * self.dpi_scale)

    def apply_theme(self, theme_name=None):
        if theme_name:
            self.current_theme = theme_name
        t = THEMES[self.current_theme]

        self.root.configure(bg=t["bg"])

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", background=t["bg"], foreground=t["fg"])
        style.configure("TFrame", background=t["bg"])
        style.configure("TLabel", background=t["bg"], foreground=t["fg"])
        style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"])
        style.map("TCheckbutton", background=[("active", t["bg"])])

        style.configure("TNotebook", background=t["bg"], borderwidth=0)
        style.configure("TNotebook.Tab",
                         background=t["notebook_tab_bg"],
                         foreground=t["fg"],
                         padding=[self._scaled(12), self._scaled(5)])
        style.map("TNotebook.Tab",
                   background=[("selected", t["notebook_tab_selected"])],
                   foreground=[("selected", t["fg"])])

        style.configure("Treeview",
                         background=t["tree_bg"],
                         foreground=t["tree_fg"],
                         fieldbackground=t["tree_bg"],
                         rowheight=self._scaled(26))
        style.configure("Treeview.Heading",
                         background=t["tree_heading_bg"],
                         foreground=t["tree_heading_fg"])

        style.configure("TCombobox", fieldbackground=t["entry_bg"], foreground=t["entry_fg"])

        # КРИТИЧНО: делаем ползунок прокрутки видимым
        style.configure("Vertical.TScrollbar",
                         troughcolor=t["scrollbar_trough"],
                         background=t["scrollbar_slider"],
                         borderwidth=1,
                         relief="solid",
                         arrowsize=self._scaled(14))
        style.map("Vertical.TScrollbar",
                   background=[("active", t["gray"]), ("!active", t["scrollbar_slider"])])

        style.configure("Horizontal.TProgressbar",
                         troughcolor=t["scrollbar_trough"],
                         background=t["accent_bg"])

        # Обновляем tk-виджеты
        self._update_tk_widgets(t)

    def _update_tk_widgets(self, t):
        """Рекурсивно обновляет цвета обычных tk-виджетов."""
        def update_widget(w):
            try:
                cls = w.winfo_class()
                if cls in ("Frame", "Labelframe"):
                    w.configure(bg=t["bg"])
                elif cls == "Label":
                    w.configure(bg=t["bg"], fg=t["fg"])
                elif cls == "Checkbutton":
                    w.configure(bg=t["bg"], fg=t["fg"],
                                activebackground=t["bg"],
                                activeforeground=t["fg"],
                                selectcolor=t["select_color"])
                elif cls == "Button":
                    if w.cget("bg") == COLORS.get("_accent", ""):
                        w.configure(bg=t["accent_bg"], fg=t["accent_fg"])
                    else:
                        w.configure(bg=t["button_bg"], fg=t["button_fg"])
                elif cls == "Entry":
                    w.configure(bg=t["entry_bg"], fg=t["entry_fg"],
                                insertbackground=t["fg"])
                elif cls == "Text":
                    w.configure(bg=t["terminal_bg"], fg=t["terminal_fg"],
                                insertbackground=t["fg"])
                elif cls == "Canvas":
                    w.configure(bg=t["bg"], highlightthickness=0)
            except Exception:
                pass
            for child in w.winfo_children():
                update_widget(child)

        update_widget(self.root)

        # Перенастраиваем теги терминала
        if hasattr(self, "terminal"):
            self.terminal.tag_configure("normal", foreground=t["terminal_fg"])
            self.terminal.tag_configure("success", foreground=t["green"])
            self.terminal.tag_configure("error", foreground=t["red"])
            self.terminal.tag_configure("warning", foreground=t["yellow"])
            self.terminal.tag_configure("info", foreground=t["blue"])
            self.terminal.tag_configure("highlight", foreground=t["orange"])

    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme()
        self.theme_button.config(
            text="Тёмная тема" if self.current_theme == "light" else "Светлая тема"
        )

    # ─── Опции ─────────────────────────────────────────────────────────────────

    def _create_options(self):
        return {
            "rsyslog": {"label": "Отключить rsyslog", "desc": "Логирование в файлы", "category": "Логи", "var": tk.BooleanVar(value=False)},
            "journald": {"label": "Логи в ОЗУ (journald)", "desc": "Storage=volatile, 50M", "category": "Логи", "var": tk.BooleanVar(value=False)},
            "audit": {"label": "audit=0 (GRUB)", "desc": "Отключить аудит ядра", "category": "GRUB", "var": tk.BooleanVar(value=False)},
            "raid": {"label": "raid=noautodetect", "desc": "Ускорить загрузку", "category": "GRUB", "var": tk.BooleanVar(value=False)},
            "corectrl": {"label": "CoreCtrl (Polkit)", "desc": "Управление AMD GPU", "category": "AMD GPU", "var": tk.BooleanVar(value=False)},
            "ppfeaturemask": {"label": "amdgpu.ppfeaturemask", "desc": "Управление питанием GPU", "category": "AMD GPU", "var": tk.BooleanVar(value=False)},
            "vrr": {"label": "VRR/FreeSync", "desc": "Переменная частота обновления", "category": "AMD GPU", "var": tk.BooleanVar(value=False)},
            "radv": {"label": "RADV_PERFTEST=sam", "desc": "Resizable BAR для AMD", "category": "AMD GPU", "var": tk.BooleanVar(value=False)},
            "pipewire": {"label": "PipeWire (звук)", "desc": "Уменьшить треск звука", "category": "Звук", "var": tk.BooleanVar(value=False)},
            "mesa": {"label": "MESA_SHADER_CACHE=4G", "desc": "Кэш шейдеров 4 ГБ", "category": "Графика", "var": tk.BooleanVar(value=False)},
            "swap": {"label": "Тюнинг swap", "desc": "vm.swappiness", "category": "Память", "var": tk.BooleanVar(value=False)},
            "sysctl": {"label": "Тюнинг sysctl", "desc": "vfs_cache_pressure, numa", "category": "Ядро", "var": tk.BooleanVar(value=False)},
            "ntsync": {"label": "ntsync (модуль)", "desc": "Для Proton/Wine", "category": "Игры", "var": tk.BooleanVar(value=False)},
            "ntfs3": {"label": "ntfs3 драйвер", "desc": "Быстрый NTFS", "category": "Диски", "var": tk.BooleanVar(value=False)},
            "aliases": {"label": "Команды в .bashrc", "desc": "upd, upgr, update_all", "category": "Удобство", "var": tk.BooleanVar(value=False)},
            "autoupdate": {"label": "Автообновления", "desc": "systemd-таймер", "category": "Обновления", "var": tk.BooleanVar(value=False)},
        }

    # ─── UI ────────────────────────────────────────────────────────────────────

    def create_ui(self):
        self.root.title(f"System Tuneup v{APP_VERSION}")

        # Адаптивные размеры под DPI
        w = self._scaled(1000)
        h = self._scaled(780)
        min_w = self._scaled(800)
        min_h = self._scaled(580)

        self.root.geometry(f"{w}x{h}")
        self.root.minsize(min_w, min_h)

        # Применяем светлую тему по умолчанию
        self.apply_theme("light")

        # Header
        header = tk.Frame(self.root)
        header.pack(fill="x", padx=self._scaled(10), pady=(self._scaled(10), self._scaled(5)))

        tk.Label(header, text="System Tuneup", font=("Arial", self._scaled(16), "bold")).pack(side="left")
        tk.Label(header, text=f"v{APP_VERSION}", font=("Arial", self._scaled(9))).pack(side="left", padx=(self._scaled(10), 0))

        self.theme_button = tk.Button(
            header, text="Тёмная тема", command=self.toggle_theme,
            font=("Arial", self._scaled(9)), padx=self._scaled(8), pady=self._scaled(2),
        )
        self.theme_button.pack(side="right")

        self.dry_check = tk.Checkbutton(
            header, text="Сухой прогон", variable=self.dry_run_var,
            command=self.update_title, font=("Arial", self._scaled(9), "bold"),
        )
        self.dry_check.pack(side="right", padx=(0, self._scaled(10)))

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=self._scaled(10), pady=self._scaled(5))

        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=self._scaled(10), pady=self._scaled(5))

        self.tab_tuneup = ttk.Frame(self.notebook)
        self.tab_services = ttk.Frame(self.notebook)
        self.tab_status = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_tuneup, text=" Тюнинг ")
        self.notebook.add(self.tab_services, text=" Службы ")
        self.notebook.add(self.tab_status, text=" Статус ")

        self.create_tuning_tab()
        self.create_services_tab()
        self.create_status_tab()

        # Buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill="x", padx=self._scaled(10), pady=self._scaled(5))

        btn_padx = self._scaled(5)
        btn_pady = self._scaled(6)
        btn_font = ("Arial", self._scaled(10))
        btn_bold = ("Arial", self._scaled(10), "bold")

        self.run_button = tk.Button(
            btn_frame, text="Применить", command=self.apply_selected,
            font=btn_bold, padx=self._scaled(18), pady=btn_pady,
        )
        self.run_button.pack(side="left", padx=btn_padx)
        # Помечаем как акцентную кнопку для темы
        self.run_button._is_accent = True

        for text, cmd in [("Выбрать все", self.select_all), ("Сбросить", self.reset_all),
                          ("Экспорт", self.export_config)]:
            tk.Button(btn_frame, text=text, command=cmd, font=btn_font,
                      padx=self._scaled(10), pady=btn_pady).pack(side="left", padx=btn_padx)

        tk.Button(btn_frame, text="Помощь", command=self.show_help, font=btn_font,
                  padx=self._scaled(10), pady=btn_pady).pack(side="right", padx=btn_padx)

        # Terminal
        term_frame = tk.Frame(self.root)
        term_frame.pack(fill="both", expand=True, padx=self._scaled(10), pady=(self._scaled(5), 0))

        tk.Label(term_frame, text="Терминальный вывод:", font=("Arial", self._scaled(8))).pack(fill="x")

        self.terminal = scrolledtext.ScrolledText(
            term_frame, height=10,
            font=("DejaVu Sans Mono", self._scaled(9)),
            wrap="word", relief="sunken", bd=1, state="disabled",
        )
        self.terminal.pack(fill="both", expand=True, pady=(self._scaled(2), 0))

        # Status bar
        status_frame = tk.Frame(self.root)
        status_frame.pack(fill="x", padx=self._scaled(10), pady=(self._scaled(2), self._scaled(10)))

        self.status_text = tk.StringVar(value="Готово")
        tk.Label(status_frame, textvariable=self.status_text, font=("Arial", self._scaled(8))).pack(side="left")

        self.progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100,
                        length=self._scaled(180), mode="determinate").pack(side="right")

        # После создания всех виджетов применяем тему повторно для корректных цветов
        self.apply_theme()

    def create_tuning_tab(self):
        container = tk.Frame(self.tab_tuneup)
        container.pack(fill="both", expand=True, padx=self._scaled(8), pady=self._scaled(8))

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

        self.options_inner = tk.Frame(canvas)
        self.canvas_window = canvas.create_window((0, 0), window=self.options_inner, anchor="nw")

        self.options_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self.canvas_window, width=e.width))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        categories = {}
        for key, opt in self.options.items():
            categories.setdefault(opt["category"], []).append(key)

        fs_label = ("Arial", self._scaled(9), "bold")
        fs_cb = ("Arial", self._scaled(9))
        fs_desc = ("Arial", self._scaled(8))

        for cat in sorted(categories.keys()):
            tk.Label(self.options_inner, text=f"--- {cat} ---", font=fs_label, anchor="w").pack(fill="x", pady=(self._scaled(10), self._scaled(3)))

            for key in categories[cat]:
                opt = self.options[key]
                row = tk.Frame(self.options_inner)
                row.pack(fill="x", pady=self._scaled(1))

                top = tk.Frame(row)
                top.pack(fill="x")

                cb = tk.Checkbutton(top, text=opt["label"], variable=opt["var"], font=fs_cb, anchor="w")
                cb.pack(side="left")
                self.option_widgets[key] = cb

                if key == "corectrl":
                    tk.Label(top, text="Группа:", font=fs_desc).pack(side="left", padx=(self._scaled(12), self._scaled(2)))
                    tk.Entry(top, textvariable=self.corectrl_group, width=12, font=fs_desc).pack(side="left")
                elif key == "swap":
                    tk.Label(top, text="Значение:", font=fs_desc).pack(side="left", padx=(self._scaled(12), self._scaled(2)))
                    tk.Entry(top, textvariable=self.swap_value, width=5, font=fs_desc).pack(side="left")
                elif key == "autoupdate":
                    tk.Label(top, text="Расписание:", font=fs_desc).pack(side="left", padx=(self._scaled(12), self._scaled(2)))
                    ttk.Combobox(top, textvariable=self.update_schedule,
                                 values=("Отключено", "Ежедневно", "Еженедельно (суббота)", "2 раза в месяц", "Ежемесячно"),
                                 state="readonly", width=24, font=fs_desc).pack(side="left")

                tk.Label(row, text=opt["desc"], font=fs_desc, anchor="w").pack(fill="x", padx=(self._scaled(26), 0))

    def create_services_tab(self):
        container = tk.Frame(self.tab_services)
        container.pack(fill="both", expand=True, padx=self._scaled(8), pady=self._scaled(8))

        btns = tk.Frame(container)
        btns.pack(fill="x", pady=(0, self._scaled(8)))

        btn_font = ("Arial", self._scaled(8))
        btn_pad = self._scaled(8)

        tk.Button(btns, text="Обновить", command=self.refresh_services, font=btn_font, padx=btn_pad, pady=self._scaled(4)).pack(side="left", padx=2)
        tk.Button(btns, text="Откл. рекомендуемые", command=self.disable_recommended, font=btn_font, padx=btn_pad, pady=self._scaled(4)).pack(side="left", padx=2)
        tk.Button(btns, text="Вкл. выбранные", command=self.enable_selected, font=btn_font, padx=btn_pad, pady=self._scaled(4)).pack(side="left", padx=2)
        tk.Button(btns, text="Откл. выбранные", command=self.disable_selected, font=btn_font, padx=btn_pad, pady=self._scaled(4)).pack(side="left", padx=2)

        tree_frame = tk.Frame(container)
        tree_frame.pack(fill="both", expand=True)

        self.services_tree = ttk.Treeview(
            tree_frame, columns=("name", "enabled", "active", "desc"),
            show="headings", selectmode="extended",
        )
        self.services_tree.heading("name", text="Служба")
        self.services_tree.heading("enabled", text="Enabled")
        self.services_tree.heading("active", text="Active")
        self.services_tree.heading("desc", text="Описание")

        self.services_tree.column("name", width=self._scaled(240), anchor="w")
        self.services_tree.column("enabled", width=self._scaled(100), anchor="center")
        self.services_tree.column("active", width=self._scaled(90), anchor="center")
        self.services_tree.column("desc", width=self._scaled(380), anchor="w")

        # Теги для цветовой индикации БЕЗ эмодзи
        self.services_tree.tag_configure("enabled_active", foreground="#2e7d32")
        self.services_tree.tag_configure("enabled_inactive", foreground="#f57f17")
        self.services_tree.tag_configure("disabled", foreground="#757575")
        self.services_tree.tag_configure("masked", foreground="#c62828")
        self.services_tree.tag_configure("not_found", foreground="#bdbdbd")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.services_tree.yview)
        self.services_tree.configure(yscrollcommand=scrollbar.set)
        self.services_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.services_count_label = tk.Label(container, text="Служб: 0", font=("Arial", self._scaled(8)))
        self.services_count_label.pack(fill="x", pady=(self._scaled(6), 0))

    def create_status_tab(self):
        container = tk.Frame(self.tab_status)
        container.pack(fill="both", expand=True, padx=self._scaled(8), pady=self._scaled(8))

        tk.Button(container, text="Обновить статус", command=self.refresh_status,
                  font=("Arial", self._scaled(9)), padx=self._scaled(12), pady=self._scaled(5)).pack(anchor="w", pady=(0, self._scaled(8)))

        self.status_text_widget = scrolledtext.ScrolledText(
            container, font=("DejaVu Sans Mono", self._scaled(9)), state="disabled",
        )
        self.status_text_widget.pack(fill="both", expand=True)

    # ─── Queue ─────────────────────────────────────────────────────────────────

    def log(self, msg, tag="normal"):
        if not msg.endswith("\n"):
            msg += "\n"
        self.q.put(("log", msg, tag))

    def process_queue(self):
        try:
            while True:
                item = self.q.get_nowait()
                kind = item[0]
                if kind == "log":
                    self.terminal.configure(state="normal")
                    self.terminal.insert(tk.END, item[1], item[2])
                    self.terminal.see(tk.END)
                    self.terminal.configure(state="disabled")
                elif kind == "statusbar":
                    self.status_text.set(item[1])
                elif kind == "progress":
                    self.progress_var.set(item[1])
                elif kind == "running":
                    self.is_running = item[1]
                    self.run_button.config(state="disabled" if item[1] else "normal")
                elif kind == "services_rows":
                    for child in self.services_tree.get_children():
                        self.services_tree.delete(child)
                    for row in item[1]:
                        name, enabled, active, desc = row
                        # Определяем тег для цветовой индикации
                        if enabled == "masked":
                            tag = "masked"
                            enabled_display = "[MASKED]"
                        elif enabled == "disabled":
                            tag = "disabled"
                            enabled_display = "[OFF]"
                        elif enabled == "not-found":
                            tag = "not_found"
                            enabled_display = "[N/A]"
                        elif active == "active":
                            tag = "enabled_active"
                            enabled_display = "[ON]"
                        else:
                            tag = "enabled_inactive"
                            enabled_display = "[ON/off]"

                        active_display = "[RUNNING]" if active == "active" else "[STOPPED]" if active == "inactive" else f"[{active}]"

                        self.services_tree.insert("", "end", values=(name, enabled_display, active_display, desc), tags=(tag,))
                    self.services_count_label.config(text=f"Служб: {len(item[1])}")
                elif kind == "status_text":
                    self.status_text_widget.configure(state="normal")
                    self.status_text_widget.delete("1.0", tk.END)
                    self.status_text_widget.insert(tk.END, item[1])
                    self.status_text_widget.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    # ─── Apply ─────────────────────────────────────────────────────────────────

    def apply_selected(self):
        if self.is_running:
            messagebox.showinfo("Выполняется", "Дождитесь завершения.")
            return
        selected = [k for k, o in self.options.items() if o["var"].get()]
        if not selected:
            messagebox.showwarning("Нет опций", "Отметьте хотя бы одну опцию.")
            return
        params = {
            "corectrl_group": self.corectrl_group.get(),
            "swap_value": self.swap_value.get(),
            "update_schedule": self.update_schedule.get(),
        }
        dry_run = self.dry_run_var.get()
        if not dry_run and not self.sudo.ensure():
            self.log("Не удалось получить sudo", "error")
            return

        self.is_running = True
        self.run_button.config(state="disabled")
        self.q.put(("running", True))
        self.q.put(("progress", 0))
        self.q.put(("statusbar", "Выполнение..."))

        threading.Thread(target=self._apply_worker, args=(selected, params, dry_run), daemon=True).start()

    def _apply_worker(self, selected, params, dry_run):
        try:
            ops = SystemOps(self.sudo, self.state, self.log, dry_run)
            total = len(selected)
            done = 0
            self.log("=" * 50, "highlight")
            self.log("ЗАПУСК ТЮНИНГА", "highlight")
            self.log(f"Режим: {'СУХОЙ ПРОГОН' if dry_run else 'ОБЫЧНЫЙ'}", "info")
            self.log(f"Опций: {total}", "info")
            self.log("=" * 50, "highlight")
            for key in selected:
                self.log(f"-> {self.options[key]['label']}", "info")
                try:
                    getattr(ops, f"apply_{key}")(params)
                except Exception as e:
                    self.log(f"Ошибка: {e}", "error")
                done += 1
                self.q.put(("progress", int(done / total * 90)))
            if not dry_run:
                ops.finalize_grub()
            self.q.put(("progress", 100))
            self.q.put(("statusbar", "Готово"))
            self.log("Завершено", "success")
        except Exception as e:
            self.log(f"Критическая ошибка: {e}", "error")
            self.q.put(("statusbar", "Ошибка"))
        finally:
            self.q.put(("running", False))

    # ─── Helpers ───────────────────────────────────────────────────────────────

    def select_all(self):
        for k, o in self.options.items():
            w = self.option_widgets.get(k)
            if w and str(w.cget("state")) == "normal":
                o["var"].set(True)

    def reset_all(self):
        for o in self.options.values():
            o["var"].set(False)

    def disable_option(self, key):
        w = self.option_widgets.get(key)
        if w:
            w.config(state="disabled")
        self.options[key]["var"].set(False)

    def apply_hardware_restrictions(self):
        if self.state.gpu not in ("AMD", "Unknown"):
            for k in ("corectrl", "ppfeaturemask", "vrr", "radv"):
                self.disable_option(k)
        if self.state.has_raid:
            self.disable_option("raid")
        if not self.state.has_swap:
            self.disable_option("swap")
        if not os.path.exists("/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"):
            self.disable_option("ntfs3")
        self.swap_value.set("150" if self.state.swap_type == "zram" else "10")

    def update_title(self):
        title = f"System Tuneup v{APP_VERSION}"
        if self.dry_run_var.get():
            title += " [СУХОЙ ПРОГОН]"
        self.root.title(title)

    def export_config(self):
        selected = [f"{k}: {self.options[k]['label']}" for k, o in self.options.items() if o["var"].get()]
        if not selected:
            messagebox.showinfo("Экспорт", "Нет выбранных опций.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", initialdir=os.path.expanduser("~"),
                                            filetypes=[("Text files", "*.txt")], title="Сохранить")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"System Tuneup v{APP_VERSION}\n")
                f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Dry run: {self.dry_run_var.get()}\n\n")
                f.write("\n".join(selected) + "\n")
            self.log(f"Сохранено: {path}", "success")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def show_help(self):
        """Открывает справку в отдельном окне нормального размера."""
        win = tk.Toplevel(self.root)
        win.title(f"Справка — System Tuneup v{APP_VERSION}")
        win.geometry(f"{self._scaled(650)}x{self._scaled(500)}")
        win.minsize(self._scaled(500), self._scaled(400))
        win.transient(self.root)

        t = THEMES[self.current_theme]
        win.configure(bg=t["bg"])

        text = scrolledtext.ScrolledText(
            win, font=("DejaVu Sans Mono", self._scaled(9)),
            bg=t["terminal_bg"], fg=t["terminal_fg"],
            wrap="word", relief="flat", padx=self._scaled(10), pady=self._scaled(10),
        )
        text.pack(fill="both", expand=True)

        help_text = f"""System Tuneup GUI v{APP_VERSION}

ГРАФИЧЕСКАЯ ОБОЛОЧКА ДЛЯ ТЮНИНГА LINUX MINT / UBUNTU / DEBIAN

=== КАК ПОЛЬЗОВАТЬСЯ ===

1. Вкладка "Тюнинг" — отметьте нужные опции
2. Заполните параметры (группа CoreCtrl, swappiness, расписание)
3. Нажмите "Применить"
4. Введите пароль sudo при запросе

=== СУХОЙ ПРОГОН ===

Включите галочку "Сухой прогон" или запустите с --dry-run.
Изменения не применяются, но в логе видно что было бы сделано.

=== ВКЛАДКА "СЛУЖБЫ" ===

[ON]      — служба включена и работает
[ON/off]  — служба включена, но не работает
[OFF]     — служба отключена
[MASKED]  — служба замаскирована (полностью заблокирована)
[N/A]     — служба не найдена в системе

Кнопки:
  "Откл. рекомендуемые" — отключает ненужные службы одним кликом
  "Вкл./Откл. выбранные" — работа с выделенными строками

=== ВКЛАДКА "СТАТУС" ===

Показывает текущее состояние системы: GPU, swap, RAID,
параметры ядра, GRUB, конфиги, таймеры.

=== БЭКАПЫ ===

Перед каждым изменением файла создаётся бэкап.
Хранится до 5 последних копий.
Расположение: ~/.local/share/system-tuneup/backups/

=== ГОРЯЧИЕ КЛАВИШИ ===

Нет (используйте кнопки интерфейса).

=== ТРЕБОВАНИЯ ===

- Python 3.8+
- Tkinter
- systemd
- sudo
"""
        text.insert("1.0", help_text)
        text.configure(state="disabled")

    # ─── Services ──────────────────────────────────────────────────────────────

    def refresh_services(self):
        dry_run = self.dry_run_var.get()
        threading.Thread(target=self._refresh_services_worker, args=(dry_run,), daemon=True).start()

    def _refresh_services_worker(self, dry_run):
        try:
            ops = SystemOps(self.sudo, self.state, lambda m, t="normal": None, dry_run)
            rows = []
            for svc in SERVICES:
                name, desc = svc["name"], svc["desc"]
                if not ops.unit_exists(name):
                    rows.append((name, "not-found", "not-found", desc))
                else:
                    rows.append((name, ops.service_enabled(name), ops.service_active(name), desc))
            self.q.put(("services_rows", rows))
        except Exception as e:
            self.q.put(("log", f"Ошибка обновления служб: {e}", "error"))

    def _ensure_service_action(self):
        if self.dry_run_var.get():
            return True
        return self.sudo.ensure()

    def disable_recommended(self):
        if not self._ensure_service_action():
            return
        threading.Thread(target=self._disable_recommended_worker, args=(self.dry_run_var.get(),), daemon=True).start()

    def _disable_recommended_worker(self, dry_run):
        try:
            ops = SystemOps(self.sudo, self.state, self.log, dry_run)
            self.log("Отключение рекомендуемых служб...", "info")
            for svc in SERVICES:
                name = svc["name"]
                if not ops.unit_exists(name):
                    continue
                enabled = ops.service_enabled(name)
                if enabled in ("disabled", "masked"):
                    continue
                if ops.dry_run:
                    ops.log(f"[DRY RUN] disable {name}", "warning")
                    continue
                ops.sudo_run(["systemctl", "disable", "--now", name], ignore_error=True)
                if name.startswith("avahi"):
                    ops.sudo_run(["systemctl", "mask", name], ignore_error=True)
                ops.log(f"[OK] {name} отключена", "success")
            self.log("Готово", "success")
            self.refresh_services()
        except Exception as e:
            self.q.put(("log", f"Ошибка: {e}", "error"))

    def enable_selected(self):
        items = self.services_tree.selection()
        if not items:
            messagebox.showinfo("Службы", "Выберите службы.")
            return
        names = [str(self.services_tree.item(i)["values"][0]) for i in items]
        if not self._ensure_service_action():
            return
        threading.Thread(target=self._enable_worker, args=(names, self.dry_run_var.get()), daemon=True).start()

    def _enable_worker(self, names, dry_run):
        try:
            ops = SystemOps(self.sudo, self.state, self.log, dry_run)
            for name in names:
                if ops.dry_run:
                    ops.log(f"[DRY RUN] enable {name}", "warning")
                    continue
                ops.sudo_run(["systemctl", "unmask", name], ignore_error=True)
                ops.sudo_run(["systemctl", "enable", name], ok_msg=f"[OK] {name} включена", ignore_error=True)
            self.refresh_services()
        except Exception as e:
            self.q.put(("log", f"Ошибка: {e}", "error"))

    def disable_selected(self):
        items = self.services_tree.selection()
        if not items:
            messagebox.showinfo("Службы", "Выберите службы.")
            return
        names = [str(self.services_tree.item(i)["values"][0]) for i in items]
        if not self._ensure_service_action():
            return
        threading.Thread(target=self._disable_worker, args=(names, self.dry_run_var.get()), daemon=True).start()

    def _disable_worker(self, names, dry_run):
        try:
            ops = SystemOps(self.sudo, self.state, self.log, dry_run)
            for name in names:
                if ops.dry_run:
                    ops.log(f"[DRY RUN] disable {name}", "warning")
                    continue
                ops.sudo_run(["systemctl", "disable", "--now", name], ignore_error=True)
                if name.startswith("avahi"):
                    ops.sudo_run(["systemctl", "mask", name], ignore_error=True)
                ops.log(f"[OK] {name} отключена", "success")
            self.refresh_services()
        except Exception as e:
            self.q.put(("log", f"Ошибка: {e}", "error"))

    # ─── Status ────────────────────────────────────────────────────────────────

    def refresh_status(self):
        threading.Thread(target=self._refresh_status_worker, daemon=True).start()

    def _refresh_status_worker(self):
        try:
            ops = SystemOps(self.sudo, self.state, lambda m, t="normal": None, True)
            lines = []
            lines.append("=== HARDWARE ===")
            lines.append(f"GPU: {self.state.gpu}")
            lines.append(f"RAID: {'yes' if self.state.has_raid else 'no'}")
            lines.append(f"Swap: {self.state.swap_type if self.state.has_swap else 'none'}")
            lines.append(f"ntsync: {'yes' if self.state.ntsync else 'no'}")
            lines.append(f"Cinnamon: {'yes' if self.state.cinnamon else 'no'}")
            lines.append(f"flatpak: {'yes' if self.state.has_flatpak else 'no'}")
            lines.append(f"User: {self.state.user_name}")
            lines.append("")
            lines.append("=== SERVICES ===")
            for svc in SERVICES:
                n = svc["name"]
                lines.append(f"  {n}: enabled={ops.service_enabled(n)}, active={ops.service_active(n)}")
            lines.append("")
            lines.append("=== KERNEL ===")
            for p in ("vm.swappiness", "vm.vfs_cache_pressure", "kernel.numa_balancing"):
                try:
                    r = subprocess.run(["sysctl", "-n", p], capture_output=True, text=True, timeout=3)
                    lines.append(f"  {p} = {r.stdout.strip() if r.returncode == 0 else 'n/a'}")
                except Exception:
                    lines.append(f"  {p} = n/a")
            lines.append("")
            lines.append("=== GRUB ===")
            grub = ops.read_file("/etc/default/grub") or ""
            for p in ("audit=0", "raid=noautodetect", "amdgpu.ppfeaturemask"):
                lines.append(f"  {p}: {'present' if p in grub else 'absent'}")
            lines.append("")
            lines.append("=== CONFIGS ===")
            j = ops.read_file("/etc/systemd/journald.conf") or ""
            is_volatile = "yes" if re.search(r"^\s*Storage\s*=\s*volatile\s*$", j, re.M) else "no"
            lines.append(f"  journald volatile: {is_volatile}")
            env = ops.read_file("/etc/environment") or ""
            lines.append(f"  MESA_SHADER_CACHE=4G: {'yes' if 'MESA_SHADER_CACHE_MAX_SIZE=4G' in env else 'no'}")
            lines.append(f"  RADV_PERFTEST=sam: {'yes' if 'RADV_PERFTEST=sam' in env else 'no'}")
            lines.append(f"  CoreCtrl: {'yes' if ops.path_exists('/etc/polkit-1/rules.d/90-corectrl.rules') else 'no'}")
            lines.append(f"  VRR: {'yes' if ops.path_exists('/etc/X11/xorg.conf.d/20-amdgpu.conf') else 'no'}")
            pp = os.path.join(self.state.user_home, ".config/pipewire/pipewire.conf.d/10-sound.conf")
            lines.append(f"  PipeWire: {'yes' if ops.path_exists(pp) else 'no'}")
            br = ops.read_file(os.path.join(self.state.user_home, ".bashrc")) or ""
            lines.append(f"  Aliases: {'yes' if 'system-tuneup' in br else 'no'}")
            lines.append(f"  Auto-update timer: {ops.service_enabled('biweekly-upgrade.timer')}")
            self.q.put(("status_text", "\n".join(lines)))
        except Exception as e:
            self.q.put(("log", f"Ошибка статуса: {e}", "error"))

    # ─── Closing ───────────────────────────────────────────────────────────────

    def on_closing(self):
        if self.is_running:
            if not messagebox.askyesno("Выполняется", "Прервать выполнение?"):
                return
        self.root.destroy()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(f"System Tuneup GUI v{APP_VERSION}\n\n  python3 tuneup_gui.py [--dry-run] [--help]")
        sys.exit(0)

    root = tk.Tk()

    # Включаем DPI-awareness на Windows (если запущено через WSL/Xming)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = TuneupApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
