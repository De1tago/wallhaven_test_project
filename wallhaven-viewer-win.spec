# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec — сборка Windows-бинарника (Qt6 / PySide6 + QML).
#
# GTK-интерфейс на Windows не нужен, поэтому PyGObject исключён.
# Упаковываются QML-файлы, SVG-иконки и резервная тема Breeze.
#
# Сборка (на Windows, в виртуальном окружении с PySide6):
#   pyinstaller --clean wallhaven-viewer-win.spec
# Результат: dist\wallhaven-viewer.exe
#
# Примечание: кросс-компиляция из Linux не поддерживается PyInstaller —
# собирать нужно на хосте с Windows.

import os

PROJECT_ROOT = os.path.abspath(SPECPATH)
SRC = os.path.join(PROJECT_ROOT, "src", "wallhaven_viewer")
UI_QT = os.path.join(SRC, "ui_qt")

datas = [
    (os.path.join(UI_QT, "qml"), "wallhaven_viewer/ui_qt/qml"),
    (os.path.join(UI_QT, "resources"), "wallhaven_viewer/ui_qt/resources"),
]

hiddenimports = [
    "requests",
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtNetwork",
    "PySide6.QtWidgets",
    "wallhaven_viewer.ui_qt.app",
    "wallhaven_viewer.ui_qt.backend",
]

a = Analysis(
    [os.path.join(SRC, "__main__.py")],
    pathex=[os.path.join(PROJECT_ROOT, "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyGObject",
        "gi",
        "dbus",
        "tkinter",
        "unittest",
        "test",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="wallhaven-viewer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
