#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GdkPixbuf, GLib, Gdk, Gio, GObject
import requests
import threading
import os
import configparser

API_URL = "https://wallhaven.cc/api/v1/search"
CONFIG_FILE = "wallhaven_viewer.ini"

# --- НОВЫЕ КОНСТАНТЫ ---
RESOLUTION_OPTIONS = [
    ("Любое", ""),
    ("1024x768 (XGA)", "1024x768"),
    ("1280x720 (HD)", "1280x720"),
    ("1920x1080 (FHD)", "1920x1080"),
    ("2560x1440 (QHD)", "2560x1440"),
    ("3840x2160 (4K)", "3840x2160"),
    ("5120x2880 (5K)", "5120x2880"),
    ("7680x4320 (8K)", "7680x4320"),
]
RATIO_OPTIONS = [
    ("Любое", ""),
    ("16:9", "16x9"),
    ("16:10", "16x10"),
    ("4:3", "4x3"),
    ("5:4", "5x4"),
    ("21:9", "21x9"),
    ("32:9", "32x9"),
]

# --- НАСТРОЙКИ ---
DEFAULT_SETTINGS = {
    'api_key': '',
    'download_path': '',
    'columns': '4',
    'last_query': '',
    'cat_general': 'true',
    'cat_anime': 'true',
    'cat_people': 'true',
    'purity_sfw': 'true',
    'purity_sketchy': 'false',
    'purity_nsfw': 'false',
    'sort_index': '5', 
    'resolution_index': '0', 
    'ratio_index': '0'       
}

# --- Функции для настроек ---

def load_settings():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    settings = DEFAULT_SETTINGS.copy()
    if 'Settings' in config:
        for key in settings:
            if key in config['Settings']:
                settings[key] = config['Settings'][key]
    return settings

def save_settings(settings_dict):
    config = configparser.ConfigParser()
    config['Settings'] = {k: v for k, v in settings_dict.items() if k in DEFAULT_SETTINGS}
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

# --- Окно настроек ---

class SettingsWindow(Gtk.Window):
    def __init__(self, parent):
        super().__init__(title="Настройки")
        self.set_modal(True)
        self.set_transient_for(parent)
        self.set_default_size(400, 300)
        
        self.parent_window = parent
        self.current_settings = load_settings()
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        vbox.set_margin_start(20)
        vbox.set_margin_end(20)
        vbox.set_margin_top(20)
        vbox.set_margin_bottom(20)
        self.set_child(vbox)
        
        # 1. API Key
        vbox.append(Gtk.Label(label="<b>API Ключ (для NSFW):</b>", use_markup=True, xalign=0))
        self.entry_api = Gtk.Entry()
        self.entry_api.set_text(self.current_settings['api_key'])
        vbox.append(self.entry_api)

        vbox.append(Gtk.Separator())

        # 2. Папка
        vbox.append(Gtk.Label(label="<b>Папка для сохранения:</b>", use_markup=True, xalign=0))
        hbox_path = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox.append(hbox_path)
        
        self.entry_path = Gtk.Entry()
        self.entry_path.set_placeholder_text("Не выбрана (спрашивать каждый раз)")
        self.entry_path.set_text(self.current_settings['download_path'])
        self.entry_path.set_hexpand(True)
        self.entry_path.set_can_focus(False)
        hbox_path.append(self.entry_path)
        
        btn_path = Gtk.Button(icon_name="folder-open-symbolic")
        btn_path.connect("clicked", self.on_select_folder)
        hbox_path.append(btn_path)
        
        btn_clear_path = Gtk.Button(icon_name="user-trash-symbolic")
        btn_clear_path.connect("clicked", lambda x: self.entry_path.set_text(""))
        hbox_path.append(btn_clear_path)

        vbox.append(Gtk.Separator())

        # 3. Колонки
        hbox_cols = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.append(hbox_cols)
        hbox_cols.append(Gtk.Label(label="Колонок в сетке:", xalign=0))
        
        adj = Gtk.Adjustment(value=int(self.current_settings['columns']), lower=2, upper=10, step_increment=1)
        self.spin_cols = Gtk.SpinButton(adjustment=adj)
        hbox_cols.append(self.spin_cols)

        vbox.append(Gtk.Separator())

        btn_save = Gtk.Button(label="Сохранить настройки")
        btn_save.add_css_class("suggested-action")
        btn_save.connect("clicked", self.on_save_clicked)
        vbox.append(btn_save)

    def on_select_folder(self, btn):
        dialog = Gtk.FileDialog()
        dialog.select_folder(self, None, self.on_folder_selected)

    def on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.entry_path.set_text(folder.get_path())
        except Exception: pass

    def on_save_clicked(self, btn):
        new_app_settings = {
            'api_key': self.entry_api.get_text().strip(),
            'download_path': self.entry_path.get_text().strip(),
            'columns': str(int(self.spin_cols.get_value()))
        }
        
        current_search_state = self.parent_window.get_current_search_state()
        final_settings = {**self.parent_window.settings, **new_app_settings, **current_search_state}

        save_settings(final_settings)
        self.parent_window.apply_settings(final_settings)
        self.close()

# --- Приложение ---

class WallpaperViewer(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.wallhaven.viewer")

    def do_activate(self):
        win = MainWindow(self)
        win.present()


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Wallhaven Viewer")
        self.set_default_size(1200, 850)

        self.current_page = 1
        self.settings = load_settings()
        self.current_query = self.settings['last_query']
        self.is_loading = False 
        self.has_more_pages = True

        # 1. Overlay
        overlay = Gtk.Overlay()
        self.set_child(overlay) 

        # 2. Основной вертикальный бокс
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_vbox.set_margin_start(10)
        main_vbox.set_margin_end(10)
        main_vbox.set_margin_top(10)
        main_vbox.set_margin_bottom(10)
        overlay.set_child(main_vbox) 
        
        # --- Gtk.InfoBar для сообщений об ошибках ---
        self.infobar = Gtk.InfoBar()
        self.infobar.set_visible(False) 
        self.infobar.add_css_class("error") 

        self.infobar_label = Gtk.Label(label="Ошибка API")
        
        # Используем add_child для старых версий GTK4
        self.infobar.add_child(self.infobar_label) 

        self.infobar.add_button("Закрыть", Gtk.ResponseType.CLOSE)
        self.infobar.connect("response", lambda w, r: self.infobar.set_visible(False))
        
        overlay.add_overlay(self.infobar)
        self.infobar.set_halign(Gtk.Align.CENTER)
        self.infobar.set_valign(Gtk.Align.START)


        # Поиск
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        main_vbox.append(search_box)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Поиск (оставьте пустым для топа)...")
        self.entry.set_text(self.current_query) 
        self.entry.set_hexpand(True)
        self.entry.connect("activate", self.on_search_clicked)
        search_box.append(self.entry)

        btn_search = Gtk.Button(label="Поиск / Обновить")
        btn_search.connect("clicked", self.on_search_clicked)
        search_box.append(btn_search)

        # --- Фильтры ---
        filters_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        main_vbox.append(filters_box)

        # Категории
        cat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        cat_box.add_css_class("linked")
        filters_box.append(cat_box)
        
        self.btn_general = Gtk.ToggleButton(label="General")
        self.btn_general.set_active(self.settings['cat_general'].lower() == 'true')
        cat_box.append(self.btn_general)
        
        self.btn_anime = Gtk.ToggleButton(label="Anime")
        self.btn_anime.set_active(self.settings['cat_anime'].lower() == 'true')
        cat_box.append(self.btn_anime)
        
        self.btn_people = Gtk.ToggleButton(label="People")
        self.btn_people.set_active(self.settings['cat_people'].lower() == 'true')
        cat_box.append(self.btn_people)

        filters_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Purity
        purity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        purity_box.add_css_class("linked")
        filters_box.append(purity_box)
        
        self.btn_sfw = Gtk.ToggleButton(label="SFW")
        self.btn_sfw.set_active(self.settings['purity_sfw'].lower() == 'true')
        purity_box.append(self.btn_sfw)
        
        self.btn_sketchy = Gtk.ToggleButton(label="Sketchy")
        self.btn_sketchy.set_active(self.settings['purity_sketchy'].lower() == 'true')
        purity_box.append(self.btn_sketchy)
        self.btn_sketchy.connect("clicked", self.check_api_key_on_purity_change)
        
        self.btn_nsfw = Gtk.ToggleButton(label="NSFW")
        self.btn_nsfw.set_active(self.settings['purity_nsfw'].lower() == 'true')
        purity_box.append(self.btn_nsfw)
        self.btn_nsfw.connect("clicked", self.check_api_key_on_purity_change)

        filters_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        
        # Разрешение
        filters_box.append(Gtk.Label(label="Разрешение:"))
        res_options = Gtk.StringList()
        for label, _ in RESOLUTION_OPTIONS:
            res_options.append(label)
        self.res_dropdown = Gtk.DropDown(model=res_options)
        self.res_dropdown.set_selected(int(self.settings['resolution_index']))
        self.res_dropdown.connect("notify::selected", self.on_filter_changed)
        filters_box.append(self.res_dropdown)

        # Соотношение сторон
        filters_box.append(Gtk.Label(label="Соотношение:"))
        ratio_options = Gtk.StringList()
        for label, _ in RATIO_OPTIONS:
            ratio_options.append(label)
        self.ratio_dropdown = Gtk.DropDown(model=ratio_options)
        self.ratio_dropdown.set_selected(int(self.settings['ratio_index']))
        self.ratio_dropdown.connect("notify::selected", self.on_filter_changed)
        filters_box.append(self.ratio_dropdown)
        
        filters_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Сортировка
        filters_box.append(Gtk.Label(label="Сортировка:"))
        sort_options = Gtk.StringList()
        for opt in ["Relevance", "Random", "Date Added", "Views", "Favorites", "Toplist", "Hot"]:
            sort_options.append(opt)
        
        self.sort_dropdown = Gtk.DropDown(model=sort_options)
        self.sort_dropdown.set_selected(int(self.settings['sort_index'])) 
        self.sort_dropdown.connect("notify::selected", self.on_filter_changed)
        filters_box.append(self.sort_dropdown)
        
        btn_settings = Gtk.Button(icon_name="preferences-system-symbolic")
        btn_settings.set_tooltip_text("Настройки")
        btn_settings.connect("clicked", self.open_settings)
        filters_box.append(btn_settings)

        # Контент
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        main_vbox.append(self.scrolled)

        self.v_adj = self.scrolled.get_vadjustment()
        # ПОДКЛЮЧЕНИЕ МЕТОДА БЕСКОНЕЧНОГО СКРОЛЛА
        self.v_adj.connect("value-changed", self.on_scroll_changed)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.scrolled.set_child(content_box)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        
        cols = int(self.settings.get('columns', 4))
        self.flowbox.set_min_children_per_line(cols)
        self.flowbox.set_max_children_per_line(cols)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        content_box.append(self.flowbox)

        self.bottom_spinner = Gtk.Spinner()
        self.bottom_spinner.set_size_request(32, 32)
        self.bottom_spinner.set_halign(Gtk.Align.CENTER)
        content_box.append(self.bottom_spinner)
        
        # Запускаем поиск 
        self.start_new_search(self.current_query)

    # --- МЕТОДЫ КЭШИРОВАНИЯ ---
    def get_cache_dir(self):
        """Возвращает путь к папке кэша и создает ее, если она не существует."""
        cache_dir = os.path.join(GLib.get_user_cache_dir(), "wallhaven_viewer_cache")
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir)
            except OSError as e:
                print(f"Ошибка создания папки кэша: {e}")
                return None
        return cache_dir
    # --- КОНЕЦ МЕТОДОВ КЭШИРОВАНИЯ ---

    # --- МЕТОД ДЛЯ ПОКАЗА ОШИБКИ ---
    def show_infobar(self, message):
        """Показывает сообщение об ошибке в Gtk.InfoBar и скрывает его через 5 секунд."""
        self.infobar_label.set_text(message)
        self.infobar.set_visible(True) 
        GLib.timeout_add_seconds(5, lambda: self.infobar.set_visible(False))
        return False

    # --- Логика ---

    def get_current_search_state(self):
        """Собирает текущее состояние всех фильтров для сохранения."""
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
        search_state = self.get_current_search_state()
        final_settings = {**self.settings, **search_state}
        save_settings(final_settings)
        self.settings = final_settings
        self.start_new_search(self.entry.get_text().strip())


    def apply_settings(self, new_settings):
        old_cols = int(self.settings.get('columns', 4))
        old_key = self.settings.get('api_key', '')
        self.settings = new_settings
        
        new_cols = int(self.settings.get('columns', 4))
        self.flowbox.set_min_children_per_line(new_cols)
        self.flowbox.set_max_children_per_line(new_cols)
        
        # Обновляем состояние DropDown, если оно изменилось в результате сохранения настроек
        self.res_dropdown.set_selected(int(self.settings.get('resolution_index', 0)))
        self.ratio_dropdown.set_selected(int(self.settings.get('ratio_index', 0)))
        self.sort_dropdown.set_selected(int(self.settings.get('sort_index', 5)))

        if old_cols != new_cols or old_key != new_settings['api_key']:
            self.start_new_search(self.current_query)

    def open_settings(self, widget):
        SettingsWindow(self).present()
        
    def check_api_key_on_purity_change(self, toggle_button):
        api_key = self.settings.get('api_key', '')
        if toggle_button.get_active() and not api_key:
            self.open_settings(None)
            toggle_button.set_active(False) 
        
        self.on_filter_changed(toggle_button)

    # --- БЕСКОНЕЧНЫЙ СКРОЛЛ ---
    def on_scroll_changed(self, adj):
        if self.is_loading or not self.has_more_pages:
            return

        current_pos = adj.get_value() + adj.get_page_size()
        max_height = adj.get_upper()

        if max_height - current_pos < 300:
            self.load_next_page()

    def load_next_page(self):
        self.current_page += 1
        self.load_wallpapers(self.current_query, self.current_page)

    # --- ЗАПРОСЫ ---

    def get_api_params(self, query, page):
        c_gen = "1" if self.btn_general.get_active() else "0"
        c_ani = "1" if self.btn_anime.get_active() else "0"
        c_peo = "1" if self.btn_people.get_active() else "0"
        
        p_sfw = "1" if self.btn_sfw.get_active() else "0"
        api_key = self.settings.get('api_key', '')
        
        if api_key:
            p_sky = "1" if self.btn_sketchy.get_active() else "0"
            p_nsf = "1" if self.btn_nsfw.get_active() else "0"
        else:
            p_sky = "0"
            p_nsf = "0"
            if self.btn_sketchy.get_active(): self.btn_sketchy.set_active(False)
            if self.btn_nsfw.get_active(): self.btn_nsfw.set_active(False)

        sort_idx = self.sort_dropdown.get_selected()
        sort_modes = ["relevance", "random", "date_added", "views", "favorites", "toplist", "hot"]
        sorting = sort_modes[sort_idx] if sort_idx < len(sort_modes) else "relevance"
        
        res_idx = self.res_dropdown.get_selected()
        ratio_idx = self.ratio_dropdown.get_selected()
        
        selected_res = RESOLUTION_OPTIONS[res_idx][1]
        selected_ratio = RATIO_OPTIONS[ratio_idx][1]

        params = {
            "q": query, "categories": f"{c_gen}{c_ani}{c_peo}", 
            "purity": f"{p_sfw}{p_sky}{p_nsf}", "sorting": sorting, "page": page
        }
        
        if selected_res:
            params["resolutions"] = selected_res
        if selected_ratio:
            params["ratios"] = selected_ratio
            
        if api_key: params["apikey"] = api_key
        return params

    @staticmethod
    def load_pixbuf_from_bytes(img_bytes):
        loader = GdkPixbuf.PixbufLoader()
        loader.write(img_bytes)
        loader.close()
        return loader.get_pixbuf()

    # --- АСИНХРОННАЯ ЗАГРУЗКА МИНИАТЮРЫ (С КЭШИРОВАНИЕМ) ---
    def load_thumbnail_async(self, thumb_url, full_url):
        cache_dir = self.get_cache_dir()
        if not cache_dir:
            # Если кэш недоступен, продолжаем обычную загрузку без кэширования
            cache_path = None
            filename = None
        else:
            filename = thumb_url.split('/')[-1]
            cache_path = os.path.join(cache_dir, filename)

        def worker():
            img_data = None
            
            # 1. Попытка загрузить из кэша
            if cache_path and os.path.exists(cache_path):
                try:
                    with open(cache_path, "rb") as f:
                        img_data = f.read()
                except Exception:
                    img_data = None 

            # 2. Загрузка из сети, если нет в кэше
            if img_data is None:
                try:
                    img_data = requests.get(thumb_url, timeout=10).content
                    
                    # 3. Сохранение в кэш
                    if cache_path:
                        try:
                            with open(cache_path, "wb") as f:
                                f.write(img_data)
                        except Exception as e:
                            print(f"Ошибка сохранения в кэш: {e}") 
                            
                except requests.exceptions.Timeout:
                    return 
                except Exception:
                    return 

            # Отображение
            if img_data:
                try:
                    pixbuf = self.load_pixbuf_from_bytes(img_data)
                    GLib.idle_add(self.add_thumbnail_to_ui, pixbuf, full_url)
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()
    # --- КОНЕЦ load_thumbnail_async ---


    def add_thumbnail_to_ui(self, pixbuf, full_url):
        try:
            cols = int(self.settings.get('columns', 4))
            
            win_width = self.get_width()
            available_width = win_width - 20 
            target_width = (available_width // cols) - 15 
            target_height = int(target_width * 0.66) 
            
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            
            picture = Gtk.Picture.new_for_paintable(texture)
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_size_request(target_width, target_height)

            button = Gtk.Button()
            button.set_child(picture)
            button.set_margin_start(5)
            button.set_margin_end(5)
            button.set_margin_top(5)
            button.set_margin_bottom(5)
            
            button.connect("clicked", self.open_full_image, full_url)
            self.flowbox.append(button)
        except Exception:
            pass

    def open_full_image(self, widget, url):
        win = FullImageWindow(self, url, self.settings.get('download_path', ''))
        win.present()

    def on_search_clicked(self, widget):
        query = self.entry.get_text().strip()
        
        search_state = self.get_current_search_state()
        final_settings = {**self.settings, **search_state}
        save_settings(final_settings)
        self.settings = final_settings
        
        self.start_new_search(query)

    def start_new_search(self, query):
        self.current_page = 1
        self.current_query = query
        self.has_more_pages = True
        self.infobar.set_visible(False) 
        
        while True:
            child = self.flowbox.get_first_child()
            if child is None: break
            self.flowbox.remove(child)
        
        self.center_spinner = Gtk.Spinner()
        self.center_spinner.set_size_request(32, 32)
        self.center_spinner.set_halign(Gtk.Align.CENTER)
        self.center_spinner.set_valign(Gtk.Align.CENTER)
        box = Gtk.Box()
        box.set_halign(Gtk.Align.CENTER)
        box.append(self.center_spinner)
        self.flowbox.append(box)
        self.center_spinner.start()
        
        self.load_wallpapers(query, 1)

    def load_wallpapers(self, query, page):
        self.is_loading = True
        if page > 1:
            self.bottom_spinner.set_visible(True)
            self.bottom_spinner.start()

        def worker():
            params = self.get_api_params(query, page)
            try:
                resp = requests.get(API_URL, params=params, timeout=10)
                resp.raise_for_status() 
                data = resp.json().get("data", [])
                meta = resp.json().get("meta", {})
                
                GLib.idle_add(self.stop_center_spinner)

                for w in data:
                    thumbs = w.get("thumbs", {})
                    thumb = thumbs.get("large") or thumbs.get("original")
                    full = w.get("path")
                    if thumb and full:
                        self.load_thumbnail_async(thumb, full)

                last_page = meta.get("last_page", 1)
                more_pages = page < last_page
                
                GLib.idle_add(self.on_api_response_ui, data, more_pages)
                
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                error_msg = f"Ошибка HTTP {status_code}: {'Слишком много запросов (429)' if status_code == 429 else 'API не найдено (404)' if status_code == 404 else 'Проверьте API ключ/запрос'}."
                GLib.idle_add(self.show_infobar, error_msg)
                GLib.idle_add(self.stop_center_spinner)
                GLib.idle_add(self.on_api_response_ui, [], False)
            except requests.exceptions.ConnectionError:
                GLib.idle_add(self.show_infobar, "Ошибка соединения: Проверьте интернет или API URL.")
                GLib.idle_add(self.stop_center_spinner)
                GLib.idle_add(self.on_api_response_ui, [], False)
            except requests.exceptions.Timeout:
                GLib.idle_add(self.show_infobar, "Таймаут запроса: API не отвечает.")
                GLib.idle_add(self.stop_center_spinner)
                GLib.idle_add(self.on_api_response_ui, [], False)
            except Exception as e:
                GLib.idle_add(self.show_infobar, f"Неизвестная ошибка: {e}")
                GLib.idle_add(self.stop_center_spinner)
                GLib.idle_add(self.on_api_response_ui, [], False)

        threading.Thread(target=worker, daemon=True).start()

    def stop_center_spinner(self):
        if hasattr(self, 'center_spinner') and self.center_spinner.get_parent():
            self.flowbox.remove(self.center_spinner.get_parent())

    def on_api_response_ui(self, data, has_more):
        self.is_loading = False
        self.has_more_pages = has_more
        self.bottom_spinner.stop()
        self.bottom_spinner.set_visible(False)
        
        if not data and self.current_page == 1:
            return

        page_size = self.v_adj.get_page_size()
        upper = self.v_adj.get_upper()
        
        if has_more and upper < (page_size * 1.5):
            self.load_next_page()


# --- Окно полноразмерного изображения (С ИСПРАВЛЕННЫМ ЗАГОЛОВКОМ) ---

class FullImageWindow(Gtk.Window):
    def __init__(self, parent, image_url, download_path):
        super().__init__(transient_for=parent)
        self.set_default_size(1000, 700)
        self.image_url = image_url
        self.download_path = download_path
        self.image_data = None
        
        self.wallpaper_id = image_url.split('/')[-1].split('.')[0]
        self.set_title(f"Wallhaven - ID: {self.wallpaper_id}")

        header = Gtk.HeaderBar()
        self.set_titlebar(header)
        
        self.save_btn = Gtk.Button(icon_name="document-save-symbolic")
        self.save_btn.set_sensitive(False)
        self.save_btn.set_tooltip_text("Сохранить изображение")
        self.save_btn.connect("clicked", self.on_save_clicked)
        header.pack_end(self.save_btn)

        overlay = Gtk.Overlay()
        self.set_child(overlay)

        self.picture = Gtk.Picture()
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.picture.set_can_shrink(True) 
        overlay.set_child(self.picture)

        spinner_box = Gtk.Box()
        spinner_box.set_halign(Gtk.Align.CENTER)
        spinner_box.set_valign(Gtk.Align.CENTER)
        
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(32, 32)
        self.spinner.set_hexpand(False)
        self.spinner.set_vexpand(False)
        self.spinner.start()
        
        spinner_box.append(self.spinner)
        overlay.add_overlay(spinner_box)

        # Выполняем загрузку изображения и информации параллельно
        threading.Thread(target=self.load_image_and_info, daemon=True).start()

    def load_image_and_info(self):
        """Загружает изображение и дополнительную информацию (для заголовка)"""
        
        # 1. Загрузка информации об изображении для разрешения
        resolution = "N/A"
        try:
            info_url = f"https://wallhaven.cc/api/v1/w/{self.wallpaper_id}"
            info_resp = requests.get(info_url, timeout=5).json()
            resolution = info_resp.get("data", {}).get("resolution", "N/A")
            GLib.idle_add(self.update_title, resolution)
        except Exception:
            GLib.idle_add(self.update_title, resolution)
            
        # 2. Загрузка самого изображения
        try:
            resp = requests.get(self.image_url, stream=True, timeout=60)
            resp.raise_for_status()
            self.image_data = b''
            for chunk in resp.iter_content(chunk_size=8192):
                self.image_data += chunk
            
            loader = GdkPixbuf.PixbufLoader()
            loader.write(self.image_data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            GLib.idle_add(self.update_image, pixbuf)
        except Exception:
            GLib.idle_add(self.spinner.stop)

    def update_title(self, resolution):
        """Обновляет заголовок окна с ID и разрешением."""
        title = f"Wallhaven - ID: {self.wallpaper_id} ({resolution})"
        self.set_title(title)

    def update_image(self, pixbuf):
        texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        self.picture.set_paintable(texture)
        self.spinner.stop()
        self.spinner.set_visible(False)
        self.save_btn.set_sensitive(True)

    def on_save_clicked(self, btn):
        if not self.image_data: return
        name = self.image_url.split("/")[-1]
        
        if self.download_path and os.path.exists(self.download_path):
            try:
                with open(os.path.join(self.download_path, name), "wb") as f:
                    f.write(self.image_data)
                self.save_btn.set_icon_name("object-select-symbolic")
                GLib.timeout_add(1500, lambda: self.save_btn.set_icon_name("document-save-symbolic"))
            except Exception: self.open_dialog(name)
        else:
            self.open_dialog(name)

    def open_dialog(self, name):
        d = Gtk.FileDialog()
        d.set_initial_name(name)
        d.save(self, None, self.on_save_finish)

    def on_save_finish(self, d, res):
        try:
            f = d.save_finish(res)
            if f:
                with open(f.get_path(), "wb") as file:
                    file.write(self.image_data)
        except Exception: pass

if __name__ == "__main__":
    app = WallpaperViewer()
    app.run()
