# -*- coding: utf-8 -*-
"""
Linux Tweaker — модуль данных.

Здесь хранятся все константы, словари и строки интерфейса:
- APP_NAME, APP_VERSION, APP_BUILD_DATE
- THEMES — цвета светлой и тёмной темы
- OPTIONS_META — описания твиков
- OPTIONS_HELP — подробные справки по твикам
- CAT_ORDER — порядок категорий
- SERVICES_META — описания служб
- SERVICES_HELP — подробные справки по службам
- SERVICES_ORDER — порядок служб
- OPTION_FILES — пути к файлам, которые правят твики
- PIPEWIRE_PRESETS — пресеты буферов PipeWire
- STR — строки интерфейса (RU/EN)
"""

# ─── Общие сведения о приложении ────────────────────────────────────────────
APP_NAME = "Linux Tweaker"
APP_VERSION = "0.6.0"
APP_BUILD_DATE = "19.09.2026"
GITHUB_URL = "https://github.com/Prikolist2021/LinuxMint_Tweaker"
LICENSE_NAME = "MIT"

# ─── Файловые системы ───────────────────────────────────────────────────────
COMMIT_OK_FS = {"ext2", "ext3", "ext4"}

# ─── Блокировка запуска ─────────────────────────────────────────────────────
LOCK_FILE = "~/.linux-tweaker.lock"

# ─── Лимит областей памяти (vm.max_map_count) ───────────────────────────────
MAX_MAP_COUNT_VALUES = ["65530", "524288", "1048576", "2147483642"]
MAX_MAP_COUNT_DEFAULT = "1048576"

# ─── Валидация значений твиков ──────────────────────────────────────────────
COMMIT_MIN = 1
COMMIT_MAX = 3600
COMMIT_DEFAULT = "60"

SWAPPINESS_MIN = 0
SWAPPINESS_MAX = 200
SWAPPINESS_DEFAULT_DISK = "10"
SWAPPINESS_DEFAULT_ZRAM = "150"

TMPFS_SIZE_DEFAULT = "512M"
TMPFS_SIZE_REGEX = r"[0-9]+[MmGgKk]?"

# ─── Таймауты для sudo-команд (в секундах) ──────────────────────────────────
SUDO_TIMEOUT_DEFAULT = 180
SUDO_TIMEOUT_APT = 900
SUDO_TIMEOUT_GRUB = 300
SUDO_TIMEOUT_INITRAMFS = 600

# ─── Таймауты для быстрых утилит (в секундах) ───────────────────────────────
TIMEOUT_QUICK = 5
TIMEOUT_DPKG_QUERY = 60
TIMEOUT_APT_SIMULATE = 60
TIMEOUT_PKG_SIZE = 30

# ─── Бэкапы ─────────────────────────────────────────────────────────────────
BACKUP_KEEP_LAST = 5

# ─── Быстрое выключение (systemd timeout) ───────────────────────────────────
SHUTDOWN_TIMEOUT_VALUES = ["5s", "8s", "10s", "15s", "20s", "30s", "45s", "60s"]
SHUTDOWN_TIMEOUT_DEFAULT = "8s"

# ─── PipeWire пресеты ───────────────────────────────────────────────────────
PIPEWIRE_PRESETS = {
    "default": {
        "min": 512, "quantum": 4096, "max": 8192,
        "label_ru": "Обычный",
        "label_en": "Default",
        "desc_ru": "подходит большинству пользователей",
        "desc_en": "suitable for most users",
    },
    "gaming": {
        "min": 256, "quantum": 1024, "max": 2048,
        "label_ru": "Для игр",
        "label_en": "Gaming",
        "desc_ru": "минимальная задержка, но может быть треск",
        "desc_en": "minimal latency, but may crackle",
    },
    "recording": {
        "min": 1024, "quantum": 8192, "max": 16384,
        "label_ru": "Для записи",
        "label_en": "Recording",
        "desc_ru": "без треска, но с задержкой 0.1–0.2 с",
        "desc_en": "no crackle, but 0.1–0.2 s latency",
    },
}
PIPEWIRE_PRESET_DEFAULT = "default"

# ─── Категории приложений (вкладка «Приложения») ────────────────────────────
APPS_CATEGORY_ORDER = {
    "ru": ["Офис", "Графика", "Интернет", "Мультимедиа",
           "Игры", "Утилиты", "Прочее"],
    "en": ["Office", "Graphics", "Internet", "Multimedia",
           "Games", "Utilities", "Other"],
}

# ─── Маски системных пакетов (защита от удаления) ───────────────────────────
SYSTEM_PACKAGE_MASKS = (
    "mint-meta-", "ubuntu-desktop", "xubuntu-", "kubuntu-",
    "lubuntu-", "cinnamon", "mate-desktop", "xfce4",
    "gnome-shell", "ubuntu-minimal", "ubuntu-standard",
)

# ─── Таймауты перезагрузки systemd для отката ───────────────────────────────
SHUTDOWN_TIMEOUT_SYSTEM_DEFAULT = "90s"

# ─── Темы оформления ────────────────────────────────────────────────────────
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

# ─── Описания твиков ────────────────────────────────────────────────────────
# Каждый твик — кортеж из 4 строк:
#   (краткое название, описание, категория, короткая метка для статуса)
OPTIONS_META = {
    "journald": {
        "ru": ("Логи в ОЗУ (journald)", "Переносит журнал системы в оперативную память и ограничивает его 50 МБ. Бережёт SSD. Работает сразу.", "Логи системы", "хранение журналов systemd в ОЗУ (50 МБ)"),
        "en": ("Logs in RAM (journald)", "Moves the system log to RAM and caps it at 50 MB. Saves SSD. Works immediately.", "System logs", "systemd journals stored in RAM (50 MB)")},
    "audit": {
        "ru": ("audit=0 (GRUB)", "Отключает фоновую запись каждого действия системы. Убирает лишнюю нагрузку. Нужна перезагрузка.", "Ядро и загрузка", "фоновая запись действий"),
        "en": ("audit=0 (GRUB)", "Stops background logging of every system action. Removes extra load. Needs reboot.", "Kernel & boot", "background action logging")},
    "raid": {
        "ru": ("raid=noautodetect (GRUB)", "Пропускает поиск RAID при загрузке, если его нет. Экономит несколько секунд. ВНИМАНИЕ: не включайте, если у вас есть RAID. Нужна перезагрузка.", "Ядро и загрузка", "поиск RAID"),
        "en": ("raid=noautodetect (GRUB)", "Skips RAID probe at boot when you have none. Saves a few seconds. WARNING: do not enable with RAID. Needs reboot.", "Kernel & boot", "RAID probe")},
    "nmi_watchdog": {
        "ru": ("nmi_watchdog=0 (GRUB)", "Отключает служебные прерывания отладки. Убирает микро-фризы в играх. Нужна перезагрузка.", "Ядро и загрузка", "прерывания отладки"),
        "en": ("nmi_watchdog=0 (GRUB)", "Disables debug interrupts. Removes micro-stutters in games. Needs reboot.", "Kernel & boot", "debug interrupts")},
    "itco_wdt": {
        "ru": ("iTCO_wdt blacklist", "Дополнительный способ заглушить NMI watchdog, если параметр ядра не сработал. Модуль iTCO_wdt включает watchdog заново после загрузки. Работает только на Intel. Нужна перезагрузка.", "Ядро и загрузка", "Intel watchdog"),
        "en": ("iTCO_wdt blacklist", "Extra step to silence NMI watchdog when the kernel parameter did not help. Intel only. Needs reboot.", "Kernel & boot", "Intel watchdog")},
    "zfs_services": {
        "ru": ("ZFS: отключение и удаление", "Останавливает и маскирует ZFS-службы — они перестают участвовать в загрузке. Кнопка дополнительно удаляет zfsutils-linux и zfs-zed, чтобы модуль ядра вообще не загружался. Доступна только если ZFS-пулы не найдены.", "Ядро и загрузка", "службы ZFS"),
        "en": ("ZFS: disable and remove", "Stops and masks ZFS services so they no longer take part in boot. The button additionally removes zfsutils-linux and zfs-zed so the kernel module is never loaded. Available only if no ZFS pools are found.", "Kernel & boot", "ZFS services")},
    "shutdown_timeout": {
        "ru": ("Быстрое выключение", "Сокращает ожидание закрытия приложений при выключении с 90 до 8 секунд. Полезно, если игры или тяжёлые программы не закрываются сами. Нужна перезагрузка.", "Ядро и загрузка", "быстрое выключение ПК"),
        "en": ("Fast shutdown", "Cuts app-close timeout at shutdown from 90 to 8 seconds. Useful when games or heavy apps do not close themselves. Needs reboot.", "Kernel & boot", "fast shutdown")},
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
        "ru": ("MESA_SHADER_CACHE_MAX_SIZE=4G", "Увеличивает кэш шейдеров, игры меньше подтормаживают в первые минуты. Нужен перезаход.", "Видеокарта и графика", "кэш шейдеров"),
        "en": ("MESA_SHADER_CACHE_MAX_SIZE=4G", "Enlarges the shader cache so games stutter less at start. Requires re-login.", "GPU & graphics", "shader cache")},
    "pipewire": {
        "ru": ("PipeWire", "Убирает треск и щелчки звука, увеличив буферы звукового сервера. Нужен перезаход в сеанс.", "Звук", "чистый звук"),
        "en": ("PipeWire", "Removes sound crackling by enlarging sound-server buffers. Requires re-login.", "Sound", "clean sound")},
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
        "ru": ("zswap (GRUB)", "Держит сжатую память в ОЗУ перед записью в swap. Меньше обращений к диску. Нужна перезагрузка. Требует наличия swap.", "Память и swap", "сжатый кэш перед swap"),
        "en": ("zswap (GRUB)", "Keeps compressed memory in RAM before swap. Fewer disk accesses. Needs reboot. Requires swap to be present.", "Memory & swap", "compressed cache before swap")},
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
    "max_map_count": {
        "ru": ("vm.max_map_count", "Лимит областей памяти у одного процесса. Некоторые игры под Proton падают, если лимит исчерпан. Рекомендуется 1048576. Ускорения не даёт, только совместимость.", "Игры и совместимость", "лимит областей памяти"),
        "en": ("vm.max_map_count", "Limit of memory mappings per process. Some Proton games crash when the limit is exhausted. 1048576 is recommended. No speed gain, compatibility only.", "Gaming & compatibility", "memory mapping limit")},
    "ntfs3": {
        "ru": ("ntfs3 драйвер", "Включает быстрый драйвер NTFS-дисков вместо медленного. ВНИМАНИЕ: только если у вас есть NTFS-диски. Нужна перезагрузка.", "Диски и файловые системы", "быстрый NTFS"),
        "en": ("ntfs3 driver", "Enables the fast NTFS driver instead of the slow one. WARNING: only if you have NTFS disks. Needs reboot.", "Drives & filesystems", "fast NTFS")},
    "commit": {
        "ru": ("commit=NN (fstab, только ext3/ext4)", "Реже сбрасывает служебную информацию на диск, меньше износа SSD. Работает ТОЛЬКО на ext3/ext4 — для NTFS, FAT32, exFAT, btrfs, xfs параметр не поддерживается и приведёт к ошибке монтирования (система может упасть в emergency-режим). ВНИМАНИЕ: при сбое питания возможна потеря последних записей. Нужна перезагрузка.", "Диски и файловые системы", "реже запись на ext4"),
        "en": ("commit=NN (fstab, ext3/ext4 only)", "Flushes disk metadata less often, less SSD wear. Works ONLY on ext3/ext4 — NTFS, FAT32, exFAT, btrfs, xfs do not support it and will fail to mount (system may drop into emergency mode). WARNING: power loss may lose last writes. Needs reboot.", "Drives & filesystems", "less ext4 disk writing")},
    "tmpfs_tmp": {
        "ru": ("/tmp в ОЗУ (tmpfs, эксперимент)", "Монтирует /tmp в оперативной памяти. Меньше записей на диск, но данные исчезают при перезагрузке. НЕ включайте при гибернации, работе с большими временными файлами и малом объёме ОЗУ.", "Диски и файловые системы", "/tmp в оперативной памяти"),
        "en": ("/tmp in RAM (tmpfs, experimental)", "Mounts /tmp in RAM. Fewer disk writes, but data disappears on reboot. Do NOT enable with hibernation, large temp files or low RAM.", "Drives & filesystems", "/tmp in RAM")},
    "aliases": {
        "ru": ("Команды в .bashrc", "Добавляет удобные команды терминала для обновления и очистки. Работает в новых терминалах.", "Удобство", "команды терминала"),
        "en": ("Commands in .bashrc", "Adds handy terminal commands for updating and cleaning. Works in new terminals.", "Convenience", "terminal commands")},
    "autoupdate": {
        "ru": ("Автообновления", "Сам обновляет систему и Flatpak по расписанию. При включении автоматически глушит apt-daily.timer, apt-daily-upgrade.timer и unattended-upgrades, чтобы не было двойной работы. ВНИМАНИЕ: отключите встроенное автообновление Mint. Работает сразу.", "Обновления", "автообновление по расписанию"),
        "en": ("Auto-updates", "Auto-updates system and Flatpak on schedule. When enabled, automatically masks apt-daily.timer, apt-daily-upgrade.timer and unattended-upgrades to avoid double work. WARNING: disable Mint's built-in auto-update. Works immediately.", "Updates", "scheduled auto-update")},
}

# ─── Порядок категорий на вкладке «Тюнинг» ──────────────────────────────────
CAT_ORDER = {
    "ru": ["Видеокарта и графика", "Ядро и загрузка", "Логи системы", "Звук", "Сеть",
           "Память и swap", "Диски и файловые системы", "Игры и совместимость",
           "Удобство", "Обновления"],
    "en": ["GPU & graphics", "Kernel & boot", "System logs", "Sound", "Network",
           "Memory & swap", "Drives & filesystems", "Gaming & compatibility",
           "Convenience", "Updates"],
}

# ─── Описания служб (вкладка «Службы») ──────────────────────────────────────
SERVICES_META = {
    "avahi-daemon.service": {"ru": "Поиск устройств в домашней сети: принтеров, телевизоров, Chromecast. Не нужен, если у вас нет сетевого принтера.", "en": "Finds devices on your home network: printers, TVs, Chromecast. Not needed without a network printer."},
    "avahi-daemon.socket": {"ru": "Сокет, который будит службу avahi при обращении из сети. Сам по себе бесполезен без службы avahi.", "en": "Socket that wakes the avahi service on network request. Useless on its own without the avahi service."},
    "bluetooth.service": {"ru": "Служба Bluetooth: беспроводные мыши, клавиатуры, наушники, геймпады, файлообмен. Не отключайте, если пользуетесь Bluetooth-устройствами.", "en": "Bluetooth service: wireless mice, keyboards, headphones, gamepads, file transfer. Do not disable if you use Bluetooth devices."},
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
    "rsyslog.service": {"ru": "Пишет подробные журналы системы на диск. Отключение экономит место и уменьшает износ SSD; важные сообщения остаются в журнале systemd.", "en": "Writes detailed system logs to disk. Disabling saves space and reduces SSD wear; important messages remain in the systemd journal."},
    "apt-daily.timer": {"ru": "Ежедневно скачивает списки пакетов и обновления в фоне. Если вы включили автообновления в твикере, этот таймер глушится автоматически.", "en": "Downloads package lists and updates daily in the background. If you enable auto-updates in the tweaker, this timer is masked automatically."},
    "apt-daily-upgrade.timer": {"ru": "Ежедневно устанавливает обновления в фоне. Может конфликтовать с автообновлениями твикера. Глушится автоматически при их включении.", "en": "Installs updates daily in the background. May conflict with the tweaker's auto-updates. Masked automatically when they are enabled."},
    "unattended-upgrades.service": {"ru": "Устанавливает обновления безопасности автоматически. Если вы управляете обновлениями сами, служба не нужна.", "en": "Installs security updates automatically. If you manage updates yourself, the service is not needed."},
    "apport.service": {"ru": "Собирает краш-репорты (отчёты о падениях программ) и предлагает отправить их разработчикам. На домашнем ПК не нужна: только занимает место в /var/crash и показывает всплывающие окна при падении приложений.", "en": "Collects crash reports (reports about program crashes) and offers to send them to developers. Not needed on a home PC: only fills /var/crash and shows popups when apps crash."},
}

SERVICES_ORDER = list(SERVICES_META.keys())

# ─── Подробные справки по службам (по кнопке «?») ───────────────────────────
SERVICES_HELP = {
    "avahi-daemon.service": {
        "ru": "Avahi — это служба, которая ищет устройства в локальной сети без настройки. Она использует протокол mDNS/DNS-SD: устройства сами объявляют о себе, и вы видите их в списке доступных принтеров, колонок, телевизоров. Например, включив Chromecast, вы сразу видите его в браузере — это работа Avahi.\n\nНа домашнем ПК без сетевого принтера и без Chromecast/AirPlay служба не нужна. Она периодически рассылает пакеты в сеть, но делает это вхолостую.\n\nОтключение безопасно. Если позже захотите снова найти сетевое устройство — включите службу обратно.",
        "en": "Avahi is a service that discovers devices on your local network without setup. It uses the mDNS/DNS-SD protocol: devices announce themselves, and you see them in the list of available printers, speakers, TVs.\n\nOn a home PC without a network printer and without Chromecast/AirPlay, the service is unneeded. It periodically broadcasts into the network, but does so idle.\n\nDisabling is safe. If you later want to find a network device again, re-enable the service.",
    },
    "avahi-daemon.socket": {
        "ru": "Сокет — это как «розетка», которая «будит» службу Avahi, когда в сеть приходит первый запрос. У сокета и службы общая задача: пока никто не ищет устройства, Avahi может спать и не занимать ресурсы.\n\nЭтот сокет бесполезен сам по себе, без службы Avahi. Если Avahi отключена, сокет тоже не нужен.\n\nОтключайте его вместе со службой Avahi.",
        "en": "A socket is like a “plug” that wakes the Avahi service when the first network request arrives. The socket and the service share a task: while nobody is looking for devices, Avahi can sleep and use no resources.\n\nThis socket is useless on its own without the Avahi service. If Avahi is disabled, the socket is unneeded too.\n\nDisable it together with the Avahi service.",
    },
    "bluetooth.service": {
        "ru": "Bluetooth — это служба для беспроводных устройств: мыши, клавиатуры, наушники, колонки, геймпады, а также передача файлов между устройствами. Демон bluetoothd работает в фоне и обслуживает подключение и отключение устройств.\n\nЕсли вы не пользуетесь Bluetooth вообще, службу можно отключить. Выигрыш в загрузке минимальный — доли секунды, — но пропадает фоновая активность и закрывается поверхность атаки: Bluetooth-подсистема ядра периодически становилась источником уязвимостей.\n\nВНИМАНИЕ: после отключения Bluetooth-устройства перестанут подключаться. Если у вас беспроводная мышь, клавиатура или наушники — не отключайте. Также учтите, что служба может активироваться по требованию через D-Bus или bluetooth.target, поэтому для полного отключения нужен не только disable, но и mask.\n\nОтключение безопасно и обратимо: включение возвращает всё как было.",
        "en": "Bluetooth is a service for wireless devices: mice, keyboards, headphones, speakers, gamepads, and file transfer between devices. The bluetoothd daemon runs in the background and handles connecting and disconnecting devices.\n\nIf you do not use Bluetooth at all, the service can be disabled. The boot-time gain is minimal — fractions of a second — but background activity disappears and the attack surface shrinks: the kernel Bluetooth subsystem has periodically been a source of vulnerabilities.\n\nWARNING: after disabling, Bluetooth devices will stop connecting. If you use a wireless mouse, keyboard or headphones — do not disable. Also note that the service can be activated on demand via D-Bus or bluetooth.target, so for a full shutdown you need not only disable but also mask.\n\nDisabling is safe and reversible: re-enabling restores everything.",
    },
    "cups-browsed.service": {
        "ru": "cups-browsed — это часть системы печати CUPS. Она автоматически ищет сетевые принтеры и добавляет их в список доступных.\n\nДома эта служба не нужна, если у вас нет сетевого принтера. Если принтер подключён по USB, служба тоже бесполезна — она ищет только сетевые устройства.\n\nОтключение безопасно.",
        "en": "cups-browsed is part of the CUPS printing system. It automatically discovers network printers and adds them to the list of available ones.\n\nAt home the service is unneeded if you have no network printer. If the printer is connected via USB, the service is also useless — it only looks for network devices.\n\nDisabling is safe.",
    },
    "cups.service": {
        "ru": "CUPS — это служба печати и сканирования. Все программы, которые что-то печатают или сканируют, обращаются к ней.\n\nЕсли у вас нет принтера или сканера, CUPS просто висит в фоне и не делает ничего полезного. Отключение освобождает память и убирает фоновую активность.\n\nОтключение безопасно.",
        "en": "CUPS is the printing and scanning service. Every program that prints or scans talks to it.\n\nIf you have no printer or scanner, CUPS just idles in the background doing nothing useful. Disabling it frees memory and removes background activity.\n\nDisabling is safe.",
    },
    "cups.socket": {
        "ru": "Сокет — это «розетка», которая будит службу печати CUPS, когда какая-то программа пытается что-то напечатать. Пока никто не печатает, CUPS может не работать.\n\nЭтот сокет бесполезен без службы CUPS. Если вы отключили CUPS, сокет тоже не нужен.\n\nОтключайте его вместе со службой CUPS.",
        "en": "A socket is a “plug” that wakes the CUPS print service when a program tries to print. While nobody prints, CUPS does not have to run.\n\nThis socket is useless without the CUPS service. If you disabled CUPS, the socket is unneeded too.\n\nDisable it together with the CUPS service.",
    },
    "ModemManager.service": {
        "ru": "ModemManager — это служба для работы с мобильными модемами. Она управляет устройствами, которые подключаются к компьютеру через USB или встроены в ноутбук и работают через сим-карту.\n\nНа стационарном ПК без модема эта служба не нужна. Более того, она иногда мешает устройствам, которые определяются как последовательный порт (serial port): Arduino, переходники USB-Serial, отладочные платы.\n\nЕсли у вас есть такие устройства и они работают нестабильно — отключение ModemManager часто решает проблему.",
        "en": "ModemManager is a service for mobile modems. It manages devices plugged in via USB or built into a laptop and working via SIM.\n\nOn a desktop PC without a modem the service is unneeded. Moreover, it sometimes interferes with devices that appear as serial ports: Arduino, USB-Serial adapters, development boards.\n\nIf you have such devices and they work unreliably, disabling ModemManager often fixes the problem.",
    },
    "openvpn.service": {
        "ru": "OpenVPN — это система для создания защищённых туннелей между компьютерами. Служба openvpn.service относится к серверной части: она принимает входящие подключения от других устройств. Если вы обычно используете VPN-клиент (например, подключаетесь к коммерческому VPN), это не та служба.\n\nДома эту службу держат только те, кто поднимает собственный VPN-сервер.\n\nОтключение безопасно.",
        "en": "OpenVPN is a system for creating secure tunnels between computers. The openvpn.service unit is the server side: it accepts incoming connections from other devices. If you usually use a VPN client (for example, connecting to a commercial VPN), that is not this service.\n\nAt home only those who run their own VPN server keep this service.\n\nDisabling is safe.",
    },
    "lvm2-monitor.service": {
        "ru": "LVM — это способ объединить несколько дисков или разделов в один большой «виртуальный» диск. Служба lvm2-monitor следит за состоянием таких объединений и уведомляет о проблемах.\n\nПри обычной установке Linux Mint или Ubuntu LVM не используется. Диски и разделы подключаются напрямую.\n\nОтключение безопасно. Не отключайте, если вы специально настраивали LVM.",
        "en": "LVM is a way to combine several disks or partitions into one big “virtual” disk. The lvm2-monitor service watches such unions and reports problems.\n\nA standard Linux Mint or Ubuntu install does not use LVM. Disks and partitions are attached directly.\n\nDisabling is safe. Do not disable it if you specifically configured LVM.",
    },
    "switcheroo-control.service": {
        "ru": "Switcheroo — это служба для ноутбуков с двумя видеокартами (обычно встроенной Intel и отдельной NVIDIA или AMD). Она позволяет переключаться между картами.\n\nНа настольном ПК с одной видеокартой эта служба не нужна.\n\nОтключение безопасно. Если у вас ноутбук с двумя картами, лучше оставить.",
        "en": "Switcheroo is a service for laptops with two GPUs (usually an integrated Intel and a discrete NVIDIA or AMD). It lets you switch between them.\n\nOn a desktop PC with a single GPU the service is unneeded.\n\nDisabling is safe. If you have a laptop with two GPUs, better leave it enabled.",
    },
    "touchegg.service": {
        "ru": "Touchegg — это служба, которая распознаёт мультитач-жесты на тачпадах и сенсорных экранах.\n\nНа настольном ПК без сенсорного ввода эта служба не нужна.\n\nОтключение безопасно. Если у вас ноутбук с тачпадом и вы пользуетесь жестами — оставьте включённой.",
        "en": "Touchegg is a service that recognizes multitouch gestures on touchpads and touchscreens.\n\nOn a desktop PC without touch input the service is unneeded.\n\nDisabling is safe. If you have a laptop with a touchpad and use gestures, keep it enabled.",
    },
    "zfs-zed.service": {
        "ru": "ZFS — это современная файловая система с поддержкой дисковых массивов. ZED — это демон ZFS, который следит за состоянием массивов и предупреждает о проблемах с дисками.\n\nНа домашнем ПК с обычными файловыми системами (ext4, btrfs) ZFS не используется.\n\nОтключение безопасно. Не отключайте, если у вас действительно есть ZFS-пулы.",
        "en": "ZFS is a modern file system with disk arrays. ZED is the ZFS daemon that watches array health and warns about disk problems.\n\nOn a home PC with conventional file systems (ext4, btrfs) ZFS is not used.\n\nDisabling is safe. Do not disable it if you actually have ZFS pools.",
    },
    "kerneloops.service": {
        "ru": "kerneloops — это служба, которая собирает отчёты о сбоях ядра (kernel oops) и отправляет их разработчикам. Информация уходит на сервер проекта.\n\nНа домашнем ПК эта служба приносит мало пользы. Она лишь добавляет фоновую нагрузку и исходящий трафик.\n\nОтключение безопасно. Оставьте включённой, если хотите помогать разработчикам ядра.",
        "en": "kerneloops is a service that collects reports about kernel crashes (kernel oops) and sends them to developers. The information goes to the project's server.\n\nOn a home PC the service brings little benefit. It only adds background load and outgoing traffic.\n\nDisabling is safe. Keep it enabled if you want to help kernel developers.",
    },
    "rsyslog.service": {
        "ru": "rsyslog — это служба, которая постоянно пишет подробные журналы системы в текстовые файлы на диске. Каждую секунду она дописывает туда события: запуск служб, ошибки, вход пользователей.\n\nОтключение освобождает место в /var/log и уменьшает износ SSD. Важные сообщения при этом никуда не пропадают — они идут в журнал systemd, который смотрится командой journalctl.\n\nОтключение безопасно и работает сразу.",
        "en": "rsyslog is a service that constantly writes detailed system logs into text files on the disk. Every second it appends events: service starts, errors, user logins.\n\nDisabling it frees space in /var/log and reduces SSD wear. Important messages are not lost — they go to the systemd journal, which you can view with journalctl.\n\nDisabling is safe and works immediately.",
    },
    "apt-daily.timer": {
        "ru": "apt-daily.timer — это systemd-таймер, который раз в сутки запускает загрузку свежих списков пакетов и обновлений в фоне.\n\nПроблема в том, что если вы уже включили автообновления в твикере, этот таймер начинает работать параллельно и создаёт двойную нагрузку. Твикер глушит его автоматически при включении автообновлений.\n\nОтключайте его вручную только если вы вообще не хотите, чтобы система что-то скачивала в фоне.",
        "en": "apt-daily.timer is a systemd timer that once a day fetches fresh package lists and updates in the background.\n\nThe problem is that if you have already enabled auto-updates in the tweaker, this timer runs in parallel and creates a double load. The tweaker masks it automatically when auto-updates are enabled.\n\nDisable it manually only if you do not want the system to download anything in the background at all.",
    },
    "apt-daily-upgrade.timer": {
        "ru": "apt-daily-upgrade.timer — это дополнение к apt-daily.timer: он не просто скачивает списки пакетов, а устанавливает обновления в фоне.\n\nЕсли вы включили автообновления в твикере, этот таймер дублирует их работу. Твикер глушит его автоматически.\n\nОтключайте вручную только если вы точно управляете обновлениями сами.",
        "en": "apt-daily-upgrade.timer complements apt-daily.timer: it not only downloads package lists but actually installs updates in the background.\n\nIf you enabled auto-updates in the tweaker, this timer duplicates their work. The tweaker masks it automatically.\n\nDisable it manually only if you truly manage updates yourself.",
    },
    "unattended-upgrades.service": {
        "ru": "unattended-upgrades — это служба, которая устанавливает обновления безопасности автоматически, без вашего участия.\n\nНа домашнем ПК это удобно, если вы не хотите думать об обновлениях. Но если вы уже управляете обновлениями через твикер, служба становится лишней. Твикер глушит её автоматически при включении автообновлений.\n\nЕсли вы не включаете автообновления в твикере и не управляете обновлениями вручную — лучше оставить службу включённой.",
        "en": "unattended-upgrades is a service that installs security updates automatically, without your involvement.\n\nOn a home PC this is convenient if you do not want to think about updates. But if you already manage updates through the tweaker, the service becomes redundant. The tweaker masks it automatically when auto-updates are enabled.\n\nIf you do not enable auto-updates in the tweaker and do not manage updates manually — better leave the service enabled.",
    },
    "apport.service": {
        "ru": "Apport — это система сбора краш-репортов в Ubuntu и Linux Mint. Когда какая-то программа падает, Apport перехватывает это, сохраняет дамп памяти в /var/crash и предлагает отправить отчёт разработчикам.\n\nНа домашнем ПК эта служба почти всегда не нужна. Она тратит немного ресурсов на перехват падений, накапливает дампы в /var/crash (которые потом надо чистить), и показывает всплывающее окно при падении любой программы — даже если вам это неинтересно.\n\nОтключение безопасно: если у вас упадёт приложение, вы просто не получите всплывающее окно и не сможете отправить баг-репорт. Сама программа от этого работать не перестанет.\n\nЕсли вы активно помогаете разработчикам Ubuntu/Mint и отправляете баг-репорты — оставьте службу включённой.\n\nОтключайте, если: у вас домашний ПК, вы не отправляете баг-репорты, и вас раздражают всплывающие окна при падениях.",
        "en": "Apport is the crash-report collection system in Ubuntu and Linux Mint. When a program crashes, Apport catches it, saves a memory dump in /var/crash and offers to send a report to developers.\n\nOn a home PC this service is almost always unneeded. It spends a little resources on catching crashes, accumulates dumps in /var/crash (which you then have to clean), and shows a popup whenever any program crashes — even if you are not interested.\n\nDisabling is safe: if an app crashes, you simply will not get a popup and will not be able to send a bug report. The app itself will not stop working because of this.\n\nIf you actively help Ubuntu/Mint developers and send bug reports — keep the service enabled.\n\nDisable it if: you have a home PC, you do not send bug reports, and popups on crashes annoy you.",
    },
}

# ─── Пути к файлам, которые правят твики (для кнопки «файл») ────────────────
OPTION_FILES = {
    "journald": ["/etc/systemd/journald.conf"],
    "audit": ["/etc/default/grub"],
    "raid": ["/etc/default/grub"],
    "nmi_watchdog": ["/etc/default/grub"],
    "itco_wdt": ["/etc/modprobe.d/nmi-watchdog.conf"],
    "zfs_services": ["/etc/default/zfs"],
    "shutdown_timeout": ["/etc/systemd/system.conf"],
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
    "max_map_count": ["/etc/sysctl.d/99-gaming-mmap.conf"],
    "ntfs3": ["/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"],
    "commit": ["/etc/fstab"],
    "tmpfs_tmp": ["/etc/fstab"],
    "aliases": ["{home}/.bashrc"],
    "autoupdate": ["/etc/systemd/system/biweekly-upgrade.timer",
                   "/etc/systemd/system/biweekly-upgrade.service"],
}

# ─── Подробные справки по твикам (кнопка «?») ───────────────────────────────
OPTIONS_HELP = {
    "journald": {
        "ru": "Журнал systemd — это запись всех событий системы: запуск служб, ошибки, подключения устройств. Обычно он хранится на диске и со временем разрастается до сотен мегабайт.\n\nЭта опция переносит журнал в оперативную память и ограничивает его 50 мегабайтами. Диск перестаёт получать постоянные записи, а значит, меньше изнашивается. Особенно полезно на SSD и на домашнем ПК, где журнал почти никто не читает.\n\nНе включайте, если вы привыкли разбирать старые проблемы по логам: после перезагрузки журнал в памяти исчезнет. Если вам нужны долгосрочные записи — оставьте как есть.\n\nОпция применяется сразу, перезагрузка не нужна.",
        "en": "The systemd journal records all system events: service starts, errors, device plugs. It usually lives on disk and grows to hundreds of megabytes over time.\n\nThis option moves the journal into RAM and caps it at 50 MB. The disk stops getting constant writes, which means less wear. It is especially useful on an SSD and on a home PC, where nobody reads the journal anyway.\n\nDo not enable it if you are used to troubleshooting by reading old logs: after a reboot the journal in RAM disappears. If you need long-term records, leave it as is.\n\nThe option applies immediately, no reboot needed.",
    },
    "audit": {
        "ru": "audit — это служба ядра, которая записывает каждое действие системы: какой процесс открыл файл, какой пользователь запустил программу. Такая детальная запись нужна в офисах и на серверах для безопасности.\n\nДома она не нужна. Каждый системный вызов превращается в запись в журнал, а это лишняя нагрузка на процессор и диск. Отключение убирает эти накладные расходы и немного ускоряет систему.\n\nНе отключайте, если вам действительно нужны журналы безопасности для проверок — например, в организации с требованиями по аудиту.\n\nПараметр audit=0 добавляется в GRUB, поэтому изменения вступят в силу только после перезагрузки.",
        "en": "audit is a kernel service that logs every system action: which process opened a file, which user started a program. Such detailed logging is needed in offices and on servers for security.\n\nAt home it is unnecessary. Every system call turns into a log entry, which adds CPU and disk load. Disabling it removes this overhead and slightly speeds up the system.\n\nDo not disable it if you actually need security logs for audits.\n\nThe audit=0 parameter is added to the GRUB bootloader, so the change only takes effect after a reboot.",
    },
    "raid": {
        "ru": "RAID — это способ объединить несколько физических дисков в один логический: для скорости или для надёжности. Если у вас такое объединение есть, у вас RAID.\n\nЕсли RAID нет, при каждой загрузке ядро всё равно несколько секунд ищет массивы и не находит. Эти секунды можно сэкономить: параметр raid=noautodetect отключает поиск и ускоряет включение.\n\nВНИМАНИЕ: не включайте эту опцию, если вы используете RAID. Система перестанет находить массивы при загрузке, и вы можете потерять доступ к данным.\n\nПараметр добавляется в GRUB, изменения вступают в силу после перезагрузки.",
        "en": "RAID is a way to combine several physical disks into one logical one: for speed, or for reliability. If your system has such a combination, you have RAID.\n\nIf there is no RAID, the kernel still spends a few seconds at every boot probing for arrays and finds nothing. You can save those seconds: raid=noautodetect disables the probe and speeds up startup.\n\nWARNING: do not enable this option if you use RAID. The system will stop finding your arrays at boot, and you may lose access to your data.\n\nThe parameter is added to GRUB, changes take effect after a reboot.",
    },
    "nmi_watchdog": {
        "ru": "NMI-watchdog — это служебный механизм ядра для отладки зависаний. Он периодически посылает процессору специальные сигналы (немаскируемые прерывания), чтобы проверить, что система ещё жива.\n\nНа домашнем ПК такая отладка не нужна. А периодические прерывания, пусть и редкие, дают микро-фризы в играх и чувствительных к задержкам задачах. Отключение убирает эти паузы.\n\nНе отключайте, если вы специально занимаетесь отладкой зависаний ядра и вам нужны эти данные.\n\nПараметр nmi_watchdog=0 добавляется в GRUB, поэтому изменения вступают в силу после перезагрузки.\n\nВАЖНО: на некоторых системах (особенно с Intel-чипсетом) модуль iTCO_wdt включает watchdog заново после загрузки. Проверить можно командой: cat /proc/sys/kernel/nmi_watchdog. Если там 1 — используйте дополнительный твик «iTCO_wdt blacklist».",
        "en": "The NMI watchdog is a kernel debugging facility for detecting hangs. It periodically sends special signals to the CPU (non-maskable interrupts) to check that the system is still alive.\n\nOn a home PC such debugging is unnecessary. And the periodic interrupts, even rare ones, cause micro-stutters in games and latency-sensitive tasks. Disabling them removes those pauses.\n\nDo not disable it if you specifically debug kernel hangs and need that data.\n\nThe nmi_watchdog=0 parameter is added to GRUB, so changes take effect after a reboot.\n\nIMPORTANT: on some systems (especially with an Intel chipset) the iTCO_wdt module re-enables the watchdog after boot. Check with: cat /proc/sys/kernel/nmi_watchdog. If it shows 1, use the extra tweak «iTCO_wdt blacklist».",
    },
    "itco_wdt": {
        "ru": "Этот твик — дополнение к «nmi_watchdog=0 (GRUB)». На многих системах с Intel-чипсетом после загрузки ядра модуль iTCO_wdt снова включает NMI watchdog, даже если вы передали параметр nmi_watchdog=0. В итоге /proc/sys/kernel/nmi_watchdog снова становится 1, и микро-фризы возвращаются.\n\nРешение — заблокировать модуль iTCO_wdt, чтобы он вообще не загружался. В файле /etc/modprobe.d/nmi-watchdog.conf прописываются строки blacklist и install ... /bin/false.\n\nТвик становится активным только если одновременно выполнены три условия: Intel-чипсет, модуль iTCO_wdt поддерживается ядром и NMI watchdog всё ещё активен (nmi_watchdog=0 уже в GRUB, но /proc/sys/kernel/nmi_watchdog показывает 1).\n\nВАЖНО: NMI watchdog помогает диагностировать аппаратные зависания (например, сбои процессора или памяти). Отключая его, вы теряете часть возможностей диагностики. Если у вас нет конкретной проблемы с микро-фризами или нестабильностью, этот твик может быть не оправдан.\n\nЕсли и этот твик не помог (watchdog всё ещё 1), значит его включает другой модуль — например, intel_oc_wdt или sp5100_tco. Проверить: lsmod | grep -i wdt.\n\nПроверить состояние после перезагрузки: cat /proc/sys/kernel/nmi_watchdog — должно быть 0.",
        "en": "This tweak complements «nmi_watchdog=0 (GRUB)». On many systems with an Intel chipset, the iTCO_wdt module re-enables the NMI watchdog after the kernel is loaded — even if you passed nmi_watchdog=0.\n\nThe fix is to block the iTCO_wdt module entirely. In /etc/modprobe.d/nmi-watchdog.conf lines blacklist and install ... /bin/false are written.\n\nThe tweak becomes active only when three conditions are met at once: Intel chipset, iTCO_wdt module supported by the kernel, and NMI watchdog still active (nmi_watchdog=0 already in GRUB but /proc/sys/kernel/nmi_watchdog shows 1).\n\nIMPORTANT: the NMI watchdog helps diagnose hardware hangs. By disabling it, you lose some diagnostic capability. If you do not have a specific problem with micro-stutters or instability, this tweak may not be justified.\n\nIf even this tweak does not help (watchdog is still 1), another module enables it — for example intel_oc_wdt or sp5100_tco. Check: lsmod | grep -i wdt.\n\nCheck the state after reboot: cat /proc/sys/kernel/nmi_watchdog — should be 0.",
    },
    "zfs_services": {
        "ru": "ZFS — это файловая система и менеджер томов, который используется на серверах и NAS. На домашнем ПК его обычно не ставят, но некоторые дистрибутивы (Ubuntu, Mint) устанавливают пакеты ZFS «на всякий случай».\n\nПроблема в том, что даже если ZFS не используется, его службы всё равно запускаются при загрузке: zfs-import.target, zfs-mount.service, zfs-share.service, zfs-volume-wait.service. Они тянут за собой systemd-udev-settle.service, который может занимать несколько секунд.\n\nЭтот твик делает две вещи. Первое — при отметке останавливает и маскирует ZFS-службы: они больше не запускаются, но пакеты остаются на месте. Это обратимо. Второе — кнопка «Удалить пакеты (осторожно)» полностью удаляет zfsutils-linux и zfs-zed. Эта операция необратима: вернуть можно только вручную командой sudo apt install zfsutils-linux.\n\nВАЖНО: перед удалением пакетов твикер проверяет, используется ли ZFS на самом деле. Если найден хотя бы один пул или монтирование, кнопка удаления становится серой.\n\nЕсли вы не знаете, используете ли ZFS — отметьте только первый вариант (отключение служб). Он безопасен и даёт заметную часть выигрыша.",
        "en": "ZFS is a file system and volume manager used on servers and NAS. It is usually not installed on a home PC, but some distributions (Ubuntu, Mint) install ZFS packages «just in case».\n\nThe problem is that even if ZFS is not used, its services still run at boot: zfs-import.target, zfs-mount.service, zfs-share.service, zfs-volume-wait.service. They pull in systemd-udev-settle.service, which can take several seconds.\n\nThis tweak does two things. First — when ticked, it stops and masks ZFS services: they no longer start, but the packages remain. This is reversible. Second — the «Remove packages (careful)» button fully removes zfsutils-linux and zfs-zed. That operation is irreversible: you can only return it manually with sudo apt install zfsutils-linux.\n\nIMPORTANT: before removing packages, the tweaker checks whether ZFS is actually used. If at least one pool or mount is found, the removal button becomes greyed out.\n\nIf you do not know whether ZFS is used — tick only the first option (disable services). It is safe and gives a noticeable part of the gain.",
    },
    "shutdown_timeout": {
        "ru": "По умолчанию systemd ждёт 90 секунд, пока приложения и службы закроются при выключении ПК. Если какая-то программа не отвечает (Wine-игра, Electron-приложение, зависший процесс), система показывает «A stop job is running» и висит все 90 секунд, прежде чем принудительно убить процесс.\n\nЭтот твик сокращает ожидание до 5–60 секунд (по умолчанию 8). Выключение становится быстрым.\n\nВНИМАНИЕ: если приложение в момент выключения сохраняло данные (база, торрент, редактор), его могут убить до завершения записи. Для обычного домашнего ПК риск минимальный, но для систем с базами данных или активной записью — не включайте.\n\nЕсли у вас очень старый systemd (Ubuntu 20.04, Mint 20), параметр может игнорироваться — там есть баг.\n\nИзменения вступают в силу после перезагрузки.",
        "en": "By default systemd waits 90 seconds for apps and services to close at shutdown. If some program does not respond (Wine game, Electron app, hung process), the system shows «A stop job is running» and hangs the full 90 seconds before force-killing the process.\n\nThis tweak cuts the wait to 5–60 seconds (8 by default). Shutdown becomes fast.\n\nWARNING: if an app was saving data at shutdown (database, torrent, editor), it may be killed before finishing the write. For a normal home PC the risk is minimal, but for systems with databases or active writes — do not enable.\n\nIf you have a very old systemd (Ubuntu 20.04, Mint 20), the parameter may be ignored — there is a bug there.\n\nChanges take effect after a reboot.",
    },
    "corectrl": {
        "ru": "CoreCtrl — это программа для тонкой настройки видеокарт AMD. Она позволяет менять частоты, управлять вентиляторами, задавать лимиты питания и следить за температурой.\n\nПо умолчанию все действия CoreCtrl требуют пароль администратора. Данная опция создаёт правило Polkit, которое разрешает вашей группе пользователей управлять видеокартой без пароля.\n\nНе включайте, если у вас не AMD или вы не пользуетесь CoreCtrl. В поле «Группа» укажите группу пользователей, которой разрешено управление.\n\nОпция работает сразу, перезагрузка не нужна. Откат удаляет правило Polkit.",
        "en": "CoreCtrl is a tool for fine-tuning AMD graphics cards. It lets you change clocks, control fans, set power limits and monitor temperature.\n\nBy default every CoreCtrl action asks for the admin password. This option creates a Polkit rule that allows your user group to control the GPU without a password.\n\nDo not enable it if you do not have an AMD GPU or do not use CoreCtrl. In the Group field, specify the user group allowed to control the GPU.\n\nThe option applies immediately, no reboot needed. Rolling back removes the Polkit rule.",
    },
    "ppfeaturemask": {
        "ru": "На старых ядрах драйвер amdgpu блокирует часть функций управления питанием видеокарты AMD. Это сделано в целях безопасности: некоторые режимы могут работать нестабильно на старых картах. Но именно эти режимы нужны для тонкой настройки частот через CoreCtrl.\n\nПараметр amdgpu.ppfeaturemask=0xffffffff снимает блокировку и открывает драйверу полный контроль над частотами и питанием. После этого CoreCtrl сможет менять всё, что вы захотите.\n\nНе включайте, если у вас не AMD или вы не собираетесь настраивать частоты. Также не стоит включать, если у вас очень старая карта — она может работать нестабильно.\n\nПараметр добавляется в GRUB, поэтому изменения вступают в силу после перезагрузки.",
        "en": "On older kernels the amdgpu driver blocks some AMD GPU power-management features. This is a safety measure: some modes can be unstable on old cards. But those are exactly the modes you need for fine-tuning clocks via CoreCtrl.\n\nThe parameter amdgpu.ppfeaturemask=0xffffffff lifts the block and gives the driver full control over clocks and power. After that CoreCtrl can change everything you want.\n\nDo not enable it if you do not have AMD or do not plan to tune clocks. Also do not enable it on a very old card — it may become unstable.\n\nThe parameter is added to GRUB, so changes take effect after a reboot.",
    },
    "nvidia_modeset": {
        "ru": "Для проприетарного драйвера NVIDIA нужен специальный режим вывода видео — kernel modesetting (KMS). Без него система работает с устаревшим способом вывода, из-за чего не запускается Wayland и возможны проблемы при переключении видеорежимов.\n\nПараметр nvidia-drm.modeset=1 включает современный режим KMS. После этого Wayland работает корректно, переключение между разрешениями экрана происходит плавно, анимации в системе не дёргаются.\n\nНе включайте, если у вас не NVIDIA.\n\nПараметр добавляется в GRUB, поэтому изменения вступают в силу после перезагрузки.",
        "en": "The proprietary NVIDIA driver needs a special video-output mode — kernel modesetting (KMS). Without it the system uses the legacy path, Wayland does not work, and mode switching may glitch.\n\nThe parameter nvidia-drm.modeset=1 enables modern KMS. After that Wayland works correctly, switching screen resolutions is smooth, and system animations do not stutter.\n\nDo not enable it if you do not have NVIDIA.\n\nThe parameter is added to GRUB, so changes take effect after a reboot.",
    },
    "vrr": {
        "ru": "VRR (он же FreeSync или Adaptive Sync) — это переменная частота обновления монитора. Обычно монитор обновляется с фиксированной частотой, например 60 Гц. Если игра выдаёт 47 FPS, кадры попадают на разные обновления, и картинка «рвётся». С VRR монитор подстраивается под текущий FPS.\n\nЭта опция включает VRR для видеокарт AMD в X11 с драйвером amdgpu.\n\nНе включайте, если у вас монитор без поддержки FreeSync, видеокарта не AMD, или вы работаете в Wayland.\n\nСоздаётся конфиг X11, для вступления в силу нужно перезайти в сеанс или перезагрузиться.",
        "en": "VRR (also known as FreeSync or Adaptive Sync) is a variable monitor refresh rate. Normally the monitor refreshes at a fixed rate, say 60 Hz. If a game outputs 47 FPS, frames land on different refreshes and the picture tears. With VRR the monitor adapts to the current FPS.\n\nThis option enables VRR for AMD GPUs in X11 with the amdgpu driver.\n\nDo not enable it if your monitor does not support FreeSync, your GPU is not AMD, or you run Wayland.\n\nAn X11 config is created; to apply it you need to re-login or reboot.",
    },
    "radv": {
        "ru": "SAM (Smart Access Memory) или Resizable BAR — это технология, при которой процессор получает доступ ко всей видеопамяти сразу, а не кусками по 256 МБ. Обычно это даёт небольшой прирост FPS в играх.\n\nПараметр RADV_PERFTEST=sam включает поддержку SAM в открытом драйвере RADV.\n\nНе включайте, если у вас не AMD, старая материнская плата без поддержки Resizable BAR, или вы работаете с драйвером NVIDIA.\n\nПеременная записывается в /etc/environment и применяется при входе в сеанс. Нужно перезайти в сеанс или перезагрузиться.",
        "en": "SAM (Smart Access Memory) or Resizable BAR is a technology where the CPU gets access to all VRAM at once instead of chunks of 256 MB. It usually gives a small FPS gain in games.\n\nThe RADV_PERFTEST=sam parameter enables SAM support in the open RADV driver.\n\nDo not enable it if you do not have AMD, have an old motherboard without Resizable BAR support, or use the NVIDIA driver.\n\nThe variable is written to /etc/environment and applies at login. You need to re-login or reboot.",
    },
    "mesa": {
        "ru": "MESA — это набор графических библиотек, которые используют игры и программы для вывода картинки. Одна из функций MESA — кэширование скомпилированных шейдеров.\n\nПо умолчанию кэш MESA небольшой, и когда он переполняется, старые шейдеры удаляются. При следующем запуске игры они компилируются заново — это и вызывает подтормаживания в первые минуты. Если увеличить кэш до 4 ГБ, шейдеры останутся, и игра будет запускаться сразу плавно.\n\nНе включайте, если вы не играете в игры с шейдерами.\n\nПеременная записывается в /etc/environment и применяется при входе в сеанс.",
        "en": "MESA is a set of graphics libraries that games and applications use to render the picture. One of MESA's features is caching compiled shaders.\n\nBy default the MESA cache is small, and when it overflows, old shaders are deleted. The next time you launch the game, they are recompiled — that is what causes stutters in the first minutes. If you raise the cache to 4 GB, shaders stay, and the game launches smoothly right away.\n\nDo not enable it if you do not play shader-heavy games.\n\nThe variable is written to /etc/environment and applies at login.",
    },
    "pipewire": {
        "ru": "PipeWire — это звуковой сервер, который передаёт звук от приложений к колонкам и наушникам. У него есть настройка размера буферов: маленькие буферы дают низкую задержку, но на некоторых системах вызывают треск и щелчки. Большие буферы убирают артефакты, но добавляют небольшую задержку.\n\nЕсть три режима на выбор:\n\n• Обычный — подходит большинству пользователей.\n• Для игр — минимальная задержка звука; может вызывать треск на слабых системах.\n• Для записи — максимальная стабильность; звук может отставать на 0.1–0.2 секунды. Для музыкантов не подходит.\n\nТвик доступен только если PipeWire установлен или уже запущен как звуковой сервер. Если у вас PulseAudio или чистая ALSA — конфиг PipeWire ничего не даст.\n\nСоздаётся конфиг в вашей домашней папке. Нужно перезайти в сеанс или перезагрузиться.",
        "en": "PipeWire is the sound server that hands audio from applications to speakers and headphones. It has a buffer-size setting: small buffers give low latency but on some systems cause crackling and pops. Large buffers remove the artifacts but add a little latency.\n\nThere are three modes:\n\n• Default — suitable for most users.\n• Gaming — minimal audio latency; may crackle on weak systems.\n• Recording — maximum stability; sound may lag by 0.1–0.2 seconds. Not suitable for musicians.\n\nThe tweak is available only if PipeWire is installed or already running as the sound server. If you use PulseAudio or plain ALSA — the PipeWire config will do nothing.\n\nA config is created in your home folder. You need to re-login or reboot.",
    },
    "bbr": {
        "ru": "BBR — это современный алгоритм управления перегрузками TCP, разработанный Google. Он определяет, с какой скоростью отправлять данные по сети, чтобы не перегружать канал и не терять пакеты. Старый алгоритм CUBIC работает хорошо на стабильных каналах, но BBR выигрывает на нестабильных.\n\nЭта опция включает BBR и очередь fq. На Wi-Fi, VPN, мобильном интернете и дальних серверах скорость загрузки становится выше, а задержки — меньше. На стабильном кабеле разница почти не заметна.\n\nНе включайте, если у вас стабильный проводной интернет.\n\nПараметр применяется сразу, перезагрузка не нужна.",
        "en": "BBR is a modern TCP congestion-control algorithm developed by Google. It decides at what rate to send data over the network so the link is not overloaded and packets are not lost. The older CUBIC algorithm works well on stable links, but BBR wins on unstable ones.\n\nThis option enables BBR and the fq queue. On Wi-Fi, VPN, mobile internet and remote servers, download speed increases and latency drops. On a stable cable the difference is barely noticeable.\n\nDo not enable it if you have a stable wired internet connection.\n\nThe parameter applies immediately, no reboot needed.",
    },
    "swap": {
        "ru": "Swap (подкачка) — это область на диске или в сжатой памяти, куда система складывает редко используемые данные, когда оперативной памяти не хватает. Насколько охотно система это делает — задаётся числом vm.swappiness от 0 до 200.\n\nВысокое значение (например, 150) означает: система активно переносит данные в swap. Это выгодно, если swap — это zram (сжатая память в ОЗУ). Низкое значение (10) означает: система старается держать данные в ОЗУ. Это выгодно, если swap на диске.\n\nПараметр применяется сразу через sysctl, перезагрузка не нужна. Откат возвращает значение 60.",
        "en": "Swap is a region on disk or in compressed memory where the system stores rarely used data when RAM runs low. How eagerly it does this is controlled by vm.swappiness, a number from 0 to 200.\n\nA high value (say 150) means the system actively moves data to swap. This is good if swap is zram (compressed memory in RAM). A low value (10) means the system tries to keep data in RAM. This is good if swap is on a disk.\n\nThe parameter applies immediately via sysctl, no reboot needed. Rolling back restores the value 60.",
    },
    "zram": {
        "ru": "zram — это сжатая область в оперативной памяти, которую система использует как дополнительную память. Когда ОЗУ не хватает, данные не сбрасываются на диск, а сжимаются в памяти. Скорость обращения к сжатой памяти намного выше, чем к диску, а ресурс SSD не расходуется.\n\nЭта опция создаёт zram через пакет zram-generator. Если у вас мало ОЗУ (4–8 ГБ), система реже будет обращаться к диску.\n\nНе включайте, если у вас много оперативной памяти (16 ГБ и больше). Также опция не имеет смысла, если пакет zram-generator не установлен.\n\nКонфиг создаётся сразу, но устройство zram появится только после перезагрузки.",
        "en": "zram is a compressed area in RAM used by the system as extra memory. When RAM runs low, data is not written to disk — it is compressed in memory. Accessing compressed memory is much faster than accessing the disk, and SSD wear is avoided.\n\nThis option sets up zram via the zram-generator package. If you have little RAM (4–8 GB), the system accesses the disk less often.\n\nDo not enable it if you have plenty of RAM (16 GB or more). Also it makes no sense if zram-generator is not installed.\n\nThe config is created immediately, but the zram device only appears after a reboot.",
    },
    "zswap": {
        "ru": "zswap — это сжатый кэш в оперативной памяти, который стоит перед обычным swap. Когда системе нужно выгрузить страницу памяти, она сначала пробует сжать её и оставить в zswap. Только если zswap переполнен, данные уходят на диск.\n\nЭта опция включает zswap и задаёт компрессор zstd. Если у вас есть swap на диске и вы иногда сталкиваетесь с нехваткой памяти, zswap уменьшит количество обращений к диску.\n\nВАЖНО: zswap требует наличия swap. Если в системе swap отсутствует, параметры не сработают — сжимать некуда. В этом случае твик будет недоступен с причиной «swap не обнаружен».\n\nНе включайте, если у вас уже настроен zram (они делают похожие вещи).\n\nПараметры добавляются в GRUB, поэтому изменения вступают в силу после перезагрузки.",
        "en": "zswap is a compressed cache in RAM that sits in front of regular swap. When the system needs to swap out a page, it first tries to compress it and keep it in zswap. Only when zswap overflows does data go to disk.\n\nThis option enables zswap and sets the zstd compressor. If you have swap on disk and occasionally run out of memory, zswap reduces disk accesses.\n\nIMPORTANT: zswap requires swap to be present. If the system has no swap, the parameters will do nothing — there is nowhere to write. In that case the tweak is disabled with the reason «no swap found».\n\nDo not enable it if you already use zram (they do similar things).\n\nThe parameters are added to GRUB, so changes take effect after a reboot.",
    },
    "thp": {
        "ru": "Память компьютера делится на страницы — небольшие кусочки. Обычно это страницы по 4 КБ. Когда программа работает с большими объёмами данных (игры, обработка фото, базы данных), системе приходится управлять миллионами таких мелких страниц, и это отнимает время.\n\nРежим THP (Transparent Huge Pages) позволяет выдавать память крупными страницами по 2 МБ. Управлять ими проще, поэтому игры и тяжёлые программы работают чуть быстрее. Есть три режима: always — выдавать крупные страницы всем, madvise — только тем программам, которые сами попросят (самый безопасный), never — не использовать вообще.\n\nРекомендуется значение madvise.\n\nПараметр добавляется в GRUB, поэтому изменения вступают в силу после перезагрузки.",
        "en": "Computer memory is divided into pages — small chunks. Normally these are 4 KB pages. When a program works with large amounts of data (games, photo editing, databases), the system has to manage millions of such small pages, and that takes time.\n\nTHP (Transparent Huge Pages) mode lets the system hand out memory in large 2 MB pages. They are easier to manage, so games and heavy apps run slightly faster. There are three modes: always — hand out large pages to everyone, madvise — only to programs that explicitly ask (safest), never — do not use at all.\n\nThe recommended value is madvise.\n\nThe parameter is added to GRUB, so changes take effect after a reboot.",
    },
    "sysctl_cache": {
        "ru": "Ядро Linux держит в оперативной памяти кэш файлов и папок — те данные, которые недавно читались с диска. Когда кэш переполняется, ядро освобождает его часть. Параметр vfs_cache_pressure говорит ядру, насколько агрессивно освобождать кэш.\n\nЗначение по умолчанию — 100. Опция ставит 50, то есть ядро будет освобождать кэш в два раза реже. Файлы и папки, которые вы недавно открывали, останутся в памяти дольше, и следующее открытие пройдёт быстрее.\n\nНе включайте, если у вас мало оперативной памяти (меньше 4 ГБ).\n\nПараметр применяется сразу через sysctl, перезагрузка не нужна.",
        "en": "The Linux kernel keeps a cache of files and folders in RAM — data recently read from disk. When the cache overflows, the kernel frees part of it. The vfs_cache_pressure parameter tells the kernel how aggressively to free the cache.\n\nThe default value is 100. This option sets 50, meaning the kernel will free the cache half as often. Files and folders you recently opened stay in memory longer, and the next open is faster.\n\nDo not enable it if you have little RAM (less than 4 GB).\n\nThe parameter applies immediately via sysctl, no reboot needed.",
    },
    "sysctl_numa": {
        "ru": "NUMA — это архитектура памяти на серверах с несколькими процессорами. На таких системах память физически разделена между процессорами, и доступ к «чужой» памяти медленнее. Ядро Linux автоматически переносит страницы памяти между процессорами.\n\nНа домашнем ПК NUMA нет — процессор один. Но механизм балансировки всё равно работает и создаёт микропаузы в работе, особенно в играх. Отключение этой балансировки убирает паузы.\n\nНе отключайте, если у вас настоящий сервер с NUMA.\n\nПараметр применяется сразу через sysctl, перезагрузка не нужна.",
        "en": "NUMA is a memory architecture on servers with several processors. On such systems, memory is physically split between CPUs, and accessing “foreign” memory is slower. The Linux kernel automatically moves memory pages between CPUs.\n\nA home PC has no NUMA — one CPU. But the balancing mechanism still runs and causes micro-pauses, especially in games. Disabling this balancing removes the pauses.\n\nDo not disable it if you actually run a NUMA server.\n\nThe parameter applies immediately via sysctl, no reboot needed.",
    },
    "reisub": {
        "ru": "Magic SysRq — это набор аварийных команд ядра, которые вызываются сочетанием Alt+PrtSc и определённой буквы. Они работают даже когда система полностью зависла. Самая полезная последовательность — R E I S U B.\n\nКаждая буква означает: R — вернуть управление клавиатуре, E — вежливо завершить процессы, I — убить оставшиеся, S — синхронизировать данные с диском, U — перемонтировать диски в режим только для чтения, B — перезагрузиться. Нажимать их нужно по порядку, с интервалом 1–2 секунды, удерживая Alt+PrtSc.\n\nПосле такой последовательности система перезагружается безопасно, без риска повредить файлы. Не отключайте эту возможность, если у вас бывают зависания.\n\nПараметр применяется сразу через sysctl, перезагрузка не нужна.",
        "en": "Magic SysRq is a set of emergency kernel commands triggered by Alt+PrtSc and a certain letter. They work even when the system is completely frozen. The most useful sequence is R E I S U B.\n\nEach letter means: R — reclaim keyboard, E — politely terminate processes, I — kill the rest, S — sync data to disk, U — remount disks read-only, B — reboot. Press them in order, 1–2 seconds apart, holding Alt+PrtSc.\n\nAfter that sequence the system reboots safely, with no risk of file corruption. Do not disable this feature if your system hangs sometimes.\n\nThe parameter applies immediately via sysctl, no reboot needed.",
    },
    "ntsync": {
        "ru": "ntsync — это новый модуль ядра, который ускоряет синхронизацию потоков в Wine и Proton. Игры под Windows активно используют примитивы синхронизации (мьютексы, события, семафоры), и их реализация в Wine долго была медленной. ntsync делает её значительно быстрее.\n\nРезультат — заметный прирост FPS в некоторых играх, особенно в тех, где много потоков. Если у вас ядро 6.14 или новее (или патченное с ntsync), опция включит модуль и добавит его в автозагрузку.\n\nНе включайте, если у вас ядро старше 6.14 без патча — модуль просто не загрузится.\n\nМодуль загружается сразу, перезагрузка не нужна.",
        "en": "ntsync is a new kernel module that speeds up thread synchronization in Wine and Proton. Windows games heavily use synchronization primitives (mutexes, events, semaphores), and their implementation in Wine was slow for a long time. ntsync makes it significantly faster.\n\nThe result is a noticeable FPS gain in some games, especially those with many threads. If you have kernel 6.14 or newer (or an ntsync-patched one), the option loads the module and adds it to autoload.\n\nDo not enable it if your kernel is older than 6.14 without a patch — the module simply will not load.\n\nThe module loads immediately, no reboot needed.",
    },
    "max_map_count": {
        "ru": "vm.max_map_count — это лимит областей памяти у одного процесса. Каждый раз, когда программа выделяет память через mmap, ядро создаёт «область памяти». Если лимит исчерпан, программа падает с ошибкой «Cannot allocate memory».\n\nНекоторые игры под Proton (Wine/Steam Play) создают очень много областей памяти. Если лимит исчерпан, игра вылетает при запуске. Увеличение лимита решает эту проблему.\n\nРекомендуемое значение — 1048576. Fedora и Arch приняли его как новое значение по умолчанию. Меньшее значение (524288) обычно тоже достаточно. Максимальное (2147483642) используется в SteamOS, но для большинства пользователей оно избыточно.\n\nВАЖНО: этот твик не ускоряет игры и не исправляет обычную нехватку памяти. Он нужен только для совместимости с приложениями, которые создают много mappings.\n\nФайл записывается в /etc/sysctl.d/99-gaming-mmap.conf, применяется сразу.",
        "en": "vm.max_map_count is the limit of memory mappings per process. Every time a program allocates memory via mmap, the kernel creates a “memory area”. If the limit is exhausted, the program crashes with «Cannot allocate memory».\n\nSome Proton games (Wine/Steam Play) create a very large number of memory areas. If the limit is exhausted, the game crashes at startup. Raising the limit solves this problem.\n\nThe recommended value is 1048576. Fedora and Arch adopted it as the new default. A smaller value (524288) is usually enough too. The maximum (2147483642) is used in SteamOS, but for most users it is excessive.\n\nIMPORTANT: this tweak does not speed up games and does not fix ordinary RAM shortage. It is only needed for compatibility with applications that create many mappings.\n\nThe file is written to /etc/sysctl.d/99-gaming-mmap.conf and applies immediately.",
    },
    "ntfs3": {
        "ru": "NTFS — это файловая система Windows. Linux умеет читать и писать на неё двумя способами: через старый медленный драйвер ntfs-3g в пользовательском пространстве и через новый быстрый ntfs3 внутри ядра.\n\nLinux Mint по умолчанию блокирует ntfs3 и использует ntfs-3g. Причина историческая: раньше у ntfs3 были проблемы со стабильностью. Сейчас они исправлены, и ntfs3 работает надёжно. Эта опция снимает блокировку, и NTFS-диски начинают работать заметно быстрее.\n\nВНИМАНИЕ: не включайте, если у вас нет NTFS-дисков. Если у вас есть NTFS-диск с важными данными, сделайте резервную копию перед включением.\n\nПосле снятия блокировки уже подключённые диски продолжат работать со старым драйвером, пока вы их не перемонтируете. Нужна перезагрузка или ручное перемонтирование.",
        "en": "NTFS is the Windows file system. Linux can read and write it two ways: through the old slow ntfs-3g driver in userspace, and through the new fast ntfs3 driver inside the kernel.\n\nLinux Mint blocks ntfs3 by default and uses ntfs-3g. The reason is historical: ntfs3 used to have stability issues. Those are fixed now, and ntfs3 works reliably. This option lifts the block, and NTFS disks start working noticeably faster.\n\nWARNING: do not enable it if you have no NTFS disks. If you have an NTFS disk with important data, make a backup before enabling.\n\nAfter the block is lifted, already mounted disks keep using the old driver until you remount them. A reboot or manual remount is required.",
    },
    "commit": {
        "ru": "Параметр commit=NN заставляет файловую систему реже сбрасывать накопленные данные на диск: не раз в 5 секунд по умолчанию, а раз в NN секунд. Это уменьшает число операций записи и продлевает жизнь SSD.\n\nВАЖНО: параметр понимают ТОЛЬКО файловые системы семейства ext — ext2, ext3, ext4. Для NTFS, FAT32, exFAT, btrfs, xfs, f2fs и других он неизвестен: в лучшем случае ядро его проигнорирует, в худшем — откажется монтировать раздел, и система при загрузке упадёт в emergency-режим.\n\nПоэтому в этом твикере для commit= показываются только разделы с ext2/ext3/ext4.\n\nВНИМАНИЕ: чем больше интервал, тем выше риск потерять последние записанные данные при внезапном отключении питания. Разумные значения — 60–120 секунд.\n\nИзменения записываются в /etc/fstab и вступают в силу после перезагрузки.",
        "en": "The commit=NN parameter makes the file system flush accumulated data to disk less often: not every 5 seconds by default, but every NN seconds. This reduces write operations and extends SSD life.\n\nIMPORTANT: only file systems of the ext family support this — ext2, ext3, ext4. For NTFS, FAT32, exFAT, btrfs, xfs, f2fs and others the parameter is unknown: at best the kernel silently ignores it, at worst it refuses to mount the partition and the system drops into emergency mode on boot.\n\nTherefore in this tweaker only partitions with ext2/ext3/ext4 are shown for commit=.\n\nWARNING: the longer the interval, the higher the risk of losing the latest written data on sudden power loss. Reasonable values are 60–120 seconds.\n\nChanges are written to /etc/fstab and take effect after a reboot.",
    },
    "tmpfs_tmp": {
        "ru": "РАСШИРЕННЫЙ ТВИК. Включайте только если понимаете риск.\n\nМонтирует /tmp как tmpfs — то есть в оперативной памяти. Файлы в /tmp исчезают при перезагрузке, диск не получает постоянные записи.\n\nВНИМАНИЕ — несколько важных предупреждений:\n\n1. ГИБЕРНАЦИЯ. tmpfs использует оперативную память и его страницы могут быть выгружены в swap. Если swap-раздел мал или отсутствует, гибернация может сломаться. У некоторых пользователей система перестаёт выходить из ждущего режима.\n\n2. ПОТЕРЯ ДАННЫХ. Всё, что лежит в /tmp, исчезнет после выключения или перезагрузки. Отдельные приложения могут рассчитывать на сохранение временных файлов в течение работы системы — после перезагрузки они их не найдут.\n\n3. РАЗМЕР. Параметр size=512M — это верхний предел, а не резервирование. Если приложение попытается записать больше, оно упадёт с ошибкой «no space left on device».\n\n4. НЕ ПУТАТЬ С /var/tmp. /var/tmp по определению предназначен для данных, сохраняющихся между перезагрузками. Его в tmpfs монтировать нельзя.\n\nОткат: удалить строку из /etc/fstab, перезагрузиться.",
        "en": "ADVANCED TWEAK. Enable only if you understand the risk.\n\nMounts /tmp as tmpfs — that is, in RAM. Files in /tmp disappear on reboot, the disk gets no constant writes.\n\nWARNING — several important notes:\n\n1. HIBERNATION. tmpfs uses RAM and its pages can be swapped out. If the swap partition is small or absent, hibernation may break. Some users find the system no longer resumes from sleep.\n\n2. DATA LOSS. Everything in /tmp disappears after shutdown or reboot. Some applications may expect temporary files to survive within a session — after reboot they will not find them.\n\n3. SIZE. The size=512M parameter is an upper limit, not a reservation. If an application tries to write more, it crashes with «no space left on device».\n\n4. DO NOT CONFUSE WITH /var/tmp. /var/tmp is by definition for data that survives reboots. Mounting it in tmpfs is wrong.\n\nRollback: remove the line from /etc/fstab, reboot.",
    },
    "aliases": {
        "ru": "В Linux много рутинных действий в терминале: обновление пакетов, очистка кэша, проверка места на диске. Каждый раз набирать длинные команды утомительно. Чтобы этого избежать, в файл .bashrc добавляют короткие функции-обёртки.\n\nЭта опция добавляет в ваш .bashrc готовый набор команд: upd (обновить списки пакетов), upgr (обновить пакеты), update_all (полное обновление системы, включая Flatpak), clean (очистка ненужных пакетов), space (показать свободное место), mem (очистить кэш памяти), fix (починить сломанные пакеты) и другие.\n\nНе включайте, если вы не пользуетесь терминалом.\n\nОпция применяется сразу, но команды появятся только в новых терминалах. Откройте новый терминал или выполните «source ~/.bashrc».",
        "en": "Linux has many routine terminal actions: updating packages, clearing cache, checking disk space. Typing long commands every time is tiring. To avoid this, short wrapper functions are added to the .bashrc file.\n\nThis option adds a ready set of commands to your .bashrc: upd (update package lists), upgr (upgrade packages), update_all (full system update, including Flatpak), clean (remove unnecessary packages), space (show free disk space), mem (clear memory cache), fix (repair broken packages) and others.\n\nDo not enable it if you do not use the terminal.\n\nThe option applies immediately, but the commands only appear in new terminals. Open a new terminal or run «source ~/.bashrc».",
    },
    "autoupdate": {
        "ru": "Обновления системы нужно ставить регулярно — это вопросы безопасности и свежих функций. Вручную это делать лень, поэтому логично поручить задачу systemd. Он умеет запускать команды по расписанию с помощью таймеров.\n\nЭта опция создаёт systemd-таймер, который сам запускает обновление APT и Flatpak в выбранное время. Вы один раз настраиваете расписание (например, каждую субботу в 18:30) и забываете об этом. При включённом Cinnamon дополнительно обновляются апплеты и темы.\n\nПри включении этой опции твикер автоматически глушит apt-daily.timer, apt-daily-upgrade.timer, unattended-upgrades.service и (если есть) mintupdate-automation-upgrade.timer. Это нужно, чтобы обновления не запускались дважды.\n\nВНИМАНИЕ: в Linux Mint есть встроенное автообновление (mintupdate). Твикер глушит только его systemd-таймер, но настройки самого mintupdate остаются как есть. Если вы хотите полностью отдать обновления твикеру — отключите автообновление в mintupdate вручную.\n\nТаймер включается сразу, перезагрузка не нужна.",
        "en": "System updates need to be installed regularly — it is a matter of security and fresh features. Doing it manually is tiring, so it makes sense to delegate the task to systemd. It can run commands on a schedule using timers.\n\nThis option creates a systemd timer that runs APT and Flatpak updates at the chosen time. You configure the schedule once (say, every Saturday at 18:30) and forget about it. On Cinnamon, applets and themes are updated as well.\n\nWhen this option is enabled, the tweaker automatically masks apt-daily.timer, apt-daily-upgrade.timer, unattended-upgrades.service and (if present) mintupdate-automation-upgrade.timer. This is needed so updates do not run twice.\n\nWARNING: Linux Mint has a built-in auto-update (mintupdate). The tweaker masks only its systemd timer, but the mintupdate settings themselves remain untouched. If you want to hand updates fully to the tweaker — disable auto-update inside mintupdate manually.\n\nThe timer starts immediately, no reboot needed.",
    },
    "mount": {
        "ru": "Когда система открывает файл на чтение, она по умолчанию обновляет время последнего доступа к нему. Это нужно для некоторых служебных задач, но на домашнем ПК бесполезно: никто не смотрит на эти метки. При этом каждая запись — это операция на диск, которая тратит ресурс SSD.\n\nОпция noatime отключает обновление времени доступа. Файлы и папки читаются как обычно, но система не делает служебную запись при каждом чтении. Диск меньше работает, SSD живёт дольше, чтение немного быстрее.\n\nПараметры записываются в /etc/fstab, поэтому применяются после перезагрузки.",
        "en": "When the system opens a file for reading, by default it updates the last-access time. This is needed for some service tasks, but on a home PC it is useless: nobody looks at those marks. Meanwhile every write is a disk operation that wears out the SSD.\n\nThe noatime option disables updating the access time. Files and folders are still read normally, but the system does not write to disk on every read. The disk works less, the SSD lives longer, and reads are slightly faster.\n\nThe parameters are written to /etc/fstab and apply after a reboot.",
    },
    "steam": {
        "ru": "Игры Steam под Proton (технология запуска Windows-игр в Linux) хранят свои данные в папке compatdata: настройки, сохранения, установленные библиотеки. По умолчанию эта папка лежит в домашней директории — в ~/.steam/steam/steamapps/compatdata.\n\nЕсли библиотека Steam находится на другом диске, например на NTFS-разделе, игра не может найти данные в домашней папке. Симлинк (ссылка) compatdata внутри библиотеки решает эту проблему: он указывает на домашнюю папку, и игры снова видят свои данные.\n\nОпция работает сразу, перезагрузка не нужна. Если папка compatdata уже существует с данными — она не трогается, чтобы не потерять сохранения. Откат удаляет только созданные симлинки.",
        "en": "Steam games under Proton (technology that runs Windows games on Linux) keep their data in the compatdata folder: settings, saves, installed libraries. By default this folder lives in the home directory — in ~/.steam/steam/steamapps/compatdata.\n\nIf the Steam library is on another disk, for example on an NTFS partition, the game cannot find the data in the home folder. A compatdata symlink (link) inside the library solves this: it points to the home folder, and games see their data again.\n\nThe option works immediately, no reboot needed. If the compatdata folder already exists with data, it is left untouched so saves are not lost. Rolling back removes only the created symlinks.",
    },
}

# ─── Строки интерфейса (RU/EN) ──────────────────────────────────────────────
STR = {
    "ru": {
        "tab_tune": "Тюнинг", "tab_serv": "Службы", "tab_stat": "Статус",
        "tab_apps": "Приложения",
        "btn_apply": "Применить выбранное", "btn_rollback": "Откатить выбранное",
        "btn_selall": "Выбрать все", "btn_selnone": "Снять выделение",
        "btn_about": "О твикере", "btn_close": "Закрыть",
        "theme_dark": "Тёмная тема", "theme_light": "Светлая тема",
        "lbl_dry": "Сухой прогон", "lbl_terminal": "Терминальный вывод:",
        "lbl_search": "Поиск:", "btn_search_clear": "Сбросить",
        "lbl_show_only_available": "Только доступное",
        "search_no_results": "Ничего не найдено по запросу «%s».",
        "lbl_group": "Группа:", "lbl_value": "Значение:", "lbl_schedule": "Расписание:",
        "lbl_mode": "Режим:",
        "ready": "Готово", "running": "Выполнение...", "done": "Готово",
        "applied_yes": "✓ применено", "applied_no": "не применено",
        "applied_manual": "применено (изменён вручную)",
        "btn_file": "файл", "btn_q": "?",
        "btn_check_status": "проверить",
        "btn_remove_zfs": "Удалить пакеты (осторожно)",
        "btn_remove_zfs_unavailable": "Удалить пакеты (недоступно)",
        "menu_copy": "Копировать", "menu_copy_all": "Копировать всё",
        "menu_select_all": "Выделить всё",
        "svc_name": "Служба", "svc_state": "Состояние", "svc_run": "Запуск",
        "svc_desc": "Описание", "svc_help": "?",
        "svc_hint": "Клик по первой колонке — отметить службу; клик по заголовку — сортировка; «?» — подробности.",
        "svc_on": "работает", "svc_onoff": "не запущена", "svc_off": "остановлена",
        "svc_masked": "заблокирована", "svc_na": "нет в системе",
        "run_yes": "работает", "run_no": "остановлена",
        "svc_on_sel": "Включить выбранные", "svc_off_sel": "Отключить выбранные",
        "svc_col_sel": "✓",
        "sort_asc": "▲", "sort_desc": "▼",
        "svc_hdr_name": "Служба", "svc_hdr_state": "Состояние",
        "svc_hdr_desc": "Описание",
        "stat_refresh": "Обновить статус",
        "st_hw": "ИНФОРМАЦИЯ О СИСТЕМЕ", "st_parts": "РАЗДЕЛЫ СИСТЕМЫ",
        "st_tweaks": "ТВИКИ", "st_services": "СЛУЖБЫ", "st_kernel": "ПАРАМЕТРЫ ЯДРА",
        "st_timer": "Таймер автообновлений",
        "st_enabled": "включён", "st_disabled": "отключён",
        "st_masked": "заблокирован", "st_notfound": "не найден",
        "part_dev": "Устройство", "part_mount": "Точка монтирования",
        "part_fs": "ФС", "part_total": "Всего", "part_free": "Свободно",
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
        "mmc_value_label": "Значение:",
        "tmpfs_size_label": "Размер:",
        "cur_value": "сейчас: %s",
        "nmi_now_active": "сейчас: активен",
        "nmi_now_off": "сейчас: отключён",
        "commit_not_set": "—",
        "commit_default_hint": "по умолчанию: 5 сек",
        "tmpfs_already": "(/tmp уже в tmpfs)",
        "journald_volatile": "ОЗУ (volatile)",
        "journald_persistent": "диск (persistent)",
        "journald_none": "выключено",
        "journald_auto": "auto (по умолчанию)",
        "kern_sw": "как часто данные уходят в подкачку",
        "kern_vfs": "сколько кэша файлов держится в памяти",
        "kern_numa": "перемещение памяти между ядрами",
        "kern_thp": "крупные блоки памяти",
        "kern_bbr": "ускорение сети на слабых каналах",
        "thp_cur": "сейчас: %s",
        "thp_val_always": "всем подряд", "thp_val_madvise": "по запросу",
        "thp_val_never": "выключено",
        "kn_hdr_param": "Параметр", "kn_hdr_val": "Значение",
        "kn_hdr_desc": "Описание", "kn_hdr_status": "Статус",
        "tw_name": "Твик", "kn_param": "Параметр", "kn_val": "Значение",
        "sudo_title": "sudo", "sudo_prompt": "Пароль sudo (попытка %d из 3):",
        "sudo_wrong": "Неверный пароль или нет прав sudo.",
        "autoupdate_warn": "Включено автообновление по расписанию. Твикер автоматически отключит apt-daily, apt-daily-upgrade и unattended-upgrades, чтобы обновления не выполнялись дважды. Встроенное автообновление Mint (mintupdate) останется как есть — отключите его вручную, если не хотите дублирования.",
        "shutdown_timeout_warn": "ВНИМАНИЕ: этот твик сокращает время ожидания закрытия приложений при выключении ПК с 90 до 8 секунд (по умолчанию).\n\nЕсли в момент выключения приложение сохраняло данные (база данных, торрент, редактор), его могут убить до завершения записи.\n\nДля обычного домашнего ПК риск минимальный. Для систем с базами данных или активной записью — не включайте.\n\nИзменения вступают в силу после перезагрузки.",
        "viewer": "Просмотр файла", "viewer_ext": "Открыть во внешнем редакторе",
        "about_title": "О твикере",
        "about_purpose": "Графическая оболочка тюнинга для Linux Mint / Ubuntu / Debian и других systemd-дистрибутивов: твики производительности, логов, дисков, сети и игр с откатом и бэкапами.",
        "about_author": "Автор", "about_author_name": "Дмитрий Свистунов",
        "about_ver": "Версия",
        "about_license": "Лицензия",
        "about_disclaimer": "ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ\n\nТвикер изменяет системные файлы (GRUB, fstab, sysctl, systemd-юниты, конфиги приложений) и может удалять пакеты. Все изменения вы делаете на свой страх и риск. Перед применением твиков убедитесь, что у вас есть резервная копия важных данных и загрузочная флешка на случай проблем с загрузкой. Автор не несёт ответственности за потерю данных, отказ загрузки или нестабильную работу системы. Бэкапы изменённых файлов сохраняются в ~/system-tuneup-backups/.",
        "zfs_remove_title": "Удаление пакетов ZFS",
        "zfs_remove_body": "Твикер проверил: ZFS-пулов нет, ZFS-монтирований нет, записей в /etc/fstab и /etc/crypttab нет.\n\nЕсли вы устанавливали ZFS вручную и используете его вне стандартных мест — удаление приведёт к потере доступа к данным.\n\nОтмена возможна только через «sudo apt install zfsutils-linux», при этом прежнее состояние служб не восстановится.\n\nУдалить пакеты zfsutils-linux и zfs-zed?",
        "disabled_reason": "недоступно: %s",
        "msg_run": "Скрипт уже запущен. Дождитесь завершения.",
        "msg_noopt": "Отметьте хотя бы одну опцию.",
        "msg_sel": "Сначала отметьте службы в первой колонке.",
        "msg_nofile": "Файл ещё не существует. Пути, где опция вносит изменения:",
        "msg_close": "Прервать выполнение и закрыть?",
        "msg_running_title": "Уже запущено",
        "msg_running_text": "Linux Tweaker уже запущен.",
        "result_ok": "Готово: %d применено, %d пропущено, %d ошибок",
        "reason_raid": "у вас есть RAID",
        "reason_itco_not_intel": "не Intel-чипсет",
        "reason_itco_no_module": "модуль iTCO_wdt не поддерживается ядром",
        "reason_itco_watchdog_off": "NMI watchdog уже отключён",
        "reason_itco_grub_missing": "сначала примените nmi_watchdog=0",
        "reason_zfs_not_installed": "пакеты ZFS не установлены",
        "reason_amd_only": "только для AMD",
        "reason_nvidia_only": "только для NVIDIA",
        "reason_no_swap": "swap не обнаружен",
        "reason_no_zram": "нет zram-generator",
        "reason_mint_only": "только для Linux Mint",
        "reason_pipewire_inactive": "PipeWire не используется",
        "reason_no_ntfs": "нет NTFS-разделов",
        "apps_search": "Поиск:",
        "apps_refresh": "Обновить",
        "apps_clear": "Снять выделение",
        "apps_remove": "Удалить выбранное",
        "apps_empty": "Из списка ничего не установлено.",
        "apps_unsupported": "Функция недоступна в этом дистрибутиве.\nУдаление пакетов поддерживается только в системах на базе Debian, Ubuntu или Linux Mint.",
        "apps_no_list": "Список пакетов не найден (tweaker_packages.py отсутствует).",
        "apps_selected": "Выбрано: %d пакетов, ~%s",
        "apps_selected_none": "Ничего не выбрано",
        "apps_confirm_title": "Удаление пакетов",
        "apps_confirm_will_remove": "Будут удалены:",
        "apps_confirm_deps": "Вместе с ними apt хочет удалить (зависимости):",
        "apps_confirm_size": "Будет освобождено примерно:",
        "apps_confirm_system_warn": "ВНИМАНИЕ: apt также хочет удалить системные пакеты:",
        "apps_confirm_system_hint": "Это может сломать систему. Продолжайте, только если понимаете, что делаете.",
        "apps_confirm_no_rollback": "Отмена невозможна. Конфиги будут стёрты.",
        "apps_confirm_btn": "Удалить",
        "apps_cancel": "Отмена",
        "apps_done": "Удалено %d пакетов, освобождено ~%s",
        "apps_done_dry": "[Сухой прогон] Будет удалено %d пакетов",
        "apps_failed": "Не удалось удалить пакеты.",
        "apps_installed": "установлен",
        "apps_careful_mark": "⚠",
    },
    "en": {
        "tab_tune": "Tuning", "tab_serv": "Services", "tab_stat": "Status",
        "tab_apps": "Applications",
        "btn_apply": "Apply selected", "btn_rollback": "Rollback selected",
        "btn_selall": "Select all", "btn_selnone": "Deselect",
        "btn_about": "About", "btn_close": "Close",
        "theme_dark": "Dark theme", "theme_light": "Light theme",
        "lbl_dry": "Dry run", "lbl_terminal": "Terminal output:",
        "lbl_search": "Search:", "btn_search_clear": "Reset",
        "lbl_show_only_available": "Available only",
        "search_no_results": "Nothing found for query “%s”.",
        "lbl_group": "Group:", "lbl_value": "Value:", "lbl_schedule": "Schedule:",
        "lbl_mode": "Mode:",
        "ready": "Ready", "running": "Running...", "done": "Done",
        "applied_yes": "✓ applied", "applied_no": "not applied",
        "applied_manual": "applied (modified manually)",
        "btn_file": "file", "btn_q": "?",
        "btn_check_status": "check",
        "btn_remove_zfs": "Remove packages (careful)",
        "btn_remove_zfs_unavailable": "Remove packages (unavailable)",
        "menu_copy": "Copy", "menu_copy_all": "Copy all",
        "menu_select_all": "Select all",
        "svc_name": "Service", "svc_state": "State", "svc_run": "Running",
        "svc_desc": "Description", "svc_help": "?",
        "svc_hint": "Click the first column to mark a service; click a header to sort; “?” opens details.",
        "svc_on": "running", "svc_onoff": "not running", "svc_off": "stopped",
        "svc_masked": "blocked", "svc_na": "not installed",
        "run_yes": "running", "run_no": "stopped",
        "svc_on_sel": "Enable selected", "svc_off_sel": "Disable selected",
        "svc_col_sel": "✓",
        "sort_asc": "▲", "sort_desc": "▼",
        "svc_hdr_name": "Service", "svc_hdr_state": "State",
        "svc_hdr_desc": "Description",
        "stat_refresh": "Refresh status",
        "st_hw": "SYSTEM INFORMATION", "st_parts": "SYSTEM PARTITIONS",
        "st_tweaks": "TWEAKS", "st_services": "SERVICES", "st_kernel": "KERNEL PARAMETERS",
        "st_timer": "Auto-update timer",
        "st_enabled": "enabled", "st_disabled": "disabled",
        "st_masked": "blocked", "st_notfound": "not found",
        "part_dev": "Device", "part_mount": "Mount point",
        "part_fs": "FS", "part_total": "Total", "part_free": "Free",
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
        "mmc_value_label": "Value:",
        "tmpfs_size_label": "Size:",
        "cur_value": "now: %s",
        "nmi_now_active": "now: active",
        "nmi_now_off": "now: off",
        "commit_not_set": "—",
        "commit_default_hint": "default: 5 sec",
        "tmpfs_already": "(/tmp already in tmpfs)",
        "journald_volatile": "RAM (volatile)",
        "journald_persistent": "disk (persistent)",
        "journald_none": "disabled",
        "journald_auto": "auto (default)",
        "kern_sw": "how often data goes to swap",
        "kern_vfs": "how much file cache stays in RAM",
        "kern_numa": "memory moving between CPU cores",
        "kern_thp": "large memory blocks",
        "kern_bbr": "faster network on unstable links",
        "thp_cur": "now: %s",
        "thp_val_always": "always on", "thp_val_madvise": "on request",
        "thp_val_never": "off",
        "kn_hdr_param": "Parameter", "kn_hdr_val": "Value",
        "kn_hdr_desc": "Description", "kn_hdr_status": "Status",
        "tw_name": "Tweak", "kn_param": "Parameter", "kn_val": "Value",
        "sudo_title": "sudo", "sudo_prompt": "sudo password (attempt %d of 3):",
        "sudo_wrong": "Wrong password or no sudo rights.",
        "autoupdate_warn": "Scheduled auto-update enabled. The tweaker will automatically mask apt-daily, apt-daily-upgrade and unattended-upgrades so updates do not run twice. Mint's built-in auto-update (mintupdate) is left as is — disable it manually if you do not want duplicates.",
        "shutdown_timeout_warn": "WARNING: this tweak cuts the app-close timeout at shutdown from 90 to 8 seconds (default).\n\nIf an app was saving data at shutdown (database, torrent, editor), it may be killed before finishing the write.\n\nFor a normal home PC the risk is minimal. For systems with databases or active writes — do not enable.\n\nChanges take effect after a reboot.",
        "viewer": "File viewer", "viewer_ext": "Open in external editor",
        "about_title": "About",
        "about_purpose": "A graphical tuning shell for Linux Mint / Ubuntu / Debian and other systemd distributions: performance, logs, disk, network and gaming tweaks with rollback and backups.",
        "about_author": "Author", "about_author_name": "Dmitry Svistunov",
        "about_ver": "Version",
        "about_license": "License",
        "about_disclaimer": "DISCLAIMER\n\nThis tweaker modifies system files (GRUB, fstab, sysctl, systemd units, application configs) and can remove packages. You use it at your own risk. Before applying tweaks, make sure you have a backup of important data and a bootable USB stick in case of boot problems. The author is not responsible for data loss, boot failure or system instability. Backups of modified files are stored in ~/system-tuneup-backups/.",
        "zfs_remove_title": "ZFS package removal",
        "zfs_remove_body": "The tweaker checked: no ZFS pools, no ZFS mounts, no entries in /etc/fstab or /etc/crypttab.\n\nIf you installed ZFS manually and use it outside standard locations, removal will cut off access to your data.\n\nRollback is possible only via «sudo apt install zfsutils-linux», and the previous state of the services will not be restored.\n\nRemove packages zfsutils-linux and zfs-zed?",
        "disabled_reason": "unavailable: %s",
        "msg_run": "A job is already running. Wait for it to finish.",
        "msg_noopt": "Tick at least one option.",
        "msg_sel": "Tick services in the first column first.",
        "msg_nofile": "This file appears after applying the option. Paths the option modifies:",
        "msg_close": "Interrupt the job and close?",
        "msg_running_title": "Already running",
        "msg_running_text": "Linux Tweaker is already running.",
        "result_ok": "Done: %d applied, %d skipped, %d failed",
        "reason_raid": "RAID detected",
        "reason_itco_not_intel": "not an Intel system",
        "reason_itco_no_module": "iTCO_wdt module not available",
        "reason_itco_watchdog_off": "NMI watchdog already disabled",
        "reason_itco_grub_missing": "apply nmi_watchdog=0 first",
        "reason_zfs_not_installed": "ZFS packages not installed",
        "reason_amd_only": "AMD only",
        "reason_nvidia_only": "NVIDIA only",
        "reason_no_swap": "no swap found",
        "reason_no_zram": "zram-generator not installed",
        "reason_mint_only": "Linux Mint only",
        "reason_pipewire_inactive": "PipeWire is not in use",
        "reason_no_ntfs": "no NTFS partitions",
        "apps_search": "Search:",
        "apps_refresh": "Refresh",
        "apps_clear": "Deselect",
        "apps_remove": "Remove selected",
        "apps_empty": "Nothing from the list is installed.",
        "apps_unsupported": "This feature is not available on this distribution.\nPackage removal is only supported on Debian, Ubuntu or Linux Mint based systems.",
        "apps_no_list": "Package list not found (tweaker_packages.py is missing).",
        "apps_selected": "Selected: %d packages, ~%s",
        "apps_selected_none": "Nothing selected",
        "apps_confirm_title": "Package removal",
        "apps_confirm_will_remove": "The following will be removed:",
        "apps_confirm_deps": "Together with them apt wants to remove (dependencies):",
        "apps_confirm_size": "About to free:",
        "apps_confirm_system_warn": "WARNING: apt also wants to remove system packages:",
        "apps_confirm_system_hint": "This may break the system. Continue only if you understand what you are doing.",
        "apps_confirm_no_rollback": "This cannot be undone. Configs will be deleted.",
        "apps_confirm_btn": "Remove",
        "apps_cancel": "Cancel",
        "apps_done": "Removed %d packages, freed ~%s",
        "apps_done_dry": "[Dry run] Would remove %d packages",
        "apps_failed": "Failed to remove packages.",
        "apps_installed": "installed",
        "apps_careful_mark": "⚠",
    },
}

# ─── Список приложений (импорт из корневого tweaker_packages.py) ────────────
# tweaker_packages.py лежит рядом с linux_tweaker.py (не внутри пакета).
# Импортируем его с fallback'ом — если файла нет, вкладка «Приложения» пуста.
try:
    from tweaker_packages import REMOVABLE_PACKAGES
except ImportError:
    try:
        import sys
        import os as _os
        _here = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        if _here not in sys.path:
            sys.path.insert(0, _here)
        from tweaker_packages import REMOVABLE_PACKAGES
    except ImportError:
        REMOVABLE_PACKAGES = {}
