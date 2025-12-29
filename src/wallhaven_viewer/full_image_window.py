"""
Модуль окна полноразмерного просмотра обоев.
"""
import os
import threading
import time
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Gio, GLib, GdkPixbuf

from wallhaven_viewer.utils import resolve_path, wallpaper_portal_available
from wallhaven_viewer.image_loader import ImageLoader
from wallhaven_viewer.api import WallhavenAPI
from gi.repository import Gtk as _Gtk

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
        # Из url вида .../wallhaven-<id>.<ext> извлекаем чистый id (без префикса "wallhaven-")
        raw_name = image_url.split('/')[-1].split('.')[0]
        if raw_name.startswith('wallhaven-'):
            self.wallpaper_id = raw_name[len('wallhaven-'):]
        else:
            self.wallpaper_id = raw_name

        # Создаем новый экземпляр Gtk.Builder для каждого окна
        builder = Gtk.Builder.new_from_file(resolve_path("fullimage.ui"))

        # Загружаем root из нового экземпляра
        content = builder.get_object("root")
        if not content:
            raise RuntimeError("root container not found in fullimage.ui")

        # Устанавливаем root как дочерний элемент окна
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

        # Метаданные и теги
        self.meta_label = builder.get_object("meta_label")
        self.meta_box = builder.get_object("meta_box")
        self.tags_flowbox = builder.get_object("tags_flowbox")
        # Скрываем блок метаданных и тегов до отображения основного контента
        try:
            if self.meta_box:
                self.meta_box.set_visible(False)
        except Exception:
            pass
        if not self.meta_label:
            print("⚠️ meta_label не найден в UI")
        if not self.tags_flowbox:
            print("⚠️ tags_flowbox не найден в UI")

        if self.local_path:
            self.load_image_and_info(local_mode=True)
            self.set_wp_btn.set_sensitive(True)
            self.save_btn.set_sensitive(False)
            self.save_btn.add_css_class("suggested-action")
            self.save_btn.set_label("Скачано")
        else:
            # Запускаем в потоке, так как делаем API запрос и загрузку изображения
            threading.Thread(target=self.load_image_and_info, daemon=True, args=(False,)).start()
        # Инициализируем контейнеры для отложенного показа мета/тегов
        self._pending_tags = []
        self._meta_info = None
        # Поддерживаем кликабельные ссылки в мета-лейбле (для автора)
        try:
            if self.meta_label:
                self.meta_label.set_use_markup(True)
                self.meta_label.connect('activate-link', self.on_meta_activate_link)
        except Exception:
            pass

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
        """Загружает полноразмерное изображение и метаданные.

        Если передан `local_mode`, пытается загрузить из `self.local_path`.
        Иначе запрашивает метаданные у API (с ретраями) и запускает загрузку изображения по сети.
        """
        resolution = ""

        # 1) Локальная загрузка
        if local_mode and self.local_path:
            try:
                with open(self.local_path, 'rb') as f:
                    self.image_data = f.read()
                GLib.idle_add(self.update_title, resolution)
            except Exception as e:
                print(f"Ошибка чтения локального файла: {e}")
                self.image_data = None
        else:
            # 2) Получаем метаданные от API с ретраем
            wallpaper_info = None
            for attempt in range(1, 4):
                try:
                    wallpaper_info = WallhavenAPI.get_wallpaper_info(self.wallpaper_id)
                    if wallpaper_info:
                        break
                except Exception as e:
                    print(f"Ошибка при запросе wallpaper_info (attempt {attempt}): {e}")
                if attempt < 3:
                    time.sleep(0.6)

            resolution = wallpaper_info.get('resolution', '') if wallpaper_info else ''

            # Собираем метаданные
            if wallpaper_info:
                try:
                    file_size = wallpaper_info.get('file_size') or wallpaper_info.get('size') or 0
                    try:
                        size_mb = float(file_size) / (1024 * 1024)
                        size_str = f"{size_mb:.2f} MB"
                    except Exception:
                        size_str = str(file_size)

                    uploader = wallpaper_info.get('uploaded_by') or wallpaper_info.get('uploader') or wallpaper_info.get('user') or ''
                    views = wallpaper_info.get('views', '')
                    favorites = wallpaper_info.get('favorites', '') or wallpaper_info.get('favourites', '')

                    self._meta_info = {
                        'size': size_str,
                        'uploader': uploader,
                        'views': views,
                        'favorites': favorites,
                    }
                except Exception:
                    self._meta_info = None

                # Теги
                try:
                    tags = wallpaper_info.get('tags', []) or []
                    self._pending_tags = tags
                except Exception:
                    self._pending_tags = []
            else:
                self._pending_tags = []

            if wallpaper_info is None:
                GLib.idle_add(self.update_title, resolution)
            else:
                GLib.idle_add(self.update_title, resolution)

            # Загрузка изображения по сети
            def on_image_loaded(img_data):
                if img_data:
                    self.image_data = img_data
                    try:
                        pixbuf = ImageLoader.load_pixbuf_from_bytes(img_data)
                        if pixbuf:
                            GLib.idle_add(self.update_image, pixbuf)
                    except Exception as e:
                        print(f"Ошибка при обработке изображения: {e}")
                        GLib.idle_add(lambda: self.progress_bar.set_visible(False))
                else:
                    GLib.idle_add(lambda: self.spinner.set_visible(False))
                    GLib.idle_add(lambda: self.progress_bar.set_visible(False))

            ImageLoader.download_image(
                self.image_url,
                on_image_loaded,
                progress_callback=self.update_progress,
                timeout=60,
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

    def populate_tags(self, tags):
        """
        Заполняет FlowBox с тегами.

        Args:
            tags (list): Список тегов (словари или строки).
        """
        if not self.tags_flowbox:
            print("⚠️ populate_tags: tags_flowbox is None")
            return

        try:
            # Очистка старых детей
            while True:
                child = self.tags_flowbox.get_first_child()
                if child is None:
                    break
                self.tags_flowbox.remove(child)

            # Добавляем новые теги
            for t in tags:
                try:
                    name = t.get('name') if isinstance(t, dict) else str(t)
                    btn = Gtk.Button.new_with_label(name)
                    btn.add_css_class('pill')

                    def make_on_click(tag_name):
                        def on_click(_btn):
                            try:
                                if hasattr(self.parent_window, 'search_and_present'):
                                    self.parent_window.search_and_present(tag_name)
                                else:
                                    self.parent_window.start_new_search(tag_name)
                                self.parent_window.present()
                            except Exception as e:
                                print(f"Ошибка при клике по тегу: {e}")
                        return on_click

                    btn.connect('clicked', make_on_click(name))

                    try:
                        fb_child = Gtk.FlowBoxChild()
                        fb_child.set_child(btn)
                        self.tags_flowbox.append(fb_child)
                    except Exception:
                        self.tags_flowbox.append(btn)
                except Exception as e:
                    print(f"Ошибка при добавлении тега: {e}")
                    continue
        except Exception as e:
            print(f"Ошибка в populate_tags: {e}")

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

        # После отображения изображения показываем сохранившиеся метаданные и теги
        print("🖼️ update_image: image shown, scheduling meta/tags display")
        # Всегда показываем блок мета/тегов после отображения изображения
        GLib.idle_add(self.show_meta_and_tags)

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

    def show_meta_and_tags(self):
        """
        Показывает блок с метаданными и тегами после того, как основное изображение отображено.
        """
        try:
            print(f"🔔 show_meta_and_tags: meta_info={'set' if self._meta_info else 'empty'}, tags_count={len(self._pending_tags) if self._pending_tags else 0}")
            # Формируем отображение метаданных: размер, автор (кликабельно), просмотры и лайки
            if self.meta_label:
                if self._meta_info:
                    size = self._meta_info.get('size') or ''
                    uploader = self._meta_info.get('uploader') or ''
                    views = self._meta_info.get('views') or ''
                    favorites = self._meta_info.get('favorites') or ''
                    # Если uploader — словарь, попробуем извлечь имя
                    if isinstance(uploader, dict):
                        uploader = uploader.get('username') or uploader.get('name') or str(uploader)
                    # Экранируем текст для безопасной вставки в markup
                    esc = GLib.markup_escape_text
                    parts = []
                    if size:
                        parts.append(f"Размер: {esc(size)}")
                    if uploader:
                        parts.append(f"Автор: <a href='https://wallhaven.cc/user/{esc(uploader)}'>{esc(uploader)}</a>")
                    if views != '':
                        parts.append(f"Просмотры: {esc(str(views))}")
                    if favorites != '':
                        parts.append(f"Лайки: {esc(str(favorites))}")
                    markup = " | ".join(parts) if parts else "Информация недоступна"
                    try:
                        self.meta_label.set_markup(markup)
                    except Exception:
                        try:
                            self.meta_label.set_text(markup)
                        except Exception:
                            self.meta_label.set_text("Информация недоступна")
                else:
                    self.meta_label.set_text("Информация недоступна")
            # Заполняем теги; если их нет — показываем плейсхолдер
            try:
                if self._pending_tags:
                    self.populate_tags(self._pending_tags)
                else:
                    # Очищаем flowbox и добавляем метку "Теги отсутствуют"
                    try:
                        # Очистка через существующую логику
                        self.populate_tags([])
                    except Exception:
                        pass
                    placeholder = Gtk.Label(label="Теги отсутствуют")
                    placeholder.add_css_class('dim-label')
                    try:
                        fb_child = Gtk.FlowBoxChild()
                        fb_child.set_child(placeholder)
                        self.tags_flowbox.append(fb_child)
                    except Exception:
                        self.tags_flowbox.append(placeholder)
            except Exception as e:
                print(f"Ошибка при populate_tags после загрузки: {e}")
            if self.meta_box:
                self.meta_box.set_visible(True)
        except Exception as e:
            print(f"Ошибка при показе мета/тегов: {e}")

    def on_meta_activate_link(self, label, uri):
        # Открываем профиль автора в системном браузере (с фолбеком на xdg-open)
        try:
            Gio.AppInfo.launch_default_for_uri(uri, None)
            return True
        except Exception:
            try:
                GLib.spawn_command_line_async(f"xdg-open '{uri}'")
                return True
            except Exception as e:
                print(f"Не удалось открыть ссылку: {e}")
        return False