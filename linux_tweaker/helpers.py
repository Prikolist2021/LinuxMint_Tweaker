# -*- coding: utf-8 -*-
"""
Linux Tweaker — вспомогательные модули.

Здесь:
- импорты стандартных библиотек
- утилиты: работа с системой (CPU, RAM, диск, GPU, GPU-драйвер)
- функции парсинга (/proc/mounts, fstab, библиотеки Steam)
- проверки состояния (PipeWire, NMI watchdog, ZFS, tmpfs, NTFS)
- работа с пакетами (installed_packages_set, estimate_packages_size, apt_dry_run_purge)
- SudoManager — управление sudo с keepalive
- SystemState — детект состояния системы (GPU, swap, RAID, PipeWire, и т.д.)
"""

import os
import re
import subprocess
import shutil
import glob
import pwd
import threading
import time
import queue
import fcntl
from datetime import datetime

from .data import (
    COMMIT_OK_FS,
    LOCK_FILE,
    MAX_MAP_COUNT_VALUES,
    SYSTEM_PACKAGE_MASKS,
    TIMEOUT_QUICK,
    TIMEOUT_DPKG_QUERY,
    TIMEOUT_APT_SIMULATE,
    TIMEOUT_PKG_SIZE,
    SUDO_TIMEOUT_DEFAULT,
)

# ─── Утилиты общего назначения ──────────────────────────────────────────────

def compute_ui_scale(root):
    """Возвращает коэффициент масштабирования UI (0.75 – 1.0)."""
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    sx = sw / 1100.0
    sy = sh / 800.0
    return max(0.75, min(sx, sy, 1.0))


def decode_bytes(v):
    """Безопасно декодирует bytes в str (None → '')."""
    if v is None:
        return ""
    return v.decode("utf-8", errors="replace") if isinstance(v, bytes) else str(v)


def lines_in(content):
    """Возвращает список строк (None → [])."""
    if content is None:
        return []
    return content.splitlines()


def cpu_model():
    """Возвращает модель процессора из /proc/cpuinfo."""
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "?"


def ram_total_gb():
    """Возвращает общий объём ОЗУ в ГБ (float) или None."""
    try:
        with open("/proc/meminfo", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    return int(line.split()[1]) / 1024.0 / 1024.0
    except Exception:
        pass
    return None


def desktop_name():
    """Определяет имя рабочей среды (Cinnamon, GNOME, XFCE и т.д.)."""
    d = (os.environ.get("XDG_CURRENT_DESKTOP", "") + " " +
         os.environ.get("DESKTOP_SESSION", "")).lower()
    for key, name in [("cinnamon", "Cinnamon"), ("xfce", "XFCE"), ("mate", "MATE"),
                      ("plasma", "KDE Plasma"), ("kde", "KDE Plasma"),
                      ("gnome", "GNOME"), ("lxqt", "LXQt"), ("lxde", "LXDE"),
                      ("openbox", "Openbox"), ("budgie", "Budgie"),
                      ("pantheon", "Pantheon")]:
        if key in d:
            return name
    return os.environ.get("XDG_CURRENT_DESKTOP", "") or "?"


def detect_lang():
    """Определяет язык системы: 'ru' или 'en'."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "")
        if val:
            return "ru" if val.lower().startswith("ru") else "en"
    return "en"


def is_debian_based():
    """True, если дистрибутив на базе Debian / Ubuntu / Mint."""
    try:
        if os.path.exists("/etc/debian_version"):
            return True
        with open("/etc/os-release", "r", encoding="utf-8", errors="replace") as f:
            content = f.read().lower()
        return ("debian" in content or "ubuntu" in content
                or "mint" in content or "id_like=debian" in content)
    except Exception:
        return False


def zram_generator_present():
    """True, если установлен zram-generator."""
    return any(os.path.exists(p) for p in (
        "/usr/lib/systemd/system-generators/zram-generator",
        "/lib/systemd/system-generators/zram-generator"))


def format_size(bytes_val):
    """Форматирует размер: '500.0 GB' (для статуса)."""
    try:
        b = float(bytes_val)
    except Exception:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024 or unit == "GB":
            return "%.1f %s" % (b, unit)
        b /= 1024.0
    return "?"


def human_size(bytes_val):
    """Компактный размер: '500G', '2.0T', '128M' (для UI тюнинга)."""
    try:
        b = float(bytes_val)
    except Exception:
        return "?"
    for unit, div in (("T", 1024 ** 4), ("G", 1024 ** 3),
                      ("M", 1024 ** 2), ("K", 1024)):
        if b >= div:
            val = b / div
            if val >= 100:
                return "%.0f%s" % (val, unit)
            elif val >= 10:
                return "%.1f%s" % (val, unit)
            else:
                return "%.2f%s" % (val, unit)
    return "%.0fB" % b


def fs_supports_commit(fstype):
    """True, если ФС поддерживает параметр commit= (ext2/3/4)."""
    return (fstype or "").lower() in COMMIT_OK_FS

# ─── Определение съёмных устройств ──────────────────────────────────────────

def _is_removable_device(dev):
    """True, если устройство съёмное (usb-флешка, внешний диск)."""
    try:
        base = os.path.basename(dev)
        m = re.match(r"^(sd[a-z]+|hd[a-z]+|vd[a-z]+|nvme\d+n\d+|mmcblk\d+)", base)
        if not m:
            return False
        disk = m.group(1)
        rm_path = "/sys/block/%s/removable" % disk
        if os.path.exists(rm_path):
            with open(rm_path, "r") as f:
                return f.read().strip() == "1"
    except Exception:
        pass
    return False


# ─── Парсинг /proc/mounts ───────────────────────────────────────────────────

def parse_mounts():
    """Возвращает список словарей {dev, mp, fstype} для смонтированных
    физических разделов (без loop, tmpfs, съёмных)."""
    items = []
    try:
        with open("/proc/mounts", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 4:
                    continue
                dev, mp, fstype, opts = parts[0], parts[1], parts[2], parts[3]
                # Раскодируем escape-последовательности в путях (пробелы, табы)
                mp = mp.replace("\\040", " ").replace("\\011", "\t") \
                       .replace("\\012", "\n").replace("\\134", "\\")
                if not dev.startswith("/dev/"):
                    continue
                if fstype not in ("ext2", "ext3", "ext4", "xfs", "btrfs",
                                  "f2fs", "ntfs", "ntfs3", "vfat", "exfat",
                                  "fuseblk"):
                    continue
                if "rw" not in opts.split(","):
                    continue
                if _is_removable_device(dev):
                    continue
                items.append({"dev": dev, "mp": mp, "fstype": fstype})
    except Exception:
        pass
    return items


def get_block_devices():
    """Список блочных устройств (без loop/ram/zram/sr)."""
    devices = []
    try:
        for name in os.listdir("/sys/block"):
            if name.startswith("loop") or name.startswith("ram") \
                    or name.startswith("zram") or name.startswith("sr"):
                continue
            if not re.match(r"^(sd[a-z]+|hd[a-z]+|vd[a-z]+|nvme\d+n\d+|mmcblk\d+)$",
                            name):
                continue
            devices.append("/dev/" + name)
    except Exception:
        pass
    return devices


# ─── Поиск библиотек Steam ──────────────────────────────────────────────────

def find_steam_libraries(user_home):
    """Возвращает список путей к steamapps/ найденных библиотек Steam."""
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


# ─── Проверки окружения ─────────────────────────────────────────────────────

def pipewire_active():
    """True, если PipeWire используется как звуковой сервер."""
    try:
        r = subprocess.run(["pgrep", "-x", "pipewire"],
                           capture_output=True, timeout=TIMEOUT_QUICK)
        if r.returncode == 0:
            return True
    except Exception:
        pass
    try:
        r = subprocess.run(["pgrep", "-x", "pulseaudio"],
                           capture_output=True, timeout=TIMEOUT_QUICK)
        if r.returncode == 0:
            return False
    except Exception:
        pass
    for pkg in ("pipewire", "pipewire-pulse", "pipewire-bin"):
        try:
            r = subprocess.run(["dpkg-query", "-W", "-f=${Status}", pkg],
                               capture_output=True, text=True,
                               timeout=TIMEOUT_QUICK)
            if r.returncode == 0 and "install ok installed" in r.stdout:
                return True
        except Exception:
            continue
    return False


def nmi_watchdog_active():
    """True, если NMI watchdog сейчас активен."""
    try:
        with open("/proc/sys/kernel/nmi_watchdog", "r") as f:
            return f.read().strip() == "1"
    except Exception:
        return False


def nmi_watchdog_in_grub():
    """True, если nmi_watchdog=0 уже есть в GRUB_CMDLINE_LINUX(_DEFAULT)."""
    try:
        with open("/etc/default/grub", "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return False
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        m = re.match(r"^\s*GRUB_CMDLINE_LINUX(?:_DEFAULT)?=(.*)$", line)
        if m:
            raw = m.group(1).strip().strip('"').strip("'")
            if "nmi_watchdog=0" in raw.split():
                return True
    return False


# ─── ZFS ────────────────────────────────────────────────────────────────────

ZFS_UNITS = [
    "zfs-import-cache.service",
    "zfs-load-module.service",
    "zfs-mount.service",
    "zfs-share.service",
    "zfs-volume-wait.service",
    "zfs-import.target",
    "zfs.target",
    "zfs-volumes.target",
]


def zfs_packages_installed():
    """True, если установлен хотя бы один пакет ZFS."""
    for pkg in ("zfsutils-linux", "zfs-zed"):
        try:
            r = subprocess.run(["dpkg-query", "-W", "-f=${Status}", pkg],
                               capture_output=True, text=True,
                               timeout=TIMEOUT_QUICK)
            if r.returncode == 0 and "install ok installed" in r.stdout:
                return True
        except Exception:
            pass
    return False


def zfs_in_use():
    """True, если ZFS реально используется (пулы, монтирования, fstab)."""
    try:
        r = subprocess.run(["zpool", "list", "-H", "-o", "name"],
                           capture_output=True, text=True, timeout=TIMEOUT_QUICK)
        if r.returncode == 0 and r.stdout.strip():
            return True
    except Exception:
        pass
    try:
        r = subprocess.run(["findmnt", "-t", "zfs", "-n", "-o", "TARGET"],
                           capture_output=True, text=True, timeout=TIMEOUT_QUICK)
        if r.returncode == 0 and r.stdout.strip():
            return True
    except Exception:
        pass
    for path in ("/etc/fstab", "/etc/crypttab"):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                if "zfs" in f.read().lower():
                    return True
        except Exception:
            pass
    return False


def zfs_units_masked():
    """True, если все ZFS-юниты замаскированы."""
    masked = 0
    present = 0
    for unit in ZFS_UNITS:
        try:
            r = subprocess.run(["systemctl", "is-enabled", unit],
                               capture_output=True, text=True,
                               timeout=TIMEOUT_QUICK)
            state = r.stdout.strip()
            if state in ("", "not-found"):
                continue
            present += 1
            if state == "masked":
                masked += 1
        except Exception:
            continue
    return present > 0 and masked == present


def zfs_units_unmasked():
    """True, если хотя бы один ZFS-юнит не замаскирован."""
    for unit in ZFS_UNITS:
        try:
            r = subprocess.run(["systemctl", "is-enabled", unit],
                               capture_output=True, text=True,
                               timeout=TIMEOUT_QUICK)
            if r.stdout.strip() == "masked":
                return False
        except Exception:
            continue
    return True


# ─── tmpfs /tmp ─────────────────────────────────────────────────────────────

def tmpfs_tmp_mounted():
    """True, если /tmp сейчас смонтирован как tmpfs."""
    try:
        with open("/proc/mounts", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3 and parts[1] == "/tmp" and parts[2] == "tmpfs":
                    return True
    except Exception:
        pass
    return False


def fstab_has_tmp_tmpfs():
    """True, если /tmp tmpfs прописан в /etc/fstab."""
    try:
        with open("/etc/fstab", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                parts = s.split()
                if len(parts) >= 3 and parts[1] == "/tmp" and parts[2] == "tmpfs":
                    return True
    except Exception:
        pass
    return False


# ─── Работа с пакетами ──────────────────────────────────────────────────────

def installed_packages_set():
    """Возвращает set установленных пакетов (через dpkg-query)."""
    try:
        r = subprocess.run(["dpkg-query", "-W", "-f=${Package}\t${Status}\n"],
                           capture_output=True, text=True,
                           timeout=TIMEOUT_DPKG_QUERY)
        installed = set()
        for line in r.stdout.splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2 and "install ok installed" in parts[1]:
                installed.add(parts[0])
        return installed
    except Exception:
        return set()


def estimate_packages_size(pkgs):
    """Оценка размера пакетов на диске. '0 B' для пустого списка."""
    if not pkgs:
        return "0 B"
    try:
        r = subprocess.run(["dpkg-query", "-W", "-f=${Installed-Size}\n"] + pkgs,
                           capture_output=True, text=True,
                           timeout=TIMEOUT_PKG_SIZE)
        total_kb = 0
        for line in r.stdout.splitlines():
            try:
                total_kb += int(line.strip())
            except Exception:
                pass
        return format_size(total_kb * 1024)
    except Exception:
        return "?"


def apt_dry_run_purge(pkgs):
    """apt-get -s purge для указанных пакетов.
    Возвращает (explicit, deps, system_hits, ok)."""
    if not pkgs:
        return ([], [], [], True)
    env = dict(os.environ)
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    try:
        r = subprocess.run(["apt-get", "-s", "purge", "-y"] + list(pkgs),
                           capture_output=True, text=True,
                           timeout=TIMEOUT_APT_SIMULATE, env=env)
        if r.returncode != 0:
            return (list(pkgs), [], [], False)
        output = decode_bytes(r.stdout) + "\n" + decode_bytes(r.stderr)
    except Exception:
        return (list(pkgs), [], [], False)
    removed = []
    in_block = False
    for line in output.splitlines():
        if "The following packages will be REMOVED" in line:
            in_block = True
            continue
        if in_block:
            if not line.strip():
                break
            for token in line.split():
                token = token.strip().strip(",")
                if token and not token.startswith("("):
                    removed.append(token)
    removed_norm = [p.split(":")[0] for p in removed]
    explicit = [p for p in pkgs if p in removed_norm]
    deps = [p for p in removed_norm if p not in explicit]
    system_hits = [p for p in removed_norm
                   if any(p.startswith(m) for m in SYSTEM_PACKAGE_MASKS)]
    return (explicit, deps, system_hits, True)


# ─── Блокировка запуска ─────────────────────────────────────────────────────

_lock_fh = None


def acquire_lock():
    """Блокировка через flock — надёжнее PID-файла."""
    global _lock_fh
    lock_path = os.path.expanduser(LOCK_FILE)
    try:
        _lock_fh = open(lock_path, "w")
        fcntl.flock(_lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_fh.write(str(os.getpid()))
        _lock_fh.flush()
        return True
    except (OSError, IOError):
        if _lock_fh is not None:
            try:
                _lock_fh.close()
            except Exception:
                pass
            _lock_fh = None
        return False
    except Exception:
        return True


def release_lock():
    """Снимает блокировку и удаляет lock-файл."""
    global _lock_fh
    try:
        if _lock_fh is not None:
            fcntl.flock(_lock_fh, fcntl.LOCK_UN)
            _lock_fh.close()
            _lock_fh = None
        lock_path = os.path.expanduser(LOCK_FILE)
        if os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except Exception:
                pass
    except Exception:
        pass

# ─── Управление sudo ────────────────────────────────────────────────────────

class SudoManager:
    """Управляет sudo-сессией: аутентификация, keepalive, запуск команд."""

    def __init__(self):
        self.prompt_password = None
        self.show_error = None
        self.authenticated = False
        self._keepalive = False
        self._keepalive_lock = threading.Lock()
        if os.geteuid() == 0:
            self.authenticated = True

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

    def run(self, args, input=None, timeout=None, env=None, log=None):
        """Запускает команду через sudo. log — необязательный коллбэк для
        логирования ('[CMD] ...')."""
        if timeout is None:
            timeout = SUDO_TIMEOUT_DEFAULT
        run_env = env if env is not None else None
        if log is not None:
            try:
                log("[CMD] %s" % " ".join(args))
            except Exception:
                pass
        if os.geteuid() == 0:
            return subprocess.run(list(args), input=input, env=run_env,
                                  capture_output=True, timeout=timeout)
        if not self._cached():
            raise PermissionError("Sudo session expired. Press Apply again.")
        return subprocess.run(["sudo", "-n"] + list(args), input=input,
                              env=run_env, capture_output=True, timeout=timeout)

    def _start_keepalive(self):
        if os.geteuid() == 0:
            return
        with self._keepalive_lock:
            if self._keepalive:
                return
            self._keepalive = True

        def loop():
            while True:
                time.sleep(50)
                try:
                    if not self._cached():
                        break
                    subprocess.run(["sudo", "-n", "-v"],
                                   capture_output=True, timeout=5)
                except Exception:
                    pass
            with self._keepalive_lock:
                self._keepalive = False
            self.authenticated = False
        threading.Thread(target=loop, daemon=True).start()


# ─── Состояние системы ──────────────────────────────────────────────────────

class SystemState:
    """Хранит сведения о системе: GPU, swap, RAID, ZFS, PipeWire и т.д."""

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
        self.is_intel = False
        self.has_itco_module = False
        self.zfs_installed = False
        self.zfs_used = False
        self.pipewire_active = False
        self.nmi_watchdog_active = False
        self.nmi_watchdog_in_grub = False
        self.current_max_map_count = "1048576"
        self.has_ntfs_partitions = False

    def detect(self):
        """Полный детект состояния системы."""
        try:
            self.user_name = self._real_user()
        except Exception:
            self.user_name = "root"
        try:
            self.user_home = pwd.getpwnam(self.user_name).pw_dir
        except Exception:
            self.user_home = os.path.expanduser("~")

        # GPU
        try:
            res = subprocess.run(["lspci"], capture_output=True, text=True,
                                 timeout=TIMEOUT_QUICK)
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

        # RAID
        try:
            if os.path.isfile("/proc/mdstat"):
                with open("/proc/mdstat", "r", encoding="utf-8",
                          errors="replace") as f:
                    if re.search(r"^md\d+", f.read(), re.M):
                        self.has_raid = True
        except Exception:
            pass
        try:
            res = subprocess.run(["lsblk", "-n", "-o", "TYPE"],
                                 capture_output=True, text=True,
                                 timeout=TIMEOUT_QUICK)
            if "raid" in res.stdout:
                self.has_raid = True
        except Exception:
            pass

        # Swap
        self._detect_swap()

        # ntsync
        self.ntsync = os.path.exists("/dev/ntsync")

        # Cinnamon
        d = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        s = os.environ.get("DESKTOP_SESSION", "").lower()
        self.cinnamon = "cinnamon" in d or s == "cinnamon"

        # Flatpak
        self.has_flatpak = bool(shutil.which("flatpak"))

        # Intel
        self.is_intel = False
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8",
                      errors="replace") as f:
                if "GenuineIntel" in f.read():
                    self.is_intel = True
        except Exception:
            pass

        # iTCO_wdt
        self.has_itco_module = False
        try:
            r = subprocess.run(["modinfo", "iTCO_wdt"],
                               capture_output=True, timeout=TIMEOUT_QUICK)
            self.has_itco_module = (r.returncode == 0)
        except Exception:
            pass

        # ZFS
        self.zfs_installed = zfs_packages_installed()
        self.zfs_used = zfs_in_use()

        # PipeWire
        self.pipewire_active = pipewire_active()

        # NMI watchdog
        self.nmi_watchdog_active = nmi_watchdog_active()
        self.nmi_watchdog_in_grub = nmi_watchdog_in_grub()

        # max_map_count
        try:
            with open("/proc/sys/vm/max_map_count", "r") as f:
                self.current_max_map_count = f.read().strip()
        except Exception:
            pass

        # NTFS
        self.has_ntfs_partitions = self._detect_ntfs_partitions()

    def _detect_swap(self):
        """Определяет наличие swap и его тип (zram / partition / file)."""
        self.has_swap = False
        self.swap_type = ""
        try:
            res = subprocess.run(["swapon", "--show=TYPE", "--noheadings"],
                                 capture_output=True, text=True,
                                 timeout=TIMEOUT_QUICK)
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

    def _detect_ntfs_partitions(self):
        """True, если в системе есть NTFS-разделы."""
        try:
            res = subprocess.run(["lsblk", "-no", "FSTYPE"],
                                 capture_output=True, text=True,
                                 timeout=TIMEOUT_QUICK)
            for line in res.stdout.splitlines():
                if line.strip() in ("ntfs", "ntfs3"):
                    return True
        except Exception:
            pass
        return False

    def _real_user(self):
        """Возвращает имя реального пользователя (даже если запущено от root)."""
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
