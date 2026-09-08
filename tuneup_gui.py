#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
  SYSTEM TUNEUP GUI v2.1.0
  Графическая оболочка для тюнинга Linux Mint / Ubuntu / Debian
═══════════════════════════════════════════════════════════════════════════════

  Особенности:
    - Не вызывает внешний bash-скрипт.
    - Вся логика применения настроек реализована на Python.
    - Безопасная многопоточность для Tkinter через queue + root.after().
    - sudo кэшируется через `sudo -S -v`, пароль не передаётся в каждую команду.
    - Есть вкладки: Тюнинг, Службы, Статус.
    - Есть режим сухого прогона.

  Запуск:
    python3 tuneup_gui.py
    python3 tuneup_gui.py --dry-run

  Требования:
    - Python 3.8+
    - Tkinter
    - systemd
    - sudo

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


# ─── ЦВЕТА ────────────────────────────────────────────────────────────────────

COLORS = {
    "bg": "#1e1e1e",
    "fg": "#d4d4d4",
    "green": "#4ec9b0",
    "yellow": "#d7ba7d",
    "red": "#f44747",
    "blue": "#569cd6",
    "orange": "#ce9178",
    "gray": "#808080",
    "terminal": "#0c0c0c",
    "entry": "#333333",
}


# ─── РЕКОМЕНДУЕМЫЕ СЛУЖБЫ ────────────────────────────────────────────────────

SERVICES = [
    {
        "name": "avahi-daemon.service",
        "desc": "Сетевое обнаружение устройств (принтеры, ТВ)",
    },
    {
        "name": "avahi-daemon.socket",
        "desc": "Сокет-активатор Avahi",
    },
    {
        "name": "cups-browsed.service",
        "desc": "Автоматический поиск сетевых принтеров",
    },
    {
        "name": "ModemManager.service",
        "desc": "Управление USB-модемами",
    },
    {
        "name": "openvpn.service",
        "desc": "Встроенный VPN-сервер",
    },
    {
        "name": "lvm2-monitor.service",
        "desc": "Мониторинг LVM-томов",
    },
    {
        "name": "switcheroo-control.service",
        "desc": "Переключение видеокарт на ноутбуках",
    },
    {
        "name": "touchegg.service",
        "desc": "Жесты тачпада",
    },
    {
        "name": "zfs-zed.service",
        "desc": "Мониторинг ZFS",
    },
    {
        "name": "kerneloops.service",
        "desc": "Отчёты об ошибках ядра",
    },
]


# ─── УТИЛИТЫ ─────────────────────────────────────────────────────────────────

def decode_bytes(value):
    """Безопасно декодирует bytes в str."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


# ─── SUDO MANAGER ────────────────────────────────────────────────────────────

class SudoManager:
    """
    Менеджер прав sudo.

    Логика:
      - Один раз запрашиваем пароль через `sudo -S -v`.
      - Далее используем `sudo -n команда` без повторной передачи пароля.
      - Фоновый поток периодически обновляет кэш sudo командой `sudo -n -v`.

    Важно:
      - Диалоги ввода пароля должны вызываться только из главного потока.
      - В фоновых потоках используем только `sudo -n`.
    """

    def __init__(self):
        self.parent = None
        self.authenticated = False
        self._keepalive_running = False

    def set_parent(self, parent):
        self.parent = parent

    def _sudo_cached(self):
        """Проверяет, есть ли уже активный кэш sudo."""
        try:
            res = subprocess.run(
                ["sudo", "-n", "true"],
                capture_output=True,
                timeout=3,
            )
            return res.returncode == 0
        except Exception:
            return False

    def authenticate(self):
        """
        Запрашивает пароль sudo и кэширует права через `sudo -S -v`.
        Вызывать только из главного потока.
        """
        if self._sudo_cached():
            self.authenticated = True
            self._start_keepalive()
            return True

        for attempt in range(1, 4):
            password = simpledialog.askstring(
                "Авторизация",
                f"Введите пароль sudo (попытка {attempt} из 3):",
                parent=self.parent,
                show="•",
            )

            if password is None:
                return False

            if not password:
                messagebox.showwarning(
                    "Пароль",
                    "Пароль не может быть пустым.",
                    parent=self.parent,
                )
                continue

            try:
                res = subprocess.run(
                    ["sudo", "-S", "-v"],
                    input=(password + "\n").encode(),
                    capture_output=True,
                    timeout=15,
                )

                if res.returncode == 0:
                    self.authenticated = True
                    self._start_keepalive()
                    return True

                messagebox.showerror(
                    "Ошибка sudo",
                    "Неверный пароль или пользователю не разрешён sudo.",
                    parent=self.parent,
                )

            except Exception as e:
                messagebox.showerror(
                    "Ошибка sudo",
                    f"Не удалось выполнить sudo:\n{e}",
                    parent=self.parent,
                )

        return False

    def ensure(self):
        """
        Гарантирует, что есть права sudo.
        Вызывать из главного потока перед запуском фоновых работ.
        """
        if self._sudo_cached():
            self.authenticated = True
            self._start_keepalive()
            return True

        return self.authenticate()

    def run(self, args, input=None):
        """
        Выполняет команду через `sudo -n`.

        Если кэш sudo истёк, бросает PermissionError.
        Не показывает диалоги из фоновых потоков.
        """
        if not self._sudo_cached():
            raise PermissionError(
                "Сессия sudo истекла или не была получена. "
                "Нажмите Применить заново."
            )

        return subprocess.run(
            ["sudo", "-n"] + list(args),
            input=input,
            capture_output=True,
            timeout=180,
        )

    def _start_keepalive(self):
        """
        Фоновое обновление кэша sudo.
        Не даёт кэшу истечь во время длительного применения настроек.
        """
        if self._keepalive_running:
            return

        self._keepalive_running = True

        def loop():
            while True:
                time.sleep(50)

                try:
                    if not self._sudo_cached():
                        break

                    subprocess.run(
                        ["sudo", "-n", "-v"],
                        capture_output=True,
                        timeout=5,
                    )

                except Exception:
                    pass

            self._keepalive_running = False
            self.authenticated = False

        threading.Thread(target=loop, daemon=True).start()


# ─── СОСТОЯНИЕ СИСТЕМЫ ───────────────────────────────────────────────────────

class SystemState:
    """Определяет GPU, swap, RAID, ntsync, Cinnamon и домашнего пользователя."""

    def __init__(self):
        self.gpu = "Unknown"
        self.has_raid = False
        self.has_swap = False
        self.swap_type = ""
        self.ntsync = False
        self.cinnamon = False
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

        # GPU
        try:
            res = subprocess.run(
                ["lspci"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in res.stdout.lower().splitlines():
                if "vga" in line or "3d controller" in line or "display controller" in line:
                    if "amd" in line or "radeon" in line:
                        self.gpu = "AMD"
                        break
                    elif "nvidia" in line:
                        self.gpu = "NVIDIA"
                        break
                    elif "intel" in line:
                        self.gpu = "Intel"
                        break

        except Exception:
            pass

        # RAID: /proc/mdstat
        try:
            if os.path.isfile("/proc/mdstat"):
                with open("/proc/mdstat", "r", encoding="utf-8", errors="replace") as f:
                    if re.search(r"^md\d+", f.read(), re.M):
                        self.has_raid = True
        except Exception:
            pass

        # RAID: lsblk
        try:
            res = subprocess.run(
                ["lsblk", "-n", "-o", "TYPE"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "raid" in res.stdout:
                self.has_raid = True
        except Exception:
            pass

        # Swap
        try:
            res = subprocess.run(
                ["swapon", "--show=TYPE", "--noheadings"],
                capture_output=True,
                text=True,
                timeout=5,
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

        # ntsync
        self.ntsync = os.path.exists("/dev/ntsync")

        # Cinnamon
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session = os.environ.get("DESKTOP_SESSION", "").lower()

        if "cinnamon" in desktop or session == "cinnamon":
            self.cinnamon = True
        else:
            try:
                res = subprocess.run(
                    ["pgrep", "-x", "cinnamon"],
                    capture_output=True,
                    timeout=3,
                )
                self.cinnamon = res.returncode == 0
            except Exception:
                pass

    def _get_real_user(self):
        """
        Возвращает реального пользователя, даже если программа запущена
        через sudo / pkexec.
        """
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

        # Если программа запущена как root и нет SUDO_USER,
        # ищем первого обычного пользователя с UID >= 1000.
        try:
            for pw in pwd.getpwall():
                if pw.pw_uid >= 1000 and pw.pw_name not in ("nobody", "nfsnobody"):
                    return pw.pw_name
        except Exception:
            pass

        return "root"


# ─── ОПЕРАЦИИ СИСТЕМЫ ────────────────────────────────────────────────────────

class SystemOps:
    """
    Основной класс применения настроек.

    Все операции выполняются здесь, а не во внешнем bash-скрипте.
    """

    def __init__(self, sudo, state, log, dry_run):
        self.sudo = sudo
        self.state = state
        self.log = log
        self.dry_run = dry_run
        self.grub_changed = False

    # ─── Базовые команды ─────────────────────────────────────────────────────

    def sudo_run(self, args, input=None, ok_msg=None, err_msg=None, ignore_error=False):
        """Выполняет команду через sudo."""
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

        if not ignore_error:
            err = decode_bytes(res.stderr).strip()
            msg = err_msg or f"Команда завершилась с ошибкой: {' '.join(args)}"
            if err:
                self.log(f"❌ {msg}\n   {err}", "error")
            else:
                self.log(f"❌ {msg}", "error")

        return False

    def path_exists(self, path):
        """Проверяет существование файла."""
        if os.path.exists(path):
            return True

        try:
            res = subprocess.run(
                ["sudo", "-n", "test", "-e", path],
                capture_output=True,
                timeout=3,
            )
            return res.returncode == 0
        except Exception:
            return False

    def read_file(self, path):
        """
        Читает файл.
        Возвращает:
          ''     - если файла нет;
          None   - если файл существует, но прочитать не удалось;
          строку - если удалось прочитать.
        """
        if not self.path_exists(path):
            return ""

        try:
            res = subprocess.run(
                ["sudo", "-n", "cat", path],
                capture_output=True,
                timeout=5,
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

    def write_file(self, path, content, chmod="644", owner=None, mkdir=False):
        """Записывает файл через sudo tee."""
        if self.dry_run:
            self.log(f"[DRY RUN] Запись файла: {path}", "warning")
            return True

        if mkdir:
            d = os.path.dirname(path)
            if d:
                self.sudo_run(["mkdir", "-p", d], ignore_error=True)

        try:
            res = self.sudo.run(["tee", path], input=content.encode())
        except PermissionError as e:
            self.log(str(e), "error")
            return False
        except Exception as e:
            self.log(f"Ошибка записи {path}: {e}", "error")
            return False

        if res.returncode != 0:
            self.log(
                f"Не удалось записать {path}:\n{decode_bytes(res.stderr)}",
                "error",
            )
            return False

        if chmod:
            self.sudo_run(["chmod", chmod, path], ignore_error=True)

        if owner:
            self.sudo_run(["chown", owner, path], ignore_error=True)

        return True

    def ensure_line(self, path, line, pattern, chmod="644", owner=None, mkdir=False):
        """
        Гарантирует, что строка есть в файле.
        Если есть похожие строки по шаблону — заменяет их одной правильной.
        """
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

        return self.write_file(
            path,
            "\n".join(new_lines) + "\n",
            chmod=chmod,
            owner=owner,
            mkdir=mkdir,
        )

    # ─── systemd helpers ─────────────────────────────────────────────────────

    def unit_exists(self, name):
        """
        Проверяет наличие unit в systemctl list-unit-files.
        Использует точное сравнение, а не подстроку.
        """
        try:
            res = subprocess.run(
                [
                    "systemctl",
                    "list-unit-files",
                    name,
                    "--no-legend",
                    "--no-pager",
                ],
                capture_output=True,
                timeout=5,
            )

            for line in decode_bytes(res.stdout).splitlines():
                parts = line.split()

                if parts and parts[0] == name:
                    return True

            return False

        except Exception:
            return False

    def service_enabled(self, name):
        """Возвращает вывод systemctl is-enabled."""
        if not self.unit_exists(name):
            return "not-found"

        try:
            res = subprocess.run(
                ["systemctl", "is-enabled", name],
                capture_output=True,
                timeout=5,
            )
            out = decode_bytes(res.stdout).strip()
            return out or "unknown"
        except Exception:
            return "unknown"

    def service_active(self, name):
        """Возвращает вывод systemctl is-active."""
        try:
            res = subprocess.run(
                ["systemctl", "is-active", name],
                capture_output=True,
                timeout=5,
            )
            out = decode_bytes(res.stdout).strip()
            return out or "unknown"
        except Exception:
            return "unknown"

    def _has_cinnamon_spices(self):
        """Проверяет наличие cinnamon-spice-updater."""
        if not self.state.cinnamon:
            return False

        if shutil.which("cinnamon-spice-updater"):
            return True

        return os.path.exists("/usr/bin/cinnamon-spice-updater")

    # ─── GRUB ────────────────────────────────────────────────────────────────

    def add_grub_params(self, params):
        """Добавляет параметры в GRUB_CMDLINE_LINUX_DEFAULT."""
        if self.dry_run:
            self.log("[DRY RUN] GRUB добавить: " + " ".join(params), "warning")
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
                    new_val = " ".join(parts)
                    new_lines.append(f'GRUB_CMDLINE_LINUX_DEFAULT="{new_val}"')
                    changed = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(
                'GRUB_CMDLINE_LINUX_DEFAULT="' + " ".join(params) + '"'
            )
            changed = True

        if not changed:
            self.log("GRUB уже содержит нужные параметры", "info")
            return True

        if self.write_file(path, "\n".join(new_lines) + "\n"):
            self.grub_changed = True
            self.log("GRUB: параметры добавлены", "success")
            return True

        return False

    def finalize_grub(self):
        """Вызывает update-grub, если GRUB был изменён."""
        if not self.grub_changed:
            return

        if self.dry_run:
            self.log("[DRY RUN] update-grub", "warning")
            return

        if shutil.which("update-grub"):
            self.sudo_run(
                ["update-grub"],
                ok_msg="GRUB обновлён",
                err_msg="Ошибка update-grub",
            )
        elif shutil.which("grub-mkconfig"):
            self.sudo_run(
                ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"],
                ok_msg="GRUB обновлён",
                err_msg="Ошибка grub-mkconfig",
            )
        else:
            self.log("Не найдена команда update-grub или grub-mkconfig", "warning")

        self.grub_changed = False

    # ─── Опции тюнинга ───────────────────────────────────────────────────────

    def apply_rsyslog(self, params=None):
        if self.dry_run:
            self.log(
                "[DRY RUN] systemctl disable rsyslog && systemctl mask rsyslog",
                "warning",
            )
            return True

        enabled = self.service_enabled("rsyslog.service")

        if enabled in ("disabled", "masked", "not-found"):
            self.log("rsyslog уже отключён", "info")
            return True

        ok1 = self.sudo_run(["systemctl", "disable", "rsyslog"], ignore_error=True)
        ok2 = self.sudo_run(["systemctl", "mask", "rsyslog"], ignore_error=True)

        if ok1 or ok2:
            self.log("✓ rsyslog отключён", "success")
            return True

        self.log("Не удалось отключить rsyslog", "error")
        return False

    def apply_journald(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] journald → volatile, RuntimeMaxUse=50M", "warning")
            return True

        path = "/etc/systemd/journald.conf"
        content = self.read_file(path)

        if content is None:
            self.log(f"Не удалось прочитать {path}", "error")
            return False

        if (
            re.search(r"^\s*Storage\s*=\s*volatile\s*$", content, re.M)
            and re.search(r"^\s*RuntimeMaxUse\s*=\s*50M\s*$", content, re.M)
        ):
            self.log("journald уже настроен", "info")
            return True

        lines = content.splitlines()
        new_lines = []

        for line in lines:
            if re.match(r"^\s*Storage\s*=", line) or re.match(r"^\s*RuntimeMaxUse\s*=", line):
                if not line.lstrip().startswith("#"):
                    new_lines.append("# " + line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        new_lines.append("Storage=volatile")
        new_lines.append("RuntimeMaxUse=50M")

        if not self.write_file(path, "\n".join(new_lines) + "\n"):
            return False

        self.sudo_run(
            ["systemctl", "restart", "systemd-journald"],
            ok_msg="systemd-journald перезапущен",
            ignore_error=True,
        )

        self.sudo_run(
            ["journalctl", "--vacuum-size=200M", "--vacuum-time=1months"],
            ignore_error=True,
        )

        self.log("✓ journald → volatile (50M)", "success")
        return True

    def apply_audit(self, params=None):
        return self.add_grub_params(["audit=0"])

    def apply_raid(self, params=None):
        if self.state.has_raid:
            self.log("Обнаружен RAID, пропуск raid=noautodetect", "warning")
            return True

        return self.add_grub_params(["raid=noautodetect"])

    def apply_corectrl(self, params=None):
        params = params or {}
        group = params.get("corectrl_group", "sudo").strip() or "sudo"

        # Валидация имени группы
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", group):
            self.log(f"Некорректное имя группы: {group}", "error")
            return False

        if self.dry_run:
            self.log(f"[DRY RUN] CoreCtrl polkit rule для группы {group}", "warning")
            return True

        try:
            grp.getgrnam(group)
        except KeyError:
            self.log(f"Группа не найдена: {group}", "error")
            return False

        content = f"""polkit.addRule(function(action, subject) {{
    if ((action.id == "org.corectrl.helper.init" ||
         action.id == "org.corectrl.helperkiller.init") &&
        subject.local == true &&
        subject.active == true &&
        subject.isInGroup("{group}")) {{
        return polkit.Result.YES;
    }}
}});
"""

        path = "/etc/polkit-1/rules.d/90-corectrl.rules"

        if self.write_file(path, content, chmod="644", mkdir=True):
            self.log(f"✓ CoreCtrl настроен для группы {group}", "success")
            return True

        return False

    def apply_ppfeaturemask(self, params=None):
        return self.add_grub_params(["amdgpu.ppfeaturemask=0xffffffff"])

    def apply_vrr(self, params=None):
        if self.state.gpu not in ("AMD", "Unknown"):
            self.log("VRR доступен только для AMD GPU", "warning")
            return True

        if self.dry_run:
            self.log("[DRY RUN] VRR/FreeSync конфиг", "warning")
            return True

        content = """Section "Device"
    Identifier "AMD"
    Driver "amdgpu"
    Option "VariableRefresh" "true"
EndSection
"""

        path = "/etc/X11/xorg.conf.d/20-amdgpu.conf"

        if self.write_file(path, content, chmod="644", mkdir=True):
            self.log("✓ VRR/FreeSync включён", "success")
            return True

        return False

    def apply_pipewire(self, params=None):
        d = os.path.join(
            self.state.user_home,
            ".config",
            "pipewire",
            "pipewire.conf.d",
        )

        path = os.path.join(d, "10-sound.conf")

        if self.dry_run:
            self.log(f"[DRY RUN] PipeWire конфиг: {path}", "warning")
            return True

        content = """context.properties = {
    default.clock.min-quantum = 512
    default.clock.quantum = 4096
    default.clock.max-quantum = 8192
}
"""

        if not self.sudo_run(["mkdir", "-p", d], ignore_error=True):
            return False

        if not self.write_file(path, content, chmod="644"):
            return False

        if self.state.user_name and self.state.user_name != "root":
            self.sudo_run(
                [
                    "chown",
                    "-R",
                    f"{self.state.user_name}:{self.state.user_name}",
                    os.path.join(self.state.user_home, ".config", "pipewire"),
                ],
                ignore_error=True,
            )

        self.log("✓ PipeWire настроен", "success")
        return True

    def apply_mesa(self, params=None):
        return self.ensure_line(
            "/etc/environment",
            "MESA_SHADER_CACHE_MAX_SIZE=4G",
            r"^\s*MESA_SHADER_CACHE_MAX_SIZE=.*",
        )

    def apply_radv(self, params=None):
        return self.ensure_line(
            "/etc/environment",
            "RADV_PERFTEST=sam",
            r"^\s*RADV_PERFTEST=.*",
        )

    def apply_swap(self, params=None):
        params = params or {}

        if not self.state.has_swap:
            self.log("Swap не обнаружен, тюнинг swap пропущен", "warning")
            return True

        val = params.get("swap_value", "").strip()

        if not val:
            val = "150" if self.state.swap_type == "zram" else "10"

        try:
            int_val = int(val)

            if int_val < 0 or int_val > 200:
                raise ValueError

        except ValueError:
            self.log(
                f"Некорректное значение swappiness: {val}. "
                "Нужно целое число от 0 до 200.",
                "error",
            )
            return False

        if self.dry_run:
            self.log(f"[DRY RUN] vm.swappiness={int_val}", "warning")
            return True

        path = "/etc/sysctl.d/99-gaming-swap.conf"

        # Проверка идемпотентности
        existing = self.read_file(path)

        if existing and re.search(rf"^vm\.swappiness={int_val}$", existing, re.M):
            self.log(f"vm.swappiness уже установлен: {int_val}", "info")
            return True

        content = f"vm.swappiness={int_val}\n"

        if not self.write_file(path, content, chmod="644", mkdir=True):
            return False

        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        self.log(f"✓ vm.swappiness={int_val}", "success")
        return True

    def apply_sysctl(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] vfs_cache_pressure=50, numa_balancing=0", "warning")
            return True

        path = "/etc/sysctl.d/99-gaming-sysctl.conf"

        # Проверка идемпотентности через точные regex
        existing = self.read_file(path)

        if existing:
            has_vfs = bool(re.search(r"^vm\.vfs_cache_pressure=50$", existing, re.M))
            has_numa = bool(re.search(r"^kernel\.numa_balancing=0$", existing, re.M))

            if has_vfs and has_numa:
                self.log("sysctl уже настроен", "info")
                return True

        # ВАЖНО: строки без отступов!
        content = """vm.vfs_cache_pressure=50
kernel.numa_balancing=0
"""

        if not self.write_file(path, content, chmod="644", mkdir=True):
            return False

        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        self.log("✓ vfs_cache_pressure=50, numa_balancing=0", "success")
        return True

    def apply_ntsync(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] ntsync modules-load", "warning")
            return True

        if self.state.ntsync:
            self.log("ntsync уже доступен в системе", "info")
            return True

        path = "/etc/modules-load.d/ntsync.conf"

        if not self.write_file(path, "ntsync\n", chmod="644", mkdir=True):
            return False

        self.sudo_run(["modprobe", "ntsync"], ignore_error=True)
        self.log("✓ ntsync добавлен в автозагрузку", "success")
        return True

    def apply_ntfs3(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] ntfs3 blacklist unlock", "warning")
            return True

        path = "/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"

        if not self.path_exists(path):
            self.log(
                "Файл mint-blacklist-ntfs3.conf не найден. "
                "Возможно, система не Mint или файл удалён.",
                "warning",
            )
            return True

        content = self.read_file(path)

        if content is None:
            self.log(f"Не удалось прочитать {path}", "error")
            return False

        if re.search(r"^\s*#\s*blacklist\s+ntfs3\s*$", content, re.M):
            self.log("ntfs3 уже раскомментирован", "info")
            return True

        if re.search(r"^\s*blacklist\s+ntfs3\s*$", content, re.M):
            new_content = re.sub(
                r"^\s*blacklist\s+ntfs3\s*$",
                "# blacklist ntfs3",
                content,
                flags=re.M,
            )

            if self.write_file(path, new_content):
                self.log("✓ ntfs3 раскомментирован", "success")
                return True

            return False

        self.log("blacklist ntfs3 не найден в файле", "warning")
        return True

    def apply_aliases(self, params=None):
        bashrc = os.path.join(self.state.user_home, ".bashrc")

        if self.dry_run:
            self.log(f"[DRY RUN] Добавить команды в {bashrc}", "warning")
            return True

        if not self.path_exists(bashrc):
            self.log(f".bashrc не найден: {bashrc}", "error")
            return False

        content = self.read_file(bashrc)

        if content is None:
            self.log(f"Не удалось прочитать {bashrc}", "error")
            return False

        start_marker = "# >>> system-tuneup commands >>>"
        end_marker = "# <<< system-tuneup commands <<<"

        lines = content.splitlines()

        # Удаляем существующий блок
        without_block = []
        skip = False

        for line in lines:
            if line.strip() == start_marker:
                skip = True
                continue

            if line.strip() == end_marker:
                skip = False
                continue

            if not skip:
                without_block.append(line)

        # Удаляем старые алиасы и функции от прошлых версий
        names = [
            "upd",
            "upgr",
            "spices",
            "update_all",
            "inst",
            "remove",
            "search",
            "info",
            "clean",
            "space",
            "fix",
            "mem",
            "serv",
            "update_time",
        ]

        names_pattern = "|".join(names)

        alias_rx = re.compile(r"^\s*alias\s+(" + names_pattern + r")=")
        func_rx = re.compile(r"^\s*(" + names_pattern + r")\s*\(\)\s*\{")

        cleaned = []
        skip_function = False

        for line in without_block:
            if alias_rx.match(line):
                continue

            if func_rx.match(line):
                # Однострочная функция вида: inst() { ...; }
                if "}" in line:
                    continue

                skip_function = True
                continue

            if skip_function:
                if line.strip().startswith("}"):
                    skip_function = False
                continue

            if "system-tuneup" in line and line.strip().startswith("#"):
                continue

            cleaned.append(line)

        spices = self._has_cinnamon_spices()

        block = []

        block.append(start_marker)
        block.append("# Пользовательские команды для обновлений (system-tuneup)")
        block.append("")

        # ── upd ──
        block.append("upd() {")
        block.append('    echo "🔍 Поиск обновлений APT..."')
        block.append("    sudo apt update")
        block.append("}")
        block.append("")

        # ── upgr ──
        block.append("upgr() {")
        block.append('    echo "📦 Обновление пакетов APT..."')
        block.append("    sudo apt full-upgrade")
        block.append('    echo "📦 Обновление Flatpak..."')

        if spices:
            block.append(
                '    flatpak update && '
                'echo "🧂 Обновление апплетов Cinnamon..." && '
                "cinnamon-spice-updater --update-all"
            )
        else:
            block.append("    flatpak update")

        block.append("}")
        block.append("")

        # ── spices ──
        if spices:
            block.append("spices() {")
            block.append('    echo "🧂 Обновление апплетов Cinnamon..."')
            block.append("    cinnamon-spice-updater --update-all")
            block.append("}")
            block.append("")

        # ── update_all ──
        block.append("update_all() {")
        block.append('    echo "🔍 Поиск обновлений APT..."')
        block.append("    sudo apt update")
        block.append('    echo "📦 Обновление пакетов APT..."')
        block.append("    sudo apt full-upgrade -y")
        block.append('    echo "📦 Обновление Flatpak..."')
        block.append("    flatpak update -y")

        if spices:
            block.append('    echo "🧂 Обновление апплетов Cinnamon..."')
            block.append("    cinnamon-spice-updater --update-all")

        block.append('    echo "✅ Все обновления завершены!"')
        block.append("}")
        block.append("")

        # ── Дополнительные команды ──
        block.append("# Дополнительные команды (system-tuneup)")

        block.append('inst() { sudo apt install "$@"; }')
        block.append('remove() { sudo apt purge --autoremove "$@"; }')
        block.append('search() { apt search "$@"; }')
        block.append('info() { apt show "$@"; }')
        block.append("")

        # ── clean ──
        block.append("clean() {")
        block.append('    echo "════════════════════════════════════════"')
        block.append('    echo "🧹  НАЧАЛО ОЧИСТКИ СИСТЕМЫ"')
        block.append('    echo "════════════════════════════════════════"')
        block.append('    echo ""')
        block.append('    echo "📦 Шаг 1/3: Удаление неиспользуемых зависимостей..."')
        block.append("    sudo apt autoremove -y")
        block.append('    echo ""')
        block.append('    echo "🗑️  Шаг 2/3: Очистка устаревших пакетов..."')
        block.append("    sudo apt autoclean")
        block.append('    echo ""')
        block.append('    echo "💾 Шаг 3/3: Полная очистка кэша..."')
        block.append("    sudo apt clean")
        block.append('    echo ""')
        block.append('    echo "════════════════════════════════════════"')
        block.append('    echo "✅  ОЧИСТКА ЗАВЕРШЕНА"')
        block.append('    echo "════════════════════════════════════════"')
        block.append(
            "    echo \"📊 Свободно на диске: "
            "$(df -h / | awk 'NR==2 {print $4}')\""
        )
        block.append('    echo ""')
        block.append("}")
        block.append("")

        # ── space ──
        block.append("space() {")
        block.append('    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"')
        block.append('    echo "💾 СВОБОДНОЕ МЕСТО"')
        block.append('    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"')

        block.append(
            "    df -h / | awk 'NR==2 {print \"📁 / (корень):   \" $4 \" свободно из \" $2}'"
        )

        block.append("    root_dev=$(df --output=source / 2>/dev/null | tail -n1)")
        block.append("    home_dev=$(df --output=source /home 2>/dev/null | tail -n1)")

        block.append(
            "    if [ -n \"$home_dev\" ] && [ \"$home_dev\" != \"$root_dev\" ]; then"
        )
        block.append(
            "        df -h /home | awk 'NR==2 {print \"🏠 /home:        \" $4 \" свободно из \" $2}'"
        )
        block.append("    else")
        block.append('        echo "🏠 /home:        на том же разделе, что и /"')
        block.append("    fi")

        block.append('    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"')
        block.append("}")
        block.append("")

        # ── fix ──
        block.append("fix() {")
        block.append('    echo "🔧 Исправление сломанных пакетов..."')
        block.append("    sudo apt --fix-broken install -y")
        block.append("    sudo dpkg --configure -a")
        block.append('    echo "✅ Готово!"')
        block.append("}")
        block.append("")

        # ── mem ──
        block.append("mem() {")
        block.append('    echo "🧠 Очистка памяти..."')
        block.append("    sync")
        block.append('    echo "До:"')
        block.append("    free -h")
        block.append("    sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'")
        block.append('    echo "После:"')
        block.append("    free -h")
        block.append('    echo "✅ Память очищена!"')
        block.append("}")
        block.append("")

        # ── serv ──
        block.append("serv() {")
        block.append("    systemctl list-unit-files --type=service | less")
        block.append("}")
        block.append("")

        # ── update_time ──
        block.append("update_time() {")
        block.append('    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"')
        block.append('    echo "⏱️  ТАЙМЕРЫ ОБНОВЛЕНИЙ"')
        block.append('    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"')
        block.append(
            "    systemctl list-timers --no-pager 2>/dev/null | "
            "grep -E \"NEXT|upgrade|update|apt\" || "
            "echo \"Таймеры обновлений не найдены\""
        )
        block.append('    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"')
        block.append("}")

        block.append(end_marker)

        while cleaned and cleaned[-1].strip() == "":
            cleaned.pop()

        new_content = "\n".join(cleaned + [""] + block) + "\n"

        if new_content == content:
            self.log("Команды уже добавлены", "info")
            return True

        if not self.write_file(bashrc, new_content):
            return False

        if self.state.user_name and self.state.user_name != "root":
            self.sudo_run(
                ["chown", f"{self.state.user_name}:{self.state.user_name}", bashrc],
                ignore_error=True,
            )

        self.log("✓ Команды добавлены в .bashrc", "success")
        return True

    def apply_autoupdate(self, params=None):
        params = params or {}
        schedule_ui = params.get("update_schedule", "Отключено")

        schedules = {
            "Ежедневно": ("*-*-* 18:30:00", "ежедневно в 18:30"),
            "Еженедельно (суббота)": ("Sat 18:30:00", "еженедельно по субботам в 18:30"),
            "2 раза в месяц (1 и 15)": ("*-*-1,15 18:30:00", "1 и 15 числа в 18:30"),
            "Ежемесячно (1 число)": ("*-*-1 18:30:00", "ежемесячно 1 числа в 18:30"),
        }

        service_path = "/etc/systemd/system/biweekly-upgrade.service"
        timer_path = "/etc/systemd/system/biweekly-upgrade.timer"

        timer_file_exists = (
            self.path_exists(timer_path) or self.path_exists(service_path)
        )

        # ── Режим удаления ────────────────────────────────────────────────
        if schedule_ui == "Отключено":
            if not timer_file_exists:
                self.log("Таймер автообновлений не найден", "info")
                return True

            if self.dry_run:
                self.log("[DRY RUN] Удалить таймер автообновлений", "warning")
                return True

            self.sudo_run(
                ["systemctl", "disable", "--now", "biweekly-upgrade.timer"],
                ignore_error=True,
            )

            self.sudo_run(
                ["rm", "-f", service_path, timer_path],
                ignore_error=True,
            )

            self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
            self.log("Таймер автообновлений удалён", "success")
            return True

        # ── Проверка расписания ───────────────────────────────────────────
        if schedule_ui not in schedules:
            self.log(f"Неизвестное расписание: {schedule_ui}", "error")
            return False

        oncalendar, desc = schedules[schedule_ui]

        spices = self._has_cinnamon_spices()

        full_cmd = "apt update && apt full-upgrade -y && flatpak update -y"

        if spices:
            full_cmd += " && cinnamon-spice-updater --update-all"

        # ВАЖНО: строки внутри этих f"""...""" должны начинаться с первой колонки.
        # Иначе systemd не сможет корректно прочитать unit-файлы.
        service_content = f"""[Unit]
Description=System upgrade ({desc})

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 600
ExecStart=/usr/bin/bash -c "{full_cmd}"
User=root
"""

        timer_content = f"""[Unit]
Description=System upgrade timer ({desc})

[Timer]
OnCalendar={oncalendar}
Persistent=true

[Install]
WantedBy=timers.target
"""

        existing_service = self.read_file(service_path)
        existing_timer = self.read_file(timer_path)

        # ── Если конфигурация уже полностью совпадает ─────────────────────
        if (
            timer_file_exists
            and existing_service is not None
            and existing_timer is not None
            and existing_service == service_content
            and existing_timer == timer_content
        ):
            self.log(f"Таймер уже настроен: {desc}", "info")

            # Если файл есть, но таймер не включён — включим.
            if self.service_enabled("biweekly-upgrade.timer") != "enabled":
                if self.dry_run:
                    self.log(
                        "[DRY RUN] systemctl enable --now biweekly-upgrade.timer",
                        "warning",
                    )
                else:
                    self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
                    self.sudo_run(
                        ["systemctl", "enable", "--now", "biweekly-upgrade.timer"],
                        ignore_error=True,
                    )

            return True

        # ── Создание или обновление ───────────────────────────────────────
        if self.dry_run:
            action = "Обновить" if timer_file_exists else "Создать"
            self.log(f"[DRY RUN] {action} таймер: {desc}", "warning")
            return True

        # Отключаем стандартный таймер Mint, если он есть.
        self.sudo_run(
            ["systemctl", "disable", "--now", "mintupdate-automation-upgrade.timer"],
            ignore_error=True,
        )

        if not self.write_file(service_path, service_content, chmod="644"):
            return False

        if not self.write_file(timer_path, timer_content, chmod="644"):
            return False

        self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)

        self.sudo_run(
            ["systemctl", "enable", "--now", "biweekly-upgrade.timer"],
            ok_msg=f"✓ Таймер создан/обновлён: {desc}",
            err_msg="Не удалось включить таймер",
        )

        return True


# ─── ГЛАВНОЕ ПРИЛОЖЕНИЕ ──────────────────────────────────────────────────────

class TuneupApp:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.is_running = False

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

        self.create_ui()
        self.apply_hardware_restrictions()

        self.root.after(100, self.process_queue)

        self.log("System Tuneup GUI запущен", "success")
        self.log(f"GPU: {self.state.gpu}", "info")
        self.log(f"Пользователь: {self.state.user_name}", "info")
        self.log(f"Домашняя папка: {self.state.user_home}", "info")

        if self.dry_run_var.get():
            self.log("Режим: СУХОЙ ПРОГОН", "warning")

        if self.sudo._sudo_cached():
            self.log("Сессия sudo уже активна", "success")
        else:
            self.log("Для применения изменений потребуется пароль sudo", "warning")

        # Автообновление служб при старте
        self.root.after(500, self.refresh_services)

    # ─── Опции ───────────────────────────────────────────────────────────────

    def _create_options(self):
        return {
            "rsyslog": {
                "label": "Отключить rsyslog",
                "desc": "Логирование в файлы (на десктопе обычно не нужно)",
                "category": "Логи",
                "var": tk.BooleanVar(value=False),
            },
            "journald": {
                "label": "Логи в ОЗУ (journald)",
                "desc": "Storage=volatile, RuntimeMaxUse=50M",
                "category": "Логи",
                "var": tk.BooleanVar(value=False),
            },
            "audit": {
                "label": "audit=0 (GRUB)",
                "desc": "Отключить аудит ядра",
                "category": "GRUB",
                "var": tk.BooleanVar(value=False),
            },
            "raid": {
                "label": "raid=noautodetect (GRUB)",
                "desc": "Ускорить загрузку, если нет RAID",
                "category": "GRUB",
                "var": tk.BooleanVar(value=False),
            },
            "corectrl": {
                "label": "CoreCtrl (Polkit)",
                "desc": "Правило для управления частотами и вентиляторами AMD GPU",
                "category": "AMD GPU",
                "var": tk.BooleanVar(value=False),
            },
            "ppfeaturemask": {
                "label": "amdgpu.ppfeaturemask",
                "desc": "Разблокировать управление питанием AMD GPU",
                "category": "AMD GPU",
                "var": tk.BooleanVar(value=False),
            },
            "vrr": {
                "label": "VRR/FreeSync",
                "desc": "Переменная частота обновления для AMD",
                "category": "AMD GPU",
                "var": tk.BooleanVar(value=False),
            },
            "radv": {
                "label": "RADV_PERFTEST=sam",
                "desc": "Оптимизация Resizable BAR для AMD",
                "category": "AMD GPU",
                "var": tk.BooleanVar(value=False),
            },
            "pipewire": {
                "label": "PipeWire (звук)",
                "desc": "Увеличить кванты звука, уменьшить треск",
                "category": "Звук",
                "var": tk.BooleanVar(value=False),
            },
            "mesa": {
                "label": "MESA_SHADER_CACHE=4G",
                "desc": "Кэш шейдеров 4 ГБ",
                "category": "Графика",
                "var": tk.BooleanVar(value=False),
            },
            "swap": {
                "label": "Тюнинг swap",
                "desc": "vm.swappiness (для zram обычно 150, для диска 10)",
                "category": "Память",
                "var": tk.BooleanVar(value=False),
            },
            "sysctl": {
                "label": "Тюнинг sysctl",
                "desc": "vfs_cache_pressure=50, numa_balancing=0",
                "category": "Ядро",
                "var": tk.BooleanVar(value=False),
            },
            "ntsync": {
                "label": "ntsync (модуль ядра)",
                "desc": "Для Proton/Wine, требует ядро с поддержкой",
                "category": "Игры",
                "var": tk.BooleanVar(value=False),
            },
            "ntfs3": {
                "label": "ntfs3 драйвер",
                "desc": "Быстрый драйвер для NTFS-дисков",
                "category": "Диски",
                "var": tk.BooleanVar(value=False),
            },
            "aliases": {
                "label": "Команды в .bashrc",
                "desc": "upd, upgr, spices, update_all и другие",
                "category": "Удобство",
                "var": tk.BooleanVar(value=False),
            },
            "autoupdate": {
                "label": "Автообновления",
                "desc": "systemd-таймер для APT + Flatpak",
                "category": "Обновления",
                "var": tk.BooleanVar(value=False),
            },
        }

    # ─── UI ──────────────────────────────────────────────────────────────────

    def create_ui(self):
        self.root.title("System Tuneup v3.2.0")
        self.root.geometry("1000x780")
        self.root.minsize(880, 640)
        self.root.configure(bg=COLORS["bg"])

        style = ttk.Style()

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#333333",
            foreground=COLORS["fg"],
            padding=[12, 5],
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#555555")],
            foreground=[("selected", "white")],
        )

        style.configure(
            "Treeview",
            background="#252525",
            foreground=COLORS["fg"],
            fieldbackground="#252525",
            rowheight=24,
        )
        style.configure(
            "Treeview.Heading",
            background="#333333",
            foreground="white",
        )

        style.configure("TCombobox", fieldbackground=COLORS["entry"])

        # Header
        header = tk.Frame(self.root, bg=COLORS["bg"])
        header.pack(fill="x", padx=10, pady=(10, 5))

        tk.Label(
            header,
            text="⚙️ System Tuneup",
            font=("Arial", 18, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["green"],
        ).pack(side="left")

        tk.Label(
            header,
            text="v3.2.0",
            font=("Arial", 10),
            bg=COLORS["bg"],
            fg=COLORS["gray"],
        ).pack(side="left", padx=(10, 0))

        tk.Checkbutton(
            header,
            text="Сухой прогон",
            variable=self.dry_run_var,
            command=self.update_title,
            bg=COLORS["bg"],
            fg=COLORS["yellow"],
            activebackground=COLORS["bg"],
            activeforeground=COLORS["yellow"],
            selectcolor="#333333",
            font=("Arial", 10, "bold"),
        ).pack(side="right")

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10, pady=5)

        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_tuneup = ttk.Frame(self.notebook)
        self.tab_services = ttk.Frame(self.notebook)
        self.tab_status = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_tuneup, text="🔧 Тюнинг")
        self.notebook.add(self.tab_services, text="📋 Службы")
        self.notebook.add(self.tab_status, text="📊 Статус")

        self.create_tuning_tab()
        self.create_services_tab()
        self.create_status_tab()

        # Buttons
        buttons = tk.Frame(self.root, bg=COLORS["bg"])
        buttons.pack(fill="x", padx=10, pady=5)

        self.run_button = tk.Button(
            buttons,
            text="▶️ Применить",
            command=self.apply_selected,
            bg=COLORS["green"],
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8,
        )
        self.run_button.pack(side="left", padx=5)

        tk.Button(
            buttons,
            text="☑️ Выбрать все",
            command=self.select_all,
            bg="#444444",
            fg="white",
            padx=12,
            pady=8,
        ).pack(side="left", padx=5)

        tk.Button(
            buttons,
            text="🔄 Сбросить",
            command=self.reset_all,
            bg="#444444",
            fg="white",
            padx=12,
            pady=8,
        ).pack(side="left", padx=5)

        tk.Button(
            buttons,
            text="💾 Экспорт",
            command=self.export_config,
            bg="#444444",
            fg="white",
            padx=12,
            pady=8,
        ).pack(side="left", padx=5)

        tk.Button(
            buttons,
            text="❓ Помощь",
            command=self.show_help,
            bg="#444444",
            fg="white",
            padx=12,
            pady=8,
        ).pack(side="right", padx=5)

        # Terminal
        terminal_frame = tk.Frame(self.root, bg=COLORS["bg"])
        terminal_frame.pack(fill="both", expand=True, padx=10, pady=(5, 0))

        tk.Label(
            terminal_frame,
            text="Терминальный вывод:",
            bg=COLORS["bg"],
            fg=COLORS["gray"],
            font=("Arial", 9),
            anchor="w",
        ).pack(fill="x")

        self.terminal = scrolledtext.ScrolledText(
            terminal_frame,
            height=12,
            bg=COLORS["terminal"],
            fg=COLORS["fg"],
            font=("Courier New", 10),
            insertbackground="white",
            wrap="word",
            relief="sunken",
            bd=1,
            state="disabled",
        )
        self.terminal.pack(fill="both", expand=True, pady=(2, 0))

        self.terminal.tag_configure("normal", foreground=COLORS["fg"])
        self.terminal.tag_configure("success", foreground=COLORS["green"])
        self.terminal.tag_configure("error", foreground=COLORS["red"])
        self.terminal.tag_configure("warning", foreground=COLORS["yellow"])
        self.terminal.tag_configure("info", foreground=COLORS["blue"])
        self.terminal.tag_configure("highlight", foreground=COLORS["orange"])

        # Status bar
        status_frame = tk.Frame(self.root, bg=COLORS["bg"])
        status_frame.pack(fill="x", padx=10, pady=(2, 10))

        self.status_text = tk.StringVar()
        self.status_text.set("Готово")

        tk.Label(
            status_frame,
            textvariable=self.status_text,
            bg=COLORS["bg"],
            fg=COLORS["gray"],
            font=("Arial", 9),
            anchor="w",
        ).pack(side="left")

        self.progress_var = tk.DoubleVar(value=0)

        ttk.Progressbar(
            status_frame,
            variable=self.progress_var,
            maximum=100,
            length=180,
            mode="determinate",
        ).pack(side="right")

    def create_tuning_tab(self):
        container = tk.Frame(self.tab_tuneup, bg=COLORS["bg"])
        container.pack(fill="both", expand=True, padx=8, pady=8)

        canvas = tk.Canvas(container, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

        self.options_inner = tk.Frame(canvas, bg=COLORS["bg"])
        self.canvas_window = canvas.create_window(
            (0, 0),
            window=self.options_inner,
            anchor="nw",
        )

        self.options_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(self.canvas_window, width=e.width),
        )

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        categories = {}

        for key, option in self.options.items():
            cat = option["category"]
            categories.setdefault(cat, []).append(key)

        for cat in sorted(categories.keys()):
            tk.Label(
                self.options_inner,
                text=f"── {cat} ──",
                bg=COLORS["bg"],
                fg=COLORS["yellow"],
                font=("Arial", 10, "bold"),
                anchor="w",
            ).pack(fill="x", pady=(10, 3))

            for key in categories[cat]:
                self.create_option_row(key)

    def create_option_row(self, key):
        option = self.options[key]

        row = tk.Frame(self.options_inner, bg=COLORS["bg"])
        row.pack(fill="x", pady=1)

        top = tk.Frame(row, bg=COLORS["bg"])
        top.pack(fill="x")

        cb = tk.Checkbutton(
            top,
            text=option["label"],
            variable=option["var"],
            bg=COLORS["bg"],
            fg=COLORS["fg"],
            activebackground=COLORS["bg"],
            activeforeground=COLORS["fg"],
            selectcolor="#333333",
            font=("Arial", 10),
            anchor="w",
        )
        cb.pack(side="left")

        self.option_widgets[key] = cb

        if key == "corectrl":
            tk.Label(
                top,
                text="Группа:",
                bg=COLORS["bg"],
                fg=COLORS["gray"],
                font=("Arial", 9),
            ).pack(side="left", padx=(15, 2))

            tk.Entry(
                top,
                textvariable=self.corectrl_group,
                width=14,
                bg=COLORS["entry"],
                fg="white",
                insertbackground="white",
            ).pack(side="left")

        elif key == "swap":
            tk.Label(
                top,
                text="Значение:",
                bg=COLORS["bg"],
                fg=COLORS["gray"],
                font=("Arial", 9),
            ).pack(side="left", padx=(15, 2))

            tk.Entry(
                top,
                textvariable=self.swap_value,
                width=6,
                bg=COLORS["entry"],
                fg="white",
                insertbackground="white",
            ).pack(side="left")

        elif key == "autoupdate":
            tk.Label(
                top,
                text="Расписание:",
                bg=COLORS["bg"],
                fg=COLORS["gray"],
                font=("Arial", 9),
            ).pack(side="left", padx=(15, 2))

            ttk.Combobox(
                top,
                textvariable=self.update_schedule,
                values=(
                    "Отключено",
                    "Ежедневно",
                    "Еженедельно (суббота)",
                    "2 раза в месяц (1 и 15)",
                    "Ежемесячно (1 число)",
                ),
                state="readonly",
                width=26,
            ).pack(side="left")

        tk.Label(
            row,
            text=option["desc"],
            bg=COLORS["bg"],
            fg=COLORS["gray"],
            font=("Arial", 8),
            anchor="w",
        ).pack(fill="x", padx=(28, 0))

    def create_services_tab(self):
        container = tk.Frame(self.tab_services, bg=COLORS["bg"])
        container.pack(fill="both", expand=True, padx=8, pady=8)

        buttons = tk.Frame(container, bg=COLORS["bg"])
        buttons.pack(fill="x", pady=(0, 8))

        tk.Button(
            buttons,
            text="🔄 Обновить",
            command=self.refresh_services,
            bg="#444444",
            fg="white",
            padx=10,
            pady=5,
        ).pack(side="left", padx=2)

        tk.Button(
            buttons,
            text="🚫 Отключить рекомендуемые",
            command=self.disable_recommended,
            bg="#444444",
            fg="white",
            padx=10,
            pady=5,
        ).pack(side="left", padx=2)

        tk.Button(
            buttons,
            text="✅ Включить выбранные",
            command=self.enable_selected,
            bg="#444444",
            fg="white",
            padx=10,
            pady=5,
        ).pack(side="left", padx=2)

        tk.Button(
            buttons,
            text="🚫 Отключить выбранные",
            command=self.disable_selected,
            bg="#444444",
            fg="white",
            padx=10,
            pady=5,
        ).pack(side="left", padx=2)

        tree_frame = tk.Frame(container, bg=COLORS["bg"])
        tree_frame.pack(fill="both", expand=True)

        self.services_tree = ttk.Treeview(
            tree_frame,
            columns=("name", "enabled", "active", "desc"),
            show="headings",
            selectmode="extended",
        )

        self.services_tree.heading("name", text="Служба")
        self.services_tree.heading("enabled", text="Enabled")
        self.services_tree.heading("active", text="Active")
        self.services_tree.heading("desc", text="Описание")

        self.services_tree.column("name", width=260, anchor="w")
        self.services_tree.column("enabled", width=110, anchor="center")
        self.services_tree.column("active", width=100, anchor="center")
        self.services_tree.column("desc", width=420, anchor="w")

        scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.services_tree.yview,
        )

        self.services_tree.configure(yscrollcommand=scrollbar.set)

        self.services_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.services_count_label = tk.Label(
            container,
            text="Служб: 0",
            bg=COLORS["bg"],
            fg=COLORS["gray"],
            font=("Arial", 9),
            anchor="w",
        )
        self.services_count_label.pack(fill="x", pady=(6, 0))

    def create_status_tab(self):
        container = tk.Frame(self.tab_status, bg=COLORS["bg"])
        container.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Button(
            container,
            text="🔄 Обновить статус",
            command=self.refresh_status,
            bg="#444444",
            fg="white",
            padx=12,
            pady=6,
        ).pack(anchor="w", pady=(0, 8))

        self.status_text_widget = scrolledtext.ScrolledText(
            container,
            bg=COLORS["terminal"],
            fg=COLORS["fg"],
            font=("Courier New", 10),
            state="disabled",
        )
        self.status_text_widget.pack(fill="both", expand=True)

    # ─── Queue / logging ─────────────────────────────────────────────────────

    def log(self, msg, tag="normal"):
        """Потокобезопасный лог."""
        if not msg.endswith("\n"):
            msg += "\n"

        self.q.put(("log", msg, tag))

    def process_queue(self):
        """Обработчик очереди. Выполняется в главном потоке."""
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
                    state = "disabled" if item[1] else "normal"
                    self.run_button.config(state=state)

                elif kind == "services_rows":
                    for child in self.services_tree.get_children():
                        self.services_tree.delete(child)

                    for row in item[1]:
                        self.services_tree.insert("", "end", values=row)

                    self.services_count_label.config(
                        text=f"Служб: {len(item[1])}"
                    )

                elif kind == "status_text":
                    self.status_text_widget.configure(state="normal")
                    self.status_text_widget.delete("1.0", tk.END)
                    self.status_text_widget.insert(tk.END, item[1])
                    self.status_text_widget.configure(state="disabled")

        except queue.Empty:
            pass

        self.root.after(100, self.process_queue)

    # ─── Apply ───────────────────────────────────────────────────────────────

    def apply_selected(self):
        if self.is_running:
            messagebox.showinfo(
                "Выполняется",
                "Скрипт уже запущен. Дождитесь завершения.",
            )
            return

        selected = [
            key
            for key, option in self.options.items()
            if option["var"].get()
        ]

        if not selected:
            messagebox.showwarning(
                "Нет выбранных опций",
                "Отметьте хотя бы одну опцию.",
            )
            return

        params = {
            "corectrl_group": self.corectrl_group.get(),
            "swap_value": self.swap_value.get(),
            "update_schedule": self.update_schedule.get(),
        }

        dry_run = self.dry_run_var.get()

        if not dry_run:
            if not self.sudo.ensure():
                self.log("Не удалось получить права sudo", "error")
                return

        self.q.put(("running", True))
        self.q.put(("progress", 0))
        self.q.put(("statusbar", "Выполнение..."))

        threading.Thread(
            target=self._apply_worker,
            args=(selected, params, dry_run),
            daemon=True,
        ).start()

    def _apply_worker(self, selected, params, dry_run):
        ops = SystemOps(self.sudo, self.state, self.log, dry_run)

        total = len(selected)
        done = 0

        self.log("=" * 60, "highlight")
        self.log("ЗАПУСК ТЮНИНГА", "highlight")
        self.log(f"Режим: {'СУХОЙ ПРОГОН' if dry_run else 'ОБЫЧНЫЙ'}", "info")
        self.log(f"Выбрано опций: {total}", "info")
        self.log("=" * 60, "highlight")

        try:
            for key in selected:
                label = self.options[key]["label"]
                self.log(f"→ {label}", "info")

                try:
                    method = getattr(ops, f"apply_{key}")
                    method(params)
                except Exception as e:
                    self.log(f"Ошибка в {label}: {e}", "error")

                done += 1
                self.q.put(("progress", int(done / total * 90)))

            if not dry_run:
                ops.finalize_grub()

            self.q.put(("progress", 100))
            self.q.put(("statusbar", "Готово"))
            self.log("Все выбранные операции обработаны", "success")

        except Exception as e:
            self.log(f"Критическая ошибка: {e}", "error")
            self.q.put(("statusbar", "Ошибка"))

        finally:
            self.q.put(("running", False))

    # ─── Options helpers ─────────────────────────────────────────────────────

    def select_all(self):
        for key, option in self.options.items():
            widget = self.option_widgets.get(key)

            if widget and str(widget.cget("state")) == "normal":
                option["var"].set(True)

    def reset_all(self):
        for option in self.options.values():
            option["var"].set(False)

    def disable_option(self, key):
        widget = self.option_widgets.get(key)

        if widget:
            widget.config(state="disabled")

        self.options[key]["var"].set(False)

    def apply_hardware_restrictions(self):
        # AMD-only
        if self.state.gpu not in ("AMD", "Unknown"):
            for key in ("corectrl", "ppfeaturemask", "vrr", "radv"):
                self.disable_option(key)

        # RAID
        if self.state.has_raid:
            self.disable_option("raid")

        # Swap
        if not self.state.has_swap:
            self.disable_option("swap")

        # ntfs3
        if not os.path.exists("/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"):
            self.disable_option("ntfs3")

        # Swap defaults
        self.swap_value.set(
            "150" if self.state.swap_type == "zram" else "10"
        )

    def update_title(self):
        title = "System Tuneup v3.2.0"

        if self.dry_run_var.get():
            title += " [СУХОЙ ПРОГОН]"

        self.root.title(title)

    def export_config(self):
        selected = []

        for key, option in self.options.items():
            if option["var"].get():
                selected.append(f"{key}: {option['label']}")

        if not selected:
            messagebox.showinfo(
                "Экспорт",
                "Нет выбранных опций для экспорта.",
            )
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialdir=os.path.expanduser("~"),
            filetypes=[("Text files", "*.txt")],
            title="Сохранить конфигурацию",
        )

        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("System Tuneup GUI config\n")
                f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Dry run: {self.dry_run_var.get()}\n")
                f.write("\nSelected options:\n")

                for line in selected:
                    f.write(line + "\n")

                f.write("\nParams:\n")
                f.write(f"corectrl_group={self.corectrl_group.get()}\n")
                f.write(f"swap_value={self.swap_value.get()}\n")
                f.write(f"update_schedule={self.update_schedule.get()}\n")

            self.log(f"Конфигурация сохранена: {path}", "success")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")

    def show_help(self):
        text = """
System Tuneup GUI v2.1.0

Это графическая оболочка для тюнинга системы.

Особенности:
  - Не использует внешний bash-скрипт.
  - Применяет настройки напрямую через Python.
  - Использует sudo -S -v для кэширования прав.
  - Потокобезопасный вывод через queue + root.after().

Как пользоваться:
  1. Откройте вкладку "Тюнинг".
  2. Отметьте нужные опции.
  3. При необходимости заполните параметры:
       - группа для CoreCtrl;
       - значение vm.swappiness;
       - расписание автообновлений.
  4. Нажмите "Применить".
  5. Введите пароль sudo, если потребуется.

Сухой прогон:
  - Включите галочку "Сухой прогон".
  - Изменения не применяются.
  - В логе видно, какие команды были бы выполнены.

Вкладка "Службы":
  - Показывает статус рекомендуемых служб.
  - Можно отключить рекомендуемые службы.
  - Можно включить/отключить выбранные службы вручную.

Вкладка "Статус":
  - Показывает текущее состояние системы.
  - Для полного статуса может потребоваться активный кэш sudo.
"""
        messagebox.showinfo("Помощь", text)

    # ─── Services ────────────────────────────────────────────────────────────

    def refresh_services(self):
        threading.Thread(
            target=self._refresh_services_worker,
            daemon=True,
        ).start()

    def _refresh_services_worker(self):
        ops = SystemOps(
            self.sudo,
            self.state,
            lambda msg, tag="normal": None,
            self.dry_run_var.get(),
        )

        rows = []

        for svc in SERVICES:
            name = svc["name"]
            desc = svc["desc"]

            if not ops.unit_exists(name):
                rows.append((name, "not-found", "not-found", desc))
                continue

            enabled = ops.service_enabled(name)
            active = ops.service_active(name)

            rows.append((name, enabled, active, desc))

        self.q.put(("services_rows", rows))

    def _ensure_service_action(self):
        if self.dry_run_var.get():
            return True

        return self.sudo.ensure()

    def disable_recommended(self):
        if not self._ensure_service_action():
            return

        threading.Thread(
            target=self._disable_recommended_worker,
            daemon=True,
        ).start()

    def _disable_recommended_worker(self):
        ops = SystemOps(
            self.sudo,
            self.state,
            self.log,
            self.dry_run_var.get(),
        )

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

            if name.startswith("avahi"):
                ops.sudo_run(
                    ["systemctl", "disable", "--now", name],
                    ignore_error=True,
                )
                ops.sudo_run(
                    ["systemctl", "mask", name],
                    ok_msg=f"{name} замаскирована",
                    ignore_error=True,
                )
            else:
                ops.sudo_run(
                    ["systemctl", "disable", "--now", name],
                    ok_msg=f"{name} отключена",
                    ignore_error=True,
                )

        self.log("Обработка служб завершена", "success")
        self.refresh_services()

    def enable_selected(self):
        items = self.services_tree.selection()

        if not items:
            messagebox.showinfo(
                "Службы",
                "Сначала выберите службы в таблице.",
            )
            return

        names = [
            str(self.services_tree.item(item)["values"][0])
            for item in items
        ]

        if not self._ensure_service_action():
            return

        threading.Thread(
            target=self._enable_units_worker,
            args=(names,),
            daemon=True,
        ).start()

    def _enable_units_worker(self, names):
        ops = SystemOps(
            self.sudo,
            self.state,
            self.log,
            self.dry_run_var.get(),
        )

        for name in names:
            if ops.dry_run:
                ops.log(f"[DRY RUN] enable {name}", "warning")
                continue

            ops.sudo_run(["systemctl", "unmask", name], ignore_error=True)
            ops.sudo_run(
                ["systemctl", "enable", name],
                ok_msg=f"{name} включена",
                ignore_error=True,
            )

        self.log("Включение служб завершено", "success")
        self.refresh_services()

    def disable_selected(self):
        items = self.services_tree.selection()

        if not items:
            messagebox.showinfo(
                "Службы",
                "Сначала выберите службы в таблице.",
            )
            return

        names = [
            str(self.services_tree.item(item)["values"][0])
            for item in items
        ]

        if not self._ensure_service_action():
            return

        threading.Thread(
            target=self._disable_units_worker,
            args=(names,),
            daemon=True,
        ).start()

    def _disable_units_worker(self, names):
        ops = SystemOps(
            self.sudo,
            self.state,
            self.log,
            self.dry_run_var.get(),
        )

        for name in names:
            if ops.dry_run:
                ops.log(f"[DRY RUN] disable {name}", "warning")
                continue

            ops.sudo_run(
                ["systemctl", "disable", "--now", name],
                ignore_error=True,
            )

            if name.startswith("avahi"):
                ops.sudo_run(
                    ["systemctl", "mask", name],
                    ignore_error=True,
                )

            self.log(f"{name} отключена", "success")

        self.log("Отключение служб завершено", "success")
        self.refresh_services()

    # ─── Status ──────────────────────────────────────────────────────────────

    def refresh_status(self):
        threading.Thread(
            target=self._refresh_status_worker,
            daemon=True,
        ).start()

    def _refresh_status_worker(self):
        ops = SystemOps(
            self.sudo,
            self.state,
            lambda msg, tag="normal": None,
            True,
        )

        lines = []

        lines.append("=== Аппаратное обеспечение ===")
        lines.append(f"GPU: {self.state.gpu}")
        lines.append(f"RAID: {'да' if self.state.has_raid else 'нет'}")
        lines.append(
            f"Swap: {self.state.swap_type if self.state.has_swap else 'нет'}"
        )
        lines.append(f"ntsync: {'доступен' if self.state.ntsync else 'не найден'}")
        lines.append(f"Cinnamon: {'да' if self.state.cinnamon else 'нет'}")
        lines.append(f"Пользователь: {self.state.user_name}")
        lines.append(f"Домашняя папка: {self.state.user_home}")
        lines.append("")

        lines.append("=== Службы ===")

        for svc in SERVICES:
            name = svc["name"]
            enabled = ops.service_enabled(name)
            active = ops.service_active(name)
            lines.append(f"{name}: enabled={enabled}, active={active}")

        lines.append("")
        lines.append("=== Ядро ===")

        for param in (
            "vm.swappiness",
            "vm.vfs_cache_pressure",
            "kernel.numa_balancing",
        ):
            try:
                res = subprocess.run(
                    ["sysctl", "-n", param],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )

                value = res.stdout.strip() if res.returncode == 0 else "н/д"

            except Exception:
                value = "н/д"

            lines.append(f"{param} = {value}")

        lines.append("")
        lines.append("=== GRUB ===")

        grub = ops.read_file("/etc/default/grub") or ""

        for param in (
            "audit=0",
            "raid=noautodetect",
            "amdgpu.ppfeaturemask",
        ):
            lines.append(
                f"{param}: "
                f"{'присутствует' if param in grub else 'отсутствует'}"
            )

        lines.append("")
        lines.append("=== Конфиги ===")

        journald = ops.read_file("/etc/systemd/journald.conf") or ""
        journald_volatile = bool(
            re.search(r"^\s*Storage\s*=\s*volatile\s*$", journald, re.M)
        )
        lines.append(f"journald volatile: {'да' if journald_volatile else 'нет'}")

        env = ops.read_file("/etc/environment") or ""
        lines.append(
            "MESA_SHADER_CACHE_MAX_SIZE=4G: "
            f"{'да' if 'MESA_SHADER_CACHE_MAX_SIZE=4G' in env else 'нет'}"
        )
        lines.append(
            "RADV_PERFTEST=sam: "
            f"{'да' if 'RADV_PERFTEST=sam' in env else 'нет'}"
        )

        lines.append(
            "CoreCtrl rules: "
            f"{'да' if ops.path_exists('/etc/polkit-1/rules.d/90-corectrl.rules') else 'нет'}"
        )

        lines.append(
            "VRR/FreeSync: "
            f"{'да' if ops.path_exists('/etc/X11/xorg.conf.d/20-amdgpu.conf') else 'нет'}"
        )

        pipewire_path = os.path.join(
            self.state.user_home,
            ".config",
            "pipewire",
            "pipewire.conf.d",
            "10-sound.conf",
        )

        lines.append(
            f"PipeWire config: {'да' if ops.path_exists(pipewire_path) else 'нет'}"
        )

        bashrc = ops.read_file(os.path.join(self.state.user_home, ".bashrc")) or ""
        lines.append(
            f"Команды в .bashrc: {'да' if 'system-tuneup' in bashrc else 'нет'}"
        )

        timer = ops.service_enabled("biweekly-upgrade.timer")
        lines.append(f"Автообновления (таймер): {timer}")

        self.q.put(("status_text", "\n".join(lines)))

    # ─── Closing ─────────────────────────────────────────────────────────────

    def on_closing(self):
        if self.is_running:
            if not messagebox.askyesno(
                "Выполняется",
                "Скрипт ещё выполняется.\n"
                "Закрыть программу и прервать выполнение?",
            ):
                return

        self.root.destroy()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(
            """
System Tuneup GUI v2.1.0

Запуск:
  python3 tuneup_gui.py
  python3 tuneup_gui.py --dry-run

Опции:
  --dry-run   включить режим сухого прогона при старте
  --help      показать эту справку
"""
        )
        sys.exit(0)

    root = tk.Tk()
    app = TuneupApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()