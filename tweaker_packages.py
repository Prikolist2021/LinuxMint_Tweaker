#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Linux Tweaker — список пакетов для вкладки «Приложения».
Формат: REMOVABLE_PACKAGES[имя_пакета] = {lang: (label, desc, category, careful)}
"""

REMOVABLE_PACKAGES = {
    # ─── Офис ───────────────────────────────────────────────────────────
    "libreoffice-core": {
        "ru": ("LibreOffice (ядро)", "Офисный пакет. Удаление освободит ~400 МБ.", "Офис", False),
        "en": ("LibreOffice (core)", "Office suite. Removing frees ~400 MB.", "Office", False)},
    "libreoffice-writer": {
        "ru": ("LibreOffice Writer", "Текстовый редактор.", "Офис", False),
        "en": ("LibreOffice Writer", "Word processor.", "Office", False)},
    "libreoffice-calc": {
        "ru": ("LibreOffice Calc", "Таблицы.", "Офис", False),
        "en": ("LibreOffice Calc", "Spreadsheets.", "Office", False)},
    "libreoffice-impress": {
        "ru": ("LibreOffice Impress", "Презентации.", "Офис", False),
        "en": ("LibreOffice Impress", "Presentations.", "Office", False)},
    "libreoffice-draw": {
        "ru": ("LibreOffice Draw", "Векторная графика.", "Офис", False),
        "en": ("LibreOffice Draw", "Vector graphics.", "Office", False)},
    "libreoffice-base": {
        "ru": ("LibreOffice Base", "Базы данных.", "Офис", False),
        "en": ("LibreOffice Base", "Databases.", "Office", False)},
    "libreoffice-math": {
        "ru": ("LibreOffice Math", "Формулы.", "Офис", False),
        "en": ("LibreOffice Math", "Formulas.", "Office", False)},
    "thunderbird": {
        "ru": ("Thunderbird", "Почтовый клиент. Удаляйте, только если не пользуетесь почтой на ПК.", "Офис", True),
        "en": ("Thunderbird", "Mail client. Remove only if you do not use mail on PC.", "Office", True)},
    "evolution": {
        "ru": ("Evolution", "Почта, календарь, контакты.", "Офис", True),
        "en": ("Evolution", "Mail, calendar, contacts.", "Office", True)},
    "rhythmbox": {
        "ru": ("Rhythmbox", "Музыкальный проигрыватель.", "Офис", False),
        "en": ("Rhythmbox", "Music player.", "Office", False)},

    # ─── Графика ────────────────────────────────────────────────────────
    "pix": {
        "ru": ("Pix", "Просмотрщик изображений из Mint. Можно заменить на gThumb или nomacs.", "Графика", False),
        "en": ("Pix", "Image viewer from Mint. Can be replaced with gThumb or nomacs.", "Graphics", False)},
    "gimp": {
        "ru": ("GIMP", "Редактор изображений. Удаляйте, только если не пользуетесь.", "Графика", True),
        "en": ("GIMP", "Image editor. Remove only if you do not use it.", "Graphics", True)},
    "drawing": {
        "ru": ("Drawing", "Простой редактор изображений из Mint.", "Графика", False),
        "en": ("Drawing", "Simple image editor from Mint.", "Graphics", False)},
    "simple-scan": {
        "ru": ("Simple Scan", "Сканирование. Не нужен, если сканера нет.", "Графика", False),
        "en": ("Simple Scan", "Scanning. Not needed without a scanner.", "Graphics", False)},
    "cheese": {
        "ru": ("Cheese", "Веб-камера. Не нужен, если камеры нет.", "Графика", False),
        "en": ("Cheese", "Webcam. Not needed without a camera.", "Graphics", False)},

    # ─── Интернет ───────────────────────────────────────────────────────
    "hexchat": {
        "ru": ("HexChat", "IRC-клиент.", "Интернет", False),
        "en": ("HexChat", "IRC client.", "Internet", False)},
    "transmission-gtk": {
        "ru": ("Transmission", "Торрент-клиент.", "Интернет", False),
        "en": ("Transmission", "BitTorrent client.", "Internet", False)},
    "matrix": {
        "ru": ("Matrix", "Клиент для децентрализованного чата Matrix.", "Интернет", False),
        "en": ("Matrix", "Client for the decentralized Matrix chat.", "Internet", False)},
    "warpinator": {
        "ru": ("Warpinator", "Обмен файлами в локальной сети (Mint).", "Интернет", False),
        "en": ("Warpinator", "File sharing over local network (Mint).", "Internet", False)},
    "webapp-manager": {
        "ru": ("WebApp Manager", "Создаёт веб-приложения (Mint).", "Интернет", False),
        "en": ("WebApp Manager", "Creates web apps (Mint).", "Internet", False)},
    "firefox": {
        "ru": ("Firefox", "Браузер. Удаляйте, только если пользуетесь другим.", "Интернет", True),
        "en": ("Firefox", "Browser. Remove only if you use another one.", "Internet", True)},

    # ─── Мультимедиа ────────────────────────────────────────────────────
    "rhythmbox-media": {
        "ru": ("Rhythmbox (медиа)", "Музыкальный проигрыватель.", "Мультимедиа", False),
        "en": ("Rhythmbox (media)", "Music player.", "Multimedia", False)},
    "celluloid": {
        "ru": ("Celluloid", "Видеоплеер из Mint.", "Мультимедиа", False),
        "en": ("Celluloid", "Video player from Mint.", "Multimedia", False)},
    "hypnotix": {
        "ru": ("Hypnotix", "IPTV-плеер из Mint.", "Мультимедиа", False),
        "en": ("Hypnotix", "IPTV player from Mint.", "Multimedia", False)},
    "xplayer": {
        "ru": ("Xplayer", "Старый видеоплеер Mint.", "Мультимедиа", False),
        "en": ("Xplayer", "Old video player from Mint.", "Multimedia", False)},
    "vlc": {
        "ru": ("VLC", "Медиаплеер. Удаляйте, только если пользуетесь другим.", "Мультимедиа", True),
        "en": ("VLC", "Media player. Remove only if you use another one.", "Multimedia", True)},
    "audacious": {
        "ru": ("Audacious", "Музыкальный проигрыватель.", "Мультимедиа", False),
        "en": ("Audacious", "Music player.", "Multimedia", False)},

    # ─── Игры ───────────────────────────────────────────────────────────
    "aisleriot": {
        "ru": ("AisleRiot", "Пасьянсы GNOME.", "Игры", False),
        "en": ("AisleRiot", "GNOME solitaire.", "Games", False)},
    "gnome-mahjongg": {
        "ru": ("GNOME Mahjongg", "Маджонг.", "Игры", False),
        "en": ("GNOME Mahjongg", "Mahjongg.", "Games", False)},
    "gnome-mines": {
        "ru": ("GNOME Mines", "Сапёр.", "Игры", False),
        "en": ("GNOME Mines", "Minesweeper.", "Games", False)},
    "gnome-sudoku": {
        "ru": ("GNOME Sudoku", "Судоку.", "Игры", False),
        "en": ("GNOME Sudoku", "Sudoku.", "Games", False)},
    "quadrapassel": {
        "ru": ("Quadrapassel", "Тетрис.", "Игры", False),
        "en": ("Quadrapassel", "Tetris.", "Games", False)},
    "swell-foop": {
        "ru": ("Swell Foop", "Головоломка.", "Игры", False),
        "en": ("Swell Foop", "Puzzle game.", "Games", False)},
    "lightsoff": {
        "ru": ("Lights Off", "Головоломка.", "Игры", False),
        "en": ("Lights Off", "Puzzle game.", "Games", False)},
    "gnome-tetravex": {
        "ru": ("GNOME Tetravex", "Головоломка.", "Игры", False),
        "en": ("GNOME Tetravex", "Puzzle game.", "Games", False)},
    "iagno": {
        "ru": ("Iagno", "Реверси.", "Игры", False),
        "en": ("Iagno", "Reversi.", "Games", False)},
    "gnome-nibbles": {
        "ru": ("GNOME Nibbles", "Змейка.", "Игры", False),
        "en": ("GNOME Nibbles", "Snake.", "Games", False)},
    "four-in-a-row": {
        "ru": ("Four in a Row", "Четыре в ряд.", "Игры", False),
        "en": ("Four in a Row", "Connect four.", "Games", False)},
    "gnome-robots": {
        "ru": ("GNOME Robots", "Логическая игра.", "Игры", False),
        "en": ("GNOME Robots", "Logic game.", "Games", False)},
    "gnome-taquin": {
        "ru": ("GNOME Taquin", "Пятнашки.", "Игры", False),
        "en": ("GNOME Taquin", "Sliding puzzle.", "Games", False)},
    "gnome-2048": {
        "ru": ("GNOME 2048", "Головоломка 2048.", "Игры", False),
        "en": ("GNOME 2048", "2048 puzzle.", "Games", False)},
    "hitori": {
        "ru": ("Hitori", "Логическая головоломка.", "Игры", False),
        "en": ("Hitori", "Logic puzzle.", "Games", False)},
    "tali": {
        "ru": ("Tali", "Игра в кости.", "Игры", False),
        "en": ("Tali", "Dice game.", "Games", False)},

    # ─── Утилиты ────────────────────────────────────────────────────────
    "timeshift": {
        "ru": ("Timeshift", "Резервное копирование системы. Удаляйте, только если не пользуетесь.", "Утилиты", True),
        "en": ("Timeshift", "System backup. Remove only if you do not use it.", "Utilities", True)},
    "thingy": {
        "ru": ("Thingy", "Менеджер электронных книг из Mint.", "Утилиты", False),
        "en": ("Thingy", "E-book manager from Mint.", "Utilities", False)},
    "sticky": {
        "ru": ("Sticky", "Заметки из Mint.", "Утилиты", False),
        "en": ("Sticky", "Notes app from Mint.", "Utilities", False)},
    "baobab": {
        "ru": ("Baobab", "Анализатор использования диска.", "Утилиты", False),
        "en": ("Baobab", "Disk usage analyzer.", "Utilities", False)},
    "gnome-disk-utility": {
        "ru": ("GNOME Disks", "Управление дисками. Удаляйте, только если пользуетесь другим инструментом.", "Утилиты", True),
        "en": ("GNOME Disks", "Disk management. Remove only if you use another tool.", "Utilities", True)},
    "mintbackup": {
        "ru": ("MintBackup", "Резервное копирование (Mint).", "Утилиты", True),
        "en": ("MintBackup", "Backup tool (Mint).", "Utilities", True)},
    "mintstick": {
        "ru": ("MintStick", "Запись ISO на USB (Mint).", "Утилиты", False),
        "en": ("MintStick", "Write ISO to USB (Mint).", "Utilities", False)},
    "mintwelcome": {
        "ru": ("MintWelcome", "Приветственное окно Mint.", "Утилиты", False),
        "en": ("MintWelcome", "Welcome screen (Mint).", "Utilities", False)},

    # ─── Прочее ─────────────────────────────────────────────────────────
    "snapd": {
        "ru": ("Snapd", "Служба Snap-пакетов (Ubuntu). Удаляйте, только если не пользуетесь Snap.", "Прочее", True),
        "en": ("Snapd", "Snap package daemon (Ubuntu). Remove only if you do not use Snap.", "Other", True)},
    "ubuntu-advantage-tools": {
        "ru": ("Ubuntu Advantage", "Служба поддержки Ubuntu Pro.", "Прочее", False),
        "en": ("Ubuntu Advantage", "Ubuntu Pro support service.", "Other", False)},
    "apport": {
        "ru": ("Apport", "Сбор отчётов о сбоях (Ubuntu).", "Прочее", False),
        "en": ("Apport", "Crash report collection (Ubuntu).", "Other", False)},
    "popularity-contest": {
        "ru": ("Popularity Contest", "Анонимная статистика использования пакетов.", "Прочее", False),
        "en": ("Popularity Contest", "Anonymous package usage statistics.", "Other", False)},
}
