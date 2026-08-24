#!/usr/bin/env bash
# Сборка Windows-бинарника (Qt6 / PySide6) через PyInstaller.
#
# ВАЖНО: PyInstaller не умеет кросс-компилировать. Запускать этот
# скрипт нужно на хосте с Windows (Git Bash / WSL не подходит для
# сборки .exe — нужна нативная Windows + Python + PySide6).
#
# 1. Установить Python 3.11+ (https://python.org)
# 2. Создать venv:        python -m venv venv && venv\Scripts\activate
# 3. Установить зависимости:
#       pip install PySide6 requests pyinstaller
# 4. Запустить сборку:    bash scripts/build-windows.sh
#
# Результат: dist/wallhaven-viewer.exe (одиночный исполняемый файл).

set -euo pipefail

DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_ROOT="$( realpath "$DIR/.." )"

cd "$PROJECT_ROOT"

echo "==> Сборка Windows-бинарника (PySide6/Qt6) через PyInstaller..."
pyinstaller --clean wallhaven-viewer-win.spec

echo "==> Готово! Бинарник: dist/wallhaven-viewer.exe"
