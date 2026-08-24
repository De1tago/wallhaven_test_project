# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec — сборка Linux-бинарника.
#
# Собирает одиночный исполняемый файл (--onefile). Общие данные
# (CSS, .ui, QML, иконки) упаковываются в _MEIPASS, откуда их
# забирает ядро (core/cache.py) и Qt-интерфейс.
#
# Бинарник содержит ОБА интерфейса (GTK и Qt). Какой именно
# запускать, выбирается автоматически в __main__.py (--ui gtk|qt):
#   * GNOME/прочие Linux → GTK (Libadwaita);
#   * KDE Plasma         → Qt (PySide6/QML);
#   * Windows            → Qt.
#
# ВНИМАНИЕ: PyGObject (GTK4/Adwaita) не умеет полностью
# самоупаковываться. Разделяемые библиотеки GTK4/Adwaita/Libadwaita
# и их typelib'ы должны быть установлены в системе, где запускается
# бинарник (типично для любого Linux-десктопа с GNOME). Qt (PySide6)
# упаковывается вместе с бинарником автоматически.
#
# Сборка:
#   pyinstaller --clean wallhaven-viewer.spec
# Результат: dist/wallhaven-viewer
#
# Требования к среде сборки: установлены PyGObject и PySide6
#   pip install PyGObject PySide6 requests dbus-python pyinstaller

import os

PROJECT_ROOT = os.path.abspath(SPECPATH)
DATA = os.path.join(PROJECT_ROOT, "data")
UI_QT = os.path.join(PROJECT_ROOT, "src", "wallhaven_viewer", "ui_qt")

# (исходный путь, каталог назначения внутри сборки)
datas = [
    (os.path.join(DATA, "css"), "data/css"),
    (os.path.join(DATA, "ui"), "data/ui"),
    (os.path.join(UI_QT, "qml"), "wallhaven_viewer/ui_qt/qml"),
    (os.path.join(UI_QT, "resources"), "wallhaven_viewer/ui_qt/resources"),
]

hiddenimports = [
    "gi",
    "gi.repository.Gtk",
    "gi.repository.Adw",
    "gi.repository.Gio",
    "gi.repository.GLib",
    "gi.repository.Gdk",
    "gi.repository.GdkPixbuf",
    "gi.repository.Pango",
    "gi.repository.HarfBuzz",
    # Qt6 / PySide6 (QML-интерфейс)
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "PySide6.QtNetwork",
    "PySide6.QtWidgets",
    "requests",
    "dbus",
    "dbus.service",
    "dbus.mainloop.glib",
]

a = Analysis(
    [os.path.join(PROJECT_ROOT, "src", "wallhaven_viewer", "__main__.py")],
    pathex=[os.path.join(PROJECT_ROOT, "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide2",
        "PyQt6",
        "PyQt5",
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
