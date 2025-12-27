"""
Основной модуль приложения Wallhaven Viewer.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, Gio, Adw
from utils import resolve_path
from main_window import MainWindow


class WallpaperViewer(Adw.Application):
    """
    Основное приложение Wallhaven Viewer, наследующее Adw.Application.

    Отвечает за инициализацию GTK-окружения, загрузку CSS стилей
    и запуск главного окна.
    """

    def __init__(self):
        super().__init__(application_id="cc.wallhaven.Viewer",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None


    def do_activate(self):
        """Активирует приложение, загружает стили и показывает главное окно."""
        import traceback
        
        try:
            # Загрузка CSS стилей
            css_provider = Gtk.CssProvider()
            try:
                css_provider.load_from_path(resolve_path("style.css"))
                Gtk.StyleContext.add_provider_for_display(
                    Gdk.Display.get_default(),
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
            except Exception as e:
                print(f"Ошибка загрузки style.css: {e}")

            # Создаем и показываем окно (без дублей)
            if not self.window:
             self.window = MainWindow(self)
            self.window.present()

            self.window.present()
        except Exception as e:
            print(f"Ошибка в do_activate: {e}")
            traceback.print_exc()
    
    def do_startup(self):
        """Вызывается при старте приложения."""
        Adw.Application.do_startup(self)


def main():
    """Точка входа приложения."""
    import sys
    import traceback
    
    try:
        app = WallpaperViewer()
        
        # Убедимся, что sys.argv корректен
        args = sys.argv if sys.argv else ['wallhaven-viewer']
        
        # Стандартный запуск приложения. 
        # Он сам вызовет startup и activate, и сам завершится, 
        # когда закроются все окна.
        exit_status = app.run(args)
        sys.exit(exit_status)

    except KeyboardInterrupt:
        print("\nЗавершение по Ctrl+C")
        sys.exit(0)
    except Exception as e:
        print(f"Критическая ошибка при запуске: {e}")
        traceback.print_exc()
        sys.exit(1)