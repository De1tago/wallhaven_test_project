#!/usr/bin/env python3
"""
Wallhaven Desktop Viewer
========================

Настольное приложение для просмотра и скачивания обоев с wallhaven.cc.
Использует GTK 4 (PyGObject) для интерфейса и Requests для работы с API.

Этот файл является обёрткой для обратной совместимости.
Вся функциональность перенесена в модульную структуру.
"""

# Импортируем все необходимые классы из новых модулей для обратной совместимости
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from wallhaven_viewer.app import WallpaperViewer, main
...

# Экспортируем основные классы и функции для обратной совместимости
__all__ = ['WallpaperViewer', 'main']

if __name__ == "__main__":
    main()