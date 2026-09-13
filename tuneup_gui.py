#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Linux Tweaker v0.11
Графическая оболочка тюнинга Linux Mint / Ubuntu / Debian на Tkinter.
RU/EN, светлая/тёмная тема, детект применённых настроек,
откат, бэкапы, mount-опции, симлинки compatdata для Steam, отладочный лог.
"""
import sys, os, re, subprocess, time, shutil, glob, pwd, grp, threading, traceback
import queue
from tkinter import (Tk, Toplevel, Frame, Label, Button, Checkbutton, Entry,
                     Text, Canvas, Menu, StringVar, BooleanVar, DoubleVar,
                     IntVar, END, NORMAL, DISABLED, LEFT, RIGHT, TOP, BOTTOM,
                     X, Y, BOTH, NW, W, E, N, S, HORIZONTAL, VERTICAL, SUNKEN,
                     RAISED, FLAT, GROOVE, RIDGE, CENTER, messagebox,
                     simpledialog, filedialog)
from tkinter import ttk, scrolledtext

APP_NAME = "Linux Tweaker"
APP_VERSION = "0.11"
GITHUB_URL = "https://github.com/Prikolist2021/Linux-Tweaker"

# Файловые системы, которые понимают параметр commit= (для ext4-оптимизации)
COMMIT_OK_FS = {"ext2", "ext3", "ext4"}

THEMES = {
    "light": {"bg": "#f5f5f5", "panel": "#ffffff", "fg": "#1e1e1e", "gray": "#616161",
              "border": "#d0d0d0", "tab": "#e4e4e4", "tab_hover": "#d8d8d8",
              "accent": "#2e9e83", "accent2": "#268a72", "accent_fg": "#ffffff",
              "button": "#e4e4e4", "button_hover": "#d8d8d8", "button_dis": "#ececec",
              "fg_dis": "#9a9a9a", "entry": "#ffffff", "terminal": "#ffffff",
              "terminal_fg": "#1e1e1e", "sel": "#cde4f7", "scroll": "#b0b0b0",
              "row_hover": "#ececec", "green": "#2e7d32", "green_bg": "#e2f0e3",
              "gray_bg": "#e8e8e8", "red": "#c62828", "yellow": "#b26a00",
              "blue": "#1565c0", "orange": "#e65100"},
    "dark": {"bg": "#1e1e1e", "panel": "#252526", "fg": "#d4d4d4", "gray": "#9a9a9a",
             "border": "#3c3c3c", "tab": "#2d2d30", "tab_hover": "#38383d",
             "accent": "#4ec9b0", "accent2": "#3aa794", "accent_fg": "#10201c",
             "button": "#3a3d41", "button_hover": "#46494e", "button_dis": "#2d2d30",
             "fg_dis": "#6a6a6a", "entry": "#333333", "terminal": "#0c0c0c",
             "terminal_fg": "#d4d4d4", "sel": "#094771", "scroll": "#5a5a5a",
             "row_hover": "#2a2d2e", "green": "#4ec9b0", "green_bg": "#17352f",
             "gray_bg": "#2f2f2f", "red": "#f44747", "yellow": "#d7ba7d",
             "blue": "#569cd6", "orange": "#ce9178"},
}

OPTIONS_META = {
    "rsyslog": {
        "ru": ("Отключить rsyslog", "Отключает запись подробных журналов на диск. Экономит место и уменьшает износ SSD. Работает сразу.", "Логи системы", "запись журналов на диск"),
        "en": ("Disable rsyslog", "Stops writing detailed logs to disk. Saves space and SSD wear. Works immediately.", "System logs", "detailed rsyslog logging to disk")},
    "journald": {
        "ru": ("Логи в ОЗУ (journald)", "Переносит журнал системы в оперативную память и ограничивает его 50 МБ. Бережёт SSD. Работает сразу.", "Логи системы", "хранение журналов systemd в ОЗУ (50 МБ)"),
        "en": ("Logs in RAM (journald)", "Moves the system log to RAM and caps it at 50 MB. Saves SSD. Works immediately.", "System logs", "systemd journals stored in RAM (50 MB)")},
    "audit": {
        "ru": ("audit=0 (GRUB)", "Отключает фоновую запись каждого действия системы. Убирает лишнюю нагрузку. Нужна перезагрузка.", "Ядро и загрузка", "фоновая запись действий"),
        "en": ("audit=0 (GRUB)", "Stops background logging of every system action. Removes extra load. Needs reboot.", "Kernel & boot", "background action logging")},
    "raid": {
        "ru": ("raid=noautodetect (GRUB)", "Пропускает поиск RAID при загрузке, если его нет. Ускоряет включение. Нужна перезагрузка.", "Ядро и загрузка", "поиск RAID"),
        "en": ("raid=noautodetect (GRUB)", "Skips RAID probe at boot when you have none. Speeds up startup. Needs reboot.", "Kernel & boot", "RAID probe")},
    "nmi_watchdog": {
        "ru": ("nmi_watchdog=0 (GRUB)", "Отключает служебные прерывания отладки. Убирает микро-фризы в играх. Нужна перезагрузка.", "Ядро и загрузка", "прерывания отладки"),
        "en": ("nmi_watchdog=0 (GRUB)", "Disables debug interrupts. Removes micro-stutters in games. Needs reboot.", "Kernel & boot", "debug interrupts")},
    "corectrl": {
        "ru": ("CoreCtrl (Polkit)", "Разрешает управлять вентиляторами и частотами AMD без пароля. Работает сразу.", "Видеокарта и графика", "управление AMD без пароля"),
        "en": ("CoreCtrl (Polkit)", "Allows controlling AMD fans and clocks without a password. Works immediately.", "GPU & graphics", "AMD control without password")},
    "ppfeaturemask": {
        "ru": ("amdgpu.ppfeaturemask", "Открывает драйверу AMD полный контроль над питанием карты. Нужна перезагрузка.", "Видеокарта и графика", "контроль питания AMD"),
        "en": ("amdgpu.ppfeaturemask", "Gives the AMD driver full power control of the card. Needs reboot.", "GPU & graphics", "AMD power control")},
    "nvidia_modeset": {
        "ru": ("nvidia-drm.modeset=1 (GRUB)", "Включает корректный вывод NVIDIA для Wayland и переключения режимов. Нужна перезагрузка.", "Видеокарта и графика", "вывод NVIDIA"),
        "en": ("nvidia-drm.modeset=1 (GRUB)", "Enables proper NVIDIA output for Wayland and mode switching. Needs reboot.", "GPU & graphics", "NVIDIA output")},
    "vrr": {
        "ru": ("VRR/FreeSync", "Убирает разрывы картинки в играх на мониторе с FreeSync. Нужен перезаход в сеанс.", "Видеокарта и графика", "плавная картинка"),
        "en": ("VRR/FreeSync", "Removes screen tearing in games on a FreeSync monitor. Requires re-login.", "GPU & graphics", "smooth picture")},
    "radv": {
        "ru": ("RADV_PERFTEST=sam", "Даёт процессору доступ ко всей видеопамяти сразу. Небольшой прирост FPS. Нужен перезаход.", "Видеокарта и графика", "доступ ко всей видеопамяти"),
        "en": ("RADV_PERFTEST=sam", "Gives the CPU access to all VRAM at once. Small FPS gain. Requires re-login.", "GPU & graphics", "full VRAM access")},
    "mesa": {
        "ru": ("MESA_SHADER_CACHE=4G", "Увеличивает кэш шейдеров, игры меньше подтормаживают в первые минуты. Нужен перезаход.", "Видеокарта и графика", "кэш шейдеров"),
        "en": ("MESA_SHADER_CACHE=4G", "Enlarges the shader cache so games stutter less at start. Requires re-login.", "GPU & graphics", "shader cache")},
    "pipewire": {
        "ru": ("PipeWire (звук)", "Убирает треск и щелчки звука, увеличив буферы звукового сервера. Нужен перезаход в сеанс.", "Звук", "чистый звук"),
        "en": ("PipeWire (sound)", "Removes sound crackling by enlarging sound-server buffers. Requires re-login.", "Sound", "clean sound")},
    "bbr": {
        "ru": ("TCP BBR", "Ускоряет интернет и убирает задержки на нестабильных каналах. Работает сразу.", "Сеть", "быстрый интернет"),
        "en": ("TCP BBR", "Speeds up internet and cuts latency on unstable links. Works immediately.", "Network", "faster internet")},
    "swap": {
        "ru": ("Тюнинг swap", "Настраивает, как охотно система выгружает память в подкачку. Меньше обращений к диску. Работает сразу.", "Память и swap", "поведение подкачки"),
        "en": ("Swap tuning", "Sets how eagerly memory goes to swap. Fewer disk accesses. Works immediately.", "Memory & swap", "swap behaviour")},
    "zram": {
        "ru": ("zram-swap", "Создаёт сжатую память в ОЗУ вместо дискового swap. Ускоряет работу при нехватке памяти. Нужна перезагрузка.", "Память и swap", "сжатая память в ОЗУ"),
        "en": ("zram-swap", "Creates compressed memory in RAM instead of disk swap. Speeds up low-RAM use. Needs reboot.", "Memory & swap", "compressed RAM")},
    "zswap": {
        "ru": ("zswap (GRUB)", "Держит сжатую память в ОЗУ перед записью в swap. Меньше обращений к диску. Нужна перезагрузка.", "Память и swap", "сжатый кэш перед swap"),
        "en": ("zswap (GRUB)", "Keeps compressed memory in RAM before swap. Fewer disk accesses. Needs reboot.", "Memory & swap", "compressed cache before swap")},
    "thp": {
        "ru": ("Крупные блоки памяти (THP)", "Система может выдавать память крупными блоками (2 МБ) вместо мелких (4 КБ). Это ускоряет игры и программы. Значения: madvise — только по запросу (рекомендуется), always — всем подряд, never — выключено.", "Память и swap", "крупные блоки памяти"),
        "en": ("Large memory blocks (THP)", "The system can hand out memory in large 2 MB blocks instead of small 4 KB ones. This speeds up games and apps. Values: madvise — on request only (recommended), always — to everyone, never — off.", "Memory & swap", "large memory blocks")},
    "sysctl_cache": {
        "ru": ("Кэш VFS (sysctl)", "Дольше держит кэш файлов в памяти, файлы открываются быстрее. Работает сразу.", "Ядро и загрузка", "кэш файлов"),
        "en": ("VFS cache (sysctl)", "Keeps file cache in RAM longer so files open faster. Works immediately.", "Kernel & boot", "file cache")},
    "sysctl_numa": {
        "ru": ("Миграция NUMA (sysctl)", "Отключает перенос памяти между ядрами, убирает паузы в играх. Работает сразу.", "Ядро и загрузка", "перенос памяти"),
        "en": ("NUMA migration (sysctl)", "Stops memory moving between cores, removes game stalls. Works immediately.", "Kernel & boot", "memory moving")},
    "reisub": {
        "ru": ("REISUB (Magic SysRq)", "Даёт безопасную перезагрузку при полном зависании через Alt+PrtSc и клавиши R E I S U B. Работает сразу.", "Ядро и загрузка", "безопасная перезагрузка"),
        "en": ("REISUB (Magic SysRq)", "Enables safe reboot on full freeze via Alt+PrtSc and R E I S U B keys. Works immediately.", "Kernel & boot", "safe reboot")},
    "ntsync": {
        "ru": ("ntsync (модуль ядра)", "Ускоряет игры под Wine/Proton за счёт быстрой синхронизации потоков. Работает сразу (нужно ядро 6.14+).", "Игры и совместимость", "быстрые игры под Wine"),
        "en": ("ntsync (kernel module)", "Speeds up Wine/Proton games via faster thread sync. Works immediately (needs kernel 6.14+).", "Gaming & compatibility", "faster Wine games")},
    "ntfs3": {
        "ru": ("ntfs3 драйвер", "Включает быстрый драйвер NTFS-дисков вместо медленного. ВНИМАНИЕ: только если у вас есть NTFS-диски. Нужна перезагрузка.", "Диски и файловые системы", "быстрый NTFS"),
        "en": ("ntfs3 driver", "Enables the fast NTFS driver instead of the slow one. WARNING: only if you have NTFS disks. Needs reboot.", "Drives & filesystems", "fast NTFS")},
    "commit": {
        "ru": ("commit=NN (fstab, только ext3/ext4)", "Реже сбрасывает служебную информацию на диск, меньше износа SSD. Работает ТОЛЬКО на ext3/ext4 — для NTFS, FAT32, exFAT, btrfs, xfs параметр не поддерживается и приведёт к ошибке монтирования (система может упасть в emergency-режим). ВНИМАНИЕ: при сбое питания возможна потеря последних записей. Нужна перезагрузка.", "Диски и файловые системы", "реже запись на ext4"),
        "en": ("commit=NN (fstab, ext3/ext4 only)", "Flushes disk metadata less often, less SSD wear. Works ONLY on ext3/ext4 — NTFS, FAT32, exFAT, btrfs, xfs do not support it and will fail to mount (system may drop into emergency mode). WARNING: power loss may lose last writes. Needs reboot.", "Drives & filesystems", "less ext4 disk writing")},
    "aliases": {
        "ru": ("Команды в .bashrc", "Добавляет удобные команды терминала для обновления и очистки. Работает в новых терминалах.", "Удобство", "команды терминала"),
        "en": ("Commands in .bashrc", "Adds handy terminal commands for updating and cleaning. Works in new terminals.", "Convenience", "terminal commands")},
    "autoupdate": {
        "ru": ("Автообновления", "Сам обновляет систему и Flatpak по расписанию. ВНИМАНИЕ: отключите встроенное автообновление Mint. Работает сразу.", "Обновления", "автообновление по расписанию"),
        "en": ("Auto-updates", "Auto-updates system and Flatpak on schedule. WARNING: disable Mint's built-in auto-update. Works immediately.", "Updates", "scheduled auto-update")},
}

CAT_ORDER = {
    "ru": ["Видеокарта и графика", "Ядро и загрузка", "Логи системы", "Звук", "Сеть",
           "Память и swap", "Диски и файловые системы", "Игры и совместимость",
           "Удобство", "Обновления"],
    "en": ["GPU & graphics", "Kernel & boot", "System logs", "Sound", "Network",
           "Memory & swap", "Drives & filesystems", "Gaming & compatibility",
           "Convenience", "Updates"],
}

SERVICES_META = {
    "avahi-daemon.service": {"ru": "Поиск устройств в домашней сети: принтеров, телевизоров, Chromecast. Не нужен, если у вас нет сетевого принтера.", "en": "Finds devices on your home network: printers, TVs, Chromecast. Not needed without a network printer."},
    "avahi-daemon.socket": {"ru": "Сокет, который будит службу avahi при обращении из сети. Сам по себе бесполезен без службы avahi.", "en": "Socket that wakes the avahi service on network request. Useless on its own without the avahi service."},
    "cups-browsed.service": {"ru": "Ищет сетевые принтеры автоматически. Не нужен, если принтера нет или он подключён по USB.", "en": "Auto-discovers network printers. Not needed without a printer or with a USB printer."},
    "cups.service": {"ru": "Печать и сканирование. Не нужно, если у вас нет принтера или сканера.", "en": "Printing and scanning. Not needed without a printer or scanner."},
    "cups.socket": {"ru": "Сокет, который будит службу печати при обращении. Сам по себе бесполезен без службы cups.", "en": "Socket that wakes the print service on request. Useless on its own without the cups service."},
    "ModemManager.service": {"ru": "Работа с мобильными модемами через USB или сим-карту. Не нужна, если интернет по Wi-Fi или кабелю.", "en": "Handles mobile modems via USB or SIM. Not needed if internet is Wi-Fi or cable."},
    "openvpn.service": {"ru": "Встроенный VPN-сервер. Не нужен, если вы не поднимаете собственный VPN.", "en": "Built-in VPN server. Not needed unless you run your own VPN."},
    "lvm2-monitor.service": {"ru": "Следит за объединением дисков в один большой (LVM). Не нужен при обычной установке Mint/Ubuntu.", "en": "Watches disks joined into one big volume (LVM). Not needed on a standard Mint/Ubuntu install."},
    "switcheroo-control.service": {"ru": "Переключает встроенную и отдельную графику на ноутбуках. Не нужен на настольном ПК.", "en": "Switches integrated and discrete graphics on laptops. Not needed on a desktop."},
    "touchegg.service": {"ru": "Распознаёт жесты тачпада и сенсора. Не нужен на настольном ПК без сенсора.", "en": "Recognizes touchpad and touchscreen gestures. Not needed on a desktop without a touchscreen."},
    "zfs-zed.service": {"ru": "Следит за дисковыми массивами ZFS и предупреждает о проблемах. Не нужен без ZFS.", "en": "Watches ZFS disk arrays and warns on problems. Not needed without ZFS."},
    "kerneloops.service": {"ru": "Отправляет разработчикам отчёты о сбоях ядра. На домашнем ПК это лишняя нагрузка и трафик.", "en": "Sends kernel crash reports to developers. On a home PC this is extra load and traffic."},
}
SERVICES_ORDER = list(SERVICES_META.keys())

OPTION_FILES = {
    "rsyslog": ["/etc/systemd/system/rsyslog.service",
                "/lib/systemd/system/rsyslog.service"],
    "journald": ["/etc/systemd/journald.conf"],
    "audit": ["/etc/default/grub"],
    "raid": ["/etc/default/grub"],
    "nmi_watchdog": ["/etc/default/grub"],
    "corectrl": ["/etc/polkit-1/rules.d/90-corectrl.rules",
                 "/etc/polkit-1/localauthority/50-local.d/90-corectrl.pkla"],
    "ppfeaturemask": ["/etc/default/grub"],
    "nvidia_modeset": ["/etc/default/grub"],
    "vrr": ["/etc/X11/xorg.conf.d/20-amdgpu.conf"],
    "radv": ["/etc/environment"],
    "mesa": ["/etc/environment"],
    "pipewire": ["{home}/.config/pipewire/pipewire.conf.d/10-sound.conf"],
    "bbr": ["/etc/sysctl.d/99-bbr.conf"],
    "swap": ["/etc/sysctl.d/99-gaming-swap.conf"],
    "zram": ["/etc/systemd/zram-generator.conf"],
    "zswap": ["/etc/default/grub"],
    "thp": ["/etc/default/grub"],
    "sysctl_cache": ["/etc/sysctl.d/99-gaming-sysctl.conf"],
    "sysctl_numa": ["/etc/sysctl.d/99-gaming-sysctl.conf"],
    "reisub": ["/etc/sysctl.d/99-sysrq.conf"],
    "ntsync": ["/etc/modules-load.d/ntsync.conf"],
    "ntfs3": ["/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"],
    "commit": ["/etc/fstab"],
    "aliases": ["{home}/.bashrc"],
    "autoupdate": ["/etc/systemd/system/biweekly-upgrade.timer",
                   "/etc/systemd/system/biweekly-upgrade.service"],
}


def decode_bytes(v):
    return v.decode("utf-8", errors="replace") if isinstance(v, bytes) else str(v)


def cpu_model():
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "?"


def ram_total_gb():
    try:
        with open("/proc/meminfo", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    return int(line.split()[1]) / 1024.0 / 1024.0
    except Exception:
        pass
    return None


def desktop_name():
    d = (os.environ.get("XDG_CURRENT_DESKTOP", "") + " " +
         os.environ.get("DESKTOP_SESSION", "")).lower()
    for key, name in [("cinnamon", "Cinnamon"), ("xfce", "XFCE"), ("mate", "MATE"),
                      ("plasma", "KDE Plasma"), ("kde", "KDE Plasma"), ("gnome", "GNOME"),
                      ("lxqt", "LXQt"), ("lxde", "LXDE"), ("openbox", "Openbox"),
                      ("budgie", "Budgie"), ("pantheon", "Pantheon")]:
        if key in d:
            return name
    return os.environ.get("XDG_CURRENT_DESKTOP", "") or "?"


def detect_lang():
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "")
        if val:
            return "ru" if val.lower().startswith("ru") else "en"
    return "en"


def zram_generator_present():
    return any(os.path.exists(p) for p in (
        "/usr/lib/systemd/system-generators/zram-generator",
        "/lib/systemd/system-generators/zram-generator"))


def parse_mounts():
    items = []
    try:
        with open("/proc/mounts", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 4:
                    continue
                dev, mp, fstype, opts = parts[0], parts[1], parts[2], parts[3]
                if not dev.startswith("/dev/"):
                    continue
                if fstype not in ("ext2", "ext3", "ext4", "xfs", "btrfs",
                                  "f2fs", "ntfs", "ntfs3", "vfat", "exfat",
                                  "fuseblk"):
                    continue
                if "rw" not in opts.split(","):
                    continue
                items.append({"dev": dev, "mp": mp, "fstype": fstype})
    except Exception:
        pass
    return items


def find_steam_libraries(user_home):
    libs = []
    for vdf in (os.path.join(user_home, ".steam", "steam", "steamapps",
                             "libraryfolders.vdf"),
                os.path.join(user_home, ".local", "share", "Steam", "steamapps",
                             "libraryfolders.vdf")):
        if not os.path.isfile(vdf):
            continue
        try:
            with open(vdf, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = re.search(r'"path"\s+"([^"]+)"', line)
                    if m:
                        p = m.group(1).replace("\\\\", "/")
                        sa = os.path.join(p, "steamapps")
                        if os.path.isdir(sa) and sa not in libs:
                            libs.append(sa)
        except Exception:
            pass
    for pat in ("/media/*/Steam/steamapps", "/mnt/*/Steam/steamapps",
                "/run/media/*/*/Steam/steamapps"):
        for p in glob.glob(pat):
            if os.path.isdir(p) and p not in libs:
                libs.append(p)
    return libs


def lines_in(content):
    return content.splitlines()


def fs_supports_commit(fstype):
    """commit= понимают только ext2/ext3/ext4. Остальные — нет."""
    return (fstype or "").lower() in COMMIT_OK_FS
class SudoManager:
    """Обёртка над sudo: аутентификация, keepalive, запуск команд."""

    def __init__(self):
        self.prompt_password = None
        self.show_error = None
        self.authenticated = False
        self._keepalive = False

    def _cached(self):
        if os.geteuid() == 0:
            return True
        try:
            return subprocess.run(["sudo", "-n", "true"], capture_output=True,
                                  timeout=3).returncode == 0
        except Exception:
            return False

    def authenticate(self):
        if self._cached():
            self.authenticated = True
            self._start_keepalive()
            return True
        for attempt in range(1, 4):
            password = self.prompt_password(attempt) if self.prompt_password else None
            if password is None:
                return False
            if not password:
                continue
            try:
                res = subprocess.run(["sudo", "-S", "-v"],
                                     input=(password + "\n").encode(),
                                     capture_output=True, timeout=15)
                if res.returncode == 0:
                    self.authenticated = True
                    self._start_keepalive()
                    return True
                err = decode_bytes(res.stderr).strip()
                if self.show_error:
                    self.show_error(err)
            except Exception as e:
                if self.show_error:
                    self.show_error(str(e))
        return False

    def ensure(self):
        if self._cached():
            self.authenticated = True
            self._start_keepalive()
            return True
        return self.authenticate()

    def run(self, args, input=None):
        if os.geteuid() == 0:
            return subprocess.run(list(args), input=input,
                                  capture_output=True, timeout=180)
        if not self._cached():
            raise PermissionError("Sudo session expired. Press Apply again.")
        return subprocess.run(["sudo", "-n"] + list(args), input=input,
                              capture_output=True, timeout=180)

    def _start_keepalive(self):
        if self._keepalive:
            return
        self._keepalive = True

        def loop():
            while True:
                time.sleep(50)
                try:
                    if not self._cached():
                        break
                    subprocess.run(["sudo", "-n", "-v"], capture_output=True, timeout=5)
                except Exception:
                    pass
            self._keepalive = False
            self.authenticated = False
        threading.Thread(target=loop, daemon=True).start()


class SystemState:
    """Определение железа и окружения один раз при старте."""

    def __init__(self):
        self.gpu = "Unknown"
        self.gpu_model = ""
        self.has_raid = False
        self.has_swap = False
        self.swap_type = ""
        self.ntsync = False
        self.cinnamon = False
        self.has_flatpak = False
        self.user_name = "root"
        self.user_home = "/root"

    def detect(self):
        try:
            self.user_name = self._real_user()
        except Exception:
            self.user_name = "root"
        try:
            self.user_home = pwd.getpwnam(self.user_name).pw_dir
        except Exception:
            self.user_home = os.path.expanduser("~")
        try:
            res = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5)
            for raw in res.stdout.splitlines():
                line = raw.lower()
                if "vga" in line or "3d controller" in line or "display controller" in line:
                    if "amd" in line or "radeon" in line:
                        self.gpu = "AMD"
                    elif "nvidia" in line:
                        self.gpu = "NVIDIA"
                    elif "intel" in line:
                        self.gpu = "Intel"
                    else:
                        continue
                    desc = raw.split(": ", 1)[1] if ": " in raw else raw
                    cleaned = re.sub(r"^[^\[]*\[[^\]]*\]\s*", "", desc)
                    cleaned = re.sub(r"\(rev [^)]*\)", "", cleaned).strip()
                    self.gpu_model = cleaned or desc.strip()
                    break
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
            res = subprocess.run(["lsblk", "-n", "-o", "TYPE"], capture_output=True,
                                 text=True, timeout=5)
            if "raid" in res.stdout:
                self.has_raid = True
        except Exception:
            pass
        try:
            res = subprocess.run(["swapon", "--show=TYPE", "--noheadings"],
                                 capture_output=True, text=True, timeout=5)
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
        d = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        s = os.environ.get("DESKTOP_SESSION", "").lower()
        self.cinnamon = "cinnamon" in d or s == "cinnamon"
        self.has_flatpak = bool(shutil.which("flatpak"))

    def _real_user(self):
        for var in ("SUDO_USER", "PKEXEC_USER"):
            v = os.environ.get(var)
            if v and v != "root":
                return v
        if os.getuid() != 0:
            return pwd.getpwuid(os.getuid()).pw_name
        v = os.environ.get("USER")
        if v and v != "root":
            return v
        try:
            for pw in pwd.getpwall():
                if pw.pw_uid >= 1000 and pw.pw_name not in ("nobody", "nfsnobody"):
                    if os.path.isdir(pw.pw_dir) and pw.pw_dir.startswith("/home/"):
                        return pw.pw_name
            for pw in pwd.getpwall():
                if pw.pw_uid >= 1000 and pw.pw_name not in ("nobody", "nfsnobody"):
                    return pw.pw_name
        except Exception:
            pass
        return "root"


class SystemOps:
    """Все прикладные операции: применение и откат твиков."""

    def __init__(self, sudo, state, log, dry_run):
        self.sudo = sudo
        self.state = state
        self.log = log
        self.dry_run = dry_run
        self.grub_changed = False
        self.mount_items = []
        # разделы, к которым разрешено применять commit=
        # (заполняется из UI; по умолчанию — только ext2/3/4)
        self.commit_targets = []
        self.backup_dir = os.path.join(state.user_home, "system-tuneup-backups")

    # ─── бэкапы и файловые операции ─────────────────────────────────────
    def backup_file(self, path):
        if self.dry_run:
            return
        try:
            if not self.path_exists(path):
                return
            content = self.read_file(path)
            if content is None:
                return
            os.makedirs(self.backup_dir, exist_ok=True)
            safe = path.lstrip("/").replace("/", "_")
            bp = os.path.join(self.backup_dir, safe + ".bak")
            with open(bp, "w", encoding="utf-8") as f:
                f.write(content)
            if self.state.user_name and self.state.user_name != "root":
                try:
                    pw = pwd.getpwnam(self.state.user_name)
                    os.chown(bp, pw.pw_uid, pw.pw_gid)
                except Exception:
                    pass
            self.log("[BACKUP] %s" % os.path.basename(bp), "info")
        except Exception as e:
            self.log("[WARN] backup %s: %s" % (path, e), "warning")

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

    def path_exists(self, path):
        if os.path.exists(path):
            return True
        try:
            return subprocess.run(["sudo", "-n", "test", "-e", path],
                                  capture_output=True, timeout=3).returncode == 0
        except Exception:
            return False

    def read_file(self, path):
        if not self.path_exists(path):
            return ""
        try:
            res = subprocess.run(["sudo", "-n", "cat", path], capture_output=True, timeout=5)
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
            self.log("[DRY RUN] write: %s" % path, "warning")
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
            self.log("Write error %s: %s" % (path, e), "error")
            return False
        if res.returncode != 0:
            self.log("Cannot write %s" % path, "error")
            return False
        if chmod:
            self.sudo_run(["chmod", chmod, path], ignore_error=True)
        if owner:
            self.sudo_run(["chown", owner, path], ignore_error=True)
        return True

    def ensure_line(self, path, line, pattern, chmod="644", mkdir=False):
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
        self.backup_file(path)
        return self.write_file(path, "\n".join(new_lines) + "\n",
                               chmod=chmod, mkdir=mkdir, backup=False)

    # ─── systemd-юниты ──────────────────────────────────────────────────
    def unit_exists(self, name):
        try:
            res = subprocess.run(["systemctl", "list-unit-files", name,
                                  "--no-legend", "--no-pager"],
                                 capture_output=True, timeout=5)
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
                                 capture_output=True, timeout=5)
            return decode_bytes(res.stdout).strip() or "unknown"
        except Exception:
            return "unknown"

    def service_active(self, name):
        try:
            res = subprocess.run(["systemctl", "is-active", name],
                                 capture_output=True, timeout=5)
            return decode_bytes(res.stdout).strip() or "unknown"
        except Exception:
            return "unknown"

    def _spices(self):
        if not self.state.cinnamon:
            return False
        if shutil.which("cinnamon-spice-updater"):
            return True
        return os.path.exists("/usr/bin/cinnamon-spice-updater")

    # ─── GRUB ───────────────────────────────────────────────────────────
    def add_grub_params(self, params):
        if self.dry_run:
            self.log("[DRY RUN] GRUB add: " + " ".join(params), "warning")
            return True
        path = "/etc/default/grub"
        content = self.read_file(path)
        if content is None:
            self.log("Cannot read %s" % path, "error")
            return False
        lines, found, changed = [], False, False
        for line in lines_in(content):
            m = re.match(r"^\s*GRUB_CMDLINE_LINUX_DEFAULT=(.*)$", line)
            if m:
                found = True
                raw = m.group(1).strip().strip('"').strip("'")
                parts = [p for p in raw.split() if p]
                orig = parts.copy()
                parts += [x for x in params if x not in parts]
                if parts != orig:
                    lines.append('GRUB_CMDLINE_LINUX_DEFAULT="' + " ".join(parts) + '"')
                    changed = True
                else:
                    lines.append(line)
            else:
                lines.append(line)
        if not found:
            lines.append('GRUB_CMDLINE_LINUX_DEFAULT="' + " ".join(params) + '"')
            changed = True
        if not changed:
            self.log("GRUB already has params", "info")
            return True
        self.backup_file(path)
        if self.write_file(path, "\n".join(lines) + "\n", backup=False):
            self.grub_changed = True
            self.log("GRUB: params added", "success")
            return True
        return False

    def _grub_set_param(self, token):
        if self.dry_run:
            self.log("[DRY RUN] GRUB set: %s" % token, "warning")
            return True
        path = "/etc/default/grub"
        content = self.read_file(path)
        if content is None:
            self.log("Cannot read %s" % path, "error")
            return False
        key = token.split("=")[0]
        lines, changed = [], False
        for line in lines_in(content):
            m = re.match(r"^\s*GRUB_CMDLINE_LINUX_DEFAULT=(.*)$", line)
            if m:
                raw = m.group(1).strip().strip('"').strip("'")
                parts = [p for p in raw.split() if p and not p.startswith(key + "=")]
                if token not in parts:
                    parts.append(token)
                newl = 'GRUB_CMDLINE_LINUX_DEFAULT="' + " ".join(parts) + '"'
                if newl != line.strip():
                    changed = True
                lines.append(newl)
            else:
                lines.append(line)
        if not changed:
            self.log("GRUB already has %s" % token, "info")
            return True
        self.backup_file(path)
        if self.write_file(path, "\n".join(lines) + "\n", backup=False):
            self.grub_changed = True
            self.log("GRUB: %s set" % token, "success")
            return True
        return False

    def _remove_grub_params(self, params):
        if self.dry_run:
            self.log("[DRY RUN] GRUB remove: " + " ".join(params), "warning")
            return True
        path = "/etc/default/grub"
        content = self.read_file(path)
        if not content:
            self.log("GRUB not found", "warning")
            return False
        new_lines, changed = [], False
        for line in lines_in(content):
            m = re.match(r"^\s*GRUB_CMDLINE_LINUX_DEFAULT=(.*)$", line)
            if m:
                raw = m.group(1).strip().strip('"').strip("'")
                parts = [p for p in raw.split() if p and p not in params]
                new_lines.append('GRUB_CMDLINE_LINUX_DEFAULT="' + " ".join(parts) + '"')
                changed = True
            else:
                new_lines.append(line)
        if not changed:
            self.log("GRUB params not found", "info")
            return True
        self.backup_file(path)
        if self.write_file(path, "\n".join(new_lines) + "\n", backup=False):
            self.grub_changed = True
            self.log("✓ GRUB params removed", "success")
            return True
        return False

    def finalize_grub(self):
        if not self.grub_changed:
            return
        if self.dry_run:
            self.log("[DRY RUN] update-grub", "warning")
            return
        ug = shutil.which("update-grub")
        if not ug and os.path.exists("/usr/sbin/update-grub"):
            ug = "/usr/sbin/update-grub"
        gm = shutil.which("grub-mkconfig")
        if not gm and os.path.exists("/usr/sbin/grub-mkconfig"):
            gm = "/usr/sbin/grub-mkconfig"
        if ug:
            self.sudo_run([ug], ok_msg="GRUB updated", err_msg="update-grub failed")
        elif gm:
            self.sudo_run([gm, "-o", "/boot/grub/grub.cfg"],
                          ok_msg="GRUB updated", err_msg="grub-mkconfig failed")
        else:
            self.log("update-grub / grub-mkconfig not found", "warning")
        self.grub_changed = False
    # ─── apply ──────────────────────────────────────────────────────────
    def apply_rsyslog(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] disable + mask rsyslog", "warning"); return True
        if self.service_enabled("rsyslog.service") in ("disabled", "masked", "not-found"):
            self.log("rsyslog already disabled", "info"); return True
        ok1 = self.sudo_run(["systemctl", "disable", "--now", "rsyslog"], ignore_error=True)
        ok2 = self.sudo_run(["systemctl", "mask", "rsyslog"], ignore_error=True)
        if ok1 or ok2:
            self.log("✓ rsyslog disabled", "success"); return True
        self.log("Cannot disable rsyslog", "error"); return False

    def apply_journald(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] journald volatile 50M", "warning"); return True
        path = "/etc/systemd/journald.conf"
        if not self.path_exists(path):
            self.log("journald.conf missing, will create with [Journal]", "info")
            content = ""
        else:
            content = self.read_file(path)
            if content is None:
                self.log("Cannot read %s" % path, "error")
                return False
        if (re.search(r"^\s*Storage\s*=\s*volatile\s*$", content, re.M)
                and re.search(r"^\s*RuntimeMaxUse\s*=\s*50M\s*$", content, re.M)):
            self.log("journald already configured", "info"); return True
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
        self.backup_file(path)
        if not self.write_file(path, "\n".join(out) + "\n", backup=False):
            return False
        self.sudo_run(["systemctl", "restart", "systemd-journald"], ignore_error=True)
        self.sudo_run(["journalctl", "--vacuum-size=200M", "--vacuum-time=1months"],
                      ignore_error=True)
        self.log("✓ journald → volatile (50M)", "success"); return True

    def apply_audit(self, params=None):
        return self.add_grub_params(["audit=0"])

    def apply_raid(self, params=None):
        if self.state.has_raid:
            self.log("RAID detected, skipping", "warning"); return True
        return self.add_grub_params(["raid=noautodetect"])

    def apply_nmi_watchdog(self, params=None):
        return self.add_grub_params(["nmi_watchdog=0"])

    def _polkit_is_new(self):
        try:
            res = subprocess.run(["pkaction", "--version"],
                                 capture_output=True, text=True, timeout=5)
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
            self.log("Bad group name: %s" % group, "error"); return False
        if self.dry_run:
            self.log("[DRY RUN] CoreCtrl polkit rule for %s" % group, "warning")
            return True
        try:
            grp.getgrnam(group)
        except KeyError:
            self.log("Group not found: %s" % group, "error"); return False
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
            self.log("✓ CoreCtrl configured for %s (%s)"
                     % (group, os.path.basename(path)), "success")
            return True
        return False

    def apply_ppfeaturemask(self, params=None):
        return self.add_grub_params(["amdgpu.ppfeaturemask=0xffffffff"])

    def apply_nvidia_modeset(self, params=None):
        return self.add_grub_params(["nvidia-drm.modeset=1"])

    def apply_vrr(self, params=None):
        if self.state.gpu not in ("AMD", "Unknown"):
            self.log("VRR is AMD-only", "warning"); return True
        if self.dry_run:
            self.log("[DRY RUN] VRR config", "warning"); return True
        content = ('Section "Device"\n    Identifier "AMD"\n    Driver "amdgpu"\n'
                   '    Option "VariableRefresh" "true"\nEndSection\n')
        if self.write_file("/etc/X11/xorg.conf.d/20-amdgpu.conf", content,
                           chmod="644", mkdir=True):
            self.log("✓ VRR/FreeSync enabled", "success"); return True
        return False

    def apply_radv(self, params=None):
        return self.ensure_line("/etc/environment", "RADV_PERFTEST=sam",
                                r"^\s*RADV_PERFTEST=.*")

    def apply_mesa(self, params=None):
        return self.ensure_line("/etc/environment", "MESA_SHADER_CACHE_MAX_SIZE=4G",
                                r"^\s*MESA_SHADER_CACHE_MAX_SIZE=.*")

    def apply_pipewire(self, params=None):
        d = os.path.join(self.state.user_home, ".config", "pipewire", "pipewire.conf.d")
        path = os.path.join(d, "10-sound.conf")
        if self.dry_run:
            self.log("[DRY RUN] PipeWire config: %s" % path, "warning"); return True
        content = ("context.properties = {\n    default.clock.min-quantum = 512\n"
                   "    default.clock.quantum = 4096\n"
                   "    default.clock.max-quantum = 8192\n}\n")
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            self.log("Cannot create %s: %s" % (d, e), "error")
            return False
        if not self.write_file(path, content, chmod="644"):
            return False
        if self.state.user_name and self.state.user_name != "root":
            self.sudo_run(["chown", "-R",
                           "%s:%s" % (self.state.user_name, self.state.user_name),
                           os.path.join(self.state.user_home, ".config", "pipewire")],
                          ignore_error=True)
        self.log("✓ PipeWire configured", "success"); return True

    def apply_bbr(self, params=None):
        path = "/etc/sysctl.d/99-bbr.conf"
        content = "net.core.default_qdisc=fq\nnet.ipv4.tcp_congestion_control=bbr\n"
        if not self.write_file(path, content, chmod="644", mkdir=True):
            return False
        self.sudo_run(["modprobe", "tcp_bbr"], ignore_error=True)
        if not os.path.exists("/sys/module/tcp_bbr"):
            self.log("tcp_bbr not available in this kernel", "warning")
        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        self.log("✓ TCP BBR enabled", "success"); return True

    def apply_swap(self, params=None):
        params = params or {}
        if not self.state.has_swap:
            self.log("No swap found, skipping", "warning"); return True
        val = params.get("swap_value", "").strip()
        if not val:
            val = "150" if self.state.swap_type == "zram" else "10"
        try:
            iv = int(val)
            if iv < 0 or iv > 200:
                raise ValueError
        except ValueError:
            self.log("Bad swappiness: %s (0-200)" % val, "error"); return False
        if self.dry_run:
            self.log("[DRY RUN] swappiness=%d" % iv, "warning"); return True
        path = "/etc/sysctl.d/99-gaming-swap.conf"
        ex = self.read_file(path)
        if ex and re.search(r"^vm\.swappiness=%d$" % iv, ex, re.M):
            self.log("swappiness already %d" % iv, "info"); return True
        if not self.write_file(path, "vm.swappiness=%d\n" % iv, chmod="644", mkdir=True):
            return False
        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        self.log("✓ swappiness=%d" % iv, "success"); return True

    def apply_zram(self, params=None):
        if not zram_generator_present():
            self.log("zram-generator not installed", "warning"); return False
        path = "/etc/systemd/zram-generator.conf"
        content = "[zram0]\nzram-size = ram-size / 2\ncompression-algorithm = zstd\n"
        if self.write_file(path, content, chmod="644", mkdir=True):
            self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
            self.log("✓ zram configured (reboot to activate)", "success"); return True
        return False

    def apply_zswap(self, params=None):
        pl = ["zswap.enabled=1", "zswap.compressor=zstd"]
        if os.path.exists("/sys/module/z3fold"):
            pl.append("zswap.zpool=z3fold")
        return self.add_grub_params(pl)

    def apply_thp(self, params=None):
        params = params or {}
        val = params.get("thp_value", "madvise")
        return self._grub_set_param("transparent_hugepage=%s" % val)

    def _sysctl_set(self, key, val):
        if self.dry_run:
            self.log("[DRY RUN] %s=%s" % (key, val), "warning"); return True
        path = "/etc/sysctl.d/99-gaming-sysctl.conf"
        content = self.read_file(path) or ""
        rx = re.compile(r"^\s*%s\s*=" % re.escape(key))
        out, replaced = [], False
        for l in lines_in(content):
            if rx.match(l):
                out.append("%s=%s" % (key, val)); replaced = True
            else:
                out.append(l)
        if not replaced:
            out.append("%s=%s" % (key, val))
        self.backup_file(path)
        if not self.write_file(path, "\n".join(out) + "\n", chmod="644",
                               mkdir=True, backup=False):
            return False
        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        self.log("✓ %s=%s" % (key, val), "success"); return True

    def _sysctl_del(self, key, default):
        if self.dry_run:
            self.log("[DRY RUN] remove %s" % key, "warning"); return True
        path = "/etc/sysctl.d/99-gaming-sysctl.conf"
        content = self.read_file(path) or ""
        rx = re.compile(r"^\s*%s\s*=" % re.escape(key))
        old = lines_in(content)
        out = [l for l in old if not rx.match(l)]
        if len(out) == len(old):
            self.log("%s not found in %s" % (key, path), "info")
        else:
            self.backup_file(path)
            self.write_file(path, "\n".join(out) + "\n", backup=False)
        self.sudo_run(["sysctl", "-w", "%s=%s" % (key, default)], ignore_error=True)
        self.log("✓ %s reverted to %s" % (key, default), "success"); return True

    def apply_sysctl_cache(self, params=None):
        return self._sysctl_set("vm.vfs_cache_pressure", "50")

    def apply_sysctl_numa(self, params=None):
        return self._sysctl_set("kernel.numa_balancing", "0")

    def apply_reisub(self, params=None):
        path = "/etc/sysctl.d/99-sysrq.conf"
        content = "kernel.sysrq=244\n"
        if self.write_file(path, content, chmod="644", mkdir=True):
            self.sudo_run(["sysctl", "-p", path], ignore_error=True)
            self.log("✓ Magic SysRq (REISUB) enabled (kernel.sysrq=244)", "success")
            return True
        return False

    def apply_ntsync(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] ntsync modules-load", "warning"); return True
        if self.state.ntsync:
            self.log("ntsync already available", "info"); return True
        if not self.write_file("/etc/modules-load.d/ntsync.conf", "ntsync\n",
                               chmod="644", mkdir=True):
            return False
        self.sudo_run(["modprobe", "ntsync"], ignore_error=True)
        self.log("✓ ntsync autoloaded", "success"); return True

    def apply_ntfs3(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] ntfs3 unlock", "warning"); return True
        path = "/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"
        if not self.path_exists(path):
            self.log("mint-blacklist-ntfs3.conf not found", "warning")
            return True
        content = self.read_file(path)
        if content is None:
            self.log("Cannot read %s" % path, "error"); return False
        if not content.strip():
            self.log("File is empty, nothing to unlock", "info"); return True
        if re.search(r"^\s*#\s*blacklist\s+ntfs3\s*$", content, re.M):
            self.log("ntfs3 already unlocked", "info"); return True
        if re.search(r"^\s*blacklist\s+ntfs3\s*$", content, re.M):
            new = re.sub(r"^\s*blacklist\s+ntfs3\s*$", "# blacklist ntfs3",
                         content, flags=re.M)
            self.backup_file(path)
            if self.write_file(path, new, backup=False):
                self.log("✓ ntfs3 unlocked", "success"); return True
            return False
        self.log("blacklist ntfs3 not found", "warning"); return True

    # ─── fstab: mount-опции и commit (безопасно, только ext2/3/4) ───────
    def _uuid_of(self, dev):
        try:
            res = subprocess.run(["lsblk", "-no", "UUID", dev],
                                 capture_output=True, text=True, timeout=5)
            return res.stdout.strip() if res.returncode == 0 else ""
        except Exception:
            return ""

    def _fstab_find(self, lines, mp, uuid):
        for i, line in enumerate(lines):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            f = s.split()
            if len(f) < 4:
                continue
            if f[1] == mp:
                return i, f
            if uuid and f[0].lower() == ("uuid=%s" % uuid).lower():
                return i, f
        return None, None

    def _dev_of(self, mp):
        return next((it["dev"] for it in self.mount_items
                     if mp in it.get("mps", [])), None)

    def _fstype_of_mp(self, mp):
        for it in self.mount_items:
            if mp in it.get("mps", []):
                return it.get("fstype", "").lower()
        return ""

    def _mount_opts_edit(self, mp, add=True):
        path = "/etc/fstab"
        content = self.read_file(path)
        if not content:
            self.log("Cannot read /etc/fstab", "error"); return False
        dev = self._dev_of(mp)
        uuid = self._uuid_of(dev) if dev else ""
        lines = lines_in(content)
        idx, parts = self._fstab_find(lines, mp, uuid)
        if idx is None:
            self.log("%s not found in fstab — skipped" % mp, "warning")
            return False
        opts = [o for o in parts[3].split(",") if not o.startswith("commit=")]
        if add:
            if "noatime" not in opts:
                opts.append("noatime")
        else:
            opts = [o for o in opts if o not in ("noatime", "nodiratime")]
        parts[3] = ",".join(opts)
        lines[idx] = "\t".join(parts)
        self.backup_file(path)
        if not self.write_file(path, "\n".join(lines) + "\n", backup=False):
            return False
        if add:
            self.log("✓ fstab %s: +noatime (after reboot)" % mp, "success")
        else:
            self.log("✓ fstab %s: noatime removed (after reboot)" % mp, "success")
        return True

    def _mount_commit_edit(self, mp, val, add=True):
        """Правка commit= в /etc/fstab. Только для ext2/3/4."""
        path = "/etc/fstab"
        fstype = self._fstype_of_mp(mp)
        if add and not fs_supports_commit(fstype):
            self.log("Skipped %s (%s): commit= is only valid for ext2/3/4"
                     % (mp, fstype or "unknown"), "warning")
            return False
        content = self.read_file(path)
        if not content:
            self.log("Cannot read /etc/fstab", "error"); return False
        dev = self._dev_of(mp)
        uuid = self._uuid_of(dev) if dev else ""
        lines = lines_in(content)
        idx, parts = self._fstab_find(lines, mp, uuid)
        if idx is None:
            self.log("%s not found in fstab — skipped" % mp, "warning")
            return False
        opts = [o for o in parts[3].split(",") if not o.startswith("commit=")]
        if add:
            opts.append("commit=%s" % val)
        parts[3] = ",".join(opts)
        lines[idx] = "\t".join(parts)
        self.backup_file(path)
        return self.write_file(path, "\n".join(lines) + "\n", backup=False)

    def apply_mount_opts(self, mps):
        if self.dry_run:
            for mp in mps:
                self.log("[DRY RUN] fstab %s +noatime" % mp, "warning")
            return True
        ok = True
        for mp in mps:
            ok = self._mount_opts_edit(mp, True) and ok
        return ok

    def rollback_mount_opts(self, mps):
        if self.dry_run:
            for mp in mps:
                self.log("[DRY RUN] fstab %s -noatime" % mp, "warning")
            return True
        ok = True
        for mp in mps:
            ok = self._mount_opts_edit(mp, False) and ok
        return ok

    def apply_commit(self, params=None):
        """commit=NN применяется ТОЛЬКО к выбранным пользователем разделам
        с ФС ext2/ext3/ext4. Разделы с другими ФС пропускаются."""
        params = params or {}
        val = str(params.get("commit_value", "60")).strip() or "60"
        try:
            iv = int(val)
            if iv < 1 or iv > 3600:
                raise ValueError
        except ValueError:
            self.log("Bad commit value: %s (1-3600)" % val, "error")
            return False
        val = str(iv)
        targets = list(self.commit_targets)
        if not targets:
            self.log("commit=: no ext2/3/4 partitions selected — nothing to do",
                     "warning")
            return True
        if self.dry_run:
            for mp in targets:
                self.log("[DRY RUN] fstab %s commit=%s" % (mp, val), "warning")
            return True
        ok = True
        applied_any = False
        for mp in targets:
            fstype = self._fstype_of_mp(mp)
            if not fs_supports_commit(fstype):
                self.log("Skipped %s (%s): commit= unsupported here"
                         % (mp, fstype or "unknown"), "warning")
                continue
            if self._mount_commit_edit(mp, val, True):
                applied_any = True
            else:
                ok = False
        if applied_any and ok:
            self.log("✓ fstab commit=%s applied to %d partition(s) (after reboot)"
                     % (val, len(targets)), "success")
        return ok

    def rollback_commit(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] fstab remove commit", "warning"); return True
        targets = list(self.commit_targets)
        if not targets:
            self.log("commit=: no partitions selected for rollback", "warning")
            return True
        ok = True
        for mp in targets:
            if self._mount_commit_edit(mp, "", False):
                pass
            else:
                ok = False
        if ok:
            self.log("✓ fstab commit removed from selected partitions "
                     "(after reboot)", "success")
        return ok

    def _commit_applied(self):
        """Проверяет, стоит ли commit= хотя бы на одном ext2/3/4-разделе
        из списка commit_targets (или на любом ext2/3/4, если список пуст)."""
        try:
            with open("/etc/fstab", "r", encoding="utf-8", errors="replace") as f:
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

    # ─── Steam compatdata ───────────────────────────────────────────────
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
                    self.log("Skipped: %s exists as data directory" % dst, "warning")
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

    # ─── .bashrc: команды ───────────────────────────────────────────────
    def apply_aliases(self, params=None):
        bashrc = os.path.join(self.state.user_home, ".bashrc")
        if self.dry_run:
            self.log("[DRY RUN] add commands to .bashrc", "warning"); return True
        if not self.path_exists(bashrc):
            self.log(".bashrc not found: %s" % bashrc, "error"); return False
        content = self.read_file(bashrc)
        if content is None:
            self.log("Cannot read .bashrc", "error"); return False
        sm = "# >>> system-tuneup commands >>>"
        em = "# <<< system-tuneup commands <<<"
        without, skip = [], False
        for line in lines_in(content):
            if line.strip() == sm:
                skip = True; continue
            if line.strip() == em:
                skip = False; continue
            if not skip:
                without.append(line)
        names = ["upd", "upgr", "spices", "update_all", "inst", "remove", "search",
                 "info", "clean", "space", "fix", "mem", "serv", "update_time"]
        np_ = "|".join(names)
        alias_rx = re.compile(r"^\s*alias\s+(" + np_ + r")=")
        func_rx = re.compile(r"^\s*(" + np_ + r")\s*\(\)\s*\{")
        cleaned, skip_fn = [], False
        for line in without:
            if alias_rx.match(line):
                continue
            if func_rx.match(line):
                if "}" in line:
                    continue
                skip_fn = True; continue
            if skip_fn:
                if line.strip().startswith("}"):
                    skip_fn = False
                continue
            if "system-tuneup" in line and line.strip().startswith("#"):
                continue
            cleaned.append(line)
        spices, has_fp = self._spices(), self.state.has_flatpak
        block = [sm, "# system-tuneup commands", ""]
        block += ["upd() {", '    echo "APT update..."', "    sudo apt update", "}", ""]
        block += ["upgr() {", '    echo "APT upgrade..."', "    sudo apt full-upgrade"]
        if has_fp:
            block.append('    echo "Flatpak update..."')
            if spices:
                block.append("    flatpak update && cinnamon-spice-updater --update-all")
            else:
                block.append("    flatpak update")
        block += ["}", ""]
        if spices:
            block += ["spices() {", '    echo "Cinnamon spices update..."',
                      "    cinnamon-spice-updater --update-all", "}", ""]
        block += ["update_all() {", "    sudo apt update && sudo apt full-upgrade -y"]
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
        block += ["clean() {", "    sudo apt autoremove -y && sudo apt autoclean && sudo apt clean", "}", ""]
        block += ["space() {", "    df -h /", "}", ""]
        block += ["fix() {", "    sudo apt --fix-broken install -y", "    sudo dpkg --configure -a", "}", ""]
        block += ["mem() {", "    sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches' && free -h", "}", ""]
        block += ["serv() {", "    systemctl list-unit-files --type=service | less", "}", ""]
        block += ["update_time() {",
                  "    systemctl list-timers --no-pager 2>/dev/null | "
                  'grep -E "NEXT|upgrade|update|apt" || echo "No timers"', "}", ""]
        block.append(em)
        while cleaned and cleaned[-1].strip() == "":
            cleaned.pop()
        new = "\n".join(cleaned + [""] + block) + "\n"
        if new == content:
            self.log("Commands already added", "info"); return True
        self.backup_file(bashrc)
        if not self.write_file(bashrc, new, backup=False):
            return False
        if self.state.user_name and self.state.user_name != "root":
            self.sudo_run(["chown", "%s:%s" % (self.state.user_name, self.state.user_name),
                           bashrc], ignore_error=True)
        self.log("✓ commands added to .bashrc (source ~/.bashrc for new cmds)", "success")
        return True

    # ─── автообновления ─────────────────────────────────────────────────
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
                self.log("Auto-update timer not found", "info"); return True
            if self.dry_run:
                self.log("[DRY RUN] remove timer", "warning"); return True
            self.sudo_run(["systemctl", "disable", "--now", "biweekly-upgrade.timer"],
                          ignore_error=True)
            self.sudo_run(["rm", "-f", svc, tmr], ignore_error=True)
            self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
            self.log("Auto-update timer removed", "success"); return True
        if sched not in table:
            self.log("Unknown schedule: %s" % sched, "error"); return False
        onc, desc = table[sched]
        spices = self._spices()
        cmd = "apt update && apt full-upgrade -y"
        if self.state.has_flatpak:
            cmd += " && flatpak update -y"
        if spices:
            cmd += " && cinnamon-spice-updater --update-all"
        svc_c = ("[Unit]\nDescription=System upgrade (%s)\n\n[Service]\nType=oneshot\n"
                 "ExecStartPre=/bin/sleep 600\nExecStart=/usr/bin/bash -c \"%s\"\n"
                 "User=root\n" % (desc, cmd))
        tmr_c = ("[Unit]\nDescription=System upgrade timer (%s)\n\n[Timer]\n"
                 "OnCalendar=%s\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n"
                 % (desc, onc))
        ex_svc = self.read_file(svc) or ""
        ex_tmr = self.read_file(tmr) or ""
        if exists and ex_svc == svc_c and ex_tmr == tmr_c:
            self.log("Timer already configured: %s" % desc, "info")
            if self.service_enabled("biweekly-upgrade.timer") != "enabled" and not self.dry_run:
                self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
                self.sudo_run(["systemctl", "enable", "--now", "biweekly-upgrade.timer"],
                              ignore_error=True)
            return True
        if self.dry_run:
            self.log("[DRY RUN] create timer: %s" % desc, "warning"); return True
        if self.service_enabled("mintupdate-automation-upgrade.timer") == "enabled":
            self.log("Disabling mintupdate-automation-upgrade.timer", "info")
            self.sudo_run(["systemctl", "disable", "--now",
                           "mintupdate-automation-upgrade.timer"], ignore_error=True)
        if not self.write_file(svc, svc_c, chmod="644"):
            return False
        if not self.write_file(tmr, tmr_c, chmod="644"):
            return False
        self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
        self.sudo_run(["systemctl", "enable", "--now", "biweekly-upgrade.timer"],
                      ok_msg="✓ timer created: %s" % desc,
                      err_msg="Cannot enable timer")
        return True
    # ─── rollback ───────────────────────────────────────────────────────
    def _rm(self, path):
        if self.dry_run:
            self.log("[DRY RUN] rm %s" % path, "warning"); return True
        if not self.path_exists(path):
            self.log("File not found: %s" % path, "info"); return True
        return self.sudo_run(["rm", "-f", path], ok_msg="✓ removed %s" % path)

    def _remove_line(self, path, pattern):
        if self.dry_run:
            self.log("[DRY RUN] %s: remove %s" % (path, pattern), "warning")
            return True
        content = self.read_file(path)
        if not content:
            self.log("File not found: %s" % path, "info"); return True
        rx = re.compile(pattern)
        old = lines_in(content)
        new = [l for l in old if not rx.match(l.strip())]
        if len(new) == len(old):
            self.log("Line not found in %s" % path, "info"); return True
        self.backup_file(path)
        return self.write_file(path, "\n".join(new) + "\n", backup=False)

    def rollback_rsyslog(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] unmask + enable rsyslog", "warning"); return True
        self.sudo_run(["systemctl", "unmask", "rsyslog"], ignore_error=True)
        self.sudo_run(["systemctl", "enable", "--now", "rsyslog"],
                      ok_msg="✓ rsyslog re-enabled", ignore_error=True)
        return True

    def rollback_journald(self, params=None):
        path = "/etc/systemd/journald.conf"
        bak = os.path.join(self.backup_dir, "etc_systemd_journald.conf.bak")
        if self.path_exists(bak):
            c = self.read_file(bak)
            if c:
                self.write_file(path, c, backup=False)
                self.sudo_run(["systemctl", "restart", "systemd-journald"],
                              ignore_error=True)
                self.log("✓ journald restored from backup", "success"); return True
        self._remove_line(path, r"^\s*Storage\s*=")
        self._remove_line(path, r"^\s*RuntimeMaxUse\s*=")
        self.sudo_run(["systemctl", "restart", "systemd-journald"], ignore_error=True)
        self.log("✓ journald back to defaults", "success")
        return True

    def rollback_audit(self, params=None):
        return self._remove_grub_params(["audit=0"])

    def rollback_raid(self, params=None):
        return self._remove_grub_params(["raid=noautodetect"])

    def rollback_nmi_watchdog(self, params=None):
        return self._remove_grub_params(["nmi_watchdog=0"])

    def rollback_corectrl(self, params=None):
        self._rm("/etc/polkit-1/rules.d/90-corectrl.rules")
        self._rm("/etc/polkit-1/localauthority/50-local.d/90-corectrl.pkla")
        self.log("✓ CoreCtrl rule removed", "success"); return True

    def rollback_ppfeaturemask(self, params=None):
        return self._remove_grub_params(["amdgpu.ppfeaturemask=0xffffffff"])

    def rollback_nvidia_modeset(self, params=None):
        return self._remove_grub_params(["nvidia-drm.modeset=1"])

    def rollback_vrr(self, params=None):
        self._rm("/etc/X11/xorg.conf.d/20-amdgpu.conf")
        self.log("✓ VRR config removed", "success"); return True

    def rollback_radv(self, params=None):
        self._remove_line("/etc/environment", r"^\s*RADV_PERFTEST=.*")
        self.log("✓ RADV_PERFTEST removed", "success"); return True

    def rollback_mesa(self, params=None):
        self._remove_line("/etc/environment", r"^\s*MESA_SHADER_CACHE_MAX_SIZE=.*")
        self.log("✓ MESA cache removed", "success"); return True

    def rollback_pipewire(self, params=None):
        self._rm(os.path.join(self.state.user_home, ".config", "pipewire",
                              "pipewire.conf.d", "10-sound.conf"))
        self.log("✓ PipeWire config removed", "success"); return True

    def rollback_bbr(self, params=None):
        self._rm("/etc/sysctl.d/99-bbr.conf")
        self.sudo_run(["sysctl", "-w", "net.ipv4.tcp_congestion_control=cubic"],
                      ignore_error=True)
        return True

    def rollback_swap(self, params=None):
        self._rm("/etc/sysctl.d/99-gaming-swap.conf")
        self.sudo_run(["sysctl", "-w", "vm.swappiness=60"], ignore_error=True)
        self.log("✓ swappiness back to 60", "success"); return True

    def rollback_zram(self, params=None):
        self._rm("/etc/systemd/zram-generator.conf")
        self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
        return True

    def rollback_zswap(self, params=None):
        return self._remove_grub_params(["zswap.enabled=1", "zswap.compressor=zstd",
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
        self.log("✓ ntsync removed", "success"); return True

    def rollback_ntfs3(self, params=None):
        path = "/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"
        content = self.read_file(path)
        if not content:
            self.log("File not found: %s" % path, "info"); return True
        if re.search(r"^\s*blacklist\s+ntfs3\s*$", content, re.M):
            self.log("ntfs3 already blocked", "info"); return True
        new = re.sub(r"^\s*#\s*blacklist\s+ntfs3\s*$", "blacklist ntfs3",
                     content, flags=re.M)
        self.backup_file(path)
        if self.write_file(path, new, backup=False):
            self.log("✓ ntfs3 blocked again", "success"); return True
        return False

    def rollback_aliases(self, params=None):
        bashrc = os.path.join(self.state.user_home, ".bashrc")
        content = self.read_file(bashrc)
        if not content:
            self.log(".bashrc not found", "info"); return True
        sm = "# >>> system-tuneup commands >>>"
        em = "# <<< system-tuneup commands <<<"
        lines, skip = [], False
        for line in lines_in(content):
            if line.strip() == sm:
                skip = True; continue
            if line.strip() == em:
                skip = False; continue
            if not skip:
                lines.append(line)
        if len(lines) == len(lines_in(content)):
            self.log("Command block not found", "info"); return True
        self.backup_file(bashrc)
        if self.write_file(bashrc, "\n".join(lines) + "\n", backup=False):
            self.log("✓ commands removed from .bashrc", "success"); return True
        return False

    def rollback_autoupdate(self, params=None):
        return self.apply_autoupdate({"update_schedule": "Отключено"})


# ─── Длинные справки по твикам ───────────────────────────────────────────
OPTIONS_HELP = {
    "rsyslog": {
        "ru": "rsyslog — это программа, которая постоянно записывает подробные журналы системы в текстовые файлы на диске. Каждую секунду она дописывает туда события: запуск служб, ошибки, вход пользователей. На домашнем ПК эти файлы почти никто не читает, но диск получает постоянные операции записи.\n\nЕсли отключить rsyslog, диск перестанет получать эти лишние записи. Это особенно полезно на SSD, где каждая запись тратит ресурс ячейки. Освободится место в /var/log, и система будет работать чуть-чуть быстрее.\n\nНе отключайте, если вы привыкли разбираться с проблемами по старым файлам журналов. Правда, важные сообщения всё равно останутся — они идут в журнал systemd, который смотрится командой journalctl. То есть вы ничего критичного не теряете.\n\nОпция работает сразу после применения, перезагрузка не нужна. Откат — просто включение службы обратно.",
        "en": "rsyslog is a program that constantly writes detailed system logs into text files on the disk. Every second it appends events: service starts, errors, user logins. On a home PC nobody reads these files, but the disk keeps getting write operations.\n\nIf you disable rsyslog, the disk stops receiving those extra writes. This is especially useful on an SSD, where every write wears out a memory cell. Space in /var/log frees up, and the system runs a bit faster.\n\nDo not disable it if you are used to troubleshooting by reading old log files. However, important messages still go to the systemd journal, which you can view with journalctl — so you are not losing anything critical.\n\nThe option applies immediately, no reboot needed. Rolling back simply re-enables the service.",
    },
    "journald": {
        "ru": "Журнал systemd — это запись всех событий системы: запуск служб, ошибки, подключения устройств. Обычно он хранится на диске и со временем разрастается до сотен мегабайт.\n\nЭта опция переносит журнал в оперативную память и ограничивает его 50 мегабайтами. Диск перестаёт получать постоянные записи, а значит, меньше изнашивается. Особенно полезно на SSD и на домашнем ПК, где журнал почти никто не читает.\n\nНе включайте, если вы привыкли разбирать старые проблемы по логам: после перезагрузки журнал в памяти исчезнет. Если вам нужны долгосрочные записи — оставьте как есть.\n\nОпция применяется сразу, перезагрузка не нужна. Служба journald перезапустится, и журнал продолжит собираться в памяти. Откат удаляет ваши изменения и возвращает журнал на диск.",
        "en": "The systemd journal records all system events: service starts, errors, device plugs. It usually lives on disk and grows to hundreds of megabytes over time.\n\nThis option moves the journal into RAM and caps it at 50 MB. The disk stops getting constant writes, which means less wear. It is especially useful on an SSD and on a home PC, where nobody reads the journal anyway.\n\nDo not enable it if you are used to troubleshooting by reading old logs: after a reboot the journal in RAM disappears. If you need long-term records, leave it as is.\n\nThe option applies immediately, no reboot needed. The journald service restarts itself, and the journal keeps collecting in memory. Rolling back removes your changes and puts the journal back on disk.",
    },
    "audit": {
        "ru": "audit — это служба ядра, которая записывает каждое действие системы: какой процесс открыл файл, какой пользователь запустил программу. Такая детальная запись нужна в офисах и на серверах для безопасности, чтобы потом можно было расследовать инциденты.\n\nДома она не нужна. Каждый системный вызов превращается в запись в журнал, а это лишняя нагрузка на процессор и диск. Отключение убирает эти накладные расходы и немного ускоряет систему.\n\nНе отключайте, если вам действительно нужны журналы безопасности для проверок — например, в организации с требованиями по аудиту.\n\nПараметр audit=0 добавляется в загрузчик GRUB, поэтому изменения вступят в силу только после перезагрузки. Откат убирает параметр из GRUB автоматически, но тоже требует перезагрузки.",
        "en": "audit is a kernel service that logs every system action: which process opened a file, which user started a program. Such detailed logging is needed in offices and on servers for security, so incidents can be investigated later.\n\nAt home it is unnecessary. Every system call turns into a log entry, which adds CPU and disk load. Disabling it removes this overhead and slightly speeds up the system.\n\nDo not disable it if you actually need security logs for audits — for example, in an organisation with compliance requirements.\n\nThe audit=0 parameter is added to the GRUB bootloader, so the change only takes effect after a reboot. Rolling back removes the parameter from GRUB automatically, but also requires a reboot.",
    },
    "raid": {
        "ru": "RAID — это способ объединить несколько физических дисков в один логический. Например, два диска могут работать как один большой для скорости или для надёжности (если один выйдет из строя, данные сохранятся на другом). Если у вас в системе есть такое объединение — у вас RAID.\n\nЕсли RAID нет, при каждой загрузке ядро всё равно несколько секунд ищет массивы и не находит. Эти секунды можно сэкономить: параметр raid=noautodetect отключает поиск и ускоряет включение.\n\nВНИМАНИЕ: не включайте эту опцию, если вы используете RAID. Система перестанет находить ваши массивы при загрузке, и вы можете потерять доступ к данным. Если сомневаетесь — не включайте.\n\nПараметр добавляется в GRUB, поэтому изменения вступают в силу после перезагрузки. Откат убирает параметр из GRUB, тоже с перезагрузкой.",
        "en": "RAID is a way to combine several physical disks into one logical one. For example, two disks can act as one big disk for speed, or for reliability (if one fails, the data stays on the other). If your system has such a combination — you have RAID.\n\nIf there is no RAID, the kernel still spends a few seconds at every boot probing for arrays and finding nothing. You can save those seconds: raid=noautodetect disables the probe and speeds up startup.\n\nWARNING: do not enable this option if you use RAID. The system will stop finding your arrays at boot, and you may lose access to your data. If in doubt — do not enable it.\n\nThe parameter is added to GRUB, so changes take effect after a reboot. Rolling back removes the parameter from GRUB, also with a reboot.",
    },
    "nmi_watchdog": {
        "ru": "NMI-watchdog — это служебный механизм ядра для отладки зависаний. Он периодически посылает процессору специальные сигналы (немаскируемые прерывания), чтобы проверить, что система ещё жива. Если система не отвечает — ядро записывает это в журнал.\n\nНа домашнем ПК такая отладка не нужна. А периодические прерывания, пусть и редкие, дают микро-фризы в играх и чувствительных к задержкам задачах. Отключение убирает эти паузы.\n\nНе отключайте, если вы специально занимаетесь отладкой зависаний ядра и вам нужны эти данные.\n\nПараметр nmi_watchdog=0 добавляется в GRUB, поэтому изменения вступают в силу после перезагрузки. Откат убирает параметр и тоже требует перезагрузки.",
        "en": "The NMI watchdog is a kernel debugging facility for detecting hangs. It periodically sends special signals to the CPU (non-maskable interrupts) to check that the system is still alive. If the system does not respond, the kernel writes it to the log.\n\nOn a home PC such debugging is unnecessary. And the periodic interrupts, even rare ones, cause micro-stutters in games and latency-sensitive tasks. Disabling them removes those pauses.\n\nDo not disable it if you specifically debug kernel hangs and need that data.\n\nThe nmi_watchdog=0 parameter is added to GRUB, so changes take effect after a reboot. Rolling back removes the parameter and also requires a reboot.",
    },
    "corectrl": {
        "ru": "CoreCtrl — это программа для тонкой настройки видеокарт AMD. Она позволяет менять частоты, управлять вентиляторами, задавать лимиты питания и следить за температурой. Без неё видеокарта работает по стандартным профилям, а с ней можно выжать больше производительности или сделать систему тише.\n\nПо умолчанию все действия CoreCtrl требуют пароль администратора. Это неудобно: чтобы менять частоты, приходится каждый раз вводить пароль. Данная опция создаёт правило Polkit, которое разрешает вашей группе пользователей управлять видеокартой без пароля.\n\nНе включайте, если у вас не AMD или вы не пользуетесь CoreCtrl. В поле «Группа» укажите группу пользователей, которой разрешено управление. По умолчанию подставляется ваша группа.\n\nОпция работает сразу, перезагрузка не нужна. Откат удаляет правило Polkit.",
        "en": "CoreCtrl is a tool for fine-tuning AMD graphics cards. It lets you change clocks, control fans, set power limits and monitor temperature. Without it the GPU runs on standard profiles; with it you can squeeze out more performance or make the system quieter.\n\nBy default every CoreCtrl action asks for the admin password. That is inconvenient: to change clocks you have to type the password each time. This option creates a Polkit rule that allows your user group to control the GPU without a password.\n\nDo not enable it if you do not have an AMD GPU or do not use CoreCtrl. In the Group field, specify the user group allowed to control the GPU. By default your own group is filled in.\n\nThe option applies immediately, no reboot needed. Rolling back removes the Polkit rule.",
    },
    "ppfeaturemask": {
        "ru": "На старых ядрах драйвер amdgpu блокирует часть функций управления питанием видеокарты AMD. Это сделано в целях безопасности: некоторые режимы могут работать нестабильно на старых картах. Но именно эти режимы нужны для тонкой настройки частот через CoreCtrl.\n\nПараметр amdgpu.ppfeaturemask=0xffffffff снимает блокировку и открывает драйверу полный контроль над частотами и питанием. После этого CoreCtrl сможет менять всё, что вы захотите.\n\nНе включайте, если у вас не AMD или вы не собираетесь настраивать частоты. Также не стоит включать, если у вас очень старая карта — она может работать нестабильно.\n\nПараметр добавляется в GRUB, поэтому изменения вступают в силу после перезагрузки. Откат убирает параметр из GRUB, тоже с перезагрузкой.",
        "en": "On older kernels the amdgpu driver blocks some AMD GPU power-management features. This is a safety measure: some modes can be unstable on old cards. But those are exactly the modes you need for fine-tuning clocks via CoreCtrl.\n\nThe parameter amdgpu.ppfeaturemask=0xffffffff lifts the block and gives the driver full control over clocks and power. After that CoreCtrl can change everything you want.\n\nDo not enable it if you do not have AMD or do not plan to tune clocks. Also do not enable it on a very old card — it may become unstable.\n\nThe parameter is added to GRUB, so changes take effect after a reboot. Rolling back removes the parameter from GRUB, also with a reboot.",
    },
    "nvidia_modeset": {
        "ru": "Для проприетарного драйвера NVIDIA нужен специальный режим вывода видео — kernel modesetting (KMS). Без него система работает с устаревшим способом вывода, из-за чего не запускается Wayland, возможны проблемы при переключении видеорежимов и композитор может вести себя странно.\n\nПараметр nvidia-drm.modeset=1 включает современный режим KMS. После этого Wayland работает корректно, переключение между разрешениями экрана происходит плавно, анимации в системе не дёргаются.\n\nНе включайте, если у вас не NVIDIA. На системах с AMD или Intel этот параметр не имеет смысла.\n\nПараметр добавляется в GRUB, поэтому изменения вступают в силу после перезагрузки. Откат убирает параметр из GRUB, тоже с перезагрузкой.",
        "en": "The proprietary NVIDIA driver needs a special video-output mode — kernel modesetting (KMS). Without it the system uses the legacy path, Wayland does not work, mode switching may glitch, and the compositor can misbehave.\n\nThe parameter nvidia-drm.modeset=1 enables modern KMS. After that Wayland works correctly, switching screen resolutions is smooth, and system animations do not stutter.\n\nDo not enable it if you do not have NVIDIA. On AMD or Intel systems this parameter is meaningless.\n\nThe parameter is added to GRUB, so changes take effect after a reboot. Rolling back removes the parameter from GRUB, also with a reboot.",
    },
    "vrr": {
        "ru": "VRR (он же FreeSync или Adaptive Sync) — это переменная частота обновления монитора. Обычно монитор обновляется с фиксированной частотой, например 60 Гц. Если игра выдаёт 47 FPS, кадры попадают на разные обновления, и картинка «рвётся». С VRR монитор подстраивается под текущий FPS: сколько кадров — столько и обновлений.\n\nЭта опция включает VRR для видеокарт AMD в X11 с драйвером amdgpu. В играх пропадут разрывы картинки, движение станет плавным даже при нестабильном FPS.\n\nНе включайте, если у вас монитор без поддержки FreeSync, видеокарта не AMD, или вы работаете в Wayland. В Wayland VRR настраивается иначе.\n\nСоздаётся конфиг X11, для вступления в силу нужно перезайти в сеанс или перезагрузиться. Откат удаляет конфиг, тоже с перезаходом.",
        "en": "VRR (also known as FreeSync or Adaptive Sync) is a variable monitor refresh rate. Normally the monitor refreshes at a fixed rate, say 60 Hz. If a game outputs 47 FPS, frames land on different refreshes and the picture tears. With VRR the monitor adapts to the current FPS: as many frames as refreshes.\n\nThis option enables VRR for AMD GPUs in X11 with the amdgpu driver. In games tearing disappears and motion stays smooth even at unstable FPS.\n\nDo not enable it if your monitor does not support FreeSync, your GPU is not AMD, or you run Wayland. In Wayland VRR is configured differently.\n\nAn X11 config is created; to apply it you need to re-login or reboot. Rolling back removes the config, also with a re-login.",
    },
    "radv": {
        "ru": "SAM (Smart Access Memory) или Resizable BAR — это технология, при которой процессор получает доступ ко всей видеопамяти сразу, а не кусками по 256 МБ. Обычно это даёт небольшой прирост FPS в играх.\n\nПараметр RADV_PERFTEST=sam включает поддержку SAM в открытом драйвере RADV. Это прирост на несколько процентов в части игр, особенно на новых картах Radeon.\n\nНе включайте, если у вас не AMD, старая материнская плата без поддержки Resizable BAR, или вы работаете с драйвером NVIDIA.\n\nПеременная записывается в /etc/environment и применяется при входе в сеанс. Нужно перезайти в сеанс или перезагрузиться. Откат убирает переменную, тоже с перезаходом.",
        "en": "SAM (Smart Access Memory) or Resizable BAR is a technology where the CPU gets access to all VRAM at once instead of chunks of 256 MB. It usually gives a small FPS gain in games.\n\nThe RADV_PERFTEST=sam parameter enables SAM support in the open RADV driver. This gives a few percent gain in some games, especially on newer Radeon cards.\n\nDo not enable it if you do not have AMD, have an old motherboard without Resizable BAR support, or use the NVIDIA driver.\n\nThe variable is written to /etc/environment and applies at login. You need to re-login or reboot. Rolling back removes the variable, also with a re-login.",
    },
    "mesa": {
        "ru": "MESA — это набор графических библиотек, которые используют игры и программы для вывода картинки. Одна из функций MESA — кэширование скомпилированных шейдеров. Шейдер — это небольшая программа для видеокарты, которую нужно скомпилировать перед первым использованием.\n\nПо умолчанию кэш MESA небольшой, и когда он переполняется, старые шейдеры удаляются. При следующем запуске игры они компилируются заново — это и вызывает подтормаживания в первые минуты. Если увеличить кэш до 4 ГБ, шейдеры останутся, и игра будет запускаться сразу плавно.\n\nНе включайте, если вы не играете в игры с шейдерами (в основном это все современные игры). Для офисных задач разницы не будет.\n\nПеременная записывается в /etc/environment и применяется при входе в сеанс. Нужно перезайти или перезагрузиться.",
        "en": "MESA is a set of graphics libraries that games and applications use to render the picture. One of MESA's features is caching compiled shaders. A shader is a small program for the GPU that must be compiled before first use.\n\nBy default the MESA cache is small, and when it overflows, old shaders are deleted. The next time you launch the game, they are recompiled — that is what causes stutters in the first minutes. If you raise the cache to 4 GB, shaders stay, and the game launches smoothly right away.\n\nDo not enable it if you do not play shader-heavy games (which is almost all modern games). For office tasks there is no difference.\n\nThe variable is written to /etc/environment and applies at login. You need to re-login or reboot.",
    },
    "pipewire": {
        "ru": "PipeWire — это звуковой сервер, который передаёт звук от приложений к колонкам и наушникам. У него есть настройка размера буферов: маленькие буферы дают низкую задержку, но на некоторых системах вызывают треск и щелчки. Большие буферы убирают артефакты, но добавляют небольшую задержку (на практике незаметно).\n\nЭта опция увеличивает буферы PipeWire. Треск, щелчки и прерывистый звук в наушниках и колонках исчезают. Особенно заметно на встроенных звуковых картах и на некоторых USB-ЦАПах.\n\nНе включайте, если у вас нет проблем со звуком. Если звук работает нормально, не стоит ничего менять.\n\nСоздаётся конфиг в вашей домашней папке. Нужно перезайти в сеанс или перезагрузиться. Откат удаляет конфиг, тоже с перезаходом.",
        "en": "PipeWire is the sound server that hands audio from applications to speakers and headphones. It has a buffer-size setting: small buffers give low latency but on some systems cause crackling and pops. Large buffers remove the artifacts but add a little latency (imperceptible in practice).\n\nThis option enlarges PipeWire buffers. Crackling, pops and stuttering in headphones and speakers disappear. Especially noticeable on built-in sound cards and some USB DACs.\n\nDo not enable it if you have no sound problems. If audio works fine, there is no reason to change anything.\n\nA config is created in your home folder. You need to re-login or reboot. Rolling back removes the config, also with a re-login.",
    },
    "bbr": {
        "ru": "BBR — это современный алгоритм управления перегрузками TCP, разработанный Google. Он определяет, с какой скоростью отправлять данные по сети, чтобы не перегружать канал и не терять пакеты. Старый алгоритм CUBIC работает хорошо на стабильных каналах, но BBR выигрывает на нестабильных.\n\nЭта опция включает BBR и очередь fq. На Wi-Fi, VPN, мобильном интернете и дальних серверах скорость загрузки становится выше, а задержки — меньше. На стабильном кабеле разница почти не заметна.\n\nНе включайте, если у вас стабильный проводной интернет и вы не жалуетесь на задержки. BBR не сломает соединение, но и заметной выгоды не даст.\n\nПараметр применяется сразу, перезагрузка не нужна. Откат возвращает старый алгоритм CUBIC и тоже работает без перезагрузки.",
        "en": "BBR is a modern TCP congestion-control algorithm developed by Google. It decides at what rate to send data over the network so the link is not overloaded and packets are not lost. The older CUBIC algorithm works well on stable links, but BBR wins on unstable ones.\n\nThis option enables BBR and the fq queue. On Wi-Fi, VPN, mobile internet and remote servers, download speed increases and latency drops. On a stable cable the difference is barely noticeable.\n\nDo not enable it if you have a stable wired internet connection and no latency complaints. BBR will not break the connection, but it will not bring noticeable benefit either.\n\nThe parameter applies immediately, no reboot needed. Rolling back restores the older CUBIC algorithm, also without a reboot.",
    },
    "swap": {
        "ru": "Swap (подкачка) — это область на диске или в сжатой памяти, куда система складывает редко используемые данные, когда оперативной памяти не хватает. Насколько охотно система это делает — задаётся числом vm.swappiness от 0 до 200.\n\nВысокое значение (например, 150) означает: система активно переносит данные в swap, освобождая оперативную память. Это выгодно, если swap — это zram (сжатая память в ОЗУ), обращение к ней дешёвое. Низкое значение (10) означает: система старается держать данные в ОЗУ и обращается к диску только в крайнем случае. Это выгодно, если swap на диске или SSD — тогда диск меньше дёргается.\n\nНе включайте, если вас устраивает поведение по умолчанию (обычно 60). На современных системах с большим количеством ОЗУ разницы вы можете не заметить.\n\nПараметр применяется сразу через sysctl, перезагрузка не нужна. Откат возвращает значение 60.",
        "en": "Swap is a region on disk or in compressed memory where the system stores rarely used data when RAM runs low. How eagerly it does this is controlled by vm.swappiness, a number from 0 to 200.\n\nA high value (say 150) means the system actively moves data to swap, freeing up RAM. This is good if swap is zram (compressed memory in RAM), because access is cheap. A low value (10) means the system tries to keep data in RAM and only touches the disk as a last resort. This is good if swap is on a disk or SSD — the disk is hit less often.\n\nDo not enable it if the default behaviour (usually 60) is fine for you. On modern systems with plenty of RAM you may not notice any difference.\n\nThe parameter applies immediately via sysctl, no reboot needed. Rolling back restores the value 60.",
    },
    "zram": {
        "ru": "zram — это сжатая область в оперативной памяти, которую система использует как дополнительную память. Когда ОЗУ не хватает, данные не сбрасываются на диск, а сжимаются в памяти. Скорость обращения к сжатой памяти намного выше, чем к диску, а ресурс SSD не расходуется.\n\nЭта опция создаёт zram через пакет zram-generator. Если у вас мало ОЗУ (4–8 ГБ), система реже будет обращаться к диску при работе с большим количеством приложений. Это ускоряет работу и продлевает жизнь SSD.\n\nНе включайте, если у вас много оперативной памяти (16 ГБ и больше) — разницы вы не почувствуете. Также опция не имеет смысла, если пакет zram-generator не установлен. Установите его командой «sudo apt install zram-generator».\n\nКонфиг создаётся сразу, но устройство zram появится только после перезагрузки. Откат удаляет конфиг, тоже с перезагрузкой.",
        "en": "zram is a compressed area in RAM used by the system as extra memory. When RAM runs low, data is not written to disk — it is compressed in memory. Accessing compressed memory is much faster than accessing the disk, and SSD wear is avoided.\n\nThis option sets up zram via the zram-generator package. If you have little RAM (4–8 GB), the system accesses the disk less often when many apps are running. This speeds up work and extends SSD life.\n\nDo not enable it if you have plenty of RAM (16 GB or more) — you will not feel a difference. Also it makes no sense if zram-generator is not installed. Install it with «sudo apt install zram-generator».\n\nThe config is created immediately, but the zram device only appears after a reboot. Rolling back removes the config, also with a reboot.",
    },
    "zswap": {
        "ru": "zswap — это сжатый кэш в оперативной памяти, который стоит перед обычным swap. Когда системе нужно выгрузить страницу памяти, она сначала пробует сжать её и оставить в zswap. Только если zswap переполнен, данные уходят на диск.\n\nЭта опция включает zswap и задаёт компрессор zstd. Если у вас есть swap на диске и вы иногда сталкиваетесь с нехваткой памяти, zswap уменьшит количество обращений к диску. Система будет отзывчивее, а SSD — живее.\n\nНе включайте, если у вас нет swap или вы им никогда не пользуетесь. Также zswap не нужен, если у вас уже настроен zram (они делают похожие вещи).\n\nПараметры добавляются в GRUB, поэтому изменения вступают в силу после перезагрузки. Откат убирает их из GRUB, тоже с перезагрузкой.",
        "en": "zswap is a compressed cache in RAM that sits in front of regular swap. When the system needs to swap out a page, it first tries to compress it and keep it in zswap. Only when zswap overflows does data go to disk.\n\nThis option enables zswap and sets the zstd compressor. If you have swap on disk and occasionally run out of memory, zswap reduces disk accesses. The system feels more responsive and the SSD lives longer.\n\nDo not enable it if you have no swap or never use it. Also zswap is unnecessary if you already use zram (they do similar things).\n\nThe parameters are added to GRUB, so changes take effect after a reboot. Rolling back removes them from GRUB, also with a reboot.",
    },
    "thp": {
        "ru": "Память компьютера делится на страницы — небольшие кусочки. Обычно это страницы по 4 КБ. Когда программа работает с большими объёмами данных (игры, обработка фото, базы данных), системе приходится управлять миллионами таких мелких страниц, и это отнимает время.\n\nРежим THP (Transparent Huge Pages) позволяет выдавать память крупными страницами по 2 МБ. Управлять ими проще, поэтому игры и тяжёлые программы работают чуть быстрее. Есть три режима: always — выдавать крупные страницы всем, madvise — только тем программам, которые сами попросят (самый безопасный), never — не использовать вообще.\n\nРекомендуется значение madvise: оно даёт выгоду там, где нужно, и не мешает остальным. Режим always иногда вызывает лёгкие подтормаживания из-за дефрагментации памяти.\n\nПараметр добавляется в GRUB, поэтому изменения вступают в силу после перезагрузки. Откат убирает параметр, тоже с перезагрузкой.",
        "en": "Computer memory is divided into pages — small chunks. Normally these are 4 KB pages. When a program works with large amounts of data (games, photo editing, databases), the system has to manage millions of such small pages, and that takes time.\n\nTHP (Transparent Huge Pages) mode lets the system hand out memory in large 2 MB pages. They are easier to manage, so games and heavy apps run slightly faster. There are three modes: always — hand out large pages to everyone, madvise — only to programs that explicitly ask (safest), never — do not use at all.\n\nThe recommended value is madvise: it gives a benefit where needed and does not interfere with the rest. always sometimes causes slight stutters due to memory defragmentation.\n\nThe parameter is added to GRUB, so changes take effect after a reboot. Rolling back removes the parameter, also with a reboot.",
    },
    "sysctl_cache": {
        "ru": "Ядро Linux держит в оперативной памяти кэш файлов и папок — те данные, которые недавно читались с диска. Когда кэш переполняется, ядро освобождает его часть. Параметр vfs_cache_pressure говорит ядру, насколько агрессивно освобождать кэш.\n\nЗначение по умолчанию — 100. Опция ставит 50, то есть ядро будет освобождать кэш в два раза реже. Файлы и папки, которые вы недавно открывали, останутся в памяти дольше, и следующее открытие пройдёт быстрее. Особенно заметно, если вы работаете с большим количеством файлов — например, с фотоархивом или исходным кодом.\n\nНе включайте, если у вас мало оперативной памяти (меньше 4 ГБ) — кэш может вытеснить нужные данные работающих программ. При большом количестве ОЗУ эта опция безопасна и полезна.\n\nПараметр применяется сразу через sysctl, перезагрузка не нужна. Откат возвращает значение 100.",
        "en": "The Linux kernel keeps a cache of files and folders in RAM — data recently read from disk. When the cache overflows, the kernel frees part of it. The vfs_cache_pressure parameter tells the kernel how aggressively to free the cache.\n\nThe default value is 100. This option sets 50, meaning the kernel will free the cache half as often. Files and folders you recently opened stay in memory longer, and the next open is faster. Especially noticeable if you work with many files — a photo archive or source code, for example.\n\nDo not enable it if you have little RAM (less than 4 GB) — the cache may push out data that running programs need. With plenty of RAM this option is safe and useful.\n\nThe parameter applies immediately via sysctl, no reboot needed. Rolling back restores the value 100.",
    },
    "sysctl_numa": {
        "ru": "NUMA — это архитектура памяти на серверах с несколькими процессорами. На таких системах память физически разделена между процессорами, и доступ к «чужой» памяти медленнее. Ядро Linux автоматически переносит страницы памяти между процессорами, чтобы всем было хорошо. Это называется numa_balancing.\n\nНа домашнем ПК NUMA нет — процессор один (или память одна). Но механизм балансировки всё равно работает и создаёт микропаузы в работе, особенно в играх. Отключение этой балансировки убирает паузы.\n\nНе отключайте, если у вас настоящий сервер с NUMA и вы знаете, зачем он нужен. На домашних системах опция безопасна и полезна.\n\nПараметр применяется сразу через sysctl, перезагрузка не нужна. Откат возвращает значение 1 (включено).",
        "en": "NUMA is a memory architecture on servers with several processors. On such systems, memory is physically split between CPUs, and accessing “foreign” memory is slower. The Linux kernel automatically moves memory pages between CPUs so everything runs well. This is called numa_balancing.\n\nA home PC has no NUMA — one CPU (or one memory pool). But the balancing mechanism still runs and causes micro-pauses, especially in games. Disabling this balancing removes the pauses.\n\nDo not disable it if you actually run a NUMA server and know why it matters. On home systems the option is safe and useful.\n\nThe parameter applies immediately via sysctl, no reboot needed. Rolling back restores the value 1 (enabled).",
    },
    "reisub": {
        "ru": "Magic SysRq — это набор аварийных команд ядра, которые вызываются сочетанием Alt+PrtSc и определённой буквы. Они работают даже когда система полностью зависла и не реагирует ни на что. Самая полезная последовательность — R E I S U B.\n\nКаждая буква означает: R — вернуть управление клавиатуре из-под графики, E — вежливо завершить процессы, I — убить оставшиеся, S — синхронизировать данные с диском, U — перемонтировать диски в режим только для чтения, B — перезагрузиться. Нажимать их нужно по порядку, с интервалом 1–2 секунды, удерживая Alt+PrtSc.\n\nПосле такой последовательности система перезагружается безопасно, без риска повредить файлы. Это намного лучше, чем жёсткий сброс кнопкой питания. Не отключайте эту возможность, если у вас бывают зависания.\n\nПараметр применяется сразу через sysctl, перезагрузка не нужна. Откат возвращает стандартную маску 176 (отключены опасные функции).",
        "en": "Magic SysRq is a set of emergency kernel commands triggered by Alt+PrtSc and a certain letter. They work even when the system is completely frozen and unresponsive. The most useful sequence is R E I S U B.\n\nEach letter means: R — reclaim keyboard from graphics, E — politely terminate processes, I — kill the rest, S — sync data to disk, U — remount disks read-only, B — reboot. Press them in order, 1–2 seconds apart, holding Alt+PrtSc.\n\nAfter that sequence the system reboots safely, with no risk of file corruption. It is much better than a hard reset with the power button. Do not disable this feature if your system hangs sometimes.\n\nThe parameter applies immediately via sysctl, no reboot needed. Rolling back restores the default mask 176 (dangerous functions disabled).",
    },
    "ntsync": {
        "ru": "ntsync — это новый модуль ядра, который ускоряет синхронизацию потоков в Wine и Proton. Игры под Windows активно используют примитивы синхронизации (мьютексы, события, семафоры), и их реализация в Wine долго была медленной. ntsync делает её значительно быстрее.\n\nРезультат — заметный прирост FPS в некоторых играх, особенно в тех, где много потоков. Если у вас ядро 6.14 или новее (или патченное с ntsync), опция включит модуль и добавит его в автозагрузку.\n\nНе включайте, если у вас ядро старше 6.14 без патча — модуль просто не загрузится. Также не имеет смысла, если вы не играете под Wine и Proton.\n\nМодуль загружается сразу, перезагрузка не нужна. При этом автозагрузка при следующем включении тоже будет настроена. Откат удаляет файл автозагрузки, модуль останется загруженным до перезагрузки.",
        "en": "ntsync is a new kernel module that speeds up thread synchronization in Wine and Proton. Windows games heavily use synchronization primitives (mutexes, events, semaphores), and their implementation in Wine was slow for a long time. ntsync makes it significantly faster.\n\nThe result is a noticeable FPS gain in some games, especially those with many threads. If you have kernel 6.14 or newer (or an ntsync-patched one), the option loads the module and adds it to autoload.\n\nDo not enable it if your kernel is older than 6.14 without a patch — the module simply will not load. Also it makes no sense if you do not play under Wine and Proton.\n\nThe module loads immediately, no reboot needed. Autoload for the next boot is also set up. Rolling back removes the autoload file; the module stays loaded until reboot.",
    },
    "ntfs3": {
        "ru": "NTFS — это файловая система Windows. Linux умеет читать и писать на неё двумя способами: через старый медленный драйвер ntfs-3g в пользовательском пространстве и через новый быстрый ntfs3 внутри ядра. Второй в разы быстрее.\n\nLinux Mint по умолчанию блокирует ntfs3 и использует ntfs-3g. Причина историческая: раньше у ntfs3 были проблемы со стабильностью. Сейчас они исправлены, и ntfs3 работает надёжно. Эта опция снимает блокировку, и NTFS-диски начинают работать заметно быстрее.\n\nВНИМАНИЕ: не включайте, если у вас нет NTFS-дисков — эффекта не будет. Если у вас есть NTFS-диск с важными данными, сделайте резервную копию перед включением, просто на всякий случай.\n\nПосле снятия блокировки уже подключённые диски продолжат работать со старым драйвером, пока вы их не перемонтируете. Нужна перезагрузка или ручное перемонтирование. Откат возвращает блокировку.",
        "en": "NTFS is the Windows file system. Linux can read and write it two ways: through the old slow ntfs-3g driver in userspace, and through the new fast ntfs3 driver inside the kernel. The second is much faster.\n\nLinux Mint blocks ntfs3 by default and uses ntfs-3g. The reason is historical: ntfs3 used to have stability issues. Those are fixed now, and ntfs3 works reliably. This option lifts the block, and NTFS disks start working noticeably faster.\n\nWARNING: do not enable it if you have no NTFS disks — there will be no effect. If you have an NTFS disk with important data, make a backup before enabling, just in case.\n\nAfter the block is lifted, already mounted disks keep using the old driver until you remount them. A reboot or manual remount is required. Rolling back restores the block.",
    },
    "commit": {
        "ru": "Параметр commit=NN заставляет файловую систему реже сбрасывать накопленные данные на диск: не раз в 5 секунд по умолчанию, а раз в NN секунд. Это уменьшает число операций записи и продлевает жизнь SSD.\n\nВАЖНО: параметр понимают ТОЛЬКО файловые системы семейства ext — ext2, ext3, ext4. Для NTFS, FAT32, exFAT, btrfs, xfs, f2fs и других он неизвестен: в лучшем случае ядро его проигнорирует, в худшем — откажется монтировать раздел, и система при загрузке упадёт в emergency-режим (аварийную консоль восстановления).\n\nПоэтому в этом твикере для commit= показываются только разделы с ext2/ext3/ext4 — их можно выбрать галочкой. Разделы с другими файловыми системами отключены намеренно, чтобы случайно не сломать загрузку.\n\nВНИМАНИЕ: чем больше интервал, тем выше риск потерять последние записанные данные при внезапном отключении питания. Разумные значения — 60–120 секунд. Значение 0 отключает периодический сброс полностью и годится только для тестовых машин.\n\nИзменения записываются в /etc/fstab и вступают в силу после перезагрузки. Откат убирает параметр из fstab, тоже с перезагрузкой.",
        "en": "The commit=NN parameter makes the file system flush accumulated data to disk less often: not every 5 seconds by default, but every NN seconds. This reduces write operations and extends SSD life.\n\nIMPORTANT: only file systems of the ext family support this — ext2, ext3, ext4. For NTFS, FAT32, exFAT, btrfs, xfs, f2fs and others the parameter is unknown: at best the kernel silently ignores it, at worst it refuses to mount the partition and the system drops into emergency mode on boot.\n\nTherefore in this tweaker only partitions with ext2/ext3/ext4 are shown for commit= — they can be ticked. Partitions with other file systems are intentionally disabled so that boot cannot be broken by accident.\n\nWARNING: the longer the interval, the higher the risk of losing the latest written data on sudden power loss. Reasonable values are 60–120 seconds. Value 0 disables periodic flushing entirely and is only suitable for test machines.\n\nChanges are written to /etc/fstab and take effect after a reboot. Rolling back removes the parameter from fstab, also with a reboot.",
    },
    "aliases": {
        "ru": "В Linux много рутинных действий в терминале: обновление пакетов, очистка кэша, проверка места на диске. Каждый раз набирать длинные команды утомительно. Чтобы этого избежать, в файл .bashrc добавляют короткие функции-обёртки.\n\nЭта опция добавляет в ваш .bashrc готовый набор команд: upd (обновить списки пакетов), upgr (обновить пакеты), update_all (полное обновление системы, включая Flatpak), clean (очистка ненужных пакетов), space (показать свободное место), mem (очистить кэш памяти), fix (починить сломанные пакеты) и другие. Набираете три буквы — получаете результат.\n\nНе включайте, если вы не пользуетесь терминалом. Также не включайте, если у вас уже есть собственные функции с такими именами — они могут конфликтовать.\n\nОпция применяется сразу, но команды появятся только в новых терминалах. Откройте новый терминал или выполните «source ~/.bashrc». Откат удаляет блок команд.",
        "en": "Linux has many routine terminal actions: updating packages, clearing cache, checking disk space. Typing long commands every time is tiring. To avoid this, short wrapper functions are added to the .bashrc file.\n\nThis option adds a ready set of commands to your .bashrc: upd (update package lists), upgr (upgrade packages), update_all (full system update, including Flatpak), clean (remove unnecessary packages), space (show free disk space), mem (clear memory cache), fix (repair broken packages) and others. Type three letters — get a result.\n\nDo not enable it if you do not use the terminal. Also do not enable it if you already have your own functions with these names — they may conflict.\n\nThe option applies immediately, but the commands only appear in new terminals. Open a new terminal or run «source ~/.bashrc». Rolling back removes the command block.",
    },
    "autoupdate": {
        "ru": "Обновления системы нужно ставить регулярно — это вопросы безопасности и свежих функций. Вручную это делать лень, поэтому логично поручить задачу systemd. Он умеет запускать команды по расписанию с помощью таймеров.\n\nЭта опция создаёт systemd-таймер, который сам запускает обновление APT и Flatpak в выбранное время. Вы один раз настраиваете расписание (например, каждую субботу в 18:30) и забываете об этом. При включённом Cinnamon дополнительно обновляются апплеты и темы.\n\nВНИМАНИЕ: в Linux Mint есть встроенное автообновление (mintupdate). Если его не отключить, обновления будут запускаться дважды и могут конфликтовать. Отключите mintupdate перед включением этой опции.\n\nТаймер включается сразу, перезагрузка не нужна. Первое обновление произойдёт в ближайшее выбранное время. Откат удаляет таймер.",
        "en": "System updates need to be installed regularly — it is a matter of security and fresh features. Doing it manually is tiring, so it makes sense to delegate the task to systemd. It can run commands on a schedule using timers.\n\nThis option creates a systemd timer that runs APT and Flatpak updates at the chosen time. You configure the schedule once (say, every Saturday at 18:30) and forget about it. On Cinnamon, applets and themes are updated as well.\n\nWARNING: Linux Mint has a built-in auto-update (mintupdate). If you do not disable it, updates will run twice and may conflict. Disable mintupdate before enabling this option.\n\nThe timer starts immediately, no reboot needed. The first update runs at the next chosen time. Rolling back removes the timer.",
    },
    "mount": {
        "ru": "Когда система открывает файл на чтение, она по умолчанию обновляет время последнего доступа к нему. Это нужно для некоторых служебных задач, но на домашнем ПК бесполезно: никто не смотрит на эти метки. При этом каждая запись — это операция на диск, которая тратит ресурс SSD.\n\nОпция noatime отключает обновление времени доступа. Файлы и папки читаются как обычно, но система не делает служебную запись при каждом чтении. Диск меньше работает, SSD живёт дольше, чтение немного быстрее.\n\nНе включайте, если у вас обычный HDD и вас не волнует ресурс диска. На SSD выгода ощутимее. Также не включайте, если у вас есть программы, которые специально следят за временем доступа — таких мало, но они существуют.\n\nПараметры записываются в /etc/fstab, поэтому применяются после перезагрузки. Откат убирает их из fstab, тоже с перезагрузкой.",
        "en": "When the system opens a file for reading, by default it updates the last-access time. This is needed for some service tasks, but on a home PC it is useless: nobody looks at those marks. Meanwhile every write is a disk operation that wears out the SSD.\n\nThe noatime option disables updating the access time. Files and folders are still read normally, but the system does not write to disk on every read. The disk works less, the SSD lives longer, and reads are slightly faster.\n\nDo not enable it if you have a conventional HDD and do not care about disk life. On an SSD the benefit is more noticeable. Also do not enable it if you have programs that specifically track access time — those are rare, but they exist.\n\nThe parameters are written to /etc/fstab and apply after a reboot. Rolling back removes them from fstab, also with a reboot.",
    },
    "steam": {
        "ru": "Игры Steam под Proton (технология запуска Windows-игр в Linux) хранят свои данные в папке compatdata: настройки, сохранения, установленные библиотеки. По умолчанию эта папка лежит в домашней директории — в ~/.steam/steam/steamapps/compatdata.\n\nЕсли библиотека Steam находится на другом диске, например на NTFS-разделе, игра не может найти данные в домашней папке. Симлинк (ссылка) compatdata внутри библиотеки решает эту проблему: он указывает на домашнюю папку, и игры снова видят свои данные.\n\nНе включайте, если все ваши библиотеки Steam находятся на домашнем диске — там симлинк не нужен. Также не имеет смысла, если у вас нет Steam или вы не играете в игры под Proton.\n\nОпция работает сразу, перезагрузка не нужна. Если папка compatdata уже существует с данными — она не трогается, чтобы не потерять сохранения. Откат удаляет только созданные симлинки.",
        "en": "Steam games under Proton (technology that runs Windows games on Linux) keep their data in the compatdata folder: settings, saves, installed libraries. By default this folder lives in the home directory — in ~/.steam/steam/steamapps/compatdata.\n\nIf the Steam library is on another disk, for example on an NTFS partition, the game cannot find the data in the home folder. A compatdata symlink (link) inside the library solves this: it points to the home folder, and games see their data again.\n\nDo not enable it if all your Steam libraries are on the home disk — the symlink is not needed there. Also it makes no sense if you do not have Steam or do not play games under Proton.\n\nThe option works immediately, no reboot needed. If the compatdata folder already exists with data, it is left untouched so saves are not lost. Rolling back removes only the created symlinks.",
    },
}

SERVICES_HELP = {
    "avahi-daemon.service": {
        "ru": "Avahi — это служба, которая ищет устройства в локальной сети без настройки. Она использует протокол mDNS/DNS-SD: устройства сами объявляют о себе, и вы видите их в списке доступных принтеров, колонок, телевизоров. Например, включив Chromecast, вы сразу видите его в браузере — это работа Avahi.\n\nНа домашнем ПК без сетевого принтера и без Chromecast/AirPlay служба не нужна. Она периодически рассылает пакеты в сеть, но делает это вхолостую. Отключение освобождает небольшой объём памяти и снижает сетевую активность.\n\nОтключение безопасно. Если позже захотите снова найти сетевое устройство — включите службу обратно.",
        "en": "Avahi is a service that discovers devices on your local network without setup. It uses the mDNS/DNS-SD protocol: devices announce themselves, and you see them in the list of available printers, speakers, TVs. For example, when you turn on Chromecast, you see it in the browser right away — that is Avahi at work.\n\nOn a home PC without a network printer and without Chromecast/AirPlay, the service is unneeded. It periodically broadcasts into the network, but does so idle. Disabling it frees a little memory and reduces network activity.\n\nDisabling is safe. If you later want to find a network device again, re-enable the service.",
    },
    "avahi-daemon.socket": {
        "ru": "Сокет — это как «розетка», которая «будит» службу Avahi, когда в сеть приходит первый запрос. У сокета и службы общая задача: пока никто не ищет устройства, Avahi может спать и не занимать ресурсы. Как только запрос появился — сокет запускает службу.\n\nЭтот сокет бесполезен сам по себе, без службы Avahi. Если Avahi отключена, сокет тоже не нужен — он просто ничего не делает.\n\nОтключайте его вместе со службой Avahi, чтобы она не «проснулась» нечаянно от сетевого запроса. Отключение безопасно.",
        "en": "A socket is like a “plug” that wakes the Avahi service when the first network request arrives. The socket and the service share a task: while nobody is looking for devices, Avahi can sleep and use no resources. As soon as a request comes in, the socket starts the service.\n\nThis socket is useless on its own without the Avahi service. If Avahi is disabled, the socket is unneeded too — it does nothing.\n\nDisable it together with the Avahi service so it cannot accidentally wake up from a network request. Disabling is safe.",
    },
    "cups-browsed.service": {
        "ru": "cups-browsed — это часть системы печати CUPS. Она автоматически ищет сетевые принтеры и добавляет их в список доступных. Удобно, когда вы подключаетесь к чужому офисному принтеру: он появляется сам, без ввода адреса.\n\nДома эта служба не нужна, если у вас нет сетевого принтера. Если принтер подключён по USB, служба тоже бесполезна — она ищет только сетевые устройства. При этом она периодически просыпается и рассылает запросы.\n\nОтключение безопасно. Если позже у вас появится сетевой принтер, можно включить обратно.",
        "en": "cups-browsed is part of the CUPS printing system. It automatically discovers network printers and adds them to the list of available ones. Handy when you connect to someone else's office printer: it appears on its own, no address entry needed.\n\nAt home the service is unneeded if you have no network printer. If the printer is connected via USB, the service is also useless — it only looks for network devices. Meanwhile it periodically wakes up and sends requests.\n\nDisabling is safe. If a network printer appears later, you can re-enable it.",
    },
    "cups.service": {
        "ru": "CUPS — это служба печати и сканирования. Все программы, которые что-то печатают или сканируют, обращаются к ней. Она управляет очередью печати, настройками принтеров, правами доступа.\n\nЕсли у вас нет принтера или сканера, CUPS просто висит в фоне и не делает ничего полезного. Отключение освобождает память и убирает фоновую активность. Если в будущем вы купите принтер — службу можно включить обратно, все настройки сохранятся.\n\nОтключение безопасно. Единственное, что перестанет работать — печать и сканирование, что и так не используется.",
        "en": "CUPS is the printing and scanning service. Every program that prints or scans talks to it. It manages the print queue, printer settings and access rights.\n\nIf you have no printer or scanner, CUPS just idles in the background doing nothing useful. Disabling it frees memory and removes background activity. If you buy a printer later, the service can be re-enabled, and all settings are preserved.\n\nDisabling is safe. The only thing that stops working is printing and scanning, which is unused anyway.",
    },
    "cups.socket": {
        "ru": "Сокет — это «розетка», которая будит службу печати CUPS, когда какая-то программа пытается что-то напечатать. Пока никто не печатает, CUPS может не работать. Как только появился запрос на печать — сокет запускает службу.\n\nЭтот сокет бесполезен без службы CUPS. Если вы отключили CUPS, сокет тоже не нужен.\n\nОтключайте его вместе со службой CUPS. Если позже включите печать обратно, не забудьте включить и сокет.",
        "en": "A socket is a “plug” that wakes the CUPS print service when a program tries to print. While nobody prints, CUPS does not have to run. As soon as a print request appears, the socket starts the service.\n\nThis socket is useless without the CUPS service. If you disabled CUPS, the socket is unneeded too.\n\nDisable it together with the CUPS service. If you later re-enable printing, remember to enable the socket as well.",
    },
    "ModemManager.service": {
        "ru": "ModemManager — это служба для работы с мобильными модемами. Она управляет устройствами, которые подключаются к компьютеру через USB или встроены в ноутбук и работают через сим-карту. Именно она позволяет выйти в интернет через 3G или 4G.\n\nНа стационарном ПК без модема эта служба не нужна. Более того, она иногда мешает устройствам, которые определяются как последовательный порт (serial port): Arduino, переходники USB-Serial, отладочные платы. ModemManager может пытаться «поговорить» с ними по-своему и портить связь.\n\nЕсли у вас есть такие устройства и они работают нестабильно — отключение ModemManager часто решает проблему. Если вы выходите в интернет через сим-карту, служба нужна.",
        "en": "ModemManager is a service for mobile modems. It manages devices plugged in via USB or built into a laptop and working via SIM. It is what lets you go online through 3G or 4G.\n\nOn a desktop PC without a modem the service is unneeded. Moreover, it sometimes interferes with devices that appear as serial ports: Arduino, USB-Serial adapters, development boards. ModemManager may try to “talk” to them its own way and disrupt communication.\n\nIf you have such devices and they work unreliably, disabling ModemManager often fixes the problem. If you get internet via SIM, keep the service enabled.",
    },
    "openvpn.service": {
        "ru": "OpenVPN — это система для создания защищённых туннелей между компьютерами. Служба openvpn.service относится к серверной части: она принимает входящие подключения от других устройств. Если вы обычно используете VPN-клиент (например, подключаетесь к коммерческому VPN), это не та служба — она для другого.\n\nДома эту службу держат только те, кто поднимает собственный VPN-сервер, к которому подключаются извне. Если вы не настраивали такое — служба просто неактивна и не нужна.\n\nОтключение безопасно. Если в будущем вы решите поднять свой VPN-сервер, службу можно включить обратно.",
        "en": "OpenVPN is a system for creating secure tunnels between computers. The openvpn.service unit is the server side: it accepts incoming connections from other devices. If you usually use a VPN client (for example, connecting to a commercial VPN), that is not this service — this one is for something else.\n\nAt home only those who run their own VPN server keep this service — the one others connect to from the outside. If you did not set up such a thing, the service is inactive and unneeded.\n\nDisabling is safe. If you later decide to run your own VPN server, the service can be re-enabled.",
    },
    "lvm2-monitor.service": {
        "ru": "LVM — это способ объединить несколько дисков или разделов в один большой «виртуальный» диск. Удобно, когда не хватает места на одном диске: вы добавляете ещё один, и они работают как один. Служба lvm2-monitor следит за состоянием таких объединений и уведомляет о проблемах.\n\nПри обычной установке Linux Mint или Ubuntu LVM не используется. Диски и разделы подключаются напрямую. Значит, служба не нужна — она только висит в фоне.\n\nОтключение безопасно. Не отключайте, если вы специально настраивали LVM и используете объединённые тома.",
        "en": "LVM is a way to combine several disks or partitions into one big “virtual” disk. Useful when one disk is not enough: you add another, and they work as one. The lvm2-monitor service watches such unions and reports problems.\n\nA standard Linux Mint or Ubuntu install does not use LVM. Disks and partitions are attached directly. So the service is unneeded — it just idles in the background.\n\nDisabling is safe. Do not disable it if you specifically configured LVM and use combined volumes.",
    },
    "switcheroo-control.service": {
        "ru": "Switcheroo — это служба для ноутбуков с двумя видеокартами (обычно встроенной Intel и отдельной NVIDIA или AMD). Она позволяет переключаться между картами: для офисных задач использовать встроенную (экономно), для игр — отдельную (мощно).\n\nНа настольном ПК с одной видеокартой эта служба не нужна. Ей нечем управлять, и она просто висит в фоне.\n\nОтключение безопасно. Если у вас ноутбук с двумя картами, лучше оставить — иначе переключение работать не будет.",
        "en": "Switcheroo is a service for laptops with two GPUs (usually an integrated Intel and a discrete NVIDIA or AMD). It lets you switch between them: use the integrated for office tasks (power-efficient), the discrete one for games (powerful).\n\nOn a desktop PC with a single GPU the service is unneeded. There is nothing to manage, and it just idles in the background.\n\nDisabling is safe. If you have a laptop with two GPUs, better leave it enabled — otherwise switching will not work.",
    },
    "touchegg.service": {
        "ru": "Touchegg — это служба, которая распознаёт мультитач-жесты на тачпадах и сенсорных экранах. Например, свайп тремя пальцами для переключения рабочих столов, жест двумя пальцами для масштабирования. Работает на некоторых ноутбуках и планшетах.\n\nНа настольном ПК без сенсорного ввода эта служба не нужна. Ей нечего распознавать, и она просто занимает небольшой объём памяти.\n\nОтключение безопасно. Если у вас ноутбук с тачпадом и вы пользуетесь жестами — оставьте включённой.",
        "en": "Touchegg is a service that recognizes multitouch gestures on touchpads and touchscreens. For example, a three-finger swipe to switch desktops, a two-finger gesture to zoom. It works on some laptops and tablets.\n\nOn a desktop PC without touch input the service is unneeded. There is nothing to recognize, and it just uses a small amount of memory.\n\nDisabling is safe. If you have a laptop with a touchpad and use gestures, keep it enabled.",
    },
    "zfs-zed.service": {
        "ru": "ZFS — это современная файловая система с поддержкой дисковых массивов, контрольных сумм и снапшотов. Она используется на серверах и NAS. ZED — это демон ZFS, который следит за состоянием массивов и предупреждает о проблемах с дисками.\n\nНа домашнем ПК с обычными файловыми системами (ext4, btrfs) ZFS не используется. Значит, и служба ZED не нужна — она не находит массивов и просто висит в фоне.\n\nОтключение безопасно. Не отключайте, если у вас действительно есть ZFS-пулы.",
        "en": "ZFS is a modern file system with disk arrays, checksums and snapshots. It is used on servers and NAS. ZED is the ZFS daemon that watches array health and warns about disk problems.\n\nOn a home PC with conventional file systems (ext4, btrfs) ZFS is not used. So the ZED service is unneeded — it finds no arrays and just idles in the background.\n\nDisabling is safe. Do not disable it if you actually have ZFS pools.",
    },
    "kerneloops.service": {
        "ru": "kerneloops — это служба, которая собирает отчёты о сбоях ядра (kernel oops) и отправляет их разработчикам. Технически она помогает находить и исправлять баги в ядре Linux. Информация уходит на сервер проекта.\n\nНа домашнем ПК эта служба приносит мало пользы. Она лишь добавляет фоновую нагрузку и исходящий трафик. Если ядро у вас падает часто — это скорее повод разобраться с драйверами, чем отправлять отчёты.\n\nОтключение безопасно. Оставьте включённой, если хотите помогать разработчикам ядра.",
        "en": "kerneloops is a service that collects reports about kernel crashes (kernel oops) and sends them to developers. Technically it helps find and fix bugs in the Linux kernel. The information goes to the project's server.\n\nOn a home PC the service brings little benefit. It only adds background load and outgoing traffic. If your kernel crashes often, that is a reason to look into drivers, not to send reports.\n\nDisabling is safe. Keep it enabled if you want to help kernel developers.",
    },
}
STR = {
    "ru": {
        "tab_tune": "Тюнинг", "tab_serv": "Службы", "tab_stat": "Статус",
        "btn_apply": "Применить выбранное", "btn_rollback": "Откатить выбранное",
        "btn_selall": "Выбрать все", "btn_selnone": "Снять выделение",
        "btn_about": "О твикере", "btn_close": "Закрыть",
        "theme_dark": "Тёмная тема", "theme_light": "Светлая тема",
        "lbl_dry": "Сухой прогон", "lbl_terminal": "Терминальный вывод:",
        "lbl_debug": "Отладка",
        "lbl_group": "Группа:", "lbl_value": "Значение:", "lbl_schedule": "Расписание:",
        "ready": "Готово", "running": "Выполнение...", "done": "Готово",
        "applied_yes": "✓ применено", "applied_no": "не применено",
        "btn_file": "файл", "btn_q": "?",
        "menu_copy": "Копировать", "menu_copy_all": "Копировать всё",
        "menu_select_all": "Выделить всё",
        "svc_name": "Служба", "svc_state": "Состояние", "svc_run": "Запуск",
        "svc_desc": "Описание", "svc_help": "?",
        "svc_hint": "Выберите строку, чтобы увидеть описание; «?» — подробности.",
        "svc_on": "работает", "svc_onoff": "не запущена", "svc_off": "остановлена",
        "svc_masked": "заблокирована", "svc_na": "нет в системе",
        "run_yes": "работает", "run_no": "остановлена",
        "svc_on_sel": "Включить выбранные", "svc_off_sel": "Отключить выбранные",
        "stat_refresh": "Обновить статус",
        "st_hw": "ИНФОРМАЦИЯ О СИСТЕМЕ", "st_parts": "РАЗДЕЛЫ СИСТЕМЫ",
        "st_tweaks": "ТВИКИ", "st_services": "СЛУЖБЫ", "st_kernel": "ПАРАМЕТРЫ ЯДРА",
        "st_timer": "Таймер автообновлений",
        "st_enabled": "включён", "st_disabled": "отключён",
        "st_masked": "заблокирован", "st_notfound": "не найден",
        "part_mount": "Раздел", "part_fs": "ФС", "part_total": "Всего",
        "part_free": "Свободно",
        "os_lbl": "ОС", "gpu_lbl": "Видеокарта", "screen_lbl": "Разрешение экрана",
        "swap_lbl": "Файл подкачки", "kernel_lbl": "Ядро", "de_lbl": "Оболочка",
        "ram_lbl": "ОЗУ", "cpu_lbl": "Процессор", "disk_lbl": "Диск",
        "driver_lbl": "Драйвер видеокарты",
        "user_lbl": "Пользователь", "home_lbl": "Домашняя папка",
        "hz": "Гц", "ram_hint": "(тип и частота — после ввода sudo)",
        "w_yes": "да", "w_no": "нет", "no_swap": "отсутствует",
        "gb": "ГБ", "free_w": "свободно", "swap_file": "файл", "swap_part": "раздел",
        "yes": "ПРИМЕНЕНО", "no": "НЕ ПРИМЕНЕНО",
        "sched_cur": "Текущее: %s", "sched_none": "не настроено",
        "mount_title": "Диски: параметры монтирования",
        "mount_desc": "Добавит опцию noatime в /etc/fstab (меньше служебных обращений к диску, полезно для SSD и NTFS; noatime покрывает и каталоги). Вступает в силу после перезагрузки.",
        "steam_title": "Steam: симлинки compatdata",
        "steam_desc": "Создаст ссылку compatdata на ~/.steam/steam/steamapps/compatdata для библиотек Steam на NTFS-разделах, чтобы игры видели данные Proton/Wine из домашней папки.",
        "mount_short": "параметры монтирования", "steam_short": "симлинк compatdata",
        "commit_title": "commit=NN (только ext3/ext4)",
        "commit_desc": "Параметр commit= понимают ТОЛЬКО ext2/ext3/ext4. Для NTFS, FAT32, exFAT, btrfs, xfs он приведёт к ошибке монтирования. Ниже — только подходящие разделы: отметьте те, к которым добавить commit.",
        "commit_none": "Подходящих разделов (ext2/ext3/ext4) не найдено. Твик commit= недоступен.",
        "commit_value_label": "Значение (сек):",
        "commit_fs_ok": "ext4 — поддерживает commit=",
        "commit_fs_bad": "%s — commit= НЕ поддерживается, раздел отключён",
        "kern_sw": "насколько охотно система выгружает память в swap (меньше значение — реже)",
        "kern_vfs": "кэш файлов в памяти",
        "kern_numa": "миграция памяти между ядрами",
        "kern_thp": "крупные блоки памяти",
        "thp_cur": "сейчас: %s",
        "thp_val_always": "всем подряд", "thp_val_madvise": "по запросу",
        "thp_val_never": "выключено",
        "tw_name": "Твик", "kn_param": "Параметр", "kn_val": "Значение",
        "sudo_title": "sudo", "sudo_prompt": "Пароль sudo (попытка %d из 3):",
        "sudo_wrong": "Неверный пароль или нет прав sudo.",
        "autoupdate_warn": "Включено автообновление по расписанию. Отключите встроенное автообновление Mint (mintupdate), иначе обновления будут выполняться дважды.",
        "viewer": "Просмотр файла", "viewer_ext": "Открыть во внешнем редакторе",
        "about_title": "О твикере",
        "about_purpose": "Графическая оболочка тюнинга для Linux Mint / Ubuntu / Debian и других systemd-дистрибутивов: твики производительности, логов, дисков, сети и игр с откатом и бэкапами.",
        "about_author": "Автор", "about_author_name": "Дмитрий Свистунов",
        "about_ver": "Версия",
        "msg_run": "Скрипт уже запущен. Дождитесь завершения.",
        "msg_noopt": "Отметьте хотя бы одну опцию.",
        "msg_sel": "Сначала выберите строки в таблице.",
        "msg_nofile": "Файл ещё не существует. Пути, где опция вносит изменения:",
        "msg_close": "Прервать выполнение и закрыть?",
        "help_title": "О твикере",
    },
    "en": {
        "tab_tune": "Tuning", "tab_serv": "Services", "tab_stat": "Status",
        "btn_apply": "Apply selected", "btn_rollback": "Rollback selected",
        "btn_selall": "Select all", "btn_selnone": "Deselect",
        "btn_about": "About", "btn_close": "Close",
        "theme_dark": "Dark theme", "theme_light": "Light theme",
        "lbl_dry": "Dry run", "lbl_terminal": "Terminal output:",
        "lbl_debug": "Debug",
        "lbl_group": "Group:", "lbl_value": "Value:", "lbl_schedule": "Schedule:",
        "ready": "Ready", "running": "Running...", "done": "Done",
        "applied_yes": "✓ applied", "applied_no": "not applied",
        "btn_file": "file", "btn_q": "?",
        "menu_copy": "Copy", "menu_copy_all": "Copy all",
        "menu_select_all": "Select all",
        "svc_name": "Service", "svc_state": "State", "svc_run": "Running",
        "svc_desc": "Description", "svc_help": "?",
        "svc_hint": "Select a row to see the description; “?” opens details.",
        "svc_on": "running", "svc_onoff": "not running", "svc_off": "stopped",
        "svc_masked": "blocked", "svc_na": "not installed",
        "run_yes": "running", "run_no": "stopped",
        "svc_on_sel": "Enable selected", "svc_off_sel": "Disable selected",
        "stat_refresh": "Refresh status",
        "st_hw": "SYSTEM INFORMATION", "st_parts": "SYSTEM PARTITIONS",
        "st_tweaks": "TWEAKS", "st_services": "SERVICES", "st_kernel": "KERNEL PARAMETERS",
        "st_timer": "Auto-update timer",
        "st_enabled": "enabled", "st_disabled": "disabled",
        "st_masked": "blocked", "st_notfound": "not found",
        "part_mount": "Partition", "part_fs": "FS", "part_total": "Total",
        "part_free": "Free",
        "os_lbl": "OS", "gpu_lbl": "GPU", "screen_lbl": "Screen resolution",
        "swap_lbl": "Swap", "kernel_lbl": "Kernel", "de_lbl": "Desktop",
        "ram_lbl": "RAM", "cpu_lbl": "CPU", "disk_lbl": "Disk",
        "driver_lbl": "GPU driver",
        "user_lbl": "User", "home_lbl": "Home folder",
        "hz": "Hz", "ram_hint": "(type & speed after sudo)",
        "w_yes": "yes", "w_no": "no", "no_swap": "none",
        "gb": "GB", "free_w": "free", "swap_file": "file", "swap_part": "partition",
        "yes": "APPLIED", "no": "NOT APPLIED",
        "sched_cur": "Current: %s", "sched_none": "not configured",
        "mount_title": "Disks: mount options",
        "mount_desc": "Adds the noatime option to /etc/fstab entries (less disk wear; noatime already covers directories). Takes effect after reboot.",
        "steam_title": "Steam: compatdata symlinks",
        "steam_desc": "Creates a compatdata symlink to ~/.steam/steam/steamapps/compatdata for Steam libraries on NTFS partitions so games can see Proton/Wine data from the home folder.",
        "mount_short": "mount options", "steam_short": "compatdata symlink",
        "commit_title": "commit=NN (ext3/ext4 only)",
        "commit_desc": "Only ext2/ext3/ext4 understand commit=. For NTFS, FAT32, exFAT, btrfs, xfs it will fail to mount. Below are only suitable partitions: tick the ones to add commit to.",
        "commit_none": "No suitable partitions (ext2/ext3/ext4) found. commit= tweak is unavailable.",
        "commit_value_label": "Value (sec):",
        "commit_fs_ok": "ext4 — commit= supported",
        "commit_fs_bad": "%s — commit= NOT supported, partition disabled",
        "kern_sw": "how eagerly the system moves memory to swap (lower = less often)",
        "kern_vfs": "file cache in RAM",
        "kern_numa": "memory migration between cores",
        "kern_thp": "large memory blocks",
        "thp_cur": "now: %s",
        "thp_val_always": "always on", "thp_val_madvise": "on request",
        "thp_val_never": "off",
        "tw_name": "Tweak", "kn_param": "Parameter", "kn_val": "Value",
        "sudo_title": "sudo", "sudo_prompt": "sudo password (attempt %d of 3):",
        "sudo_wrong": "Wrong password or no sudo rights.",
        "autoupdate_warn": "Scheduled auto-update enabled. Disable the built-in Mint auto-update (mintupdate), otherwise updates will run twice.",
        "viewer": "File viewer", "viewer_ext": "Open in external editor",
        "about_title": "About",
        "about_purpose": "A graphical tuning shell for Linux Mint / Ubuntu / Debian and other systemd distributions: performance, logs, disk, network and gaming tweaks with rollback and backups.",
        "about_author": "Author", "about_author_name": "Dmitry Svistunov",
        "about_ver": "Version",
        "msg_run": "A job is already running. Wait for it to finish.",
        "msg_noopt": "Tick at least one option.",
        "msg_sel": "Select table rows first.",
        "msg_nofile": "This file appears after applying the option. Paths the option modifies:",
        "msg_close": "Interrupt the job and close?",
        "help_title": "About",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
class MainWindow:
    """Главное окно приложения на Tkinter."""

    def __init__(self, root):
        self.root = root
        self.lang = detect_lang()
        self.theme = "light"
        self.is_running = False
        self.applied = {}
        self.mount_applied = {}
        self.steam_applied = {}
        self.badges = {}
        self.mount_badges = {}
        self.steam_badges = {}
        self.commit_badges = {}
        self.option_widgets = {}
        self.opts_state = {k: BooleanVar(value=False) for k in OPTIONS_META}
        self.mount_state = {}
        self.steam_state = {}
        # разделы с подходящей ФС для commit= (ext2/3/4) и флаги выбора
        self.commit_state = {}
        self.msg_queue = queue.Queue()
        self._ram_cache = None
        self.debug_enabled = False
        self._debug_fh = None
        self._debug_lock = threading.Lock()
        self.sudo = SudoManager()
        self.sudo.prompt_password = self._ask_password
        self.sudo.show_error = lambda m: messagebox.showwarning(
            self.t("sudo_title"),
            self.t("sudo_wrong") + ("\n" + m if m else ""),
            parent=self.root)
        self.state = SystemState()
        self.state.detect()
        self.debug_log_path = os.path.join(self.state.user_home,
                                           "linux-tweaker-debug.log")
        self.corectrl_group = StringVar(
            value=self.state.user_name if self.state.user_name != "root" else "sudo")
        self.swap_value = StringVar(
            value="150" if self.state.swap_type == "zram" else "10")
        self.commit_value = StringVar(value="60")
        self.thp_value = StringVar(value="madvise")
        self.schedule_value = StringVar(value=self._schedule_values()[2])
        mounts, seen = [], set()
        for it in parse_mounts():
            if it["mp"] == "/boot/efi" or (it["fstype"] == "vfat"
                                           and it["mp"].startswith("/boot")):
                continue
            if it["dev"] in seen:
                for m in mounts:
                    if m["dev"] == it["dev"]:
                        m["mps"].append(it["mp"])
                continue
            seen.add(it["dev"])
            it["mps"] = [it["mp"]]
            mounts.append(it)
            self.mount_state[it["mp"]] = BooleanVar(value=False)
        self.mount_items = mounts
        # для commit= доступны только ext2/3/4
        for m in self.mount_items:
            if fs_supports_commit(m.get("fstype", "")):
                for mp in m["mps"]:
                    self.commit_state[mp] = BooleanVar(value=False)
        self.steam_items = []
        for lib in find_steam_libraries(self.state.user_home):
            if self._lib_on_ntfs(lib):
                self.steam_items.append(lib)
                self.steam_state[lib] = BooleanVar(value=False)
        self._notebook = None
        self._tune_inner = None
        self._tune_canvas = None
        self._services_tree = None
        self._services_count_lbl = None
        self._status_view = None
        self._terminal = None
        self._progress = None
        self._status_lbl = None
        self._sched_lbl = None
        self._thp_lbl = None
        self._apply_btn = None
        self._theme_btn = None
        self._lang_btn = None
        self._about_btn = None
        self._dry_var = BooleanVar(value="--dry-run" in sys.argv)
        self._debug_var = BooleanVar(value=False)
        self._build_ui()
        self._apply_theme()
        self._bind_global_wheel()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.log("%s v%s запущен" % (APP_NAME, APP_VERSION), "success")
        self.log("GPU: %s %s" % (self.state.gpu, self.state.gpu_model), "info")
        self.root.after(100, self._process_queue)
        self.root.after(300, lambda: self._run_bg(self._services_work))
        self.root.after(600, lambda: self._run_bg(self._applied_work))
        self.root.after(900, lambda: self._run_bg(self._status_work))

    # ─── i18n и цвета ───────────────────────────────────────────────────
    def t(self, k):
        if k not in STR[self.lang]:
            self._debug_write("MISSING i18n key: %s" % k)
            return k
        return STR[self.lang][k]

    def om(self, k):
        return OPTIONS_META[k][self.lang]

    def colors(self):
        return THEMES[self.theme]

    # ─── отладка ────────────────────────────────────────────────────────
    def _debug_write(self, msg, tb_obj=None):
        with self._debug_lock:
            if not self.debug_enabled or self._debug_fh is None:
                return
            try:
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                self._debug_fh.write("[%s] %s\n" % (ts, msg))
                if tb_obj:
                    traceback.print_exception(*tb_obj, file=self._debug_fh)
                self._debug_fh.flush()
            except Exception:
                pass

    def _toggle_debug(self):
        on = bool(self._debug_var.get())
        self.debug_enabled = on
        if on:
            try:
                with self._debug_lock:
                    self._debug_fh = open(self.debug_log_path, "a", encoding="utf-8")
                    self._debug_fh.write("\n=== BUILD %s | session start %s ===\n"
                                         % (APP_VERSION,
                                            time.strftime("%Y-%m-%d %H:%M:%S")))
                    self._debug_fh.flush()
                self.log("Debug log: %s" % self.debug_log_path, "info")
            except Exception as e:
                self.debug_enabled = False
                with self._debug_lock:
                    self._debug_fh = None
                self.log("Cannot open debug log: %s" % e, "error")
        else:
            with self._debug_lock:
                if self._debug_fh:
                    try:
                        self._debug_fh.write("=== session end %s ===\n"
                                             % time.strftime("%Y-%m-%d %H:%M:%S"))
                        self._debug_fh.close()
                    finally:
                        self._debug_fh = None

    def _ask_password(self, attempt):
        return simpledialog.askstring(
            self.t("sudo_title"),
            self.t("sudo_prompt") % attempt,
            parent=self.root, show="*")

    def _schedule_values(self):
        if self.lang == "ru":
            return ("Отключено", "Ежедневно", "Еженедельно (суббота)",
                    "2 раза в месяц (1 и 15)", "Ежемесячно (1 число)")
        return ("Disabled", "Daily", "Weekly (Saturday)",
                "Twice a month (1 & 15)", "Monthly (1st)")

    # ─── вспомогательные ────────────────────────────────────────────────
    def _lib_on_ntfs(self, lib):
        best, dev, fstype = "", "", ""
        for it in parse_mounts():
            mp = it["mp"]
            if lib == mp or lib.startswith(mp.rstrip("/") + "/") or mp == "/":
                if len(mp) > len(best):
                    best, dev, fstype = mp, it["dev"], it["fstype"]
        if fstype in ("ntfs", "ntfs3", "fuseblk"):
            return True
        if fstype in ("auto", ""):
            fstype = self._fstype_of(dev)
        return fstype in ("ntfs", "ntfs3", "fuseblk")

    def _fstype_of(self, dev):
        known = {"ext2", "ext3", "ext4", "xfs", "btrfs", "f2fs",
                 "ntfs", "ntfs3", "vfat", "exfat", "fuseblk"}
        try:
            res = subprocess.run(["lsblk", "-no", "FSTYPE", dev], capture_output=True,
                                 text=True, timeout=5, env=self._host_env())
            out = [x.strip() for x in res.stdout.strip().splitlines() if x.strip()]
            for ln in out:
                if ln in known:
                    return ln
            return out[0] if out else ""
        except Exception:
            return ""

    def _host_env(self):
        return {k: v for k, v in os.environ.items()
                if k not in ("LD_LIBRARY_PATH", "LD_PRELOAD", "PYTHONPATH",
                             "PYTHONHOME", "APPDIR", "APPIMAGE")}

    def _gpu_driver(self):
        name = ""
        try:
            res = subprocess.run(["lspci", "-k"], capture_output=True, text=True,
                                 timeout=5, env=self._host_env())
            lines = res.stdout.splitlines()
            for i, ln in enumerate(lines):
                if "VGA compatible controller" in ln or "3D controller" in ln:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        m = re.search(r"Kernel driver in use:\s*(\S+)", lines[j])
                        if m:
                            name = m.group(1)
                            break
                    break
        except Exception:
            pass
        ver = ""
        if name == "nvidia":
            try:
                res = subprocess.run(["nvidia-smi", "--query-gpu=driver_version",
                                      "--format=csv,noheader"],
                                     capture_output=True, text=True,
                                     timeout=5, env=self._host_env())
                if res.returncode == 0 and res.stdout.strip():
                    ver = res.stdout.strip().splitlines()[0]
            except Exception:
                pass
        if not ver and name:
            try:
                res = subprocess.run(["modinfo", "-F", "version", name],
                                     capture_output=True, text=True,
                                     timeout=5, env=self._host_env())
                ver = res.stdout.strip()
            except Exception:
                pass
        return name, ver

    def _mesa_version(self):
        try:
            res = subprocess.run(["glxinfo"], capture_output=True, text=True,
                                 timeout=5, env=self._host_env())
            if res.returncode == 0:
                m = re.search(r"Mesa\s+([0-9][0-9a-zA-Z.\-+]*)", res.stdout)
                if m:
                    return m.group(1)
        except Exception:
            pass
        for pkg in ("libglx-mesa0", "libgl1-mesa-dri", "libgl1-mesa-glx"):
            try:
                res = subprocess.run(["dpkg-query", "-W", "-f=${Version}", pkg],
                                     capture_output=True, text=True,
                                     timeout=5, env=self._host_env())
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except Exception:
                continue
        return ""

    def _ram_details(self):
        if self._ram_cache is not None:
            return self._ram_cache
        try:
            res = subprocess.run(["sudo", "-n", "dmidecode", "-t", "17"],
                                 capture_output=True, text=True,
                                 timeout=5, env=self._host_env())
            if res.returncode != 0:
                return ""
            typ, speed = "", ""
            for ln in res.stdout.splitlines():
                s = ln.strip()
                if not typ and s.startswith("Type:"):
                    v = s.split(":", 1)[1].strip()
                    if v and v != "Unknown":
                        typ = v
                if not speed and s.startswith("Configured Memory Speed:"):
                    v = s.split(":", 1)[1].strip()
                    if v and v != "Unknown":
                        speed = v.replace("MT/s", "MHz").strip()
                if typ and speed:
                    break
            self._ram_cache = ", ".join([x for x in (typ, speed) if x])
            return self._ram_cache
        except Exception:
            return ""

    def _thp_current(self):
        try:
            with open("/sys/kernel/mm/transparent_hugepage/enabled", "r",
                      encoding="utf-8", errors="replace") as f:
                m = re.search(r"\[(\w+)\]", f.read())
                return m.group(1) if m else ""
        except Exception:
            return ""

    def _disk_info(self, path):
        try:
            st = os.statvfs(path)
            total = st.f_blocks * st.f_frsize / 1024.0 ** 3
            free = st.f_bavail * st.f_frsize / 1024.0 ** 3
            return total, free
        except Exception:
            return None

    def _swap_size_gb(self):
        try:
            with open("/proc/meminfo", "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("SwapTotal:"):
                        return int(line.split()[1]) / 1024.0 / 1024.0
        except Exception:
            pass
        return None

    def _screen_info(self):
        w = self.root.winfo_screenwidth()
        h = self.root.winfo_screenheight()
        return w, h, 0.0

    # ─── лог и очередь ──────────────────────────────────────────────────
    def log(self, msg, tag="normal"):
        self._debug_write("<%s> %s" % (tag, msg.rstrip()))
        self.msg_queue.put(("log", msg, tag))

    def _run_bg(self, fn, *args):
        threading.Thread(target=self._bg_wrap, args=(fn, args), daemon=True).start()

    def _bg_wrap(self, fn, args):
        try:
            fn(*args)
        except Exception:
            traceback.print_exc()
            self._debug_write("BG CRASH", tb_obj=sys.exc_info())

    def _process_queue(self):
        try:
            while True:
                item = self.msg_queue.get_nowait()
                try:
                    self._handle_msg(item)
                except Exception:
                    traceback.print_exc()
        except queue.Empty:
            pass
        try:
            self.root.after(80, self._process_queue)
        except Exception:
            pass

    def _handle_msg(self, item):
        kind = item[0]
        if kind == "log":
            self._append_log(item[1], item[2])
        elif kind == "statusbar":
            if self._status_lbl is not None:
                self._status_lbl.config(text=item[1])
        elif kind == "progress":
            if self._progress is not None:
                self._progress["value"] = item[1]
        elif kind == "running":
            self.is_running = item[1]
        elif kind == "applied":
            self.applied = item[1]
            self._update_badges()
        elif kind == "mount_applied":
            self.mount_applied = item[1]
            self._update_badges()
        elif kind == "steam_applied":
            self.steam_applied = item[1]
            self._update_badges()
        elif kind == "schedule":
            if self._sched_lbl is not None:
                self._sched_lbl.config(text=self.t("sched_cur") % item[1])
        elif kind == "services_rows":
            self._render_services_rows(item[1])
        elif kind == "status_text":
            self._render_status(item[1])

    def _append_log(self, msg, tag):
        if self._terminal is None:
            return
        self._terminal.configure(state=NORMAL)
        self._terminal.insert(END, msg + ("\n" if not msg.endswith("\n") else ""),
                              tag)
        self._terminal.see(END)
        self._terminal.configure(state=DISABLED)

    # ─── UI ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        c = self.colors()
        self.root.title("%s v%s" % (APP_NAME, APP_VERSION))
        sw, sh, _ = self._screen_info()
        w = min(1080, sw - 40)
        h = min(820, sh - 60)
        self.root.geometry("%dx%d" % (w, h))
        self.root.minsize(min(880, sw - 40), min(640, sh - 60))
        self.root.configure(bg=c["bg"])
        # шапка
        head = Frame(self.root, bg=c["bg"])
        head.pack(fill=X, padx=10, pady=(10, 4))
        self._logo_cv = Canvas(head, width=34, height=34, highlightthickness=0,
                               bg=c["bg"])
        self._logo_cv.pack(side=LEFT)
        self._logo_cv.create_oval(2, 2, 32, 32, fill=c["accent"], outline="")
        self._logo_cv.create_text(17, 17, text="⚙", fill="#ffffff",
                                  font=("DejaVu Sans", 16, "bold"))
        title = Label(head, text=APP_NAME, bg=c["bg"], fg=c["accent"],
                      font=("DejaVu Sans", 16, "bold"))
        title.pack(side=LEFT, padx=(8, 4))
        ver = Label(head, text="v%s" % APP_VERSION, bg=c["bg"], fg=c["gray"],
                    font=("DejaVu Sans", 9))
        ver.pack(side=LEFT, pady=(6, 0))
        self._about_btn = Button(head, text=self.t("btn_about"),
                                 command=self._show_about,
                                 bg=c["button"], fg=c["fg"],
                                 activebackground=c["button_hover"],
                                 relief=FLAT, padx=10, pady=4)
        self._about_btn.pack(side=RIGHT, padx=(4, 0))
        self._theme_btn = Button(head,
                                 text=self.t("theme_dark") if self.theme == "light"
                                 else self.t("theme_light"),
                                 command=self._toggle_theme,
                                 bg=c["button"], fg=c["fg"],
                                 activebackground=c["button_hover"],
                                 relief=FLAT, padx=10, pady=4)
        self._theme_btn.pack(side=RIGHT, padx=(4, 0))
        self._lang_btn = Button(head, text="EN" if self.lang == "ru" else "RU",
                                command=self._toggle_lang,
                                bg=c["button"], fg=c["fg"],
                                activebackground=c["button_hover"],
                                relief=FLAT, padx=10, pady=4)
        self._lang_btn.pack(side=RIGHT, padx=(4, 0))
        self._dry_chk = Checkbutton(head, text=self.t("lbl_dry"),
                                    variable=self._dry_var,
                                    bg=c["bg"], fg=c["yellow"],
                                    activebackground=c["bg"],
                                    activeforeground=c["yellow"],
                                    selectcolor=c["bg"],
                                    font=("DejaVu Sans", 9, "bold"))
        self._dry_chk.pack(side=RIGHT, padx=(4, 0))
        # вкладки
        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill=BOTH, expand=True, padx=10, pady=4)
        self._tab_tune = Frame(self._notebook, bg=c["bg"])
        self._tab_serv = Frame(self._notebook, bg=c["bg"])
        self._tab_stat = Frame(self._notebook, bg=c["bg"])
        self._notebook.add(self._tab_tune, text="  %s  " % self.t("tab_tune"))
        self._notebook.add(self._tab_serv, text="  %s  " % self.t("tab_serv"))
        self._notebook.add(self._tab_stat, text="  %s  " % self.t("tab_stat"))
        self._build_tune_tab()
        self._build_serv_tab()
        self._build_stat_tab()
        # терминал
        term_lbl = Label(self.root, text=self.t("lbl_terminal"),
                         bg=c["bg"], fg=c["gray"], anchor=W,
                         font=("DejaVu Sans", 9))
        term_lbl.pack(fill=X, padx=10, pady=(4, 0))
        self._terminal = scrolledtext.ScrolledText(
            self.root, height=7, wrap="word",
            bg=c["terminal"], fg=c["terminal_fg"],
            insertbackground=c["fg"], relief=FLAT, bd=0,
            font=("DejaVu Sans Mono", 9), state=DISABLED)
        self._terminal.pack(fill=BOTH, expand=False, padx=10, pady=(2, 4))
        for tag, col in (("normal", c["terminal_fg"]), ("success", c["green"]),
                         ("error", c["red"]), ("warning", c["yellow"]),
                         ("info", c["blue"]), ("highlight", c["orange"])):
            self._terminal.tag_configure(tag, foreground=col)
        self._make_copyable(self._terminal)
        # статусная строка
        sb = Frame(self.root, bg=c["bg"])
        sb.pack(fill=X, padx=10, pady=(0, 8))
        self._status_lbl = Label(sb, text=self.t("ready"), bg=c["bg"],
                                 fg=c["gray"], font=("DejaVu Sans", 9))
        self._status_lbl.pack(side=LEFT)
        self._progress = ttk.Progressbar(sb, mode="determinate",
                                         maximum=100, length=200)
        self._progress.pack(side=RIGHT)
        self._debug_chk = Checkbutton(
            sb, text=self.t("lbl_debug"), variable=self._debug_var,
            command=self._toggle_debug,
            bg=c["bg"], fg=c["gray"], activebackground=c["bg"],
            activeforeground=c["gray"], selectcolor=c["bg"],
            font=("DejaVu Sans", 8))
        self._debug_chk.pack(side=RIGHT, padx=(0, 12))

    def _build_tune_tab(self):
        c = self.colors()
        wrap = Frame(self._tab_tune, bg=c["bg"])
        wrap.pack(fill=BOTH, expand=True, padx=6, pady=6)
        bar = Frame(wrap, bg=c["bg"])
        bar.pack(fill=X, pady=(0, 6))
        self._apply_btn = Button(bar, text=self.t("btn_apply"),
                                 command=self.apply_selected,
                                 bg=c["accent"], fg=c["accent_fg"],
                                 activebackground=c["accent2"],
                                 activeforeground=c["accent_fg"],
                                 relief=FLAT, padx=14, pady=6,
                                 font=("DejaVu Sans", 10, "bold"))
        self._apply_btn.pack(side=LEFT, padx=2)
        Button(bar, text=self.t("btn_rollback"), command=self.rollback_selected,
               bg=c["button"], fg=c["fg"], activebackground=c["button_hover"],
               relief=FLAT, padx=12, pady=6).pack(side=LEFT, padx=2)
        Button(bar, text=self.t("btn_selall"), command=self.select_all_options,
               bg=c["button"], fg=c["fg"], activebackground=c["button_hover"],
               relief=FLAT, padx=12, pady=6).pack(side=LEFT, padx=2)
        Button(bar, text=self.t("btn_selnone"), command=self.reset_options,
               bg=c["button"], fg=c["fg"], activebackground=c["button_hover"],
               relief=FLAT, padx=12, pady=6).pack(side=LEFT, padx=2)
        scroll_frame = Frame(wrap, bg=c["bg"])
        scroll_frame.pack(fill=BOTH, expand=True)
        self._tune_canvas = Canvas(scroll_frame, bg=c["panel"],
                                   highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(scroll_frame, orient=VERTICAL,
                            command=self._tune_canvas.yview)
        self._tune_canvas.configure(yscrollcommand=vsb.set)
        self._tune_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)
        self._tune_inner = Frame(self._tune_canvas, bg=c["panel"])
        win_id = self._tune_canvas.create_window((0, 0), window=self._tune_inner,
                                                 anchor=NW)
        self._tune_inner.bind(
            "<Configure>",
            lambda e: self._tune_canvas.configure(
                scrollregion=self._tune_canvas.bbox("all")))
        self._tune_canvas.bind(
            "<Configure>",
            lambda e: self._tune_canvas.itemconfig(win_id, width=e.width))
        cats = {}
        for k in OPTIONS_META:
            cats.setdefault(self.om(k)[2], []).append(k)
        order = CAT_ORDER[self.lang]
        seq = [x for x in order if x in cats] + \
              [x for x in sorted(cats) if x not in order]
        disk_cat = self.om("ntfs3")[2]
        for cat in seq:
            hdr = Label(self._tune_inner, text="─── %s ───" % cat,
                        bg=c["panel"], fg=c["yellow"], anchor=W,
                        font=("DejaVu Sans", 10, "bold"))
            hdr.pack(fill=X, padx=8, pady=(10, 4))
            for k in cats[cat]:
                self._build_option_row(k)
            if cat == disk_cat:
                self._build_disk_extras()
        self._bind_wheel_tree(self._tune_inner)

    def _build_option_row(self, key):
        c = self.colors()
        label, desc, _cat, _short = self.om(key)
        row = Frame(self._tune_inner, bg=c["panel"])
        row.pack(fill=X, padx=8, pady=2)
        top = Frame(row, bg=c["panel"])
        top.pack(fill=X)
        chk = Checkbutton(top, text=label, variable=self.opts_state[key],
                          bg=c["panel"], fg=c["fg"],
                          activebackground=c["panel"],
                          activeforeground=c["fg"],
                          selectcolor=c["panel"],
                          anchor=W, font=("DejaVu Sans", 10))
        chk.pack(side=LEFT)
        self.option_widgets[key] = chk
        if key == "corectrl":
            Label(top, text=self.t("lbl_group"), bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(10, 2))
            Entry(top, textvariable=self.corectrl_group, width=12,
                  bg=c["entry"], fg=c["fg"], relief=FLAT).pack(side=LEFT)
        elif key == "swap":
            Label(top, text=self.t("lbl_value"), bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(10, 2))
            Entry(top, textvariable=self.swap_value, width=6,
                  bg=c["entry"], fg=c["fg"], relief=FLAT).pack(side=LEFT)
        elif key == "thp":
            Label(top, text=self.t("lbl_value"), bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(10, 2))
            combo = ttk.Combobox(top, textvariable=self.thp_value,
                                 values=["always", "madvise", "never"],
                                 state="readonly", width=10,
                                 font=("DejaVu Sans", 9),
                                 style="TCombobox")
            combo.pack(side=LEFT)
            self._thp_lbl = Label(top, text="",
                                  bg=c["panel"], fg=c["gray"],
                                  font=("DejaVu Sans", 8))
            self._thp_lbl.pack(side=LEFT, padx=(6, 0))
        elif key == "autoupdate":
            Label(top, text=self.t("lbl_schedule"), bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(10, 2))
            combo = ttk.Combobox(top, textvariable=self.schedule_value,
                                 values=self._schedule_values(),
                                 state="readonly", width=24,
                                 font=("DejaVu Sans", 9),
                                 style="TCombobox")
            combo.pack(side=LEFT)
            self._sched_lbl = Label(top, text="",
                                    bg=c["panel"], fg=c["gray"],
                                    font=("DejaVu Sans", 8))
            self._sched_lbl.pack(side=LEFT, padx=(6, 0))
        badge = Label(top, text="…", bg=c["panel"], fg=c["gray"],
                      font=("DejaVu Sans", 9, "bold"))
        badge.pack(side=LEFT, padx=(12, 0))
        self.badges[key] = badge

        fb = Button(top, text=self.t("btn_file"),
                    command=lambda k=key: self._open_option_file(k),
                    bg=c["button"], fg=c["blue"],
                    activebackground=c["button_hover"],
                    activeforeground=c["blue"],
                    relief=FLAT, padx=6, pady=0,
                    font=("DejaVu Sans", 8))
        fb._keep_fg = c["blue"]
        fb.pack(side=LEFT, padx=(8, 0))

        qb = Button(top, text=self.t("btn_q"),
                    command=lambda k=key: self._show_option_help(k),
                    bg=c["button"], fg=c["blue"],
                    activebackground=c["button_hover"],
                    activeforeground=c["blue"],
                    relief=FLAT, padx=6, pady=0,
                    font=("DejaVu Sans", 8, "bold"))
        qb._keep_fg = c["blue"]
        qb.pack(side=LEFT, padx=(2, 0))

        dl = Label(row, text=desc, bg=c["panel"], fg=c["gray"],
                   anchor=W, justify=LEFT, wraplength=820,
                   font=("DejaVu Sans", 9))
        dl.pack(fill=X, padx=(24, 0))
    def _build_disk_extras(self):
        c = self.colors()

        # --- параметры монтирования (noatime) ---
        if self.mount_items:
            top = Frame(self._tune_inner, bg=c["panel"])
            top.pack(fill=X, padx=8, pady=(10, 2))
            Label(top, text="─── %s ───" % self.t("mount_title"),
                  bg=c["panel"], fg=c["yellow"], anchor=W,
                  font=("DejaVu Sans", 10, "bold")).pack(side=LEFT)
            fb = Button(top, text=self.t("btn_file"),
                        command=lambda: self._open_path("/etc/fstab"),
                        bg=c["button"], fg=c["blue"],
                        activebackground=c["button_hover"],
                        activeforeground=c["blue"],
                        relief=FLAT, padx=6, pady=0,
                        font=("DejaVu Sans", 8))
            fb._keep_fg = c["blue"]
            fb.pack(side=LEFT, padx=(8, 0))
            qb = Button(top, text=self.t("btn_q"),
                        command=lambda: self._show_option_help("mount"),
                        bg=c["button"], fg=c["blue"],
                        activebackground=c["button_hover"],
                        activeforeground=c["blue"],
                        relief=FLAT, padx=6, pady=0,
                        font=("DejaVu Sans", 8, "bold"))
            qb._keep_fg = c["blue"]
            qb.pack(side=LEFT, padx=(2, 0))
            Label(self._tune_inner, text=self.t("mount_desc"),
                  bg=c["panel"], fg=c["gray"], anchor=W, justify=LEFT,
                  wraplength=820, font=("DejaVu Sans", 9)).pack(
                fill=X, padx=(24, 8), pady=(0, 4))
            for m in self.mount_items:
                row = Frame(self._tune_inner, bg=c["panel"])
                row.pack(fill=X, padx=24, pady=1)
                key = m["mps"][0]
                chk = Checkbutton(row,
                                  text="%s (%s)" % (", ".join(m["mps"]), m["dev"]),
                                  variable=self.mount_state[key],
                                  bg=c["panel"], fg=c["fg"],
                                  activebackground=c["panel"],
                                  activeforeground=c["fg"],
                                  selectcolor=c["panel"],
                                  anchor=W, font=("DejaVu Sans", 10))
                chk.pack(side=LEFT)
                badge = Label(row, text="…", bg=c["panel"], fg=c["gray"],
                              font=("DejaVu Sans", 9, "bold"))
                badge.pack(side=LEFT, padx=(12, 0))
                self.mount_badges[key] = badge

        # --- commit= только для ext2/3/4 ---
        if self.commit_state:
            top = Frame(self._tune_inner, bg=c["panel"])
            top.pack(fill=X, padx=8, pady=(10, 2))
            Label(top, text="─── %s ───" % self.t("commit_title"),
                  bg=c["panel"], fg=c["yellow"], anchor=W,
                  font=("DejaVu Sans", 10, "bold")).pack(side=LEFT)
            fb = Button(top, text=self.t("btn_file"),
                        command=lambda: self._open_path("/etc/fstab"),
                        bg=c["button"], fg=c["blue"],
                        activebackground=c["button_hover"],
                        activeforeground=c["blue"],
                        relief=FLAT, padx=6, pady=0,
                        font=("DejaVu Sans", 8))
            fb._keep_fg = c["blue"]
            fb.pack(side=LEFT, padx=(8, 0))
            qb = Button(top, text=self.t("btn_q"),
                        command=lambda: self._show_option_help("commit"),
                        bg=c["button"], fg=c["blue"],
                        activebackground=c["button_hover"],
                        activeforeground=c["blue"],
                        relief=FLAT, padx=6, pady=0,
                        font=("DejaVu Sans", 8, "bold"))
            qb._keep_fg = c["blue"]
            qb.pack(side=LEFT, padx=(2, 0))
            # строка со значением commit
            top2 = Frame(self._tune_inner, bg=c["panel"])
            top2.pack(fill=X, padx=8, pady=(0, 2))
            Label(top2, text=self.t("commit_value_label"),
                  bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(4, 2))
            Entry(top2, textvariable=self.commit_value, width=6,
                  bg=c["entry"], fg=c["fg"], relief=FLAT).pack(side=LEFT)
            Label(self._tune_inner, text=self.om("commit")[1],
                  bg=c["panel"], fg=c["gray"], anchor=W, justify=LEFT,
                  wraplength=820, font=("DejaVu Sans", 9)).pack(
                fill=X, padx=(24, 8), pady=(0, 4))
            for m in self.mount_items:
                if not fs_supports_commit(m.get("fstype", "")):
                    continue
                for mp in m["mps"]:
                    row = Frame(self._tune_inner, bg=c["panel"])
                    row.pack(fill=X, padx=24, pady=1)
                    chk = Checkbutton(
                        row,
                        text="%s (%s) — %s" % (mp, m["dev"], m["fstype"]),
                        variable=self.commit_state[mp],
                        bg=c["panel"], fg=c["fg"],
                        activebackground=c["panel"],
                        activeforeground=c["fg"],
                        selectcolor=c["panel"],
                        anchor=W, font=("DejaVu Sans", 10))
                    chk.pack(side=LEFT)
                    badge = Label(row, text="…", bg=c["panel"], fg=c["gray"],
                                  font=("DejaVu Sans", 9, "bold"))
                    badge.pack(side=LEFT, padx=(12, 0))
                    self.commit_badges[mp] = badge
        else:
            top = Frame(self._tune_inner, bg=c["panel"])
            top.pack(fill=X, padx=8, pady=(10, 2))
            Label(top, text="─── %s ───" % self.t("commit_title"),
                  bg=c["panel"], fg=c["yellow"], anchor=W,
                  font=("DejaVu Sans", 10, "bold")).pack(side=LEFT)
            Label(self._tune_inner, text=self.t("commit_none"),
                  bg=c["panel"], fg=c["gray"], anchor=W, justify=LEFT,
                  wraplength=820, font=("DejaVu Sans", 9)).pack(
                fill=X, padx=(24, 8), pady=(0, 4))

        # --- Steam ---
        if self.steam_items:
            top = Frame(self._tune_inner, bg=c["panel"])
            top.pack(fill=X, padx=8, pady=(10, 2))
            Label(top, text="─── %s ───" % self.t("steam_title"),
                  bg=c["panel"], fg=c["yellow"], anchor=W,
                  font=("DejaVu Sans", 10, "bold")).pack(side=LEFT)
            qb = Button(top, text=self.t("btn_q"),
                        command=lambda: self._show_option_help("steam"),
                        bg=c["button"], fg=c["blue"],
                        activebackground=c["button_hover"],
                        activeforeground=c["blue"],
                        relief=FLAT, padx=6, pady=0,
                        font=("DejaVu Sans", 8, "bold"))
            qb._keep_fg = c["blue"]
            qb.pack(side=LEFT, padx=(8, 0))
            Label(self._tune_inner, text=self.t("steam_desc"),
                  bg=c["panel"], fg=c["gray"], anchor=W, justify=LEFT,
                  wraplength=820, font=("DejaVu Sans", 9)).pack(
                fill=X, padx=(24, 8), pady=(0, 4))
            for lib in self.steam_items:
                row = Frame(self._tune_inner, bg=c["panel"])
                row.pack(fill=X, padx=24, pady=1)
                chk = Checkbutton(row, text=lib, variable=self.steam_state[lib],
                                  bg=c["panel"], fg=c["fg"],
                                  activebackground=c["panel"],
                                  activeforeground=c["fg"],
                                  selectcolor=c["panel"],
                                  anchor=W, font=("DejaVu Sans", 10))
                chk.pack(side=LEFT)
                badge = Label(row, text="…", bg=c["panel"], fg=c["gray"],
                              font=("DejaVu Sans", 9, "bold"))
                badge.pack(side=LEFT, padx=(12, 0))
                self.steam_badges[lib] = badge
    def _build_serv_tab(self):
        c = self.colors()
        wrap = Frame(self._tab_serv, bg=c["bg"])
        wrap.pack(fill=BOTH, expand=True, padx=6, pady=6)
        bar = Frame(wrap, bg=c["bg"])
        bar.pack(fill=X, pady=(0, 6))
        for text, cmd in ((self.t("btn_selall"), self.select_all_services),
                          (self.t("btn_selnone"), self.clear_services_selection),
                          (self.t("svc_off_sel"), self.disable_selected),
                          (self.t("svc_on_sel"), self.enable_selected)):
            Button(bar, text=text, command=cmd,
                   bg=c["button"], fg=c["fg"],
                   activebackground=c["button_hover"],
                   relief=FLAT, padx=12, pady=6).pack(side=LEFT, padx=2)
        tree_wrap = Frame(wrap, bg=c["bg"])
        tree_wrap.pack(fill=BOTH, expand=True)
        cols = ("name", "state", "run", "desc", "q")
        self._services_tree = ttk.Treeview(tree_wrap, columns=cols,
                                           show="headings",
                                           selectmode="extended")
        self._services_tree.heading("name", text=self.t("svc_name"))
        self._services_tree.heading("state", text=self.t("svc_state"))
        self._services_tree.heading("run", text=self.t("svc_run"))
        self._services_tree.heading("desc", text=self.t("svc_desc"))
        self._services_tree.heading("q", text=self.t("svc_help"))
        self._services_tree.column("name", width=230, anchor=W, stretch=False)
        self._services_tree.column("state", width=140, anchor=W, stretch=False)
        self._services_tree.column("run", width=100, anchor=CENTER, stretch=False)
        self._services_tree.column("desc", width=400, anchor=W, stretch=True)
        self._services_tree.column("q", width=34, anchor=CENTER, stretch=False)
        vsb = ttk.Scrollbar(tree_wrap, orient=VERTICAL,
                            command=self._services_tree.yview)
        self._services_tree.configure(yscrollcommand=vsb.set)
        self._services_tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)
        self._services_tree.tag_configure("ok", foreground=c["green"])
        self._services_tree.tag_configure("warn", foreground=c["yellow"])
        self._services_tree.tag_configure("err", foreground=c["red"])
        self._services_tree.tag_configure("muted", foreground=c["gray"])
        self._services_tree.bind("<<TreeviewSelect>>", self._on_service_select)
        self._services_tree.bind("<ButtonRelease-1>", self._on_service_click)
        hint = Label(wrap, text=self.t("svc_hint"), bg=c["bg"], fg=c["gray"],
                     anchor=W, font=("DejaVu Sans", 9))
        hint.pack(fill=X, pady=(4, 0))
        self._svc_detail = Text(wrap, height=4, wrap="word",
                                bg=c["panel"], fg=c["fg"], relief=FLAT, bd=0,
                                font=("DejaVu Sans", 9))
        self._svc_detail.pack(fill=X, pady=(2, 0))
        self._make_copyable(self._svc_detail)

    def _build_stat_tab(self):
        c = self.colors()
        wrap = Frame(self._tab_stat, bg=c["bg"])
        wrap.pack(fill=BOTH, expand=True, padx=6, pady=6)
        Button(wrap, text=self.t("stat_refresh"),
               command=lambda: self._run_bg(self._status_work),
               bg=c["button"], fg=c["fg"],
               activebackground=c["button_hover"],
               relief=FLAT, padx=12, pady=6).pack(anchor=W, pady=(0, 6))
        self._status_view = scrolledtext.ScrolledText(
            wrap, wrap="word", bg=c["terminal"], fg=c["terminal_fg"],
            relief=FLAT, bd=0, font=("DejaVu Sans Mono", 9), state=DISABLED)
        self._status_view.pack(fill=BOTH, expand=True)
        self._make_copyable(self._status_view)
        self._status_view.tag_configure("head", foreground=c["blue"],
                                        font=("DejaVu Sans Mono", 9, "bold"))
        self._status_view.tag_configure("info", foreground=c["terminal_fg"])
        self._status_view.tag_configure("ok", foreground=c["green"])
        self._status_view.tag_configure("no", foreground=c["red"])
        self._status_view.tag_configure("warn", foreground=c["yellow"])
        self._status_view.tag_configure("muted", foreground=c["gray"])

    # ─── прокрутка колесом ──────────────────────────────────────────────
    def _bind_global_wheel(self):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.root.bind_all(seq, self._on_wheel, add="+")

    def _bind_wheel_tree(self, widget):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(seq, self._on_wheel, add="+")
        for child in widget.winfo_children():
            self._bind_wheel_tree(child)

    def _on_wheel(self, event):
        if self._tune_canvas is None:
            return
        try:
            widget = self.root.winfo_containing(event.x_root, event.y_root)
        except Exception:
            widget = None
        p = widget
        in_tune = False
        while p is not None:
            if p is self._tune_canvas or p is self._tune_inner:
                in_tune = True
                break
            try:
                p = p.master
            except Exception:
                p = None
        if not in_tune:
            return
        d = 0
        num = getattr(event, "num", None)
        if num == 4:
            d = -1
        elif num == 5:
            d = 1
        elif getattr(event, "delta", 0):
            d = -1 if event.delta > 0 else 1
        if d:
            self._tune_canvas.yview_scroll(d, "units")

    # ─── копирование ────────────────────────────────────────────────────
    def _make_copyable(self, w):
        menu = Menu(self.root, tearoff=0)
        menu.add_command(label=self.t("menu_copy"),
                         command=lambda: self._copy_sel(w))
        menu.add_command(label=self.t("menu_copy_all"),
                         command=lambda: self._copy_all(w))
        menu.add_command(label=self.t("menu_select_all"),
                         command=lambda: self._select_all(w))

        def on_copy(_e):
            self._copy_sel(w)
            return "break"

        def on_menu(e):
            try:
                menu.tk_popup(e.x_root, e.y_root)
            finally:
                menu.grab_release()
            return "break"
        for seq in ("<Control-c>", "<Control-C>", "<Control-Insert>"):
            w.bind(seq, on_copy, add="+")
        w.bind("<Button-3>", on_menu, add="+")

    def _copy_sel(self, w):
        try:
            sel = w.get("sel.first", "sel.last")
        except Exception:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(sel)

    def _copy_all(self, w):
        self.root.clipboard_clear()
        self.root.clipboard_append(w.get("1.0", "end-1c"))

    def _select_all(self, w):
        w.tag_add("sel", "1.0", "end-1c")

    # ─── тема ───────────────────────────────────────────────────────────
    def _apply_theme(self):
        c = self.colors()
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        try:
            style.configure("TNotebook", background=c["bg"], borderwidth=0)
            style.configure("TNotebook.Tab", background=c["tab"], foreground=c["fg"],
                            padding=[14, 6])
            style.map("TNotebook.Tab",
                      background=[("selected", c["panel"])],
                      foreground=[("selected", c["accent"])])
            style.configure("Treeview",
                            background=c["panel"],
                            foreground=c["fg"],
                            fieldbackground=c["panel"],
                            rowheight=26)
            style.map("Treeview",
                      background=[("selected", c["sel"])],
                      foreground=[("selected", c["fg"])])
            style.configure("Treeview.Heading",
                            background=c["tab"],
                            foreground=c["fg"])
            style.map("Treeview.Heading",
                      background=[("active", c["tab_hover"])],
                      foreground=[("active", c["fg"])])
            # Combobox: явно задаём и поле, и стрелку, и выпадающий список
            style.configure("TCombobox",
                            fieldbackground=c["entry"],
                            background=c["button"],
                            foreground=c["fg"],
                            arrowcolor=c["fg"],
                            bordercolor=c["border"],
                            lightcolor=c["border"],
                            darkcolor=c["border"],
                            selectbackground=c["entry"],
                            selectforeground=c["fg"])
            style.map("TCombobox",
                      fieldbackground=[("readonly", c["entry"]),
                                       ("disabled", c["button_dis"])],
                      foreground=[("readonly", c["fg"]),
                                  ("disabled", c["fg_dis"])],
                      background=[("readonly", c["button"]),
                                  ("active", c["button_hover"])],
                      arrowcolor=[("readonly", c["fg"]),
                                  ("disabled", c["fg_dis"])])
            style.configure("TProgressbar", troughcolor=c["gray_bg"],
                            background=c["accent"])
            style.configure("Vertical.TScrollbar",
                            background=c["scroll"],
                            troughcolor=c["bg"],
                            bordercolor=c["bg"],
                            arrowcolor=c["fg"],
                            borderwidth=0, arrowsize=12)
            style.map("Vertical.TScrollbar",
                      background=[("active", c["button_hover"])])
            style.configure("Horizontal.TScrollbar",
                            background=c["scroll"],
                            troughcolor=c["bg"],
                            bordercolor=c["bg"],
                            arrowcolor=c["fg"],
                            borderwidth=0, arrowsize=12)
        except Exception:
            pass
        # Tk-виджеты внутри выпадающего списка Combobox:
        try:
            self.root.option_add("*TCombobox*Listbox.background", c["panel"])
            self.root.option_add("*TCombobox*Listbox.foreground", c["fg"])
            self.root.option_add("*TCombobox*Listbox.selectBackground", c["sel"])
            self.root.option_add("*TCombobox*Listbox.selectForeground", c["fg"])
        except Exception:
            pass
    def _repaint_all(self):
        c = self.colors()

        def repaint_panel(w):
            try:
                cls = w.winfo_class()
                inside_tune = self._inside(w, self._tune_inner)

                if cls == "Frame" and w is not self.root:
                    w.configure(bg=c["panel"] if inside_tune else c["bg"])

                elif cls == "Label":
                    # Цвет текста не трогаем — иначе пропадают жёлтые заголовки
                    # категорий, серые описания и цветные бейджи.
                    w.configure(bg=c["panel"] if inside_tune else c["bg"])

                elif cls == "Checkbutton":
                    # Явно задаём цвет текста — в тёмной теме Tk иначе
                    # рисует его почти чёрным.
                    w.configure(
                        bg=c["panel"] if inside_tune else c["bg"],
                        fg=c["fg"],
                        activebackground=c["panel"] if inside_tune else c["bg"],
                        activeforeground=c["fg"],
                        selectcolor=c["panel"] if inside_tune else c["bg"],
                    )

                elif cls == "Button":
                    if w is getattr(self, "_apply_btn", None):
                        # Акцентная кнопка "Применить"
                        w.configure(bg=c["accent"], fg=c["accent_fg"],
                                    activebackground=c["accent2"],
                                    activeforeground=c["accent_fg"])
                    else:
                        # Если у кнопки свой цвет текста (синие "файл"/"?"),
                        # сохраняем его, иначе ставим цвет темы.
                        keep = getattr(w, "_keep_fg", None)
                        w.configure(
                            bg=c["button"],
                            fg=keep if keep else c["fg"],
                            activebackground=c["button_hover"],
                            activeforeground=keep if keep else c["fg"],
                        )

                elif cls == "Entry":
                    w.configure(bg=c["entry"], fg=c["fg"],
                                insertbackground=c["fg"],
                                disabledbackground=c["button_dis"],
                                disabledforeground=c["fg_dis"])

                elif cls == "Text":
                    w.configure(bg=c["terminal"], fg=c["terminal_fg"],
                                insertbackground=c["fg"])

                elif cls == "Canvas":
                    w.configure(bg=c["bg"])

            except Exception:
                pass
            for child in w.winfo_children():
                repaint_panel(child)

        repaint_panel(self.root)

        if self._terminal is not None:
            for tag, col in (("normal", c["terminal_fg"]),
                             ("success", c["green"]),
                             ("error", c["red"]),
                             ("warning", c["yellow"]),
                             ("info", c["blue"]),
                             ("highlight", c["orange"])):
                self._terminal.tag_configure(tag, foreground=col)

        if self._status_view is not None:
            self._status_view.tag_configure("head", foreground=c["blue"],
                                            font=("DejaVu Sans Mono", 9, "bold"))
            self._status_view.tag_configure("info", foreground=c["terminal_fg"])
            self._status_view.tag_configure("ok", foreground=c["green"])
            self._status_view.tag_configure("no", foreground=c["red"])
            self._status_view.tag_configure("warn", foreground=c["yellow"])
            self._status_view.tag_configure("muted", foreground=c["gray"])

        if self._services_tree is not None:
            self._services_tree.tag_configure("ok", foreground=c["green"])
            self._services_tree.tag_configure("warn", foreground=c["yellow"])
            self._services_tree.tag_configure("err", foreground=c["red"])
            self._services_tree.tag_configure("muted", foreground=c["gray"])

        self._apply_theme()

    def _inside(self, w, parent):
        if parent is None:
            return False
        p = w
        while p is not None:
            if p is parent:
                return True
            try:
                p = p.master
            except Exception:
                p = None
        return False

    def _toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        if self._theme_btn is not None:
            self._theme_btn.configure(
                text=self.t("theme_dark") if self.theme == "light"
                else self.t("theme_light"))
        self._repaint_all()

    def _toggle_lang(self):
        current = self.schedule_value.get()
        ru_vals = ("Отключено", "Ежедневно", "Еженедельно (суббота)",
                   "2 раза в месяц (1 и 15)", "Ежемесячно (1 число)")
        en_vals = ("Disabled", "Daily", "Weekly (Saturday)",
                   "Twice a month (1 & 15)", "Monthly (1st)")
        self.lang = "en" if self.lang == "ru" else "ru"
        if self.lang == "ru":
            self.schedule_value.set(dict(zip(en_vals, ru_vals)).get(current, current))
        else:
            self.schedule_value.set(dict(zip(ru_vals, en_vals)).get(current, current))
        self._rebuild_ui()

    def _rebuild_ui(self):
        saved_opts = {k: v.get() for k, v in self.opts_state.items()}
        saved_mounts = {k: v.get() for k, v in self.mount_state.items()}
        saved_steam = {k: v.get() for k, v in self.steam_state.items()}
        saved_commit = {k: v.get() for k, v in self.commit_state.items()}
        for child in self.root.winfo_children():
            child.destroy()
        self.badges = {}
        self.mount_badges = {}
        self.steam_badges = {}
        self.commit_badges = {}
        self.option_widgets = {}
        self._sched_lbl = None
        self._thp_lbl = None
        self._apply_btn = None
        self._theme_btn = None
        self._lang_btn = None
        self._about_btn = None
        self.opts_state = {k: BooleanVar(value=saved_opts.get(k, False))
                           for k in OPTIONS_META}
        for k in list(self.mount_state.keys()):
            self.mount_state[k] = BooleanVar(value=saved_mounts.get(k, False))
        for k in list(self.steam_state.keys()):
            self.steam_state[k] = BooleanVar(value=saved_steam.get(k, False))
        for k in list(self.commit_state.keys()):
            self.commit_state[k] = BooleanVar(value=saved_commit.get(k, False))
        self._build_ui()
        self._apply_theme()
        self._bind_global_wheel()
        self._update_badges()
        self._run_bg(self._services_work)
        self._run_bg(self._applied_work)
        self._run_bg(self._status_work)

    # ─── детект применённых настроек ────────────────────────────────────
    def _applied_work(self):
        ops = SystemOps(self.sudo, self.state, lambda m, t="normal": None, True)
        ops.mount_items = self.mount_items
        ops.commit_targets = [mp for mp in self.commit_state]
        try:
            self.msg_queue.put(("applied", self._detect_applied(ops)))
            self.msg_queue.put(("mount_applied", self._detect_mount()))
            self.msg_queue.put(("steam_applied", self._detect_steam()))
            self.msg_queue.put(("schedule", self._schedule_text()))
        except Exception:
            traceback.print_exc()

    def _schedule_text(self):
        path = "/etc/systemd/system/biweekly-upgrade.timer"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return self.t("sched_none")
        m = re.search(r"^\s*OnCalendar\s*=\s*(.+)$", content, re.M)
        if not m:
            return self.t("sched_none")
        cal = m.group(1).strip()
        names = {"*-*-* 18:30:00": ("Ежедневно", "Daily"),
                 "Sat 18:30:00": ("Еженедельно (суббота)", "Weekly (Saturday)"),
                 "*-*-1,15 18:30:00": ("2 раза в месяц (1 и 15)", "Twice a month (1 & 15)"),
                 "*-*-1 18:30:00": ("Ежемесячно (1 число)", "Monthly (1st)")}
        pair = names.get(cal)
        return pair[0 if self.lang == "ru" else 1] if pair else cal

    def _corectrl_found(self, ops):
        for d in ("/etc/polkit-1/rules.d", "/usr/share/polkit-1/rules.d",
                  "/etc/polkit-1/localauthority/50-local.d"):
            try:
                names = os.listdir(d)
            except Exception:
                names = []
            for fn in names:
                if "corectrl" in fn.lower():
                    return True
                try:
                    with open(os.path.join(d, fn), "r",
                              encoding="utf-8", errors="replace") as f:
                        if "org.corectrl" in f.read():
                            return True
                except Exception:
                    continue
        for p in ("/etc/polkit-1/rules.d/90-corectrl.rules",
                  "/usr/share/polkit-1/rules.d/90-corectrl.rules",
                  "/etc/polkit-1/localauthority/50-local.d/90-corectrl.pkla"):
            cc = ops.read_file(p)
            if cc and "org.corectrl" in cc:
                return True
        try:
            res = subprocess.run(["pkcheck", "--action-id",
                                  "org.corectrl.helper.init", "--process",
                                  str(os.getpid())], capture_output=True,
                                 timeout=5, env=self._host_env())
            if res.returncode == 0:
                return True
        except Exception:
            pass
        return False

    def _detect_applied(self, ops):
        grub = ops.read_file("/etc/default/grub") or ""
        env = ops.read_file("/etc/environment") or ""
        j = ops.read_file("/etc/systemd/journald.conf") or ""
        swp = ops.read_file("/etc/sysctl.d/99-gaming-swap.conf") or ""
        sysc = ops.read_file("/etc/sysctl.d/99-gaming-sysctl.conf") or ""
        bashrc = ops.read_file(os.path.join(self.state.user_home, ".bashrc")) or ""
        mint = ops.read_file("/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf") or ""

        def sv(p):
            try:
                r = subprocess.run(["sysctl", "-n", p], capture_output=True,
                                   text=True, timeout=3, env=self._host_env())
                return r.stdout.strip() if r.returncode == 0 else ""
            except Exception:
                return ""
        m_sw = re.search(r"^\s*vm\.swappiness\s*=\s*(\d+)\s*$", swp, re.M)
        cur = sv("vm.swappiness")
        pw = os.path.join(self.state.user_home, ".config", "pipewire",
                          "pipewire.conf.d", "10-sound.conf")
        return {
            "rsyslog": ops.service_enabled("rsyslog.service") in ("disabled", "masked"),
            "journald": bool(re.search(r"^\s*Storage\s*=\s*volatile\s*$", j, re.M)),
            "audit": "audit=0" in grub,
            "raid": "raid=noautodetect" in grub,
            "nmi_watchdog": "nmi_watchdog=0" in grub,
            "corectrl": self._corectrl_found(ops),
            "ppfeaturemask": "amdgpu.ppfeaturemask" in grub,
            "nvidia_modeset": "nvidia-drm.modeset=1" in grub,
            "vrr": ops.path_exists("/etc/X11/xorg.conf.d/20-amdgpu.conf"),
            "radv": "RADV_PERFTEST=sam" in env,
            "mesa": "MESA_SHADER_CACHE_MAX_SIZE=4G" in env,
            "pipewire": ops.path_exists(pw),
            "bbr": sv("net.ipv4.tcp_congestion_control") == "bbr",
            "swap": (m_sw and m_sw.group(1) in ("10", "150")) or cur in ("10", "150"),
            "zram": ops.path_exists("/etc/systemd/zram-generator.conf")
                    and zram_generator_present(),
            "zswap": "zswap.enabled=1" in grub,
            "thp": (self._thp_current() == self.thp_value.get())
                    or bool(re.search(r"transparent_hugepage=%s\b"
                                      % self.thp_value.get(), grub)),
            "sysctl_cache": bool(re.search(r"^vm\.vfs_cache_pressure=50$", sysc, re.M))
                            or sv("vm.vfs_cache_pressure") == "50",
            "sysctl_numa": bool(re.search(r"^kernel\.numa_balancing=0$", sysc, re.M))
                           or sv("kernel.numa_balancing") == "0",
            "reisub": sv("kernel.sysrq") == "244"
                      or ops.path_exists("/etc/sysctl.d/99-sysrq.conf"),
            "ntsync": self.state.ntsync
                      or ops.path_exists("/etc/modules-load.d/ntsync.conf"),
            "ntfs3": bool(re.search(r"^\s*#\s*blacklist\s+ntfs3\s*$", mint, re.M)),
            "commit": ops._commit_applied(),
            "aliases": "system-tuneup" in bashrc,
            "autoupdate": ops.service_enabled("biweekly-upgrade.timer") == "enabled",
        }

    def _detect_mount(self):
        try:
            with open("/etc/fstab", "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            content = ""
        res = {}
        for m in self.mount_items:
            oks = []
            for mp in m["mps"]:
                ok = False
                for line in lines_in(content):
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    f2 = s.split()
                    if len(f2) >= 4 and f2[1] == mp:
                        opts = f2[3].split(",")
                        ok = "noatime" in opts
                        break
                oks.append(ok)
            res[m["mps"][0]] = all(oks)
        return res

    def _detect_steam(self):
        return {lib: os.path.islink(os.path.join(lib, "compatdata"))
                for lib in self.steam_items}

    # ─── список служб ───────────────────────────────────────────────────
    def _services_work(self):
        ops = SystemOps(self.sudo, self.state, lambda m, t="normal": None,
                        self._dry_var.get())
        rows = []
        for n in SERVICES_ORDER:
            if not ops.unit_exists(n):
                continue
            desc = SERVICES_META[n][self.lang]
            en = ops.service_enabled(n)
            ac = ops.service_active(n)
            if en == "masked":
                st, tag = self.t("svc_masked"), "err"
            elif en == "disabled":
                st, tag = self.t("svc_off"), "muted"
            elif ac == "active":
                st, tag = self.t("svc_on"), "ok"
            else:
                st, tag = self.t("svc_onoff"), "warn"
            run = self.t("run_yes") if ac == "active" else self.t("run_no")
            rows.append((n, st, run, desc, "?", tag))
        self.msg_queue.put(("services_rows", rows))

    def _render_services_rows(self, rows):
        if self._services_tree is None:
            return
        for it in self._services_tree.get_children():
            self._services_tree.delete(it)
        for n, st, run, desc, q, tag in rows:
            self._services_tree.insert("", END, values=(n, st, run, desc, q),
                                       tags=(tag,))

    def _on_service_select(self, _e=None):
        if self._services_tree is None or self._svc_detail is None:
            return
        items = self._services_tree.selection()
        parts = []
        for it in items[:3]:
            name = str(self._services_tree.item(it)["values"][0])
            desc = SERVICES_META.get(name, {}).get(self.lang, "")
            parts.append("%s — %s" % (name, desc))
        self._svc_detail.configure(state=NORMAL)
        self._svc_detail.delete("1.0", END)
        self._svc_detail.insert("1.0", "\n".join(parts))
        self._svc_detail.configure(state=DISABLED)

    def _on_service_click(self, event):
        if self._services_tree is None:
            return
        region = self._services_tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self._services_tree.identify_column(event.x)
        if col != "#5":
            return
        row_id = self._services_tree.identify_row(event.y)
        if not row_id:
            return
        name = str(self._services_tree.item(row_id)["values"][0])
        self._services_tree.selection_remove(self._services_tree.selection())
        self._show_service_help(name)

    # ─── бейджи ─────────────────────────────────────────────────────────
    def _update_badges(self):
        c = self.colors()
        for k, lbl in self.badges.items():
            if lbl is None or not lbl.winfo_exists():
                continue
            self._style_badge(lbl, self.applied.get(k, False), c)
        for k, lbl in self.mount_badges.items():
            if lbl is None or not lbl.winfo_exists():
                continue
            self._style_badge(lbl, self.mount_applied.get(k, False), c)
        for k, lbl in self.steam_badges.items():
            if lbl is None or not lbl.winfo_exists():
                continue
            self._style_badge(lbl, self.steam_applied.get(k, False), c)
        for k, lbl in self.commit_badges.items():
            if lbl is None or not lbl.winfo_exists():
                continue
            self._style_badge(lbl, self.applied.get("commit", False), c)
        if self._thp_lbl is not None and self._thp_lbl.winfo_exists():
            cur = self._thp_current() or "?"
            fmt = self.t("thp_cur")
            self._thp_lbl.config(text=fmt % cur if "%" in fmt else fmt,
                                 fg=c["gray"], bg=c["panel"])

    def _style_badge(self, lbl, ok, c):
        lbl.config(text=self.t("applied_yes") if ok else self.t("applied_no"),
                   bg=c["panel"], fg=c["green"] if ok else c["gray"])

    # ─── apply / rollback ───────────────────────────────────────────────
    def apply_selected(self):
        if self.is_running:
            messagebox.showinfo(APP_NAME, self.t("msg_run"), parent=self.root)
            return
        selected = [k for k, v in self.opts_state.items() if v.get()]
        mount_sel = [mp for m in self.mount_items
                     if self.mount_state[m["mps"][0]].get()
                     for mp in m["mps"]]
        steam_sel = [l for l in self.steam_items if self.steam_state[l].get()]
        commit_sel = [mp for mp, v in self.commit_state.items() if v.get()]
        if not selected and not mount_sel and not steam_sel:
            messagebox.showwarning(APP_NAME, self.t("msg_noopt"), parent=self.root)
            return
        params = {"corectrl_group": self.corectrl_group.get(),
                  "swap_value": self.swap_value.get(),
                  "update_schedule": self.schedule_value.get(),
                  "commit_value": self.commit_value.get(),
                  "thp_value": self.thp_value.get()}
        dry = self._dry_var.get()
        if ("autoupdate" in selected and not dry
                and params["update_schedule"] not in ("Отключено", "Disabled")):
            messagebox.showinfo(APP_NAME, self.t("autoupdate_warn"), parent=self.root)
        if not dry and not self.sudo.ensure():
            self.log("sudo failed", "error")
            return
        self._ram_cache = None
        self.is_running = True
        self._set_running(True)
        self.msg_queue.put(("progress", 0))
        self.msg_queue.put(("statusbar", self.t("running")))
        self._run_bg(self._apply_work, selected, mount_sel, steam_sel,
                     commit_sel, params, dry)

    def _apply_work(self, selected, mount_sel, steam_sel, commit_sel, params, dry):
        ops = SystemOps(self.sudo, self.state, self.log, dry)
        ops.mount_items = self.mount_items
        ops.commit_targets = commit_sel
        # commit-твик не входит в selected — отдельный блок
        total = len(selected) + (1 if mount_sel else 0) + (1 if steam_sel else 0) \
            + (1 if commit_sel else 0)
        if total == 0:
            self._finish_run()
            return
        done = 0
        self.log("=" * 60, "highlight")
        self.log("APPLY START" if self.lang == "en" else "ЗАПУСК ТЮНИНГА",
                 "highlight")
        try:
            for k in selected:
                label = self.om(k)[0]
                self.log("→ %s" % label, "info")
                try:
                    getattr(ops, "apply_%s" % k)(params)
                except Exception as e:
                    self.log("Error in %s: %s" % (k, e), "error")
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if mount_sel:
                self.log("→ %s" % self.t("mount_title"), "info")
                ops.apply_mount_opts(mount_sel)
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if commit_sel:
                self.log("→ %s" % self.t("commit_title"), "info")
                ops.apply_commit(params)
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if steam_sel:
                self.log("→ %s" % self.t("steam_title"), "info")
                ops.apply_steam_links(steam_sel)
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if not dry:
                ops.finalize_grub()
            self.msg_queue.put(("progress", 100))
            self.msg_queue.put(("statusbar", self.t("done")))
            self.log("Done", "success")
        except Exception as e:
            self.log("Critical error: %s" % e, "error")
        finally:
            self._finish_run()

    def rollback_selected(self):
        if self.is_running:
            messagebox.showinfo(APP_NAME, self.t("msg_run"), parent=self.root)
            return
        selected = [k for k, v in self.opts_state.items() if v.get()]
        mount_sel = [mp for m in self.mount_items
                     if self.mount_state[m["mps"][0]].get()
                     for mp in m["mps"]]
        steam_sel = [l for l in self.steam_items if self.steam_state[l].get()]
        commit_sel = [mp for mp, v in self.commit_state.items() if v.get()]
        if not selected and not mount_sel and not steam_sel:
            messagebox.showwarning(APP_NAME, self.t("msg_noopt"), parent=self.root)
            return
        dry = self._dry_var.get()
        if not dry and not self.sudo.ensure():
            self.log("sudo failed", "error")
            return
        self._ram_cache = None
        self.is_running = True
        self._set_running(True)
        self.msg_queue.put(("progress", 0))
        self.msg_queue.put(("statusbar", self.t("running")))
        self._run_bg(self._rollback_work, selected, mount_sel, steam_sel,
                     commit_sel, dry)

    def _rollback_work(self, selected, mount_sel, steam_sel, commit_sel, dry):
        ops = SystemOps(self.sudo, self.state, self.log, dry)
        ops.mount_items = self.mount_items
        ops.commit_targets = commit_sel
        total = len(selected) + (1 if mount_sel else 0) + (1 if steam_sel else 0) \
            + (1 if commit_sel else 0)
        if total == 0:
            self._finish_run()
            return
        done = 0
        self.log("=" * 60, "highlight")
        self.log("ROLLBACK START" if self.lang == "en" else "ЗАПУСК ОТКАТА",
                 "highlight")
        try:
            for k in selected:
                label = self.om(k)[0]
                self.log("→ %s" % label, "info")
                try:
                    getattr(ops, "rollback_%s" % k)()
                except Exception as e:
                    self.log("Error in %s: %s" % (k, e), "error")
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if mount_sel:
                ops.rollback_mount_opts(mount_sel)
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if commit_sel:
                ops.rollback_commit({})
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if steam_sel:
                ops.rollback_steam_links(steam_sel)
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if not dry:
                ops.finalize_grub()
            self.msg_queue.put(("progress", 100))
            self.msg_queue.put(("statusbar", self.t("done")))
            self.log("Rollback done", "success")
        except Exception as e:
            self.log("Critical error: %s" % e, "error")
        finally:
            self._finish_run()

    def _finish_run(self):
        self.is_running = False
        self._set_running(False)
        self._run_bg(self._applied_work)
        self._run_bg(self._status_work)
        self._run_bg(self._services_work)

    def _set_running(self, running):
        if self._apply_btn is not None and self._apply_btn.winfo_exists():
            self._apply_btn.config(state=DISABLED if running else NORMAL)

    # ─── выбор всего / ничего ──────────────────────────────────────────
    def select_all_options(self):
        for k, var in self.opts_state.items():
            w = self.option_widgets.get(k)
            if w is not None and str(w.cget("state")) == "normal":
                var.set(True)
        for var in self.mount_state.values():
            var.set(True)
        for var in self.steam_state.values():
            var.set(True)
        for var in self.commit_state.values():
            var.set(True)

    def reset_options(self):
        for var in self.opts_state.values():
            var.set(False)
        for var in self.mount_state.values():
            var.set(False)
        for var in self.steam_state.values():
            var.set(False)
        for var in self.commit_state.values():
            var.set(False)

    def select_all_services(self):
        if self._services_tree is not None:
            self._services_tree.selection_set(
                self._services_tree.get_children())

    def clear_services_selection(self):
        if self._services_tree is not None:
            self._services_tree.selection_remove(
                self._services_tree.selection())

    def enable_selected(self):
        if self.is_running:
            messagebox.showinfo(APP_NAME, self.t("msg_run"), parent=self.root)
            return
        if self._services_tree is None:
            return
        names = [str(self._services_tree.item(i)["values"][0])
                 for i in self._services_tree.selection()]
        if not names:
            messagebox.showinfo(APP_NAME, self.t("msg_sel"), parent=self.root)
            return
        if not self._dry_var.get() and not self.sudo.ensure():
            return
        self._run_bg(self._enable_work, names)

    def _enable_work(self, names):
        ops = SystemOps(self.sudo, self.state, self.log, self._dry_var.get())
        for name in names:
            if ops.dry_run:
                ops.log("[DRY RUN] enable %s" % name, "warning")
                continue
            ok = ops.sudo_run(["systemctl", "unmask", name], ignore_error=True)
            ok2 = ops.sudo_run(["systemctl", "enable", name], ignore_error=True)
            if ok or ok2:
                ops.log("✓ %s enabled" % name, "success")
            else:
                ops.log("Cannot enable %s" % name, "warning")
        self._run_bg(self._services_work)
        self._run_bg(self._status_work)

    def disable_selected(self):
        if self.is_running:
            messagebox.showinfo(APP_NAME, self.t("msg_run"), parent=self.root)
            return
        if self._services_tree is None:
            return
        names = [str(self._services_tree.item(i)["values"][0])
                 for i in self._services_tree.selection()]
        if not names:
            messagebox.showinfo(APP_NAME, self.t("msg_sel"), parent=self.root)
            return
        if not self._dry_var.get() and not self.sudo.ensure():
            return
        self._run_bg(self._disable_work, names)

    def _disable_work(self, names):
        ops = SystemOps(self.sudo, self.state, self.log, self._dry_var.get())
        for name in names:
            if ops.dry_run:
                ops.log("[DRY RUN] disable %s" % name, "warning")
                continue
            ok = ops.sudo_run(["systemctl", "disable", "--now", name],
                              ignore_error=True)
            if name.startswith("avahi"):
                ok = ops.sudo_run(["systemctl", "mask", name],
                                  ignore_error=True) or ok
            if ok:
                ops.log("✓ %s disabled" % name, "success")
            else:
                ops.log("Cannot disable %s" % name, "warning")
        self._run_bg(self._services_work)
        self._run_bg(self._status_work)

    # ─── статус ─────────────────────────────────────────────────────────
    def _status_work(self):
        try:
            self._status_inner()
        except Exception:
            traceback.print_exc()
            self._debug_write("STATUS CRASH", tb_obj=sys.exc_info())

    def _status_inner(self):
        ops = SystemOps(self.sudo, self.state, lambda m, t="normal": None, True)
        ops.mount_items = self.mount_items
        ops.commit_targets = list(self.commit_state.keys())
        try:
            A = self._detect_applied(ops)
            self.msg_queue.put(("applied", A))
        except Exception:
            A = self.applied

        def sv(p):
            try:
                r = subprocess.run(["sysctl", "-n", p], capture_output=True,
                                   text=True, timeout=3, env=self._host_env())
                return r.stdout.strip() if r.returncode == 0 else "n/a"
            except Exception:
                return "n/a"
        vals = {p: sv(p) for p in ("vm.swappiness", "vm.vfs_cache_pressure",
                                   "kernel.numa_balancing",
                                   "net.ipv4.tcp_congestion_control")}
        rows = []
        rows.append((self.t("st_hw"), "head"))
        bits = 64 if sys.maxsize > 2 ** 32 else 32
        name = ""
        try:
            with open("/etc/os-release", "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        name = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass
        rows.append(("%s: %s (%d-bit)" % (self.t("os_lbl"), name or "Linux", bits),
                     "info"))
        rows.append(("%s: %s" % (self.t("cpu_lbl"), cpu_model()), "info"))
        gpu = self.state.gpu + ((" " + self.state.gpu_model)
                                if self.state.gpu_model else "")
        rows.append(("%s: %s" % (self.t("gpu_lbl"), gpu), "info"))
        drv, drv_ver = self._gpu_driver()
        mesa = self._mesa_version() if drv != "nvidia" else ""
        drv_s = ""
        if drv or mesa:
            pp = []
            if drv:
                pp.append(drv + ((" " + drv_ver) if drv_ver else ""))
            if mesa:
                pp.append("Mesa %s" % mesa)
            drv_s = ", ".join(pp)
        rows.append(("%s: %s" % (self.t("driver_lbl"), drv_s or "n/a"), "info"))
        sw, sh, _ = self._screen_info()
        rows.append(("%s: %dx%d" % (self.t("screen_lbl"), sw, sh), "info"))
        ram = ram_total_gb()
        if ram is not None:
            extra = self._ram_details()
            rs = "%.1f %s" % (ram, self.t("gb"))
            if extra:
                rs += ", %s" % extra
            rows.append(("%s: %s" % (self.t("ram_lbl"), rs), "info"))
        if self.state.has_swap:
            tn = {"file": self.t("swap_file"), "partition": self.t("swap_part"),
                  "zram": "zram"}
            sv_ = tn.get(self.state.swap_type, self.state.swap_type)
            sz = self._swap_size_gb()
            if sz:
                sv_ += ", %.1f %s" % (sz, self.t("gb"))
        else:
            sv_ = self.t("no_swap")
        rows.append(("%s: %s" % (self.t("swap_lbl"), sv_), "info"))
        rows.append(("%s: %s" % (self.t("kernel_lbl"), os.uname().release), "info"))
        rows.append(("%s: %s" % (self.t("de_lbl"), desktop_name()), "info"))
        rows.append((self.t("user_lbl") + ": " + self.state.user_name, "info"))
        rows.append((self.t("home_lbl") + ": " + self.state.user_home, "info"))
        rows.append(("", "info"))
        # разделы
        rows.append((self.t("st_parts"), "head"))
        seen = {}
        for it in parse_mounts():
            if it["mp"] == "/boot/efi" or (it["fstype"] == "vfat"
                                           and it["mp"].startswith("/boot")):
                continue
            seen.setdefault(it["dev"], {"mps": [], "fstype": it["fstype"]})
            seen[it["dev"]]["mps"].append(it["mp"])
        for dev, info in seen.items():
            d = self._disk_info(info["mps"][0])
            if not d:
                continue
            total, free = d
            rows.append(("%s (%s, %s): %.1f %s, %s %.1f %s"
                         % (", ".join(info["mps"]), os.path.basename(dev),
                            info["fstype"], total, self.t("gb"),
                            self.t("free_w"), free, self.t("gb")), "info"))
        rows.append(("", "info"))
        # твики
        rows.append((self.t("st_tweaks"), "head"))
        for k in OPTIONS_META:
            label, _d, _c, short = self.om(k)
            ok = A.get(k, False)
            mark = self.t("yes") if ok else self.t("no")
            rows.append(("%-42s %-14s %s" % (label, mark, short),
                         "ok" if ok else "no"))
        for mp in self.commit_state:
            ok = A.get("commit", False)
            mark = self.t("yes") if ok else self.t("no")
            rows.append(("%-42s %-14s %s" % (self.t("commit_title"), mark, mp),
                         "ok" if ok else "no"))
        for m in self.mount_items:
            ok = self.mount_applied.get(m["mps"][0], False)
            mark = self.t("yes") if ok else self.t("no")
            rows.append(("%-42s %-14s %s"
                         % (self.t("mount_short"), mark, ", ".join(m["mps"])),
                         "ok" if ok else "no"))
        for lib in self.steam_items:
            ok = self.steam_applied.get(lib, False)
            mark = self.t("yes") if ok else self.t("no")
            rows.append(("%-42s %-14s %s" % (self.t("steam_short"), mark, lib),
                         "ok" if ok else "no"))
        rows.append(("", "info"))
        # службы
        rows.append((self.t("st_services"), "head"))
        for name in SERVICES_ORDER:
            if not ops.unit_exists(name):
                continue
            en = ops.service_enabled(name)
            ac = ops.service_active(name)
            if en == "masked":
                tag, word = "no", self.t("svc_masked")
            elif en == "disabled":
                tag, word = "muted", self.t("svc_off")
            elif ac == "active":
                tag, word = "ok", self.t("svc_on")
            else:
                tag, word = "warn", self.t("svc_onoff")
            desc = SERVICES_META[name][self.lang]
            rows.append(("  %s: %s — %s" % (name, word, desc), tag))
        rows.append(("", "info"))
        # параметры ядра
        rows.append((self.t("st_kernel"), "head"))
        kern = [("vm.swappiness", self.t("kern_sw"), A.get("swap", False)),
                ("vm.vfs_cache_pressure", self.t("kern_vfs"),
                 A.get("sysctl_cache", False)),
                ("kernel.numa_balancing", self.t("kern_numa"),
                 A.get("sysctl_numa", False)),
                ("net.ipv4.tcp_congestion_control", "BBR", A.get("bbr", False))]
        for p, dsc, ok in kern:
            rows.append(("  %s = %s — %s [%s]"
                         % (p, vals[p], dsc, self.t("yes") if ok else self.t("no")),
                         "ok" if ok else "no"))
        raw = self._thp_current() or "n/a"
        thp_val = self.t("thp_val_" + raw) if raw in ("always", "madvise", "never") else raw
        disp = "%s (%s)" % (raw, thp_val) if thp_val != raw else raw
        thp_ok = A.get("thp", False)
        rows.append(("  transparent_hugepage = %s — %s [%s]"
                     % (disp, self.t("kern_thp"),
                        self.t("yes") if thp_ok else self.t("no")),
                     "ok" if thp_ok else "no"))
        timer = ops.service_enabled("biweekly-upgrade.timer")
        rows.append(("%s: %s" % (self.t("st_timer"), self._fmt_state(timer)),
                     "ok" if timer == "enabled" else "muted"))
        self.msg_queue.put(("status_text", rows))

    def _render_status(self, rows):
        if self._status_view is None:
            return
        self._status_view.configure(state=NORMAL)
        self._status_view.delete("1.0", END)
        for text, tag in rows:
            self._status_view.insert(END, text + "\n", tag)
        self._status_view.configure(state=DISABLED)

    def _fmt_state(self, value):
        mapping = {
            "enabled": self.t("st_enabled"),
            "disabled": self.t("st_disabled"),
            "masked": self.t("st_masked"),
            "not-found": self.t("st_notfound"),
            "active": self.t("run_yes"),
            "inactive": self.t("run_no"),
        }
        return mapping.get(value, value)

    # ─── диалоги ────────────────────────────────────────────────────────
    def _show_option_help(self, key):
        try:
            txt = OPTIONS_HELP.get(key, {}).get(self.lang, "")
            if not txt:
                self.log("No help for %s" % key, "info")
                return
            if key in OPTIONS_META:
                title = self.om(key)[0]
            elif key == "mount":
                title = self.t("mount_title")
            elif key == "commit":
                title = self.t("commit_title")
            else:
                title = self.t("steam_title")
            self._open_info_dialog(title, txt)
        except Exception as e:
            traceback.print_exc()
            self.log("Help error: %s" % e, "error")

    def _show_service_help(self, name):
        try:
            txt = SERVICES_HELP.get(name, {}).get(self.lang, "")
            if not txt:
                self.log("No help for %s" % name, "info")
                return
            self._open_info_dialog(name, txt)
        except Exception as e:
            traceback.print_exc()
            self.log("Help error: %s" % e, "error")

    def _open_info_dialog(self, title, text):
        c = self.colors()
        dlg = Toplevel(self.root)
        dlg.title(title)
        dlg.transient(self.root)
        sw, sh, _ = self._screen_info()
        dlg.geometry("%dx%d" % (min(720, sw - 60), min(560, sh - 80)))
        dlg.configure(bg=c["bg"])
        txt = scrolledtext.ScrolledText(dlg, wrap="word",
                                        bg=c["terminal"], fg=c["terminal_fg"],
                                        relief=FLAT, bd=0, padx=10, pady=10,
                                        font=("DejaVu Sans", 10))
        txt.pack(fill=BOTH, expand=True, padx=8, pady=8)
        txt.insert("1.0", text)
        txt.configure(state=DISABLED)
        self._make_copyable(txt)
        Button(dlg, text=self.t("btn_close"), command=dlg.destroy,
               bg=c["button"], fg=c["fg"], activebackground=c["button_hover"],
               relief=FLAT, padx=14, pady=6).pack(pady=(0, 8))
        try:
            dlg.grab_set()
        except Exception:
            pass

    def _show_about(self):
        text = ("%s v%s\n\n%s\n\n%s: %s\n%s"
                % (APP_NAME, APP_VERSION, self.t("about_purpose"),
                   self.t("about_author"), self.t("about_author_name"),
                   GITHUB_URL))
        self._open_info_dialog(self.t("about_title"), text)

    def _open_path(self, path):
        ops = SystemOps(self.sudo, self.state, lambda m, t="normal": None, True)
        ops.mount_items = self.mount_items
        content = ops.read_file(path) or ""
        self._show_viewer(path, content)

    def _show_viewer(self, path, content):
        c = self.colors()
        dlg = Toplevel(self.root)
        dlg.title("%s: %s" % (self.t("viewer"), path))
        dlg.transient(self.root)
        sw, sh, _ = self._screen_info()
        dlg.geometry("%dx%d" % (min(760, sw - 40), min(520, sh - 60)))
        dlg.configure(bg=c["bg"])
        txt = scrolledtext.ScrolledText(dlg, wrap="word",
                                        bg=c["terminal"], fg=c["terminal_fg"],
                                        relief=FLAT, bd=0, padx=8, pady=8,
                                        font=("DejaVu Sans Mono", 9))
        txt.pack(fill=BOTH, expand=True, padx=8, pady=8)
        txt.insert("1.0", content)
        txt.configure(state=DISABLED)
        self._make_copyable(txt)
        bf = Frame(dlg, bg=c["bg"])
        bf.pack(fill=X, padx=8, pady=(0, 8))
        Button(bf, text=self.t("viewer_ext"),
               command=lambda: self._open_ext(path),
               bg=c["button"], fg=c["fg"],
               activebackground=c["button_hover"],
               relief=FLAT, padx=12, pady=5).pack(side=LEFT)
        Button(bf, text=self.t("btn_close"), command=dlg.destroy,
               bg=c["button"], fg=c["fg"], activebackground=c["button_hover"],
               relief=FLAT, padx=12, pady=5).pack(side=RIGHT)
        try:
            dlg.grab_set()
        except Exception:
            pass

    def _open_ext(self, path):
        env = self._host_env()
        if os.geteuid() == 0 and self.state.user_name != "root":
            env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
            env["XAUTHORITY"] = os.environ.get("XAUTHORITY") or \
                os.path.join(self.state.user_home, ".Xauthority")
        for cmd in (["xed", path], ["mousepad", path], ["gedit", path],
                    ["kate", path], ["pluma", path], ["xdg-open", path],
                    ["gio", "open", path]):
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 start_new_session=True, env=env)
                return
            except Exception:
                continue
        self.log("Cannot open external editor for %s" % path, "error")

    def _open_option_file(self, key):
        cands = [p.format(home=self.state.user_home)
                 for p in OPTION_FILES.get(key, [])]
        target = next((p for p in cands if os.path.exists(p)), None)
        if target is None and cands:
            if not self.sudo._cached():
                if not self.sudo.ensure():
                    return
            target = next((p for p in cands
                           if subprocess.run(["sudo", "-n", "test", "-e", p],
                                             capture_output=True).returncode == 0),
                          None)
        if target is None:
            if not cands:
                return
            messagebox.showinfo(self.t("viewer"),
                                self.t("msg_nofile") + "\n" + "\n".join(cands),
                                parent=self.root)
            return
        ops = SystemOps(self.sudo, self.state, lambda m, t="normal": None, True)
        ops.mount_items = self.mount_items
        content = ops.read_file(target) or ""
        self._show_viewer(target, content)

    def on_close(self):
        if self.is_running:
            if not messagebox.askyesno(APP_NAME, self.t("msg_close"),
                                       parent=self.root):
                return
        with self._debug_lock:
            if self._debug_fh:
                try:
                    self._debug_fh.write("=== session end %s ===\n"
                                         % time.strftime("%Y-%m-%d %H:%M:%S"))
                    self._debug_fh.flush()
                except Exception:
                    pass
        try:
            self.root.destroy()
        except Exception:
            pass


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("%s v%s\npython3 linux_tweaker.py [--dry-run]"
              % (APP_NAME, APP_VERSION))
        sys.exit(0)
    if os.geteuid() == 0:
        print("WARNING: Linux Tweaker should be run as a normal user, not as root. "
              "Sudo will be requested when needed.", file=sys.stderr)
    root = Tk()
    app = MainWindow(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
