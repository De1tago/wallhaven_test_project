"""
Утилиты для работы с путями, кэшем и файловой системой.
"""

import os
import sys
from gi.repository import GLib


def resolve_path(filename: str) -> str:
    """
    Ищет ресурс по следующим местам (в указанном порядке):

    1. dev-режим: ../data/(css|ui)/<file> или ../data/<file>
    2. установленный Flatpak: /app/share/wallhaven_viewer/(css|ui)/<file>
    3. рядом с текущим модулем (старое расположение)
    """
    import pathlib

    here = pathlib.Path(__file__).parent
    project_root = (here / ".." / "..").resolve()
    dev_data = project_root / "data"

    # 1. поиск в каталоге data/
    candidates = [
        dev_data / filename,                   # data/<file>
        dev_data / "css" / filename,           # data/css/<file>
        dev_data / "ui" / filename,            # data/ui/<file>
    ]

    # 2. путь внутри Flatpak
    flatpak_base = pathlib.Path("/app/share/wallhaven_viewer")
    candidates += [
        flatpak_base / filename,
        flatpak_base / "css" / filename,
        flatpak_base / "ui" / filename,
    ]

    # 3. исторический — рядом с .py
    candidates.append(here / filename)

    for path in candidates:
        if path.exists():
            return str(path)

    # fallback — вернём абсолютный путь для отладки
    return str((here / filename).resolve())

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

import os, subprocess

def wallpaper_portal_available() -> bool:
    """True, если org.freedesktop.portal.Wallpaper реагирует."""
    try:
        # qdbus/dbus-send отсутствуют в некоторых системах; ловим любые ошибки
        out = subprocess.check_output(
            ["gdbus", "call", "--session",
             "--dest", "org.freedesktop.portal.Desktop",
             "--object-path", "/org/freedesktop/portal/desktop",
             "--method", "org.freedesktop.DBus.Properties.Get",
             "org.freedesktop.portal.Wallpaper", "version"],
            stderr=subprocess.DEVNULL,
            timeout=2
        )
        return b"(" in out  # ответ пришёл
    except Exception:
        return False