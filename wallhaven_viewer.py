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

DEFAULT_SETTINGS = {
    'api_key': '',
    'download_path': '',
    'columns': '4'
}

# --- Настройки ---

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
    config['Settings'] = settings_dict
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
        new_settings = {
            'api_key': self.entry_api.get_text().strip(),
            'download_path': self.entry_path.get_text().strip(),
            'columns': str(int(self.spin_cols.get_value()))
        }
        save_settings(new_settings)
        self.parent_window.apply_settings(new_settings)
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
        self.current_query = "" 
        self.settings = load_settings()
        self.is_loading = False
        self.has_more_pages = True

        # UI
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        self.set_child(vbox)

        # Поиск
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox.append(search_box)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Поиск (оставьте пустым для топа)...")
        self.entry.set_hexpand(True)
        self.entry.connect("activate", self.on_search_clicked)
        search_box.append(self.entry)

        btn_search = Gtk.Button(label="Поиск / Обновить")
        btn_search.connect("clicked", self.on_search_clicked)
        search_box.append(btn_search)

        # Фильтры
        filters_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        vbox.append(filters_box)

        cat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        cat_box.add_css_class("linked")
        filters_box.append(cat_box)
        
        self.btn_general = Gtk.ToggleButton(label="General")
        self.btn_general.set_active(True)
        cat_box.append(self.btn_general)
        self.btn_anime = Gtk.ToggleButton(label="Anime")
        self.btn_anime.set_active(True)
        cat_box.append(self.btn_anime)
        self.btn_people = Gtk.ToggleButton(label="People")
        self.btn_people.set_active(True)
        cat_box.append(self.btn_people)

        filters_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        purity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        purity_box.add_css_class("linked")
        filters_box.append(purity_box)
        
        self.btn_sfw = Gtk.ToggleButton(label="SFW")
        self.btn_sfw.set_active(True)
        purity_box.append(self.btn_sfw)
        self.btn_sketchy = Gtk.ToggleButton(label="Sketchy")
        purity_box.append(self.btn_sketchy)
        self.btn_sketchy.connect("clicked", self.check_api_key_on_purity_change)
        self.btn_nsfw = Gtk.ToggleButton(label="NSFW")
        purity_box.append(self.btn_nsfw)
        self.btn_nsfw.connect("clicked", self.check_api_key_on_purity_change)

        filters_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        filters_box.append(Gtk.Label(label="Сортировка:"))
        sort_options = Gtk.StringList()
        for opt in ["Relevance", "Random", "Date Added", "Views", "Favorites", "Toplist", "Hot"]:
            sort_options.append(opt)
        
        self.sort_dropdown = Gtk.DropDown(model=sort_options)
        self.sort_dropdown.set_selected(5) 
        filters_box.append(self.sort_dropdown)
        
        btn_settings = Gtk.Button(icon_name="preferences-system-symbolic")
        btn_settings.set_tooltip_text("Настройки")
        btn_settings.connect("clicked", self.open_settings)
        filters_box.append(btn_settings)

        # Контент
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        vbox.append(self.scrolled)

        self.v_adj = self.scrolled.get_vadjustment()
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

        # Спиннер для "Загрузить еще"
        self.bottom_spinner = Gtk.Spinner()
        self.bottom_spinner.set_size_request(32, 32)
        self.bottom_spinner.set_halign(Gtk.Align.CENTER)
        content_box.append(self.bottom_spinner)

        self.start_new_search("")

    # --- Логика ---

    def apply_settings(self, new_settings):
        old_cols = int(self.settings.get('columns', 4))
        old_key = self.settings.get('api_key', '')
        self.settings = new_settings
        
        new_cols = int(self.settings.get('columns', 4))
        self.flowbox.set_min_children_per_line(new_cols)
        self.flowbox.set_max_children_per_line(new_cols)
        
        if old_cols != new_cols or old_key != new_settings['api_key']:
            self.start_new_search(self.current_query)

    def open_settings(self, widget):
        SettingsWindow(self).present()
        
    def check_api_key_on_purity_change(self, toggle_button):
        api_key = self.settings.get('api_key', '')
        if toggle_button.get_active() and not api_key:
            self.open_settings(None)
            toggle_button.set_active(False) 

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

        sort_idx = self.sort_dropdown.get_selected()
        sort_modes = ["relevance", "random", "date_added", "views", "favorites", "toplist", "hot"]
        sorting = sort_modes[sort_idx] if sort_idx < len(sort_modes) else "relevance"

        params = {
            "q": query, "categories": f"{c_gen}{c_ani}{c_peo}", 
            "purity": f"{p_sfw}{p_sky}{p_nsf}", "sorting": sorting, "page": page
        }
        if api_key: params["apikey"] = api_key
        return params

    @staticmethod
    def load_pixbuf_from_bytes(img_bytes):
        loader = GdkPixbuf.PixbufLoader()
        loader.write(img_bytes)
        loader.close()
        return loader.get_pixbuf()

    def load_thumbnail_async(self, thumb_url, full_url):
        def worker():
            try:
                img_data = requests.get(thumb_url, timeout=10).content
                pixbuf = self.load_pixbuf_from_bytes(img_data)
                GLib.idle_add(self.add_thumbnail_to_ui, pixbuf, full_url)
            except Exception as e:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def add_thumbnail_to_ui(self, pixbuf, full_url):
        try:
            cols = int(self.settings.get('columns', 4))
            
            available_width = 1050
            target_width = (available_width // cols) - 12
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
        except Exception as e:
            print(f"Err UI: {e}")

    def open_full_image(self, widget, url):
        win = FullImageWindow(self, url, self.settings.get('download_path', ''))
        win.present()

    def on_search_clicked(self, widget):
        self.start_new_search(self.entry.get_text().strip())

    def start_new_search(self, query):
        self.current_page = 1
        self.current_query = query
        self.has_more_pages = True
        
        while True:
            child = self.flowbox.get_first_child()
            if child is None: break
            self.flowbox.remove(child)
        
        # Центральный спиннер для первой загрузки
        self.center_spinner = Gtk.Spinner()
        self.center_spinner.set_size_request(32, 32)
        self.center_spinner.set_halign(Gtk.Align.CENTER)
        self.center_spinner.set_valign(Gtk.Align.CENTER)
        # Используем тот же "трюк" с коробкой для безопасности
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

                if not data and page == 1: print("Пусто.")
                
                for w in data:
                    thumbs = w.get("thumbs", {})
                    thumb = thumbs.get("large") or thumbs.get("original")
                    full = w.get("path")
                    if thumb and full:
                        self.load_thumbnail_async(thumb, full)

                last_page = meta.get("last_page", 1)
                more_pages = page < last_page
                
                GLib.idle_add(self.on_api_response_ui, data, more_pages)
                
            except Exception as e:
                print("Err API:", e)
                GLib.idle_add(self.stop_center_spinner)
                GLib.idle_add(self.on_api_response_ui, [], False)

        threading.Thread(target=worker, daemon=True).start()

    def stop_center_spinner(self):
        if hasattr(self, 'center_spinner') and self.center_spinner.get_parent():
            # Удаляем родительский Box, в котором лежит спиннер
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


class FullImageWindow(Gtk.Window):
    def __init__(self, parent, image_url, download_path):
        super().__init__(transient_for=parent)
        self.set_default_size(1000, 700)
        self.image_url = image_url
        self.download_path = download_path
        self.image_data = None

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

        # === ИСПРАВЛЕНИЕ: КОНТЕЙНЕР ДЛЯ СПИННЕРА ===
        # Чтобы спиннер не раздувался на весь экран, кладем его в Box
        spinner_box = Gtk.Box()
        spinner_box.set_halign(Gtk.Align.CENTER)
        spinner_box.set_valign(Gtk.Align.CENTER)
        
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(32, 32) # Размер 32x32
        self.spinner.set_hexpand(False)
        self.spinner.set_vexpand(False)
        self.spinner.start()
        
        spinner_box.append(self.spinner)
        overlay.add_overlay(spinner_box)

        threading.Thread(target=self.load_image, daemon=True).start()

    def load_image(self):
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
