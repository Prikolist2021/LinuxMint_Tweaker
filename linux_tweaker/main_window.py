# -*- coding: utf-8 -*-
"""
Linux Tweaker — главное окно приложения.

Класс MainWindow:
- строит интерфейс (4 вкладки: Тюнинг, Службы, Статус, Приложения)
- управляет фоновыми задачами через очередь
- обрабатывает действия пользователя (применить, откатить, обновить)
- показывает диалоги (справка, просмотр файла, о программе)
"""

import os
import re
import queue
import glob
import subprocess
import threading
import traceback
import shutil

from tkinter import (Tk, Toplevel, Frame, Label, Button, Checkbutton, Entry,
                     Text, Canvas, Menu, StringVar, BooleanVar,
                     END, NORMAL, DISABLED, LEFT, RIGHT, BOTH, NW, W, E, N, S,
                     X, Y, VERTICAL, HORIZONTAL, FLAT, CENTER, SUNKEN, RAISED,
                     GROOVE, RIDGE, messagebox, simpledialog, PhotoImage)
from tkinter import ttk, scrolledtext

from .data import (
    APP_NAME, APP_VERSION, APP_BUILD_DATE, GITHUB_URL, LICENSE_NAME,
    THEMES, OPTIONS_META, OPTIONS_HELP, CAT_ORDER,
    SERVICES_META, SERVICES_HELP, SERVICES_ORDER,
    OPTION_FILES, STR,
    MAX_MAP_COUNT_VALUES, MAX_MAP_COUNT_DEFAULT,
    SHUTDOWN_TIMEOUT_VALUES, SHUTDOWN_TIMEOUT_DEFAULT,
    PIPEWIRE_PRESETS, PIPEWIRE_PRESET_DEFAULT,
)
from .helpers import (
    compute_ui_scale, cpu_model, ram_total_gb, desktop_name, detect_lang,
    is_debian_based, zram_generator_present,
    parse_mounts, find_steam_libraries, lines_in,
    fs_supports_commit, human_size,
    tmpfs_tmp_mounted, fstab_has_tmp_tmpfs,
    installed_packages_set, estimate_packages_size,
    apt_dry_run_purge,
    acquire_lock, release_lock,
    SudoManager, SystemState,
)
from .ops import SystemOps


class MainWindow:
    """Главное окно твикера."""

    def __init__(self, root):
        self.root = root
        self.scale = compute_ui_scale(root)
        self.lang = detect_lang()
        self.theme = "light"
        self.is_running = False

        # Данные о применённых настройках
        self.applied = {}
        self.mount_applied = {}
        self.steam_applied = {}
        self.commit_applied_per_mp = {}

        # Ссылки на виджеты-бейджи
        self.badges = {}
        self.mount_badges = {}
        self.steam_badges = {}
        self.commit_badges = {}
        self.option_widgets = {}

        # Состояния чекбоксов
        self.opts_state = {k: BooleanVar(value=False) for k in OPTIONS_META}
        self.mount_state = {}
        self.steam_state = {}
        self.commit_state = {}

        # Причины недоступности твиков
        self.disabled_reasons = {}

        # Состояние вкладки служб
        self.svc_checked = set()
        self.svc_rows = []
        self._svc_sort_col = None
        self._svc_sort_reverse = False

        # Фильтры
        self._tune_filter = StringVar(value="")
        self._show_only_available = BooleanVar(value=False)
        self._tune_filter.trace_add("write",
                                    lambda *a: self._rebuild_tune_list())
        self._show_only_available.trace_add("write",
                                            lambda *a: self._rebuild_tune_list())

        # Очередь сообщений из фоновых задач
        self.msg_queue = queue.Queue()
        self._running_tasks = set()
        self._running_lock = threading.Lock()

        # Кэш деталей ОЗУ
        self._ram_cache = None

        # Кнопка удаления ZFS (обновляется)
        self._zfs_button = None

        # Переменные для UI-виджетов
        self.max_map_count_value = StringVar(value=MAX_MAP_COUNT_DEFAULT)
        self.tmpfs_size_value = StringVar(value="512M")
        self.shutdown_timeout_value = StringVar(
            value=SHUTDOWN_TIMEOUT_DEFAULT)
        self.pipewire_preset_value = StringVar(value=PIPEWIRE_PRESET_DEFAULT)

        # Вкладка «Приложения»
        self.apps_checked = set()
        self._installed_packages = None
        self._apps_filter = StringVar(value="")
        self._apps_filter.trace_add("write", lambda *a: self._apps_render())
        self._apps_canvas = None
        self._apps_inner = None
        self._apps_status = None

        # Sudo
        self.sudo = SudoManager()
        self.sudo.prompt_password = self._ask_password
        self.sudo.show_error = lambda m: messagebox.showwarning(
            self.t("sudo_title"),
            self.t("sudo_wrong") + ("\n" + m if m else ""),
            parent=self.root)

        # Состояние системы
        self.state = SystemState()
        self.state.detect()

        # Переменные для UI
        self.corectrl_group = StringVar(
            value=self.state.user_name if self.state.user_name != "root"
            else "sudo")
        self.swap_value = StringVar(
            value="150" if self.state.swap_type == "zram" else "10")
        self.commit_value = StringVar(value="60")
        self.thp_value = StringVar(value="madvise")
        self.schedule_value = StringVar(value=self._schedule_values()[2])

        # Разделы
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
        for m in self.mount_items:
            if fs_supports_commit(m.get("fstype", "")):
                for mp in m["mps"]:
                    self.commit_state[mp] = BooleanVar(value=False)

        # Библиотеки Steam
        self.steam_items = []
        for lib in find_steam_libraries(self.state.user_home):
            if self._lib_on_ntfs(lib):
                self.steam_items.append(lib)
                self.steam_state[lib] = BooleanVar(value=False)

        # Ссылки на виджеты (создаются в _build_ui)
        self._notebook = None
        self._tune_inner = None
        self._tune_canvas = None
        self._services_tree = None
        self._status_view = None
        self._terminal = None
        self._progress = None
        self._status_lbl = None
        self._sched_lbl = None
        self._thp_lbl = None
        self._apply_btn = None
        self._rollback_btn = None
        self._selall_btn = None
        self._selnone_btn = None
        self._theme_btn = None
        self._lang_btn = None
        self._about_btn = None
        self._result_lbl = None
        self._result_hide_id = None

        self._dry_var = BooleanVar(value="--dry-run" in os.sys.argv)
        self._compute_disabled_reasons()
        self._build_ui()
        self._apply_theme()
        self._bind_global_wheel()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.log("%s v%s запущен" % (APP_NAME, APP_VERSION), "success")
        self.log("GPU: %s %s" % (self.state.gpu, self.state.gpu_model), "info")

        self.root.after(100, self._process_queue)
        self.root.after(300, lambda: self._run_bg("services", self._services_work))
        self.root.after(600, lambda: self._run_bg("applied", self._applied_work))
        self.root.after(900, lambda: self._run_bg("status", self._status_work))
        self.root.after(1200,
                        lambda: self._run_bg("apps_load",
                                             self._apps_load_installed))

    # ─── i18n и цвета ───────────────────────────────────────────────────

    def t(self, k):
        if k not in STR[self.lang]:
            return k
        return STR[self.lang][k]

    def om(self, k):
        return OPTIONS_META[k][self.lang]

    def colors(self):
        return THEMES[self.theme]

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

    # ─── Причины недоступности твиков ───────────────────────────────────

    def _compute_disabled_reasons(self):
        r = {}
        if self.state.has_raid:
            r["raid"] = self.t("reason_raid")
        if not getattr(self.state, "is_intel", False):
            r["itco_wdt"] = self.t("reason_itco_not_intel")
        elif not getattr(self.state, "has_itco_module", False):
            r["itco_wdt"] = self.t("reason_itco_no_module")
        elif not getattr(self.state, "nmi_watchdog_active", False):
            r["itco_wdt"] = self.t("reason_itco_watchdog_off")
        elif not getattr(self.state, "nmi_watchdog_in_grub", False):
            r["itco_wdt"] = self.t("reason_itco_grub_missing")
        if not getattr(self.state, "zfs_installed", False):
            r["zfs_services"] = self.t("reason_zfs_not_installed")
        if self.state.gpu not in ("AMD", "Unknown"):
            for k in ("corectrl", "ppfeaturemask", "vrr", "radv"):
                r[k] = self.t("reason_amd_only")
        if self.state.gpu not in ("NVIDIA", "Unknown"):
            r["nvidia_modeset"] = self.t("reason_nvidia_only")
        if not self.state.has_swap:
            r["swap"] = self.t("reason_no_swap")
            r["zswap"] = self.t("reason_no_swap")
        if not zram_generator_present():
            r["zram"] = self.t("reason_no_zram")
        if not os.path.exists("/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"):
            r["ntfs3"] = self.t("reason_mint_only")
        elif not getattr(self.state, "has_ntfs_partitions", False):
            r["ntfs3"] = self.t("reason_no_ntfs")
        if not getattr(self.state, "pipewire_active", False):
            r["pipewire"] = self.t("reason_pipewire_inactive")
        self.disabled_reasons = r

    # ─── Вспомогательные ────────────────────────────────────────────────

    def _lib_on_ntfs(self, lib):
        """True, если библиотека Steam лежит на NTFS."""
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
        """Определяет ФС устройства через lsblk."""
        known = {"ext2", "ext3", "ext4", "xfs", "btrfs", "f2fs",
                 "ntfs", "ntfs3", "vfat", "exfat", "fuseblk"}
        try:
            res = subprocess.run(["lsblk", "-no", "FSTYPE", dev],
                                 capture_output=True, text=True,
                                 timeout=5, env=self._host_env())
            out = [x.strip() for x in res.stdout.strip().splitlines()
                   if x.strip()]
            for ln in out:
                if ln in known:
                    return ln
            return out[0] if out else ""
        except Exception:
            return ""

    def _host_env(self):
        """Окружение без переменных AppImage, чтобы lspci/lsblk работали."""
        return {k: v for k, v in os.environ.items()
                if k not in ("LD_LIBRARY_PATH", "LD_PRELOAD", "PYTHONPATH",
                             "PYTHONHOME", "APPDIR", "APPIMAGE")}

    def _read_text_file(self, path):
        """Читает текстовый файл без sudo (для пользовательских файлов)."""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return ""

    def _gpu_driver(self):
        """Определяет драйвер GPU через lspci -k и его версию."""
        name = ""
        try:
            res = subprocess.run(["lspci", "-k"], capture_output=True,
                                 text=True, timeout=5, env=self._host_env())
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
                res = subprocess.run(["nvidia-smi",
                                      "--query-gpu=driver_version",
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
        """Определяет версию Mesa (через glxinfo или dpkg)."""
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
        """Тип и частота ОЗУ (через dmidecode). Кэширует результат."""
        if self._ram_cache is not None:
            return self._ram_cache
        try:
            res = subprocess.run(["sudo", "-n", "dmidecode", "-t", "17"],
                                 capture_output=True, text=True,
                                 timeout=5, env=self._host_env())
            if res.returncode != 0:
                self._ram_cache = ""
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
            self._ram_cache = ""
            return ""

    def _thp_current(self):
        """Текущее значение transparent_hugepage."""
        try:
            with open("/sys/kernel/mm/transparent_hugepage/enabled", "r",
                      encoding="utf-8", errors="replace") as f:
                m = re.search(r"\[(\w+)\]", f.read())
                return m.group(1) if m else ""
        except Exception:
            return ""

    def _read_sysctl_int(self, path, default=""):
        """Читает sysctl-значение из /proc."""
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except Exception:
            return default

    def _swap_current(self):
        return self._read_sysctl_int("/proc/sys/vm/swappiness", "?")

    def _numa_current(self):
        v = self._read_sysctl_int("/proc/sys/kernel/numa_balancing", "")
        if v == "1":
            return "включено" if self.lang == "ru" else "enabled"
        if v == "0":
            return "отключено" if self.lang == "ru" else "disabled"
        return v or "?"

    def _bbr_current(self):
        return self._read_sysctl_int(
            "/proc/sys/net/ipv4/tcp_congestion_control", "?")

    def _journald_current(self):
        """Определяет текущее хранилище журнала: сначала Storage= в конфиге,
        потом наличие папок."""
        content = self._read_text_file("/etc/systemd/journald.conf")
        m = re.search(r"^\s*Storage\s*=\s*(\w+)\s*$", content, re.M)
        if m:
            val = m.group(1).lower()
            if val == "volatile":
                return self.t("journald_volatile")
            if val == "persistent":
                return self.t("journald_persistent")
            if val == "none":
                return self.t("journald_none")
            # auto — падаем на проверку папок
        if os.path.isdir("/var/log/journal"):
            return self.t("journald_persistent")
        if os.path.isdir("/run/log/journal"):
            return self.t("journald_volatile")
        return self.t("journald_auto")

    def _zswap_current(self):
        """Текущее состояние zswap."""
        try:
            with open("/sys/module/zswap/parameters/enabled", "r") as f:
                en = f.read().strip().lower()
        except Exception:
            return "?"
        if en not in ("y", "1", "yes", "true"):
            return "отключён" if self.lang == "ru" else "off"
        comp = "?"
        try:
            with open("/sys/module/zswap/parameters/compressor", "r") as f:
                comp = f.read().strip()
        except Exception:
            pass
        return ("включён (%s)" % comp) if self.lang == "ru" \
            else ("on (%s)" % comp)

    def _zram_current(self):
        """Активен ли zram."""
        try:
            with open("/proc/swaps", "r", encoding="utf-8",
                      errors="replace") as f:
                for line in f:
                    if "zram" in line:
                        return "активен" if self.lang == "ru" else "active"
        except Exception:
            pass
        return "не активен" if self.lang == "ru" else "inactive"

    def _ntfs3_current(self):
        """Заблокирован или разблокирован ntfs3."""
        path = "/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"
        if not os.path.exists(path):
            return "?"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return "?"
        if re.search(r"^\s*blacklist\s+ntfs3\s*$", content, re.M):
            return "заблокирован" if self.lang == "ru" else "blocked"
        return "разблокирован" if self.lang == "ru" else "unblocked"

    def _ntsync_current(self):
        return (("доступен" if self.lang == "ru" else "available")
                if getattr(self.state, "ntsync", False)
                else ("недоступен" if self.lang == "ru" else "unavailable"))

    def _shutdown_timeout_current(self):
        """Текущий таймаут systemd для остановки служб.
        Берём через systemctl show; fallback — из файла."""
        try:
            res = subprocess.run(
                ["systemctl", "show", "-p", "DefaultTimeoutStopSec",
                 "--value"],
                capture_output=True, text=True, timeout=5,
                env=self._host_env())
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        content = self._read_text_file("/etc/systemd/system.conf")
        m = re.search(r"^\s*DefaultTimeoutStopSec\s*=\s*(\S+)", content, re.M)
        if m:
            return m.group(1)
        return "?"

    def _pipewire_preset_current(self):
        """Определяет, какой пресет сейчас применён в PipeWire.
        Возвращает ключ ('default'/'gaming'/'recording'), 'manual' или None."""
        path = os.path.join(self.state.user_home, ".config", "pipewire",
                            "pipewire.conf.d", "10-sound.conf")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return None
        m_min = re.search(r"min-quantum\s*=\s*(\d+)", content)
        m_q = re.search(r"default\.clock\.quantum\s*=\s*(\d+)", content)
        m_max = re.search(r"max-quantum\s*=\s*(\d+)", content)
        if not (m_min and m_q and m_max):
            return "manual"
        cur = (int(m_min.group(1)), int(m_q.group(1)), int(m_max.group(1)))
        for key, p in PIPEWIRE_PRESETS.items():
            if (p["min"], p["quantum"], p["max"]) == cur:
                return key
        return "manual"

    def _commit_is_effective(self, value):
        """True, если commit=NN даёт эффект (NN не 0 и не 5)."""
        if not value:
            return False
        m = re.match(r"commit=(\d+)$", value)
        if not m:
            return False
        v = m.group(1)
        return v not in ("0", "5")

    def _commit_value_for_ui(self, mp):
        """Обёртка для быстрого чтения commit= для точки монтирования."""
        ops = SystemOps(self.sudo, self.state,
                        lambda m, t="normal": None, True)
        return ops._commit_value_for(mp)

    def _detect_commit_per_mp(self, ops):
        """Определяет, применён ли commit= к каждому разделу."""
        res = {}
        for mp in self.commit_state:
            val = ops._commit_value_for(mp)
            res[mp] = self._commit_is_effective(val)
        return res

    def _detect_pipewire_preset(self, ops):
        """Возвращает текущий применённый пресет PipeWire (или None/manual)."""
        return self._pipewire_preset_current()

    def _shutdown_timeout_applied(self):
        """True, если DefaultTimeoutStopSec в /etc/systemd/system.conf
        раскомментирован и не равен дефолту."""
        content = self._read_text_file("/etc/systemd/system.conf")
        m = re.search(r"^\s*DefaultTimeoutStopSec\s*=\s*(\S+)", content, re.M)
        if not m:
            return False
        val = m.group(1).strip()
        if val == "90s":
            return False
        return val in SHUTDOWN_TIMEOUT_VALUES

    def _disk_info(self, path):
        """Возвращает (total_gb, free_gb) для точки монтирования."""
        try:
            st = os.statvfs(path)
            total = st.f_blocks * st.f_frsize / 1024.0 ** 3
            free = st.f_bavail * st.f_frsize / 1024.0 ** 3
            return total, free
        except Exception:
            return None

    def _swap_size_gb(self):
        """Размер swap в ГБ."""
        try:
            with open("/proc/meminfo", "r", encoding="utf-8",
                      errors="replace") as f:
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

    # ─── Логирование и очередь сообщений ────────────────────────────────

    def log(self, msg, tag="normal"):
        """Кладёт сообщение в очередь для главного потока."""
        self.msg_queue.put(("log", msg, tag))

    def _run_bg(self, name, fn, *args):
        """Запускает фоновую задачу. Не запускает дубликат (P2 #30)."""
        with self._running_lock:
            if name in self._running_tasks:
                return
            self._running_tasks.add(name)

        def wrapper():
            try:
                fn(*args)
            except Exception:
                traceback.print_exc()
            finally:
                with self._running_lock:
                    self._running_tasks.discard(name)

        threading.Thread(target=wrapper, daemon=True).start()

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
        elif kind == "commit_applied":
            self.commit_applied_per_mp = item[1]
            self._update_badges()
        elif kind == "schedule":
            if self._sched_lbl is not None:
                self._sched_lbl.config(text=self.t("sched_cur") % item[1])
        elif kind == "services_rows":
            self.svc_rows = item[1]
            self._render_services_rows()
        elif kind == "status_text":
            self._render_status(item[1])
        elif kind == "apps_redraw":
            self._apps_render()
        elif kind == "apps_confirm":
            body, pkgs = item[1]
            self._apps_show_confirm(body, pkgs)
        elif kind == "result":
            self._show_result(item[1], item[2], item[3])
        elif kind == "toast":
            self.log(item[1][0], item[1][1])

    def _append_log(self, msg, tag):
        if self._terminal is None:
            return
        self._terminal.configure(state=NORMAL)
        self._terminal.insert(END,
                              msg + ("\n" if not msg.endswith("\n") else ""),
                              tag)
        self._terminal.see(END)
        self._terminal.configure(state=DISABLED)

    def _show_result(self, ok, skip, fail):
        """Показывает краткий индикатор результата рядом с кнопкой Применить."""
        if self._result_lbl is None or not self._result_lbl.winfo_exists():
            return
        c = self.colors()
        if fail == 0 and ok > 0:
            mark = "✓"
            col = c["green"]
        elif fail == 0 and ok == 0:
            mark = "•"
            col = c["gray"]
        elif fail < ok:
            mark = "⚠"
            col = c["yellow"]
        else:
            mark = "✗"
            col = c["red"]
        text = "%s  %d ok / %d skip / %d fail" % (mark, ok, skip, fail)
        self._result_lbl.config(text=text, fg=col)
        if self._result_hide_id is not None:
            try:
                self.root.after_cancel(self._result_hide_id)
            except Exception:
                pass
        self._result_hide_id = self.root.after(
            5000, lambda: self._result_lbl.config(text=""))

    # ─── Построение интерфейса ──────────────────────────────────────────

    def _shrink_fonts(self, w):
        """Уменьшает шрифты виджетов при масштабе < 1.0."""
        try:
            f = w.cget("font")
            if f:
                parts = str(f).split()
                if len(parts) >= 2 and parts[-2].isdigit():
                    base = int(parts[-2])
                    new_size = max(7, int(round(base * self.scale)))
                    rest = parts[:-2] + [str(new_size)]
                    if parts[-1] in ("bold", "italic", "roman", "normal",
                                     "underline", "overstrike"):
                        rest += [parts[-1]]
                    w.configure(font=" ".join(rest))
        except Exception:
            pass
        for c in w.winfo_children():
            self._shrink_fonts(c)

    def _build_ui(self):
        c = self.colors()
        self.root.title("%s v%s" % (APP_NAME, APP_VERSION))
        sw, sh, _ = self._screen_info()
        w = min(1080, sw - 40)
        h = min(820, sh - 60)
        self.root.geometry("%dx%d" % (w, h))
        min_w = min(880, sw - 40)
        min_h = min(640, sh - 60)
        self.root.minsize(min_w, min_h)
        self.root.configure(bg=c["bg"])

        # Шапка
        head = Frame(self.root, bg=c["bg"])
        head.pack(fill=X, padx=10, pady=(10, 4))
        self._logo_cv = Canvas(head, width=34, height=34,
                               highlightthickness=0, bg=c["bg"])
        self._logo_cv.pack(side=LEFT)
        self._logo_cv.create_oval(2, 2, 32, 32, fill=c["accent"], outline="")
        self._logo_cv.create_text(17, 17, text="⚙", fill="#ffffff",
                                  font=("DejaVu Sans", 16, "bold"))
        title = Label(head, text=APP_NAME, bg=c["bg"], fg=c["accent"],
                      font=("DejaVu Sans", 16, "bold"))
        title.pack(side=LEFT, padx=(8, 4))
        ver = Label(head, text="v%s" % APP_VERSION,
                    bg=c["bg"], fg=c["gray"], font=("DejaVu Sans", 9))
        ver.pack(side=LEFT, pady=(6, 0))
        self._about_btn = Button(head, text=self.t("btn_about"),
                                 command=self._show_about,
                                 bg=c["button"], fg=c["fg"],
                                 activebackground=c["button_hover"],
                                 relief=FLAT, padx=10, pady=4)
        self._about_btn.pack(side=RIGHT, padx=(4, 0))
        self._theme_btn = Button(
            head,
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

        # Вкладки
        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill=BOTH, expand=True, padx=10, pady=4)
        self._tab_tune = Frame(self._notebook, bg=c["bg"])
        self._tab_serv = Frame(self._notebook, bg=c["bg"])
        self._tab_stat = Frame(self._notebook, bg=c["bg"])
        self._tab_apps = Frame(self._notebook, bg=c["bg"])
        self._notebook.add(self._tab_tune, text="  %s  " % self.t("tab_tune"))
        self._notebook.add(self._tab_serv, text="  %s  " % self.t("tab_serv"))
        self._notebook.add(self._tab_stat, text="  %s  " % self.t("tab_stat"))
        self._notebook.add(self._tab_apps, text="  %s  " % self.t("tab_apps"))

        self._build_tune_tab()
        self._build_serv_tab()
        self._build_stat_tab()
        self._build_apps_tab()

        # Терминальный вывод
        term_lbl = Label(self.root, text=self.t("lbl_terminal"),
                         bg=c["bg"], fg=c["gray"], anchor=W,
                         font=("DejaVu Sans", 9))
        term_lbl.pack(fill=X, padx=10, pady=(4, 0))
        term_h = 7 if sh >= 800 else 4
        self._terminal = scrolledtext.ScrolledText(
            self.root, height=term_h, wrap="word",
            bg=c["terminal"], fg=c["terminal_fg"],
            insertbackground=c["fg"], relief=FLAT, bd=0,
            font=("DejaVu Sans Mono", 9), state=DISABLED)
        self._terminal.pack(fill=BOTH, expand=False, padx=10, pady=(2, 4))
        for tag, col in (("normal", c["terminal_fg"]), ("success", c["green"]),
                         ("error", c["red"]), ("warning", c["yellow"]),
                         ("info", c["blue"]), ("highlight", c["orange"])):
            self._terminal.tag_configure(tag, foreground=col)
        self._make_copyable(self._terminal)

        # Статус-бар
        sb = Frame(self.root, bg=c["bg"])
        sb.pack(fill=X, padx=10, pady=(0, 8))
        self._status_lbl = Label(sb, text=self.t("ready"), bg=c["bg"],
                                 fg=c["gray"], font=("DejaVu Sans", 9))
        self._status_lbl.pack(side=LEFT)
        self._progress = ttk.Progressbar(sb, mode="determinate",
                                         maximum=100, length=200)
        self._progress.pack(side=RIGHT)
        self._dry_chk = Checkbutton(
            sb, text=self.t("lbl_dry"), variable=self._dry_var,
            bg=c["bg"], fg=c["gray"], activebackground=c["bg"],
            activeforeground=c["gray"], selectcolor=c["bg"],
            font=("DejaVu Sans", 8))
        self._dry_chk.pack(side=RIGHT, padx=(0, 12))

        if self.scale < 1.0:
            self.root.after(50, lambda: self._shrink_fonts(self.root))

    def _build_tune_tab(self):
        c = self.colors()
        wrap = Frame(self._tab_tune, bg=c["bg"])
        wrap.pack(fill=BOTH, expand=True, padx=6, pady=6)

        # Верхняя панель кнопок
        bar = Frame(wrap, bg=c["bg"])
        bar.pack(fill=X, pady=(0, 4))
        self._apply_btn = Button(bar, text=self.t("btn_apply"),
                                 command=self.apply_selected,
                                 bg=c["accent"], fg=c["accent_fg"],
                                 activebackground=c["accent2"],
                                 activeforeground=c["accent_fg"],
                                 relief=FLAT, padx=14, pady=6,
                                 font=("DejaVu Sans", 10, "bold"))
        self._apply_btn.pack(side=LEFT, padx=2)
        self._rollback_btn = Button(bar, text=self.t("btn_rollback"),
                                    command=self.rollback_selected,
                                    bg=c["button"], fg=c["fg"],
                                    activebackground=c["button_hover"],
                                    relief=FLAT, padx=12, pady=6)
        self._rollback_btn.pack(side=LEFT, padx=2)
        self._selall_btn = Button(bar, text=self.t("btn_selall"),
                                  command=self.select_all_options,
                                  bg=c["button"], fg=c["fg"],
                                  activebackground=c["button_hover"],
                                  relief=FLAT, padx=12, pady=6)
        self._selall_btn.pack(side=LEFT, padx=2)
        self._selnone_btn = Button(bar, text=self.t("btn_selnone"),
                                   command=self.reset_options,
                                   bg=c["button"], fg=c["fg"],
                                   activebackground=c["button_hover"],
                                   relief=FLAT, padx=12, pady=6)
        self._selnone_btn.pack(side=LEFT, padx=2)
        self._result_lbl = Label(bar, text="", bg=c["bg"], fg=c["gray"],
                                 font=("DejaVu Sans", 10, "bold"))
        self._result_lbl.pack(side=LEFT, padx=(16, 0))

        # Панель поиска
        search_bar = Frame(wrap, bg=c["bg"])
        search_bar.pack(fill=X, pady=(0, 6))
        Label(search_bar, text=self.t("lbl_search"),
              bg=c["bg"], fg=c["gray"],
              font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(2, 4))
        self._search_entry = Entry(search_bar,
                                   textvariable=self._tune_filter,
                                   bg=c["entry"], fg=c["fg"], relief=FLAT,
                                   insertbackground=c["fg"],
                                   font=("DejaVu Sans", 9))
        self._search_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        Button(search_bar, text=self.t("btn_search_clear"),
               command=lambda: self._tune_filter.set(""),
               bg=c["button"], fg=c["fg"],
               activebackground=c["button_hover"],
               relief=FLAT, padx=10, pady=2,
               font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(0, 8))
        Checkbutton(search_bar, text=self.t("lbl_show_only_available"),
                    variable=self._show_only_available,
                    bg=c["bg"], fg=c["gray"],
                    activebackground=c["bg"], activeforeground=c["gray"],
                    selectcolor=c["bg"],
                    font=("DejaVu Sans", 9)).pack(side=LEFT)

        # Скролл-область с твиками
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
        win_id = self._tune_canvas.create_window((0, 0),
                                                 window=self._tune_inner,
                                                 anchor=NW)
        self._tune_inner.bind(
            "<Configure>",
            lambda e: self._tune_canvas.configure(
                scrollregion=self._tune_canvas.bbox("all")))
        self._tune_canvas.bind(
            "<Configure>",
            lambda e: self._tune_canvas.itemconfig(win_id, width=e.width))
        self._rebuild_tune_list()
        self._bind_wheel_tree(self._tune_inner)

    def _build_serv_tab(self):
        c = self.colors()
        wrap = Frame(self._tab_serv, bg=c["bg"])
        wrap.pack(fill=BOTH, expand=True, padx=6, pady=6)
        bar = Frame(wrap, bg=c["bg"])
        bar.pack(fill=X, pady=(0, 6))
        for text, cmd in ((self.t("btn_selall"), self.select_all_services),
                          (self.t("btn_selnone"),
                           self.clear_services_selection),
                          (self.t("svc_off_sel"), self.disable_selected),
                          (self.t("svc_on_sel"), self.enable_selected)):
            Button(bar, text=text, command=cmd,
                   bg=c["button"], fg=c["fg"],
                   activebackground=c["button_hover"],
                   relief=FLAT, padx=12, pady=6).pack(side=LEFT, padx=2)
        tree_wrap = Frame(wrap, bg=c["bg"])
        tree_wrap.pack(fill=BOTH, expand=True)
        cols = ("sel", "name", "state", "run", "desc", "q")
        self._services_tree = ttk.Treeview(tree_wrap, columns=cols,
                                           show="headings",
                                           selectmode="extended")
        self._services_tree.heading("sel", text=self.t("svc_col_sel"))
        self._services_tree.heading(
            "name", text=self.t("svc_name"),
            command=lambda: self._sort_services("name"))
        self._services_tree.heading(
            "state", text=self.t("svc_state"),
            command=lambda: self._sort_services("state"))
        self._services_tree.heading(
            "run", text=self.t("svc_run"),
            command=lambda: self._sort_services("run"))
        self._services_tree.heading(
            "desc", text=self.t("svc_desc"),
            command=lambda: self._sort_services("desc"))
        self._services_tree.heading("q", text=self.t("svc_help"))
        self._services_tree.column("sel", width=30, anchor=CENTER,
                                   stretch=False)
        self._services_tree.column("name", width=220, anchor=W, stretch=False)
        self._services_tree.column("state", width=130, anchor=W,
                                   stretch=False)
        self._services_tree.column("run", width=90, anchor=CENTER,
                                   stretch=False)
        self._services_tree.column("desc", width=380, anchor=W, stretch=True)
        self._services_tree.column("q", width=34, anchor=CENTER,
                                   stretch=False)
        vsb = ttk.Scrollbar(tree_wrap, orient=VERTICAL,
                            command=self._services_tree.yview)
        self._services_tree.configure(yscrollcommand=vsb.set)
        self._services_tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)
        self._services_tree.tag_configure("ok", foreground=c["green"])
        self._services_tree.tag_configure("warn", foreground=c["yellow"])
        self._services_tree.tag_configure("err", foreground=c["red"])
        self._services_tree.tag_configure("muted", foreground=c["gray"])
        self._services_tree.bind("<<TreeviewSelect>>",
                                 self._on_service_select)
        self._services_tree.bind("<ButtonRelease-1>",
                                 self._on_service_click)
        hint = Label(wrap, text=self.t("svc_hint"), bg=c["bg"], fg=c["gray"],
                     anchor=W, font=("DejaVu Sans", 9))
        hint.pack(fill=X, pady=(4, 0))
        self._svc_detail = Text(wrap, height=4, wrap="word",
                                bg=c["panel"], fg=c["fg"],
                                relief=FLAT, bd=0,
                                font=("DejaVu Sans", 9))
        self._svc_detail.pack(fill=X, pady=(2, 0))
        self._make_copyable(self._svc_detail)

    def _build_stat_tab(self):
        c = self.colors()
        wrap = Frame(self._tab_stat, bg=c["bg"])
        wrap.pack(fill=BOTH, expand=True, padx=6, pady=6)
        Button(wrap, text=self.t("stat_refresh"),
               command=lambda: self._run_bg("status", self._status_work),
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
        self._status_view.tag_configure("info",
                                        foreground=c["terminal_fg"])
        self._status_view.tag_configure("ok", foreground=c["green"])
        self._status_view.tag_configure("no", foreground=c["red"])
        self._status_view.tag_configure("warn", foreground=c["yellow"])
        self._status_view.tag_configure("muted", foreground=c["gray"])

    def _build_apps_tab(self):
        c = self.colors()
        wrap = Frame(self._tab_apps, bg=c["bg"])
        wrap.pack(fill=BOTH, expand=True, padx=6, pady=6)
        bar = Frame(wrap, bg=c["bg"])
        bar.pack(fill=X, pady=(0, 4))
        Button(bar, text=self.t("apps_remove"),
               command=self._apps_remove_selected,
               bg=c["orange"], fg=c["accent_fg"],
               activebackground=c["red"],
               activeforeground=c["accent_fg"],
               relief=FLAT, padx=14, pady=6,
               font=("DejaVu Sans", 10, "bold")).pack(side=LEFT, padx=2)
        Button(bar, text=self.t("apps_clear"),
               command=self._apps_clear,
               bg=c["button"], fg=c["fg"],
               activebackground=c["button_hover"],
               relief=FLAT, padx=12, pady=6).pack(side=LEFT, padx=2)
        Button(bar, text=self.t("apps_refresh"),
               command=self._apps_refresh,
               bg=c["button"], fg=c["fg"],
               activebackground=c["button_hover"],
               relief=FLAT, padx=12, pady=6).pack(side=LEFT, padx=2)
        search_bar = Frame(wrap, bg=c["bg"])
        search_bar.pack(fill=X, pady=(0, 6))
        Label(search_bar, text=self.t("apps_search"),
              bg=c["bg"], fg=c["gray"],
              font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(2, 4))
        Entry(search_bar, textvariable=self._apps_filter,
              bg=c["entry"], fg=c["fg"], relief=FLAT,
              insertbackground=c["fg"],
              font=("DejaVu Sans", 9)).pack(side=LEFT, fill=X, expand=True)
        scroll_frame = Frame(wrap, bg=c["bg"])
        scroll_frame.pack(fill=BOTH, expand=True)
        self._apps_canvas = Canvas(scroll_frame, bg=c["panel"],
                                   highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(scroll_frame, orient=VERTICAL,
                            command=self._apps_canvas.yview)
        self._apps_canvas.configure(yscrollcommand=vsb.set)
        self._apps_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)
        self._apps_inner = Frame(self._apps_canvas, bg=c["panel"])
        win_id = self._apps_canvas.create_window((0, 0),
                                                 window=self._apps_inner,
                                                 anchor=NW)
        self._apps_inner.bind(
            "<Configure>",
            lambda e: self._apps_canvas.configure(
                scrollregion=self._apps_canvas.bbox("all")))
        self._apps_canvas.bind(
            "<Configure>",
            lambda e: self._apps_canvas.itemconfig(win_id, width=e.width))
        self._apps_status = Label(wrap, text=self.t("apps_selected_none"),
                                  bg=c["bg"], fg=c["gray"], anchor=W,
                                  font=("DejaVu Sans", 9))
        self._apps_status.pack(fill=X, pady=(4, 0))
        self._apps_render()

    # ─── Вкладка «Тюнинг»: построение списка ────────────────────────────

    def _rebuild_tune_list(self):
        if self._tune_inner is None:
            return
        for child in self._tune_inner.winfo_children():
            child.destroy()
        self.badges = {}
        self.mount_badges = {}
        self.steam_badges = {}
        self.commit_badges = {}
        self.option_widgets = {}
        self._sched_lbl = None
        self._thp_lbl = None
        self._zfs_button = None
        c = self.colors()
        cats = {}
        for k in OPTIONS_META:
            cats.setdefault(self.om(k)[2], []).append(k)
        order = CAT_ORDER[self.lang]
        seq = [x for x in order if x in cats] + \
              [x for x in sorted(cats) if x not in order]
        query = self._tune_filter.get().strip().lower()
        show_only_avail = self._show_only_available.get()
        disk_cat = self.om("ntfs3")[2]
        any_shown = False
        for cat in seq:
            matches = []
            for k in cats[cat]:
                if k == "commit":
                    continue
                label, desc, _c, short = self.om(k)
                if show_only_avail and k in self.disabled_reasons:
                    continue
                if not query or (query in label.lower()
                                 or query in desc.lower()
                                 or query in short.lower()):
                    matches.append(k)
            show_disk_extras = (cat == disk_cat and not query)
            if not matches and not show_disk_extras:
                continue
            any_shown = True
            hdr = Label(self._tune_inner, text="─── %s ───" % cat,
                        bg=c["panel"], fg=c["yellow"], anchor=W,
                        font=("DejaVu Sans", 10, "bold"))
            hdr.pack(fill=X, padx=8, pady=(10, 4))
            for k in matches:
                self._build_option_row(k)
            if show_disk_extras:
                self._build_disk_extras()
        if not any_shown:
            Label(self._tune_inner,
                  text=self.t("search_no_results") % self._tune_filter.get(),
                  bg=c["panel"], fg=c["gray"], anchor=W,
                  font=("DejaVu Sans", 10, "italic")).pack(
                fill=X, padx=24, pady=20)
        self._bind_wheel_tree(self._tune_inner)
        self._update_badges()

    def _build_option_row(self, key):
        c = self.colors()
        label, desc, _cat, _short = self.om(key)
        disabled = key in self.disabled_reasons
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
        if disabled:
            chk.configure(state=DISABLED, fg=c["gray"])
            self.opts_state[key].set(False)
        chk.pack(side=LEFT)
        self.option_widgets[key] = chk
        if disabled:
            Label(top, text="(%s)" % self.disabled_reasons[key],
                  bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 9, "italic")).pack(
                side=LEFT, padx=(8, 0))

        # Особые элементы управления для отдельных твиков
        if key == "corectrl":
            Label(top, text=self.t("lbl_group"), bg=c["panel"],
                  fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(10, 2))
            e = Entry(top, textvariable=self.corectrl_group, width=12,
                      bg=c["entry"], fg=c["fg"], relief=FLAT)
            if disabled:
                e.configure(state=DISABLED, disabledbackground=c["bg"],
                            disabledforeground=c["gray"])
            e.pack(side=LEFT)
        elif key == "swap":
            Label(top, text=self.t("lbl_value"), bg=c["panel"],
                  fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(10, 2))
            e = Entry(top, textvariable=self.swap_value, width=6,
                      bg=c["entry"], fg=c["fg"], relief=FLAT)
            if disabled:
                e.configure(state=DISABLED, disabledbackground=c["bg"],
                            disabledforeground=c["gray"])
            e.pack(side=LEFT)
        elif key == "thp":
            Label(top, text=self.t("lbl_value"), bg=c["panel"],
                  fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(10, 2))
            combo = ttk.Combobox(top, textvariable=self.thp_value,
                                 values=["always", "madvise", "never"],
                                 state="disabled" if disabled else "readonly",
                                 width=10,
                                 font=("DejaVu Sans", 9),
                                 style="TCombobox")
            combo.pack(side=LEFT)
            self._thp_lbl = Label(top, text="",
                                  bg=c["panel"], fg=c["gray"],
                                  font=("DejaVu Sans", 8))
            self._thp_lbl.pack(side=LEFT, padx=(6, 0))
        elif key == "max_map_count":
            Label(top, text=self.t("mmc_value_label"),
                  bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(10, 2))
            combo = ttk.Combobox(top, textvariable=self.max_map_count_value,
                                 values=MAX_MAP_COUNT_VALUES,
                                 state="disabled" if disabled else "readonly",
                                 width=12,
                                 font=("DejaVu Sans", 9),
                                 style="TCombobox")
            combo.pack(side=LEFT)
            cur = getattr(self.state, "current_max_map_count", "")
            if cur:
                Label(top, text=self.t("cur_value") % cur,
                      bg=c["panel"], fg=c["gray"],
                      font=("DejaVu Sans", 8)).pack(side=LEFT, padx=(6, 0))
        elif key == "shutdown_timeout":
            Label(top, text=self.t("lbl_value"), bg=c["panel"],
                  fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(10, 2))
            combo = ttk.Combobox(top, textvariable=self.shutdown_timeout_value,
                                 values=SHUTDOWN_TIMEOUT_VALUES,
                                 state="disabled" if disabled else "readonly",
                                 width=6,
                                 font=("DejaVu Sans", 9),
                                 style="TCombobox")
            combo.pack(side=LEFT)
            cur = self._shutdown_timeout_current()
            if cur:
                Label(top, text=self.t("cur_value") % cur,
                      bg=c["panel"], fg=c["gray"],
                      font=("DejaVu Sans", 8)).pack(side=LEFT, padx=(6, 0))
        elif key == "tmpfs_tmp":
            Label(top, text=self.t("tmpfs_size_label"),
                  bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(10, 2))
            e = Entry(top, textvariable=self.tmpfs_size_value, width=8,
                      bg=c["entry"], fg=c["fg"], relief=FLAT)
            if disabled:
                e.configure(state=DISABLED, disabledbackground=c["bg"],
                            disabledforeground=c["gray"])
            e.pack(side=LEFT)
            if tmpfs_tmp_mounted() or fstab_has_tmp_tmpfs():
                Label(top, text=self.t("tmpfs_already"),
                      bg=c["panel"], fg=c["green"],
                      font=("DejaVu Sans", 8)).pack(side=LEFT, padx=(6, 0))
        elif key == "autoupdate":
            Label(top, text=self.t("lbl_schedule"), bg=c["panel"],
                  fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(10, 2))
            combo = ttk.Combobox(top, textvariable=self.schedule_value,
                                 values=self._schedule_values(),
                                 state="disabled" if disabled else "readonly",
                                 width=24,
                                 font=("DejaVu Sans", 9),
                                 style="TCombobox")
            combo.pack(side=LEFT)
            self._sched_lbl = Label(top, text="",
                                    bg=c["panel"], fg=c["gray"],
                                    font=("DejaVu Sans", 8))
            self._sched_lbl.pack(side=LEFT, padx=(6, 0))
        elif key == "pipewire":
            Label(top, text=self.t("lbl_mode"), bg=c["panel"],
                  fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(10, 2))
            combo = ttk.Combobox(top, textvariable=self.pipewire_preset_value,
                                 values=self._pipewire_preset_strings(),
                                 state="disabled" if disabled else "readonly",
                                 width=28,
                                 font=("DejaVu Sans", 9),
                                 style="TCombobox")
            combo.pack(side=LEFT)
            combo.bind("<<ComboboxSelected>>",
                       lambda e: self._pipewire_preset_on_select())

        # Текущее значение — подпись справа
        cur_label = None
        if key == "sysctl_cache":
            cur_label = self.t("cur_value") % self._read_sysctl_int(
                "/proc/sys/vm/vfs_cache_pressure", "?")
        elif key == "nmi_watchdog":
            cur_label = (self.t("nmi_now_active")
                         if getattr(self.state, "nmi_watchdog_active", False)
                         else self.t("nmi_now_off"))
        elif key == "swap":
            cur_label = self.t("cur_value") % self._swap_current()
        elif key == "sysctl_numa":
            cur_label = self.t("cur_value") % self._numa_current()
        elif key == "bbr":
            cur_label = self.t("cur_value") % self._bbr_current()
        elif key == "journald":
            cur_label = self.t("cur_value") % self._journald_current()
        elif key == "zswap":
            cur_label = self.t("cur_value") % self._zswap_current()
        elif key == "zram":
            cur_label = self.t("cur_value") % self._zram_current()
        elif key == "ntfs3":
            cur_label = self.t("cur_value") % self._ntfs3_current()
        elif key == "ntsync":
            cur_label = self.t("cur_value") % self._ntsync_current()
        if cur_label:
            Label(top, text=cur_label, bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 8)).pack(side=LEFT, padx=(8, 0))

        # Бейдж «применено / не применено»
        badge = Label(top, text="…", bg=c["panel"], fg=c["gray"],
                      font=("DejaVu Sans", 9, "bold"))
        badge.pack(side=LEFT, padx=(12, 0))
        self.badges[key] = badge

        # Для corectrl — кнопка «проверить» (спросит sudo и прочитает файл)
        if key == "corectrl":
            rb = Button(top, text=self.t("btn_check_status"),
                        command=self._check_corectrl_status,
                        bg=c["button"], fg=c["orange"],
                        activebackground=c["button_hover"],
                        activeforeground=c["orange"],
                        relief=FLAT, padx=6, pady=0,
                        font=("DejaVu Sans", 8))
            rb._keep_fg = c["orange"]
            rb.pack(side=LEFT, padx=(4, 0))

        # Кнопки «файл» и «?»
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

        # Описание
        dl = Label(row, text=desc, bg=c["panel"], fg=c["gray"],
                   anchor=W, justify=LEFT, wraplength=820,
                   font=("DejaVu Sans", 9))
        dl.pack(fill=X, padx=(24, 0))

        # Специальная кнопка удаления ZFS
        if key == "zfs_services":
            zfs_removable = (self.state.zfs_installed
                             and not self.state.zfs_used)
            btn_text = (self.t("btn_remove_zfs") if zfs_removable
                        else self.t("btn_remove_zfs_unavailable"))
            self._zfs_button = Button(
                row, text=btn_text,
                command=self._zfs_remove_packages,
                bg=c["button"],
                fg=c["red"] if zfs_removable else c["gray"],
                activebackground=c["button_hover"],
                activeforeground=c["red"] if zfs_removable else c["gray"],
                state=NORMAL if zfs_removable else DISABLED,
                relief=FLAT, padx=10, pady=4,
                font=("DejaVu Sans", 9))
            self._zfs_button.pack(anchor=W, padx=(24, 0), pady=(4, 0))

    def _pipewire_preset_strings(self):
        """Возвращает список строк для dropdown PipeWire."""
        result = []
        for key in ("default", "gaming", "recording"):
            p = PIPEWIRE_PRESETS[key]
            label = p["label_%s" % self.lang]
            desc = p["desc_%s" % self.lang]
            result.append("%s — %s" % (label, desc))
        return result

    def _pipewire_preset_on_select(self):
        """После выбора в dropdown — обрезаем строку до названия и
        сохраняем ключ."""
        cur = self.pipewire_preset_value.get()
        for key in ("default", "gaming", "recording"):
            p = PIPEWIRE_PRESETS[key]
            label = p["label_%s" % self.lang]
            if cur.startswith(label + " —"):
                self.pipewire_preset_value.set(key)
                return

    def _build_disk_extras(self):
        c = self.colors()
        mono = ("DejaVu Sans Mono", 9)
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
                chk = Checkbutton(row, text="",
                                  variable=self.mount_state[key],
                                  bg=c["panel"], fg=c["fg"],
                                  activebackground=c["panel"],
                                  activeforeground=c["fg"],
                                  selectcolor=c["panel"], anchor=W)
                chk.pack(side=LEFT)
                dev_short = os.path.basename(m["dev"])
                mp_str = ", ".join(m["mps"])
                if len(mp_str) > 22:
                    mp_str = mp_str[:19] + "…"
                info = self._disk_info(m["mps"][0])
                size_str = human_size(info[0] * 1024 ** 3) if info else "?"
                label_text = "%-10s %-22s %-6s %-8s" % (
                    dev_short, mp_str, m.get("fstype", ""), size_str)
                Label(row, text=label_text, bg=c["panel"], fg=c["fg"],
                      anchor=W, font=mono).pack(side=LEFT, padx=(4, 0))
                badge = Label(row, text="…", bg=c["panel"], fg=c["gray"],
                              font=("DejaVu Sans", 9, "bold"), anchor=W)
                badge.pack(side=LEFT, padx=(12, 0))
                self.mount_badges[key] = badge
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
            top2 = Frame(self._tune_inner, bg=c["panel"])
            top2.pack(anchor=W, padx=8, pady=(4, 4))
            Label(top2, text=self.t("commit_value_label"),
                  bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(4, 6))
            Entry(top2, textvariable=self.commit_value, width=8,
                  bg=c["entry"], fg=c["fg"], relief=FLAT,
                  insertbackground=c["fg"]).pack(side=LEFT)
            Label(top2, text=self.t("commit_default_hint"),
                  bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 8)).pack(side=LEFT, padx=(8, 0))
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
                    chk = Checkbutton(row, text="",
                                      variable=self.commit_state[mp],
                                      bg=c["panel"], fg=c["fg"],
                                      activebackground=c["panel"],
                                      activeforeground=c["fg"],
                                      selectcolor=c["panel"], anchor=W)
                    chk.pack(side=LEFT)
                    dev_short = os.path.basename(m["dev"])
                    mp_str = mp
                    if len(mp_str) > 22:
                        mp_str = mp_str[:19] + "…"
                    cur_val = self._commit_value_for_ui(mp) or \
                        self.t("commit_not_set")
                    info = self._disk_info(mp)
                    size_str = human_size(info[0] * 1024 ** 3) if info else "?"
                    label_text = "%-10s %-22s %-6s %-8s %-12s" % (
                        dev_short, mp_str, m.get("fstype", ""),
                        size_str, cur_val)
                    Label(row, text=label_text, bg=c["panel"], fg=c["fg"],
                          anchor=W, font=mono).pack(side=LEFT, padx=(4, 0))
                    badge = Label(row, text="…", bg=c["panel"], fg=c["gray"],
                                  font=("DejaVu Sans", 9, "bold"), anchor=W)
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
                chk = Checkbutton(row, text="",
                                  variable=self.steam_state[lib],
                                  bg=c["panel"], fg=c["fg"],
                                  activebackground=c["panel"],
                                  activeforeground=c["fg"],
                                  selectcolor=c["panel"], anchor=W)
                chk.pack(side=LEFT)
                Label(row, text=lib, bg=c["panel"], fg=c["fg"],
                      anchor=W, font=mono).pack(side=LEFT, padx=(4, 0))
                badge = Label(row, text="…", bg=c["panel"], fg=c["gray"],
                              font=("DejaVu Sans", 9, "bold"), anchor=W)
                badge.pack(side=LEFT, padx=(12, 0))
                self.steam_badges[lib] = badge

    # ─── Вкладка «Приложения» ───────────────────────────────────────────

    def _apps_load_installed(self):
        try:
            from .data import REMOVABLE_PACKAGES  # локальный импорт
        except ImportError:
            self._installed_packages = set()
            self.msg_queue.put(("apps_redraw", None))
            return
        self._installed_packages = installed_packages_set()
        self.msg_queue.put(("apps_redraw", None))

    def _apps_refresh(self):
        self._installed_packages = None
        self._run_bg("apps_load", self._apps_load_installed)

    def _apps_render(self):
        if self._apps_inner is None:
            return
        c = self.colors()
        for child in self._apps_inner.winfo_children():
            child.destroy()
        try:
            from .data import REMOVABLE_PACKAGES
        except ImportError:
            REMOVABLE_PACKAGES = {}
        if not is_debian_based():
            Label(self._apps_inner, text=self.t("apps_unsupported"),
                  bg=c["panel"], fg=c["gray"], anchor=W, justify=LEFT,
                  font=("DejaVu Sans", 10)).pack(fill=X, padx=24, pady=20)
            self._apps_update_status()
            return
        if not REMOVABLE_PACKAGES:
            Label(self._apps_inner, text=self.t("apps_no_list"),
                  bg=c["panel"], fg=c["gray"], anchor=W, justify=LEFT,
                  font=("DejaVu Sans", 10)).pack(fill=X, padx=24, pady=20)
            self._apps_update_status()
            return
        if self._installed_packages is None:
            Label(self._apps_inner, text="…",
                  bg=c["panel"], fg=c["gray"], anchor=W,
                  font=("DejaVu Sans", 10)).pack(fill=X, padx=24, pady=20)
            return
        query = self._apps_filter.get().strip().lower()
        cats = {}
        for pkg, meta in REMOVABLE_PACKAGES.items():
            if pkg not in self._installed_packages:
                continue
            lang_meta = meta.get(self.lang) or meta.get("en")
            if not lang_meta:
                continue
            label, desc, cat, careful = lang_meta
            if query and query not in pkg.lower() \
                    and query not in label.lower() \
                    and query not in desc.lower():
                continue
            cats.setdefault(cat, []).append((pkg, label, desc, careful))
        if not cats:
            Label(self._apps_inner, text=self.t("apps_empty"),
                  bg=c["panel"], fg=c["gray"], anchor=W,
                  font=("DejaVu Sans", 10)).pack(fill=X, padx=24, pady=20)
            self._apps_update_status()
            return
        order = None
        try:
            from .data import APPS_CATEGORY_ORDER
            order = APPS_CATEGORY_ORDER[self.lang]
        except ImportError:
            order = sorted(cats.keys())
        seq = [x for x in order if x in cats] + \
              [x for x in sorted(cats) if x not in order]
        for cat in seq:
            Label(self._apps_inner, text="─── %s ───" % cat,
                  bg=c["panel"], fg=c["yellow"], anchor=W,
                  font=("DejaVu Sans", 10, "bold")).pack(
                fill=X, padx=8, pady=(10, 4))
            for pkg, label, desc, careful in sorted(
                    cats[cat], key=lambda x: x[1].lower()):
                row = Frame(self._apps_inner, bg=c["panel"])
                row.pack(fill=X, padx=24, pady=1)
                var = BooleanVar(value=pkg in self.apps_checked)
                chk = Checkbutton(
                    row, text="", variable=var,
                    bg=c["panel"], fg=c["fg"],
                    activebackground=c["panel"],
                    activeforeground=c["fg"],
                    selectcolor=c["panel"], anchor=W,
                    command=lambda p=pkg, v=var: self._apps_toggle(p, v))
                chk.pack(side=LEFT)
                text = "%-28s %s" % (pkg, desc)
                if careful:
                    text += "  " + self.t("apps_careful_mark")
                Label(row, text=text, bg=c["panel"], fg=c["fg"],
                      anchor=W, font=("DejaVu Sans Mono", 9)).pack(
                    side=LEFT, padx=(4, 0))
        self._bind_wheel_tree(self._apps_inner)
        self._apps_update_status()

    def _apps_toggle(self, pkg, var):
        if var.get():
            self.apps_checked.add(pkg)
        else:
            self.apps_checked.discard(pkg)
        self._apps_update_status()

    def _apps_clear(self):
        self.apps_checked.clear()
        self._apps_render()

    def _apps_update_status(self):
        if self._apps_status is None:
            return
        if not self.apps_checked:
            self._apps_status.config(text=self.t("apps_selected_none"))
            return
        count = len(self.apps_checked)
        size = estimate_packages_size(list(self.apps_checked))
        self._apps_status.config(
            text=self.t("apps_selected") % (count, size))

    def _apps_remove_selected(self):
        if self.is_running:
            messagebox.showinfo(APP_NAME, self.t("msg_run"),
                                parent=self.root)
            return
        pkgs = sorted(self.apps_checked)
        if not pkgs:
            messagebox.showinfo(APP_NAME, self.t("msg_noopt"),
                                parent=self.root)
            return
        if not self._dry_var.get() and not self.sudo.ensure():
            self.log("sudo failed", "error")
            return
        self._run_bg("apps_dry", self._apps_dry_run_work, pkgs)

    def _apps_dry_run_work(self, pkgs):
        explicit, deps, system_hits, ok = apt_dry_run_purge(pkgs)
        if not ok:
            self.log("apt simulation failed — cannot confirm removal list",
                     "error")
        size = estimate_packages_size(explicit + deps)
        lines = [self.t("apps_confirm_will_remove"),
                 "  " + ", ".join(explicit)]
        if deps:
            lines += ["", self.t("apps_confirm_deps"),
                      "  " + ", ".join(deps)]
        lines += ["", "%s %s" % (self.t("apps_confirm_size"), size)]
        if system_hits:
            lines += ["",
                      self.t("apps_confirm_system_warn"),
                      "  " + ", ".join(system_hits),
                      self.t("apps_confirm_system_hint")]
        lines += ["", self.t("apps_confirm_no_rollback")]
        body = "\n".join(lines)
        self.msg_queue.put(("apps_confirm", (body, pkgs)))

    def _apps_show_confirm(self, body, pkgs):
        answer = messagebox.askyesno(self.t("apps_confirm_title"), body,
                                     parent=self.root,
                                     default=messagebox.NO)
        if not answer:
            return
        self.is_running = True
        self._set_running(True)
        self.msg_queue.put(("progress", 0))
        self.msg_queue.put(("statusbar", self.t("running")))
        self._run_bg("apps_remove", self._apps_remove_work, pkgs)

    def _apps_remove_work(self, pkgs):
        ops = SystemOps(self.sudo, self.state, self.log, self._dry_var.get())
        try:
            ok, freed = ops.apps_purge(pkgs)
            if ok:
                if self._dry_var.get():
                    self.log(self.t("apps_done_dry") % len(pkgs), "success")
                else:
                    self.log(self.t("apps_done") % (len(pkgs), freed),
                             "success")
                    self.apps_checked.clear()
            else:
                self.log(self.t("apps_failed"), "error")
        except Exception as e:
            self.log("Critical error: %s" % e, "error")
        finally:
            self.is_running = False
            self._set_running(False)
            if not self._dry_var.get():
                self._installed_packages = installed_packages_set()
            self.msg_queue.put(("apps_redraw", None))

    # ─── Прокрутка колесом ──────────────────────────────────────────────

    def _bind_global_wheel(self):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.root.bind_all(seq, self._on_wheel, add="+")

    def _bind_wheel_tree(self, widget):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(seq, self._on_wheel, add="+")
        for child in widget.winfo_children():
            self._bind_wheel_tree(child)

    def _on_wheel(self, event):
        try:
            widget = self.root.winfo_containing(event.x_root, event.y_root)
        except Exception:
            widget = None
        target_canvas = None
        p = widget
        while p is not None:
            if p is self._apps_canvas:
                target_canvas = self._apps_canvas
                break
            if p is self._tune_canvas or p is self._tune_inner:
                target_canvas = self._tune_canvas
                break
            try:
                p = p.master
            except Exception:
                p = None
        if target_canvas is None:
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
            target_canvas.yview_scroll(d, "units")

    # ─── Копирование ────────────────────────────────────────────────────

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
        try:
            text = w.get("1.0", "end-1c")
        except Exception:
            try:
                text = w.get()
            except Exception:
                return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _select_all(self, w):
        try:
            w.tag_add("sel", "1.0", "end-1c")
        except Exception:
            try:
                w.selection_range(0, "end")
            except Exception:
                pass

    # ─── Темы ───────────────────────────────────────────────────────────

    def _apply_theme(self):
        c = self.colors()
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        try:
            style.configure("TNotebook", background=c["bg"], borderwidth=0)
            style.configure("TNotebook.Tab", background=c["tab"],
                            foreground=c["fg"], padding=[14, 6])
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
                            background=c["tab"], foreground=c["fg"])
            style.map("Treeview.Heading",
                      background=[("active", c["tab_hover"])],
                      foreground=[("active", c["fg"])])
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
        try:
            self.root.option_add("*TCombobox*Listbox.background", c["panel"])
            self.root.option_add("*TCombobox*Listbox.foreground", c["fg"])
            self.root.option_add("*TCombobox*Listbox.selectBackground",
                                 c["sel"])
            self.root.option_add("*TCombobox*Listbox.selectForeground", c["fg"])
        except Exception:
            pass

    def _repaint_all(self):
        c = self.colors()

        def repaint_panel(w):
            try:
                cls = w.winfo_class()
                inside_tune = self._inside(w, self._tune_inner)
                inside_apps = self._inside(w, self._apps_inner)
                inside_any_panel = inside_tune or inside_apps
                if cls == "Frame" and w is not self.root:
                    w.configure(bg=c["panel"] if inside_any_panel else c["bg"])
                elif cls == "Label":
                    w.configure(bg=c["panel"] if inside_any_panel else c["bg"])
                elif cls == "Checkbutton":
                    w.configure(
                        bg=c["panel"] if inside_any_panel else c["bg"],
                        fg=c["fg"],
                        activebackground=(c["panel"] if inside_any_panel
                                          else c["bg"]),
                        activeforeground=c["fg"],
                        selectcolor=(c["panel"] if inside_any_panel
                                     else c["bg"]))
                elif cls == "Button":
                    if w is getattr(self, "_apply_btn", None):
                        w.configure(bg=c["accent"], fg=c["accent_fg"],
                                    activebackground=c["accent2"],
                                    activeforeground=c["accent_fg"])
                    elif w is getattr(self, "_zfs_button", None):
                        zfs_removable = (self.state.zfs_installed
                                         and not self.state.zfs_used)
                        w.configure(
                            bg=c["button"],
                            fg=c["red"] if zfs_removable else c["gray"],
                            activebackground=c["button_hover"],
                            activeforeground=(c["red"] if zfs_removable
                                              else c["gray"]))
                    else:
                        keep = getattr(w, "_keep_fg", None)
                        w.configure(
                            bg=c["button"],
                            fg=keep if keep else c["fg"],
                            activebackground=c["button_hover"],
                            activeforeground=keep if keep else c["fg"])
                elif cls == "Entry":
                    w.configure(bg=c["entry"], fg=c["fg"],
                                insertbackground=c["fg"],
                                disabledbackground=c["button_dis"],
                                disabledforeground=c["fg_dis"])
                elif cls == "Text":
                    w.configure(bg=c["terminal"], fg=c["terminal_fg"],
                                insertbackground=c["fg"])
                elif cls == "Canvas":
                    w.configure(bg=c["panel"] if inside_any_panel else c["bg"])
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
                                            font=("DejaVu Sans Mono", 9,
                                                  "bold"))
            self._status_view.tag_configure("info",
                                            foreground=c["terminal_fg"])
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
        if self.is_running:
            return
        self.theme = "dark" if self.theme == "light" else "light"
        if self._theme_btn is not None:
            self._theme_btn.configure(
                text=self.t("theme_dark") if self.theme == "light"
                else self.t("theme_light"))
        self._repaint_all()

    def _toggle_lang(self):
        if self.is_running:
            return
        current = self.schedule_value.get()
        ru_vals = ("Отключено", "Ежедневно", "Еженедельно (суббота)",
                   "2 раза в месяц (1 и 15)", "Ежемесячно (1 число)")
        en_vals = ("Disabled", "Daily", "Weekly (Saturday)",
                   "Twice a month (1 & 15)", "Monthly (1st)")
        self.lang = "en" if self.lang == "ru" else "ru"
        if self.lang == "ru":
            self.schedule_value.set(
                dict(zip(en_vals, ru_vals)).get(current, current))
        else:
            self.schedule_value.set(
                dict(zip(ru_vals, en_vals)).get(current, current))
        self._rebuild_ui()

    def _rebuild_ui(self):
        saved_opts = {k: v.get() for k, v in self.opts_state.items()}
        saved_mounts = {k: v.get() for k, v in self.mount_state.items()}
        saved_steam = {k: v.get() for k, v in self.steam_state.items()}
        saved_commit = {k: v.get() for k, v in self.commit_state.items()}
        try:
            for child in self.root.winfo_children():
                child.destroy()
        except Exception:
            pass
        self.badges = {}
        self.mount_badges = {}
        self.steam_badges = {}
        self.commit_badges = {}
        self.option_widgets = {}
        self._sched_lbl = None
        self._thp_lbl = None
        self._apply_btn = None
        self._rollback_btn = None
        self._selall_btn = None
        self._selnone_btn = None
        self._theme_btn = None
        self._lang_btn = None
        self._about_btn = None
        self._zfs_button = None
        self._result_lbl = None
        self._apps_status = None
        self._apps_canvas = None
        self._apps_inner = None
        self._tune_canvas = None
        self._tune_inner = None
        self._services_tree = None
        self._status_view = None
        self._terminal = None
        self._progress = None
        self._status_lbl = None
        self.opts_state = {k: BooleanVar(value=saved_opts.get(k, False))
                           for k in OPTIONS_META}
        for k in list(self.mount_state.keys()):
            self.mount_state[k] = BooleanVar(value=saved_mounts.get(k, False))
        for k in list(self.steam_state.keys()):
            self.steam_state[k] = BooleanVar(value=saved_steam.get(k, False))
        for k in list(self.commit_state.keys()):
            self.commit_state[k] = BooleanVar(value=saved_commit.get(k, False))
        try:
            self.state.zfs_installed = zfs_packages_installed()
            self.state.zfs_used = zfs_in_use()
            self.state.pipewire_active = pipewire_active()
            self.state.nmi_watchdog_active = nmi_watchdog_active()
            self.state.nmi_watchdog_in_grub = nmi_watchdog_in_grub()
            with open("/proc/sys/vm/max_map_count", "r") as f:
                self.state.current_max_map_count = f.read().strip()
        except Exception:
            pass
        try:
            self._compute_disabled_reasons()
            self._build_ui()
            self._apply_theme()
            self._update_badges()
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror(
                APP_NAME,
                "UI rebuild failed:\n%s\n\nSee terminal for traceback." % e,
                parent=self.root)
            return
        self._run_bg("services", self._services_work)
        self._run_bg("applied", self._applied_work)
        self._run_bg("status", self._status_work)
        self._run_bg("apps_load", self._apps_load_installed)

    # ─── Детект применённых настроек ────────────────────────────────────

    def _applied_work(self):
        ops = SystemOps(self.sudo, self.state,
                        lambda m, t="normal": None, True)
        ops.mount_items = self.mount_items
        ops.commit_targets = [mp for mp in self.commit_state]
        try:
            self.msg_queue.put(("applied", self._detect_applied(ops)))
            self.msg_queue.put(("mount_applied", self._detect_mount()))
            self.msg_queue.put(("steam_applied", self._detect_steam()))
            self.msg_queue.put(("schedule", self._schedule_text()))
            self.msg_queue.put(("commit_applied",
                                self._detect_commit_per_mp(ops)))
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
        lang = self.lang
        names = {
            "*-*-* 18:30:00": ("Ежедневно", "Daily"),
            "Sat 18:30:00": ("Еженедельно (суббота)", "Weekly (Saturday)"),
            "*-*-1,15 18:30:00": ("2 раза в месяц (1 и 15)",
                                  "Twice a month (1 & 15)"),
            "*-*-1 18:30:00": ("Ежемесячно (1 число)", "Monthly (1st)"),
        }
        pair = names.get(cal)
        if pair:
            label = pair[0 if lang == "ru" else 1]
            m2 = re.search(r"(\d{2}:\d{2}(?::\d{2})?)", cal)
            if m2:
                t = m2.group(1)
                if len(t) == 8:
                    t = t[:5]
                label = "%s, %s" % (label, t)
            return label
        return cal
    def _check_corectrl_status(self):
        """Кнопка «проверить» для CoreCtrl: запрашивает sudo,
        читает файл правила, обновляет бейдж."""
        if self.is_running:
            return
        # Запрашиваем sudo (если ещё не аутентифицирован)
        if not self.sudo.ensure():
            self.log("sudo failed", "error")
            return
        # Перечитываем состояние и обновляем бейдж
        try:
            ops = SystemOps(self.sudo, self.state,
                            lambda m, t="normal": None, True)
            found = self._corectrl_found(ops)
            self.applied["corectrl"] = found
            self._update_badges()
            if found:
                self.log("CoreCtrl rule found", "success")
            else:
                self.log("CoreCtrl rule NOT found", "warning")
        except Exception as e:
            self.log("Check corectrl failed: %s" % e, "error")

    def _corectrl_found(self, ops):
        """Ищет правило Polkit для CoreCtrl.

        Каталог /etc/polkit-1/rules.d/ обычно имеет права 750 (root:polkitd),
        поэтому обычный пользователь его не читает. Используем три уровня:
        1) прямое чтение (работает, если права позволяют),
        2) sudo -n cat (работает после первой sudo-аутентификации),
        3) sudo -n ls + cat (полный перебор с sudo).
        """
        direct_paths = (
            "/etc/polkit-1/rules.d/90-corectrl.rules",
            "/usr/share/polkit-1/rules.d/90-corectrl.rules",
            "/etc/polkit-1/localauthority/50-local.d/90-corectrl.pkla",
        )
        # 1. Прямое чтение (если права позволяют)
        for p in direct_paths:
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    if "org.corectrl" in f.read():
                        return True
            except Exception:
                continue
        # 2. Через sudo -n cat (если sudo-сессия активна)
        for p in direct_paths:
            try:
                r = subprocess.run(["sudo", "-n", "cat", p],
                                   capture_output=True, text=True,
                                   timeout=3)
                if r.returncode == 0 and "org.corectrl" in r.stdout:
                    return True
            except Exception:
                continue
        # 3. Перебор каталогов через sudo -n ls + cat
        for d in ("/etc/polkit-1/rules.d",
                  "/usr/share/polkit-1/rules.d",
                  "/etc/polkit-1/localauthority/50-local.d"):
            try:
                r = subprocess.run(["sudo", "-n", "ls", d],
                                   capture_output=True, text=True,
                                   timeout=3)
                if r.returncode != 0:
                    continue
                for fn in r.stdout.splitlines():
                    fn = fn.strip()
                    if not fn or fn.startswith("total"):
                        continue
                    if "corectrl" in fn.lower():
                        return True
                    full = os.path.join(d, fn)
                    r2 = subprocess.run(["sudo", "-n", "cat", full],
                                        capture_output=True, text=True,
                                        timeout=3)
                    if r2.returncode == 0 and "org.corectrl" in r2.stdout:
                        return True
            except Exception:
                continue
        return False

    def _max_map_count_applied(self, mmc_content):
        m = re.search(r"^vm\.max_map_count=(\d+)\s*$", mmc_content, re.M)
        if m and m.group(1) == self.max_map_count_value.get():
            return True
        try:
            with open("/proc/sys/vm/max_map_count", "r") as f:
                current = f.read().strip()
            return current == self.max_map_count_value.get()
        except Exception:
            return False

    def _grub_has_token(self, grub, token):
        for line in grub.splitlines():
            s = line.strip()
            if s.startswith("#"):
                continue
            m = re.match(r"^\s*GRUB_CMDLINE_LINUX(?:_DEFAULT)?=(.*)$", line)
            if not m:
                continue
            raw = m.group(1).strip().strip('"').strip("'")
            if token in raw.split():
                return True
        return False

    def _detect_applied(self, ops):
        grub = ops.read_file("/etc/default/grub") or ""
        env = ops.read_file("/etc/environment") or ""
        j = ops.read_file("/etc/systemd/journald.conf") or ""
        swp = ops.read_file("/etc/sysctl.d/99-gaming-swap.conf") or ""
        sysc = ops.read_file("/etc/sysctl.d/99-gaming-sysctl.conf") or ""
        bashrc = ops.read_file(os.path.join(self.state.user_home,
                                            ".bashrc")) or ""
        mint = ops.read_file(
            "/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf") or ""
        itco = ops.read_file("/etc/modprobe.d/nmi-watchdog.conf") or ""
        mmc = ops.read_file("/etc/sysctl.d/99-gaming-mmap.conf") or ""

        def sv(p):
            try:
                r = subprocess.run(["sysctl", "-n", p], capture_output=True,
                                   text=True, timeout=3,
                                   env=self._host_env())
                return r.stdout.strip() if r.returncode == 0 else ""
            except Exception:
                return ""

        m_sw = re.search(r"^\s*vm\.swappiness\s*=\s*(\d+)\s*$", swp, re.M)
        cur_sw = sv("vm.swappiness")
        want_sw = self.swap_value.get().strip()
        sw_ok = False
        if m_sw and m_sw.group(1) == want_sw:
            sw_ok = True
        elif cur_sw == want_sw:
            sw_ok = True
        pw = os.path.join(self.state.user_home, ".config", "pipewire",
                          "pipewire.conf.d", "10-sound.conf")
        j_ok = (re.search(r"^\s*Storage\s*=\s*volatile\s*$", j, re.M)
                and re.search(r"^\s*RuntimeMaxUse\s*=\s*50M\s*$", j, re.M))
        thp_want = self.thp_value.get()
        thp_ok = (self._thp_current() == thp_want) or \
                 self._grub_has_token(grub,
                                      "transparent_hugepage=%s" % thp_want)
        pipewire_preset = self._pipewire_preset_current()
        return {
            "journald": bool(j_ok),
            "audit": self._grub_has_token(grub, "audit=0"),
            "raid": self._grub_has_token(grub, "raid=noautodetect"),
            "nmi_watchdog": self._grub_has_token(grub, "nmi_watchdog=0"),
            "itco_wdt": "blacklist iTCO_wdt" in itco,
            "zfs_services": (zfs_units_masked()
                             if self.state.zfs_installed else False),
            "shutdown_timeout": self._shutdown_timeout_applied(),
            "corectrl": self._corectrl_found(ops),
            "ppfeaturemask": self._grub_has_token(
                grub, "amdgpu.ppfeaturemask=0xffffffff")
                or "amdgpu.ppfeaturemask" in grub,
            "nvidia_modeset": self._grub_has_token(grub,
                                                   "nvidia-drm.modeset=1"),
            "vrr": ops.path_exists("/etc/X11/xorg.conf.d/20-amdgpu.conf"),
            "radv": "RADV_PERFTEST=sam" in env,
            "mesa": "MESA_SHADER_CACHE_MAX_SIZE=4G" in env,
            "pipewire": bool(pipewire_preset),
            "bbr": sv("net.ipv4.tcp_congestion_control") == "bbr",
            "swap": sw_ok,
            "zram": (ops.path_exists("/etc/systemd/zram-generator.conf")
                     and zram_generator_present()),
            "zswap": (self._grub_has_token(grub, "zswap.enabled=1")
                      and self.state.has_swap),
            "thp": thp_ok,
            "sysctl_cache": bool(
                re.search(r"^vm\.vfs_cache_pressure=50$", sysc, re.M))
                or sv("vm.vfs_cache_pressure") == "50",
            "sysctl_numa": bool(
                re.search(r"^kernel\.numa_balancing=0$", sysc, re.M))
                or sv("kernel.numa_balancing") == "0",
            "reisub": (sv("kernel.sysrq") == "244"
                       or ops.path_exists("/etc/sysctl.d/99-sysrq.conf")),
            "ntsync": (self.state.ntsync
                       or ops.path_exists("/etc/modules-load.d/ntsync.conf")),
            "max_map_count": self._max_map_count_applied(mmc),
            "ntfs3": bool(re.search(r"^\s*#\s*blacklist\s+ntfs3\s*$",
                                    mint, re.M)),
            "commit": ops._commit_applied(),
            "tmpfs_tmp": tmpfs_tmp_mounted() or fstab_has_tmp_tmpfs(),
            "aliases": "system-tuneup" in bashrc,
            "autoupdate": ops.service_enabled(
                "biweekly-upgrade.timer") == "enabled",
        }

    def _detect_mount(self):
        try:
            with open("/etc/fstab", "r", encoding="utf-8",
                      errors="replace") as f:
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

    # ─── Список служб ───────────────────────────────────────────────────

    def _services_work(self):
        ops = SystemOps(self.sudo, self.state,
                        lambda m, t="normal": None, self._dry_var.get())
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

    def _sort_services(self, col):
        if self._svc_sort_col == col:
            self._svc_sort_reverse = not self._svc_sort_reverse
        else:
            self._svc_sort_col = col
            self._svc_sort_reverse = False
        self._render_services_rows()

    def _sort_key_for(self, row, col):
        name, st, run, desc, q, tag = row
        if col == "name":
            return name.lower()
        if col == "state":
            order = {"err": 0, "muted": 1, "ok": 2, "warn": 3}
            return order.get(tag, 9)
        if col == "run":
            return 0 if run in ("running", "работает") else 1
        if col == "desc":
            return desc.lower()
        return name.lower()

    def _render_services_rows(self):
        if self._services_tree is None:
            return
        for it in self._services_tree.get_children():
            self._services_tree.delete(it)
        rows = list(self.svc_rows)
        if self._svc_sort_col:
            rows.sort(key=lambda r: self._sort_key_for(r, self._svc_sort_col),
                      reverse=self._svc_sort_reverse)
        self._update_sort_indicators()
        for n, st, run, desc, q, tag in rows:
            mark = "[✓]" if n in self.svc_checked else "[ ]"
            self._services_tree.insert("", END,
                                       values=(mark, n, st, run, desc, q),
                                       tags=(tag,))

    def _update_sort_indicators(self):
        if self._services_tree is None:
            return
        base = {
            "name": self.t("svc_name"),
            "state": self.t("svc_state"),
            "run": self.t("svc_run"),
            "desc": self.t("svc_desc"),
        }
        for col, text in base.items():
            if col == self._svc_sort_col:
                arrow = (self.t("sort_desc") if self._svc_sort_reverse
                         else self.t("sort_asc"))
                self._services_tree.heading(col, text="%s %s" % (text, arrow))
            else:
                self._services_tree.heading(col, text=text)

    def _on_service_select(self, _e=None):
        if self._services_tree is None or self._svc_detail is None:
            return
        items = self._services_tree.selection()
        parts = []
        for it in items[:3]:
            vals = self._services_tree.item(it)["values"]
            if len(vals) >= 2:
                name = str(vals[1])
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
        row_id = self._services_tree.identify_row(event.y)
        if not row_id:
            return
        vals = self._services_tree.item(row_id)["values"]
        if len(vals) < 2:
            return
        name = str(vals[1])
        if col == "#1":
            if name in self.svc_checked:
                self.svc_checked.discard(name)
                mark = "[ ]"
            else:
                self.svc_checked.add(name)
                mark = "[✓]"
            new_vals = list(vals)
            new_vals[0] = mark
            self._services_tree.item(row_id, values=new_vals)
        elif col == "#6":
            self._services_tree.selection_remove(
                self._services_tree.selection())
            self._show_service_help(name)

    # ─── Бейджи применения ──────────────────────────────────────────────

    def _update_badges(self):
        c = self.colors()
        for k, lbl in self.badges.items():
            if lbl is None or not lbl.winfo_exists():
                continue
            if k == "pipewire":
                preset = self._pipewire_preset_current()
                if preset is None:
                    self._style_badge(lbl, False, c)
                elif preset == "manual":
                    self._style_badge(lbl, True, c,
                                      text_override=self.t("applied_manual"))
                else:
                    self._style_badge(lbl, True, c)
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
            ok = self.commit_applied_per_mp.get(k, False)
            self._style_badge(lbl, ok, c)
        if self._thp_lbl is not None and self._thp_lbl.winfo_exists():
            cur = self._thp_current() or "?"
            fmt = self.t("thp_cur")
            self._thp_lbl.config(text=fmt % cur if "%" in fmt else fmt,
                                 fg=c["gray"], bg=c["panel"])

    def _style_badge(self, lbl, ok, c, text_override=None):
        text = text_override if text_override else (
            self.t("applied_yes") if ok else self.t("applied_no"))
        lbl.config(text=text,
                   bg=c["panel"], fg=c["green"] if ok else c["gray"])

    # ─── ZFS: удаление пакетов ──────────────────────────────────────────

    def _zfs_remove_packages(self):
        if self.is_running:
            messagebox.showinfo(APP_NAME, self.t("msg_run"),
                                parent=self.root)
            return
        if self.state.zfs_used:
            messagebox.showwarning(
                APP_NAME,
                "ZFS is in use, removal blocked."
                if self.lang == "en"
                else "ZFS используется, удаление заблокировано.",
                parent=self.root)
            return
        if not self.state.zfs_installed:
            messagebox.showinfo(
                APP_NAME,
                "ZFS packages not installed."
                if self.lang == "en"
                else "Пакеты ZFS не установлены.",
                parent=self.root)
            return
        answer = messagebox.askyesno(
            self.t("zfs_remove_title"),
            self.t("zfs_remove_body"),
            parent=self.root, default=messagebox.NO)
        if not answer:
            return
        if not self._dry_var.get() and not self.sudo.ensure():
            self.log("sudo failed", "error")
            return
        self.is_running = True
        self._set_running(True)
        self.msg_queue.put(("progress", 0))
        self.msg_queue.put(("statusbar", self.t("running")))
        self._run_bg("zfs_remove", self._zfs_remove_work)

    def _zfs_remove_work(self):
        ops = SystemOps(self.sudo, self.state, self.log, self._dry_var.get())
        try:
            ok = ops.apply_zfs_remove_packages()
            if ok:
                self.log("ZFS packages removed. Rolling back requires "
                         "'sudo apt install zfsutils-linux'.", "info")
        except Exception as e:
            self.log("Critical error: %s" % e, "error")
        finally:
            self.state.zfs_installed = zfs_packages_installed()
            self.state.zfs_used = zfs_in_use()
            self.is_running = False
            self._set_running(False)
            self._run_bg("applied", self._applied_work)
            self._run_bg("status", self._status_work)
            self._run_bg("services", self._services_work)

    # ─── apply / rollback ───────────────────────────────────────────────

    def apply_selected(self):
        if self.is_running:
            messagebox.showinfo(APP_NAME, self.t("msg_run"),
                                parent=self.root)
            return
        selected = [k for k, v in self.opts_state.items()
                    if v.get() and k not in self.disabled_reasons]
        mount_sel = [mp for m in self.mount_items
                     if self.mount_state[m["mps"][0]].get()
                     for mp in m["mps"]]
        steam_sel = [l for l in self.steam_items if self.steam_state[l].get()]
        commit_sel = [mp for mp, v in self.commit_state.items() if v.get()]
        if not selected and not mount_sel and not steam_sel and not commit_sel:
            messagebox.showwarning(APP_NAME, self.t("msg_noopt"),
                                   parent=self.root)
            return
        params = {
            "corectrl_group": self.corectrl_group.get(),
            "swap_value": self.swap_value.get(),
            "update_schedule": self.schedule_value.get(),
            "commit_value": self.commit_value.get(),
            "thp_value": self.thp_value.get(),
            "max_map_count_value": self.max_map_count_value.get(),
            "tmpfs_size_value": self.tmpfs_size_value.get(),
            "shutdown_timeout_value": self.shutdown_timeout_value.get(),
            "pipewire_preset": self.pipewire_preset_value.get()
                or PIPEWIRE_PRESET_DEFAULT,
        }
        dry = self._dry_var.get()
        if ("autoupdate" in selected and not dry
                and params["update_schedule"] not in ("Отключено",
                                                      "Disabled")):
            messagebox.showinfo(APP_NAME, self.t("autoupdate_warn"),
                                parent=self.root)
        if ("shutdown_timeout" in selected and not dry):
            messagebox.showinfo(APP_NAME, self.t("shutdown_timeout_warn"),
                                parent=self.root)
        needs_sudo = bool(mount_sel or commit_sel or steam_sel
                          or any(k != "pipewire" for k in selected))
        if not dry and needs_sudo and not self.sudo.ensure():
            self.log("sudo failed", "error")
            return
        self._ram_cache = None
        self.is_running = True
        self._set_running(True)
        if self._result_lbl is not None:
            self._result_lbl.config(text="")
        self.msg_queue.put(("progress", 0))
        self.msg_queue.put(("statusbar", self.t("running")))
        self._run_bg("apply", self._apply_work, selected, mount_sel,
                     steam_sel, commit_sel, params, dry)

    def _apply_work(self, selected, mount_sel, steam_sel, commit_sel,
                    params, dry):
        ops = SystemOps(self.sudo, self.state, self.log, dry)
        ops.mount_items = self.mount_items
        ops.commit_targets = commit_sel
        total = len(selected) + (1 if mount_sel else 0) + \
            (1 if steam_sel else 0) + (1 if commit_sel else 0)
        if total == 0:
            self._finish_run(0, 0, 0)
            return
        done = 0
        ok_count = skip_count = fail_count = 0
        self.log("=" * 60, "highlight")
        self.log("APPLY START" if self.lang == "en" else "ЗАПУСК ТЮНИНГА",
                 "highlight")
        try:
            for k in selected:
                label = self.om(k)[0]
                self.log("→ %s" % label, "info")
                result = None
                try:
                    result = getattr(ops, "apply_%s" % k)(params)
                except Exception as e:
                    self.log("Error in %s: %s" % (k, e), "error")
                    result = False
                if result is False:
                    fail_count += 1
                elif result is None:
                    skip_count += 1
                else:
                    ok_count += 1
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if mount_sel:
                self.log("→ %s" % self.t("mount_title"), "info")
                r = ops.apply_mount_opts(mount_sel)
                if r is False:
                    fail_count += 1
                elif r is None:
                    skip_count += 1
                else:
                    ok_count += 1
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if commit_sel:
                self.log("→ %s" % self.t("commit_title"), "info")
                r = ops.apply_commit(params)
                if r is False:
                    fail_count += 1
                elif r is None:
                    skip_count += 1
                else:
                    ok_count += 1
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if steam_sel:
                self.log("→ %s" % self.t("steam_title"), "info")
                r = ops.apply_steam_links(steam_sel)
                if r is False:
                    fail_count += 1
                elif r is None:
                    skip_count += 1
                else:
                    ok_count += 1
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if not dry:
                ops.finalize_grub()
            self.msg_queue.put(("progress", 100))
            self.msg_queue.put(("statusbar", self.t("done")))
            self.log("Done", "success")
        except Exception as e:
            self.log("Critical error: %s" % e, "error")
            fail_count += 1
        finally:
            self._finish_run(ok_count, skip_count, fail_count)

    def rollback_selected(self):
        if self.is_running:
            messagebox.showinfo(APP_NAME, self.t("msg_run"),
                                parent=self.root)
            return
        selected = [k for k, v in self.opts_state.items()
                    if v.get() and k not in self.disabled_reasons]
        mount_sel = [mp for m in self.mount_items
                     if self.mount_state[m["mps"][0]].get()
                     for mp in m["mps"]]
        steam_sel = [l for l in self.steam_items if self.steam_state[l].get()]
        commit_sel = [mp for mp, v in self.commit_state.items() if v.get()]
        if not selected and not mount_sel and not steam_sel and not commit_sel:
            messagebox.showwarning(APP_NAME, self.t("msg_noopt"),
                                   parent=self.root)
            return
        dry = self._dry_var.get()
        needs_sudo = bool(mount_sel or commit_sel or steam_sel
                          or any(k != "pipewire" for k in selected))
        if not dry and needs_sudo and not self.sudo.ensure():
            self.log("sudo failed", "error")
            return
        self._ram_cache = None
        self.is_running = True
        self._set_running(True)
        if self._result_lbl is not None:
            self._result_lbl.config(text="")
        self.msg_queue.put(("progress", 0))
        self.msg_queue.put(("statusbar", self.t("running")))
        self._run_bg("rollback", self._rollback_work, selected, mount_sel,
                     steam_sel, commit_sel, dry)

    def _rollback_work(self, selected, mount_sel, steam_sel, commit_sel, dry):
        ops = SystemOps(self.sudo, self.state, self.log, dry)
        ops.mount_items = self.mount_items
        ops.commit_targets = commit_sel
        total = len(selected) + (1 if mount_sel else 0) + \
            (1 if steam_sel else 0) + (1 if commit_sel else 0)
        if total == 0:
            self._finish_run(0, 0, 0)
            return
        done = 0
        ok_count = skip_count = fail_count = 0
        self.log("=" * 60, "highlight")
        self.log("ROLLBACK START" if self.lang == "en" else "ЗАПУСК ОТКАТА",
                 "highlight")
        try:
            for k in selected:
                label = self.om(k)[0]
                self.log("→ %s" % label, "info")
                result = None
                try:
                    result = getattr(ops, "rollback_%s" % k)()
                except Exception as e:
                    self.log("Error in %s: %s" % (k, e), "error")
                    result = False
                if result is False:
                    fail_count += 1
                elif result is None:
                    skip_count += 1
                else:
                    ok_count += 1
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if mount_sel:
                r = ops.rollback_mount_opts(mount_sel)
                if r is False:
                    fail_count += 1
                elif r is None:
                    skip_count += 1
                else:
                    ok_count += 1
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if commit_sel:
                r = ops.rollback_commit({})
                if r is False:
                    fail_count += 1
                elif r is None:
                    skip_count += 1
                else:
                    ok_count += 1
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if steam_sel:
                r = ops.rollback_steam_links(steam_sel)
                if r is False:
                    fail_count += 1
                elif r is None:
                    skip_count += 1
                else:
                    ok_count += 1
                done += 1
                self.msg_queue.put(("progress", int(done / total * 90)))
            if not dry:
                ops.finalize_grub()
            self.msg_queue.put(("progress", 100))
            self.msg_queue.put(("statusbar", self.t("done")))
            self.log("Rollback done", "success")
        except Exception as e:
            self.log("Critical error: %s" % e, "error")
            fail_count += 1
        finally:
            self._finish_run(ok_count, skip_count, fail_count)

    def _finish_run(self, ok_count, skip_count, fail_count):
        self.is_running = False
        self._set_running(False)
        self.msg_queue.put(("result", ok_count, skip_count, fail_count))
        try:
            self.state.detect()
        except Exception:
            pass
        self._run_bg("applied", self._applied_work)
        self._run_bg("status", self._status_work)
        self._run_bg("services", self._services_work)

    def _set_running(self, running):
        for btn_attr in ("_apply_btn", "_rollback_btn",
                         "_selall_btn", "_selnone_btn"):
            btn = getattr(self, btn_attr, None)
            if btn is not None and btn.winfo_exists():
                btn.config(state=DISABLED if running else NORMAL)

    # ─── Выбор всех / ничего ────────────────────────────────────────────

    def select_all_options(self):
        for k, var in self.opts_state.items():
            if k in self.disabled_reasons:
                continue
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
        if self._services_tree is None:
            return
        for item in self._services_tree.get_children():
            vals = self._services_tree.item(item)["values"]
            if len(vals) >= 2:
                name = str(vals[1])
                self.svc_checked.add(name)
                new_vals = list(vals)
                new_vals[0] = "[✓]"
                self._services_tree.item(item, values=new_vals)

    def clear_services_selection(self):
        if self._services_tree is None:
            return
        self.svc_checked.clear()
        for item in self._services_tree.get_children():
            vals = self._services_tree.item(item)["values"]
            if len(vals) >= 2:
                new_vals = list(vals)
                new_vals[0] = "[ ]"
                self._services_tree.item(item, values=new_vals)
        self._services_tree.selection_remove(
            self._services_tree.selection())

    def _checked_service_names(self):
        if not self.svc_checked:
            return []
        if self._services_tree is None:
            return list(self.svc_checked)
        present = set()
        for item in self._services_tree.get_children():
            vals = self._services_tree.item(item)["values"]
            if len(vals) >= 2:
                present.add(str(vals[1]))
        return [n for n in self.svc_checked if n in present]

    def enable_selected(self):
        if self.is_running:
            messagebox.showinfo(APP_NAME, self.t("msg_run"),
                                parent=self.root)
            return
        names = self._checked_service_names()
        if not names:
            messagebox.showinfo(APP_NAME, self.t("msg_sel"),
                                parent=self.root)
            return
        if not self._dry_var.get() and not self.sudo.ensure():
            return
        self._run_bg("enable_svc", self._enable_work, names)

    def _enable_work(self, names):
        ops = SystemOps(self.sudo, self.state, self.log, self._dry_var.get())
        for name in names:
            if ops.dry_run:
                ops.log("[DRY RUN] enable %s" % name, "warning")
                continue
            ok = ops.sudo_run(["systemctl", "unmask", name],
                              ignore_error=True)
            ok2 = ops.sudo_run(["systemctl", "enable", "--now", name],
                               ignore_error=True)
            if ok or ok2:
                ops.log("✓ %s enabled" % name, "success")
            else:
                ops.log("Cannot enable %s" % name, "warning")
        self._run_bg("services", self._services_work)
        self._run_bg("status", self._status_work)

    def disable_selected(self):
        if self.is_running:
            messagebox.showinfo(APP_NAME, self.t("msg_run"),
                                parent=self.root)
            return
        names = self._checked_service_names()
        if not names:
            messagebox.showinfo(APP_NAME, self.t("msg_sel"),
                                parent=self.root)
            return
        if not self._dry_var.get() and not self.sudo.ensure():
            return
        self._run_bg("disable_svc", self._disable_work, names)

    def _disable_work(self, names):
        ops = SystemOps(self.sudo, self.state, self.log, self._dry_var.get())
        for name in names:
            if ops.dry_run:
                ops.log("[DRY RUN] disable %s" % name, "warning")
                continue
            ok = ops.sudo_run(["systemctl", "disable", "--now", name],
                              ignore_error=True)
            if (name.startswith("avahi") or name.startswith("bluetooth")
                    or name.startswith("apport")):
                ok = ops.sudo_run(["systemctl", "mask", name],
                                  ignore_error=True) or ok
            if ok:
                ops.log("✓ %s disabled" % name, "success")
            else:
                ops.log("Cannot disable %s" % name, "warning")
        self._run_bg("services", self._services_work)
        self._run_bg("status", self._status_work)

    # ─── Статус ─────────────────────────────────────────────────────────

    def _status_work(self):
        try:
            self._status_inner()
        except Exception:
            traceback.print_exc()

    def _status_hardware(self, A):
        rows = [(self.t("st_hw"), "head")]
        bits = 64 if os.sys.maxsize > 2 ** 32 else 32
        name = ""
        try:
            with open("/etc/os-release", "r", encoding="utf-8",
                      errors="replace") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        name = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass
        rows.append(("%s: %s (%d-bit)" % (self.t("os_lbl"),
                                          name or "Linux", bits), "info"))
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
        rows.append(("%s: %s" % (self.t("driver_lbl"), drv_s or "n/a"),
                     "info"))
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
            tn = {"file": self.t("swap_file"),
                  "partition": self.t("swap_part"), "zram": "zram"}
            sv_ = tn.get(self.state.swap_type, self.state.swap_type)
            sz = self._swap_size_gb()
            if sz:
                sv_ += ", %.1f %s" % (sz, self.t("gb"))
        else:
            sv_ = self.t("no_swap")
        rows.append(("%s: %s" % (self.t("swap_lbl"), sv_), "info"))
        rows.append(("%s: %s" % (self.t("kernel_lbl"), os.uname().release),
                     "info"))
        rows.append(("%s: %s" % (self.t("de_lbl"), desktop_name()), "info"))
        rows.append((self.t("user_lbl") + ": " + self.state.user_name, "info"))
        rows.append((self.t("home_lbl") + ": " + self.state.user_home, "info"))
        return rows

    def _status_partitions(self):
        rows = [("", "info"), (self.t("st_parts"), "head")]
        seen = {}
        for it in parse_mounts():
            if it["mp"] == "/boot/efi" or (it["fstype"] == "vfat"
                                           and it["mp"].startswith("/boot")):
                continue
            seen.setdefault(it["dev"], {"mps": [], "fstype": it["fstype"]})
            seen[it["dev"]]["mps"].append(it["mp"])
        header = "  %-12s %-32s %-7s %10s %10s" % (
            self.t("part_dev"), self.t("part_mount"), self.t("part_fs"),
            self.t("part_total"), self.t("part_free"))
        rows.append((header, "muted"))
        for dev, info in seen.items():
            d = self._disk_info(info["mps"][0])
            if not d:
                continue
            total, free = d
            mp_str = ", ".join(info["mps"])
            if len(mp_str) > 32:
                mp_str = mp_str[:29] + "…"
            dev_short = os.path.basename(dev)
            total_str = "%.1f %s" % (total, self.t("gb"))
            free_str = "%.1f %s" % (free, self.t("gb"))
            line = "  %-12s %-32s %-7s %10s %10s" % (
                dev_short, mp_str, info["fstype"], total_str, free_str)
            rows.append((line, "info"))
        return rows

    def _status_tweaks(self, A):
        rows = [("", "info"), (self.t("st_tweaks"), "head")]
        for k in OPTIONS_META:
            label, _d, _c, short = self.om(k)
            ok = A.get(k, False)
            mark = self.t("yes") if ok else self.t("no")
            extra = ""
            if k == "shutdown_timeout" and ok:
                cur = self._shutdown_timeout_current()
                if cur and cur != "?":
                    extra = " (%s)" % cur
            elif k == "pipewire" and ok:
                preset = self._pipewire_preset_current()
                if preset and preset != "manual":
                    p = PIPEWIRE_PRESETS.get(preset, {})
                    label_mode = p.get("label_%s" % self.lang, preset)
                    extra = " (%s)" % label_mode
                elif preset == "manual":
                    extra = " (%s)" % self.t("applied_manual").split("(")[-1].rstrip(")")
            rows.append(("%-42s %-14s %s" % (label, mark + extra, short),
                         "ok" if ok else "no"))
        for mp in self.commit_state:
            val = self._commit_value_for_ui(mp) or self.t("commit_not_set")
            ok = self._commit_is_effective(
                val if val != self.t("commit_not_set") else "")
            mark = self.t("yes") if ok else self.t("no")
            rows.append(("%-42s %-14s %s %s"
                         % (self.t("commit_title"), mark, mp, val),
                         "ok" if ok else "no"))
        for m in self.mount_items:
            ok = self.mount_applied.get(m["mps"][0], False)
            mark = self.t("yes") if ok else self.t("no")
            rows.append(("%-42s %-14s %s"
                         % (self.t("mount_short"), mark,
                            ", ".join(m["mps"])),
                         "ok" if ok else "no"))
        for lib in self.steam_items:
            ok = self.steam_applied.get(lib, False)
            mark = self.t("yes") if ok else self.t("no")
            rows.append(("%-42s %-14s %s"
                         % (self.t("steam_short"), mark, lib),
                         "ok" if ok else "no"))
        return rows

    def _status_services(self, ops):
        rows = [("", "info"), (self.t("st_services"), "head")]
        rows.append(("  %-30s %-13s %s" % (self.t("svc_hdr_name"),
                                           self.t("svc_hdr_state"),
                                           self.t("svc_hdr_desc")), "muted"))
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
            if len(desc) > 80:
                desc = desc[:77] + "…"
            rows.append(("  %-30s %-13s %s" % (name, word, desc), tag))
        return rows

    def _status_kernel(self, A):
        def sv(p):
            try:
                r = subprocess.run(["sysctl", "-n", p],
                                   capture_output=True, text=True,
                                   timeout=3, env=self._host_env())
                return r.stdout.strip() if r.returncode == 0 else "n/a"
            except Exception:
                return "n/a"

        rows = [("", "info"), (self.t("st_kernel"), "head")]
        rows.append(("  %-32s %-11s %-30s %-14s"
                     % (self.t("kn_hdr_param"), self.t("kn_hdr_val"),
                        self.t("kn_hdr_desc"), self.t("kn_hdr_status")),
                     "muted"))
        kern = [
            ("vm.swappiness", self.t("kern_sw"), A.get("swap", False)),
            ("vm.vfs_cache_pressure", self.t("kern_vfs"),
             A.get("sysctl_cache", False)),
            ("kernel.numa_balancing", self.t("kern_numa"),
             A.get("sysctl_numa", False)),
            ("net.ipv4.tcp_congestion_control", self.t("kern_bbr"),
             A.get("bbr", False)),
        ]
        for p, dsc, ok in kern:
            if len(dsc) > 30:
                dsc = dsc[:27] + "…"
            status = self.t("yes") if ok else self.t("no")
            line = "  %-32s %-11s %-30s %-14s" % (p, sv(p), dsc, status)
            rows.append((line, "ok" if ok else "no"))
        raw = self._thp_current() or "n/a"
        thp_ok = A.get("thp", False)
        thp_dsc = self.t("kern_thp")
        if len(thp_dsc) > 30:
            thp_dsc = thp_dsc[:27] + "…"
        thp_status = self.t("yes") if thp_ok else self.t("no")
        rows.append(("  %-32s %-11s %-30s %-14s"
                     % ("transparent_hugepage", raw, thp_dsc, thp_status),
                     "ok" if thp_ok else "no"))
        return rows

    def _status_timer(self, ops):
        rows = [("", "info")]
        timer = ops.service_enabled("biweekly-upgrade.timer")
        if timer == "enabled":
            sched = self._schedule_text()
            timer_txt = sched if sched and sched != self.t("sched_none") \
                else self.t("st_enabled")
        else:
            timer_txt = self._fmt_state(timer)
        rows.append(("%s: %s" % (self.t("st_timer"), timer_txt),
                     "ok" if timer == "enabled" else "muted"))
        return rows

    def _status_inner(self):
        ops = SystemOps(self.sudo, self.state,
                        lambda m, t="normal": None, True)
        ops.mount_items = self.mount_items
        ops.commit_targets = list(self.commit_state.keys())
        try:
            A = self._detect_applied(ops)
            self.msg_queue.put(("applied", A))
        except Exception:
            A = self.applied

        rows = []
        rows += self._status_hardware(A)
        rows += self._status_partitions()
        rows += self._status_tweaks(A)
        rows += self._status_services(ops)
        rows += self._status_kernel(A)
        rows += self._status_timer(ops)
        self.msg_queue.put(("status_text", rows))

    def _render_status(self, rows):
        if self._status_view is None:
            return
        try:
            scroll_pos = self._status_view.yview()[0]
        except Exception:
            scroll_pos = 0.0
        self._status_view.configure(state=NORMAL)
        self._status_view.delete("1.0", END)
        for text, tag in rows:
            self._status_view.insert(END, text + "\n", tag)
        self._status_view.configure(state=DISABLED)
        try:
            self._status_view.yview_moveto(scroll_pos)
        except Exception:
            pass

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

    # ─── Диалоги ────────────────────────────────────────────────────────

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
                                        bg=c["terminal"],
                                        fg=c["terminal_fg"],
                                        relief=FLAT, bd=0, padx=10, pady=10,
                                        font=("DejaVu Sans", 10))
        txt.pack(fill=BOTH, expand=True, padx=8, pady=8)
        txt.insert("1.0", text)
        txt.configure(state=DISABLED)
        self._make_copyable(txt)
        Button(dlg, text=self.t("btn_close"), command=dlg.destroy,
               bg=c["button"], fg=c["fg"],
               activebackground=c["button_hover"],
               relief=FLAT, padx=14, pady=6).pack(pady=(0, 8))
        try:
            dlg.grab_set()
        except Exception:
            pass

    def _show_about(self):
        text = ("%s v%s (%s)\n\n%s\n\n%s: %s\n%s: %s\n%s\n\n%s"
                % (APP_NAME, APP_VERSION, APP_BUILD_DATE,
                   self.t("about_purpose"),
                   self.t("about_author"), self.t("about_author_name"),
                   self.t("about_license"), LICENSE_NAME,
                   GITHUB_URL,
                   self.t("about_disclaimer")))
        self._open_info_dialog(self.t("about_title"), text)

    def _open_path(self, path):
        ops = SystemOps(self.sudo, self.state,
                        lambda m, t="normal": None, True)
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
                                        bg=c["terminal"],
                                        fg=c["terminal_fg"],
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
               bg=c["button"], fg=c["fg"],
               activebackground=c["button_hover"],
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
        if not cands:
            return
        target = next((p for p in cands if os.path.exists(p)), None)
        if target is None:
            if not self.sudo._cached():
                if not self.sudo.ensure():
                    return
            target = next(
                (p for p in cands
                 if subprocess.run(["sudo", "-n", "test", "-e", p],
                                   capture_output=True,
                                   timeout=5).returncode == 0), None)
        if target is None:
            messagebox.showinfo(self.t("viewer"),
                                self.t("msg_nofile") + "\n" + "\n".join(cands),
                                parent=self.root)
            return
        ops = SystemOps(self.sudo, self.state,
                        lambda m, t="normal": None, True)
        ops.mount_items = self.mount_items
        content = ops.read_file(target) or ""
        self._show_viewer(target, content)

    def on_close(self):
        if self.is_running:
            if not messagebox.askyesno(APP_NAME, self.t("msg_close"),
                                       parent=self.root):
                return
        release_lock()
        try:
            self.root.destroy()
        except Exception:
            pass      
