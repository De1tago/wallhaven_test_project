"""
Точка входа для запуска:  python -m wallhaven_viewer

Автоматически выбирает графический интерфейс:
  * GTK4/Libadwaita — для GNOME и большинства Linux-окружений;
  * Qt6/PySide6    — для Windows и KDE Plasma.

Выбор можно переопределить флагом  --ui gtk  или  --ui qt .
"""

import argparse
import os
import sys


def choose_ui(ui_flag=None):
    """
    Определяет, какой UI запускать, в порядке приоритета:
      1. явный флаг --ui;
      2. Windows → Qt;
      3. KDE Plasma → Qt;
      4. всё остальное (GNOME и др.) → GTK.
    """
    if ui_flag:
        return ui_flag

    if sys.platform == "win32":
        return "qt"

    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    if "KDE" in desktop:
        return "qt"

    return "gtk"


def _run_gtk(argv):
    """Запускает GTK4/Libadwaita интерфейс."""
    from wallhaven_viewer.ui_gtk.app import WallpaperViewer

    app = WallpaperViewer()
    return app.run(argv)


def _run_qt(argv):
    """Запускает Qt6 (PySide6/QML) интерфейс."""
    from wallhaven_viewer.ui_qt.app import WallhavenQtApp

    app = WallhavenQtApp(argv)
    return app.run()


def main():
    parser = argparse.ArgumentParser(
        description="Wallhaven Desktop Viewer",
        add_help=False,
    )
    parser.add_argument(
        "--ui",
        choices=["gtk", "qt"],
        default=None,
        help="Принудительный выбор интерфейса: gtk (Libadwaita) или qt (PySide6/QML).",
    )
    parser.add_argument(
        "-h", "--help",
        action="help",
        help="Показать эту справку и выйти.",
    )
    args, unknown = parser.parse_known_args()

    # Передаём UI-приложению только его собственные аргументы (без --ui)
    clean_argv = [sys.argv[0]] + unknown

    ui_type = choose_ui(args.ui)
    order = ("gtk", "qt") if ui_type == "gtk" else ("qt", "gtk")
    if args.ui:
        order = (args.ui,)

    try:
        for attempt in order:
            try:
                if attempt == "gtk":
                    return _run_gtk(clean_argv)
                return _run_qt(clean_argv)
            except ImportError as e:
                print(f"[Warning] Не удалось запустить {attempt}-интерфейс ({e}), пробуем следующий...")
    except KeyboardInterrupt:
        print("\nЗавершение по Ctrl+C")
        return 0

    print(
        "Ошибка: не удалось запустить приложение. "
        "Установите PyGObject (GTK) или PySide6 (Qt)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
