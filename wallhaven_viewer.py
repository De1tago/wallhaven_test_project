#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GdkPixbuf, GLib, Gdk, Gio, GObject
import requests
import threading
import os

API_URL = "https://wallhaven.cc/api/v1/search"

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
        
        # === ВАШ API КЛЮЧ ===
        # Замените этот текст на ваш реальный API ключ с Wallhaven для доступа к NSFW/Sketchy
        self.api_key = "ВАШ_API_КЛЮЧ_СЮДА" 

        # === ГЛАВНЫЙ КОНТЕЙНЕР ===
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        self.set_child(vbox)

        # === 1. ПОИСКОВАЯ СТРОКА ===
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

        # === 2. ПАНЕЛЬ ФИЛЬТРОВ ===
        filters_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        vbox.append(filters_box)

        # --- Группа: Категории ---
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

        # --- Группа: Чистота (Purity) ---
        purity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        purity_box.add_css_class("linked")
        filters_box.append(purity_box)

        self.btn_sfw = Gtk.ToggleButton(label="SFW")
        self.btn_sfw.set_active(True)
        purity_box.append(self.btn_sfw)

        self.btn_sketchy = Gtk.ToggleButton(label="Sketchy")
        purity_box.append(self.btn_sketchy)

        self.btn_nsfw = Gtk.ToggleButton(label="NSFW")
        purity_box.append(self.btn_nsfw)

        filters_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # --- Сортировка ---
        lbl_sort = Gtk.Label(label="Сортировка:")
        filters_box.append(lbl_sort)

        sort_options = Gtk.StringList()
        sort_options.append("Relevance")   # 0
        sort_options.append("Random")      # 1
        sort_options.append("Date Added")  # 2
        sort_options.append("Views")       # 3
        sort_options.append("Favorites")   # 4
        sort_options.append("Toplist")     # 5
        sort_options.append("Hot")         # 6
        
        self.sort_dropdown = Gtk.DropDown(model=sort_options)
        # Устанавливаем "Toplist" (индекс 5) как сортировку по умолчанию
        self.sort_dropdown.set_selected(5) 
        filters_box.append(self.sort_dropdown)

        # === 3. ОБЛАСТЬ ПРОСМОТРА ===
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        vbox.append(scrolled)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        scrolled.set_child(content_box)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(4)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        content_box.append(self.flowbox)

        self.load_more_btn = Gtk.Button(label="Загрузить ещё...")
        self.load_more_btn.set_margin_bottom(20)
        self.load_more_btn.set_visible(False)
        self.load_more_btn.connect("clicked", self.on_load_more_clicked)
        content_box.append(self.load_more_btn)

        # === ЗАПУСК ПЕРВОГО ПОИСКА ===
        # Запускаем поиск сразу при инициализации, чтобы показать популярные обои
        self.start_new_search("")


    # ======= СБОР ПАРАМЕТРОВ ========
    def get_api_params(self, query, page):
        c_gen = "1" if self.btn_general.get_active() else "0"
        c_ani = "1" if self.btn_anime.get_active() else "0"
        c_peo = "1" if self.btn_people.get_active() else "0"
        categories = f"{c_gen}{c_ani}{c_peo}"

        p_sfw = "1" if self.btn_sfw.get_active() else "0"
        p_sky = "1" if self.btn_sketchy.get_active() else "0"
        p_nsf = "1" if self.btn_nsfw.get_active() else "0"
        purity = f"{p_sfw}{p_sky}{p_nsf}"

        selected_idx = self.sort_dropdown.get_selected()
        sorting_map = {
            0: "relevance",
            1: "random",
            2: "date_added",
            3: "views",
            4: "favorites",
            5: "toplist",
            6: "hot"
        }
        sorting = sorting_map.get(selected_idx, "relevance")

        params = {
            "q": query,
            "categories": categories,
            "purity": purity,
            "sorting": sorting,
            "page": page
        }
        
        # Добавление API КЛЮЧА
        if self.api_key and self.api_key != "ВАШ_API_КЛЮЧ_СЮДА":
            params["apikey"] = self.api_key

        return params


    # ======= СЕТЬ И UI ========
    @staticmethod
    def load_pixbuf_from_bytes(img_bytes):
        loader = GdkPixbuf.PixbufLoader()
        loader.write(img_bytes)
        loader.close()
        return loader.get_pixbuf()

    def add_wallpaper(self, thumb_url, full_url):
        try:
            img_data = requests.get(thumb_url, timeout=10).content
            pixbuf = self.load_pixbuf_from_bytes(img_data)
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            picture = Gtk.Picture.new_for_paintable(texture)
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_size_request(280, 200)
        except Exception as e:
            print(f"Ошибка картинки: {e}")
            return

        button = Gtk.Button()
        button.set_child(picture)
        
        # Исправленные отступы
        button.set_margin_start(5)
        button.set_margin_end(5)
        button.set_margin_top(5)
        button.set_margin_bottom(5)
        
        button.connect("clicked", self.open_full_image, full_url)
        self.flowbox.append(button)

    def open_full_image(self, widget, url):
        win = FullImageWindow(self, url)
        win.present()

    def on_search_clicked(self, widget):
        query = self.entry.get_text().strip()
        self.start_new_search(query)

    def on_load_more_clicked(self, widget):
        self.current_page += 1
        self.load_wallpapers(self.current_query, self.current_page)

    def start_new_search(self, query):
        self.current_page = 1
        self.current_query = query
        while True:
            child = self.flowbox.get_first_child()
            if child is None: break
            self.flowbox.remove(child)
        self.load_more_btn.set_visible(False)
        self.load_wallpapers(query, 1)

    def load_wallpapers(self, query, page):
        def worker():
            params = self.get_api_params(query, page)
            try:
                print(f"Запрос: {params}")
                GLib.idle_add(self.load_more_btn.set_sensitive, False)
                GLib.idle_add(self.load_more_btn.set_label, "Загрузка...")

                response = requests.get(API_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json().get("data", [])
                meta = response.json().get("meta", {})

                if not data and page == 1: print("Ничего не найдено.")
                
                for w in data:
                    thumbs = w.get("thumbs", {})
                    thumb_url = thumbs.get("large") or thumbs.get("original")
                    full_url = w.get("path")
                    if thumb_url and full_url:
                        GLib.idle_add(self.add_wallpaper, thumb_url, full_url)

                has_more = page < meta.get("last_page", 1)
                GLib.idle_add(self.update_load_more_button, has_more)
            except Exception as e:
                print("Ошибка API:", e)
                GLib.idle_add(self.update_load_more_button, True)

        threading.Thread(target=worker, daemon=True).start()

    def update_load_more_button(self, visible):
        self.load_more_btn.set_visible(visible)
        self.load_more_btn.set_sensitive(True)
        self.load_more_btn.set_label("Загрузить ещё...")


# ======== ОКНО ПОЛНОГО ПРОСМОТРА ========
class FullImageWindow(Gtk.Window):
    def __init__(self, parent, image_url):
        super().__init__(transient_for=parent)
        self.set_default_size(1000, 700)
        self.image_url = image_url
        self.image_data = None

        header = Gtk.HeaderBar()
        self.set_titlebar(header)
        
        self.save_btn = Gtk.Button(icon_name="document-save-symbolic")
        self.save_btn.set_sensitive(False)
        self.save_btn.connect("clicked", self.on_save_clicked)
        header.pack_end(self.save_btn)

        overlay = Gtk.Overlay()
        self.set_child(overlay)

        self.picture = Gtk.Picture()
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.picture.set_can_shrink(True) 
        overlay.set_child(self.picture)

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(64, 64)
        self.spinner.set_halign(Gtk.Align.CENTER)
        self.spinner.set_valign(Gtk.Align.CENTER)
        self.spinner.start()
        overlay.add_overlay(self.spinner)

        threading.Thread(target=self.load_image, daemon=True).start()

    def load_image(self):
        try:
            resp = requests.get(self.image_url, timeout=30)
            resp.raise_for_status()
            self.image_data = resp.content
            
            loader = GdkPixbuf.PixbufLoader()
            loader.write(self.image_data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            GLib.idle_add(self.update_image, pixbuf)
        except Exception as e:
            print("Ошибка фулла:", e)
            GLib.idle_add(self.spinner.stop)

    def update_image(self, pixbuf):
        texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        self.picture.set_paintable(texture)
        self.spinner.stop()
        self.spinner.set_visible(False)
        self.save_btn.set_sensitive(True)

    def on_save_clicked(self, btn):
        if not self.image_data: return
        suggested_name = self.image_url.split("/")[-1]
        file_dialog = Gtk.FileDialog()
        file_dialog.set_initial_name(suggested_name)
        file_dialog.save(self, None, self.on_save_finish)

    def on_save_finish(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file:
                with open(file.get_path(), "wb") as f:
                    f.write(self.image_data)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

if __name__ == "__main__":
    app = WallpaperViewer()
    app.run()
