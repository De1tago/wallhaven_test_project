#!/usr/bin/env bash
set -euo pipefail

DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_ROOT="$( realpath "$DIR/.." )"

cd "$PROJECT_ROOT"

echo "==> Активация виртуального окружения..."
if [ -d .venv ]; then
    source .venv/bin/activate
elif [ -d venv ]; then
    source venv/bin/activate
fi

echo "==> Установка зависимостей для сборки..."
pip install -q pyinstaller packaging setuptools

echo "==> Сборка бинарника через PyInstaller..."
pyinstaller --clean wallhaven-viewer.spec

BIN="$(realpath dist/wallhaven-viewer)"

echo "==> Регистрация приложения в системе (~/.local/share)..."
# Под нативным Wayland KDE KWin берёт иконку окна НЕ из setWindowIcon(),
# а из .desktop-файла, сопоставленного по app_id (Desktop File Name).
# Регистрируем .desktop + иконки, чтобы в панели задач была наша иконка.
APP_ID="cc.wallhaven.Viewer"
APPS_DIR="$HOME/.local/share/applications"
ICON_ROOT="$HOME/.local/share/icons/hicolor"
mkdir -p "$APPS_DIR" "$ICON_ROOT/512x512/apps" \
         "$ICON_ROOT/256x256/apps" "$ICON_ROOT/128x128/apps"
cat > "$APPS_DIR/$APP_ID.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Wallhaven Viewer
Comment=Просмотр и загрузка обоев с Wallhaven.cc
Exec=$BIN
Icon=$APP_ID
Terminal=false
Categories=Graphics;Utility;
Keywords=wallpaper;wallhaven;background;
StartupNotify=true
EOF
cp assets/app-icon.png "$ICON_ROOT/512x512/apps/$APP_ID.png"
[ -f assets/ico/256x256.png ] && \
    cp assets/ico/256x256.png "$ICON_ROOT/256x256/apps/$APP_ID.png"
[ -f assets/ico/128x128.png ] && \
    cp assets/ico/128x128.png "$ICON_ROOT/128x128/apps/$APP_ID.png"

echo "==> Готово! Бинарник в dist/wallhaven-viewer"
echo "    Запуск: $BIN"
echo "    .desktop: $APPS_DIR/$APP_ID.desktop"
