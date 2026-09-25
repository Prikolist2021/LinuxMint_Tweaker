#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Linux Tweaker v0.6.0
Графическая оболочка тюнинга Linux Mint / Ubuntu / Debian на Tkinter.
RU/EN, светлая/тёмная тема, детект применённых настроек,
откат, бэкапы, mount-опции, симлинки compatdata для Steam,
вкладка «Приложения» для удаления ненужных пакетов.

Лицензия: MIT

────────────────────────────────────────────────────────────────────────────
Структура файла (24 блока):

   1.  Импорты и константы
   2.  Темы (THEMES)
   3.  Метаданные твиков (OPTIONS_META)
   4.  Метаданные служб (CAT_ORDER, SERVICES_META, SERVICES_HELP)
   5.  Справки по твикам (OPTIONS_HELP)
   6.  Пути и строки UI (OPTION_FILES, STR)
   7.  Утилиты
   8.  SudoManager
   9.  SystemState
  10.  SystemOps: база (файлы, бэкапы, sudo_run)
  11.  SystemOps: GRUB и базовые твики
  12.  SystemOps: GPU, память, сеть
  13.  SystemOps: fstab, Steam, aliases, apps, удаление
  14.  SystemOps: rollback
  15.  MainWindow: ядро и хелперы (детекты)
  16.  MainWindow: UI-каркас
  17.  MainWindow: вкладка Приложения
  18.  MainWindow: прокрутка, копирование, темы
  19.  MainWindow: службы
  20.  MainWindow: бейджи и ZFS
  21.  MainWindow: apply / rollback / выбор
  22.  MainWindow: статус
  23.  MainWindow: диалоги и закрытие
  24.  Точка входа (main)

Поиск по файлу: Ctrl+F → "# БЛОК N".
────────────────────────────────────────────────────────────────────────────
"""

# ============================================================================
# БЛОК 1. ИМПОРТЫ И КОНСТАНТЫ
# ============================================================================

import sys
import os
import re
import subprocess
import time
import shutil
import glob
import fnmatch
import pwd
import grp
import threading
import traceback
import queue
import fcntl
from datetime import datetime

from tkinter import (Tk, Toplevel, Frame, Label, Button, Checkbutton, Entry,
                     Text, Canvas, Menu, StringVar, BooleanVar,
                     END, NORMAL, DISABLED, LEFT, RIGHT, TOP, BOTTOM,
                     X, Y, BOTH, NW, W, E, N, S, HORIZONTAL, VERTICAL,
                     SUNKEN, RAISED, FLAT, GROOVE, RIDGE, CENTER,
                     messagebox, simpledialog, PhotoImage)
from tkinter import ttk, scrolledtext


APP_NAME = "Linux Tweaker"
APP_VERSION = "0.6.0"
APP_BUILD_DATE = "19.09.2026"
GITHUB_URL = "https://github.com/Prikolist2021/LinuxMint_Tweaker"
LICENSE_NAME = "MIT"

# Файловые системы
COMMIT_OK_FS = {"ext2", "ext3", "ext4"}

# Файловые системы, для которых имеет смысл отключать fsck (pass=0)
NOFSCK_OK_FS = {"ext2", "ext3", "ext4", "xfs", "btrfs", "f2fs"}

# Значения антенны для Realtek
REALTEK_ANT_VALUES = ["default", "1", "2"]

# Блокировка запуска
LOCK_FILE = "~/.linux-tweaker.lock"

# Лимит областей памяти (vm.max_map_count)
MAX_MAP_COUNT_VALUES = ["65530", "524288", "1048576", "2147483642"]
MAX_MAP_COUNT_DEFAULT = "1048576"

# Валидация значений твиков
COMMIT_MIN = 1
COMMIT_MAX = 3600
COMMIT_DEFAULT = "60"

SWAPPINESS_MIN = 0
SWAPPINESS_MAX = 200
SWAPPINESS_DEFAULT_DISK = "10"
SWAPPINESS_DEFAULT_ZRAM = "150"

TMPFS_SIZE_DEFAULT = "512M"
TMPFS_SIZE_REGEX = r"[0-9]+[MmGgKk]?"

# Таймауты для sudo-команд (в секундах)
SUDO_TIMEOUT_DEFAULT = 180
SUDO_TIMEOUT_APT = 900
SUDO_TIMEOUT_GRUB = 300
SUDO_TIMEOUT_INITRAMFS = 600

# Таймауты для быстрых утилит (в секундах)
TIMEOUT_QUICK = 5
TIMEOUT_DPKG_QUERY = 60
TIMEOUT_APT_SIMULATE = 60
TIMEOUT_PKG_SIZE = 30

# Бэкапы: сколько последних версий файла хранить
BACKUP_KEEP_LAST = 1

# Быстрое выключение (systemd timeout)
SHUTDOWN_TIMEOUT_VALUES = ["5s", "8s", "10s", "15s", "20s", "30s", "45s", "60s"]
SHUTDOWN_TIMEOUT_DEFAULT = "8s"
SHUTDOWN_TIMEOUT_SYSTEM_DEFAULT = "90s"

# PipeWire: пресеты буферов
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

# Категории приложений (вкладка «Приложения»)
APPS_CATEGORY_ORDER = {
    "ru": ["Офис", "Графика", "Интернет", "Мультимедиа",
           "Игры", "Утилиты", "Прочее"],
    "en": ["Office", "Graphics", "Internet", "Multimedia",
           "Games", "Utilities", "Other"],
}

# Маски системных пакетов (защита от удаления)
SYSTEM_PACKAGE_MASKS = (
    "mint-meta-", "ubuntu-desktop", "xubuntu-", "kubuntu-",
    "lubuntu-", "cinnamon", "mate-desktop", "xfce4",
    "gnome-shell", "ubuntu-minimal", "ubuntu-standard",
)

# Пути ZFS-юнитов (для маскирования)
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

# ============================================================================
# БЛОК 2. ТЕМЫ (THEMES)
# ============================================================================

THEMES = {
    "light": {
        "bg": "#f5f5f5", "panel": "#ffffff", "fg": "#1e1e1e", "gray": "#616161",
        "border": "#d0d0d0", "tab": "#e4e4e4", "tab_hover": "#d8d8d8",
        "accent": "#2e9e83", "accent2": "#268a72", "accent_fg": "#ffffff",
        "button": "#e4e4e4", "button_hover": "#d8d8d8", "button_dis": "#ececec",
        "fg_dis": "#9a9a9a", "entry": "#ffffff", "terminal": "#ffffff",
        "terminal_fg": "#1e1e1e", "sel": "#cde4f7", "scroll": "#b0b0b0",
        "row_hover": "#ececec", "green": "#2e7d32", "green_bg": "#e2f0e3",
        "gray_bg": "#e8e8e8", "red": "#c62828", "yellow": "#b26a00",
        "blue": "#1565c0", "orange": "#e65100",
    },
    "dark": {
        "bg": "#1e1e1e", "panel": "#252526", "fg": "#d4d4d4", "gray": "#9a9a9a",
        "border": "#3c3c3c", "tab": "#2d2d30", "tab_hover": "#38383d",
        "accent": "#4ec9b0", "accent2": "#3aa794", "accent_fg": "#10201c",
        "button": "#3a3d41", "button_hover": "#46494e", "button_dis": "#2d2d30",
        "fg_dis": "#6a6a6a", "entry": "#333333", "terminal": "#0c0c0c",
        "terminal_fg": "#d4d4d4", "sel": "#094771", "scroll": "#5a5a5a",
        "row_hover": "#2a2d2e", "green": "#4ec9b0", "green_bg": "#17352f",
        "gray_bg": "#2f2f2f", "red": "#f44747", "yellow": "#d7ba7d",
        "blue": "#569cd6", "orange": "#ce9178",
    },
}


# ============================================================================
# БЛОК 3. МЕТАДАННЫЕ ТВИКОВ (OPTIONS_META)
# ============================================================================
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
    "rtl_msi": {
        "ru": ("Realtek Wi-Fi: MSI и антенна",
               "Фикс для Wi-Fi-модулей Realtek (rtl8723ae, rtl8723be, "
               "rtl8188ee и подобных): переключает прерывания в режим MSI "
               "(msi=1) и при необходимости выбирает антенну (ant_sel=1 или 2). "
               "Помогает при обрывах связи, низкой скорости и «пропадании» "
               "Wi-Fi. Твик доступен только если в системе найден подходящий "
               "модуль Realtek. Нужна перезагрузка.",
               "Сеть", "Wi-Fi Realtek: MSI и антенна"),
        "en": ("Realtek Wi-Fi: MSI and antenna",
               "Fix for Realtek Wi-Fi modules (rtl8723ae, rtl8723be, "
               "rtl8188ee and similar): switches interrupts to MSI mode "
               "(msi=1) and optionally selects the antenna (ant_sel=1 or 2). "
               "Helps with connection drops, low speed and “disappearing” "
               "Wi-Fi. The tweak is only available if a matching Realtek "
               "module is found. Needs reboot.",
               "Network", "Realtek Wi-Fi: MSI and antenna")},
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
    "nofsck": {
        "ru": ("Отключить проверку дисков (fsck)",
               "Выставляет в /etc/fstab последнее поле (pass) в 0 — "
               "fsck для раздела при загрузке не запускается. Загрузка "
               "быстрее, диск меньше изнашивается. Применяется к ext2/ext3/ext4, "
               "xfs, btrfs, f2fs. Для btrfs и xfs это рекомендованный режим: "
               "их fsck — заглушка, а целостность проверяется через scrub "
               "во время работы. Для NTFS, FAT32 и exFAT параметр бесполезен "
               "(проверка делается средствами Windows) — такие разделы твикер "
               "пропускает. НЕ отключайте для корневого раздела ext*, если "
               "бывали сбои питания. Нужна перезагрузка.",
               "Диски и файловые системы", "проверка дисков при загрузке"),
        "en": ("Disable disk check (fsck)",
               "Sets the last field (pass) in /etc/fstab to 0 — fsck is not "
               "run for the partition at boot. Boot is faster, the disk wears "
               "less. Applies to ext2/ext3/ext4, xfs, btrfs, f2fs. For btrfs "
               "and xfs this is the recommended mode: their fsck is a no-op, "
               "and integrity is checked via scrub at runtime. For NTFS, "
               "FAT32 and exFAT the parameter is useless (the check is done "
               "by Windows) — the tweaker skips such partitions. Do NOT "
               "disable for the root ext* partition if you have had power "
               "failures. Needs reboot.",
               "Drives & filesystems", "disk check at boot")},
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

# ============================================================================
# БЛОК 4. МЕТАДАННЫЕ СЛУЖБ (CAT_ORDER, SERVICES_META, SERVICES_HELP)
# ============================================================================

# Порядок категорий на вкладке «Тюнинг»
CAT_ORDER = {
    "ru": ["Видеокарта и графика", "Ядро и загрузка", "Логи системы", "Звук",
           "Сеть", "Память и swap", "Диски и файловые системы",
           "Игры и совместимость", "Удобство", "Обновления"],
    "en": ["GPU & graphics", "Kernel & boot", "System logs", "Sound", "Network",
           "Memory & swap", "Drives & filesystems", "Gaming & compatibility",
           "Convenience", "Updates"],
}

# Описания служб (вкладка «Службы»)
SERVICES_META = {
    "avahi-daemon.service": {
        "ru": "Поиск устройств в домашней сети: принтеров, телевизоров, Chromecast. Не нужен, если у вас нет сетевого принтера.",
        "en": "Finds devices on your home network: printers, TVs, Chromecast. Not needed without a network printer."},
    "avahi-daemon.socket": {
        "ru": "Сокет, который будит службу avahi при обращении из сети. Сам по себе бесполезен без службы avahi.",
        "en": "Socket that wakes the avahi service on network request. Useless on its own without the avahi service."},
    "bluetooth.service": {
        "ru": "Служба Bluetooth: беспроводные мыши, клавиатуры, наушники, геймпады, файлообмен. Не отключайте, если пользуетесь Bluetooth-устройствами.",
        "en": "Bluetooth service: wireless mice, keyboards, headphones, gamepads, file transfer. Do not disable if you use Bluetooth devices."},
    "cups-browsed.service": {
        "ru": "Ищет сетевые принтеры автоматически. Не нужен, если принтера нет или он подключён по USB.",
        "en": "Auto-discovers network printers. Not needed without a printer or with a USB printer."},
    "cups.service": {
        "ru": "Печать и сканирование. Не нужно, если у вас нет принтера или сканера.",
        "en": "Printing and scanning. Not needed without a printer or scanner."},
    "cups.socket": {
        "ru": "Сокет, который будит службу печати при обращении. Сам по себе бесполезен без службы cups.",
        "en": "Socket that wakes the print service on request. Useless on its own without the cups service."},
    "ModemManager.service": {
        "ru": "Работа с мобильными модемами через USB или сим-карту. Не нужна, если интернет по Wi-Fi или кабелю.",
        "en": "Handles mobile modems via USB or SIM. Not needed if internet is Wi-Fi or cable."},
    "openvpn.service": {
        "ru": "Встроенный VPN-сервер. Не нужен, если вы не поднимаете собственный VPN.",
        "en": "Built-in VPN server. Not needed unless you run your own VPN."},
    "lvm2-monitor.service": {
        "ru": "Следит за объединением дисков в один большой (LVM). Не нужен при обычной установке Mint/Ubuntu.",
        "en": "Watches disks joined into one big volume (LVM). Not needed on a standard Mint/Ubuntu install."},
    "switcheroo-control.service": {
        "ru": "Переключает встроенную и отдельную графику на ноутбуках. Не нужен на настольном ПК.",
        "en": "Switches integrated and discrete graphics on laptops. Not needed on a desktop."},
    "touchegg.service": {
        "ru": "Распознаёт жесты тачпада и сенсора. Не нужен на настольном ПК без сенсора.",
        "en": "Recognizes touchpad and touchscreen gestures. Not needed on a desktop without a touchscreen."},
    "zfs-zed.service": {
        "ru": "Следит за дисковыми массивами ZFS и предупреждает о проблемах. Не нужен без ZFS.",
        "en": "Watches ZFS disk arrays and warns on problems. Not needed without ZFS."},
    "kerneloops.service": {
        "ru": "Отправляет разработчикам отчёты о сбоях ядра. На домашнем ПК это лишняя нагрузка и трафик.",
        "en": "Sends kernel crash reports to developers. On a home PC this is extra load and traffic."},
    "rsyslog.service": {
        "ru": "Пишет подробные журналы системы на диск. Отключение экономит место и уменьшает износ SSD; важные сообщения остаются в журнале systemd.",
        "en": "Writes detailed system logs to disk. Disabling saves space and reduces SSD wear; important messages remain in the systemd journal."},
    "apt-daily.timer": {
        "ru": "Ежедневно скачивает списки пакетов и обновления в фоне. Если вы включили автообновления в твикере, этот таймер глушится автоматически.",
        "en": "Downloads package lists and updates daily in the background. If you enable auto-updates in the tweaker, this timer is masked automatically."},
    "apt-daily-upgrade.timer": {
        "ru": "Ежедневно устанавливает обновления в фоне. Может конфликтовать с автообновлениями твикера. Глушится автоматически при их включении.",
        "en": "Installs updates daily in the background. May conflict with the tweaker's auto-updates. Masked automatically when they are enabled."},
    "unattended-upgrades.service": {
        "ru": "Устанавливает обновления безопасности автоматически. Если вы управляете обновлениями сами, служба не нужна.",
        "en": "Installs security updates automatically. If you manage updates yourself, the service is not needed."},
    "apport.service": {
        "ru": "Собирает краш-репорты (отчёты о падениях программ) и предлагает отправить их разработчикам. На домашнем ПК не нужна: только занимает место в /var/crash и показывает всплывающие окна при падении приложений.",
        "en": "Collects crash reports (reports about program crashes) and offers to send them to developers. Not needed on a home PC: only fills /var/crash and shows popups when apps crash."},
}

SERVICES_ORDER = list(SERVICES_META.keys())

# Подробные справки по службам (по кнопке «?»)
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

# ============================================================================
# БЛОК 5. СПРАВКИ ПО ТВИКАМ (OPTIONS_HELP)
# ============================================================================
# Подробные тексты для кнопки «?» у каждого твика.

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
    "rtl_msi": {
        "ru": "Модули Wi-Fi Realtek (rtl8723ae, rtl8723be, rtl8188ee, rtl8192ce и другие) часто страдают от обрывов связи, низкой скорости и «пропадания» сети. Это связано с тем, как драйвер обрабатывает прерывания и выбирает антенну.\n\nДва параметра решают большинство проблем:\n\n• msi=1 — включает режим MSI (Message Signaled Interrupts). Убирает конфликты прерываний с другими устройствами и часто лечит обрывы связи.\n\n• ant_sel=1 или ant_sel=2 — выбирает активную антенну. На ноутбуках с двумя антеннами (main и aux) драйвер по умолчанию может использовать неправильную, из-за чего сигнал слабый. Переключение на другую антенну часто кардинально улучшает приём.\n\nЗначение ant_sel=default означает «не трогать антенну», применять только msi=1.\n\nТвик создаёт файл /etc/modprobe.d/rtlwifi-tweaker.conf с нужными параметрами. Модуль перезагружается только после перезагрузки системы.\n\nТвик доступен только если в системе реально найден один из поддерживаемых модулей Realtek. Проверить можно командой: lsmod | grep rtl.",
        "en": "Realtek Wi-Fi modules (rtl8723ae, rtl8723be, rtl8188ee, rtl8192ce and others) often suffer from connection drops, low speed and “disappearing” network. This is due to how the driver handles interrupts and selects the antenna.\n\nTwo parameters solve most problems:\n\n• msi=1 — enables MSI (Message Signaled Interrupts). Removes interrupt conflicts with other devices and often cures connection drops.\n\n• ant_sel=1 or ant_sel=2 — selects the active antenna. On laptops with two antennas (main and aux) the driver may use the wrong one by default, making the signal weak. Switching to the other antenna often dramatically improves reception.\n\nant_sel=default means “do not touch the antenna”, apply only msi=1.\n\nThe tweak creates /etc/modprobe.d/rtlwifi-tweaker.conf with the needed parameters. The module reloads only after a system reboot.\n\nThe tweak is available only if one of the supported Realtek modules is actually found. Check with: lsmod | grep rtl.",
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
    "nofsck": {
        "ru": "В /etc/fstab у каждой строки есть два числа в конце: dump и pass.\n\n"
              "• dump — резервное копирование (почти всегда 0, не трогаем).\n"
              "• pass — порядок проверки ФС при загрузке:\n"
              "    0 — не проверять,\n"
              "    1 — проверить первым (корневой раздел),\n"
              "    2 — проверить после корня (остальные разделы).\n\n"
              "Этот твик ставит pass=0 для подходящих разделов — "
              "fsck для них не запускается.\n\n"
              "К каким ФС применяется и почему:\n\n"
              "• ext2, ext3, ext4 — да. Проверка бывает долгой и обычно "
              "не нужна. Оговорка: для корневого раздела ext4 при частых "
              "сбоях питания лучше оставить pass=1.\n\n"
              "• btrfs — да, и это рекомендованный режим. fsck.btrfs — "
              "заглушка (no-op): она существует только для совместимости "
              "с fstab и ничего не делает. Целостность Btrfs проверяется "
              "встроенными механизмами во время работы: контрольные суммы "
              "блоков, самовосстановление из зеркал, команда btrfs scrub "
              "для онлайн-проверки. Опасная btrfs check --repair не "
              "запускается автоматически, поэтому отключение pass ничего "
              "не ломает.\n\n"
              "• xfs — да. fsck.xfs — тоже заглушка, для XFS "
              "рекомендуется pass=0.\n\n"
              "• f2fs — да. ФС рассчитана на работу без регулярной проверки.\n\n"
              "• NTFS, FAT32, exFAT — твикер пропускает. Поле pass "
              "технически записать можно, но Linux проверку этих ФС "
              "не делает — она выполняется средствами Windows (chkdsk). "
              "Отключать нечего.\n\n"
              "Когда НЕ отключать:\n"
              "• корневой раздел ext* на машине, которая бывала "
              "в сбоях питания или с ошибками ФС — fsck помогает "
              "восстановить структуру;\n"
              "• если вы не уверены в состоянии диска (проверьте "
              "сначала smartctl -a).\n\n"
              "Изменения записываются в /etc/fstab и вступают в силу "
              "после перезагрузки. Откат возвращает pass=1 для корня "
              "и pass=2 для остальных разделов.",
        "en": "In /etc/fstab every line ends with two numbers: dump and pass.\n\n"
              "• dump — backup flag (almost always 0, we leave it alone).\n"
              "• pass — filesystem check order at boot:\n"
              "    0 — do not check,\n"
              "    1 — check first (root partition),\n"
              "    2 — check after root (other partitions).\n\n"
              "This tweak sets pass=0 for suitable partitions — "
              "fsck is not run for them.\n\n"
              "Which filesystems it applies to and why:\n\n"
              "• ext2, ext3, ext4 — yes. The check can be slow and is "
              "usually not needed. Caveat: for the root ext4 partition on "
              "a machine with frequent power failures, better keep pass=1.\n\n"
              "• btrfs — yes, and this is the recommended mode. fsck.btrfs "
              "is a no-op: it exists only for fstab compatibility and does "
              "nothing. Btrfs integrity is checked by built-in mechanisms "
              "at runtime: block checksums, self-healing from mirrors, and "
              "btrfs scrub for online verification. The dangerous "
              "btrfs check --repair is not run automatically, so disabling "
              "pass breaks nothing.\n\n"
              "• xfs — yes. fsck.xfs is also a no-op, pass=0 is "
              "recommended for XFS.\n\n"
              "• f2fs — yes. The filesystem is designed to run without "
              "regular checks.\n\n"
              "• NTFS, FAT32, exFAT — the tweaker skips them. pass can "
              "technically be written, but Linux does not run the check "
              "for these filesystems — it is done by Windows (chkdsk). "
              "There is nothing to disable.\n\n"
              "When NOT to disable:\n"
              "• the root ext* partition on a machine that has had power "
              "failures or filesystem errors — fsck helps restore "
              "the structure;\n"
              "• if you are unsure about the disk health (check with "
              "smartctl -a first).\n\n"
              "Changes are written to /etc/fstab and take effect after "
              "a reboot. Rollback restores pass=1 for root and pass=2 "
              "for the rest.",
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

# ============================================================================
# БЛОК 6. ПУТИ И СТРОКИ UI (OPTION_FILES, STR)
# ============================================================================

# Пути к файлам, которые правят твики (для кнопки «файл»)
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
    "rtl_msi": ["/etc/modprobe.d/rtlwifi-tweaker.conf"],
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
    "nofsck": ["/etc/fstab"],
    "tmpfs_tmp": ["/etc/fstab"],
    "aliases": ["{home}/.bashrc"],
    "autoupdate": ["/etc/systemd/system/biweekly-upgrade.timer",
                   "/etc/systemd/system/biweekly-upgrade.service"],
}


# Строки интерфейса (RU/EN)
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
        "lbl_show_only_unapplied": "Показать неприменённые",
        "search_no_results": "Ничего не найдено по запросу «%s».",
        "lbl_group": "Группа:", "lbl_value": "Значение:",
        "lbl_schedule": "Расписание:", "lbl_mode": "Режим:",
        "ready": "Готово", "running": "Выполнение...", "done": "Готово",
        "applied_yes": "✓ применено", "applied_no": "не применено",
        "applied_manual": "применено (изменён вручную)",
        "applied_unknown": "неизвестно",
        "btn_file": "файл", "btn_q": "?",
        "btn_check_status": "проверить",
        "btn_remove_zfs": "Удалить пакеты (осторожно)",
        "btn_remove_zfs_unavailable": "Удалить пакеты (недоступно)",
        "menu_copy": "Копировать", "menu_copy_all": "Копировать всё",
        "menu_select_all": "Выделить всё",
        "svc_name": "Служба", "svc_state": "Состояние", "svc_run": "Запуск",
        "svc_desc": "Описание", "svc_help": "?",
        "svc_hint": "Клик по первой колонке — отметить службу; клик по заголовку — сортировка; «?» — подробности.",
        "svc_on": "работает", "svc_onoff": "не запущена",
        "svc_off": "остановлена", "svc_masked": "заблокирована",
        "svc_na": "нет в системе",
        "run_yes": "работает", "run_no": "остановлена",
        "svc_on_sel": "Включить выбранные", "svc_off_sel": "Отключить выбранные",
        "svc_col_sel": "✓",
        "sort_asc": "▲", "sort_desc": "▼",
        "svc_hdr_name": "Служба", "svc_hdr_state": "Состояние",
        "svc_hdr_desc": "Описание",
        "stat_refresh": "Обновить статус",
        "st_hw": "ИНФОРМАЦИЯ О СИСТЕМЕ", "st_parts": "РАЗДЕЛЫ СИСТЕМЫ",
        "st_tweaks": "ТВИКИ", "st_services": "СЛУЖБЫ",
        "st_kernel": "ПАРАМЕТРЫ ЯДРА",
        "st_timer": "Таймер автообновлений",
        "st_enabled": "включён", "st_disabled": "отключён",
        "st_masked": "заблокирован", "st_notfound": "не найден",
        "part_dev": "Устройство", "part_mount": "Точка монтирования",
        "part_fs": "ФС", "part_total": "Всего", "part_free": "Свободно",
        "os_lbl": "ОС", "gpu_lbl": "Видеокарта",
        "screen_lbl": "Разрешение экрана",
        "swap_lbl": "Файл подкачки", "kernel_lbl": "Ядро",
        "de_lbl": "Оболочка", "ram_lbl": "ОЗУ", "cpu_lbl": "Процессор",
        "disk_lbl": "Диск", "driver_lbl": "Драйвер видеокарты",
        "user_lbl": "Пользователь", "home_lbl": "Домашняя папка",
        "hz": "Гц", "ram_hint": "(тип и частота — после ввода sudo)",
        "w_yes": "да", "w_no": "нет", "no_swap": "отсутствует",
        "gb": "ГБ", "free_w": "свободно", "swap_file": "файл",
        "swap_part": "раздел",
        "yes": "ПРИМЕНЕНО", "no": "НЕ ПРИМЕНЕНО",
        "unknown": "НЕИЗВЕСТНО",
        "sched_cur": "Текущее: %s", "sched_none": "не настроено",
        "mount_title": "Диски: параметры монтирования",
        "mount_desc": "Добавит опцию noatime в /etc/fstab (меньше служебных обращений к диску, полезно для SSD и NTFS; noatime покрывает и каталоги). Вступает в силу после перезагрузки.",
        "steam_title": "Steam: симлинки compatdata",
        "steam_desc": "Создаст ссылку compatdata на ~/.steam/steam/steamapps/compatdata для библиотек Steam на NTFS-разделах, чтобы игры видели данные Proton/Wine из домашней папки.",
        "mount_short": "параметры монтирования",
        "steam_short": "симлинк compatdata",
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
        "viewer": "Просмотр файла",
        "viewer_ext": "Открыть во внешнем редакторе",
        "about_title": "О твикере",
        "about_purpose": "Графическая оболочка тюнинга для Linux Mint / Ubuntu / Debian и других systemd-дистрибутивов: твики производительности, логов, дисков, сети и игр с откатом и бэкапами.",
        "about_author": "Автор", "about_author_name": "Дмитрий Свистунов",
        "about_ver": "Версия", "about_license": "Лицензия",
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
        "result_text": "%d применено / %d пропущено / %d ошибок",
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
        "reason_no_rtl": "нет подходящих модулей Realtek",
        "rtl_default": "По умолчанию",
        "rtl_ant_1": "Антенна 1 (ant_sel=1)",
        "rtl_ant_2": "Антенна 2 (ant_sel=2)",
        "fsck_title": "Диски: отключение проверки при загрузке",
        "fsck_desc": (
            "Устанавливает последнее поле (pass) в /etc/fstab в 0, чтобы "
            "не запускать проверку файловой системы при загрузке. В первую "
            "очередь безопасно для btrfs и xfs (их fsck — заглушка, "
            "целостность проверяется через scrub). Для ext2/ext3/ext4 "
            "отключайте обдуманно: после сбоя питания быстрая проверка "
            "может быть полезной. Для NTFS/FAT/exFAT параметр бесполезен. "
            "Вступает в силу после перезагрузки."
        ),
        "fsck_short": "отключение проверки дисков",
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
        "apps_group_hint": " (удалится группой)",
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
        "lbl_show_only_unapplied": "Only not applied",
        "search_no_results": "Nothing found for query “%s”.",
        "lbl_group": "Group:", "lbl_value": "Value:",
        "lbl_schedule": "Schedule:", "lbl_mode": "Mode:",
        "ready": "Ready", "running": "Running...", "done": "Done",
        "applied_yes": "✓ applied", "applied_no": "not applied",
        "applied_manual": "applied (modified manually)",
        "applied_unknown": "unknown",
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
        "st_tweaks": "TWEAKS", "st_services": "SERVICES",
        "st_kernel": "KERNEL PARAMETERS",
        "st_timer": "Auto-update timer",
        "st_enabled": "enabled", "st_disabled": "disabled",
        "st_masked": "blocked", "st_notfound": "not found",
        "part_dev": "Device", "part_mount": "Mount point",
        "part_fs": "FS", "part_total": "Total", "part_free": "Free",
        "os_lbl": "OS", "gpu_lbl": "GPU",
        "screen_lbl": "Screen resolution",
        "swap_lbl": "Swap", "kernel_lbl": "Kernel",
        "de_lbl": "Desktop", "ram_lbl": "RAM", "cpu_lbl": "CPU",
        "disk_lbl": "Disk", "driver_lbl": "GPU driver",
        "user_lbl": "User", "home_lbl": "Home folder",
        "hz": "Hz", "ram_hint": "(type & speed after sudo)",
        "w_yes": "yes", "w_no": "no", "no_swap": "none",
        "gb": "GB", "free_w": "free", "swap_file": "file",
        "swap_part": "partition",
        "yes": "APPLIED", "no": "NOT APPLIED",
        "unknown": "UNKNOWN",
        "sched_cur": "Current: %s", "sched_none": "not configured",
        "mount_title": "Disks: mount options",
        "mount_desc": "Adds the noatime option to /etc/fstab entries (less disk wear; noatime already covers directories). Takes effect after reboot.",
        "steam_title": "Steam: compatdata symlinks",
        "steam_desc": "Creates a compatdata symlink to ~/.steam/steam/steamapps/compatdata for Steam libraries on NTFS partitions so games can see Proton/Wine data from the home folder.",
        "mount_short": "mount options",
        "steam_short": "compatdata symlink",
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
        "viewer": "File viewer",
        "viewer_ext": "Open in external editor",
        "about_title": "About",
        "about_purpose": "A graphical tuning shell for Linux Mint / Ubuntu / Debian and other systemd distributions: performance, logs, disk, network and gaming tweaks with rollback and backups.",
        "about_author": "Author", "about_author_name": "Dmitry Svistunov",
        "about_ver": "Version", "about_license": "License",
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
        "result_text": "%d applied / %d skipped / %d failed",
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
        "reason_no_rtl": "no supported Realtek module",
        "rtl_default": "Default",
        "rtl_ant_1": "Antenna 1 (ant_sel=1)",
        "rtl_ant_2": "Antenna 2 (ant_sel=2)",
        "fsck_title": "Disks: disable boot filesystem check",
        "fsck_desc": (
            "Sets the last field (pass) in /etc/fstab to 0 so the filesystem "
            "check is not started at boot. It is primarily safe for btrfs and "
            "xfs (their fsck is a no-op, integrity is verified via scrub). "
            "For ext2/ext3/ext4 disable thoughtfully: after a power failure "
            "a boot check can be useful. For NTFS/FAT/exFAT the parameter is "
            "meaningless. Takes effect after reboot."
        ),
        "fsck_short": "disable disk check",
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
        "apps_group_hint": " (group removal)",
    },
}


# Импорт списка приложений из внешнего tweaker_packages.py
try:
    from tweaker_packages import REMOVABLE_PACKAGES
except ImportError:
    try:
        _here = os.path.dirname(os.path.abspath(__file__))
        if _here not in sys.path:
            sys.path.insert(0, _here)
        from tweaker_packages import REMOVABLE_PACKAGES
    except ImportError:
        REMOVABLE_PACKAGES = {}

if not isinstance(REMOVABLE_PACKAGES, dict):
    REMOVABLE_PACKAGES = {}

# ============================================================================
# ДОПОЛНИТЕЛЬНЫЕ ПАКЕТЫ ДЛЯ ВКЛАДКИ «ПРИЛОЖЕНИЯ»
# ============================================================================
ADDITIONAL_REMOVABLE_PACKAGES = {
    "libreoffice-*": {
        "ru": (
            "LibreOffice (все компоненты)",
            "Удаляет сразу все установленные пакеты LibreOffice по маске libreoffice-*.",
            "Офис",
            True
        ),
        "en": (
            "LibreOffice (all components)",
            "Removes all installed LibreOffice packages matching libreoffice-*.",
            "Office",
            True
        ),
    },
    "onboard": {
        "ru": (
            "OnBoard",
            "Экранная клавиатура. Не нужна, если вы не пользуетесь сенсорным вводом или специальными возможностями.",
            "Утилиты",
            False
        ),
        "en": (
            "OnBoard",
            "On-screen keyboard. Not needed unless you use touch input or accessibility.",
            "Utilities",
            False
        ),
    },
    "mintchat": {
        "ru": (
            "Matrix (чат Linux Mint)",
            "Встроенный клиент Matrix для доступа к чату поддержки Linux Mint. "
            "Это веб-обёртка над Element. Можно удалить, если не пользуетесь.",
            "Интернет",
            False
        ),
        "en": (
            "Matrix (Linux Mint chat)",
            "Built-in Matrix client for the Linux Mint support chat. "
            "It is a web wrapper around Element. Can be removed if unused.",
            "Internet",
            False
        ),
    },
}

for _k, _v in ADDITIONAL_REMOVABLE_PACKAGES.items():
    REMOVABLE_PACKAGES.setdefault(_k, _v)
# ============================================================================
# БЛОК 7. УТИЛИТЫ
# ============================================================================

def compute_ui_scale(root):
    """Возвращает коэффициент масштабирования UI (0.75 – 1.0)."""
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    sx = sw / 1100.0
    sy = sh / 800.0
    return max(0.75, min(sx, sy, 1.0))


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
    """Модель процессора из /proc/cpuinfo."""
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "?"


def ram_total_gb():
    """Общий объём ОЗУ в ГБ (float) или None."""
    try:
        with open("/proc/meminfo", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    return int(line.split()[1]) / 1024.0 / 1024.0
    except Exception:
        pass
    return None


def desktop_name():
    """Имя рабочей среды (Cinnamon, GNOME, XFCE и т.д.)."""
    d = (os.environ.get("XDG_CURRENT_DESKTOP", "") + " " +
         os.environ.get("DESKTOP_SESSION", "")).lower()
    for key, name in [("cinnamon", "Cinnamon"), ("xfce", "XFCE"),
                      ("mate", "MATE"), ("plasma", "KDE Plasma"),
                      ("kde", "KDE Plasma"), ("gnome", "GNOME"),
                      ("lxqt", "LXQt"), ("lxde", "LXDE"),
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
        with open("/etc/os-release", "r", encoding="utf-8",
                  errors="replace") as f:
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


def _is_removable_device(dev):
    """True, если устройство съёмное (usb-флешка, внешний диск)."""
    try:
        base = os.path.basename(dev)
        m = re.match(r"^(sd[a-z]+|hd[a-z]+|vd[a-z]+|nvme\d+n\d+|mmcblk\d+)",
                     base)
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


def parse_mounts():
    """Список {dev, mp, fstype} для смонтированных физических разделов."""
    items = []
    try:
        with open("/proc/mounts", "r", encoding="utf-8",
                  errors="replace") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 4:
                    continue
                dev, mp, fstype, opts = parts[0], parts[1], parts[2], parts[3]
                mp = unescape_fstab_token(mp)
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


def find_steam_libraries(user_home):
    """Список путей к steamapps/ найденных библиотек Steam."""
    libs = []
    for vdf in (os.path.join(user_home, ".steam", "steam", "steamapps",
                             "libraryfolders.vdf"),
                os.path.join(user_home, ".local", "share", "Steam",
                             "steamapps", "libraryfolders.vdf")):
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


def fs_supports_commit(fstype):
    """True, если ФС поддерживает параметр commit= (ext2/3/4)."""
    return (fstype or "").lower() in COMMIT_OK_FS


def fs_supports_nofsck(fstype):
    """True, если ФС имеет смысл отключать fsck (pass=0)."""
    return (fstype or "").lower() in NOFSCK_OK_FS


def format_size(bytes_val):
    """Формат '500.0 GB' для статуса."""
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
    """Компактный размер: '500G', '2.0T', '128M'."""
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
        with open("/etc/default/grub", "r", encoding="utf-8",
                  errors="replace") as f:
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
    """True, если ZFS реально используется."""
    try:
        r = subprocess.run(["zpool", "list", "-H", "-o", "name"],
                           capture_output=True, text=True,
                           timeout=TIMEOUT_QUICK)
        if r.returncode == 0 and r.stdout.strip():
            return True
    except Exception:
        pass
    try:
        r = subprocess.run(["findmnt", "-t", "zfs", "-n", "-o", "TARGET"],
                           capture_output=True, text=True,
                           timeout=TIMEOUT_QUICK)
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


def tmpfs_tmp_mounted():
    """True, если /tmp сейчас смонтирован как tmpfs."""
    try:
        with open("/proc/mounts", "r", encoding="utf-8",
                  errors="replace") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3 and parts[1] == "/tmp" \
                        and parts[2] == "tmpfs":
                    return True
    except Exception:
        pass
    return False


def fstab_has_tmp_tmpfs():
    """True, если /tmp tmpfs прописан в /etc/fstab."""
    try:
        with open("/etc/fstab", "r", encoding="utf-8",
                  errors="replace") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                parts = s.split()
                if len(parts) >= 3 and parts[1] == "/tmp" \
                        and parts[2] == "tmpfs":
                    return True
    except Exception:
        pass
    return False


def installed_packages_set():
    """Возвращает set установленных пакетов."""
    try:
        r = subprocess.run(["dpkg-query", "-W",
                            "-f=${Package}\t${Status}\n"],
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
    """Оценка размера пакетов на диске."""
    if not pkgs:
        return "0 B"
    try:
        r = subprocess.run(["dpkg-query", "-W",
                            "-f=${Installed-Size}\n"] + pkgs,
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


def unescape_fstab_token(s):
    """Раскодирует спец-последовательности fstab."""
    return (s or "") \
        .replace("\\040", " ") \
        .replace("\\011", "\t") \
        .replace("\\012", "\n") \
        .replace("\\134", "\\")


def escape_fstab_token(s):
    """Кодирует пробелы и служебные символы для fstab."""
    return (s or "") \
        .replace("\\", "\\\\") \
        .replace(" ", "\\040") \
        .replace("\t", "\\011") \
        .replace("\n", "\\012")


def expand_package_pattern(pkgs, installed=None):
    """Раскрывает пакеты с масками, например libreoffice-*."""
    if not pkgs:
        return []
    if installed is None:
        installed = installed_packages_set()

    out = []
    for p in pkgs:
        if not p:
            continue
        if any(ch in p for ch in "*?["):
            try:
                rx = re.compile(fnmatch.translate(p))
            except Exception:
                continue
            for ip in installed:
                if any(ch in ip for ch in "*?["):
                    continue
                if rx.match(ip):
                    out.append(ip)
        else:
            out.append(p)
    return sorted(set(out))


def rtl_wifi_fix_candidates():
    """
    Возвращает dict:
      { "rtl8723ae": {"msi": True, "ant_sel": True}, ... }
    только для загруженных Realtek-модулей с подходящими параметрами.
    """
    caps = {}
    try:
        with open("/proc/modules", "r", encoding="utf-8",
                  errors="replace") as f:
            loaded = [ln.split()[0] for ln in f if ln.strip()]
    except Exception:
        loaded = []

    for mod in loaded:
        if not re.match(r"^rtl8[0-9a-z]+$", mod):
            continue

        has_msi = os.path.exists("/sys/module/%s/parameters/msi" % mod)
        has_ant = os.path.exists("/sys/module/%s/parameters/ant_sel" % mod)

        if not (has_msi or has_ant):
            try:
                r = subprocess.run(
                    ["modinfo", "-F", "parm", mod],
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_QUICK
                )
                parm = r.stdout or ""
                if re.search(r"\bmsi\b", parm):
                    has_msi = True
                if re.search(r"\bant_sel\b", parm):
                    has_ant = True
            except Exception:
                pass

        if has_msi or has_ant:
            caps[mod] = {"msi": has_msi, "ant_sel": has_ant}

    return caps


def apt_dry_run_purge(pkgs):
    """apt-get -s purge. Возвращает (explicit, deps, system_hits, ok)."""
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


# ============================================================================
# БЛОК 8. SUDOMANAGER
# ============================================================================

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
            password = (self.prompt_password(attempt)
                        if self.prompt_password else None)
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
        """Запускает команду через sudo. log — необязательный коллбэк."""
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
                              env=run_env, capture_output=True,
                              timeout=timeout)

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


# ============================================================================
# БЛОК 9. SYSTEMSTATE
# ============================================================================

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
        self.rtl_wifi_caps = {}
        self.rtl_wifi_modules = []

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
                if ("vga" in line or "3d controller" in line
                        or "display controller" in line):
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

        # Realtek Wi-Fi
        self.rtl_wifi_caps = rtl_wifi_fix_candidates()
        self.rtl_wifi_modules = sorted(self.rtl_wifi_caps.keys())

    def _detect_swap(self):
        """Определяет наличие swap и его тип."""
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
                if pw.pw_uid >= 1000 and pw.pw_name not in ("nobody",
                                                            "nfsnobody"):
                    if os.path.isdir(pw.pw_dir) \
                            and pw.pw_dir.startswith("/home/"):
                        return pw.pw_name
            for pw in pwd.getpwall():
                if pw.pw_uid >= 1000 and pw.pw_name not in ("nobody",
                                                            "nfsnobody"):
                    return pw.pw_name
        except Exception:
            pass
        return "root"


# ============================================================================
# БЛОК 10. SYSTEMMOPS: БАЗА (файлы, бэкапы, sudo_run)
# ============================================================================

class SystemOps:
    """Все системные операции с бэкапами и откатами."""

    # Список юнитов apt-daily / unattended-upgrades для маскировки
    APT_DAILY_UNITS = [
        "apt-daily.timer",
        "apt-daily-upgrade.timer",
        "apt-daily.service",
        "apt-daily-upgrade.service",
        "unattended-upgrades.service",
        "mintupdate-automation-upgrade.timer",
        "mintupdate-automation-upgrade.service",
    ]

    def __init__(self, sudo, state, log, dry_run):
        self.sudo = sudo
        self.state = state
        self.log = log
        self.dry_run = dry_run
        self.grub_changed = False
        self.mount_items = []
        self.commit_targets = []
        self.backup_dir = os.path.join(state.user_home,
                                       "system-tuneup-backups")

    # ─── Бэкапы ─────────────────────────────────────────────────────────

    def _safe_backup_name(self, path):
        """Возвращает имя бэкапа с timestamp."""
        safe = path.lstrip("/").replace("/", "_")
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        return "%s.%s.bak" % (safe, ts)

    def _prune_backups(self, path):
        """Оставляет только последние BACKUP_KEEP_LAST бэкапов."""
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
                self.log("[WARN] cannot read %s for backup" % path,
                         "warning")
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
        """Читает файл (через sudo cat или напрямую)."""
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

    def atomic_write(self, path, content, chmod="644", owner=None,
                     mkdir=False):
        """Пишет во временный файл и атомарно перемещает."""
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
                                 err_msg="Cannot move %s -> %s"
                                 % (tmp, path)):
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


# ============================================================================
# БЛОК 11. SYSTEMMOPS: GRUB И БАЗОВЫЕ ТВИКИ
# ============================================================================

    @staticmethod
    def _grub_key(param):
        """Возвращает ключ параметра ядра (до '=')."""
        return param.split("=")[0]

    def add_grub_params(self, params):
        """Добавляет параметры в GRUB. Заменяет старые значения по ключу."""
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
                kept = [p for p in old_parts
                        if self._grub_key(p) not in keys]
                new_parts = kept + list(params)
                new_line = ('GRUB_CMDLINE_LINUX_DEFAULT="' +
                            " ".join(new_parts) + '"')
                if old_parts != new_parts:
                    changed = True
                lines.append(new_line)
            else:
                lines.append(line)
        if not found:
            lines.append('GRUB_CMDLINE_LINUX_DEFAULT="' +
                         " ".join(params) + '"')
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
                kept = [p for p in old_parts
                        if self._grub_key(p) != key]
                new_parts = kept + [token]
                new_line = ('GRUB_CMDLINE_LINUX_DEFAULT="' +
                            " ".join(new_parts) + '"')
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
        if not self.write_file(path, "\n".join(new_lines) + "\n",
                               backup=True):
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
                and re.search(r"^\s*RuntimeMaxUse\s*=\s*50M\s*$",
                              content, re.M)):
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
            out = ["[Journal]", "Storage=volatile",
                   "RuntimeMaxUse=50M"] + out
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
        if not self.write_file(path, "\n".join(new_lines) + "\n",
                               backup=True):
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
        if not self.write_file(path, "\n".join(new_lines) + "\n",
                               backup=True):
            return False
        self.sudo_run(["systemctl", "daemon-reexec"], ignore_error=True)
        self.log("✓ shutdown timeout reset to 90s", "success")
        return True


# ============================================================================
# БЛОК 12. SYSTEMMOPS: GPU, ПАМЯТЬ, СЕТЬ
# ============================================================================

    # ─── ZFS ────────────────────────────────────────────────────────────

    def apply_zfs_services(self, params=None):
        if self.dry_run:
            for u in ZFS_UNITS:
                self.log("[DRY RUN] systemctl disable --now %s" % u,
                         "warning")
                self.log("[DRY RUN] systemctl mask %s" % u, "warning")
            return True
        ok_any = False
        for u in ZFS_UNITS:
            if not self.unit_exists(u):
                continue
            self.sudo_run(["systemctl", "disable", "--now", u],
                          ignore_error=True)
            if self.sudo_run(["systemctl", "mask", u],
                             ignore_error=True):
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
            self.log("[DRY RUN] apt purge zfs-zed zfsutils-linux",
                     "warning")
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
            self.log("update-initramfs failed after ZFS removal",
                     "warning")
        if not self.sudo_run(["update-grub"], ignore_error=True,
                             timeout=SUDO_TIMEOUT_GRUB):
            self.log("update-grub failed after ZFS removal", "warning")
        self.log("✓ ZFS packages removed", "success")
        return True

    def rollback_zfs_remove_packages(self, params=None):
        self.log("Rollback of ZFS package removal is not supported. "
                 "Run 'sudo apt install zfsutils-linux' manually.",
                 "warning")
        return False

    # ─── GPU: CoreCtrl ──────────────────────────────────────────────────

    def _polkit_is_new(self):
        """True, если polkit поддерживает новый формат правил (.rules)."""
        try:
            res = subprocess.run(["pkaction", "--version"],
                                 capture_output=True, text=True,
                                 timeout=TIMEOUT_QUICK)
            m = re.search(r"(\d+)\.(\d+)",
                          (res.stdout or "") + (res.stderr or ""))
            if m:
                return int(m.group(1)) > 0 or int(m.group(2)) >= 106
        except Exception:
            pass
        return os.path.isdir("/etc/polkit-1/rules.d")

    def apply_corectrl(self, params=None):
        params = params or {}
        group = params.get("corectrl_group",
                           "").strip() or self.state.user_name
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", group):
            self.log("Bad group name: %s" % group, "error")
            return False
        if self.dry_run:
            self.log("[DRY RUN] CoreCtrl polkit rule for %s" % group,
                     "warning")
            return True
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
            content = ("[User permissions]\n"
                       "Identity=unix-group:" + group + "\n"
                       "Action=org.corectrl.*\nResultActive=yes\n")
            path = ("/etc/polkit-1/localauthority/50-local.d/"
                    "90-corectrl.pkla")
        if self.write_file(path, content, chmod="644", mkdir=True):
            pdir = os.path.dirname(path)
            if pdir and os.path.isdir(pdir):
                self.sudo_run(["chmod", "755", pdir], ignore_error=True)
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
        content = ('Section "Device"\n    Identifier "AMD"\n'
                   '    Driver "amdgpu"\n'
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
        preset_key = params.get("pipewire_preset",
                                PIPEWIRE_PRESET_DEFAULT)
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

    def rollback_pipewire(self, params=None):
        path = os.path.join(self.state.user_home, ".config", "pipewire",
                            "pipewire.conf.d", "10-sound.conf")
        self.remove_user_file(path)
        self.log("✓ PipeWire config removed", "success")
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
            self.log("tcp_bbr module not available in this kernel",
                     "warning")
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

    def rollback_bbr(self, params=None):
        self._rm("/etc/sysctl.d/99-bbr.conf")
        self.sudo_run(["sysctl", "-w",
                       "net.ipv4.tcp_congestion_control=cubic"],
                      ignore_error=True)
        self.sudo_run(["sysctl", "-w",
                       "net.core.default_qdisc=pfifo_fast"],
                      ignore_error=True)
        self.log("✓ BBR and fq reverted", "success")
        return True

    # ─── Сеть: Realtek Wi-Fi fix ────────────────────────────────────────

    def apply_rtl_msi(self, params=None):
        params = params or {}
        ant = str(params.get("rtl_ant_sel", "default")).strip()
        if ant not in REALTEK_ANT_VALUES:
            ant = "default"

        caps = rtl_wifi_fix_candidates() or getattr(
            self.state, "rtl_wifi_caps", {})
        if not caps:
            self.log("No suitable Realtek modules found", "warning")
            return None

        lines = ["# Created by Linux Tweaker"]
        any_line = False

        for mod in sorted(caps):
            c = caps[mod]
            opts = []
            if c.get("msi"):
                opts.append("msi=1")
            if ant in ("1", "2") and c.get("ant_sel"):
                opts.append("ant_sel=%s" % ant)
            if opts:
                lines.append("options %s %s" % (mod, " ".join(opts)))
                any_line = True

        if not any_line:
            self.log("No supported Realtek module options to write",
                     "warning")
            return None

        content = "\n".join(lines) + "\n"
        if not self.write_file("/etc/modprobe.d/rtlwifi-tweaker.conf",
                               content, chmod="644", mkdir=True):
            return False
        self.log("✓ Realtek Wi-Fi fix written (reboot to apply)",
                 "success")
        return True

    def rollback_rtl_msi(self, params=None):
        self._rm("/etc/modprobe.d/rtlwifi-tweaker.conf")
        self.log("✓ Realtek Wi-Fi fix removed", "success")
        return True

    # ─── Память: swap ───────────────────────────────────────────────────

    def apply_swap(self, params=None):
        params = params or {}
        if not self.state.has_swap:
            self.log("No swap found, skipping", "warning")
            return None
        val = params.get("swap_value", "").strip()
        if not val:
            val = (SWAPPINESS_DEFAULT_ZRAM
                   if self.state.swap_type == "zram"
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

    def rollback_swap(self, params=None):
        self._rm("/etc/sysctl.d/99-gaming-swap.conf")
        self.log("✓ swappiness: file removed; live value reverts "
                 "to stock after reboot", "success")
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
            self.sudo_run(["systemctl", "daemon-reload"],
                          ignore_error=True)
            self.log("✓ zram configured (reboot to activate)",
                     "success")
            return True
        return False

    def rollback_zram(self, params=None):
        path = "/etc/systemd/zram-generator.conf"
        content = self.read_file(path) or ""
        if re.search(r"zram-size\s*=\s*ram-size", content):
            self._rm(path)
            self.sudo_run(["systemctl", "daemon-reload"],
                          ignore_error=True)
            self.log("✓ zram config removed", "success")
        else:
            self.log("zram config not ours, left untouched", "info")
        return True

    def apply_zswap(self, params=None):
        if not self.state.has_swap:
            self.log("No swap found, zswap skipped", "warning")
            return None
        pl = ["zswap.enabled=1", "zswap.compressor=zstd"]
        if os.path.exists("/sys/module/z3fold"):
            pl.append("zswap.zpool=z3fold")
        return self.add_grub_params(pl)

    def rollback_zswap(self, params=None):
        return self._remove_grub_params(["zswap.enabled=1",
                                         "zswap.compressor=zstd",
                                         "zswap.zpool=z3fold"])

    def apply_thp(self, params=None):
        params = params or {}
        val = params.get("thp_value", "madvise")
        return self._grub_set_param("transparent_hugepage=%s" % val)

    def rollback_thp(self, params=None):
        return self._remove_grub_params(["transparent_hugepage=always",
                                         "transparent_hugepage=madvise",
                                         "transparent_hugepage=never"])

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
        if not self.write_file(path, "\n".join(out) + "\n",
                               chmod="644", mkdir=True, backup=True):
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
        """Удаляет sysctl-параметр и возвращает default."""
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
            if not self.write_file(path, "\n".join(out) + "\n",
                                   backup=True):
                return False
        self.sudo_run(["sysctl", "-w", "%s=%s" % (key, default)],
                      ignore_error=True)
        self.log("✓ %s reverted to %s" % (key, default), "success")
        return True

    def apply_sysctl_cache(self, params=None):
        return self._sysctl_set("vm.vfs_cache_pressure", "50")

    def rollback_sysctl_cache(self, params=None):
        return self._sysctl_del("vm.vfs_cache_pressure", "100")

    def apply_sysctl_numa(self, params=None):
        return self._sysctl_set("kernel.numa_balancing", "0")

    def rollback_sysctl_numa(self, params=None):
        return self._sysctl_del("kernel.numa_balancing", "1")

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

    def rollback_reisub(self, params=None):
        self._rm("/etc/sysctl.d/99-sysrq.conf")
        self.sudo_run(["sysctl", "-w", "kernel.sysrq=176"],
                      ignore_error=True)
        self.log("✓ kernel.sysrq back to 176", "success")
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
        if not self.write_file("/etc/modules-load.d/ntsync.conf",
                               "ntsync\n", chmod="644", mkdir=True):
            return False
        if not self.sudo_run(["modprobe", "ntsync"], ignore_error=True):
            self.log("ntsync module not loaded (needs kernel 6.14+)",
                     "warning")
            return False
        if not os.path.exists("/dev/ntsync"):
            self.log("ntsync loaded but /dev/ntsync not present",
                     "warning")
            return False
        self.log("✓ ntsync autoloaded", "success")
        return True

    def rollback_ntsync(self, params=None):
        self._rm("/etc/modules-load.d/ntsync.conf")
        self.log("✓ ntsync removed", "success")
        return True

    # ─── Диски: tmpfs /tmp ──────────────────────────────────────────────

    def apply_tmpfs_tmp(self, params=None):
        params = params or {}
        size = str(params.get("tmpfs_size_value",
                              TMPFS_SIZE_DEFAULT)).strip() \
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
            self.log("/tmp tmpfs already configured with size %s" % size,
                     "info")
            return True
        if not self.write_file(path, "\n".join(new_lines) + "\n",
                               backup=True):
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
            new = re.sub(r"^\s*blacklist\s+ntfs3\s*$",
                         "# blacklist ntfs3", content, flags=re.M)
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


# ============================================================================
# БЛОК 13. SYSTEMMOPS: FSTAB, STEAM, ALIASES, APPS, УДАЛЕНИЕ
# ============================================================================

    # ─── fstab: определение устройств и поиск строк ─────────────────────

    def _device_identifiers(self, dev):
        """Возвращает список идентификаторов: UUID=..., LABEL=..., PARTUUID=..."""
        idents = []
        try:
            res = subprocess.run(["lsblk", "-no", "UUID,LABEL,PARTUUID",
                                  dev],
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

    def _fstab_find(self, lines, mp, dev):
        """Ищет строку fstab по mp или идентификатору устройства."""
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

            mp_field = unescape_fstab_token(f[1])
            if mp_field == mp or f[1] == mp:
                return i, f

            if idents:
                first_raw = f[0]
                first_unescaped = unescape_fstab_token(first_raw)
                first_lower = first_raw.lower()
                first_unescaped_lower = first_unescaped.lower()

                for ident in idents:
                    il = ident.lower()
                    if first_lower == il or first_unescaped_lower == il:
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
            filtered = [o for o in opts
                        if o not in ("noatime", "nodiratime")]
            if filtered == opts:
                self.log("fstab %s has no noatime" % mp, "info")
                return True
            opts = filtered
        parts[3] = ",".join(opts)
        lines[idx] = "\t".join(parts)
        if not self.write_file(path, "\n".join(lines) + "\n", backup=True):
            return False
        if not self.verify_fstab():
            self.log("fstab verification failed after editing %s" % mp,
                     "error")
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
        res = [self._mount_opts_edit(mp, True) for mp in mps]
        if all(r is None for r in res):
            return None
        if any(r is False for r in res):
            return False
        return True

    def rollback_mount_opts(self, mps):
        if self.dry_run:
            for mp in mps:
                self.log("[DRY RUN] fstab %s -noatime" % mp, "warning")
            return True
        res = [self._mount_opts_edit(mp, False) for mp in mps]
        if all(r is None for r in res):
            return None
        if any(r is False for r in res):
            return False
        return True

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
        opts = [o for o in parts[3].split(",")
                if not o.startswith("commit=")]
        if add:
            opts.append("commit=%s" % val)
        parts[3] = ",".join(opts)
        lines[idx] = "\t".join(parts)
        if not self.write_file(path, "\n".join(lines) + "\n", backup=True):
            return False
        if not self.verify_fstab():
            self.log("fstab verification failed after commit edit on %s"
                     % mp, "error")
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
                self.log("[DRY RUN] fstab %s commit=%s" % (mp, val),
                         "warning")
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
        if not applied_any:
            self.log("commit=: all targets skipped", "warning")
            return None
        if not ok:
            return False
        self.log("✓ fstab commit=%s applied" % val, "success")
        return True

    def rollback_commit(self, params=None):
        if self.dry_run:
            self.log("[DRY RUN] fstab remove commit", "warning")
            return True
        targets = list(self.commit_targets)
        if not targets:
            return True
        res = [self._mount_commit_edit(mp, "", False) for mp in targets]
        if all(r is None for r in res):
            return None
        if any(r is False for r in res):
            return False
        self.log("✓ fstab commit removed", "success")
        return True

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
                    if any(o.startswith("commit=")
                           for o in f2[3].split(",")):
                        return True
        return False

    # ─── fstab: pass=0 (nofsck) ─────────────────────────────────────────

    def _mount_pass_edit(self, mp, disable=True):
        """Ставит pass=0 (disable=True) или восстановленный pass
        в /etc/fstab для точки монтирования."""
        path = "/etc/fstab"
        fstype = self._fstype_of_mp(mp)
        if fstype and not fs_supports_nofsck(fstype):
            self.log("Skipped %s (%s): fsck option not applicable here"
                     % (mp, fstype), "warning")
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

        while len(parts) < 6:
            parts.append("0")

        if disable:
            new_pass = "0"
        else:
            if mp == "/" and fstype in ("ext2", "ext3", "ext4"):
                new_pass = "1"
            elif fstype in ("ext2", "ext3", "ext4", "f2fs"):
                new_pass = "2"
            else:
                new_pass = "0"

        # dump (parts[4]) не трогаем — почти всегда 0
        if parts[5] == new_pass:
            self.log("fstab %s already has pass=%s" % (mp, new_pass),
                     "info")
            return True

        parts[5] = new_pass
        lines[idx] = "\t".join(parts)

        if not self.write_file(path, "\n".join(lines) + "\n", backup=True):
            return False
        if not self.verify_fstab():
            self.log("fstab verification failed after pass edit on %s"
                     % mp, "error")
            return False
        if disable:
            self.log("✓ fstab %s: fsck disabled (pass=0)" % mp, "success")
        else:
            self.log("✓ fstab %s: fsck restored (pass=%s)"
                     % (mp, new_pass), "success")
        return True

    def apply_nofsck(self, mps):
        if self.dry_run:
            for mp in mps:
                self.log("[DRY RUN] fstab %s pass=0" % mp, "warning")
            return True
        res = [self._mount_pass_edit(mp, True) for mp in mps]
        if all(r is None for r in res):
            return None
        if any(r is False for r in res):
            return False
        return True

    def rollback_nofsck(self, mps):
        if self.dry_run:
            for mp in mps:
                self.log("[DRY RUN] fstab %s pass restored" % mp,
                         "warning")
            return True
        res = [self._mount_pass_edit(mp, False) for mp in mps]
        if all(r is None for r in res):
            return None
        if any(r is False for r in res):
            return False
        self.log("✓ fstab fsck settings restored", "success")
        return True

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
            if os.path.realpath(lib) == os.path.realpath(
                    os.path.dirname(src)):
                continue
            if self.dry_run:
                self.log("[DRY RUN] ln -s %s -> %s" % (src, dst),
                         "warning")
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
                    self.log("Existing user aliases with same names "
                             "found — left untouched", "warning")
                    warned = True
                cleaned.append(line)
                continue
            if func_rx.match(line):
                if not warned:
                    self.log("Existing user functions with same names "
                             "found — left untouched", "warning")
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
            block += ["spices() {",
                      '    echo "Cinnamon spices update..."',
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
        if not self.write_file(bashrc, "\n".join(lines) + "\n",
                               backup=True):
            return False
        if self.state.user_name and self.state.user_name != "root":
            self.sudo_run(["chown",
                           "%s:%s" % (self.state.user_name,
                                      self.state.user_name),
                           bashrc], ignore_error=True)
        self.log("✓ commands removed from .bashrc", "success")
        return True

    # ─── Автообновления ─────────────────────────────────────────────────

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
            if self.sudo_run(["systemctl", "mask", u],
                             ignore_error=True):
                masked_any = True
        if masked_any:
            self.log("✓ apt-daily / unattended-upgrades masked",
                     "success")
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
            self.sudo_run(["systemctl", "disable", "--now",
                           "biweekly-upgrade.timer"], ignore_error=True)
            self.sudo_run(["rm", "-f", svc, tmr], ignore_error=True)
            self.sudo_run(["systemctl", "daemon-reload"],
                          ignore_error=True)
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
        svc_c = ("[Unit]\nDescription=System upgrade (%s)\n\n"
                 "[Service]\nType=oneshot\nExecStartPre=/bin/sleep 600\n"
                 "Environment=DEBIAN_FRONTEND=noninteractive\n"
                 "ExecStart=/usr/bin/bash -c \"%s\"\nUser=root\n"
                 % (desc, cmd))
        tmr_c = ("[Unit]\nDescription=System upgrade timer (%s)\n\n"
                 "[Timer]\nOnCalendar=%s\nPersistent=true\n\n"
                 "[Install]\nWantedBy=timers.target\n" % (desc, onc))
        ex_svc = self.read_file(svc) or ""
        ex_tmr = self.read_file(tmr) or ""
        if exists and ex_svc == svc_c and ex_tmr == tmr_c:
            self.log("Timer already configured: %s" % desc, "info")
            if (self.service_enabled("biweekly-upgrade.timer") != "enabled"
                    and not self.dry_run):
                self.sudo_run(["systemctl", "daemon-reload"],
                              ignore_error=True)
                self.sudo_run(["systemctl", "enable", "--now",
                               "biweekly-upgrade.timer"],
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

    def _apps_expand_groups(self, pkgs):
        """Если среди выбранных есть записи из ADDITIONAL_REMOVABLE_PACKAGES
        с маской (например, libreoffice-*), вернуть как есть — раскрытие
        делает expand_package_pattern."""
        return list(pkgs)

    def apps_purge(self, pkgs):
        """Удаляет пакеты через apt purge + autoremove.
        Возвращает (ok, freed)."""
        if self.dry_run:
            self.log("[DRY RUN] apt purge " + " ".join(pkgs), "warning")
            return True, "?"
        freed = estimate_packages_size([p for p in pkgs
                                        if "*" not in p and "?" not in p])
        env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
        if not self.sudo_run(["apt-get", "purge", "-y"] + list(pkgs),
                             err_msg="apt purge failed",
                             timeout=SUDO_TIMEOUT_APT, env=env):
            return False, "?"
        self.sudo_run(["apt-get", "autoremove", "-y"],
                      ignore_error=True,
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
        """Удаляет строки, соответствующие regex pattern."""
        if self.dry_run:
            self.log("[DRY RUN] %s: remove %s" % (path, pattern),
                     "warning")
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


# ============================================================================
# БЛОК 14. SYSTEMMOPS: ROLLBACK
# ============================================================================

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
                    self.log("✓ VRR config restored from backup",
                             "success")
                    return True
        content = self.read_file(path) or ""
        if re.search(r'Option\s+"VariableRefresh"', content, re.I):
            self._rm(path)
            self.log("✓ VRR config removed", "success")
        else:
            self.log("VRR config not ours, left untouched", "info")
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
# ============================================================================
# БЛОК 15. MAINWINDOW: ЯДРО И ХЕЛПЕРЫ (детекты)
# ============================================================================

class MainWindow:
    """Главное окно твикера."""

    def __init__(self, root):
        self.root = root
        self.scale = compute_ui_scale(root)
        self.lang = detect_lang()
        self.theme = "light"
        self.is_running = False

        self.applied = {}
        self.mount_applied = {}
        self.steam_applied = {}
        self.commit_applied_per_mp = {}
        self.fsck_applied = {}

        self.badges = {}
        self.mount_badges = {}
        self.steam_badges = {}
        self.commit_badges = {}
        self.fsck_badges = {}
        self.option_widgets = {}

        self.opts_state = {k: BooleanVar(value=False) for k in OPTIONS_META}
        self.mount_state = {}
        self.steam_state = {}
        self.commit_state = {}
        self.fsck_state = {}

        self.disabled_reasons = {}

        self.svc_checked = set()
        self.svc_rows = []
        self._svc_sort_col = None
        self._svc_sort_reverse = False

        self._tune_filter = StringVar(value="")
        self._show_only_unapplied = BooleanVar(value=False)
        self._tune_filter.trace_add(
            "write", lambda *a: self._rebuild_tune_list())
        self._show_only_unapplied.trace_add(
            "write", lambda *a: self._rebuild_tune_list())

        self.msg_queue = queue.Queue()
        self._running_tasks = set()
        self._running_lock = threading.Lock()

        self._ram_cache = None
        self._zfs_button = None
        self._svc_result_lbl = None
        self._apps_result_lbl = None
        self._result_lbl = None
        self._result_hide_ids = {}

        self.max_map_count_value = StringVar(value=MAX_MAP_COUNT_DEFAULT)
        self.tmpfs_size_value = StringVar(value="512M")
        self.shutdown_timeout_value = StringVar(
            value=SHUTDOWN_TIMEOUT_DEFAULT)
        self.pipewire_preset_key = PIPEWIRE_PRESET_DEFAULT
        self.pipewire_preset_value = StringVar(
            value=self._pipewire_preset_label(PIPEWIRE_PRESET_DEFAULT))

        self.rtl_ant_sel_key = "default"
        self.rtl_ant_sel_value = StringVar(
            value=self._rtl_ant_sel_label("default"))

        self.apps_checked = set()
        self._installed_packages = None
        self._real_installed_packages = None
        self._apps_filter = StringVar(value="")
        self._apps_filter.trace_add("write", lambda *a: self._apps_render())
        self._apps_canvas = None
        self._apps_inner = None
        self._apps_status = None

        self.sudo = SudoManager()
        self.sudo.prompt_password = self._ask_password
        self.sudo.show_error = lambda m: messagebox.showwarning(
            self.t("sudo_title"),
            self.t("sudo_wrong") + ("\n" + m if m else ""),
            parent=self.root)

        self.state = SystemState()
        self.state.detect()

        self.corectrl_group = StringVar(
            value=self.state.user_name
            if self.state.user_name != "root" else "sudo")
        self.swap_value = StringVar(
            value="150" if self.state.swap_type == "zram" else "10")
        self.commit_value = StringVar(value="60")
        self.thp_value = StringVar(value="madvise")
        self.schedule_value = StringVar(value=self._schedule_values()[2])

        # Разделы
        mounts, seen = [], set()
        for it in parse_mounts():
            if it["mp"] == "/boot/efi" or (
                    it["fstype"] == "vfat"
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
            for mp in m["mps"]:
                self.fsck_state[mp] = BooleanVar(value=False)

        # Библиотеки Steam
        self.steam_items = []
        for lib in find_steam_libraries(self.state.user_home):
            if self._lib_on_ntfs(lib):
                self.steam_items.append(lib)
                self.steam_state[lib] = BooleanVar(value=False)

        # Ссылки на виджеты
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

        self._dry_var = BooleanVar(value="--dry-run" in sys.argv)
        self._compute_disabled_reasons()
        self._build_ui()
        self._apply_theme()
        self._bind_global_wheel()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.log("%s v%s запущен" % (APP_NAME, APP_VERSION), "success")
        self.log("GPU: %s %s" % (self.state.gpu, self.state.gpu_model),
                 "info")

        self.root.after(100, self._process_queue)
        self.root.after(300,
                        lambda: self._run_bg("services",
                                             self._services_work))
        self.root.after(600,
                        lambda: self._run_bg("applied",
                                             self._applied_work))
        self.root.after(900,
                        lambda: self._run_bg("status",
                                             self._status_work))
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
        if not os.path.exists(
                "/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf"):
            r["ntfs3"] = self.t("reason_mint_only")
        elif not getattr(self.state, "has_ntfs_partitions", False):
            r["ntfs3"] = self.t("reason_no_ntfs")
        if not getattr(self.state, "pipewire_active", False):
            r["pipewire"] = self.t("reason_pipewire_inactive")
        if not getattr(self.state, "rtl_wifi_modules", []):
            r["rtl_msi"] = self.t("reason_no_rtl")
        self.disabled_reasons = r

    # ─── Вспомогательные ────────────────────────────────────────────────

    def _lib_on_ntfs(self, lib):
        """True, если библиотека Steam лежит на NTFS."""
        best, dev, fstype = "", "", ""
        for it in parse_mounts():
            mp = it["mp"]
            if (lib == mp or lib.startswith(mp.rstrip("/") + "/")
                    or mp == "/"):
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
        """Окружение без переменных AppImage."""
        return {k: v for k, v in os.environ.items()
                if k not in ("LD_LIBRARY_PATH", "LD_PRELOAD", "PYTHONPATH",
                             "PYTHONHOME", "APPDIR", "APPIMAGE")}

    def _read_text_file(self, path):
        """Читает текстовый файл без sudo."""
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
                                 text=True, timeout=5,
                                 env=self._host_env())
            lines = res.stdout.splitlines()
            for i, ln in enumerate(lines):
                if ("VGA compatible controller" in ln
                        or "3D controller" in ln):
                    for j in range(i + 1, min(i + 4, len(lines))):
                        m = re.search(r"Kernel driver in use:\s*(\S+)",
                                      lines[j])
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
            res = subprocess.run(["glxinfo"], capture_output=True,
                                 text=True, timeout=5,
                                 env=self._host_env())
            if res.returncode == 0:
                m = re.search(r"Mesa\s+([0-9][0-9a-zA-Z.\-+]*)",
                              res.stdout)
                if m:
                    return m.group(1)
        except Exception:
            pass
        for pkg in ("libglx-mesa0", "libgl1-mesa-dri", "libgl1-mesa-glx"):
            try:
                res = subprocess.run(
                    ["dpkg-query", "-W", "-f=${Version}", pkg],
                    capture_output=True, text=True, timeout=5,
                    env=self._host_env())
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
                content = f.read()
            m = re.search(r"\[(\w+)\]", content)
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
        """Определяет текущее хранилище журнала."""
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
            with open(path, "r", encoding="utf-8",
                      errors="replace") as f:
                content = f.read()
        except Exception:
            return "?"
        if re.search(r"^\s*blacklist\s+ntfs3\s*$", content, re.M):
            return "заблокирован" if self.lang == "ru" else "blocked"
        return "разблокирован" if self.lang == "ru" else "unblocked"

    def _ntsync_current(self):
        return (("доступен" if self.lang == "ru" else "available")
                if getattr(self.state, "ntsync", False)
                else ("недоступен" if self.lang == "ru"
                      else "unavailable"))

    def _shutdown_timeout_current(self):
        """Текущий таймаут systemd для остановки служб."""
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
        m = re.search(r"^\s*DefaultTimeoutStopSec\s*=\s*(\S+)",
                      content, re.M)
        if m:
            return m.group(1)
        return "?"

    def _pipewire_preset_current(self):
        """Определяет, какой пресет сейчас применён в PipeWire."""
        path = os.path.join(self.state.user_home, ".config", "pipewire",
                            "pipewire.conf.d", "10-sound.conf")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8",
                      errors="replace") as f:
                content = f.read()
        except Exception:
            return None
        m_min = re.search(r"min-quantum\s*=\s*(\d+)", content)
        m_q = re.search(r"default\.clock\.quantum\s*=\s*(\d+)", content)
        m_max = re.search(r"max-quantum\s*=\s*(\d+)", content)
        if not (m_min and m_q and m_max):
            return "manual"
        cur = (int(m_min.group(1)), int(m_q.group(1)),
               int(m_max.group(1)))
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

    def _detect_fsck(self, ops):
        """Определяет, применён ли pass=0 к каждому разделу."""
        content = ops.read_file("/etc/fstab") or ""
        lines = lines_in(content)
        res = {}
        for mp in self.fsck_state:
            dev = None
            for m in self.mount_items:
                if mp in m["mps"]:
                    dev = m["dev"]
                    break
            idx, parts = ops._fstab_find(lines, mp, dev)
            ok = idx is not None and len(parts) >= 6 and parts[5] == "0"
            res[mp] = ok
        return res

    def _pipewire_preset_label(self, key):
        p = PIPEWIRE_PRESETS[key]
        return "%s — %s" % (p["label_%s" % self.lang],
                            p["desc_%s" % self.lang])

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
        cur = self.pipewire_preset_value.get()
        for key in ("default", "gaming", "recording"):
            if cur == self._pipewire_preset_label(key):
                self.pipewire_preset_key = key
                return

    # ─── Realtek ant_sel UI ───────────────────────────────────────────
    def _rtl_ant_sel_label(self, key):
        if key == "1":
            return self.t("rtl_ant_1")
        if key == "2":
            return self.t("rtl_ant_2")
        return self.t("rtl_default")

    def _rtl_ant_sel_strings(self):
        return [self._rtl_ant_sel_label(k) for k in ("default", "1", "2")]

    def _rtl_ant_sel_on_select(self):
        cur = self.rtl_ant_sel_value.get()
        for key in ("default", "1", "2"):
            if cur == self._rtl_ant_sel_label(key):
                self.rtl_ant_sel_key = key
                return

    def _rtl_ant_sel_current_key(self):
        path = "/etc/modprobe.d/rtlwifi-tweaker.conf"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            content = ""

        mods = getattr(self.state, "rtl_wifi_modules", [])
        for mod in mods:
            m = re.search(
                r"^\s*options\s+%s\s+.*\bant_sel=(\d+)\b" % re.escape(mod),
                content,
                re.M
            )
            if m and m.group(1) in ("1", "2"):
                return m.group(1)

        for mod in mods:
            p = "/sys/module/%s/parameters/ant_sel" % mod
            if os.path.exists(p):
                try:
                    with open(p, "r") as f:
                        v = f.read().strip()
                    if v in ("1", "2"):
                        return v
                except Exception:
                    pass

        return "default"

    def _rtl_ant_sel_current_label(self):
        return self._rtl_ant_sel_label(self._rtl_ant_sel_current_key())

    def _rtl_msi_applied(self, ops):
        content = ops.read_file(
            "/etc/modprobe.d/rtlwifi-tweaker.conf") or ""
        if not content.strip():
            return False

        mods = getattr(self.state, "rtl_wifi_modules", [])
        if not mods:
            mods = sorted(rtl_wifi_fix_candidates().keys())

        for mod in mods:
            rx = re.compile(
                r"^\s*options\s+%s\s+.*\b(msi=1|ant_sel=\d+)\b"
                % re.escape(mod),
                re.M
            )
            if rx.search(content):
                return True

        return False

    def _shutdown_timeout_applied(self):
        """True, если DefaultTimeoutStopSec отличается от дефолта."""
        content = self._read_text_file("/etc/systemd/system.conf")
        m = re.search(r"^\s*DefaultTimeoutStopSec\s*=\s*(\S+)",
                      content, re.M)
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

    # ─── Логирование и очередь ──────────────────────────────────────────

    def log(self, msg, tag="normal"):
        """Кладёт сообщение в очередь для главного потока."""
        self.msg_queue.put(("log", msg, tag))

    def _run_bg(self, name, fn, *args):
        """Запускает фоновую задачу. Не запускает дубликат."""
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
            self._set_running(item[1])
        elif kind == "applied":
            self.applied = item[1]
            self._update_badges()
            if self._show_only_unapplied.get():
                self._rebuild_tune_list()
        elif kind == "mount_applied":
            self.mount_applied = item[1]
            self._update_badges()
        elif kind == "steam_applied":
            self.steam_applied = item[1]
            self._update_badges()
        elif kind == "commit_applied":
            self.commit_applied_per_mp = item[1]
            self._update_badges()
        elif kind == "fsck_applied":
            self.fsck_applied = item[1]
            self._update_badges()
        elif kind == "schedule":
            if self._sched_lbl is not None:
                self._sched_lbl.config(
                    text=self.t("sched_cur") % item[1])
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
            self._show_tab_result("tune", item[1], item[2], item[3])
        elif kind == "svc_result":
            self._show_tab_result("svc", item[1], item[2], item[3])
        elif kind == "apps_result":
            self._show_tab_result("apps", item[1], item[2], item[3])
        elif kind == "toast":
            self.log(item[1][0], item[1][1])

    def _append_log(self, msg, tag):
        if self._terminal is None:
            return
        self._terminal.configure(state=NORMAL)
        self._terminal.insert(
            END,
            msg + ("\n" if not msg.endswith("\n") else ""),
            tag)
        self._terminal.see(END)
        self._terminal.configure(state=DISABLED)

    def _show_result(self, ok, skip, fail):
        """Совместимость со старыми вызовами."""
        self._show_tab_result("tune", ok, skip, fail)

    def _show_tab_result(self, tab, ok, skip, fail):
        """Показывает локализованный индикатор результата на вкладке."""
        attr = {
            "tune": "_result_lbl",
            "svc": "_svc_result_lbl",
            "apps": "_apps_result_lbl",
        }.get(tab)

        lbl = getattr(self, attr, None) if attr else None
        if lbl is None:
            return

        try:
            if not lbl.winfo_exists():
                return
        except Exception:
            return

        c = self.colors()
        if fail == 0 and ok > 0:
            mark, col = "✓", c["green"]
        elif fail == 0 and ok == 0:
            mark, col = "•", c["gray"]
        elif fail < ok:
            mark, col = "⚠", c["yellow"]
        else:
            mark, col = "✗", c["red"]

        txt = ("%s  " + self.t("result_text")) % (mark, ok, skip, fail)
        lbl.config(text=txt, fg=col)

        old = self._result_hide_ids.get(tab)
        if old is not None:
            try:
                self.root.after_cancel(old)
            except Exception:
                pass

        def hide():
            try:
                if lbl.winfo_exists():
                    lbl.config(text="")
            except Exception:
                pass

        self._result_hide_ids[tab] = self.root.after(5000, hide)

    # ─── Детект: applied ────────────────────────────────────────────────

    def _applied_work(self):
        ops = SystemOps(self.sudo, self.state,
                        lambda m, t="normal": None, True)
        ops.mount_items = self.mount_items
        ops.commit_targets = [mp for mp in self.commit_state]

        try:
            self.msg_queue.put(("applied", self._detect_applied(ops)))
            self.msg_queue.put(("mount_applied", self._detect_mount(ops)))
            self.msg_queue.put(("steam_applied", self._detect_steam()))
            self.msg_queue.put(("schedule", self._schedule_text()))
            self.msg_queue.put(("commit_applied",
                                self._detect_commit_per_mp(ops)))
            self.msg_queue.put(("fsck_applied", self._detect_fsck(ops)))
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
                 "Sat 18:30:00": ("Еженедельно (суббота)",
                                  "Weekly (Saturday)"),
                 "*-*-1,15 18:30:00": ("2 раза в месяц (1 и 15)",
                                       "Twice a month (1 & 15)"),
                 "*-*-1 18:30:00": ("Ежемесячно (1 число)",
                                    "Monthly (1st)")}
        pair = names.get(cal)
        if pair:
            label = pair[0 if self.lang == "ru" else 1]
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
        if not self.sudo.ensure():
            self.log("sudo failed", "error")
            return
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
        Возвращает:
        - True  — правило найдено;
        - False — правило точно отсутствует;
        - None  — не смогли проверить.
        """
        direct_paths = (
            "/etc/polkit-1/rules.d/90-corectrl.rules",
            "/usr/share/polkit-1/rules.d/90-corectrl.rules",
            "/etc/polkit-1/localauthority/50-local.d/90-corectrl.pkla",
        )
        direct_decisive = True
        for p in direct_paths:
            try:
                with open(p, "r", encoding="utf-8",
                          errors="replace") as f:
                    if "org.corectrl" in f.read():
                        return True
            except FileNotFoundError:
                continue
            except PermissionError:
                direct_decisive = False
            except Exception:
                direct_decisive = False
        sudo_decisive = True
        for p in direct_paths:
            try:
                r = subprocess.run(["sudo", "-n", "cat", p],
                                   capture_output=True, text=True,
                                   timeout=3)
                if r.returncode == 0:
                    if "org.corectrl" in r.stdout:
                        return True
                elif "No such file" in (r.stderr or ""):
                    continue
                else:
                    sudo_decisive = False
            except Exception:
                sudo_decisive = False
        if direct_decisive or sudo_decisive:
            return False
        return None

    def _max_map_count_applied(self, mmc_content):
        return bool(re.search(r"^vm\.max_map_count=\d+\s*$",
                              mmc_content, re.M))

    def _vrr_applied(self, ops):
        content = ops.read_file(
            "/etc/X11/xorg.conf.d/20-amdgpu.conf") or ""
        return bool(re.search(r'Option\s+"VariableRefresh"\s+"true"',
                              content, re.I))

    def _zram_applied(self, ops):
        if not zram_generator_present():
            return False
        content = ops.read_file(
            "/etc/systemd/zram-generator.conf") or ""
        return bool(re.search(r"^\s*\[zram", content, re.M))

    def _grub_has_token(self, grub, token):
        for line in grub.splitlines():
            s = line.strip()
            if s.startswith("#"):
                continue
            m = re.match(r"^\s*GRUB_CMDLINE_LINUX(?:_DEFAULT)?=(.*)$",
                         line)
            if not m:
                continue
            raw = m.group(1).strip().strip('"').strip("'")
            if token in raw.split():
                return True
        return False

    def _grub_has_prefix(self, grub, prefix):
        for line in grub.splitlines():
            s = line.strip()
            if s.startswith("#"):
                continue
            m = re.match(
                r"^\s*GRUB_CMDLINE_LINUX(?:_DEFAULT)?=(.*)$", line)
            if not m:
                continue
            raw = m.group(1).strip().strip('"').strip("'")
            if any(t.startswith(prefix) for t in raw.split()):
                return True
        return False

    def _detect_applied(self, ops):
        grub = ops.read_file("/etc/default/grub") or ""
        env = ops.read_file("/etc/environment") or ""
        j = ops.read_file("/etc/systemd/journald.conf") or ""
        swp = ops.read_file("/etc/sysctl.d/99-gaming-swap.conf") or ""
        sysc = ops.read_file("/etc/sysctl.d/99-gaming-sysctl.conf") or ""
        bashrc = ops.read_file(
            os.path.join(self.state.user_home, ".bashrc")) or ""
        mint = ops.read_file(
            "/usr/lib/modprobe.d/mint-blacklist-ntfs3.conf") or ""
        itco = ops.read_file("/etc/modprobe.d/nmi-watchdog.conf") or ""
        mmc = ops.read_file("/etc/sysctl.d/99-gaming-mmap.conf") or ""

        def sv(p):
            try:
                r = subprocess.run(["sysctl", "-n", p],
                                   capture_output=True, text=True,
                                   timeout=3, env=self._host_env())
                return r.stdout.strip() if r.returncode == 0 else ""
            except Exception:
                return ""

        sw_ok = bool(re.search(r"^\s*vm\.swappiness\s*=\s*\d+\s*$",
                               swp, re.M))
        pw = os.path.join(self.state.user_home, ".config", "pipewire",
                          "pipewire.conf.d", "10-sound.conf")
        j_ok = (re.search(r"^\s*Storage\s*=\s*volatile\s*$", j, re.M)
                and re.search(r"^\s*RuntimeMaxUse\s*=\s*50M\s*$",
                              j, re.M))
        thp_kernel = self._thp_current()
        thp_want = self.thp_value.get()
        thp_ok = (self._grub_has_prefix(grub, "transparent_hugepage=")
                  or (thp_kernel and thp_kernel == thp_want))
        pipewire_preset = self._pipewire_preset_current()
        return {
            "journald": bool(j_ok),
            "audit": self._grub_has_token(grub, "audit=0"),
            "raid": self._grub_has_token(grub, "raid=noautodetect"),
            "nmi_watchdog": self._grub_has_token(grub,
                                                 "nmi_watchdog=0"),
            "itco_wdt": "blacklist iTCO_wdt" in itco,
            "zfs_services": (zfs_units_masked()
                             if self.state.zfs_installed else False),
            "shutdown_timeout": self._shutdown_timeout_applied(),
            "corectrl": self._corectrl_found(ops),
            "ppfeaturemask": (self._grub_has_token(
                grub, "amdgpu.ppfeaturemask=0xffffffff")
                or "amdgpu.ppfeaturemask" in grub),
            "nvidia_modeset": self._grub_has_token(
                grub, "nvidia-drm.modeset=1"),
            "vrr": self._vrr_applied(ops),
            "radv": "RADV_PERFTEST=sam" in env,
            "mesa": "MESA_SHADER_CACHE_MAX_SIZE=4G" in env,
            "pipewire": bool(pipewire_preset),
            "bbr": sv("net.ipv4.tcp_congestion_control") == "bbr",
            "rtl_msi": self._rtl_msi_applied(ops),
            "swap": sw_ok,
            "zram": self._zram_applied(ops),
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
                       or ops.path_exists(
                           "/etc/modules-load.d/ntsync.conf")),
            "max_map_count": self._max_map_count_applied(mmc),
            "ntfs3": bool(re.search(r"^\s*#\s*blacklist\s+ntfs3\s*$",
                                    mint, re.M)),
            "commit": ops._commit_applied(),
            "tmpfs_tmp": tmpfs_tmp_mounted() or fstab_has_tmp_tmpfs(),
            "aliases": "system-tuneup" in bashrc,
            "autoupdate": ops.service_enabled(
                "biweekly-upgrade.timer") == "enabled",
            "nofsck": any(self._detect_fsck(ops).values()),
        }

    def _detect_mount(self, ops):
        content = ops.read_file("/etc/fstab") or ""
        lines = lines_in(content)
        res = {}
        for m in self.mount_items:
            oks = []
            for mp in m["mps"]:
                idx, parts = ops._fstab_find(lines, mp, m["dev"])
                ok = False
                if idx is not None and len(parts) >= 4:
                    ok = "noatime" in parts[3].split(",")
                oks.append(ok)
            res[m["mps"][0]] = all(oks) if oks else False
        return res

    def _detect_steam(self):
        return {lib: os.path.islink(os.path.join(lib, "compatdata"))
                for lib in self.steam_items}


# ============================================================================
# БЛОК 16. MAINWINDOW: UI-КАРКАС
# ============================================================================

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
        self._lang_btn = Button(head,
                                text="EN" if self.lang == "ru" else "RU",
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
        self._notebook.add(self._tab_tune,
                           text="  %s  " % self.t("tab_tune"))
        self._notebook.add(self._tab_serv,
                           text="  %s  " % self.t("tab_serv"))
        self._notebook.add(self._tab_stat,
                           text="  %s  " % self.t("tab_stat"))
        self._notebook.add(self._tab_apps,
                           text="  %s  " % self.t("tab_apps"))

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
        for tag, col in (("normal", c["terminal_fg"]),
                         ("success", c["green"]),
                         ("error", c["red"]),
                         ("warning", c["yellow"]),
                         ("info", c["blue"]),
                         ("highlight", c["orange"])):
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
        self._search_entry.pack(side=LEFT, fill=X, expand=True,
                                padx=(0, 6))
        Button(search_bar, text=self.t("btn_search_clear"),
               command=lambda: self._tune_filter.set(""),
               bg=c["button"], fg=c["fg"],
               activebackground=c["button_hover"],
               relief=FLAT, padx=10, pady=2,
               font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(0, 8))
        Checkbutton(search_bar, text=self.t("lbl_show_only_unapplied"),
                    variable=self._show_only_unapplied,
                    bg=c["bg"], fg=c["gray"],
                    activebackground=c["bg"],
                    activeforeground=c["gray"],
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

        self._svc_result_lbl = Label(bar, text="", bg=c["bg"], fg=c["gray"],
                                     font=("DejaVu Sans", 10, "bold"))
        self._svc_result_lbl.pack(side=LEFT, padx=(16, 0))

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
        self._services_tree.column("name", width=220, anchor=W,
                                   stretch=False)
        self._services_tree.column("state", width=130, anchor=W,
                                   stretch=False)
        self._services_tree.column("run", width=90, anchor=CENTER,
                                   stretch=False)
        self._services_tree.column("desc", width=380, anchor=W,
                                   stretch=True)
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
        hint = Label(wrap, text=self.t("svc_hint"), bg=c["bg"],
                     fg=c["gray"], anchor=W,
                     font=("DejaVu Sans", 9))
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
            relief=FLAT, bd=0, font=("DejaVu Sans Mono", 9),
            state=DISABLED)
        self._status_view.pack(fill=BOTH, expand=True)
        self._make_copyable(self._status_view)
        self._status_view.tag_configure("head", foreground=c["blue"],
                                        font=("DejaVu Sans Mono", 9,
                                              "bold"))
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

        self._apps_result_lbl = Label(bar, text="", bg=c["bg"],
                                      fg=c["gray"],
                                      font=("DejaVu Sans", 10, "bold"))
        self._apps_result_lbl.pack(side=LEFT, padx=(16, 0))

        search_bar = Frame(wrap, bg=c["bg"])
        search_bar.pack(fill=X, pady=(0, 6))
        Label(search_bar, text=self.t("apps_search"),
              bg=c["bg"], fg=c["gray"],
              font=("DejaVu Sans", 9)).pack(side=LEFT, padx=(2, 4))
        Entry(search_bar, textvariable=self._apps_filter,
              bg=c["entry"], fg=c["fg"], relief=FLAT,
              insertbackground=c["fg"],
              font=("DejaVu Sans", 9)).pack(side=LEFT, fill=X,
                                            expand=True)
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
        self.fsck_badges = {}
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
        show_only_unapplied = self._show_only_unapplied.get()
        disk_cat = self.om("ntfs3")[2]
        any_shown = False
        for cat in seq:
            matches = []
            for k in cats[cat]:
                if k == "commit":
                    continue
                # Недоступные скрываем ВСЕГДА
                if k in self.disabled_reasons:
                    continue
                # Фильтр «только неприменённое»
                if show_only_unapplied and self.applied.get(k, False) is True:
                    continue
                label, desc, _c, short = self.om(k)
                if (not query or query in label.lower()
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
                  text=self.t("search_no_results")
                  % self._tune_filter.get(),
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
        chk = Checkbutton(top, text=label,
                          variable=self.opts_state[key],
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
                  font=("DejaVu Sans", 9)).pack(side=LEFT,
                                                padx=(10, 2))
            e = Entry(top, textvariable=self.corectrl_group, width=12,
                      bg=c["entry"], fg=c["fg"], relief=FLAT)
            if disabled:
                e.configure(state=DISABLED, disabledbackground=c["bg"],
                            disabledforeground=c["gray"])
            e.pack(side=LEFT)
        elif key == "swap":
            Label(top, text=self.t("lbl_value"), bg=c["panel"],
                  fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT,
                                                padx=(10, 2))
            e = Entry(top, textvariable=self.swap_value, width=6,
                      bg=c["entry"], fg=c["fg"], relief=FLAT)
            if disabled:
                e.configure(state=DISABLED, disabledbackground=c["bg"],
                            disabledforeground=c["gray"])
            e.pack(side=LEFT)
        elif key == "thp":
            Label(top, text=self.t("lbl_value"), bg=c["panel"],
                  fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT,
                                                padx=(10, 2))
            combo = ttk.Combobox(top, textvariable=self.thp_value,
                                 values=["always", "madvise", "never"],
                                 state="disabled" if disabled
                                 else "readonly",
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
                  font=("DejaVu Sans", 9)).pack(side=LEFT,
                                                padx=(10, 2))
            combo = ttk.Combobox(top,
                                 textvariable=self.max_map_count_value,
                                 values=MAX_MAP_COUNT_VALUES,
                                 state="disabled" if disabled
                                 else "readonly",
                                 width=12,
                                 font=("DejaVu Sans", 9),
                                 style="TCombobox")
            combo.pack(side=LEFT)
            cur = getattr(self.state, "current_max_map_count", "")
            if cur:
                Label(top, text=self.t("cur_value") % cur,
                      bg=c["panel"], fg=c["gray"],
                      font=("DejaVu Sans", 8)).pack(side=LEFT,
                                                    padx=(6, 0))
        elif key == "shutdown_timeout":
            Label(top, text=self.t("lbl_value"), bg=c["panel"],
                  fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT,
                                                padx=(10, 2))
            combo = ttk.Combobox(
                top, textvariable=self.shutdown_timeout_value,
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
                      font=("DejaVu Sans", 8)).pack(side=LEFT,
                                                    padx=(6, 0))
        elif key == "tmpfs_tmp":
            Label(top, text=self.t("tmpfs_size_label"),
                  bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT,
                                                padx=(10, 2))
            e = Entry(top, textvariable=self.tmpfs_size_value, width=8,
                      bg=c["entry"], fg=c["fg"], relief=FLAT)
            if disabled:
                e.configure(state=DISABLED, disabledbackground=c["bg"],
                            disabledforeground=c["gray"])
            e.pack(side=LEFT)
            if tmpfs_tmp_mounted() or fstab_has_tmp_tmpfs():
                Label(top, text=self.t("tmpfs_already"),
                      bg=c["panel"], fg=c["green"],
                      font=("DejaVu Sans", 8)).pack(side=LEFT,
                                                    padx=(6, 0))
        elif key == "autoupdate":
            Label(top, text=self.t("lbl_schedule"), bg=c["panel"],
                  fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT,
                                                padx=(10, 2))
            combo = ttk.Combobox(top, textvariable=self.schedule_value,
                                 values=self._schedule_values(),
                                 state="disabled" if disabled
                                 else "readonly",
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
                  font=("DejaVu Sans", 9)).pack(side=LEFT,
                                                padx=(10, 2))
            combo = ttk.Combobox(
                top, textvariable=self.pipewire_preset_value,
                values=self._pipewire_preset_strings(),
                state="disabled" if disabled else "readonly",
                width=28,
                font=("DejaVu Sans", 9),
                style="TCombobox")
            combo.pack(side=LEFT)
            combo.bind("<<ComboboxSelected>>",
                       lambda e: self._pipewire_preset_on_select())
        elif key == "rtl_msi":
            Label(top, text=self.t("lbl_mode"), bg=c["panel"],
                  fg=c["gray"],
                  font=("DejaVu Sans", 9)).pack(side=LEFT,
                                                padx=(10, 2))
            combo = ttk.Combobox(
                top, textvariable=self.rtl_ant_sel_value,
                values=self._rtl_ant_sel_strings(),
                state="disabled" if disabled else "readonly",
                width=28,
                font=("DejaVu Sans", 9),
                style="TCombobox")
            combo.pack(side=LEFT)
            combo.bind("<<ComboboxSelected>>",
                       lambda e: self._rtl_ant_sel_on_select())

        # Текущее значение — подпись справа
        cur_label = None
        if key == "sysctl_cache":
            cur_label = self.t("cur_value") % self._read_sysctl_int(
                "/proc/sys/vm/vfs_cache_pressure", "?")
        elif key == "nmi_watchdog":
            cur_label = (self.t("nmi_now_active")
                         if getattr(self.state, "nmi_watchdog_active",
                                     False)
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
        elif key == "rtl_msi":
            cur_label = (self.t("cur_value")
                         % self._rtl_ant_sel_current_label())
        if cur_label:
            Label(top, text=cur_label, bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 8)).pack(side=LEFT, padx=(8, 0))

        # Бейдж «применено / не применено»
        badge = Label(top, text="…", bg=c["panel"], fg=c["gray"],
                      font=("DejaVu Sans", 9, "bold"))
        badge.pack(side=LEFT, padx=(12, 0))
        self.badges[key] = badge

        # Для corectrl — кнопка «проверить» (спросит sudo)
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
                activeforeground=(c["red"] if zfs_removable
                                  else c["gray"]),
                state=NORMAL if zfs_removable else DISABLED,
                relief=FLAT, padx=10, pady=4,
                font=("DejaVu Sans", 9))
            self._zfs_button.pack(anchor=W, padx=(24, 0), pady=(4, 0))

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
                  bg=c["panel"], fg=c["gray"], anchor=W,
                  justify=LEFT, wraplength=820,
                  font=("DejaVu Sans", 9)).pack(
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
                size_str = (human_size(info[0] * 1024 ** 3)
                            if info else "?")
                label_text = "%-10s %-22s %-6s %-8s" % (
                    dev_short, mp_str, m.get("fstype", ""), size_str)
                Label(row, text=label_text, bg=c["panel"],
                      fg=c["fg"], anchor=W, font=mono).pack(
                    side=LEFT, padx=(4, 0))
                badge = Label(row, text="…", bg=c["panel"],
                              fg=c["gray"],
                              font=("DejaVu Sans", 9, "bold"),
                              anchor=W)
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
                  font=("DejaVu Sans", 9)).pack(side=LEFT,
                                                padx=(4, 6))
            Entry(top2, textvariable=self.commit_value, width=8,
                  bg=c["entry"], fg=c["fg"], relief=FLAT,
                  insertbackground=c["fg"]).pack(side=LEFT)
            Label(top2, text=self.t("commit_default_hint"),
                  bg=c["panel"], fg=c["gray"],
                  font=("DejaVu Sans", 8)).pack(side=LEFT,
                                                padx=(8, 0))
            Label(self._tune_inner, text=self.om("commit")[1],
                  bg=c["panel"], fg=c["gray"], anchor=W,
                  justify=LEFT, wraplength=820,
                  font=("DejaVu Sans", 9)).pack(
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
                    size_str = (human_size(info[0] * 1024 ** 3)
                                if info else "?")
                    label_text = "%-10s %-22s %-6s %-8s %-12s" % (
                        dev_short, mp_str, m.get("fstype", ""),
                        size_str, cur_val)
                    Label(row, text=label_text, bg=c["panel"],
                          fg=c["fg"], anchor=W, font=mono).pack(
                        side=LEFT, padx=(4, 0))
                    badge = Label(row, text="…", bg=c["panel"],
                                  fg=c["gray"],
                                  font=("DejaVu Sans", 9, "bold"),
                                  anchor=W)
                    badge.pack(side=LEFT, padx=(12, 0))
                    self.commit_badges[mp] = badge
        else:
            top = Frame(self._tune_inner, bg=c["panel"])
            top.pack(fill=X, padx=8, pady=(10, 2))
            Label(top, text="─── %s ───" % self.t("commit_title"),
                  bg=c["panel"], fg=c["yellow"], anchor=W,
                  font=("DejaVu Sans", 10, "bold")).pack(side=LEFT)
            Label(self._tune_inner, text=self.t("commit_none"),
                  bg=c["panel"], fg=c["gray"], anchor=W,
                  justify=LEFT, wraplength=820,
                  font=("DejaVu Sans", 9)).pack(
                fill=X, padx=(24, 8), pady=(0, 4))
        if self.mount_items:
            top = Frame(self._tune_inner, bg=c["panel"])
            top.pack(fill=X, padx=8, pady=(10, 2))
            Label(top, text="─── %s ───" % self.t("fsck_title"),
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
                        command=lambda: self._show_option_help("fsck"),
                        bg=c["button"], fg=c["blue"],
                        activebackground=c["button_hover"],
                        activeforeground=c["blue"],
                        relief=FLAT, padx=6, pady=0,
                        font=("DejaVu Sans", 8, "bold"))
            qb._keep_fg = c["blue"]
            qb.pack(side=LEFT, padx=(2, 0))
            Label(self._tune_inner, text=self.t("fsck_desc"),
                  bg=c["panel"], fg=c["gray"], anchor=W,
                  justify=LEFT, wraplength=820,
                  font=("DejaVu Sans", 9)).pack(
                fill=X, padx=(24, 8), pady=(0, 4))
            for m in self.mount_items:
                for mp in m["mps"]:
                    row = Frame(self._tune_inner, bg=c["panel"])
                    row.pack(fill=X, padx=24, pady=1)
                    chk = Checkbutton(row, text="",
                                      variable=self.fsck_state[mp],
                                      bg=c["panel"], fg=c["fg"],
                                      activebackground=c["panel"],
                                      activeforeground=c["fg"],
                                      selectcolor=c["panel"], anchor=W)
                    chk.pack(side=LEFT)
                    dev_short = os.path.basename(m["dev"])
                    mp_str = mp
                    if len(mp_str) > 22:
                        mp_str = mp_str[:19] + "…"
                    info = self._disk_info(mp)
                    size_str = (human_size(info[0] * 1024 ** 3)
                                if info else "?")
                    label_text = "%-10s %-22s %-6s %-8s" % (
                        dev_short, mp_str, m.get("fstype", ""), size_str)
                    Label(row, text=label_text, bg=c["panel"],
                          fg=c["fg"], anchor=W, font=mono).pack(
                        side=LEFT, padx=(4, 0))
                    badge = Label(row, text="…", bg=c["panel"],
                                  fg=c["gray"],
                                  font=("DejaVu Sans", 9, "bold"),
                                  anchor=W)
                    badge.pack(side=LEFT, padx=(12, 0))
                    self.fsck_badges[mp] = badge
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
                  bg=c["panel"], fg=c["gray"], anchor=W,
                  justify=LEFT, wraplength=820,
                  font=("DejaVu Sans", 9)).pack(
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
                      anchor=W, font=mono).pack(side=LEFT,
                                                padx=(4, 0))
                badge = Label(row, text="…", bg=c["panel"],
                              fg=c["gray"],
                              font=("DejaVu Sans", 9, "bold"),
                              anchor=W)
                badge.pack(side=LEFT, padx=(12, 0))
                self.steam_badges[lib] = badge


# ============================================================================
# БЛОК 17. MAINWINDOW: ВКЛАДКА ПРИЛОЖЕНИЯ
# ============================================================================

    def _fmt_pkg_list(self, items, limit=14):
        items = list(items)
        if len(items) <= limit:
            return ", ".join(items)
        return ", ".join(items[:limit]) + " … (+%d)" % (len(items) - limit)

    def _apps_load_installed(self):
        if not is_debian_based():
            self._real_installed_packages = set()
            self._installed_packages = set()
            self.msg_queue.put(("apps_redraw", None))
            return

        try:
            real = installed_packages_set()
        except Exception:
            real = set()

        augmented = set(real)

        for pkg in REMOVABLE_PACKAGES.keys():
            if any(ch in pkg for ch in "*?["):
                try:
                    rx = re.compile(fnmatch.translate(pkg))
                    if any(rx.match(ip) for ip in real):
                        augmented.add(pkg)
                except Exception:
                    pass

        self._real_installed_packages = real
        self._installed_packages = augmented
        self.msg_queue.put(("apps_redraw", None))

    def _apps_refresh(self):
        self._installed_packages = None
        self._real_installed_packages = None
        self._run_bg("apps_load", self._apps_load_installed)

    def _apps_render(self):
        if self._apps_inner is None:
            return
        c = self.colors()
        for child in self._apps_inner.winfo_children():
            child.destroy()
        if not is_debian_based():
            Label(self._apps_inner, text=self.t("apps_unsupported"),
                  bg=c["panel"], fg=c["gray"], anchor=W, justify=LEFT,
                  font=("DejaVu Sans", 10)).pack(fill=X, padx=24, pady=20)
            self._apps_update_status()
            return
        if not REMOVABLE_PACKAGES:
            Label(self._apps_inner, text=self.t("apps_no_list"),
                  bg=c["panel"], fg=c["gray"], anchor=W, justify=LEFT,
                  font=("DejaVu Sans", 10)).pack(fill=X, padx=24,
                                                 pady=20)
            self._apps_update_status()
            return
        if self._installed_packages is None:
            Label(self._apps_inner, text="…",
                  bg=c["panel"], fg=c["gray"], anchor=W,
                  font=("DejaVu Sans", 10)).pack(fill=X, padx=24,
                                                 pady=20)
            return
        query = self._apps_filter.get().strip().lower()
        real = self._real_installed_packages or set()
        cats = {}
        for pkg, meta in REMOVABLE_PACKAGES.items():
            is_mask = any(ch in pkg for ch in "*?[")
            if is_mask:
                # Показываем маску, только если есть хоть один матч
                if pkg not in self._installed_packages:
                    continue
            else:
                if pkg not in real:
                    continue
            lang_meta = meta.get(self.lang) or meta.get("en")
            if not lang_meta:
                continue
            label, desc, cat, careful = lang_meta
            if is_mask:
                desc += self.t("apps_group_hint")
            if (query and query not in pkg.lower()
                    and query not in label.lower()
                    and query not in desc.lower()):
                continue
            cats.setdefault(cat, []).append((pkg, label, desc, careful))
        if not cats:
            Label(self._apps_inner, text=self.t("apps_empty"),
                  bg=c["panel"], fg=c["gray"], anchor=W,
                  font=("DejaVu Sans", 10)).pack(fill=X, padx=24,
                                                 pady=20)
            self._apps_update_status()
            return
        order = APPS_CATEGORY_ORDER[self.lang]
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
                    command=lambda p=pkg, v=var:
                        self._apps_toggle(p, v))
                chk.pack(side=LEFT)
                text = "%-28s %s" % (pkg, desc)
                if careful:
                    text += "  " + self.t("apps_careful_mark")
                Label(row, text=text, bg=c["panel"], fg=c["fg"],
                      anchor=W,
                      font=("DejaVu Sans Mono", 9)).pack(
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

        real = getattr(self, "_real_installed_packages", None)
        if real is None:
            real = installed_packages_set()

        expanded = expand_package_pattern(list(self.apps_checked), real)
        count = len(expanded)
        size = estimate_packages_size(expanded) if expanded else "0 B"

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
        real = getattr(self, "_real_installed_packages", None)
        if real is None:
            real = installed_packages_set()

        expanded = expand_package_pattern(pkgs, real)
        if not expanded:
            self.log("No packages to remove after expanding patterns",
                     "warning")
            self.msg_queue.put(("apps_result", 0, 0, 0))
            return

        explicit, deps, system_hits, ok = apt_dry_run_purge(expanded)

        if not ok:
            self.log("apt simulation failed — cannot confirm removal list",
                     "error")
            return

        size = estimate_packages_size(explicit + deps)

        lines = [
            self.t("apps_confirm_will_remove"),
            "  " + self._fmt_pkg_list(explicit),
        ]

        if deps:
            lines += [
                "",
                self.t("apps_confirm_deps"),
                "  " + self._fmt_pkg_list(deps),
            ]

        lines += [
            "",
            "%s %s" % (self.t("apps_confirm_size"), size),
        ]

        if system_hits:
            lines += [
                "",
                self.t("apps_confirm_system_warn"),
                "  " + self._fmt_pkg_list(system_hits),
                self.t("apps_confirm_system_hint"),
            ]

        lines += ["", self.t("apps_confirm_no_rollback")]

        body = "\n".join(lines)
        self.msg_queue.put(("apps_confirm", (body, expanded)))

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
        ops = SystemOps(self.sudo, self.state, self.log,
                        self._dry_var.get())

        try:
            ok, freed = ops.apps_purge(pkgs)

            if ok:
                if self._dry_var.get():
                    self.log(self.t("apps_done_dry") % len(pkgs),
                             "success")
                    self.msg_queue.put(("apps_result", 0, len(pkgs), 0))
                else:
                    self.log(self.t("apps_done") % (len(pkgs), freed),
                             "success")
                    self.apps_checked.clear()
                    self.msg_queue.put(("apps_result", len(pkgs), 0, 0))
            else:
                self.log(self.t("apps_failed"), "error")
                self.msg_queue.put(("apps_result", 0, 0, 1))

        except Exception as e:
            self.log("Critical error: %s" % e, "error")
            self.msg_queue.put(("apps_result", 0, 0, 1))

        finally:
            self.msg_queue.put(("running", False))

            if not self._dry_var.get():
                try:
                    real = installed_packages_set()
                except Exception:
                    real = set()

                augmented = set(real)
                for pkg in REMOVABLE_PACKAGES.keys():
                    if any(ch in pkg for ch in "*?["):
                        try:
                            rx = re.compile(fnmatch.translate(pkg))
                            if any(rx.match(ip) for ip in real):
                                augmented.add(pkg)
                        except Exception:
                            pass

                self._real_installed_packages = real
                self._installed_packages = augmented

            self.msg_queue.put(("apps_redraw", None))


# ============================================================================
# БЛОК 18. MAINWINDOW: ПРОКРУТКА, КОПИРОВАНИЕ, ТЕМЫ
# ============================================================================

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
            widget = self.root.winfo_containing(event.x_root,
                                                event.y_root)
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
            def close_menu(_e=None):
                try:
                    menu.unpost()
                except Exception:
                    pass
                try:
                    self.root.unbind("<Button-1>", bind_id)
                except Exception:
                    pass
                try:
                    self.root.unbind("<Escape>", bind_id_esc)
                except Exception:
                    pass

            bind_id = self.root.bind("<Button-1>", close_menu, add="+")
            bind_id_esc = self.root.bind("<Escape>", close_menu, add="+")
            try:
                menu.tk_popup(e.x_root, e.y_root)
            finally:
                try:
                    menu.grab_release()
                except Exception:
                    pass
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
            self.root.option_add("*TCombobox*Listbox.background",
                                 c["panel"])
            self.root.option_add("*TCombobox*Listbox.foreground", c["fg"])
            self.root.option_add("*TCombobox*Listbox.selectBackground",
                                 c["sel"])
            self.root.option_add("*TCombobox*Listbox.selectForeground",
                                 c["fg"])
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
                    w.configure(bg=c["panel"] if inside_any_panel
                                else c["bg"])
                elif cls == "Label":
                    w.configure(bg=c["panel"] if inside_any_panel
                                else c["bg"])
                elif cls == "Checkbutton":
                    w.configure(
                        bg=c["panel"] if inside_any_panel else c["bg"],
                        fg=c["fg"],
                        activebackground=(c["panel"]
                                          if inside_any_panel
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
                            activeforeground=(c["red"]
                                              if zfs_removable
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
                    w.configure(bg=c["panel"] if inside_any_panel
                                else c["bg"])
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
            self._status_view.tag_configure("head",
                                            foreground=c["blue"],
                                            font=("DejaVu Sans Mono", 9,
                                                  "bold"))
            self._status_view.tag_configure("info",
                                            foreground=c["terminal_fg"])
            self._status_view.tag_configure("ok",
                                            foreground=c["green"])
            self._status_view.tag_configure("no",
                                            foreground=c["red"])
            self._status_view.tag_configure("warn",
                                            foreground=c["yellow"])
            self._status_view.tag_configure("muted",
                                            foreground=c["gray"])
        if self._services_tree is not None:
            self._services_tree.tag_configure("ok",
                                              foreground=c["green"])
            self._services_tree.tag_configure("warn",
                                              foreground=c["yellow"])
            self._services_tree.tag_configure("err",
                                              foreground=c["red"])
            self._services_tree.tag_configure("muted",
                                              foreground=c["gray"])
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
        self.pipewire_preset_value.set(
            self._pipewire_preset_label(self.pipewire_preset_key))
        self.rtl_ant_sel_value.set(
            self._rtl_ant_sel_label(self.rtl_ant_sel_key))
        self._rebuild_ui()

    def _rebuild_ui(self):
        saved_opts = {k: v.get() for k, v in self.opts_state.items()}
        saved_mounts = {k: v.get() for k, v in self.mount_state.items()}
        saved_steam = {k: v.get() for k, v in self.steam_state.items()}
        saved_commit = {k: v.get() for k, v in self.commit_state.items()}
        saved_fsck = {k: v.get() for k, v in self.fsck_state.items()}
        try:
            for child in self.root.winfo_children():
                child.destroy()
        except Exception:
            pass
        self.badges = {}
        self.mount_badges = {}
        self.steam_badges = {}
        self.commit_badges = {}
        self.fsck_badges = {}
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
        self._svc_result_lbl = None
        self._apps_result_lbl = None
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
            self.mount_state[k] = BooleanVar(
                value=saved_mounts.get(k, False))
        for k in list(self.steam_state.keys()):
            self.steam_state[k] = BooleanVar(
                value=saved_steam.get(k, False))
        for k in list(self.commit_state.keys()):
            self.commit_state[k] = BooleanVar(
                value=saved_commit.get(k, False))
        for k in list(self.fsck_state.keys()):
            self.fsck_state[k] = BooleanVar(
                value=saved_fsck.get(k, False))
        try:
            self.state.zfs_installed = zfs_packages_installed()
            self.state.zfs_used = zfs_in_use()
            self.state.pipewire_active = pipewire_active()
            self.state.nmi_watchdog_active = nmi_watchdog_active()
            self.state.nmi_watchdog_in_grub = nmi_watchdog_in_grub()
            self.state.rtl_wifi_caps = rtl_wifi_fix_candidates()
            self.state.rtl_wifi_modules = sorted(
                self.state.rtl_wifi_caps.keys())
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
            traceback.print_exc()
            messagebox.showerror(
                APP_NAME,
                "UI rebuild failed:\n%s\n\nSee terminal for traceback."
                % e,
                parent=self.root)
            return
        self._run_bg("services", self._services_work)
        self._run_bg("applied", self._applied_work)
        self._run_bg("status", self._status_work)
        self._run_bg("apps_load", self._apps_load_installed)


# ============================================================================
# БЛОК 19. MAINWINDOW: СЛУЖБЫ
# ============================================================================

    def _services_work(self):
        ops = SystemOps(self.sudo, self.state,
                        lambda m, t="normal": None,
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
            run = (self.t("run_yes") if ac == "active"
                   else self.t("run_no"))
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
            rows.sort(key=lambda r: self._sort_key_for(
                r, self._svc_sort_col),
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
                arrow = (self.t("sort_desc")
                         if self._svc_sort_reverse
                         else self.t("sort_asc"))
                self._services_tree.heading(
                    col, text="%s %s" % (text, arrow))
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
# ============================================================================
# БЛОК 20. MAINWINDOW: БЕЙДЖИ И ZFS
# ============================================================================

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
                    self._style_badge(
                        lbl, True, c,
                        text_override=self.t("applied_manual"))
                else:
                    self._style_badge(lbl, True, c)
                continue
            if k == "corectrl":
                val = self.applied.get("corectrl", None)
                if val is True:
                    self._style_badge(lbl, True, c)
                elif val is False:
                    self._style_badge(lbl, False, c)
                else:
                    self._style_badge(
                        lbl, False, c,
                        text_override=self.t("applied_unknown"))
                    lbl.config(fg=c["yellow"])
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
        for k, lbl in self.fsck_badges.items():
            if lbl is None or not lbl.winfo_exists():
                continue
            self._style_badge(lbl, self.fsck_applied.get(k, False), c)
        if self._thp_lbl is not None and self._thp_lbl.winfo_exists():
            cur = self._thp_current() or "?"
            fmt = self.t("thp_cur")
            self._thp_lbl.config(text=fmt % cur if "%" in fmt else fmt,
                                 fg=c["gray"], bg=c["panel"])

    def _style_badge(self, lbl, ok, c, text_override=None):
        text = text_override if text_override else (
            self.t("applied_yes") if ok else self.t("applied_no"))
        lbl.config(text=text,
                   bg=c["panel"],
                   fg=c["green"] if ok else c["gray"])

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
        ops = SystemOps(self.sudo, self.state, self.log,
                        self._dry_var.get())
        try:
            ok = ops.apply_zfs_remove_packages()
            if ok:
                self.log("ZFS packages removed. Rolling back requires "
                         "'sudo apt install zfsutils-linux'.", "info")
                self.msg_queue.put(("apps_result", 0, 0, 0))
            else:
                self.msg_queue.put(("apps_result", 0, 0, 1))
        except Exception as e:
            self.log("Critical error: %s" % e, "error")
            self.msg_queue.put(("apps_result", 0, 0, 1))
        finally:
            self.state.zfs_installed = zfs_packages_installed()
            self.state.zfs_used = zfs_in_use()
            self.msg_queue.put(("running", False))
            self._run_bg("applied", self._applied_work)
            self._run_bg("status", self._status_work)
            self._run_bg("services", self._services_work)


# ============================================================================
# БЛОК 21. MAINWINDOW: APPLY / ROLLBACK / ВЫБОР
# ============================================================================

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

        steam_sel = [l for l in self.steam_items
                     if self.steam_state[l].get()]

        commit_sel = [mp for mp, v in self.commit_state.items()
                      if v.get()]

        fsck_sel = [mp for mp, v in self.fsck_state.items()
                    if v.get()]

        if (not selected and not mount_sel and not steam_sel
                and not commit_sel and not fsck_sel):
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
            "pipewire_preset": self.pipewire_preset_key,
            "rtl_ant_sel": self.rtl_ant_sel_key,
        }

        dry = self._dry_var.get()

        # Намеренно без messagebox-предупреждений при применении:
        # вся информация — в справке по кнопке «?».

        needs_sudo = bool(mount_sel or commit_sel or steam_sel or fsck_sel
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
                     steam_sel, commit_sel, fsck_sel, params, dry)

    def _apply_work(self, selected, mount_sel, steam_sel, commit_sel,
                    fsck_sel, params, dry):
        ops = SystemOps(self.sudo, self.state, self.log, dry)
        ops.mount_items = self.mount_items
        ops.commit_targets = commit_sel

        total = len(selected) + (1 if mount_sel else 0) + \
            (1 if steam_sel else 0) + (1 if commit_sel else 0) + \
            (1 if fsck_sel else 0)

        if total == 0:
            self._finish_run(0, 0, 0)
            return

        done = 0
        ok_count = skip_count = fail_count = 0

        self.log("=" * 60, "highlight")
        self.log("APPLY START" if self.lang == "en"
                 else "ЗАПУСК ТЮНИНГА", "highlight")

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
                self.msg_queue.put(("progress",
                                    int(done / total * 90)))

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
                self.msg_queue.put(("progress",
                                    int(done / total * 90)))

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
                self.msg_queue.put(("progress",
                                    int(done / total * 90)))

            if fsck_sel:
                self.log("→ %s" % self.t("fsck_title"), "info")
                r = ops.apply_nofsck(fsck_sel)
                if r is False:
                    fail_count += 1
                elif r is None:
                    skip_count += 1
                else:
                    ok_count += 1
                done += 1
                self.msg_queue.put(("progress",
                                    int(done / total * 90)))

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
                self.msg_queue.put(("progress",
                                    int(done / total * 90)))

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

        steam_sel = [l for l in self.steam_items
                     if self.steam_state[l].get()]

        commit_sel = [mp for mp, v in self.commit_state.items()
                      if v.get()]

        fsck_sel = [mp for mp, v in self.fsck_state.items()
                    if v.get()]

        if (not selected and not mount_sel and not steam_sel
                and not commit_sel and not fsck_sel):
            messagebox.showwarning(APP_NAME, self.t("msg_noopt"),
                                   parent=self.root)
            return

        dry = self._dry_var.get()

        needs_sudo = bool(mount_sel or commit_sel or steam_sel or fsck_sel
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
                     steam_sel, commit_sel, fsck_sel, dry)

    def _rollback_work(self, selected, mount_sel, steam_sel, commit_sel,
                       fsck_sel, dry):
        ops = SystemOps(self.sudo, self.state, self.log, dry)
        ops.mount_items = self.mount_items
        ops.commit_targets = commit_sel

        total = len(selected) + (1 if mount_sel else 0) + \
            (1 if steam_sel else 0) + (1 if commit_sel else 0) + \
            (1 if fsck_sel else 0)

        if total == 0:
            self._finish_run(0, 0, 0)
            return

        done = 0
        ok_count = skip_count = fail_count = 0

        self.log("=" * 60, "highlight")
        self.log("ROLLBACK START" if self.lang == "en"
                 else "ЗАПУСК ОТКАТА", "highlight")

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
                self.msg_queue.put(("progress",
                                    int(done / total * 90)))

            if mount_sel:
                r = ops.rollback_mount_opts(mount_sel)
                if r is False:
                    fail_count += 1
                elif r is None:
                    skip_count += 1
                else:
                    ok_count += 1
                done += 1
                self.msg_queue.put(("progress",
                                    int(done / total * 90)))

            if commit_sel:
                r = ops.rollback_commit({})
                if r is False:
                    fail_count += 1
                elif r is None:
                    skip_count += 1
                else:
                    ok_count += 1
                done += 1
                self.msg_queue.put(("progress",
                                    int(done / total * 90)))

            if fsck_sel:
                r = ops.rollback_nofsck(fsck_sel)
                if r is False:
                    fail_count += 1
                elif r is None:
                    skip_count += 1
                else:
                    ok_count += 1
                done += 1
                self.msg_queue.put(("progress",
                                    int(done / total * 90)))

            if steam_sel:
                r = ops.rollback_steam_links(steam_sel)
                if r is False:
                    fail_count += 1
                elif r is None:
                    skip_count += 1
                else:
                    ok_count += 1
                done += 1
                self.msg_queue.put(("progress",
                                    int(done / total * 90)))

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
        self.msg_queue.put(("running", False))
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
        for var in self.fsck_state.values():
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
        for var in self.fsck_state.values():
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
        ops = SystemOps(self.sudo, self.state, self.log,
                        self._dry_var.get())

        ok_count = 0
        skip_count = 0
        fail_count = 0

        for name in names:
            if ops.dry_run:
                ops.log("[DRY RUN] enable %s" % name, "warning")
                skip_count += 1
                continue

            ok1 = ops.sudo_run(["systemctl", "unmask", name],
                               ignore_error=True)
            ok2 = ops.sudo_run(["systemctl", "enable", "--now", name],
                               ignore_error=True)

            if ok1 or ok2:
                ops.log("✓ %s enabled" % name, "success")
                ok_count += 1
            else:
                ops.log("Cannot enable %s" % name, "warning")
                fail_count += 1

        self.msg_queue.put(("svc_result", ok_count, skip_count, fail_count))
        self.msg_queue.put(("statusbar", self.t("done")))

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
        ops = SystemOps(self.sudo, self.state, self.log,
                        self._dry_var.get())

        ok_count = 0
        skip_count = 0
        fail_count = 0

        for name in names:
            if ops.dry_run:
                ops.log("[DRY RUN] disable %s" % name, "warning")
                skip_count += 1
                continue

            ok = ops.sudo_run(["systemctl", "disable", "--now", name],
                              ignore_error=True)

            if (name.startswith("avahi")
                    or name.startswith("bluetooth")
                    or name.startswith("apport")):
                ok = ops.sudo_run(["systemctl", "mask", name],
                                  ignore_error=True) or ok

            if ok:
                ops.log("✓ %s disabled" % name, "success")
                ok_count += 1
            else:
                ops.log("Cannot disable %s" % name, "warning")
                fail_count += 1

        self.msg_queue.put(("svc_result", ok_count, skip_count, fail_count))
        self.msg_queue.put(("statusbar", self.t("done")))

        self._run_bg("services", self._services_work)
        self._run_bg("status", self._status_work)


# ============================================================================
# БЛОК 22. MAINWINDOW: СТАТУС
# ============================================================================

    def _status_work(self):
        try:
            self._status_inner()
        except Exception:
            traceback.print_exc()

    def _status_hardware(self, A):
        rows = [(self.t("st_hw"), "head")]
        bits = 64 if sys.maxsize > 2 ** 32 else 32
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
        rows.append(("%s: %s (%d-bit)"
                     % (self.t("os_lbl"), name or "Linux", bits), "info"))
        rows.append(("%s: %s" % (self.t("cpu_lbl"), cpu_model()),
                     "info"))
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
        rows.append(("%s: %dx%d" % (self.t("screen_lbl"), sw, sh),
                     "info"))
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
        rows.append(("%s: %s" % (self.t("kernel_lbl"),
                                 os.uname().release), "info"))
        rows.append(("%s: %s" % (self.t("de_lbl"), desktop_name()),
                     "info"))
        rows.append((self.t("user_lbl") + ": " + self.state.user_name,
                     "info"))
        rows.append((self.t("home_lbl") + ": " + self.state.user_home,
                     "info"))
        return rows

    def _status_partitions(self):
        rows = [("", "info"), (self.t("st_parts"), "head")]
        seen = {}
        for it in parse_mounts():
            if it["mp"] == "/boot/efi" or (
                    it["fstype"] == "vfat"
                    and it["mp"].startswith("/boot")):
                continue
            seen.setdefault(it["dev"], {"mps": [],
                                        "fstype": it["fstype"]})
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
            val = A.get(k, None)
            if val is True:
                mark = self.t("yes")
                tag = "ok"
            elif val is False:
                mark = self.t("no")
                tag = "no"
            else:
                mark = self.t("unknown")
                tag = "warn"
            extra = ""
            if k == "shutdown_timeout" and val is True:
                cur = self._shutdown_timeout_current()
                if cur and cur != "?":
                    extra = " (%s)" % cur
            elif k == "pipewire" and val is True:
                preset = self._pipewire_preset_current()
                if preset and preset != "manual":
                    p = PIPEWIRE_PRESETS.get(preset, {})
                    label_mode = p.get("label_%s" % self.lang, preset)
                    extra = " (%s)" % label_mode
                elif preset == "manual":
                    extra = (" (%s)"
                             % self.t("applied_manual")
                             .split("(")[-1].rstrip(")"))
            rows.append(("%-42s %-22s %s" % (label, mark + extra, short),
                         tag))
        for mp in self.commit_state:
            val = self._commit_value_for_ui(mp) or \
                self.t("commit_not_set")
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
        for mp in self.fsck_state:
            ok = self.fsck_applied.get(mp, False)
            mark = self.t("yes") if ok else self.t("no")
            rows.append(("%-42s %-14s %s"
                         % (self.t("fsck_short"), mark, mp),
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
                                           self.t("svc_hdr_desc")),
                     "muted"))
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
            ("vm.swappiness", self.t("kern_sw"),
             A.get("swap", False)),
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
            line = "  %-32s %-11s %-30s %-14s" % (p, sv(p), dsc,
                                                  status)
            rows.append((line, "ok" if ok else "no"))
        raw = self._thp_current() or "n/a"
        thp_ok = A.get("thp", False)
        thp_dsc = self.t("kern_thp")
        if len(thp_dsc) > 30:
            thp_dsc = thp_dsc[:27] + "…"
        thp_status = self.t("yes") if thp_ok else self.t("no")
        rows.append(("  %-32s %-11s %-30s %-14s"
                     % ("transparent_hugepage", raw, thp_dsc,
                        thp_status),
                     "ok" if thp_ok else "no"))
        return rows

    def _status_timer(self, ops):
        rows = [("", "info")]
        timer = ops.service_enabled("biweekly-upgrade.timer")
        if timer == "enabled":
            sched = self._schedule_text()
            timer_txt = (sched if sched
                         and sched != self.t("sched_none")
                         else self.t("st_enabled"))
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
            traceback.print_exc()
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


# ============================================================================
# БЛОК 23. MAINWINDOW: ДИАЛОГИ И ЗАКРЫТИЕ
# ============================================================================

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
            elif key == "fsck":
                title = self.t("fsck_title")
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
                                        relief=FLAT, bd=0,
                                        padx=10, pady=10,
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
                                        relief=FLAT, bd=0,
                                        padx=8, pady=8,
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
                                   timeout=5).returncode == 0),
                None)
        if target is None:
            messagebox.showinfo(self.t("viewer"),
                                self.t("msg_nofile") + "\n"
                                + "\n".join(cands),
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


# ============================================================================
# БЛОК 24. ТОЧКА ВХОДА (main)
# ============================================================================

def _find_icon_path():
    """Ищет иконку рядом с приложением или в _MEIPASS (PyInstaller)."""
    candidates = []
    if getattr(sys, "_MEIPASS", None):
        candidates.append(os.path.join(sys._MEIPASS,
                                       "linux-tweaker.png"))
        candidates.append(os.path.join(sys._MEIPASS,
                                       "linux_tweaker.png"))
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, "linux-tweaker.png"))
    candidates.append(os.path.join(here, "linux_tweaker.png"))
    parent = os.path.dirname(here)
    candidates.append(os.path.join(parent, "linux-tweaker.png"))
    candidates.append(os.path.join(parent, "linux_tweaker.png"))
    try:
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        candidates.append(os.path.join(exe_dir, "linux-tweaker.png"))
        candidates.append(os.path.join(exe_dir, "linux_tweaker.png"))
    except Exception:
        pass
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("%s v%s\npython3 linux_tweaker.py [--dry-run]"
              % (APP_NAME, APP_VERSION))
        sys.exit(0)

    if not acquire_lock():
        root = Tk()
        root.withdraw()
        lang = detect_lang()
        messagebox.showwarning(
            APP_NAME,
            "Linux Tweaker is already running." if lang == "en"
            else "Linux Tweaker уже запущен.")
        root.destroy()
        sys.exit(1)

    if os.geteuid() == 0:
        print("WARNING: Linux Tweaker should be run as a normal user, "
              "not as root. Sudo will be requested when needed.",
              file=sys.stderr)

    root = Tk()

    # Иконка приложения (и во всех диалогах тоже)
    icon_path = _find_icon_path()
    if icon_path:
        try:
            logo = PhotoImage(file=icon_path)
            root.iconphoto(True, logo)
            root._icon_ref = logo  # держим ссылку, чтобы Python не удалил
        except Exception as e:
            print("Cannot load icon %s: %s" % (icon_path, e),
                  file=sys.stderr)

    app = MainWindow(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        release_lock()


if __name__ == "__main__":
    main()           
