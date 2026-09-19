#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# ─── Проверка структуры ─────────────────────────────────────────────────────

if [ ! -f linux_tweaker.py ]; then
    echo "Ошибка: рядом должен быть файл linux_tweaker.py (launcher)" >&2
    exit 1
fi

if [ ! -d linux_tweaker ]; then
    echo "Ошибка: рядом должна быть папка linux_tweaker/ с модулями." >&2
    exit 1
fi

for f in __init__.py __main__.py data.py helpers.py ops.py main_window.py; do
    if [ ! -f "linux_tweaker/$f" ]; then
        echo "Ошибка: в папке linux_tweaker/ нет файла $f" >&2
        exit 1
    fi
done

# ─── Проверка Docker ────────────────────────────────────────────────────────

if ! command -v docker >/dev/null 2>&1; then
    echo "Ошибка: нужен Docker." >&2
    echo "Установите: sudo apt install docker.io" >&2
    echo "Или используйте podman, заменив команды docker на podman." >&2
    exit 1
fi

# ─── Подготовка сборочной папки ─────────────────────────────────────────────

rm -rf build-appimage
mkdir -p build-appimage/src

cp linux_tweaker.py build-appimage/src/
if [ -d linux_tweaker ]; then
    cp -r linux_tweaker build-appimage/src/
fi

# Если рядом есть иконка — копируем её в сборку (и в корень, и в src/)
if [ -f linux-tweaker.png ]; then
    cp linux-tweaker.png build-appimage/linux-tweaker.png
    cp linux-tweaker.png build-appimage/src/linux-tweaker.png
    echo "Иконка linux-tweaker.png будет включена в AppImage."
else
    echo "Иконка linux-tweaker.png не найдена — будет сгенерирована заглушка."
fi

# ─── Скрипт сборки внутри контейнера ────────────────────────────────────────

cat > build-appimage/build-inside.sh <<'EOF'
#!/bin/bash
set -euxo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
    python3 python3-tk python3-pip python3-dev \
    libpython3.8 libpython3.8-dev \
    wget ca-certificates file desktop-file-utils \
    libglib2.0-bin binutils patchelf libfuse2

python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller

# ─── PyInstaller: собираем пакет ────────────────────────────────────────────
if [ -f src/linux-tweaker.png ]; then
    ADD_DATA_ICON="--add-data src/linux-tweaker.png:."
else
    ADD_DATA_ICON=""
fi

pyinstaller \
    --onefile \
    --windowed \
    --name linux-tweaker \
    --hidden-import tkinter \
    --hidden-import _tkinter \
    --collect-all tkinter \
    $ADD_DATA_ICON \
    --clean \
    src/linux_tweaker.py

# ─── Структура AppDir ───────────────────────────────────────────────────────
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

cp dist/linux-tweaker AppDir/usr/bin/linux-tweaker
chmod +x AppDir/usr/bin/linux-tweaker

cat > AppDir/AppRun <<'APPRUN'
#!/bin/sh
SELF_DIR="$(dirname "$(readlink -f "$0")")"
exec "$SELF_DIR/usr/bin/linux-tweaker" "$@"
APPRUN

chmod +x AppDir/AppRun

cat > AppDir/linux-tweaker.desktop <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Linux Tweaker
Comment=System tuning GUI for Linux Mint / Ubuntu / Debian
Exec=linux-tweaker
Icon=linux-tweaker
Terminal=false
Categories=System;Settings;
StartupWMClass=LinuxTweaker
DESKTOP

cp AppDir/linux-tweaker.desktop AppDir/usr/share/applications/

# ─── Иконка: используем готовую, иначе генерируем заглушку ──────────────────
if [ -f linux-tweaker.png ]; then
    cp linux-tweaker.png AppDir/linux-tweaker.png
else
    python3 - <<'PY'
import struct
import zlib

width = 256
height = 256

rgba = b'\x1e\x1e\x1e\xff'

raw = b''
for _ in range(height):
    raw += b'\x00'
    raw += rgba * width

def chunk(chunk_type, data):
    return (
        struct.pack('>I', len(data))
        + chunk_type
        + data
        + struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff)
    )

png = b'\x89PNG\r\n\x1a\n'
png += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
png += chunk(b'IDAT', zlib.compress(raw))
png += chunk(b'IEND', b'')

with open('AppDir/linux-tweaker.png', 'wb') as f:
    f.write(png)
PY
fi

cp AppDir/linux-tweaker.png AppDir/usr/share/icons/hicolor/256x256/apps/linux-tweaker.png

# .DirIcon — используется проводниками для показа иконки самого AppImage
ln -sf linux-tweaker.png AppDir/.DirIcon

# ─── Сборка AppImage через linuxdeploy ──────────────────────────────────────
wget -q https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
wget -q https://github.com/linuxdeploy/linuxdeploy-plugin-appimage/releases/download/continuous/linuxdeploy-plugin-appimage-x86_64.AppImage

chmod +x linuxdeploy-x86_64.AppImage linuxdeploy-plugin-appimage-x86_64.AppImage

export APPIMAGE_EXTRACT_AND_RUN=1
export ARCH=x86_64
export OUTPUT=LinuxTweaker-x86_64.AppImage

./linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage

if [ -n "${HOST_UID:-}" ] && [ -n "${HOST_GID:-}" ]; then
    chown -R "$HOST_UID:$HOST_GID" /build
fi
EOF

chmod +x build-appimage/build-inside.sh

# ─── Запуск сборки в контейнере ─────────────────────────────────────────────

docker run --rm \
    -e HOST_UID="$(id -u)" \
    -e HOST_GID="$(id -g)" \
    -v "$PWD/build-appimage":/build \
    -w /build \
    ubuntu:20.04 \
    bash ./build-inside.sh

cp build-appimage/LinuxTweaker-x86_64.AppImage .
chmod +x LinuxTweaker-x86_64.AppImage

echo ""
echo "Готово."
echo "Файл: $(pwd)/LinuxTweaker-x86_64.AppImage"
echo ""
echo "Запуск:"
echo "  ./LinuxTweaker-x86_64.AppImage"
echo ""
echo "Сухой прогон:"
echo "  ./LinuxTweaker-x86_64.AppImage --dry-run"
