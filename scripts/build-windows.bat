@echo off
REM Сборка Windows-бинарника (Qt6 / PySide6) через PyInstaller.
REM Запускать на нативной Windows (cmd или PowerShell).

setlocal
cd /d "%~dp0\.."

if not exist "venv\Scripts\activate.bat" (
    echo ==^> Создание виртуального окружения...
    python -m venv venv
)

echo ==^> Активация venv...
call venv\Scripts\activate.bat

echo ==^> Установка зависимостей...
pip install PySide6 requests pyinstaller

echo ==^> Сборка бинарника (PySide6/Qt6)...
pyinstaller --clean wallhaven-viewer-win.spec

echo ==^> Готово! Бинарник: dist\wallhaven-viewer.exe
endlocal
