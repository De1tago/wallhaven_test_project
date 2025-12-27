"""
Утилиты для работы с путями, кэшем и файловой системой.
"""

import os
import sys
from gi.repository import GLib


def resolve_path(filename):
    """
    Возвращает путь к файлу, учитывая особенности работы PyInstaller.

    Args:
        filename (str): Имя файла относительно корня проекта.

    Returns:
        str: Абсолютный путь к файлу.
    """
    if getattr(sys, 'frozen', False):
        # Если приложение запущено как скомпилированный файл
        base_dir = sys._MEIPASS
    else:
        # Если приложение запущено как обычный скрипт .py
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, filename)


def get_cache_dir():
    """
    Возвращает путь к папке кэша Wallhaven Viewer.

    Returns:
        str or None: Абсолютный путь к папке кэша или None в случае ошибки.
    """
    cache_dir = os.path.join(GLib.get_user_cache_dir(), "wallhaven_viewer_cache")
    if not os.path.exists(cache_dir):
        try:
            os.makedirs(cache_dir)
        except OSError as e:
            print(f"Ошибка создания папки кэша: {e}")
            return None
    return cache_dir


def extract_wallpaper_id(filename):
    """
    Извлекает ID обоев из имени файла.

    Поддерживает различные форматы:
    - yqqxq7.jpg → yqqxq7
    - wallhaven-yqqxq7.jpg → yqqxq7
    - full-yqqxq7.png → yqqxq7

    Args:
        filename (str): Имя файла.

    Returns:
        str: ID обоев или пустая строка, если не удалось извлечь.
    """
    name = filename.split('.')[0]
    # Удаляем возможные префиксы
    for prefix in ['wallhaven-', 'full-', 'w-', 'wh-']:
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name


def get_cache_path(thumb_url, cache_dir=None):
    """
    Возвращает путь к файлу в кэше для заданного URL миниатюры.

    Args:
        thumb_url (str): URL миниатюры.
        cache_dir (str, optional): Путь к папке кэша. Если None, будет получен автоматически.

    Returns:
        str or None: Путь к файлу в кэше или None, если cache_dir недоступен.
    """
    if not thumb_url:
        return None

    if cache_dir is None:
        cache_dir = get_cache_dir()

    if not cache_dir:
        return None

    filename = thumb_url.split('/')[-1]
    return os.path.join(cache_dir, filename)

