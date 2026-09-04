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
    except FileNotFoundError:
        print("[WallpaperSetter] gdbus not found", flush=True)
        return False
    except Exception as e:
        print(f"[WallpaperSetter] portal check failed: {e}", flush=True)
        return False


def _set_via_portal(image_path: str) -> bool:
    """Устанавливает обои через xdg-desktop-portal (Wayland/GNOME/KDE).

    Пробует два способа:
    1. ``dbus-python`` — передаёт файловый дескриптор (UnixFd).
    2. ``gdbus`` CLI + ``SetWallpaperURI`` — запасной вариант для
       Flatpak и сред, где dbus-python недоступен.
    """
    uri = "file://" + os.path.abspath(image_path)

    # Способ 1: dbus-python (UnixFd)
    try:
        import dbus
        import dbus.types
        try:
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
        except Exception as e:
            print(f"[WallpaperSetter] dbus-python SetWallpaperFile failed: {e}", flush=True)
    except ImportError:
        print("[WallpaperSetter] dbus-python not available, trying gdbus CLI", flush=True)

    # Способ 2: gdbus CLI + SetWallpaperURI (не требует dbus-python)
    cmd = [
        "gdbus", "call", "--session",
        "--dest", "org.freedesktop.portal.Desktop",
        "--object-path", "/org/freedesktop/portal/desktop",
        "--method", "org.freedesktop.portal.Wallpaper.SetWallpaperURI",
        "", uri, "{}",
    ]
    try:
        result = subprocess.run(
            cmd, check=False, timeout=10,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        if result.returncode == 0:
            return True
        print(f"[WallpaperSetter] gdbus SetWallpaperURI failed (rc={result.returncode}): "
              f"{result.stderr.decode(errors='replace').strip()}", flush=True)
    except FileNotFoundError:
        print("[WallpaperSetter] gdbus not found", flush=True)
    except Exception as e:
        print(f"[WallpaperSetter] gdbus SetWallpaperURI exception: {e}", flush=True)

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
    """Устанавливает обои в KDE Plasma через D-Bus или CLI."""
    abs_path = os.path.abspath(image_path)
    uri = "file://" + abs_path

    # 1. plasma-apply-wallpaperimage (Plasma 5.20+ и Plasma 6)
    try:
        result = subprocess.run(
            ["plasma-apply-wallpaperimage", abs_path],
            check=False, timeout=15,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[WallpaperSetter] plasma-apply-wallpaperimage failed: {e}", flush=True)

    # 2. gdbus → org.kde.plasmashell (работает в Flatpak, т.к. gdbus
    #    есть в GNOME-рантайме, а разрешение --talk-name уже выдано)
    jscript = (
        'var allDesktops = desktops();'
        'for (var i = 0; i < allDesktops.length; i++) {'
        '  var d = allDesktops[i];'
        '  d.wallpaperPlugin = "org.kde.image";'
        '  d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");'
        f'  d.writeConfig("Image", "{uri}");'
        '}'
    )
    cmd = [
        "gdbus", "call", "--session",
        "--dest", "org.kde.plasmashell",
        "--object-path", "/PlasmaShell",
        "--method", "org.kde.PlasmaShell.evaluateScript",
        jscript,
    ]
    try:
        result = subprocess.run(
            cmd, check=False, timeout=15,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        if result.returncode == 0:
            return True
        print(f"[WallpaperSetter] gdbus PlasmaShell failed (rc={result.returncode}): "
              f"{result.stderr.decode(errors='replace').strip()}", flush=True)
    except FileNotFoundError:
        print("[WallpaperSetter] gdbus not found", flush=True)
    except Exception as e:
        print(f"[WallpaperSetter] gdbus PlasmaShell exception: {e}", flush=True)

    # 3. D-Bus через qdbus6 (Plasma 6) или qdbus (Plasma 5)
    for qdbus_bin in ("qdbus6", "qdbus"):
        cmd = [qdbus_bin, "org.kde.plasmashell", "/PlasmaShell",
               "org.kde.PlasmaShell.evaluateScript", jscript]
        try:
            result = subprocess.run(
                cmd, check=False, timeout=15,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"[WallpaperSetter] {qdbus_bin} failed: {e}", flush=True)
            continue

    print("[WallpaperSetter] _set_kde: all methods failed", flush=True)
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
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()

        # KDE — нативные методы (plasma-apply-wallpaperimage, gdbus →
        # PlasmaShell, qdbus) надёжнее портала. Портал — запасной вариант.
        if "KDE" in desktop:
            if _set_kde(image_path):
                return True
            return _set_via_portal(image_path)

        # 1. Портал — работает на Wayland и большинстве DE (включая Flatpak)
        if _set_via_portal(image_path):
            return True

        # 2. Запасные методы по окружению
        if "GNOME" in desktop or "CINNAMON" in desktop:
            return _set_gnome(image_path)
        if "XFCE" in desktop:
            return _set_xfce(image_path)
        # Wayland без портала и без опознанного DE — честно сообщаем о неудаче
        return False

    return False