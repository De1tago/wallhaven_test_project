#!/usr/bin/env python3
"""
Wallhaven Desktop Viewer
=======================

Настольное приложение для просмотра и скачивания обоев с wallhaven.cc.
Интерфейсы: GTK4/Libadwaita (GNOME) и Qt6/PySide6 (Windows, KDE Plasma).

Этот файл является обёрткой для обратной совместимости: просто делегирует
управление умной точке входа (__main__.py), которая сама выбирает интерфейс.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from wallhaven_viewer.__main__ import main

if __name__ == "__main__":
    sys.exit(main())