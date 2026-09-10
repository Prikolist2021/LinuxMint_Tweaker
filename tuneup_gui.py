#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Tuneup GUI v0.5
Графическая оболочка тюнинга Linux Mint / Ubuntu / Debian.
RU/EN, темы, детект применённых настроек, откат, бэкапы,
mount-опции noatime/nodiratime, симлинки compatdata для Steam (только NTFS),
встроенный просмотрщик файлов, контекстное меню копирования.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog, filedialog
import subprocess, os, sys, threading, queue, re, pwd, grp, time, shutil, glob

APP_VERSION = "0.5"

THEMES = {
    "light": {"bg": "#f5f5f5", "fg": "#1e1e1e", "green": "#2e7d32", "yellow": "#b26a00",
              "red": "#c62828", "blue": "#1565c0", "orange": "#e65100", "gray": "#616161",
              "terminal_bg": "#ffffff", "terminal_fg": "#1e1e1e", "entry_bg": "#ffffff",
              "entry_fg": "#1e1e1e", "select_color": "#e0e0e0", "button_bg": "#e0e0e0",
              "button_fg": "#1e1e1e", "accent_bg": "#4caf50", "accent_fg": "#ffffff",
              "tree_bg": "#ffffff", "tree_fg": "#1e1e1e", "tree_heading_bg": "#e0e0e0",
              "tree_heading_fg": "#1e1e1e", "notebook_tab_bg": "#e0e0e0",
              "notebook_tab_selected": "#ffffff", "scrollbar_trough": "#e8e8e8",
              "scrollbar_slider": "#9e9e9e"},
    "dark": {"bg": "#1e1e1e", "fg": "#d4d4d4", "green": "#4ec9b0", "yellow": "#d7ba7d",
             "red": "#f44747", "blue": "#569cd6", "orange": "#ce9178", "gray": "#9a9a9a",
             "terminal_bg": "#0c0c0c", "terminal_fg": "#d4d4d4", "entry_bg": "#333333",
             "entry_fg": "#d4d4d4", "select_color": "#333333", "button_bg": "#444444",
             "button_fg": "#d4d4d4", "accent_bg": "#4ec9b0", "accent_fg": "#1e1e1e",
             "tree_bg": "#252525", "tree_fg": "#d4d4d4", "tree_heading_bg": "#333333",
             "tree_heading_fg": "#ffffff", "notebook_tab_bg": "#333333",
             "notebook_tab_selected": "#555555", "scrollbar_trough": "#2d2d2d",
             "scrollbar_slider": "#6a6a6a"},
}

OPTIONS_META = {
    "rsyslog": {
        "ru": ("Отключить rsyslog", "Система постоянно пишет подробные журналы на диск. На домашнем ПК это лишняя нагрузка: отключение экономит ресурс SSD и слегка ускоряет работу. Краткие журналы при этом остаются в памяти (см. следующий пункт).", "Логи системы", "запись подробных журналов rsyslog на диск"),
        "en": ("Disable rsyslog", "The system constantly writes detailed logs to disk. On a home PC this is unnecessary wear: disabling saves SSD life and slightly speeds things up. Short logs remain in RAM (see next item).", "System logs", "detailed rsyslog logging to disk")},
    "journald": {
        "ru": ("Логи в ОЗУ (journald)", "Переносит журналы systemd в оперативную память и ограничивает их 50 МБ. Диски не изнашиваются, старые логи не накапливаются годами.", "Логи системы", "хранение журналов systemd в ОЗУ (50 МБ)"),
        "en": ("Logs in RAM (journald)", "Moves systemd journals to RAM and caps them at 50 MB. No disk wear, old logs do not pile up for years.", "System logs", "systemd journals stored in RAM (50 MB)")},
    "audit": {
        "ru": ("audit=0 (GRUB)", "Отключает встроенный аудит ядра: система перестаёт протоколировать каждый системный вызов. Меньше накладных расходов — чуть быстрее загрузка и работа.", "Ядро и загрузка", "аудит ядра (audit=0)"),
        "en": ("audit=0 (GRUB)", "Disables kernel auditing: the kernel stops logging every syscall. Less overhead — slightly faster boot and runtime.", "Kernel & boot", "kernel auditing (audit=0)")},
    "raid": {
        "ru": ("raid=noautodetect (GRUB)", "Если у вас нет RAID-массива, при каждой загрузке система тратит время на его поиск. Параметр отключает этот поиск — загрузка быстрее.", "Ядро и загрузка", "поиск RAID при загрузке"),
        "en": ("raid=noautodetect (GRUB)", "If you have no RAID array, the system wastes boot time probing for one. This option skips the probe — faster boot.", "Kernel & boot", "RAID probing at boot")},
    "corectrl": {
        "ru": ("CoreCtrl (Polkit)", "Правило Polkit для программы CoreCtrl: позволяет управлять частотами и вентиляторами видеокарты AMD без ввода пароля. В поле указывается группа пользователей, которым это разрешено (по умолчанию — ваша).", "Видеокарта и графика", "polkit-правило для CoreCtrl"),
        "en": ("CoreCtrl (Polkit)", "Polkit rule for CoreCtrl: allows controlling AMD GPU clocks and fans without a password. The field sets the user group allowed to do so (defaults to yours).", "GPU & graphics", "Polkit rule for CoreCtrl")},
    "ppfeaturemask": {
        "ru": ("amdgpu.ppfeaturemask", "Разблокирует скрытые возможности управления питанием AMD GPU (нужно на старых ядрах). Открывает CoreCtrl полный контроль над частотами.", "Видеокарта и графика", "разблокировка управления питанием AMD"),
        "en": ("amdgpu.ppfeaturemask", "Unlocks hidden AMD GPU power-management features (needed on older kernels). Gives CoreCtrl full clock control.", "GPU & graphics", "AMD power management unlock")},
    "vrr": {
        "ru": ("VRR/FreeSync", "Включает переменную частоту обновления (FreeSync) для AMD: картинка в играх без разрывов при плавающем FPS. Работает в X11 с драйвером amdgpu.", "Видеокарта и графика", "VRR/FreeSync (X11, amdgpu)"),
        "en": ("VRR/FreeSync", "Enables variable refresh rate (FreeSync) on AMD: tear-free gaming at fluctuating FPS. Works in X11 with the amdgpu driver.", "GPU & graphics", "VRR/FreeSync (X11, amdgpu)")},
    "radv": {
        "ru": ("RADV_PERFTEST=sam", "Включает в драйвере RADV оптимизацию SAM / Resizable BAR: процессор получает доступ ко всей видеопамяти сразу — небольшой прирост FPS в играх.", "Видеокарта и графика", "SAM / Resizable BAR в RADV"),
        "en": ("RADV_PERFTEST=sam", "Enables SAM / Resizable BAR optimization in the RADV driver: the CPU accesses all VRAM at once — a small FPS gain in games.", "GPU & graphics", "SAM / Resizable BAR in RADV")},
    "mesa": {
        "ru": ("MESA_SHADER_CACHE=4G", "Увеличивает кэш скомпилированных шейдеров до 4 ГБ. Игры и GL-приложения реже перекомпилируют шейдеры — меньше подтормаживаний в первые минуты игры.", "Видеокарта и графика", "кэш шейдеров MESA 4 ГБ"),
        "en": ("MESA_SHADER_CACHE=4G", "Raises the compiled shader cache to 4 GB. Games and GL apps recompile shaders less often — fewer hitches in the first minutes of play.", "GPU & graphics", "MESA shader cache 4 GB")},
    "pipewire": {
        "ru": ("PipeWire (звук)", "Увеличивает буферы (кванты) звукового сервера PipeWire. Убирает треск, щелчки и прерывистый звук в наушниках и колонках.", "Звук", "увеличенные буферы PipeWire"),
        "en": ("PipeWire (sound)", "Increases PipeWire sound-server quanta. Removes crackling, pops and stuttering audio in headphones and speakers.", "Sound", "increased PipeWire quanta")},
    "swap": {
        "ru": ("Тюнинг swap", "Настраивает vm.swappiness — насколько охотно система сбрасывает память в swap. Для сжатого zram выгодно 150, для диска/SSD — 10: меньше лишних обращений к диску.", "Память и swap", "настройка vm.swappiness"),
        "en": ("Swap tuning", "Sets vm.swappiness — how eagerly memory is pushed to swap. 150 suits compressed zram, 10 suits disk/SSD: fewer pointless disk accesses.", "Memory & swap", "vm.swappiness tuning")},
    "sysctl": {
        "ru": ("Тюнинг sysctl", "vfs_cache_pressure=50 — система дольше держит кэш каталогов в памяти (быстрее работа с файлами). numa_balancing=0 — отключает лишнюю миграцию памяти между ядрами (полезно играм).", "Ядро и загрузка", "sysctl-тюнинг (vfs_cache, numa)"),
        "en": ("sysctl tuning", "vfs_cache_pressure=50 — directory cache stays in RAM longer (faster file access). numa_balancing=0 — disables needless memory migration between cores (good for games).", "Kernel & boot", "sysctl tuning (vfs_cache, numa)")},
    "ntsync": {
        "ru": ("ntsync (модуль ядра)", "Включает модуль ntsync — новый ускоритель синхронизации для Wine/Proton. Заметный прирост FPS в части игр. Требуется ядро 6.14+ или с патчем ntsync.", "Игры и совместимость", "модуль ядра ntsync"),
        "en": ("ntsync (kernel module)", "Enables the ntsync module — a new synchronization accelerator for Wine/Proton. Noticeable FPS gain in some games. Needs kernel 6.14+ or an ntsync-patched one.", "Gaming & compatibility", "ntsync kernel module")},
    "ntfs3": {
        "ru": ("ntfs3 драйвер", "Включает быстрый встроенный драйвер ntfs3 для NTFS-дисков вместо медленного ntfs-3g. Linux Mint по умолчанию его блокирует — опция снимает блокировку.", "Диски и файловые системы", "быстрый драйвер ntfs3"),
        "en": ("ntfs3 driver", "Enables the fast in-kernel ntfs3 driver for NTFS disks instead of slow ntfs-3g. Linux Mint blocks it by default — this option lifts the block.", "Drives & filesystems", "fast ntfs3 driver")},
    "aliases": {
        "ru": ("Команды в .bashrc", "Добавляет удобные команды терминала: upd, upgr, update_all (обновление всей системы), clean (очистка), space (место на диске), mem (очистка памяти) и другие.", "Удобство", "команды upd/upgr/clean в .bashrc"),
        "en": ("Commands in .bashrc", "Adds handy shell commands: upd, upgr, update_all (full system update), clean, space (disk free), mem (memory clean) and more.", "Convenience", "upd/upgr/clean commands in .bashrc")},
    "autoupdate": {
        "ru": ("Автообновления", "Создаёт systemd-таймер, который по выбранному расписанию сам обновляет APT-пакеты и Flatpak без вашего участия.", "Обновления", "systemd-таймер автообновлений"),
        "en": ("Auto-updates", "Creates a systemd timer that updates APT packages and Flatpak on the chosen schedule without you.", "Updates", "systemd auto-update timer")},
}

CAT_ORDER = {
    "ru": ["Видеокарта и графика", "Ядро и загрузка", "Логи системы", "Звук",
           "Память и swap", "Диски и файловые системы", "Игры и совместимость",
           "Удобство", "Обновления"],
    "en": ["GPU & graphics", "Kernel & boot", "System logs", "Sound",
           "Memory & swap", "Drives & filesystems", "Gaming & compatibility",
           "Convenience", "Updates"],
}

SERVICES_META = {
    "avahi-daemon.service": {"ru": "Сетевое обнаружение устройств (принтеры, ТВ, Chromecast). На домашнем ПК без сетевой печати почти не нужно.", "en": "Network device discovery (printers, TVs, Chromecast). Rarely needed on a home PC without network printing."},
    "avahi-daemon.socket": {"ru": "Сокет-активатор Avahi: будит службу при обращении из сети. Отключается вместе со службой.", "en": "Avahi socket activator: wakes the service on network requests. Disabled together with the service."},
    "cups-browsed.service": {"ru": "Автоматический поиск сетевых принтеров. Если у вас нет сетевого принтера — служба простаивает зря.", "en": "Automatic network printer discovery. Useless if you have no network printer."},
    "ModemManager.service": {"ru": "Управление USB-модемами (3G/4G). Без модема не нужен; иногда мешает serial-устройствам и Arduino.", "en": "USB modem (3G/4G) management. Useless without a modem; can interfere with serial devices and Arduino."},
    "openvpn.service": {"ru": "Встроенный VPN-сервер. Если не поднимаете собственный VPN — не нужен.", "en": "Built-in VPN server. Useless unless you run your own VPN."},
    "lvm2-monitor.service": {"ru": "Мониторинг LVM-томов. При обычной установке без LVM не нужен.", "en": "LVM volume monitoring. Useless on a plain install without LVM."},
    "switcheroo-control.service": {"ru": "Переключение встроенной и дискретной графики на ноутбуках. На настольном ПК не нужен.", "en": "Switching integrated/discrete graphics on laptops. Useless on a desktop."},
    "touchegg.service": {"ru": "Распознавание мультитач-жестов тачпада. На настольном ПК без тачскрина не нужен.", "en": "Multitouch gesture recognition. Useless on a desktop without a touchscreen."},
    "zfs-zed.service": {"ru": "Мониторинг ZFS-пулов (дисковые массивы ZFS). Без ZFS не нужен.", "en": "ZFS pool monitoring. Useless without ZFS."},
    "kerneloops.service": {"ru": "Отправка разработчикам отчётов о сбоях ядра. На домашнем ПК не нужна.", "en": "Sends kernel crash reports to developers. Unneeded on a home PC."},
}
SERVICES_ORDER = list(SERVICES_META.keys())

OPTION_FILES = {
    "rsyslog": ["/etc/systemd/system/rsyslog.service",
                "/lib/systemd/system/rsyslog.service"],
    "journald": ["/etc/systemd/journald.conf"],
    "audit": ["/etc/default/grub"],
    "raid": ["/etc/default/grub"],
    "corectrl": ["/etc/polkit-1/rules.d/90-corectrl.rules",
                 "/etc/polkit-1/localauthority/50-local.d/90-corectrl.pkla"],
    "ppfeaturemask": ["/etc/default/grub"],
    "vrr": ["/etc/X11/xorg.conf.d/20-amdgpu.conf"],
    "radv": ["/etc/environment"],
    "mesa": ["/etc/environment"],
    "pipewire": ["{home}/.config/pipewire/pipewire.conf.d/10-sound.conf"],
    "swap": ["/etc/sysctl.d/99-gaming-swap.conf"],
    "sysctl": ["/etc/sysctl.d/99-gaming-sysctl.conf"],
    "ntsync": ["/etc/modules-load.d/ntsync.conf"],
    "ntfs3": ["/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"],
    "aliases": ["{home}/.bashrc"],
    "autoupdate": ["/etc/systemd/system/biweekly-upgrade.timer",
                   "/etc/systemd/system/biweekly-upgrade.service"],
}

STR = {
    "ru": {
        "tab_tune": " Тюнинг ", "tab_serv": " Службы ", "tab_stat": " Статус ",
        "btn_apply_sel": "Применить выбранное", "btn_rollback": "Откатить выбранное",
        "btn_selall_opt": "Выбрать все", "btn_selnone": "Снять выделение",
        "btn_export": "Экспорт", "btn_help": "О твикере",
        "theme_dark": "Тёмная тема", "theme_light": "Светлая тема",
        "lbl_dry": "Сухой прогон", "lbl_terminal": "Терминальный вывод:",
        "lbl_group": "Группа:", "lbl_value": "Значение:", "lbl_schedule": "Расписание:",
        "status_ready": "Готово", "status_running": "Выполнение...",
        "status_done": "Готово", "status_error": "Ошибка",
        "applied_yes": "✓ применено", "applied_no": "не применено",
        "btn_open_file": "файл",
        "menu_copy": "Копировать", "menu_copy_all": "Копировать всё",
        "menu_select_all": "Выделить всё",
        "svc_col_name": "Служба", "svc_col_en": "Состояние", "svc_col_act": "Запуск",
        "svc_col_desc": "Описание и зачем отключать",
        "svc_on": "[ON] работает", "svc_onoff": "[ON/off] включена, не запущена",
        "svc_off": "[OFF] отключена", "svc_masked": "[MASKED] заблокирована",
        "svc_na": "[N/A] нет в системе", "run_yes": "работает", "run_no": "остановлена",
        "svc_count": "Служб: {n}",
        "svc_detail_hint": "Выберите строку, чтобы увидеть полное описание службы.",
        "svc_on_sel": "Включить выбранные", "svc_off_sel": "Отключить выбранные",
        "stat_refresh": "Обновить статус",
        "st_hw": "=== ИНФОРМАЦИЯ О СИСТЕМЕ ===",
        "st_tweaks": "=== ТВИКИ ===",
        "st_services": "=== СЛУЖБЫ ===", "st_kernel": "=== ЯДРО (текущие значения) ===",
        "st_timer": "Таймер автообновлений",
        "st_os_lbl": "ОС", "st_gpu_lbl": "Видеокарта", "st_screen_lbl": "Разрешение экрана",
        "st_swap_lbl": "Файл подкачки", "st_kernel_lbl": "Ядро",
        "st_de_lbl": "Графическая оболочка",
        "st_ram_lbl": "ОЗУ", "st_disk_lbl": "Диск /", "st_disk_home": "Диск /home",
        "gb": "ГБ", "free_word": "свободно",
        "user_note": "Пользователь", "home_note": "Домашняя папка",
        "w_yes": "да", "w_no": "нет", "no_swap": "отсутствует",
        "st_enabled": "включён", "st_disabled": "отключён",
        "st_masked": "заблокирован", "st_notfound": "не найден",
        "yes": "ПРИМЕНЕНО", "no": "НЕ ПРИМЕНЕНО",
        "schedule_current": "Текущее: %s", "schedule_none": "не настроено",
        "mount_row_name": "Параметры монтирования",
        "steam_row_name": "Симлинк Steam",
        "mount_row_desc": "Добавляет в /etc/fstab опции noatime,nodiratime для раздела: меньше служебных обращений к диску при чтении (полезно для SSD и NTFS-дисков). Вступает в силу после перезагрузки.",
        "steam_row_desc": "Создаёт символическую ссылку compatdata в библиотеке Steam на этом NTFS-разделе, чтобы игры Steam видели данные Proton/Wine из домашней папки. Если compatdata уже есть как каталог с данными — он не трогается.",
        "viewer_title": "Просмотр файла",
        "about_purpose": "Графическая оболочка для безопасного тюнинга Linux Mint / Ubuntu / Debian: твики производительности, логов, дисков и игр с откатом и бэкапами.",
        "about_author": "Автор", "about_author_name": "Дмитрий Свистунов",
        "about_version": "Версия",
        "st_disk_both": "Диск / и /home (общий раздел)",
        "swap_file": "файл", "swap_part": "раздел",
        "viewer_open_ext": "Открыть во внешнем редакторе",
        "msg_run_title": "Выполняется", "msg_run_text": "Скрипт уже запущен. Дождитесь завершения.",
        "msg_noopt_title": "Нет выбранных опций", "msg_noopt_text": "Отметьте хотя бы одну опцию.",
        "msg_sel_title": "Службы", "msg_sel_text": "Сначала выберите строки в таблице (Ctrl/Shift + клик).",
        "msg_no_file_title": "Файл ещё не существует",
        "msg_no_file_text": "Этот файл появится после применения опции. Пути, где опция вносит изменения:",
        "help_title": "О твикере",
        "help": """System Tuneup GUI v0.5

Графическая оболочка для безопасного тюнинга Linux Mint / Ubuntu / Debian.

КАК ПОЛЬЗОВАТЬСЯ
1. Вкладка «Тюнинг»: отметьте нужные опции. Зелёная пометка «✓ применено»
   означает, что настройка уже активна в системе (даже если вы делали её вручную).
2. При необходимости укажите параметры: группа CoreCtrl, значение swappiness,
   расписание автообновлений.
3. Нажмите «Применить выбранное» и введите пароль sudo при запросе.
Текст в терминале, статусе и справке можно копировать: выделение + Ctrl+C
или правый клик мышью («Копировать», «Копировать всё», «Выделить всё»).
Меню закрывается левым кликом по любому месту или клавишей Escape.

КНОПКА «ФАЙЛ»
Открывает встроенный просмотрщик с содержимым файла, который изменяет опция
(работает в любом окружении, читает даже защищённые файлы через sudo).
Кнопка «Открыть во внешнем редакторе» передаёт файл системному редактору.

СУХОЙ ПРОГОН
Галочка «Сухой прогон» сверху: команды только показываются в логе,
изменения в систему не вносятся.

ПАРАМЕТРЫ МОНТИРОВАНИЯ (раздел «Диски и файловые системы»)
Отметьте смонтированные разделы — в /etc/fstab им будут добавлены опции
noatime,nodiratime (меньше обращений к диску). Изменения вступают в силу
после перезагрузки. Откат убирает эти опции из fstab.

СИМЛИНКИ STEAM (раздел «Диски и файловые системы»)
Предлагаются только библиотеки Steam на NTFS-разделах. Для отмеченных
создаётся ссылка <библиотека>/compatdata на ~/.steam/steam/steamapps/compatdata
(нужно для игр Steam на NTFS-дисках). Если compatdata уже существует как
каталог с данными — он не трогается, в логе будет предупреждение.
Откат удаляет только символические ссылки.

ВКЛАДКА «СЛУЖБЫ»
Показывает состояние служб, которые обычно не нужны на домашнем ПК.
Клик по строке выводит полное описание службы в панели под таблицей.
Кнопки выделяют/снимают выделение строк и включают/отключают выделенное.

ВКЛАДКА «СТАТУС»
Сводка по системе. В разделе «ТВИКИ» зелёным показаны применённые
настройки, красным — нет, рядом краткое описание.

ОТКАТ ИЗМЕНЕНИЙ
Перед изменением любого файла копия сохраняется в ~/system-tuneup-backups
(одна последняя копия каждого файла). Для отката:
- отметьте опции и нажмите «Откатить выбранное»;
- rsyslog: sudo systemctl unmask rsyslog && sudo systemctl enable --now rsyslog;
- GRUB-параметры удаляются вместе с update-grub при откате;
- службы: выделите на вкладке «Службы» и нажмите «Включить выбранные».
""",
    },
    "en": {
        "tab_tune": " Tuning ", "tab_serv": " Services ", "tab_stat": " Status ",
        "btn_apply_sel": "Apply selected", "btn_rollback": "Rollback selected",
        "btn_selall_opt": "Select all", "btn_selnone": "Deselect",
        "btn_export": "Export", "btn_help": "About",
        "theme_dark": "Dark theme", "theme_light": "Light theme",
        "lbl_dry": "Dry run", "lbl_terminal": "Terminal output:",
        "lbl_group": "Group:", "lbl_value": "Value:", "lbl_schedule": "Schedule:",
        "status_ready": "Ready", "status_running": "Running...",
        "status_done": "Done", "status_error": "Error",
        "applied_yes": "✓ applied", "applied_no": "not applied",
        "btn_open_file": "file",
        "menu_copy": "Copy", "menu_copy_all": "Copy all",
        "menu_select_all": "Select all",
        "svc_col_name": "Service", "svc_col_en": "State", "svc_col_act": "Running",
        "svc_col_desc": "Description & why disable",
        "svc_on": "[ON] running", "svc_onoff": "[ON/off] enabled, not running",
        "svc_off": "[OFF] disabled", "svc_masked": "[MASKED] blocked",
        "svc_na": "[N/A] not installed", "run_yes": "running", "run_no": "stopped",
        "svc_count": "Services: {n}",
        "svc_detail_hint": "Select a row to see the full service description.",
        "svc_on_sel": "Enable selected", "svc_off_sel": "Disable selected",
        "stat_refresh": "Refresh status",
        "st_hw": "=== SYSTEM INFORMATION ===",
        "st_tweaks": "=== TWEAKS ===",
        "st_services": "=== SERVICES ===", "st_kernel": "=== KERNEL (live values) ===",
        "st_timer": "Auto-update timer",
        "st_os_lbl": "OS", "st_gpu_lbl": "GPU", "st_screen_lbl": "Screen resolution",
        "st_swap_lbl": "Swap", "st_kernel_lbl": "Kernel",
        "st_de_lbl": "Desktop environment",
        "st_ram_lbl": "RAM", "st_disk_lbl": "Disk /", "st_disk_home": "Disk /home",
        "gb": "GB", "free_word": "free",
        "user_note": "User", "home_note": "Home folder",
        "w_yes": "yes", "w_no": "no", "no_swap": "none",
        "st_enabled": "enabled", "st_disabled": "disabled",
        "st_masked": "blocked", "st_notfound": "not found",
        "yes": "APPLIED", "no": "NOT APPLIED",
        "schedule_current": "Current: %s", "schedule_none": "not configured",
        "mount_row_name": "Mount options",
        "steam_row_name": "Steam symlink",
        "mount_row_desc": "Adds noatime,nodiratime options to the partition's /etc/fstab entry: fewer service disk accesses on reads (useful for SSD and NTFS disks). Takes effect after reboot.",
        "steam_row_desc": "Creates a compatdata symlink in the Steam library on this NTFS partition so Steam games can see Proton/Wine data from the home folder. If compatdata already exists as a directory with data it is left untouched.",
        "viewer_title": "File viewer",
        "about_purpose": "A graphical shell for safe tuning of Linux Mint / Ubuntu / Debian: performance, logs, disk and gaming tweaks with rollback and backups.",
        "about_author": "Author", "about_author_name": "Dmitry Svistunov",
        "about_version": "Version",
        "st_disk_both": "Disk / and /home (shared partition)",
        "swap_file": "file", "swap_part": "partition",
        "viewer_open_ext": "Open in external editor",
        "msg_run_title": "Running", "msg_run_text": "A job is already running. Wait for it to finish.",
        "msg_noopt_title": "No options selected", "msg_noopt_text": "Tick at least one option.",
        "msg_sel_title": "Services", "msg_sel_text": "Select table rows first (Ctrl/Shift + click).",
        "msg_no_file_title": "File does not exist yet",
        "msg_no_file_text": "This file appears after applying the option. Paths the option modifies:",
        "help_title": "About",
        "help": """System Tuneup GUI v0.5

A graphical shell for safe tuning of Linux Mint / Ubuntu / Debian.

HOW TO USE
1. Tuning tab: tick the options you want. A green "applied" mark means
   the setting is already active (even if you configured it manually).
2. Fill in parameters if needed: CoreCtrl group, swappiness, update schedule.
3. Press "Apply selected" and enter your sudo password when asked.
Text in the terminal, status and help can be copied: select + Ctrl+C
or right-click (Copy, Copy all, Select all).
The menu closes on a left click anywhere or Escape.

"FILE" BUTTON
Opens a built-in viewer with the content of the file the option modifies
(works in any desktop environment, reads protected files via sudo).
The "Open in external editor" button hands the file to the system editor.

DRY RUN
Tick "Dry run" at the top: commands are only printed to the log.

MOUNT OPTIONS ("Drives & filesystems" section)
Tick mounted partitions — noatime,nodiratime will be added to their
/etc/fstab entries (less disk wear). Changes take effect after reboot.
Rollback removes these options from fstab.

STEAM SYMLINKS ("Drives & filesystems" section)
Only Steam libraries on NTFS partitions are offered. For ticked ones a
symlink <library>/compatdata -> ~/.steam/steam/steamapps/compatdata is
created (needed for Steam games on NTFS disks). If compatdata already
exists as a directory with data it is left untouched with a warning.
Rollback removes symlinks only.

SERVICES TAB
Shows services usually unneeded on a home PC.
Clicking a row shows the full description in the panel below the table.
Buttons select/clear rows and enable/disable the selection.

STATUS TAB
System summary. In the TWEAKS section green means applied, red means not
applied, with a short description next to each line.

ROLLBACK
Before modifying any file a copy is saved to ~/system-tuneup-backups
(one latest copy per file). To roll back:
- tick options and press "Rollback selected";
- rsyslog: sudo systemctl unmask rsyslog && sudo systemctl enable --now rsyslog;
- GRUB parameters are removed together with update-grub on rollback;
- services: select on the Services tab and press "Enable selected".
""",
    },
}


def decode_bytes(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


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
    table = [("cinnamon", "Cinnamon"), ("xfce", "XFCE"), ("mate", "MATE"),
             ("plasma", "KDE Plasma"), ("kde", "KDE Plasma"), ("gnome", "GNOME"),
             ("lxqt", "LXQt"), ("lxde", "LXDE"), ("openbox", "Openbox"),
             ("budgie", "Budgie"), ("pantheon", "Pantheon"), ("i3", "i3"),
             ("hyprland", "Hyprland"), ("ukui", "UKUI")]
    for key, name in table:
        if key in d:
            return name
    return os.environ.get("XDG_CURRENT_DESKTOP", "") or "?"


def detect_lang():
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "")
        if val:
            return "ru" if val.lower().startswith("ru") else "en"
    return "en"


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
    vdf = os.path.join(user_home, ".steam", "steam", "steamapps",
                       "libraryfolders.vdf")
    if os.path.isfile(vdf):
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


class SudoManager:
    def __init__(self):
        self.parent = None
        self.authenticated = False
        self._keepalive_running = False

    def set_parent(self, parent):
        self.parent = parent

    def _sudo_cached(self):
        try:
            res = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=3)
            return res.returncode == 0
        except Exception:
            return False

    def authenticate(self):
        if self._sudo_cached():
            self.authenticated = True
            self._start_keepalive()
            return True
        for attempt in range(1, 4):
            password = simpledialog.askstring(
                "sudo", "Password (attempt %d/3):" % attempt,
                parent=self.parent, show="*")
            if password is None:
                return False
            if not password:
                messagebox.showwarning("sudo", "Empty password.", parent=self.parent)
                continue
            try:
                res = subprocess.run(["sudo", "-S", "-v"],
                                     input=(password + "\n").encode(),
                                     capture_output=True, timeout=15)
                if res.returncode == 0:
                    self.authenticated = True
                    self._start_keepalive()
                    return True
                messagebox.showerror("sudo", "Wrong password or no sudo rights.",
                                     parent=self.parent)
            except Exception as e:
                messagebox.showerror("sudo", "sudo failed:\n%s" % e, parent=self.parent)
        return False

    def ensure(self):
        if self._sudo_cached():
            self.authenticated = True
            self._start_keepalive()
            return True
        return self.authenticate()

    def run(self, args, input=None):
        if not self._sudo_cached():
            raise PermissionError("Sudo session expired. Press Apply again.")
        return subprocess.run(["sudo", "-n"] + list(args), input=input,
                              capture_output=True, timeout=180)

    def _start_keepalive(self):
        if self._keepalive_running:
            return
        self._keepalive_running = True

        def loop():
            while True:
                time.sleep(50)
                try:
                    if not self._sudo_cached():
                        break
                    subprocess.run(["sudo", "-n", "-v"], capture_output=True, timeout=5)
                except Exception:
                    pass
            self._keepalive_running = False
            self.authenticated = False
        threading.Thread(target=loop, daemon=True).start()


class SystemState:
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
            self.user_name = self._get_real_user()
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
                    self.gpu_model = self._parse_gpu_model(raw)
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
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session = os.environ.get("DESKTOP_SESSION", "").lower()
        if "cinnamon" in desktop or session == "cinnamon":
            self.cinnamon = True
        else:
            try:
                res = subprocess.run(["pgrep", "-x", "cinnamon"], capture_output=True, timeout=3)
                self.cinnamon = res.returncode == 0
            except Exception:
                pass
        self.has_flatpak = bool(shutil.which("flatpak"))

    def _parse_gpu_model(self, line):
        desc = line.split(": ", 1)[1] if ": " in line else line
        cleaned = re.sub(r"^[^\[]*\[[^\]]*\]\s*", "", desc)
        cleaned = re.sub(r"\(rev [^)]*\)", "", cleaned).strip()
        return cleaned or desc.strip()

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


class SystemOps:
    def __init__(self, sudo, state, log, dry_run):
        self.sudo = sudo
        self.state = state
        self.log = log
        self.dry_run = dry_run
        self.grub_changed = False
        self.backup_dir = os.path.join(state.user_home, "system-tuneup-backups")

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
            safe_name = path.lstrip("/").replace("/", "_")
            backup_path = os.path.join(self.backup_dir, safe_name + ".bak")
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(content)
            if self.state.user_name and self.state.user_name != "root":
                try:
                    pw = pwd.getpwnam(self.state.user_name)
                    os.chown(backup_path, pw.pw_uid, pw.pw_gid)
                except Exception:
                    pass
            self.log("[BACKUP] %s" % os.path.basename(backup_path), "info")
        except Exception as e:
            self.log("[WARN] Бэкап %s: %s" % (path, e), "warning")

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
            self.log("Ошибка команды: %s" % e, "error")
            return False
        if res.returncode == 0:
            if ok_msg:
                self.log(ok_msg, "success")
            return True
        if not ignore_error:
            err = decode_bytes(res.stderr).strip()
            msg = err_msg or "Команда завершилась с ошибкой: " + " ".join(args)
            if err:
                self.log("[ERR] %s\n   %s" % (msg, err), "error")
            else:
                self.log("[ERR] %s" % msg, "error")
        return False

    def path_exists(self, path):
        if os.path.exists(path):
            return True
        try:
            res = subprocess.run(["sudo", "-n", "test", "-e", path],
                                 capture_output=True, timeout=3)
            return res.returncode == 0
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
            self.log("[DRY RUN] Запись файла: %s" % path, "warning")
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
            self.log("Ошибка записи %s: %s" % (path, e), "error")
            return False
        if res.returncode != 0:
            self.log("Не удалось записать %s" % path, "error")
            return False
        if chmod:
            self.sudo_run(["chmod", chmod, path], ignore_error=True)
        if owner:
            self.sudo_run(["chown", owner, path], ignore_error=True)
        return True

    def ensure_line(self, path, line, pattern, chmod="644", owner=None, mkdir=False):
        if self.dry_run:
            self.log("[DRY RUN] %s: %s" % (path, line), "warning")
            return True
        content = self.read_file(path)
        if content is None:
            self.log("Не удалось прочитать %s" % path, "error")
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
            self.log("Уже настроено: %s" % path, "info")
            return True
        self.backup_file(path)
        return self.write_file(path, "\n".join(new_lines) + "\n",
                               chmod=chmod, owner=owner, mkdir=mkdir, backup=False)

    def unit_exists(self, name):
        try:
            res = subprocess.run(["systemctl", "list-unit-files", name,
                                  "--no-legend", "--no-pager"],
                                 capture_output=True, timeout=5)
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

    def _has_cinnamon_spices(self):
        if not self.state.cinnamon:
            return False
        if shutil.which("cinnamon-spice-updater"):
            return True
        return os.path.exists("/usr/bin/cinnamon-spice-updater")

    def add_grub_params(self, params):
        if self.dry_run:
            self.log("[DRY RUN] GRUB добавить: " + " ".join(params), "warning")
            return True
        path = "/etc/default/grub"
        if not self.path_exists(path):
            self.log("%s не найден" % path, "warning")
            return False
        content = self.read_file(path)
        if content is None:
            self.log("Не удалось прочитать %s" % path, "error")
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
                    new_lines.append('GRUB_CMDLINE_LINUX_DEFAULT="' + " ".join(parts) + '"')
                    changed = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        if not found:
            new_lines.append('GRUB_CMDLINE_LINUX_DEFAULT="' + " ".join(params) + '"')
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
        update_grub = shutil.which("update-grub")
        if not update_grub and os.path.exists("/usr/sbin/update-grub"):
            update_grub = "/usr/sbin/update-grub"
        grub_mkconfig = shutil.which("grub-mkconfig")
        if not grub_mkconfig and os.path.exists("/usr/sbin/grub-mkconfig"):
            grub_mkconfig = "/usr/sbin/grub-mkconfig"
        if update_grub:
            self.sudo_run([update_grub], ok_msg="GRUB обновлён",
                          err_msg="Ошибка update-grub")
        elif grub_mkconfig:
            self.sudo_run([grub_mkconfig, "-o", "/boot/grub/grub.cfg"],
                          ok_msg="GRUB обновлён", err_msg="Ошибка grub-mkconfig")
        else:
            self.log("Не найдена команда update-grub или grub-mkconfig", "warning")
        self.grub_changed = False

    def apply_rsyslog(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] disable + mask rsyslog", "warning"); return True
        if self.service_enabled("rsyslog.service") in ("disabled", "masked", "not-found"):
            self.log("rsyslog уже отключён", "info"); return True
        ok1 = self.sudo_run(["systemctl", "disable", "--now", "rsyslog"], ignore_error=True)
        ok2 = self.sudo_run(["systemctl", "mask", "rsyslog"], ignore_error=True)
        if ok1 or ok2:
            self.log("✓ rsyslog отключён", "success"); return True
        self.log("Не удалось отключить rsyslog", "error"); return False

    def apply_journald(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] journald → volatile, 50M", "warning"); return True
        path = "/etc/systemd/journald.conf"
        content = self.read_file(path)
        if content is None:
            self.log("Не удалось прочитать %s" % path, "error"); return False
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
        self.sudo_run(["journalctl", "--vacuum-size=200M", "--vacuum-time=1months"],
                      ignore_error=True)
        self.log("✓ journald → volatile (50M)", "success"); return True

    def apply_audit(self, params=None):
        return self.add_grub_params(["audit=0"])

    def apply_raid(self, params=None):
        if self.state.has_raid:
            self.log("Обнаружен RAID, пропуск raid=noautodetect", "warning"); return True
        return self.add_grub_params(["raid=noautodetect"])

    def _polkit_is_new(self):
        try:
            res = subprocess.run(["pkaction", "--version"],
                                 capture_output=True, text=True, timeout=5)
            m = re.search(r"(\d+)\.(\d+)", (res.stdout or "") + (res.stderr or ""))
            if m:
                major, minor = int(m.group(1)), int(m.group(2))
                return major > 0 or minor >= 106
        except Exception:
            pass
        return os.path.isdir("/etc/polkit-1/rules.d")

    def apply_corectrl(self, params=None):
        params = params or {}
        group = params.get("corectrl_group", "").strip() or self.state.user_name
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", group):
            self.log("Некорректное имя группы: %s" % group, "error"); return False
        if self.dry_run:
            self.log("[DRY RUN] CoreCtrl polkit rule для группы %s" % group, "warning")
            return True
        try:
            grp.getgrnam(group)
        except KeyError:
            self.log("Группа не найдена: %s" % group, "error"); return False
        if self._polkit_is_new():
            content = (
                "polkit.addRule(function(action, subject) {\n"
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
            self.log("✓ CoreCtrl настроен для группы %s (%s)"
                     % (group, os.path.basename(path)), "success")
            return True
        return False

    def apply_ppfeaturemask(self, params=None):
        return self.add_grub_params(["amdgpu.ppfeaturemask=0xffffffff"])

    def apply_vrr(self, params=None):
        if self.state.gpu not in ("AMD", "Unknown"):
            self.log("VRR доступен только для AMD GPU", "warning"); return True
        if self.dry_run:
            self.log("[DRY RUN] VRR/FreeSync конфиг", "warning"); return True
        content = ('Section "Device"\n    Identifier "AMD"\n    Driver "amdgpu"\n'
                   '    Option "VariableRefresh" "true"\nEndSection\n')
        path = "/etc/X11/xorg.conf.d/20-amdgpu.conf"
        if self.write_file(path, content, chmod="644", mkdir=True):
            self.log("✓ VRR/FreeSync включён", "success"); return True
        return False

    def apply_pipewire(self, params=None):
        d = os.path.join(self.state.user_home, ".config", "pipewire", "pipewire.conf.d")
        path = os.path.join(d, "10-sound.conf")
        if self.dry_run:
            self.log("[DRY RUN] PipeWire конфиг: %s" % path, "warning"); return True
        content = ("context.properties = {\n    default.clock.min-quantum = 512\n"
                   "    default.clock.quantum = 4096\n    default.clock.max-quantum = 8192\n}\n")
        if not self.sudo_run(["mkdir", "-p", d], ignore_error=True):
            return False
        if not self.write_file(path, content, chmod="644"):
            return False
        if self.state.user_name and self.state.user_name != "root":
            self.sudo_run(["chown", "-R",
                           "%s:%s" % (self.state.user_name, self.state.user_name),
                           os.path.join(self.state.user_home, ".config", "pipewire")],
                          ignore_error=True)
        self.log("✓ PipeWire настроен", "success"); return True

    def apply_mesa(self, params=None):
        return self.ensure_line("/etc/environment", "MESA_SHADER_CACHE_MAX_SIZE=4G",
                                r"^\s*MESA_SHADER_CACHE_MAX_SIZE=.*")

    def apply_radv(self, params=None):
        return self.ensure_line("/etc/environment", "RADV_PERFTEST=sam",
                                r"^\s*RADV_PERFTEST=.*")

    def apply_swap(self, params=None):
        params = params or {}
        if not self.state.has_swap:
            self.log("Swap не обнаружен, тюнинг swap пропущен", "warning"); return True
        val = params.get("swap_value", "").strip()
        if not val:
            val = "150" if self.state.swap_type == "zram" else "10"
        try:
            int_val = int(val)
            if int_val < 0 or int_val > 200:
                raise ValueError
        except ValueError:
            self.log("Некорректное значение swappiness: %s (нужно 0-200)" % val, "error")
            return False
        if self.dry_run:
            self.log("[DRY RUN] vm.swappiness=%d" % int_val, "warning"); return True
        path = "/etc/sysctl.d/99-gaming-swap.conf"
        existing = self.read_file(path)
        pat = "^vm\\.swappiness=%d$" % int_val
        if existing and re.search(pat, existing, re.M):
            self.log("vm.swappiness уже установлен: %d" % int_val, "info"); return True
        if not self.write_file(path, "vm.swappiness=%d\n" % int_val, chmod="644", mkdir=True):
            return False
        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        self.log("✓ vm.swappiness=%d" % int_val, "success"); return True

    def apply_sysctl(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] vfs_cache_pressure=50, numa_balancing=0", "warning")
            return True
        path = "/etc/sysctl.d/99-gaming-sysctl.conf"
        existing = self.read_file(path)
        if existing:
            if (re.search(r"^vm\.vfs_cache_pressure=50$", existing, re.M)
                    and re.search(r"^kernel\.numa_balancing=0$", existing, re.M)):
                self.log("sysctl уже настроен", "info"); return True
        content = "vm.vfs_cache_pressure=50\nkernel.numa_balancing=0\n"
        self.backup_file(path)
        if not self.write_file(path, content, chmod="644", mkdir=True, backup=False):
            return False
        self.sudo_run(["sysctl", "-p", path], ignore_error=True)
        self.log("✓ vfs_cache_pressure=50, numa_balancing=0", "success"); return True

    def apply_ntsync(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] ntsync modules-load", "warning"); return True
        if self.state.ntsync:
            self.log("ntsync уже доступен в системе", "info"); return True
        path = "/etc/modules-load.d/ntsync.conf"
        if not self.write_file(path, "ntsync\n", chmod="644", mkdir=True):
            return False
        self.sudo_run(["modprobe", "ntsync"], ignore_error=True)
        self.log("✓ ntsync добавлен в автозагрузку", "success"); return True

    def apply_ntfs3(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] ntfs3 blacklist unlock", "warning"); return True
        path = "/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"
        if not self.path_exists(path):
            self.log("mint-blacklist-ntfs3.conf не найден (система не Mint?)", "warning")
            return True
        content = self.read_file(path)
        if content is None:
            self.log("Не удалось прочитать %s" % path, "error"); return False
        if re.search(r"^\s*#\s*blacklist\s+ntfs3\s*$", content, re.M):
            self.log("ntfs3 уже раскомментирован", "info"); return True
        if re.search(r"^\s*blacklist\s+ntfs3\s*$", content, re.M):
            new_content = re.sub(r"^\s*blacklist\s+ntfs3\s*$", "# blacklist ntfs3",
                                 content, flags=re.M)
            self.backup_file(path)
            if self.write_file(path, new_content, backup=False):
                self.log("✓ ntfs3 раскомментирован", "success"); return True
            return False
        self.log("blacklist ntfs3 не найден в файле", "warning"); return True

    def apply_aliases(self, params=None):
        bashrc = os.path.join(self.state.user_home, ".bashrc")
        if self.dry_run:
            self.log("[DRY RUN] Добавить команды в %s" % bashrc, "warning"); return True
        if not self.path_exists(bashrc):
            self.log(".bashrc не найден: %s" % bashrc, "error"); return False
        content = self.read_file(bashrc)
        if content is None:
            self.log("Не удалось прочитать .bashrc", "error"); return False
        start_marker = "# >>> system-tuneup commands >>>"
        end_marker = "# <<< system-tuneup commands <<<"
        lines = content.splitlines()
        without_block = []
        skip = False
        for line in lines:
            if line.strip() == start_marker:
                skip = True; continue
            if line.strip() == end_marker:
                skip = False; continue
            if not skip:
                without_block.append(line)
        names = ["upd", "upgr", "spices", "update_all", "inst", "remove", "search",
                 "info", "clean", "space", "fix", "mem", "serv", "update_time"]
        names_pattern = "|".join(names)
        alias_rx = re.compile(r"^\s*alias\s+(" + names_pattern + r")=")
        func_rx = re.compile(r"^\s*(" + names_pattern + r")\s*\(\)\s*\{")
        cleaned = []
        skip_function = False
        for line in without_block:
            if alias_rx.match(line):
                continue
            if func_rx.match(line):
                if "}" in line:
                    continue
                skip_function = True; continue
            if skip_function:
                if line.strip().startswith("}"):
                    skip_function = False
                continue
            if "system-tuneup" in line and line.strip().startswith("#"):
                continue
            cleaned.append(line)
        spices = self._has_cinnamon_spices()
        has_fp = self.state.has_flatpak
        block = [start_marker, "# Пользовательские команды обновлений (system-tuneup)", ""]
        block += ["upd() {", '    echo "Поиск обновлений APT..."', "    sudo apt update", "}", ""]
        block += ["upgr() {", '    echo "Обновление пакетов APT..."', "    sudo apt full-upgrade"]
        if has_fp:
            block.append('    echo "Обновление Flatpak..."')
            if spices:
                block.append("    flatpak update && cinnamon-spice-updater --update-all")
            else:
                block.append("    flatpak update")
        block += ["}", ""]
        if spices:
            block += ["spices() {", '    echo "Обновление апплетов Cinnamon..."',
                      "    cinnamon-spice-updater --update-all", "}", ""]
        block += ["update_all() {", "    sudo apt update && sudo apt full-upgrade -y"]
        if has_fp:
            block.append("    flatpak update -y")
        if spices:
            block.append("    cinnamon-spice-updater --update-all")
        block += ['    echo "Все обновления завершены!"', "}", ""]
        block += ["# Дополнительные команды (system-tuneup)",
                  'inst() { sudo apt install "$@"; }',
                  'remove() { sudo apt purge --autoremove "$@"; }',
                  'search() { apt search "$@"; }',
                  'info() { apt show "$@"; }', ""]
        block += ["clean() {", '    echo "Очистка системы..."', "    sudo apt autoremove -y",
                  "    sudo apt autoclean", "    sudo apt clean",
                  '    echo "Очистка завершена"', "}", ""]
        block += ["space() {", "    df -h / | awk 'NR==2 {print \"/: \" $4 \" свободно из \" $2}'",
                  "}", ""]
        block += ["fix() {", '    echo "Исправление сломанных пакетов..."',
                  "    sudo apt --fix-broken install -y", "    sudo dpkg --configure -a",
                  '    echo "Готово!"', "}", ""]
        block += ["mem() {", '    echo "Очистка памяти..."', "    sync",
                  "    sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'", "    free -h", "}", ""]
        block += ["serv() {", "    systemctl list-unit-files --type=service | less", "}", ""]
        block += ["update_time() {",
                  "    systemctl list-timers --no-pager 2>/dev/null | "
                  'grep -E "NEXT|upgrade|update|apt" || echo "Таймеры не найдены"', "}", ""]
        block.append(end_marker)
        while cleaned and cleaned[-1].strip() == "":
            cleaned.pop()
        new_content = "\n".join(cleaned + [""] + block) + "\n"
        if new_content == content:
            self.log("Команды уже добавлены", "info"); return True
        self.backup_file(bashrc)
        if not self.write_file(bashrc, new_content, backup=False):
            return False
        if self.state.user_name and self.state.user_name != "root":
            self.sudo_run(["chown", "%s:%s" % (self.state.user_name, self.state.user_name),
                           bashrc], ignore_error=True)
        self.log("✓ Команды добавлены в .bashrc", "success"); return True

    def apply_autoupdate(self, params=None):
        params = params or {}
        schedule_ui = params.get("update_schedule", "Отключено")
        schedules = {
            "Ежедневно": ("*-*-* 18:30:00", "ежедневно в 18:30"),
            "Еженедельно (суббота)": ("Sat 18:30:00", "по субботам в 18:30"),
            "2 раза в месяц (1 и 15)": ("*-*-1,15 18:30:00", "1 и 15 числа в 18:30"),
            "Ежемесячно (1 число)": ("*-*-1 18:30:00", "1 числа в 18:30"),
            "Daily": ("*-*-* 18:30:00", "daily at 18:30"),
            "Weekly (Saturday)": ("Sat 18:30:00", "Saturdays at 18:30"),
            "Twice a month (1 & 15)": ("*-*-1,15 18:30:00", "on the 1st and 15th"),
            "Monthly (1st)": ("*-*-1 18:30:00", "on the 1st"),
            "Disabled": (None, None),
            "Отключено": (None, None),
        }
        svc = "/etc/systemd/system/biweekly-upgrade.service"
        tmr = "/etc/systemd/system/biweekly-upgrade.timer"
        exists = self.path_exists(tmr) or self.path_exists(svc)
        if schedule_ui in ("Отключено", "Disabled"):
            if not exists:
                self.log("Таймер автообновлений не найден", "info"); return True
            if self.dry_run:
                self.log("[DRY RUN] Удалить таймер автообновлений", "warning"); return True
            self.sudo_run(["systemctl", "disable", "--now", "biweekly-upgrade.timer"],
                          ignore_error=True)
            self.sudo_run(["rm", "-f", svc, tmr], ignore_error=True)
            self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
            self.log("Таймер автообновлений удалён", "success"); return True
        if schedule_ui not in schedules:
            self.log("Неизвестное расписание: %s" % schedule_ui, "error"); return False
        oncalendar, desc = schedules[schedule_ui]
        spices = self._has_cinnamon_spices()
        full_cmd = "apt update && apt full-upgrade -y"
        if self.state.has_flatpak:
            full_cmd += " && flatpak update -y"
        if spices:
            full_cmd += " && cinnamon-spice-updater --update-all"
        svc_content = ("[Unit]\nDescription=System upgrade (%s)\n\n[Service]\nType=oneshot\n"
                       "ExecStartPre=/bin/sleep 600\nExecStart=/usr/bin/bash -c \"%s\"\n"
                       "User=root\n" % (desc, full_cmd))
        tmr_content = ("[Unit]\nDescription=System upgrade timer (%s)\n\n[Timer]\n"
                       "OnCalendar=%s\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n"
                       % (desc, oncalendar))
        ex_svc = self.read_file(svc)
        ex_tmr = self.read_file(tmr)
        if exists and ex_svc == svc_content and ex_tmr == tmr_content:
            self.log("Таймер уже настроен: %s" % desc, "info")
            if self.service_enabled("biweekly-upgrade.timer") != "enabled":
                if not self.dry_run:
                    self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
                    self.sudo_run(["systemctl", "enable", "--now", "biweekly-upgrade.timer"],
                                  ignore_error=True)
            return True
        if self.dry_run:
            self.log("[DRY RUN] Создать/обновить таймер: %s" % desc, "warning"); return True
        self.sudo_run(["systemctl", "disable", "--now",
                       "mintupdate-automation-upgrade.timer"], ignore_error=True)
        if not self.write_file(svc, svc_content, chmod="644"):
            return False
        if not self.write_file(tmr, tmr_content, chmod="644"):
            return False
        self.sudo_run(["systemctl", "daemon-reload"], ignore_error=True)
        self.sudo_run(["systemctl", "enable", "--now", "biweekly-upgrade.timer"],
                      ok_msg="✓ Таймер создан/обновлён: %s" % desc,
                      err_msg="Не удалось включить таймер")
        return True

    # ─── fstab: noatime,nodiratime ───────────────────────────────────────
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
            parts = s.split()
            if len(parts) < 4:
                continue
            if parts[1] == mp:
                return i, parts
            if uuid and parts[0].lower() == ("uuid=%s" % uuid).lower():
                return i, parts
        return None, None

    def _mount_opts_edit(self, mp, add=True):
        path = "/etc/fstab"
        content = self.read_file(path)
        if not content:
            self.log("Не удалось прочитать /etc/fstab", "error"); return False
        dev = None
        for it in parse_mounts():
            if it["mp"] == mp:
                dev = it["dev"]; break
        uuid = self._uuid_of(dev) if dev else ""
        lines = content.splitlines()
        idx, parts = self._fstab_find(lines, mp, uuid)
        if idx is None:
            self.log("%s не найден в /etc/fstab — пропуск" % mp, "warning")
            return False
        opts = parts[3].split(",")
        target = ["noatime", "nodiratime"]
        if add:
            new_opts = opts + [o for o in target if o not in opts]
        else:
            new_opts = [o for o in opts if o not in target]
        if new_opts == opts:
            self.log("Уже настроено: %s" % mp, "info"); return True
        parts[3] = ",".join(new_opts)
        lines[idx] = "\t".join(parts)
        self.backup_file(path)
        if not self.write_file(path, "\n".join(lines) + "\n", backup=False):
            return False
        if add:
            self.log("✓ fstab: %s → noatime,nodiratime (вступит в силу после перезагрузки)"
                     % mp, "success")
        else:
            self.log("✓ fstab: %s → опции убраны (после перезагрузки)" % mp, "success")
        return True

    def apply_mount_opts(self, mps):
        if self.dry_run:
            for mp in mps:
                self.log("[DRY RUN] fstab: %s +noatime,nodiratime" % mp, "warning")
            return True
        for mp in mps:
            self._mount_opts_edit(mp, add=True)
        return True

    def rollback_mount_opts(self, mps):
        if self.dry_run:
            for mp in mps:
                self.log("[DRY RUN] fstab: %s -noatime,nodiratime" % mp, "warning")
            return True
        for mp in mps:
            self._mount_opts_edit(mp, add=False)
        return True

    # ─── Steam compatdata ────────────────────────────────────────────────
    def apply_steam_links(self, libs):
        src = os.path.join(self.state.user_home, ".steam", "steam",
                           "steamapps", "compatdata")
        try:
            os.makedirs(src, exist_ok=True)
        except Exception as e:
            self.log("Не удалось создать %s: %s" % (src, e), "error")
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
                    self.log("Пропуск: %s уже существует как каталог с данными" % dst,
                             "warning")
                    continue
                elif os.path.exists(dst):
                    self.log("Пропуск: %s существует и не является каталогом/ссылкой" % dst,
                             "warning")
                    continue
                os.symlink(src, dst)
                self.log("✓ симлинк создан: %s" % dst, "success")
            except Exception as e:
                self.log("Ошибка симлинка %s: %s" % (dst, e), "error")
        return True

    def rollback_steam_links(self, libs):
        for lib in libs:
            dst = os.path.join(lib, "compatdata")
            if self.dry_run:
                self.log("[DRY RUN] rm %s (симлинк)" % dst, "warning")
                continue
            try:
                if os.path.islink(dst):
                    os.remove(dst)
                    self.log("✓ симлинк удалён: %s" % dst, "success")
                else:
                    self.log("Не симлинк, не трогаем: %s" % dst, "info")
            except Exception as e:
                self.log("Ошибка удаления %s: %s" % (dst, e), "error")
        return True

    # ─── Откат изменений ─────────────────────────────────────────────────
    def _rm(self, path):
        if self.dry_run:
            self.log("[DRY RUN] rm %s" % path, "warning"); return True
        if not self.path_exists(path):
            self.log("Файл не найден, удалять нечего: %s" % path, "info")
            return True
        return self.sudo_run(["rm", "-f", path], ok_msg="✓ удалён %s" % path)

    def _remove_line(self, path, pattern):
        if self.dry_run:
            self.log("[DRY RUN] %s: удалить строку по %s" % (path, pattern), "warning")
            return True
        content = self.read_file(path)
        if not content:
            self.log("Файл %s не найден" % path, "info"); return True
        rx = re.compile(pattern)
        old = content.splitlines()
        lines = [l for l in old if not rx.match(l.strip())]
        if len(lines) == len(old):
            self.log("Строка не найдена в %s" % path, "info"); return True
        self.backup_file(path)
        return self.write_file(path, "\n".join(lines) + "\n", backup=False)

    def _remove_grub_params(self, params):
        if self.dry_run:
            self.log("[DRY RUN] GRUB убрать: " + " ".join(params), "warning")
            return True
        path = "/etc/default/grub"
        content = self.read_file(path)
        if not content:
            self.log("GRUB не найден", "warning"); return False
        new_lines = []
        changed = False
        for line in content.splitlines():
            m = re.match(r"^\s*GRUB_CMDLINE_LINUX_DEFAULT=(.*)$", line)
            if m:
                raw = m.group(1).strip().strip('"').strip("'")
                parts = [p for p in raw.split() if p and p not in params]
                new_lines.append('GRUB_CMDLINE_LINUX_DEFAULT="' + " ".join(parts) + '"')
                changed = True
            else:
                new_lines.append(line)
        if not changed:
            self.log("GRUB: параметры не найдены", "info"); return True
        self.backup_file(path)
        if self.write_file(path, "\n".join(new_lines) + "\n", backup=False):
            self.grub_changed = True
            self.log("✓ GRUB: параметры удалены", "success"); return True
        return False

    def rollback_rsyslog(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] unmask + enable rsyslog", "warning"); return True
        self.sudo_run(["systemctl", "unmask", "rsyslog"], ignore_error=True)
        self.sudo_run(["systemctl", "enable", "--now", "rsyslog"],
                      ok_msg="✓ rsyslog снова включён", ignore_error=True)
        return True

    def rollback_journald(self, params=None):
        path = "/etc/systemd/journald.conf"
        bak = os.path.join(self.backup_dir, "etc_systemd_journald.conf.bak")
        if self.path_exists(bak):
            content = self.read_file(bak)
            if content:
                self.write_file(path, content, backup=False)
                self.sudo_run(["systemctl", "restart", "systemd-journald"],
                              ignore_error=True)
                self.log("✓ journald: восстановлен из бэкапа", "success"); return True
        self._remove_line(path, r"^\s*Storage\s*=")
        self._remove_line(path, r"^\s*RuntimeMaxUse\s*=")
        self.sudo_run(["systemctl", "restart", "systemd-journald"], ignore_error=True)
        self.log("✓ journald: возвращён к значениям по умолчанию", "success")
        return True

    def rollback_audit(self, params=None):
        return self._remove_grub_params(["audit=0"])

    def rollback_raid(self, params=None):
        return self._remove_grub_params(["raid=noautodetect"])

    def rollback_ppfeaturemask(self, params=None):
        return self._remove_grub_params(["amdgpu.ppfeaturemask=0xffffffff"])

    def rollback_corectrl(self, params=None):
        self._rm("/etc/polkit-1/rules.d/90-corectrl.rules")
        self._rm("/etc/polkit-1/localauthority/50-local.d/90-corectrl.pkla")
        self.log("✓ правило CoreCtrl удалено", "success"); return True

    def rollback_vrr(self, params=None):
        self._rm("/etc/X11/xorg.conf.d/20-amdgpu.conf")
        self.log("✓ конфиг VRR удалён", "success"); return True

    def rollback_radv(self, params=None):
        self._remove_line("/etc/environment", r"^\s*RADV_PERFTEST=.*")
        self.log("✓ RADV_PERFTEST удалён", "success"); return True

    def rollback_mesa(self, params=None):
        self._remove_line("/etc/environment", r"^\s*MESA_SHADER_CACHE_MAX_SIZE=.*")
        self.log("✓ MESA_SHADER_CACHE удалён", "success"); return True

    def rollback_pipewire(self, params=None):
        self._rm(os.path.join(self.state.user_home, ".config", "pipewire",
                              "pipewire.conf.d", "10-sound.conf"))
        self.log("✓ конфиг PipeWire удалён", "success"); return True

    def rollback_swap(self, params=None):
        self._rm("/etc/sysctl.d/99-gaming-swap.conf")
        self.sudo_run(["sysctl", "-w", "vm.swappiness=60"], ignore_error=True)
        self.log("✓ swappiness возвращён к 60", "success"); return True

    def rollback_sysctl(self, params=None):
        self._rm("/etc/sysctl.d/99-gaming-sysctl.conf")
        self.sudo_run(["sysctl", "-w", "vm.vfs_cache_pressure=100"], ignore_error=True)
        self.sudo_run(["sysctl", "-w", "kernel.numa_balancing=1"], ignore_error=True)
        self.log("✓ sysctl возвращён к значениям по умолчанию", "success"); return True

    def rollback_ntsync(self, params=None):
        self._rm("/etc/modules-load.d/ntsync.conf")
        self.log("✓ ntsync убран из автозагрузки", "success"); return True

    def rollback_ntfs3(self, params=None):
        path = "/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"
        content = self.read_file(path)
        if not content:
            self.log("Файл не найден: %s" % path, "info"); return True
        if re.search(r"^\s*blacklist\s+ntfs3\s*$", content, re.M):
            self.log("ntfs3 уже заблокирован", "info"); return True
        new_content = re.sub(r"^\s*#\s*blacklist\s+ntfs3\s*$", "blacklist ntfs3",
                             content, flags=re.M)
        self.backup_file(path)
        if self.write_file(path, new_content, backup=False):
            self.log("✓ ntfs3 снова заблокирован", "success"); return True
        return False

    def rollback_aliases(self, params=None):
        bashrc = os.path.join(self.state.user_home, ".bashrc")
        content = self.read_file(bashrc)
        if not content:
            self.log(".bashrc не найден", "info"); return True
        start_marker = "# >>> system-tuneup commands >>>"
        end_marker = "# <<< system-tuneup commands <<<"
        lines = []
        skip = False
        for line in content.splitlines():
            if line.strip() == start_marker:
                skip = True; continue
            if line.strip() == end_marker:
                skip = False; continue
            if not skip:
                lines.append(line)
        if len(lines) == len(content.splitlines()):
            self.log("Блок команд не найден", "info"); return True
        self.backup_file(bashrc)
        if self.write_file(bashrc, "\n".join(lines) + "\n", backup=False):
            self.log("✓ команды удалены из .bashrc", "success"); return True
        return False

    def rollback_autoupdate(self, params=None):
        return self.apply_autoupdate({"update_schedule": "Отключено"})


class TuneupApp:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.is_running = False
        self.lang = detect_lang()
        self.current_theme = "light"
        self.applied = {}
        self.mount_applied = {}
        self.steam_applied = {}
        self.option_widgets = {}
        self.applied_labels = {}
        self.mount_labels = {}
        self.steam_labels = {}
        self._copy_menu_shown = None
        self.dry_run_var = tk.BooleanVar(value="--dry-run" in sys.argv)
        self.sudo = SudoManager()
        self.sudo.set_parent(root)
        self.state = SystemState()
        self.state.detect()
        default_group = self.state.user_name if self.state.user_name != "root" else "sudo"
        self.corectrl_group = tk.StringVar(value=default_group)
        self.swap_value = tk.StringVar(
            value="150" if self.state.swap_type == "zram" else "10")
        self.update_schedule = tk.StringVar(value=self._schedule_values()[2])
        self.options = {k: {"var": tk.BooleanVar(value=False)} for k in OPTIONS_META}
        self.mount_items = []
        for it in parse_mounts():
            it["var"] = tk.BooleanVar(value=False)
            self.mount_items.append(it)
        self.steam_items = []
        for lib in find_steam_libraries(self.state.user_home):
            if self._lib_on_ntfs(lib):
                self.steam_items.append({"lib": lib, "var": tk.BooleanVar(value=False)})
        self.dpi_scale = max(1.0, self.root.winfo_fpixels('1i') / 96.0)
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.ui_scale = min(1.0, self.screen_w / 1100.0, self.screen_h / 850.0)
        if self.ui_scale < 0.75:
            self.ui_scale = 0.75
        self.create_ui()
        self.apply_hardware_restrictions()
        self.update_title()
        self.root.after(100, self.process_queue)
        self.log("System Tuneup GUI запущен", "success")
        self.log("Версия: %s" % APP_VERSION, "info")
        self.log("GPU: %s %s" % (self.state.gpu, self.state.gpu_model), "info")
        if self.dry_run_var.get():
            self.log("Режим: СУХОЙ ПРОГОН", "warning")
        if self.sudo._sudo_cached():
            self.log("Сессия sudo активна", "success")
        else:
            self.log("Для применения нужен пароль sudo", "warning")
        self.root.after(400, self.refresh_services)
        self.root.after(900, self.refresh_applied)
        self.root.after(1200, self.refresh_status)

    # ─── дисковые helpers ───
    def _fstype_of(self, dev):
        try:
            res = subprocess.run(["lsblk", "-no", "FSTYPE", dev],
                                 capture_output=True, text=True, timeout=5)
            out = res.stdout.strip().splitlines()
            return out[0] if out else ""
        except Exception:
            return ""

    def _lib_on_ntfs(self, lib):
        best_mp = ""
        dev = ""
        fstype = ""
        for it in parse_mounts():
            mp = it["mp"]
            if lib == mp or lib.startswith(mp.rstrip("/") + "/") or mp == "/":
                if len(mp) > len(best_mp):
                    best_mp, dev, fstype = mp, it["dev"], it["fstype"]
        if fstype in ("ntfs", "ntfs3", "fuseblk"):
            return True
        if fstype in ("auto", ""):
            fstype = self._fstype_of(dev)
        return fstype in ("ntfs", "ntfs3", "fuseblk")

    def _disk_info(self, path):
        try:
            st = os.statvfs(path)
            total = st.f_blocks * st.f_frsize / 1024.0 ** 3
            free = st.f_bavail * st.f_frsize / 1024.0 ** 3
            return total, free
        except Exception:
            return None

    def _home_separate(self):
        try:
            return os.stat("/").st_dev != os.stat(self.state.user_home).st_dev
        except Exception:
            return False

    def _col(self, name):
        if len(name) > 31:
            name = name[:30] + "…"
        return name.ljust(32)

    def _exists_any(self, p):
        if os.path.exists(p):
            return True
        try:
            r = subprocess.run(["sudo", "-n", "test", "-e", p],
                               capture_output=True, timeout=3)
            return r.returncode == 0
        except Exception:
            return False

    def _spawn(self, cmd):
        env = {k: v for k, v in os.environ.items()
               if k not in ("LD_LIBRARY_PATH", "LD_PRELOAD", "PYTHONPATH",
                            "PYTHONHOME", "APPDIR", "APPIMAGE", "UNION_PRELOAD")}
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         start_new_session=True, env=env)

    def _show_viewer(self, path, content):
        win = tk.Toplevel(self.root)
        win.title("%s: %s" % (self.t("viewer_title"), path))
        win.geometry("%dx%d" % (min(self._scaled(760), self.screen_w - 20),
                                min(self._scaled(520), self.screen_h - 40)))
        t = THEMES[self.current_theme]
        win.configure(bg=t["bg"])
        text = scrolledtext.ScrolledText(win, font=("DejaVu Sans Mono", self._scaled(9)),
                                         bg=t["terminal_bg"], fg=t["terminal_fg"],
                                         wrap="word", relief="flat",
                                         padx=self._scaled(8), pady=self._scaled(8))
        text.pack(fill="both", expand=True)
        text.insert("1.0", content)
        text.configure(state="disabled")
        self._make_copyable(text)
        bf = tk.Frame(win, bg=t["bg"])
        bf.pack(fill="x", padx=self._scaled(8), pady=(0, self._scaled(8)))

        def open_ext():
            for cmd in (["xdg-open", path], ["gio", "open", path],
                        ["xed", path], ["gedit", path], ["mousepad", path],
                        ["kate", path], ["pluma", path]):
                try:
                    self._spawn(cmd)
                    return
                except Exception:
                    continue
        tk.Button(bf, text=self.t("viewer_open_ext"), command=open_ext,
                  font=("DejaVu Sans", self._scaled(9)),
                  padx=self._scaled(10), pady=self._scaled(3)).pack(side="left")

    def create_disk_extras(self):
        for it in self.mount_items:
            row = tk.Frame(self.options_inner)
            row.pack(fill="x", pady=self._scaled(1))
            top = tk.Frame(row)
            top.pack(fill="x")
            cb = tk.Checkbutton(top, text="%s (%s)" % (it["mp"], it["dev"]),
                                variable=it["var"],
                                font=("DejaVu Sans", self._scaled(10)), anchor="w")
            cb.pack(side="left")
            ap = tk.Label(top, text="…", font=("DejaVu Sans", self._scaled(9), "bold"))
            ap.pack(side="left", padx=(self._scaled(12), 0))
            self.mount_labels[it["mp"]] = ap
            self._fix(tk.Label(row, text=self.t("mount_row_desc"),
                               font=("DejaVu Sans", self._scaled(8)),
                               anchor="w", wraplength=self._scaled(760),
                               justify="left"),
                      "gray").pack(fill="x", padx=(self._scaled(26), 0),
                                   pady=(0, self._scaled(2)))
        if self.mount_items and self.steam_items:
            ttk.Separator(self.options_inner, orient="horizontal").pack(
                fill="x", pady=self._scaled(8))
        for it in self.steam_items:
            row = tk.Frame(self.options_inner)
            row.pack(fill="x", pady=self._scaled(1))
            top = tk.Frame(row)
            top.pack(fill="x")
            cb = tk.Checkbutton(top, text=it["lib"], variable=it["var"],
                                font=("DejaVu Sans", self._scaled(10)), anchor="w")
            cb.pack(side="left")
            ap = tk.Label(top, text="…", font=("DejaVu Sans", self._scaled(9), "bold"))
            ap.pack(side="left", padx=(self._scaled(12), 0))
            self.steam_labels[it["lib"]] = ap
            self._fix(tk.Label(row, text=self.t("steam_row_desc"),
                               font=("DejaVu Sans", self._scaled(8)),
                               anchor="w", wraplength=self._scaled(760),
                               justify="left"),
                      "gray").pack(fill="x", padx=(self._scaled(26), 0),
                                   pady=(0, self._scaled(2)))

    # ─── helpers ───
    def t(self, key):
        return STR[self.lang][key]

    def om(self, key):
        return OPTIONS_META[key][self.lang]

    def _scaled(self, px):
        v = int(px * self.dpi_scale * self.ui_scale)
        if px >= 8 and v < 7:
            v = 7
        return max(1, v)

    def _fix(self, widget, color_key):
        widget._fixed_fg = color_key
        return widget

    def _alive(self, name):
        w = getattr(self, name, None)
        return w is not None and w.winfo_exists()

    def _schedule_values(self):
        if self.lang == "ru":
            return ("Отключено", "Ежедневно", "Еженедельно (суббота)",
                    "2 раза в месяц (1 и 15)", "Ежемесячно (1 число)")
        return ("Disabled", "Daily", "Weekly (Saturday)",
                "Twice a month (1 & 15)", "Monthly (1st)")

    def _swap_size_gb(self):
        try:
            with open("/proc/meminfo", "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("SwapTotal:"):
                        return int(line.split()[1]) / 1024.0 / 1024.0
        except Exception:
            pass
        return None

    def _os_pretty(self):
        name = ""
        try:
            with open("/etc/os-release", "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        name = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass
        if not name:
            name = "Linux"
        bits = 64 if sys.maxsize > 2 ** 32 else 32
        return "%s (%d-бит)" % (name, bits) if self.lang == "ru" \
            else "%s (%d-bit)" % (name, bits)

    # ─── theme ──
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
        style.configure("TNotebook.Tab", background=t["notebook_tab_bg"],
                        foreground=t["fg"],
                        padding=[self._scaled(12), self._scaled(5)])
        style.map("TNotebook.Tab",
                  background=[("selected", t["notebook_tab_selected"])],
                  foreground=[("selected", t["fg"])])
        style.configure("Treeview", background=t["tree_bg"], foreground=t["tree_fg"],
                        fieldbackground=t["tree_bg"], rowheight=self._scaled(26))
        style.configure("Treeview.Heading", background=t["tree_heading_bg"],
                        foreground=t["tree_heading_fg"])
        style.configure("TCombobox", fieldbackground=t["entry_bg"],
                        foreground=t["entry_fg"])
        style.configure("Vertical.TScrollbar", troughcolor=t["scrollbar_trough"],
                        background=t["scrollbar_slider"], borderwidth=1, relief="solid",
                        width=self._scaled(14), arrowsize=self._scaled(14))
        style.map("Vertical.TScrollbar",
                  background=[("active", t["gray"]), ("!active", t["scrollbar_slider"])])
        style.configure("Horizontal.TProgressbar", troughcolor=t["scrollbar_trough"],
                        background=t["accent_bg"])
        self._update_tk_widgets(t)
        if self._alive("services_tree"):
            self.services_tree.tag_configure("g", foreground=t["green"])
            self.services_tree.tag_configure("y", foreground=t["yellow"])
            self.services_tree.tag_configure("r", foreground=t["red"])
            self.services_tree.tag_configure("gr", foreground=t["gray"])
        if self._alive("status_text_widget"):
            mono = ("DejaVu Sans Mono", self._scaled(9))
            mono_b = ("DejaVu Sans Mono", self._scaled(9), "bold")
            self.status_text_widget.tag_configure("ok", foreground=t["green"])
            self.status_text_widget.tag_configure("no", foreground=t["red"])
            self.status_text_widget.tag_configure("warn", foreground=t["yellow"])
            self.status_text_widget.tag_configure("info", foreground=t["terminal_fg"],
                                                  font=mono)
            self.status_text_widget.tag_configure("head", foreground=t["blue"],
                                                  font=mono_b)
            self.status_text_widget.tag_configure("r", foreground=t["red"])
            self.status_text_widget.tag_configure("gr", foreground=t["gray"])
        self._update_applied_labels()
        self._update_header_buttons()

    def _update_tk_widgets(self, t):
        def update_widget(w):
            try:
                cls = w.winfo_class()
                ff = getattr(w, "_fixed_fg", None)
                fg = t.get(ff, ff) if ff else None
                if cls in ("Frame", "Labelframe"):
                    w.configure(bg=t["bg"])
                elif cls == "Label":
                    w.configure(bg=t["bg"], fg=fg or t["fg"])
                elif cls == "Checkbutton":
                    w.configure(bg=t["bg"], fg=fg or t["fg"],
                                activebackground=t["bg"],
                                activeforeground=fg or t["fg"],
                                selectcolor=t["select_color"])
                elif cls == "Button":
                    if getattr(w, "_is_accent", False):
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
        if self._alive("terminal"):
            self.terminal.tag_configure("normal", foreground=t["terminal_fg"])
            self.terminal.tag_configure("success", foreground=t["green"])
            self.terminal.tag_configure("error", foreground=t["red"])
            self.terminal.tag_configure("warning", foreground=t["yellow"])
            self.terminal.tag_configure("info", foreground=t["blue"])
            self.terminal.tag_configure("highlight", foreground=t["orange"])

    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme()

    def toggle_lang(self):
        current = self.update_schedule.get()
        ru_vals = ("Отключено", "Ежедневно", "Еженедельно (суббота)",
                   "2 раза в месяц (1 и 15)", "Ежемесячно (1 число)")
        en_vals = ("Disabled", "Daily", "Weekly (Saturday)",
                   "Twice a month (1 & 15)", "Monthly (1st)")
        self.lang = "en" if self.lang == "ru" else "ru"
        if self.lang == "ru":
            self.update_schedule.set(dict(zip(en_vals, ru_vals)).get(current, current))
        else:
            self.update_schedule.set(dict(zip(ru_vals, en_vals)).get(current, current))
        self.rebuild_ui()

    def _update_header_buttons(self):
        if hasattr(self, "theme_button") and self.theme_button.winfo_exists():
            self.theme_button.config(
                text=self.t("theme_dark") if self.current_theme == "light"
                else self.t("theme_light"))
        if hasattr(self, "lang_button") and self.lang_button.winfo_exists():
            self.lang_button.config(text="EN" if self.lang == "ru" else "RU")

    def rebuild_ui(self):
        for w in self.root.winfo_children():
            w.destroy()
        for attr in ("terminal", "services_tree", "status_text_widget", "svc_detail",
                     "tune_canvas", "options_inner", "notebook", "run_button",
                     "theme_button", "lang_button", "services_count_label",
                     "schedule_label"):
            if hasattr(self, attr):
                try:
                    delattr(self, attr)
                except Exception:
                    pass
        self.option_widgets = {}
        self.applied_labels = {}
        self.mount_labels = {}
        self.steam_labels = {}
        self.create_ui()
        self.apply_hardware_restrictions()
        self.update_title()
        self._update_applied_labels()
        self.refresh_services()
        self.refresh_status()
        self.refresh_applied()

    # ─── UI ──
    def create_ui(self):
        self.root.title("System Tuneup v%s" % APP_VERSION)
        w = min(self._scaled(1060), self.screen_w - 10)
        h = min(self._scaled(800), self.screen_h - 80)
        self.root.geometry("%dx%d" % (w, h))
        self.root.minsize(min(self._scaled(880), self.screen_w - 10),
                          min(self._scaled(640), self.screen_h - 80))
        self.apply_theme()
        header = tk.Frame(self.root)
        header.pack(fill="x", padx=self._scaled(10), pady=(self._scaled(10), self._scaled(5)))
        self._fix(tk.Label(header, text="System Tuneup",
                           font=("DejaVu Sans", self._scaled(16), "bold")),
                  "green").pack(side="left")
        self._fix(tk.Label(header, text="v%s" % APP_VERSION,
                           font=("DejaVu Sans", self._scaled(9))),
                  "gray").pack(side="left", padx=(self._scaled(10), 0))
        self.theme_button = tk.Button(header, text="", command=self.toggle_theme,
                                      font=("DejaVu Sans", self._scaled(9)),
                                      padx=self._scaled(8), pady=self._scaled(2))
        self.theme_button.pack(side="right")
        self.lang_button = tk.Button(header, text="", command=self.toggle_lang,
                                     font=("DejaVu Sans", self._scaled(9), "bold"),
                                     padx=self._scaled(8), pady=self._scaled(2))
        self.lang_button.pack(side="right", padx=(0, self._scaled(6)))
        self._fix(tk.Checkbutton(header, text=self.t("lbl_dry"),
                                 variable=self.dry_run_var, command=self.update_title,
                                 font=("DejaVu Sans", self._scaled(9), "bold")),
                  "yellow").pack(side="right", padx=(0, self._scaled(10)))
        ttk.Separator(self.root, orient="horizontal").pack(fill="x",
                                                           padx=self._scaled(10),
                                                           pady=self._scaled(5))
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=self._scaled(10),
                           pady=self._scaled(5))
        self.tab_tuneup = ttk.Frame(self.notebook)
        self.tab_services = ttk.Frame(self.notebook)
        self.tab_status = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tuneup, text=self.t("tab_tune"))
        self.notebook.add(self.tab_services, text=self.t("tab_serv"))
        self.notebook.add(self.tab_status, text=self.t("tab_stat"))
        self.create_tuning_tab()
        self.create_services_tab()
        self.create_status_tab()
        buttons = tk.Frame(self.root)
        buttons.pack(fill="x", padx=self._scaled(10), pady=self._scaled(5))
        tk.Button(buttons, text=self.t("btn_help"), command=self.show_help,
                  font=("DejaVu Sans", self._scaled(10)),
                  padx=self._scaled(10), pady=self._scaled(6)).pack(
            side="right", padx=self._scaled(5))
        tk.Button(buttons, text=self.t("btn_export"), command=self.export_config,
                  font=("DejaVu Sans", self._scaled(10)),
                  padx=self._scaled(10), pady=self._scaled(6)).pack(
            side="right", padx=self._scaled(5))
        term_frame = tk.Frame(self.root)
        term_frame.pack(fill="both", expand=True, padx=self._scaled(10),
                        pady=(self._scaled(5), 0))
        self._fix(tk.Label(term_frame, text=self.t("lbl_terminal"),
                           font=("DejaVu Sans", self._scaled(8))),
                  "gray").pack(fill="x")
        term_lines = max(3, int((5 if self.screen_h < 700 else 10) * self.ui_scale))
        self.terminal = scrolledtext.ScrolledText(
            term_frame, height=term_lines, font=("DejaVu Sans Mono", self._scaled(9)),
            wrap="word", relief="sunken", bd=1, state="disabled")
        self.terminal.pack(fill="both", expand=True, pady=(self._scaled(2), 0))
        self._make_copyable(self.terminal)
        status_frame = tk.Frame(self.root)
        status_frame.pack(fill="x", padx=self._scaled(10),
                          pady=(self._scaled(2), self._scaled(10)))
        self.status_text = tk.StringVar(value=self.t("status_ready"))
        self._fix(tk.Label(status_frame, textvariable=self.status_text,
                           font=("DejaVu Sans", self._scaled(8))),
                  "gray").pack(side="left")
        self.progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100,
                        length=self._scaled(180),
                        mode="determinate").pack(side="right")
        self.apply_theme()

    # ─── wheel ──
    def _on_wheel(self, event):
        d = 0
        num = getattr(event, "num", None)
        if num == 4:
            d = -1
        elif num == 5:
            d = 1
        elif getattr(event, "delta", 0):
            d = -1 if event.delta > 0 else 1
        if d:
            self.tune_canvas.yview_scroll(d, "units")

    def _bind_wheel(self, widget):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(seq, self._on_wheel, add="+")
        for child in widget.winfo_children():
            self._bind_wheel(child)

    # ─── tabs ───
    def create_tuning_tab(self):
        container = tk.Frame(self.tab_tuneup)
        container.pack(fill="both", expand=True, padx=self._scaled(8),
                       pady=self._scaled(8))
        btns = tk.Frame(container)
        btns.pack(fill="x", pady=(0, self._scaled(6)))
        self.run_button = tk.Button(btns, text=self.t("btn_apply_sel"),
                                    command=self.apply_selected,
                                    font=("DejaVu Sans", self._scaled(10), "bold"),
                                    padx=self._scaled(14), pady=self._scaled(5))
        self.run_button._is_accent = True
        self.run_button.pack(side="left", padx=self._scaled(2))
        for key, cmd in (("btn_rollback", self.rollback_selected),
                         ("btn_selall_opt", self.select_all_options),
                         ("btn_selnone", self.reset_options)):
            tk.Button(btns, text=self.t(key), command=cmd,
                      font=("DejaVu Sans", self._scaled(9)),
                      padx=self._scaled(10), pady=self._scaled(5)).pack(
                side="left", padx=self._scaled(2))
        self.tune_canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical",
                                  command=self.tune_canvas.yview)
        self.tune_canvas.configure(yscrollcommand=scrollbar.set)
        self.options_inner = tk.Frame(self.tune_canvas)
        self.canvas_window = self.tune_canvas.create_window((0, 0),
                                                            window=self.options_inner,
                                                            anchor="nw")
        self.options_inner.bind("<Configure>",
                                lambda e: self.tune_canvas.configure(
                                    scrollregion=self.tune_canvas.bbox("all")))
        self.tune_canvas.bind("<Configure>",
                              lambda e: self.tune_canvas.itemconfig(
                                  self.canvas_window, width=e.width))
        self.tune_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        categories = {}
        for key in self.options:
            categories.setdefault(self.om(key)[2], []).append(key)
        order = CAT_ORDER[self.lang]
        cats = [c for c in order if c in categories]
        cats += [c for c in sorted(categories) if c not in order]
        disk_cat = self.om("ntfs3")[2]
        for cat in cats:
            self._fix(tk.Label(self.options_inner, text="─── %s ───" % cat,
                               font=("DejaVu Sans", self._scaled(10), "bold"),
                               anchor="w"), "yellow").pack(
                fill="x", pady=(self._scaled(10), self._scaled(3)))
            for key in categories[cat]:
                self.create_option_row(key)
            if cat == disk_cat:
                self.create_disk_extras()
        self._bind_wheel(self.tune_canvas)
        self._bind_wheel(self.options_inner)

    def create_option_row(self, key):
        label, desc, _cat, _short = self.om(key)
        row = tk.Frame(self.options_inner)
        row.pack(fill="x", pady=self._scaled(1))
        top = tk.Frame(row)
        top.pack(fill="x")
        cb = tk.Checkbutton(top, text=label, variable=self.options[key]["var"],
                            font=("DejaVu Sans", self._scaled(10)), anchor="w")
        cb.pack(side="left")
        self.option_widgets[key] = cb
        if key == "corectrl":
            self._fix(tk.Label(top, text=self.t("lbl_group"),
                               font=("DejaVu Sans", self._scaled(9))),
                      "gray").pack(side="left", padx=(self._scaled(12), self._scaled(2)))
            tk.Entry(top, textvariable=self.corectrl_group, width=14,
                     font=("DejaVu Sans", self._scaled(9))).pack(side="left")
        elif key == "swap":
            self._fix(tk.Label(top, text=self.t("lbl_value"),
                               font=("DejaVu Sans", self._scaled(9))),
                      "gray").pack(side="left", padx=(self._scaled(12), self._scaled(2)))
            tk.Entry(top, textvariable=self.swap_value, width=6,
                     font=("DejaVu Sans", self._scaled(9))).pack(side="left")
        elif key == "autoupdate":
            self._fix(tk.Label(top, text=self.t("lbl_schedule"),
                               font=("DejaVu Sans", self._scaled(9))),
                      "gray").pack(side="left", padx=(self._scaled(12), self._scaled(2)))
            ttk.Combobox(top, textvariable=self.update_schedule,
                         values=self._schedule_values(),
                         state="readonly", width=26,
                         font=("DejaVu Sans", self._scaled(9))).pack(side="left")
            self.schedule_label = self._fix(tk.Label(
                top, text=self.t("schedule_current") % self._current_schedule_text(),
                font=("DejaVu Sans", self._scaled(8))), "gray")
            self.schedule_label.pack(side="left", padx=(self._scaled(8), 0))
        ap = tk.Label(top, text="…", font=("DejaVu Sans", self._scaled(9), "bold"))
        ap.pack(side="left", padx=(self._scaled(12), 0))
        self.applied_labels[key] = ap
        tk.Button(top, text=self.t("btn_open_file"),
                  command=lambda k=key: self.open_option_file(k),
                  font=("DejaVu Sans", self._scaled(8)),
                  padx=self._scaled(6), pady=0).pack(
            side="left", padx=(self._scaled(8), 0))
        self._fix(tk.Label(row, text=desc, font=("DejaVu Sans", self._scaled(8)),
                           anchor="w", wraplength=self._scaled(760), justify="left"),
                  "gray").pack(fill="x", padx=(self._scaled(26), 0),
                               pady=(0, self._scaled(2)))

    def create_services_tab(self):
        container = tk.Frame(self.tab_services)
        container.pack(fill="both", expand=True, padx=self._scaled(8),
                       pady=self._scaled(8))
        btns = tk.Frame(container)
        btns.pack(fill="x", pady=(0, self._scaled(8)))
        for key, cmd in (("btn_selall_opt", self.select_all_services),
                         ("btn_selnone", self.clear_services_selection),
                         ("svc_off_sel", self.disable_selected),
                         ("svc_on_sel", self.enable_selected)):
            tk.Button(btns, text=self.t(key), command=cmd,
                      font=("DejaVu Sans", self._scaled(9)),
                      padx=self._scaled(10), pady=self._scaled(4)).pack(
                side="left", padx=self._scaled(2))
        tree_frame = tk.Frame(container)
        tree_frame.pack(fill="both", expand=True)
        self.services_tree = ttk.Treeview(tree_frame,
                                          columns=("name", "enabled", "active", "desc"),
                                          show="headings", selectmode="extended")
        self.services_tree.heading("name", text=self.t("svc_col_name"))
        self.services_tree.heading("enabled", text=self.t("svc_col_en"))
        self.services_tree.heading("active", text=self.t("svc_col_act"))
        self.services_tree.heading("desc", text=self.t("svc_col_desc"))
        self.services_tree.column("name", width=self._scaled(210), anchor="w", stretch=False)
        self.services_tree.column("enabled", width=self._scaled(160), anchor="w", stretch=False)
        self.services_tree.column("active", width=self._scaled(90), anchor="center", stretch=False)
        self.services_tree.column("desc", width=self._scaled(400), anchor="w", stretch=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical",
                                  command=self.services_tree.yview)
        self.services_tree.configure(yscrollcommand=scrollbar.set)
        self.services_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.services_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._fix(tk.Label(container, text=self.t("svc_detail_hint"),
                           font=("DejaVu Sans", self._scaled(8)), anchor="w"),
                  "gray").pack(fill="x", pady=(self._scaled(6), 0))
        self.svc_detail = tk.Text(container, height=3, wrap="word",
                                  font=("DejaVu Sans", self._scaled(9)),
                                  relief="flat", bd=0, state="disabled")
        self.svc_detail.pack(fill="x", pady=(self._scaled(2), 0))
        self._make_copyable(self.svc_detail)
        self.services_count_label = tk.Label(container,
                                             text=self.t("svc_count").format(n=0),
                                             font=("DejaVu Sans", self._scaled(8)))
        self._fix(self.services_count_label, "gray").pack(fill="x",
                                                          pady=(self._scaled(4), 0))

    def _on_tree_select(self, event=None):
        if not self._alive("svc_detail") or not self._alive("services_tree"):
            return
        items = self.services_tree.selection()
        parts = []
        for it in items[:3]:
            name = str(self.services_tree.item(it)["values"][0])
            desc = SERVICES_META.get(name, {}).get(self.lang, "")
            parts.append("%s — %s" % (name, desc))
        w = self.svc_detail
        w.configure(state="normal")
        w.delete("1.0", tk.END)
        w.insert("1.0", "\n".join(parts))
        w.configure(state="disabled")

    def create_status_tab(self):
        container = tk.Frame(self.tab_status)
        container.pack(fill="both", expand=True, padx=self._scaled(8),
                       pady=self._scaled(8))
        tk.Button(container, text=self.t("stat_refresh"), command=self.refresh_status,
                  font=("DejaVu Sans", self._scaled(9)),
                  padx=self._scaled(12), pady=self._scaled(5)).pack(
            anchor="w", pady=(0, self._scaled(8)))
        self.status_text_widget = scrolledtext.ScrolledText(
            container, font=("DejaVu Sans Mono", self._scaled(9)), state="disabled")
        self.status_text_widget.pack(fill="both", expand=True)
        self._make_copyable(self.status_text_widget)

    # ─── copy / menu ───
    def _copy_selection(self, w):
        try:
            sel = w.get("sel.first", "sel.last")
        except Exception:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(sel)

    def _copy_all(self, w):
        self.root.clipboard_clear()
        self.root.clipboard_append(w.get("1.0", "end-1c"))

    def _select_all_text(self, w):
        w.tag_add("sel", "1.0", "end-1c")

    def _copy_menu_hide(self, event=None):
        menu = self._copy_menu_shown
        if menu is not None:
            try:
                menu.unpost()
            except Exception:
                pass
            self._copy_menu_shown = None
        try:
            self.root.unbind_all("<Button-1>")
        except Exception:
            pass
        try:
            self.root.unbind_all("<Escape>")
        except Exception:
            pass

    def _copy_menu_click(self, event):
        if self._copy_menu_shown is None:
            return
        if event.widget == self._copy_menu_shown:
            return
        self._copy_menu_hide()

    def _make_copyable(self, w):
        menu = tk.Menu(self.root, tearoff=0, font=("DejaVu Sans", self._scaled(9)))

        def wrap(fn):
            def wrapper():
                self._copy_menu_hide()
                fn()
            return wrapper
        menu.add_command(label=self.t("menu_copy"),
                         command=wrap(lambda: self._copy_selection(w)))
        menu.add_command(label=self.t("menu_copy_all"),
                         command=wrap(lambda: self._copy_all(w)))
        menu.add_command(label=self.t("menu_select_all"),
                         command=wrap(lambda: self._select_all_text(w)))

        def on_key(event):
            self._copy_selection(w)
            return "break"

        def on_right(event):
            self._copy_menu_hide()
            self._copy_menu_shown = menu
            self.root.bind_all("<Button-1>", self._copy_menu_click, add="+")
            self.root.bind_all("<Escape>", self._copy_menu_hide, add="+")
            try:
                menu.post(event.x_root, event.y_root)
            except Exception:
                self._copy_menu_hide()
            return "break"
        for seq in ("<Control-c>", "<Control-C>", "<Control-Insert>"):
            w.bind(seq, on_key, add="+")
        w.bind("<Button-3>", on_right, add="+")

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

    # ─── applied detection ───
    def refresh_applied(self):
        threading.Thread(target=self._applied_worker, daemon=True).start()

    def _applied_worker(self):
        try:
            self.q.put(("applied", self.detect_applied()))
            self.q.put(("mount_applied", self.detect_mount_applied()))
            self.q.put(("steam_applied", self.detect_steam_applied()))
            self.q.put(("schedule", self._current_schedule_text()))
        except Exception:
            pass

    def _current_schedule_text(self):
        path = "/etc/systemd/system/biweekly-upgrade.timer"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return self.t("schedule_none")
        m = re.search(r"^\s*OnCalendar\s*=\s*(.+)$", content, re.M)
        if not m:
            return self.t("schedule_none")
        cal = m.group(1).strip()
        names = {
            "*-*-* 18:30:00": ("Ежедневно", "Daily"),
            "Sat 18:30:00": ("Еженедельно (суббота)", "Weekly (Saturday)"),
            "*-*-1,15 18:30:00": ("2 раза в месяц (1 и 15)", "Twice a month (1 & 15)"),
            "*-*-1 18:30:00": ("Ежемесячно (1 число)", "Monthly (1st)"),
        }
        pair = names.get(cal)
        if pair:
            cal = pair[0] if self.lang == "ru" else pair[1]
        return cal

    def _corectrl_found(self, ops=None):
        if ops is None:
            ops = SystemOps(self.sudo, self.state, lambda m, t="normal": None, True)
        for d in ("/etc/polkit-1/rules.d",
                  "/usr/share/polkit-1/rules.d",
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
            try:
                content = ops.read_file(p)
            except Exception:
                content = ""
            if content and "org.corectrl" in content:
                return True
        try:
            res = subprocess.run(
                ["pkcheck", "--action-id", "org.corectrl.helper.init",
                 "--process", str(os.getpid())],
                capture_output=True, timeout=5)
            if res.returncode == 0:
                return True
        except Exception:
            pass
        return False

    def detect_applied(self):
        ops = SystemOps(self.sudo, self.state, lambda m, t="normal": None, True)
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
                                   text=True, timeout=3)
                return r.stdout.strip() if r.returncode == 0 else ""
            except Exception:
                return ""
        pw_path = os.path.join(self.state.user_home, ".config", "pipewire",
                               "pipewire.conf.d", "10-sound.conf")
        return {
            "rsyslog": ops.service_enabled("rsyslog.service") in ("disabled", "masked"),
            "journald": bool(re.search(r"^\s*Storage\s*=\s*volatile\s*$", j, re.M)),
            "audit": "audit=0" in grub,
            "raid": "raid=noautodetect" in grub,
            "corectrl": self._corectrl_found(ops),
            "ppfeaturemask": "amdgpu.ppfeaturemask" in grub,
            "vrr": ops.path_exists("/etc/X11/xorg.conf.d/20-amdgpu.conf"),
            "radv": "RADV_PERFTEST=sam" in env,
            "pipewire": ops.path_exists(pw_path),
            "mesa": "MESA_SHADER_CACHE_MAX_SIZE=4G" in env,
            "swap": bool(swp) or "vm.swappiness" in sysc or sv("vm.swappiness") not in ("", "60"),
            "sysctl": bool(sysc) or (sv("vm.vfs_cache_pressure") == "50"
                                     and sv("kernel.numa_balancing") == "0"),
            "ntsync": self.state.ntsync or ops.path_exists("/etc/modules-load.d/ntsync.conf"),
            "ntfs3": bool(re.search(r"^\s*#\s*blacklist\s+ntfs3\s*$", mint, re.M)),
            "aliases": "system-tuneup" in bashrc,
            "autoupdate": ops.service_enabled("biweekly-upgrade.timer") == "enabled",
        }

    def detect_mount_applied(self):
        res = {}
        try:
            with open("/etc/fstab", "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            content = ""
        for it in self.mount_items:
            mp = it["mp"]
            ok = False
            for line in content.splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                parts = s.split()
                if len(parts) >= 4 and parts[1] == mp:
                    opts = parts[3].split(",")
                    ok = "noatime" in opts and "nodiratime" in opts
                    break
            res[mp] = ok
        return res

    def detect_steam_applied(self):
        res = {}
        for it in self.steam_items:
            dst = os.path.join(it["lib"], "compatdata")
            res[it["lib"]] = os.path.islink(dst)
        return res

    def _update_applied_labels(self):
        t = THEMES[self.current_theme]
        groups = ((self.applied_labels, self.applied),
                  (self.mount_labels, self.mount_applied),
                  (self.steam_labels, self.steam_applied))
        for labels, store in groups:
            for key, lbl in labels.items():
                if not lbl.winfo_exists():
                    continue
                val = store.get(key, False)
                lbl.configure(text=self.t("applied_yes") if val else self.t("applied_no"),
                              bg=t["bg"], fg=t["green"] if val else t["gray"])
                lbl._fixed_fg = "green" if val else "gray"

    # ─── queue ───
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
                    if not self._alive("terminal"):
                        continue
                    self.terminal.configure(state="normal")
                    self.terminal.insert(tk.END, item[1], item[2])
                    self.terminal.see(tk.END)
                    self.terminal.configure(state="disabled")
                elif kind == "statusbar":
                    if hasattr(self, "status_text"):
                        self.status_text.set(item[1])
                elif kind == "progress":
                    if hasattr(self, "progress_var"):
                        self.progress_var.set(item[1])
                elif kind == "running":
                    self.is_running = item[1]
                    if self._alive("run_button"):
                        self.run_button.config(state="disabled" if item[1] else "normal")
                elif kind == "applied":
                    self.applied = item[1]
                    self._update_applied_labels()
                elif kind == "mount_applied":
                    self.mount_applied = item[1]
                    self._update_applied_labels()
                elif kind == "steam_applied":
                    self.steam_applied = item[1]
                    self._update_applied_labels()
                elif kind == "schedule":
                    if self._alive("schedule_label"):
                        self.schedule_label.config(
                            text=self.t("schedule_current") % item[1])
                elif kind == "services_rows":
                    if not self._alive("services_tree"):
                        continue
                    for child in self.services_tree.get_children():
                        self.services_tree.delete(child)
                    for row in item[1]:
                        self.services_tree.insert("", "end", values=row[:4],
                                                  tags=(row[4],))
                    if self._alive("services_count_label"):
                        self.services_count_label.config(
                            text=self.t("svc_count").format(n=len(item[1])))
                elif kind == "status_lines":
                    if not self._alive("status_text_widget"):
                        continue
                    w = self.status_text_widget
                    w.configure(state="normal")
                    w.delete("1.0", tk.END)
                    for text, tag in item[1]:
                        w.insert(tk.END, text + "\n", tag)
                    w.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    # ─── actions ───
    def open_option_file(self, key):
        cands = [p.format(home=self.state.user_home)
                 for p in OPTION_FILES.get(key, [])]
        target = None
        for p in cands:
            if self._exists_any(p):
                target = p
                break
        if target is None and cands:
            if not self.sudo._sudo_cached():
                if not self.sudo.ensure():
                    return
            for p in cands:
                if self._exists_any(p):
                    target = p
                    break
        if target is None:
            if not cands:
                return
            messagebox.showinfo(self.t("msg_no_file_title"),
                                self.t("msg_no_file_text") + "\n" + "\n".join(cands))
            return
        ops = SystemOps(self.sudo, self.state, lambda m, t="normal": None, True)
        content = ops.read_file(target)
        if content is None:
            if not self.sudo.ensure():
                return
            content = ops.read_file(target) or ""
        self._show_viewer(target, content)

    def select_all_options(self):
        for k, o in self.options.items():
            w = self.option_widgets.get(k)
            if w and str(w.cget("state")) == "normal":
                o["var"].set(True)
        for it in self.mount_items:
            it["var"].set(True)
        for it in self.steam_items:
            it["var"].set(True)

    def reset_options(self):
        for o in self.options.values():
            o["var"].set(False)
        for it in self.mount_items:
            it["var"].set(False)
        for it in self.steam_items:
            it["var"].set(False)

    def select_all_services(self):
        if self._alive("services_tree"):
            self.services_tree.selection_set(self.services_tree.get_children())

    def clear_services_selection(self):
        if self._alive("services_tree"):
            self.services_tree.selection_remove(self.services_tree.selection())

    def apply_selected(self):
        if self.is_running:
            messagebox.showinfo(self.t("msg_run_title"), self.t("msg_run_text"))
            return
        selected = [k for k, o in self.options.items() if o["var"].get()]
        mount_sel = [it["mp"] for it in self.mount_items if it["var"].get()]
        steam_sel = [it["lib"] for it in self.steam_items if it["var"].get()]
        if not selected and not mount_sel and not steam_sel:
            messagebox.showwarning(self.t("msg_noopt_title"), self.t("msg_noopt_text"))
            return
        params = {"corectrl_group": self.corectrl_group.get(),
                  "swap_value": self.swap_value.get(),
                  "update_schedule": self.update_schedule.get()}
        dry_run = self.dry_run_var.get()
        if not dry_run and not self.sudo.ensure():
            self.log("Не удалось получить права sudo", "error")
            return
        self.is_running = True
        if self._alive("run_button"):
            self.run_button.config(state="disabled")
        self.q.put(("running", True))
        self.q.put(("progress", 0))
        self.q.put(("statusbar", self.t("status_running")))
        threading.Thread(target=self._apply_worker,
                         args=(selected, mount_sel, steam_sel, params, dry_run),
                         daemon=True).start()

    def _apply_worker(self, selected, mount_sel, steam_sel, params, dry_run):
        ops = SystemOps(self.sudo, self.state, self.log, dry_run)
        total = len(selected) + (1 if mount_sel else 0) + (1 if steam_sel else 0)
        done = 0
        self.log("=" * 60, "highlight")
        self.log("ЗАПУСК ТЮНИНГА", "highlight")
        self.log("=" * 60, "highlight")
        try:
            for key in selected:
                label = self.om(key)[0]
                self.log("→ %s" % label, "info")
                try:
                    getattr(ops, "apply_%s" % key)(params)
                except Exception as e:
                    self.log("Ошибка в %s: %s" % (label, e), "error")
                done += 1
                self.q.put(("progress", int(done / total * 90)))
            if mount_sel:
                self.log("→ %s" % self.t("mount_row_name"), "info")
                ops.apply_mount_opts(mount_sel)
                done += 1
                self.q.put(("progress", int(done / total * 90)))
            if steam_sel:
                self.log("→ %s" % self.t("steam_row_name"), "info")
                ops.apply_steam_links(steam_sel)
                done += 1
                self.q.put(("progress", int(done / total * 90)))
            if not dry_run:
                ops.finalize_grub()
            self.q.put(("progress", 100))
            self.q.put(("statusbar", self.t("status_done")))
            self.log("Все выбранные операции обработаны", "success")
        except Exception as e:
            self.log("Критическая ошибка: %s" % e, "error")
            self.q.put(("statusbar", self.t("status_error")))
        finally:
            self.q.put(("running", False))
            self.refresh_applied()
            self.refresh_status()
            self.refresh_services()

    def rollback_selected(self):
        if self.is_running:
            messagebox.showinfo(self.t("msg_run_title"), self.t("msg_run_text"))
            return
        selected = [k for k, o in self.options.items() if o["var"].get()]
        mount_sel = [it["mp"] for it in self.mount_items if it["var"].get()]
        steam_sel = [it["lib"] for it in self.steam_items if it["var"].get()]
        if not selected and not mount_sel and not steam_sel:
            messagebox.showwarning(self.t("msg_noopt_title"), self.t("msg_noopt_text"))
            return
        dry_run = self.dry_run_var.get()
        if not dry_run and not self.sudo.ensure():
            self.log("Не удалось получить права sudo", "error")
            return
        self.is_running = True
        if self._alive("run_button"):
            self.run_button.config(state="disabled")
        self.q.put(("running", True))
        self.q.put(("progress", 0))
        self.q.put(("statusbar", self.t("status_running")))
        threading.Thread(target=self._rollback_worker,
                         args=(selected, mount_sel, steam_sel, dry_run),
                         daemon=True).start()

    def _rollback_worker(self, selected, mount_sel, steam_sel, dry_run):
        ops = SystemOps(self.sudo, self.state, self.log, dry_run)
        total = len(selected) + (1 if mount_sel else 0) + (1 if steam_sel else 0)
        done = 0
        self.log("=" * 60, "highlight")
        self.log("ЗАПУСК ОТКАТА", "highlight")
        self.log("=" * 60, "highlight")
        try:
            for key in selected:
                label = self.om(key)[0]
                self.log("→ %s" % label, "info")
                try:
                    getattr(ops, "rollback_%s" % key)()
                except Exception as e:
                    self.log("Ошибка в %s: %s" % (label, e), "error")
                done += 1
                self.q.put(("progress", int(done / total * 90)))
            if mount_sel:
                self.log("→ %s" % self.t("mount_row_name"), "info")
                ops.rollback_mount_opts(mount_sel)
                done += 1
                self.q.put(("progress", int(done / total * 90)))
            if steam_sel:
                self.log("→ %s" % self.t("steam_row_name"), "info")
                ops.rollback_steam_links(steam_sel)
                done += 1
                self.q.put(("progress", int(done / total * 90)))
            if not dry_run:
                ops.finalize_grub()
            self.q.put(("progress", 100))
            self.q.put(("statusbar", self.t("status_done")))
            self.log("Откат завершён", "success")
        except Exception as e:
            self.log("Критическая ошибка: %s" % e, "error")
            self.q.put(("statusbar", self.t("status_error")))
        finally:
            self.q.put(("running", False))
            self.refresh_applied()
            self.refresh_status()
            self.refresh_services()

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
        title = "System Tuneup v%s" % APP_VERSION
        if self.dry_run_var.get():
            title += " [DRY RUN]"
        self.root.title(title)

    def export_config(self):
        selected = [k for k, o in self.options.items() if o["var"].get()]
        if not selected:
            messagebox.showinfo(self.t("btn_export"), self.t("msg_noopt_text"))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", initialdir=os.path.expanduser("~"),
            filetypes=[("Text files", "*.txt")], title=self.t("btn_export"))
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("System Tuneup v%s\n" % APP_VERSION)
                f.write("Date: %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
                for k in selected:
                    f.write("%s: %s\n" % (k, self.om(k)[0]))
            self.log("Конфигурация сохранена: %s" % path, "success")
        except Exception as e:
            messagebox.showerror(self.t("status_error"), str(e))

    def show_help(self):
        win = tk.Toplevel(self.root)
        win.title(self.t("help_title"))
        win.geometry("%dx%d" % (min(self._scaled(700), self.screen_w - 20),
                                min(self._scaled(600), self.screen_h - 40)))
        t = THEMES[self.current_theme]
        win.configure(bg=t["bg"])
        text = scrolledtext.ScrolledText(win, font=("DejaVu Sans Mono", self._scaled(9)),
                                         bg=t["terminal_bg"], fg=t["terminal_fg"],
                                         wrap="word", relief="flat",
                                         padx=self._scaled(10), pady=self._scaled(10))
        text.pack(fill="both", expand=True)
        text.tag_configure("title", foreground=t["green"],
                           font=("DejaVu Sans Mono", self._scaled(13), "bold"))
        text.tag_configure("author", foreground=t["yellow"],
                           font=("DejaVu Sans Mono", self._scaled(10), "bold"))
        text.tag_configure("sep", foreground=t["gray"])
        text.insert("1.0", "System Tuneup GUI\n", "title")
        text.insert(tk.END, "%s: %s\n" % (self.t("about_version"), APP_VERSION))
        text.insert(tk.END, "%s\n" % self.t("about_purpose"))
        text.insert(tk.END, "─" * 60 + "\n", "sep")
        text.insert(tk.END, "%s: " % self.t("about_author"), "author")
        text.insert(tk.END, "%s\n" % self.t("about_author_name"), "author")
        text.insert(tk.END, "─" * 60 + "\n\n" % (), "sep")
        text.insert(tk.END, self.t("help"))
        text.configure(state="disabled")
        self._make_copyable(text)

    # ─── services ───
    def refresh_services(self):
        threading.Thread(target=self._refresh_services_worker, daemon=True).start()

    def _refresh_services_worker(self):
        ops = SystemOps(self.sudo, self.state, lambda m, t="normal": None,
                        self.dry_run_var.get())
        rows = []
        for name in SERVICES_ORDER:
            desc = SERVICES_META[name][self.lang]
            if not ops.unit_exists(name):
                rows.append((name, self.t("svc_na"), self.t("svc_na"), desc, "gr"))
                continue
            enabled = ops.service_enabled(name)
            active = ops.service_active(name)
            if enabled == "masked":
                en_d, tag = self.t("svc_masked"), "r"
            elif enabled == "disabled":
                en_d, tag = self.t("svc_off"), "gr"
            elif active == "active":
                en_d, tag = self.t("svc_on"), "g"
            else:
                en_d, tag = self.t("svc_onoff"), "y"
            act_d = self.t("run_yes") if active == "active" else self.t("run_no")
            rows.append((name, en_d, act_d, desc, tag))
        self.q.put(("services_rows", rows))

    def _ensure_service_action(self):
        if self.dry_run_var.get():
            return True
        return self.sudo.ensure()

    def enable_selected(self):
        if self.is_running:
            messagebox.showinfo(self.t("msg_run_title"), self.t("msg_run_text"))
            return
        items = self.services_tree.selection()
        if not items:
            messagebox.showinfo(self.t("msg_sel_title"), self.t("msg_sel_text"))
            return
        names = [str(self.services_tree.item(i)["values"][0]) for i in items]
        if not self._ensure_service_action():
            return
        threading.Thread(target=self._enable_worker, args=(names,), daemon=True).start()

    def _enable_worker(self, names):
        ops = SystemOps(self.sudo, self.state, self.log, self.dry_run_var.get())
        for name in names:
            if ops.dry_run:
                ops.log("[DRY RUN] enable %s" % name, "warning")
                continue
            ok = ops.sudo_run(["systemctl", "unmask", name], ignore_error=True)
            ok2 = ops.sudo_run(["systemctl", "enable", name], ignore_error=True)
            if ok or ok2:
                ops.log("✓ %s включена" % name, "success")
            else:
                ops.log("Не удалось включить %s" % name, "warning")
        self.refresh_services()

    def disable_selected(self):
        if self.is_running:
            messagebox.showinfo(self.t("msg_run_title"), self.t("msg_run_text"))
            return
        items = self.services_tree.selection()
        if not items:
            messagebox.showinfo(self.t("msg_sel_title"), self.t("msg_sel_text"))
            return
        names = [str(self.services_tree.item(i)["values"][0]) for i in items]
        if not self._ensure_service_action():
            return
        threading.Thread(target=self._disable_worker, args=(names,), daemon=True).start()

    def _disable_worker(self, names):
        ops = SystemOps(self.sudo, self.state, self.log, self.dry_run_var.get())
        for name in names:
            if ops.dry_run:
                ops.log("[DRY RUN] disable %s" % name, "warning")
                continue
            ok = ops.sudo_run(["systemctl", "disable", "--now", name], ignore_error=True)
            if name.startswith("avahi"):
                ok_mask = ops.sudo_run(["systemctl", "mask", name], ignore_error=True)
                ok = ok or ok_mask
            if ok:
                ops.log("✓ %s отключена" % name, "success")
            else:
                ops.log("Не удалось отключить %s" % name, "warning")
        self.refresh_services()

    # ─── status ───
    def refresh_status(self):
        threading.Thread(target=self._refresh_status_worker, daemon=True).start()

    def _refresh_status_worker(self):
        ops = SystemOps(self.sudo, self.state, lambda m, t="normal": None, True)
        try:
            A = self.detect_applied()
            self.q.put(("applied", A))
        except Exception:
            A = self.applied
        rows = []
        rows.append((self.t("st_hw"), "head"))
        rows.append(("%s: %s" % (self.t("st_os_lbl"), self._os_pretty()), "info"))
        gpu_line = self.state.gpu
        if self.state.gpu_model:
            gpu_line += " %s" % self.state.gpu_model
        rows.append(("%s: %s" % (self.t("st_gpu_lbl"), gpu_line), "info"))
        rows.append(("%s: %dx%d" % (self.t("st_screen_lbl"),
                                    self.screen_w, self.screen_h), "info"))
        ram = ram_total_gb()
        if ram is not None:
            rows.append(("%s: %.1f %s" % (self.t("st_ram_lbl"), ram,
                                          self.t("gb")), "info"))
        if self._home_separate():
            disk_pairs = (("/", "st_disk_lbl"),
                          (self.state.user_home, "st_disk_home"))
        else:
            disk_pairs = (("/", "st_disk_both"),)
        for path, lbl_key in disk_pairs:
            info = self._disk_info(path)
            if info:
                total, free = info
                rows.append(("%s: %.1f %s, %s %.1f %s"
                             % (self.t(lbl_key), total, self.t("gb"),
                                self.t("free_word"), free, self.t("gb")), "info"))
        if self.state.has_swap:
            type_names = {"file": self.t("swap_file"),
                          "partition": self.t("swap_part"),
                          "zram": "zram"}
            swap_val = type_names.get(self.state.swap_type, self.state.swap_type)
            sz = self._swap_size_gb()
            if sz is not None and sz > 0:
                swap_val += ", %.1f %s" % (sz, self.t("gb"))
        else:
            swap_val = self.t("no_swap")
        rows.append(("%s: %s" % (self.t("st_swap_lbl"), swap_val), "info"))
        rows.append(("%s: %s" % (self.t("st_kernel_lbl"), os.uname().release), "info"))
        rows.append(("%s: %s" % (self.t("st_de_lbl"), desktop_name()), "info"))
        rows.append(("RAID: %s" % (self.t("w_yes") if self.state.has_raid
                                   else self.t("w_no")), "info"))
        rows.append(("ntsync: %s" % (self.t("w_yes") if self.state.ntsync
                                     else self.t("w_no")), "info"))
        rows.append(("%s: %s" % (self.t("user_note"), self.state.user_name), "info"))
        rows.append(("%s: %s" % (self.t("home_note"), self.state.user_home), "info"))
        rows.append(("", "info"))
        rows.append((self.t("st_tweaks"), "head"))
        for key in self.options:
            label, _d, _c, short = self.om(key)
            ok = A.get(key, False)
            mark = self.t("yes") if ok else self.t("no")
            rows.append(("%s%s%s" % (self._col(label), mark.ljust(16), short),
                         "ok" if ok else "no"))
        for it in self.mount_items:
            ok = self.mount_applied.get(it["mp"], False)
            mark = self.t("yes") if ok else self.t("no")
            rows.append(("%s%s%s" % (self._col(self.t("mount_row_name")),
                                     mark.ljust(16), it["mp"]),
                         "ok" if ok else "no"))
        for it in self.steam_items:
            ok = self.steam_applied.get(it["lib"], False)
            mark = self.t("yes") if ok else self.t("no")
            rows.append(("%s%s%s" % (self._col(self.t("steam_row_name")),
                                     mark.ljust(16), it["lib"]),
                         "ok" if ok else "no"))
        rows.append(("", "info"))
        rows.append((self.t("st_services"), "head"))
        for name in SERVICES_ORDER:
            enabled = ops.service_enabled(name)
            active = ops.service_active(name)
            if enabled == "masked":
                tag, word = "r", self.t("svc_masked")
            elif enabled == "disabled":
                tag, word = "gr", self.t("svc_off")
            elif enabled == "not-found":
                tag, word = "gr", self.t("svc_na")
            elif active == "active":
                tag, word = "ok", self.t("svc_on")
            else:
                tag, word = "warn", self.t("svc_onoff")
            desc = SERVICES_META.get(name, {}).get(self.lang, "")
            rows.append(("  %s: %s — %s" % (name, word, desc), tag))
        rows.append(("", "info"))
        rows.append((self.t("st_kernel"), "head"))
        for p in ("vm.swappiness", "vm.vfs_cache_pressure", "kernel.numa_balancing"):
            try:
                r = subprocess.run(["sysctl", "-n", p], capture_output=True,
                                   text=True, timeout=3)
                val = r.stdout.strip() if r.returncode == 0 else "n/a"
            except Exception:
                val = "n/a"
            rows.append(("  %s = %s" % (p, val), "info"))
        rows.append(("", "info"))
        timer = ops.service_enabled("biweekly-upgrade.timer")
        rows.append(("%s: %s" % (self.t("st_timer"), self._fmt_state(timer)),
                     "ok" if timer == "enabled" else "gr"))
        self.q.put(("status_lines", rows))

    def on_closing(self):
        if self.is_running:
            if not messagebox.askyesno(self.t("msg_run_title"), self.t("msg_run_text")):
                return
        self.root.destroy()


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("System Tuneup GUI v%s\n  python3 tuneup_gui.py [--dry-run]" % APP_VERSION)
        sys.exit(0)
    root = tk.Tk()
    app = TuneupApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
