#!/usr/bin/env python3
"""
Wallhaven Desktop Viewer
========================

Настольное приложение для просмотра и скачивания обоев с wallhaven.cc.
Использует GTK 4 (PyGObject) для интерфейса и Requests для работы с API.
"""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GdkPixbuf, GLib, Gdk, Gio, GObject
import requests
import threading
import os
import configparser
import sys
import traceback
import glob

API_URL = "https://wallhaven.cc/api/v1/search"
CONFIG_FILE = "wallhaven_viewer.ini"

# --- ХЕЛПЕР ДЛЯ ПУТЕЙ ---
def resolve_path(filename):
    """
    Возвращает абсолютный путь к файлу относительно расположения скрипта.

    Args:
        filename (str): Имя файла (например, 'style.css' или 'config.ini').

    Returns:
        str: Полный, абсолютный путь к файлу.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, filename)

# --- КОНСТАНТЫ ---
RESOLUTION_OPTIONS = [
    ("Любое", ""),
    ("1024x768 (XGA)", "1024x768"),
    ("1280x720 (HD)", "1280x720"),
    ("1920x1080 (FHD)", "1999x1080"), # Wallhaven использует "at least" для 1920x1080
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
SORT_OPTIONS = ["Relevance", "Random", "Date Added", "Views", "Favorites", "Toplist", "Hot"]
# ------------------------------------------------------------------------

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

def load_settings():
    """
    Загружает настройки из INI-файла.

    Если файл не найден, возвращает словарь с настройками по умолчанию.

    Returns:
        dict: Словарь текущих или дефолтных настроек приложения.
    """
    config = configparser.ConfigParser()
    config.read(resolve_path(CONFIG_FILE))
    settings = DEFAULT_SETTINGS.copy()
    if 'Settings' in config:
        for key in settings:
            if key in config['Settings']:
                settings[key] = config['Settings'][key]
    return settings

def save_settings(settings_dict):
    """
    Сохраняет переданный словарь настроек в INI-файл.

    Args:
        settings_dict (dict): Словарь настроек, которые необходимо сохранить.
    """
    config = configparser.ConfigParser()
    config['Settings'] = {k: v for k, v in settings_dict.items() if k in DEFAULT_SETTINGS}
    with open(resolve_path(CONFIG_FILE), 'w') as configfile:
        config.write(configfile)

# --- SettingsWindow ---
class SettingsWindow(Gtk.Window):
    """
    Окно настроек приложения.

    Позволяет пользователю настроить API-ключ, путь для сохранения обоев
    и количество колонок в сетке главного окна.

    Args:
        parent (MainWindow): Ссылка на родительское окно.
    """
    
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
        
        # API Key
        vbox.append(Gtk.Label(label="<b>API Ключ (для NSFW):</b>", use_markup=True, xalign=0))
        self.entry_api = Gtk.Entry()
        self.entry_api.set_text(self.current_settings['api_key'])
        vbox.append(self.entry_api)

        vbox.append(Gtk.Separator())

        # Путь сохранения
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

        # Колонки
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
        """Открывает диалог выбора папки для сохранения."""
        dialog = Gtk.FileDialog()
        dialog.select_folder(self, None, self.on_folder_selected)

    def on_folder_selected(self, dialog, result):
        """
        Обработчик завершения выбора папки. 
        Устанавливает выбранный путь в поле ввода.
        """
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.entry_path.set_text(folder.get_path())
        except Exception: pass

    def on_save_clicked(self, btn):
        """
        Сохраняет настройки в INI-файл, применяет их к главному окну и закрывает диалог.
        """
        new_app_settings = {
            'api_key': self.entry_api.get_text().strip(),
            'download_path': self.entry_path.get_text().strip(),
            'columns': str(int(self.spin_cols.get_value()))
        }
        
        current_search_state = self.parent_window.get_current_search_state()
        final_settings = {**self.parent_window.settings, **new_app_settings, **current_search_state}

        save_settings(final_settings)
        self.parent_window.apply_settings(final_settings)
        self.parent_window.scan_downloaded_wallpapers() 
        self.close()

# --- Приложение ---
class WallpaperViewer(Gtk.Application):
    """
    Основное приложение Wallhaven Viewer, наследующее Gtk.Application.

    Отвечает за инициализацию GTK-окружения, загрузку CSS стилей 
    и запуск главного окна.
    """

    def __init__(self):
        super().__init__(application_id="org.wallhaven.viewer")

    def do_activate(self):
        """
        Вызывается при активации приложения. Загружает стили и показывает главное окно.
        """
        provider = Gtk.CssProvider()
        css_path = resolve_path("style.css")
        try:
            provider.load_from_path(css_path) 
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            print(f"Ошибка загрузки CSS из {css_path}: {e}")
            
        win = MainWindow(self)
        win.present()


class MainWindow(Gtk.ApplicationWindow):
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
            app (WallpaperViewer): Экземпляр Gtk.Application.
        """
        super().__init__(application=app)
        self.set_title("Wallhaven Viewer")
        self.set_default_size(1200, 850)

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
        xml_window = builder.get_object("main_window")
        
        header_bar = builder.get_object("header_bar")
        if header_bar:
            xml_window.set_titlebar(None)
            self.set_titlebar(header_bar)

        content = xml_window.get_child()
        if content:
            xml_window.set_child(None)
            self.set_child(content)
        
        self.builder = builder
        self.entry = builder.get_object("entry")
        self.btn_search = builder.get_object("btn_search") 
        self.btn_settings = builder.get_object("btn_settings") 
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
        self.btn_settings.connect("clicked", self.open_settings)
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
        self.scan_downloaded_wallpapers() 
        self.start_new_search(self.current_query)
        
    def scan_downloaded_wallpapers(self):
        """
        Сканирует настроенную папку для загрузок.

        Обновляет словарь self.downloaded_files (ID: путь) и множество self.downloaded_ids (только ID).
        """
        self.downloaded_files = {} 
        self.downloaded_ids.clear()
        download_path = self.settings.get('download_path', '')
        
        if not download_path or not os.path.isdir(download_path):
            return

        for ext in ['*.jpg', '*.png', '*.jpeg']:
            for file_path in glob.glob(os.path.join(download_path, ext)):
                filename = os.path.basename(file_path)
                wallpaper_id = filename.split('.')[0] 
                if wallpaper_id:
                    self.downloaded_files[wallpaper_id] = file_path
        
        self.downloaded_ids = set(self.downloaded_files.keys()) 
        print(f"Найдено скачанных обоев: {len(self.downloaded_ids)}")
        
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
        if win_width <= 1: win_width = 1200 
        available_width = win_width - 40 
        target_width = (available_width // cols) - 15 
        if target_width < 50: target_width = 50
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
        
    def get_cache_dir(self):
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

    def open_settings(self, widget):
        """Открывает окно настроек (SettingsWindow)."""
        SettingsWindow(self).present()
        
    def check_api_key_on_purity_change(self, toggle_button):
        """
        Проверяет наличие API-ключа при попытке включить Sketchy/NSFW.
        Открывает настройки, если ключ отсутствует.
        """
        api_key = self.settings.get('api_key', '')
        if toggle_button.get_active() and not api_key:
            self.open_settings(None)
            toggle_button.set_active(False) 
        self.on_filter_changed(toggle_button)
        
    def on_scroll_changed(self, adj):
        """
        Обработчик изменения положения скролла. 
        Запускает загрузку следующей страницы, если достигнут низ.
        """
        if self.is_loading or not self.has_more_pages or self.is_downloaded_mode: 
            return
        current_pos = adj.get_value() + adj.get_page_size()
        max_height = adj.get_upper()
        if max_height - current_pos < 300:
            self.load_next_page()

    def load_next_page(self):
        """Увеличивает номер страницы и запускает загрузку следующего блока обоев."""
        self.current_page += 1
        self.load_wallpapers(self.current_query, self.current_page)
        
    def get_api_params(self, query, page):
        """
        Формирует словарь параметров для запроса к Wallhaven API на основе текущих фильтров.

        Args:
            query (str): Поисковый запрос.
            page (int): Номер страницы.

        Returns:
            dict: Параметры запроса.
        """
        c_gen = "1" if self.btn_general.get_active() else "0"
        c_ani = "1" if self.btn_anime.get_active() else "0"
        c_peo = "1" if self.btn_people.get_active() else "0"
        p_sfw = "1" if self.btn_sfw.get_active() else "0"
        api_key = self.settings.get('api_key', '')
        
        # Обработка Purity в зависимости от наличия API-ключа
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
        sorting = sort_modes[sort_idx] if sort_idx < len(sort_modes) else "vievs"
        
        res_idx = self.res_dropdown.get_selected()
        ratio_idx = self.ratio_dropdown.get_selected()
        selected_res = RESOLUTION_OPTIONS[res_idx][1]
        selected_ratio = RATIO_OPTIONS[ratio_idx][1]

        params = {
            "q": query, "categories": f"{c_gen}{c_ani}{c_peo}", 
            "purity": f"{p_sfw}{p_sky}{p_nsf}", "sorting": sorting, "page": page
        }
        if selected_res: params["resolutions"] = selected_res
        if selected_ratio: params["ratios"] = selected_ratio
        if api_key: params["apikey"] = api_key
        return params

    @staticmethod
    def load_pixbuf_from_bytes(img_bytes):
        """
        Создает GdkPixbuf из байтов изображения.

        Использует GdkPixbuf.PixbufLoader для корректной обработки данных.

        Args:
            img_bytes (bytes): Сырые байты изображения (JPEG, PNG и т. д.).

        Returns:
            GdkPixbuf.Pixbuf or None: Созданный Pixbuf или None в случае ошибки.
        """
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(img_bytes)
            loader.close()
            return loader.get_pixbuf()
        except Exception as e:
            print(f"Ошибка создания Pixbuf: {e}")
            return None
    
    def load_thumbnail_async(self, placeholder_btn, thumb_url, full_url, wallpaper_id, local_path=None): 
        """
        Загружает миниатюру в фоне, используя многопоточность.

        Приоритет загрузки: локальный файл -> кэш -> сеть.
        Обновляет UI после завершения загрузки или при возникновении ошибки.

        Args:
            placeholder_btn (Gtk.Button): Кнопка-заглушка, которую нужно обновить.
            thumb_url (str or None): URL миниатюры для загрузки из сети/кэша.
            full_url (str): URL полноразмерного изображения (для передачи в FullImageWindow).
            wallpaper_id (str): Уникальный ID обоев.
            local_path (str, optional): Полный локальный путь к файлу, если он скачан.
        """
        cache_dir = self.get_cache_dir()
        
        def worker():
            img_data = None
            cache_path = None

            # 1. ЛОКАЛЬНАЯ ЗАГРУЗКА (ЕСЛИ ФАЙЛ СКАЧАН)
            if local_path and os.path.exists(local_path):
                try:
                    with open(local_path, "rb") as f: 
                        img_data = f.read()
                    print(f"Миниатюра загружена локально для ID: {wallpaper_id}")
                    
                except Exception as e:
                    print(f"Ошибка чтения локального файла {local_path}: {e}")
                    img_data = None
            
            # 2. Кэш (только если нет локального пути, но есть URL миниатюры)
            elif thumb_url and cache_dir:
                filename = thumb_url.split('/')[-1]
                cache_path = os.path.join(cache_dir, filename)
                if os.path.exists(cache_path):
                    try:
                        with open(cache_path, "rb") as f: img_data = f.read()
                    except Exception: img_data = None 

            # 3. Сеть (только если нет локального пути и кэша, но есть URL)
            if img_data is None and thumb_url:
                try:
                    resp = requests.get(thumb_url, timeout=15)
                    resp.raise_for_status()
                    img_data = resp.content
                    if cache_path: 
                        try:
                            with open(cache_path, "wb") as f: f.write(img_data)
                        except Exception: pass
                except Exception as e:
                    print(f"Ошибка загрузки {thumb_url}: {e}")
                    GLib.idle_add(self.show_error_indicator, placeholder_btn, wallpaper_id)
                    return 

            # 4. Обновление UI
            if img_data:
                try:
                    pixbuf = MainWindow.load_pixbuf_from_bytes(img_data)
                    if pixbuf:
                        target_width, target_height = self.get_thumbnail_size()
                        pixbuf = pixbuf.scale_simple(
                            target_width, 
                            target_height, 
                            GdkPixbuf.InterpType.BILINEAR
                        )
                        GLib.idle_add(self.update_thumbnail_ui, placeholder_btn, pixbuf, wallpaper_id)
                except Exception as e:
                    print(f"Ошибка создания Pixbuf из данных: {e}")
                    GLib.idle_add(self.show_error_indicator, placeholder_btn, wallpaper_id)

        threading.Thread(target=worker, daemon=True).start()
    
    def update_thumbnail_ui(self, btn, pixbuf, wallpaper_id): 
        """
        Заменяет содержимое заглушки на загруженное изображение.

        Args:
            btn (Gtk.Button): Кнопка, на которой отображается миниатюра.
            pixbuf (GdkPixbuf.Pixbuf): Загруженная и масштабированная миниатюра.
            wallpaper_id (str): ID обоев.
        """
        try:
            btn.set_child(None)
            btn.remove_css_class("skeleton")
            
            if wallpaper_id in self.downloaded_ids:
                btn.add_css_class("downloaded") 
                
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

    def open_full_image(self, widget, url):
        """
        Открывает окно полноразмерного просмотра для выбранных обоев.
        """
        wallpaper_id = url.split('/')[-1].split('.')[0]
        local_path = self.downloaded_files.get(wallpaper_id)
        win = FullImageWindow(self, url, self.settings.get('download_path', ''), local_path) 
        win.present()

    def on_search_clicked(self, widget):
        """Обработчик нажатия кнопки поиска или Enter в поле ввода."""
        query = self.entry.get_text().strip()
        search_state = self.get_current_search_state()
        final_settings = {**self.settings, **search_state}
        save_settings(final_settings)
        self.settings = final_settings
        self.start_new_search(query)
        
    def create_placeholder_btn(self, full_url, wallpaper_id): 
        """
        Создает кнопку-заглушку ('скелет') с анимацией загрузки.
        """
        width, height = self.get_thumbnail_size()
        btn = Gtk.Button()
        btn.set_size_request(-1, height)
        btn.set_hexpand(True)
        btn.set_margin_start(5)
        btn.set_margin_end(5)
        btn.set_margin_top(5)
        btn.set_margin_bottom(5)
        if wallpaper_id in self.downloaded_ids:
             btn.add_css_class("downloaded") 
        btn.add_css_class("skeleton")
        btn.add_css_class("thumbnail")
        s = Gtk.Spinner()
        s.start()
        s.set_halign(Gtk.Align.CENTER)
        s.set_valign(Gtk.Align.CENTER)
        btn.set_child(s)
        btn.connect("clicked", self.open_full_image, full_url)
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
            if child is None: break
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
                full_url = f"https://w.wallhaven.cc/full/{w_id[0:2]}/wallhaven-{w_id}.jpg"
                items_to_add.append((None, full_url, w_id, local_path)) 
            GLib.idle_add(self.create_placeholders_and_load, items_to_add)
            GLib.idle_add(self.finish_loading_page, False)
            self.is_loading = False
            return
            
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
                last_page = meta.get("last_page", 1)
                more_pages = page < last_page
                GLib.idle_add(self.finish_loading_page, more_pages)
                
            except Exception as e:
                GLib.idle_add(self.show_infobar, f"Ошибка API: {e}")
                GLib.idle_add(self.finish_loading_page, False)

        threading.Thread(target=worker, daemon=True).start()
    
    def create_placeholders_and_load(self, items):
        """
        Создает заглушки в UI и запускает асинхронную загрузку миниатюр.
        """
        for thumb_url, full_url, wallpaper_id, local_path in items: 
            btn = self.create_placeholder_btn(full_url, wallpaper_id) 
            self.flowbox.append(btn)
            self.load_thumbnail_async(btn, thumb_url, full_url, wallpaper_id, local_path) 

    def finish_loading_page(self, has_more):
        """
        Завершает процесс загрузки страницы, обновляет статус и скрывает спиннер.
        """
        self.is_loading = False
        self.has_more_pages = has_more
        self.bottom_spinner.stop()
        self.bottom_spinner.set_visible(False)


# --- FullImageWindow ---
class FullImageWindow(Gtk.Window):
    """
    Окно для полноразмерного просмотра и управления обоями.

    Осуществляет загрузку полного изображения, его сохранение на диск
    и установку в качестве обоев рабочего стола.

    Args:
        parent (MainWindow): Ссылка на родительское окно.
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
        builder = Gtk.Builder.new_from_file(ui_path)
        xml_window = builder.get_object("full_image_window")
        
        w, h = xml_window.get_default_size()
        self.set_default_size(w, h)
        self.set_title(f"Wallhaven - ID: {self.wallpaper_id}")
        
        header_bar = builder.get_object("header_bar")
        if header_bar:
            xml_window.set_titlebar(None)
            self.set_titlebar(header_bar)

        content = xml_window.get_child()
        if content:
            xml_window.set_child(None)
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
            threading.Thread(target=self.load_image_and_info, daemon=True).start()

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
            self.spinner.stop()
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
                info_url = f"https://wallhaven.cc/api/v1/w/{self.wallpaper_id}"
                info_resp = requests.get(info_url, timeout=5).json()
                resolution = info_resp.get("data", {}).get("resolution", "") 
                GLib.idle_add(self.update_title, resolution)
            except Exception:
                GLib.idle_add(self.update_title, resolution)
                
            # Загрузка по сети
            try:
                resp = requests.get(self.image_url, stream=True, timeout=60)
                resp.raise_for_status()
                
                total_bytes = int(resp.headers.get('content-length', 0))
                current_bytes = 0
                self.image_data = b''
                
                if total_bytes == 0:
                    GLib.idle_add(self.spinner.start)
                else:
                    GLib.idle_add(self.update_progress, 0, total_bytes) 
                
                for chunk in resp.iter_content(chunk_size=8192):
                    self.image_data += chunk
                    current_bytes += len(chunk)
                    if total_bytes > 0:
                        GLib.idle_add(self.update_progress, current_bytes, total_bytes)
            
            except Exception:
                GLib.idle_add(self.spinner.stop)
                GLib.idle_add(lambda: self.progress_bar.set_visible(False))
                self.image_data = None


        # 2. Обновление UI
        if self.image_data:
            try:
                pixbuf = MainWindow.load_pixbuf_from_bytes(self.image_data)
                if pixbuf:
                    GLib.idle_add(self.update_image, pixbuf)
            except Exception as e:
                print(f"Ошибка: {e}")
        else:
            GLib.idle_add(self.spinner.stop)


    def update_title(self, resolution):
        """Обновляет заголовок окна с информацией о разрешении."""
        if resolution: res_str = f" ({resolution})"
        else: res_str = ""
        self.set_title(f"Wallhaven - ID: {self.wallpaper_id}{res_str}")

    def update_image(self, pixbuf):
        """
        Отображает загруженное изображение в Gtk.Picture.

        Args:
            pixbuf (GdkPixbuf.Pixbuf): Загруженное изображение.
        """
        # --- ВОЗВРАТ К РАБОЧЕМУ МЕТОДУ (Gdk.Texture.new_for_pixbuf) ---
        texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        # -------------------------------------------------------------------
        
        self.picture.set_paintable(texture)
        self.spinner.stop()
        self.spinner.set_visible(False)
        self.progress_bar.set_visible(False)
        
        if not self.local_path:
            self.save_btn.set_sensitive(True)
        self.set_wp_btn.set_sensitive(True) 

    def on_save_clicked(self, btn):
        """Обработчик нажатия кнопки сохранения. Сохраняет файл либо по умолчанию, либо через диалог."""
        if not self.image_data: return
        
        # --- Определение формата ---
        content_type = ""
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(self.image_data)
            content_type = loader.get_format().get_name()
            loader.close()
        except Exception:
            content_type = "jpeg" 

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
                
            except Exception: self.open_dialog(name)
        else: self.open_dialog(name)

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
                with open(local_path, "wb") as file: file.write(self.image_data)
                
                self.local_path = local_path
                self.save_btn.set_label("Скачано")
                self.save_btn.set_sensitive(False)
                self.set_wp_btn.set_sensitive(True)
                
                self.parent_window.scan_downloaded_wallpapers()
                self.parent_window.flowbox.invalidate_filter()
                
        except Exception: pass
        
    def on_set_wallpaper_clicked(self, btn):
        """
        Устанавливает изображение в качестве обоев рабочего стола.
        Меняет иконку на "выбрано" на 1.5 секунды.
        """
        if self.local_path:
            try:
                threading.Thread(target=self._set_wallpaper_worker, args=(self.local_path,), daemon=True).start()
                btn.set_icon_name("object-select-symbolic")  # Кратковременная обратная связь
                GLib.timeout_add(1500, lambda: btn.set_icon_name("preferences-desktop-wallpaper-symbolic"))
            except Exception as e:
                print(f"Ошибка инициализации установки обоев: {e}")


    def _set_wallpaper_worker(self, path):
        """
        Рабочий поток для безопасной установки обоев.
        Проверяет наличие ключа 'picture-uri-dark' перед использованием.
        """
        try:
            uri = Gio.File.new_for_path(path).get_uri()
            settings = Gio.Settings.new('org.gnome.desktop.background')

            # --- 🔑 Безопасная проверка наличия ключа ---
            schema_source = Gio.SettingsSchemaSource.get_default()
            schema = schema_source.lookup('org.gnome.desktop.background', True)

            if schema and schema.has_key('picture-uri-dark'):
                # Устанавливаем отдельно для светлого и тёмного режима
                settings.set_string('picture-uri', uri)
                settings.set_string('picture-uri-dark', uri)
                print(f"Обои установлены: {uri} (поддержка dark mode)")
            else:
                # Только общий ключ
                settings.set_string('picture-uri', uri)
                print(f"Обои установлены (без picture-uri-dark): {uri}")

        except Exception as e:
            # Даже если ошибка GIO, мы её перехватим
            print(f"Ошибка установки обоев: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    app = WallpaperViewer()
    app.run()