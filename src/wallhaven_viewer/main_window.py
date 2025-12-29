"""
Модуль главного окна приложения.
"""

import os
import glob
import threading
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, Gio, GLib, GdkPixbuf, Adw
from wallhaven_viewer.utils import resolve_path, get_cache_path, extract_wallpaper_id, clean_cache
from wallhaven_viewer.config import load_settings, save_settings, RESOLUTION_OPTIONS, RATIO_OPTIONS, SORT_OPTIONS
from wallhaven_viewer.api import WallhavenAPI
from wallhaven_viewer.image_loader import ImageLoader
from wallhaven_viewer.settings_window import SettingsWindow
from wallhaven_viewer.full_image_window import FullImageWindow


class MainWindow(Adw.ApplicationWindow):
    """
    Главное окно приложения.

    Отображает сетку обоев, панель фильтров и управляет логикой
    поиска, загрузки миниатюр, а также переключением между режимами
    API-поиска и локальной библиотеки.
    """

    def __init__(self, app):
        """
        Инициализирует главное окно, загружает UI-файлы и настройки.

        Args:
            app: Экземпляр Gtk.Application.
        """
        super().__init__(application=app)
        self.set_title("Wallhaven Viewer")
        self.set_default_size(1200, 850)
        # Обработчик закрытия окна
        self.connect("close-request", self.on_close_request)
        self.style_manager = Adw.StyleManager.get_default()

        self.current_page = 1
        self.settings = load_settings()
        self.current_query = self.settings['last_query']
        self.is_loading = False
        self.has_more_pages = True

        # Словарь {ID: local_path}
        self.downloaded_files = {}
        # Множество ID для быстрых проверок в UI
        self.downloaded_ids = set()

        self.is_downloaded_mode = False

        # ЗАГРУЗКА UI
        ui_path = resolve_path("mainwindow.ui")
        if not os.path.exists(ui_path):
            print(f"КРИТИЧЕСКАЯ ОШИБКА: Файл {ui_path} не найден!")
            return

        builder = Gtk.Builder.new_from_file(ui_path)

        content = builder.get_object("root")
        if not content:
            raise RuntimeError("root container not found in mainwindow.ui")

        self.set_content(content)

        self.builder = builder
        self.entry = builder.get_object("entry")
        self.btn_search = builder.get_object("btn_search")

        self.primary_menu_btn = builder.get_object("primary_menu_btn")
        self.setup_menu_actions()

        self.btn_general = builder.get_object("btn_general")
        self.btn_anime = builder.get_object("btn_anime")
        self.btn_people = builder.get_object("btn_people")
        self.btn_sfw = builder.get_object("btn_sfw")
        self.btn_sketchy = builder.get_object("btn_sketchy")
        self.btn_nsfw = builder.get_object("btn_nsfw")
        self.res_dropdown = builder.get_object("res_dropdown")
        self.ratio_dropdown = builder.get_object("ratio_dropdown")
        self.sort_dropdown = builder.get_object("sort_dropdown")
        self.infobar = builder.get_object("infobar")
        self.infobar_label = builder.get_object("infobar_label")
        self.scrolled = builder.get_object("scrolled")
        self.connect("notify::default-width", lambda *args: GLib.idle_add(self.check_if_can_load_next_page))
        self.flowbox = builder.get_object("flowbox")
        self.bottom_spinner = builder.get_object("bottom_spinner")

        self.btn_downloaded = builder.get_object("btn_downloaded")

        self.flowbox.set_valign(Gtk.Align.START)

        # Настройка виджетов
        self.entry.set_text(self.current_query)
        self.btn_general.set_active(self.settings['cat_general'].lower() == 'true')
        self.btn_anime.set_active(self.settings['cat_anime'].lower() == 'true')
        self.btn_people.set_active(self.settings['cat_people'].lower() == 'true')
        self.btn_sfw.set_active(self.settings['purity_sfw'].lower() == 'true')
        self.btn_sketchy.set_active(self.settings['purity_sketchy'].lower() == 'true')
        self.btn_nsfw.set_active(self.settings['purity_nsfw'].lower() == 'true')

        res_options_list = Gtk.StringList.new([label for label, _ in RESOLUTION_OPTIONS])
        self.res_dropdown.set_model(res_options_list)
        self.res_dropdown.set_selected(int(self.settings['resolution_index']))

        ratio_options_list = Gtk.StringList.new([label for label, _ in RATIO_OPTIONS])
        self.ratio_dropdown.set_model(ratio_options_list)
        self.ratio_dropdown.set_selected(int(self.settings['ratio_index']))

        sort_options_list = Gtk.StringList.new(SORT_OPTIONS)
        self.sort_dropdown.set_model(sort_options_list)
        self.sort_dropdown.set_selected(int(self.settings['sort_index']))

        # Подключение сигналов
        self.btn_search.connect("clicked", self.on_search_clicked)
        self.btn_downloaded.connect("clicked", self.on_downloaded_toggle)

        btn_infobar_close = builder.get_object("btn_infobar_close")
        if btn_infobar_close:
            btn_infobar_close.connect("clicked", self.on_infobar_close_clicked)

        self.btn_sketchy.connect("clicked", self.check_api_key_on_purity_change)
        self.btn_nsfw.connect("clicked", self.check_api_key_on_purity_change)
        self.res_dropdown.connect("notify::selected", self.on_filter_changed)
        self.ratio_dropdown.connect("notify::selected", self.on_filter_changed)
        self.sort_dropdown.connect("notify::selected", self.on_filter_changed)
        self.entry.connect("activate", self.on_search_clicked)

        self.v_adj = self.scrolled.get_vadjustment()
        self.v_adj.connect("value-changed", self.on_scroll_changed)

        cols = int(self.settings.get('columns', 4))
        self.flowbox.set_min_children_per_line(cols)
        self.flowbox.set_max_children_per_line(cols)

        # --- ЗАПУСК ---
        # Асинхронный запуск очистки кэша (файлы старше 7 дней)
        try:
            import threading
            threading.Thread(target=lambda: clean_cache(7, 300), daemon=True).start()
        except Exception:
            pass

        self.scan_downloaded_wallpapers()
        self.start_new_search(self.current_query)

    def search_and_present(self, query):
        """Внешний вызов поиска — устанавливает текст в строке поиска и запускает поиск."""
        try:
            self.entry.set_text(query)
            self.entry.grab_focus()
            self.start_new_search(query)
            self.present()
        except Exception as e:
            print(f"Ошибка при запуске поиска по тегу: {e}")

    def setup_menu_actions(self):
        """Создает меню и привязывает действия (Actions)."""
        # 1. Создаем группу действий для окна
        action_group = Gio.SimpleActionGroup()
        self.insert_action_group("win", action_group)

        # 2. Действие "Настройки"
        action_settings = Gio.SimpleAction.new("preferences", None)
        action_settings.connect("activate", self.open_settings)
        action_group.add_action(action_settings)

        # 3. Действие "О приложении"
        action_about = Gio.SimpleAction.new("about", None)
        action_about.connect("activate", self.show_about_dialog)
        action_group.add_action(action_about)

        # 4. Создаем модель меню
        menu = Gio.Menu()
        menu.append("Настройки", "win.preferences")
        menu.append("О приложении", "win.about")

        # 5. Привязываем меню к кнопке
        self.primary_menu_btn.set_menu_model(menu)

    def scan_downloaded_wallpapers(self):
        """
        Сканирует папку загрузок и индексирует все изображения по ID.
        Поддерживает: wallhaven-<id>.jpg, <id>.jpg, full-<id>.png и т.д.
        """
        self.downloaded_files = {}
        self.downloaded_ids.clear()

        download_path = self.settings.get('download_path', '')
        if not download_path or not os.path.isdir(download_path):
            print(f"❌ Папка для загрузок не задана или не существует: {download_path}")
            return

        print(f"🔍 Сканируем папку: {download_path}")

        # Поддержка разных расширений
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            pattern = os.path.join(download_path, ext)
            for file_path in glob.glob(pattern):
                filename = os.path.basename(file_path)
                wallpaper_id = extract_wallpaper_id(filename)
                if wallpaper_id:
                    self.downloaded_files[wallpaper_id] = file_path

        self.downloaded_ids = set(self.downloaded_files.keys())
        print(f"✅ Найдено скачанных обоев: {len(self.downloaded_ids)}")

    def on_downloaded_toggle(self, btn):
        """
        Обработчик кнопки "Только скачанные".

        Переключает режим отображения между API-поиском и локальной библиотекой.
        """
        self.is_downloaded_mode = btn.get_active()
        self.entry.set_sensitive(not self.is_downloaded_mode)

        if self.is_downloaded_mode:
            self.show_infobar("Отображаются только скачанные обои. Фильтры временно отключены.")
            self.current_query = ""
        else:
            self.current_query = self.settings.get('last_query', '')

        self.start_new_search(self.current_query)

    def get_thumbnail_size(self):
        """
        Рассчитывает оптимальный размер миниатюры на основе ширины окна
        и количества колонок.

        Returns:
            tuple: (ширина: int, высота: int) миниатюры.
        """
        cols = int(self.settings.get('columns', 4))
        win_width = self.get_width()
        if win_width <= 1:
            win_width = 1200
        available_width = win_width - 40
        target_width = (available_width // cols) - 15
        if target_width < 50:
            target_width = 50
        target_height = int(target_width * 0.66)
        return target_width, target_height

    def show_infobar(self, message):
        """
        Отображает сообщение в нижней панели (Infobar) и скрывает его через 5 секунд.

        Args:
            message (str): Сообщение для отображения.
        """
        self.infobar_label.set_text(message)
        self.infobar.set_visible(True)
        GLib.timeout_add_seconds(5, lambda: self.infobar.set_visible(False))
        return False

    def on_infobar_close_clicked(self, button):
        """Скрывает Infobar при нажатии кнопки закрытия."""
        self.infobar.set_visible(False)
        return False

    def get_current_search_state(self):
        """
        Возвращает текущее состояние фильтров и поисковой строки.

        Returns:
            dict: Словарь с текущими параметрами поиска.
        """
        return {
            'last_query': self.entry.get_text().strip(),
            'cat_general': str(self.btn_general.get_active()).lower(),
            'cat_anime': str(self.btn_anime.get_active()).lower(),
            'cat_people': str(self.btn_people.get_active()).lower(),
            'purity_sfw': str(self.btn_sfw.get_active()).lower(),
            'purity_sketchy': str(self.btn_sketchy.get_active()).lower(),
            'purity_nsfw': str(self.btn_nsfw.get_active()).lower(),
            'sort_index': str(self.sort_dropdown.get_selected()),
            'resolution_index': str(self.res_dropdown.get_selected()),
            'ratio_index': str(self.ratio_dropdown.get_selected())
        }

    def on_filter_changed(self, widget, *args):
        """
        Обработчик изменения фильтров и выпадающих списков. Сохраняет состояние и начинает новый поиск.
        """
        search_state = self.get_current_search_state()
        final_settings = {**self.settings, **search_state}
        save_settings(final_settings)
        self.settings = final_settings
        self.start_new_search(self.entry.get_text().strip())

    def apply_settings(self, new_settings):
        """
        Применяет новые настройки (из окна настроек) к главному окну.

        Args:
            new_settings (dict): Словарь с новыми настройками.
        """
        old_cols = int(self.settings.get('columns', 4))
        old_key = self.settings.get('api_key', '')
        self.settings = new_settings

        new_cols = int(self.settings.get('columns', 4))
        self.flowbox.set_min_children_per_line(new_cols)
        self.flowbox.set_max_children_per_line(new_cols)

        self.res_dropdown.set_selected(int(self.settings.get('resolution_index', 0)))
        self.ratio_dropdown.set_selected(int(self.settings.get('ratio_index', 0)))
        self.sort_dropdown.set_selected(int(self.settings.get('sort_index', 5)))

        if old_cols != new_cols or old_key != new_settings['api_key']:
            self.start_new_search(self.current_query)

    def open_settings(self, action, param):
        """Открывает окно настроек (SettingsWindow)."""
        SettingsWindow(self).present()

    def show_about_dialog(self, action, param):
        """Максимально совместимое окно 'О приложении'."""
        # Регистрируем путь к иконке, чтобы GTK нашел её по короткому имени
        icon_path = os.path.join(os.path.dirname(__file__), "app-icon.png")
        if os.path.exists(icon_path):
            theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            theme.add_search_path(os.path.dirname(__file__))

        about = Adw.AboutWindow(
            transient_for=self,
            application_name="Wallhaven Viewer",
            application_icon="cc.wallhaven.Viewer",
            developer_name="OOOTMYV_DENEG",
            version="1.0",
            comments="Просмотр и скачивание обоев с Wallhaven.cc",
            website="https://wallhaven.cc",
            copyright="© 2025 Vadim",
            license_type=Gtk.License.MIT_X11,
        )
        about.present()

    def check_api_key_on_purity_change(self, toggle_button):
        """
        Проверяет наличие API-ключа при попытке включить Sketchy/NSFW.
        Открывает настройки, если ключ отсутствует.
        """
        api_key = self.settings.get('api_key', '')
        if toggle_button.get_active() and not api_key:
            self.open_settings(None, None)
            toggle_button.set_active(False)
        self.on_filter_changed(toggle_button)

    def on_scroll_changed(self, adj):
        """
        Обработчик прокрутки. Подгружает следующую страницу, когда пользователь
        приближается к концу списка (на расстоянии одной строки).
        """
        GLib.idle_add(self.check_if_can_load_next_page)
        if self.is_loading or not self.has_more_pages or self.is_downloaded_mode:
            return

        # Оцениваем высоту строки на основе размера миниатюры
        _, thumbnail_height = self.get_thumbnail_size()
        row_height = thumbnail_height + 10  # +10 отступы (5 сверху + 5 снизу)

        current_pos = adj.get_value() + adj.get_page_size()
        max_height = adj.get_upper()

        if max_height - current_pos < row_height * 1.5:
            self.load_next_page()

    def check_if_can_load_next_page(self):
        """
        Проверяет, нужно ли подгрузить следующую страницу.
        Работает как при активной прокрутке, так и при её отсутствии.
        """
        if self.is_loading or not self.has_more_pages or self.is_downloaded_mode:
            return False

        adj = self.v_adj
        current_pos = adj.get_value() + adj.get_page_size()
        max_height = adj.get_upper()

        # Если скролл активен — используем обычную логику
        if max_height > adj.get_page_size():
            row_height = self.get_thumbnail_size()[1] + 10
            if max_height - current_pos < row_height:
                self.load_next_page()
                return True
        else:
            # Скролла нет (весь контент виден), но может быть больше страниц
            # → Попробуем подгрузить, если пользователь "внизу"
            child = self.flowbox.get_first_child()
            if child is not None:
                self.load_next_page()
                return True

        return False

    def load_next_page(self):
        """Увеличивает номер страницы и запускает загрузку следующего блока обоев."""
        self.current_page += 1
        self.load_wallpapers(self.current_query, self.current_page)

    def load_thumbnail_async(self, placeholder_btn, thumb_url, full_url, wallpaper_id, local_path=None):
        """Асинхронно загружает миниатюру для кнопки."""
        target_size = self.get_thumbnail_size()
        cache_path = get_cache_path(thumb_url) if thumb_url else None

        def on_thumbnail_loaded(pixbuf):
            if pixbuf:
                self.update_thumbnail_ui(placeholder_btn, pixbuf, wallpaper_id)
            else:
                self.show_error_indicator(placeholder_btn, wallpaper_id)

        ImageLoader.load_thumbnail(
            local_path=local_path,
            cache_path=cache_path,
            thumb_url=thumb_url,
            target_size=target_size,
            callback=on_thumbnail_loaded
        )

    def update_thumbnail_ui(self, btn, pixbuf, wallpaper_id):
        """Обновляет UI кнопки миниатюры."""
        try:
            btn.set_child(None)
            btn.remove_css_class("skeleton")

            if wallpaper_id in self.downloaded_ids:
                btn.add_css_class("downloaded")
                btn.wallhaven_local_path = self.downloaded_files.get(wallpaper_id)
            else:
                btn.remove_css_class("downloaded")
                btn.wallhaven_local_path = None

            btn.set_hexpand(True)
            btn.set_vexpand(False)

            target_width, target_height = self.get_thumbnail_size()

            overlay = Gtk.Overlay()
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            picture = Gtk.Picture.new_for_paintable(texture)
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_size_request(-1, target_height)
            overlay.set_child(picture)

            if wallpaper_id in self.downloaded_ids:
                icon = Gtk.Image.new_from_icon_name("media-floppy-symbolic")
                icon.add_css_class("download-indicator")
                icon.set_halign(Gtk.Align.END)
                icon.set_valign(Gtk.Align.END)
                icon.set_margin_end(10)
                icon.set_margin_bottom(10)
                overlay.add_overlay(icon)

            btn.set_child(overlay)
        except Exception as e:
            print(f"Ошибка обновления UI: {e}")

    def show_error_indicator(self, btn, wallpaper_id):
        """
        Показывает заглушку (индикатор отсутствия миниатюры), если загрузка не удалась.
        """
        try:
            btn.set_child(None)
            btn.remove_css_class("skeleton")
            target_width, target_height = self.get_thumbnail_size()

            error_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            error_box.set_size_request(-1, target_height)
            error_box.set_halign(Gtk.Align.CENTER)
            error_box.set_valign(Gtk.Align.CENTER)

            icon = Gtk.Image.new_from_icon_name("media-floppy-symbolic")
            icon.add_css_class("download-indicator")
            icon.set_icon_size(Gtk.IconSize.LARGE)

            label = Gtk.Label(label=f"ID: {wallpaper_id}\n(Нет миниатюры)", use_markup=False)
            label.add_css_class("dim-label")

            error_box.append(icon)
            error_box.append(label)

            if wallpaper_id in self.downloaded_ids:
                btn.add_css_class("downloaded")

            btn.set_child(error_box)
        except Exception as e:
            print(f"Критическая ошибка при создании индикатора ошибки: {e}")

    def open_full_image(self, widget, url, local_path=None):
        """Открывает окно полноразмерного изображения."""
        if hasattr(widget, 'wallhaven_local_path') and widget.wallhaven_local_path:
            local_path = widget.wallhaven_local_path

        # Проверяем, существует ли уже окно FullImageWindow
        if hasattr(self, '_full_image_window') and self._full_image_window:
            try:
                self._full_image_window.present()
                return
            except Exception:
                # Старое окно возможно было уничтожено/искажено — обнуляем ссылку и создаём новое
                try:
                    self._full_image_window = None
                except Exception:
                    pass

        # Создаём новое окно и сохраняем ссылку на него
        self._full_image_window = FullImageWindow(self, url, self.settings.get('download_path', ''), local_path)
        # Сбрасываем ссылку при уничтожении
        self._full_image_window.connect("destroy", lambda _: setattr(self, '_full_image_window', None))

        # Обрабатываем закрытие окна (close-request) — гарантируем корректное очищение ссылки
        def _on_full_close(window, *args):
            try:
                setattr(self, '_full_image_window', None)
            except Exception:
                pass
            return False

        try:
            self._full_image_window.connect('close-request', _on_full_close)
        except Exception:
            # Если сигнал недоступен, продолжаем — destroy обработчик уже установлен
            pass

        self._full_image_window.present()

    def on_search_clicked(self, widget):
        """Обработчик нажатия кнопки поиска или Enter в поле ввода."""
        query = self.entry.get_text().strip()
        search_state = self.get_current_search_state()
        final_settings = {**self.settings, **search_state}
        save_settings(final_settings)
        self.settings = final_settings
        self.start_new_search(query)

    def create_placeholder_btn(self, full_url, wallpaper_id, local_path=None):
        """Создает кнопку-заглушку для миниатюры."""
        width, height = self.get_thumbnail_size()
        btn = Gtk.Button()
        btn.set_size_request(-1, height)
        btn.set_hexpand(True)
        btn.set_margin_start(5)
        btn.set_margin_end(5)
        btn.set_margin_top(5)
        btn.set_margin_bottom(5)
        if local_path and os.path.exists(local_path):
            btn.add_css_class("downloaded")
        btn.add_css_class("skeleton")
        btn.add_css_class("thumbnail")

        btn.wallhaven_local_path = local_path

        s = Adw.Spinner()
        s.set_halign(Gtk.Align.CENTER)
        s.set_valign(Gtk.Align.CENTER)
        btn.set_child(s)
        btn.connect("clicked", self.open_full_image, full_url, local_path)
        return btn

    def start_new_search(self, query):
        """
        Очищает сетку, сбрасывает счетчик страниц и начинает новый поиск.
        """
        self.current_page = 1
        self.current_query = query
        self.has_more_pages = not self.is_downloaded_mode
        self.infobar.set_visible(False)
        while True:
            child = self.flowbox.get_first_child()
            if child is None:
                break
            self.flowbox.remove(child)
        self.load_wallpapers(query, 1)

    def load_wallpapers(self, query, page):
        """
        Основная функция для загрузки обоев (API-поиск или локальная библиотека).
        """
        self.is_loading = True

        if self.is_downloaded_mode:
            self.bottom_spinner.set_visible(False)
            items_to_add = []
            for w_id, local_path in self.downloaded_files.items():
                full_url = WallhavenAPI.build_wallpaper_url(w_id)
                items_to_add.append((None, full_url, w_id, local_path))
            GLib.idle_add(self.create_placeholders_and_load, items_to_add)
            GLib.idle_add(self.finish_loading_page, False)
            self.is_loading = False
            return

        if page > 1:
            self.bottom_spinner.set_visible(True)

        def worker():
            # Используем новый API класс
            search_state = self.get_current_search_state()
            search_settings = {**self.settings, **search_state}
            data, meta = WallhavenAPI.search_wallpapers(query, page, search_settings)

            if data is None:
                GLib.idle_add(self.show_infobar, "Ошибка API")
                GLib.idle_add(self.finish_loading_page, False)
                return

            if not data and page == 1:
                GLib.idle_add(self.show_infobar, "Ничего не найдено")

            items_to_add = []
            for w in data:
                thumbs = w.get("thumbs", {})
                thumb = thumbs.get("large") or thumbs.get("original")
                full = w.get("path")
                w_id = w.get("id")
                if thumb and full and w_id:
                    items_to_add.append((thumb, full, w_id, None))

            GLib.idle_add(self.create_placeholders_and_load, items_to_add)
            last_page = meta.get("last_page", 1) if meta else 1
            more_pages = page < last_page
            GLib.idle_add(self.finish_loading_page, more_pages)

        threading.Thread(target=worker, daemon=True).start()

    def create_placeholders_and_load(self, items):
        """
        Создает заглушки в UI и запускает асинхронную загрузку миниатюр.
        """
        for thumb_url, full_url, wallpaper_id, local_path in items:
            btn = self.create_placeholder_btn(full_url, wallpaper_id, local_path)
            self.flowbox.append(btn)
            self.load_thumbnail_async(btn, thumb_url, full_url, wallpaper_id, local_path)

    def finish_loading_page(self, has_more):
        """
        Завершает процесс загрузки страницы, обновляет статус и скрользер.
        """
        self.is_loading = False
        self.has_more_pages = has_more
        self.bottom_spinner.set_visible(False)

        # Попробуем подгрузить следующую страницу сразу,
        # если контент не прокручивается
        GLib.idle_add(self.check_if_can_load_next_page)

    def on_close_request(self, widget):
        """Вызывается при попытке закрыть окно."""
        self.get_application().quit()
        return False  # Возвращаем False, чтобы продолжить закрытие
