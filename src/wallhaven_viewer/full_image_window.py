"""
Модуль окна полноразмерного просмотра обоев.
"""
import os
import threading
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Gio, GLib, GdkPixbuf

from wallhaven_viewer.utils import resolve_path, wallpaper_portal_available
from wallhaven_viewer.image_loader import ImageLoader
from wallhaven_viewer.api import WallhavenAPI

class FullImageWindow(Gtk.Window):
    """
    Окно для полноразмерного просмотра и управления обоями.

    Осуществляет загрузку полного изображения, его сохранение на диск
    и установку в качестве обоев рабочего стола.

    Args:
        parent: Ссылка на родительское окно.
        image_url (str): URL-адрес полноразмерного изображения.
        download_path (str): Путь для сохранения файлов по умолчанию.
        local_path (str, optional): Локальный путь к файлу, если он уже скачан.
    """

    def __init__(self, parent, image_url, download_path, local_path=None):
        super().__init__(transient_for=parent)
        self.parent_window = parent
        self.image_url = image_url
        self.download_path = download_path
        self.local_path = local_path
        self.image_data = None
        self.wallpaper_id = image_url.split('/')[-1].split('.')[0]

        ui_path = resolve_path("fullimage.ui")
        builder = Gtk.Builder.new_from_file(resolve_path("fullimage.ui"))

        content = builder.get_object("root")
        if not content:
            raise RuntimeError("root container not found in fullimage.ui")

        self.set_child(content)

        xml_window = builder.get_object("full_image_window")

        w, h = xml_window.get_default_size()
        self.set_default_size(w, h)
        self.set_title(f"Wallhaven - ID: {self.wallpaper_id}")

        content = xml_window.get_child()
        if content:
            content.unparent()  # Это критически важно!
            self.set_child(content)

        self.picture = builder.get_object("picture")
        self.spinner = builder.get_object("spinner")
        self.save_btn = builder.get_object("save_btn")
        self.progress_bar = builder.get_object("progress_bar")

        self.set_wp_btn = builder.get_object("set_wp_btn")

        self.save_btn.connect("clicked", self.on_save_clicked)
        self.set_wp_btn.connect("clicked", self.on_set_wallpaper_clicked)

        if self.local_path:
            self.load_image_and_info(local_mode=True)
            self.set_wp_btn.set_sensitive(True)
            self.save_btn.set_sensitive(False)
            self.save_btn.add_css_class("suggested-action")
            self.save_btn.set_label("Скачано")
        else:
            # Запускаем в потоке, так как делаем API запрос и загрузку изображения
            threading.Thread(target=self.load_image_and_info, daemon=True, args=(False,)).start()

    def update_progress(self, current_bytes, total_bytes):
        """
        Обновляет прогресс-бар во время загрузки полноразмерного изображения.

        Args:
            current_bytes (int): Количество загруженных байт.
            total_bytes (int): Общий размер файла.
        """
        if total_bytes > 0:
            fraction = current_bytes / total_bytes
            percent = int(fraction * 100)
            self.progress_bar.set_fraction(fraction)
            self.progress_bar.set_text(f"Загрузка: {percent}%")
            self.progress_bar.set_visible(True)
            self.spinner.set_visible(False)

    def load_image_and_info(self, local_mode=False):
        """
        Загружает полноразмерное изображение (локально или по сети) и получает метаданные (разрешение).

        Args:
            local_mode (bool, optional): Если True, пытается загрузить из local_path.
        """
        resolution = ""

        # 1. Загрузка данных (API или локально)
        if local_mode and self.local_path:
            try:
                with open(self.local_path, "rb") as f:
                    self.image_data = f.read()
                GLib.idle_add(self.update_title, resolution)
            except Exception as e:
                print(f"Ошибка чтения локального файла: {e}")
                self.image_data = None
        else:
            # Запрос API для разрешения
            try:
                wallpaper_info = WallhavenAPI.get_wallpaper_info(self.wallpaper_id)
                resolution = wallpaper_info.get("resolution", "") if wallpaper_info else ""
                GLib.idle_add(self.update_title, resolution)
            except Exception:
                GLib.idle_add(self.update_title, resolution)

            # Загрузка по сети
            def on_image_loaded(img_data):
                if img_data:
                    self.image_data = img_data
                    try:
                        pixbuf = ImageLoader.load_pixbuf_from_bytes(img_data)
                        if pixbuf:
                            GLib.idle_add(self.update_image, pixbuf)
                    except Exception as e:
                        print(f"Ошибка: {e}")
                        GLib.idle_add(lambda: self.progress_bar.set_visible(False))
                else:
                    GLib.idle_add(lambda: self.spinner.set_visible(False))
                    GLib.idle_add(lambda: self.progress_bar.set_visible(False))

            ImageLoader.download_image(
                self.image_url,
                on_image_loaded,
                progress_callback=self.update_progress,
                timeout=60
            )

        # 2. Обновление UI для локального режима
        if local_mode and self.image_data:
            try:
                pixbuf = ImageLoader.load_pixbuf_from_bytes(self.image_data)
                if pixbuf:
                    GLib.idle_add(self.update_image, pixbuf)
            except Exception as e:
                print(f"Ошибка: {e}")
                GLib.idle_add(lambda: self.progress_bar.set_visible(False))

    def update_title(self, resolution):
        """Обновляет заголовок окна с информацией о разрешении."""
        res_str = f" ({resolution})" if resolution else ""
        self.set_title(f"Wallhaven - ID: {self.wallpaper_id}{res_str}")

    def update_image(self, pixbuf):
        """
        Отображает загруженное изображение в Gtk.Picture.

        Args:
            pixbuf (GdkPixbuf.Pixbuf): Загруженное изображение.
        """
        texture = Gdk.Texture.new_for_pixbuf(pixbuf)

        self.picture.set_paintable(texture)
        self.spinner.set_visible(False)
        self.progress_bar.set_visible(False)

        if not self.local_path:
            self.save_btn.set_sensitive(True)
        self.set_wp_btn.set_sensitive(True)

    def on_save_clicked(self, btn):
        """Обработчик нажатия кнопки сохранения. Сохраняет файл либо по умолчанию, либо через диалог."""
        if not self.image_data:
            return

        # Определение формата
        content_type = ImageLoader.get_image_format_from_bytes(self.image_data)
        ext = '.jpg' if 'jpeg' in content_type else '.png'
        name = self.wallpaper_id + ext

        if self.download_path and os.path.exists(self.download_path):
            try:
                local_path = os.path.join(self.download_path, name)
                with open(local_path, "wb") as f:
                    f.write(self.image_data)

                self.local_path = local_path
                self.save_btn.set_label("Скачано")
                self.save_btn.set_sensitive(False)
                self.set_wp_btn.set_sensitive(True)

                # Обновляем список скачанных файлов в главном окне
                self.parent_window.scan_downloaded_wallpapers()
                self.parent_window.flowbox.invalidate_filter()

            except Exception:
                self.open_dialog(name)
        else:
            self.open_dialog(name)

    def open_dialog(self, name):
        """Открывает диалог сохранения файла, если путь по умолчанию недоступен."""
        d = Gtk.FileDialog()
        d.set_initial_name(name)
        d.save(self, None, self.on_save_finish)

    def on_save_finish(self, d, res):
        """Обработчик завершения диалога сохранения."""
        try:
            f = d.save_finish(res)
            if f:
                local_path = f.get_path()
                with open(local_path, "wb") as file:
                    file.write(self.image_data)

                self.local_path = local_path
                self.save_btn.set_label("Скачано")
                self.save_btn.set_sensitive(False)
                self.set_wp_btn.set_sensitive(True)

                # Обновляем список скачанных файлов в главном окне
                self.parent_window.scan_downloaded_wallpapers()
                self.parent_window.flowbox.invalidate_filter()
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    from wallhaven_viewer.utils import wallpaper_portal_available

    def on_set_wallpaper_clicked(self, _btn):
        if not self.local_path or not os.path.exists(self.local_path):
            print("❌ Нет локального файла — нельзя установить обои")
            return

        used_portal = False
        if wallpaper_portal_available() and os.getenv("FLATPAK_ID"):
            # пробуем портал ТОЛЬКО внутри Flatpak и если backend отвечает
            try:
                import dbus, dbus.types
                bus = dbus.SessionBus()
                iface = dbus.Interface(
                    bus.get_object("org.freedesktop.portal.Desktop",
                                "/org/freedesktop/portal/desktop"),
                    "org.freedesktop.portal.Wallpaper")
                fd = os.open(self.local_path, os.O_RDONLY)
                try:
                    iface.SetWallpaperFile(
                        "",
                        dbus.types.UnixFd(fd),
                        {'show-preview': dbus.Boolean(False, variant_level=1)}
                    )
                    print(f"✅ Обои установлены через портал: {self.local_path}")
                    used_portal = True
                finally:
                    os.close(fd)
            except Exception as e:
                print(f"⚠️  Портал недоступен ({e}); fallback на GSettings")

        if not used_portal:
            self._set_wallpaper_worker(self.local_path)

    def _set_wallpaper_worker(self, path):
        """
        Устанавливает обои через GSettings.
        Безопасно проверяет доступность ключей.
        """
        try:
            # Преобразуем путь в file:// URI (экранируем пробелы и спецсимволы)
            file_uri = Gio.File.new_for_path(os.path.abspath(path)).get_uri()

            # Создаём Settings
            settings = Gio.Settings.new('org.gnome.desktop.background')

            # Проверяем схему
            schema_source = Gio.SettingsSchemaSource.get_default()
            schema = schema_source.lookup('org.gnome.desktop.background', True)

            if not schema:
                print("❌ Схема org.gnome.desktop.background не найдена")
                return

            # Устанавливаем обои
            if schema.has_key('picture-uri-dark'):
                settings.set_string('picture-uri', file_uri)
                settings.set_string('picture-uri-dark', file_uri)
                print(f"✅ Обои установлены (с поддержкой тёмного режима): {file_uri}")
            else:
                settings.set_string('picture-uri', file_uri)
                print(f"✅ Обои установлены: {file_uri}")

        except Exception as e:
            print(f"❌ Ошибка установки обоев: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()