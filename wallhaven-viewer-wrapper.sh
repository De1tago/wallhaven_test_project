#!/bin/bash

# Путь к директории, где лежит сам скрипт
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Переходим в папку с бинарником (чтобы относительные пути внутри, если они есть, не ломались)
cd "$SCRIPT_DIR/dist"

# Запускаем бинарник и перенаправляем возможные ошибки в лог-файл для отладки
./WallhavenViewer >> "$SCRIPT_DIR/app.log" 2>&1 &

# Уведомление о запуске (опционально)
notify-send "Wallhaven Viewer" "Приложение запускается..." --icon="$SCRIPT_DIR/app-icon.png"