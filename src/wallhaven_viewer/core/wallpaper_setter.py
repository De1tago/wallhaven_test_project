"""
Кроссплатформенная установка обоев рабочего стола.

Модуль сам определяет операционную систему и окружение рабочего стола,
поэтому одинаково работает из GTK- и Qt-интерфейсов.
"""

import os
import subprocess
import sys


def wallpaper_portal_available() -> bool:
    """True, если org.freedesktop.portal.Wallpaper реагирует."""
    try:
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


def _set_via_portal(image_path: str) -> bool:
    """Устанавливает обои через xdg-desktop-portal (Wayland/GNOME/KDE)."""
    if not wallpaper_portal_available():
        return False
    try:
        import dbus
        import dbus.types
        bus = dbus.SessionBus()
        iface = dbus.Interface(
            bus.get_object("org.freedesktop.portal.Desktop",
                           "/org/freedesktop/portal/desktop"),
            "org.freedesktop.portal.Wallpaper")
        fd = os.open(image_path, os.O_RDONLY)
        try:
            iface.SetWallpaperFile(
                "",
                dbus.types.UnixFd(fd),
                {'show-preview': dbus.Boolean(False, variant_level=1)}
            )
            return True
        finally:
            os.close(fd)
    except Exception:
        return False


def _set_gnome(image_path: str) -> bool:
    """Устанавливает обои через GSettings (GNOME / Cinnamon)."""
    uri = "file://" + image_path
    ok = True
    ok = subprocess.run(
        ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri],
        check=False,
    ).returncode == 0 or ok
    subprocess.run(
        ["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri],
        check=False,
    )
    return ok


def _set_kde(image_path: str) -> bool:
    """Устанавливает обои в KDE Plasma через D-Bus (qdbus)."""
    jscript = f"""
    var allDesktops = desktops();
    for (var i = 0; i < allDesktops.length; i++) {{
        var d = allDesktops[i];
        d.wallpaperPlugin = "org.kde.image";
        d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
        d.writeConfig("Image", "file://{image_path}");
    }}
    """
    cmd = ["qdbus", "org.kde.plasmashell", "/PlasmaShell",
           "org.kde.PlasmaShell.evaluateScript", jscript]
    try:
        subprocess.run(cmd, check=False, timeout=15)
        return True
    except Exception:
        return False


def _set_xfce(image_path: str) -> bool:
    """Устанавливает обои в XFCE через xfconf-query."""
    result = subprocess.run(
        ["xfconf-query", "-c", "xfce4-desktop", "-p",
         "/backdrop/screen0/monitor0/workspace0/last-image", "-s", image_path],
        check=False,
    )
    return result.returncode == 0


def _set_windows(image_path: str) -> bool:
    """Устанавливает обои в Windows через Win32 API."""
    import ctypes

    SPI_SETDESKWALLPAPER = 20
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02
    return bool(ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER,
        0,
        image_path,
        SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
    ))


def set_desktop_wallpaper(image_path: str) -> bool:
    """
    Устанавливает указанное изображение в качестве обоев рабочего стола.

    Последовательно пробует: портал рабочего стола, затем специфичный для
    окружения метод (GNOME, KDE, XFCE, Windows).

    Args:
        image_path (str): Путь к локальному файлу изображения.

    Returns:
        bool: True в случае успеха, иначе False.
    """
    image_path = os.path.abspath(image_path)
    if not os.path.exists(image_path):
        return False

    if sys.platform == "win32":
        return _set_windows(image_path)

    if sys.platform.startswith("linux"):
        # 1. Портал — работает на Wayland и большинстве DE (включая Flatpak)
        if _set_via_portal(image_path):
            return True

        # 2. Запасные методы по окружению
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
        if "GNOME" in desktop or "CINNAMON" in desktop:
            return _set_gnome(image_path)
        if "KDE" in desktop:
            return _set_kde(image_path)
        if "XFCE" in desktop:
            return _set_xfce(image_path)
        # Wayland без портала и без опознанного DE — честно сообщаем о неудаче
        return False

    return False