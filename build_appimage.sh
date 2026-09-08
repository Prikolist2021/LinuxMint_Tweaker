   #!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f tuneup_gui.py ]; then
    echo "Ошибка: рядом должен быть файл tuneup_gui.py" >&2
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "Ошибка: нужен Docker." >&2
    echo "Установите: sudo apt install docker.io" >&2
    echo "Или используйте podman, заменив команды docker на podman." >&2
    exit 1
fi

rm -rf build-appimage
mkdir -p build-appimage/src

cp tuneup_gui.py build-appimage/src/

cat > build-appimage/build-inside.sh <<'EOF'
#!/bin/bash
set -euxo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update

apt-get install -y --no-install-recommends python3 python3-tk python3-pip libpython3.8 libpython3.8-dev wget ca-certificates file desktop-file-utils libglib2.0-bin binutils patchelf

python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller

pyinstaller \
    --onefile \
    --windowed \
    --name system-tuneup \
    --hidden-import tkinter \
    src/tuneup_gui.py

mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

cp dist/system-tuneup AppDir/usr/bin/system-tuneup
chmod +x AppDir/usr/bin/system-tuneup

cat > AppDir/AppRun <<'APPRUN'
#!/bin/sh
SELF_DIR="$(dirname "$(readlink -f "$0")")"
exec "$SELF_DIR/usr/bin/system-tuneup" "$@"
APPRUN

chmod +x AppDir/AppRun

cat > AppDir/system-tuneup.desktop <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=System Tuneup
Comment=System tuning GUI for Linux Mint/Ubuntu/Debian
Exec=system-tuneup
Icon=system-tuneup
Terminal=false
Categories=System;Settings;
DESKTOP

cp AppDir/system-tuneup.desktop AppDir/usr/share/applications/

# Генерируем простую тёмную иконку 256x256 без внешних зависимостей
python3 - <<'PY'
import struct
import zlib

width = 256
height = 256

# Цвет фона: тёмный, примерно как интерфейс программы
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

with open('AppDir/system-tuneup.png', 'wb') as f:
    f.write(png)
PY

cp AppDir/system-tuneup.png AppDir/usr/share/icons/hicolor/256x256/apps/system-tuneup.png

wget -q https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
wget -q https://github.com/linuxdeploy/linuxdeploy-plugin-appimage/releases/download/continuous/linuxdeploy-plugin-appimage-x86_64.AppImage

chmod +x linuxdeploy-x86_64.AppImage linuxdeploy-plugin-appimage-x86_64.AppImage

export APPIMAGE_EXTRACT_AND_RUN=1
export ARCH=x86_64
export OUTPUT=SystemTuneup-x86_64.AppImage

./linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage

if [ -n "${HOST_UID:-}" ] && [ -n "${HOST_GID:-}" ]; then
    chown -R "$HOST_UID:$HOST_GID" /build
fi
EOF

chmod +x build-appimage/build-inside.sh

docker run --rm \
    -e HOST_UID="$(id -u)" \
    -e HOST_GID="$(id -g)" \
    -v "$PWD/build-appimage":/build \
    -w /build \
    ubuntu:20.04 \
    bash ./build-inside.sh

cp build-appimage/SystemTuneup-x86_64.AppImage .
chmod +x SystemTuneup-x86_64.AppImage

echo ""
echo "Готово."
echo "Файл: $(pwd)/SystemTuneup-x86_64.AppImage"
echo ""
echo "Запуск:"
echo "  ./SystemTuneup-x86_64.AppImage"
echo ""
echo "Сухой прогон:"
echo "  ./SystemTuneup-x86_64.AppImage --dry-run"
