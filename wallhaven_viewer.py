#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GdkPixbuf, GLib, Gdk
import requests
import threading

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
        self.set_default_size(1200, 800)

        # Состояние
        self.current_page = 1
        self.current_query = "toplist"

        # === Основной контейнер ===
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        self.set_child(vbox)

        # === Поисковая строка ===
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox.append(search_box)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Введите запрос...")
        self.entry.set_hexpand(True)
        self.entry.connect("activate", self.on_search_clicked)
        search_box.append(self.entry)

        btn = Gtk.Button(label="Поиск")
        btn.connect("clicked", self.on_search_clicked)
        search_box.append(btn)

        # === Область прокрутки ===
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        vbox.append(scrolled)

        # Внутри скролла нужен VBox, чтобы разместить FlowBox и кнопку "Еще" друг под другом
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        scrolled.set_child(content_box)

        # Сетка изображений
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(4)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        content_box.append(self.flowbox)

        # Кнопка "Загрузить ещё"
        self.load_more_btn = Gtk.Button(label="Загрузить ещё...")
        self.load_more_btn.set_margin_bottom(20)
        self.load_more_btn.set_visible(False) # Скрыта по умолчанию
        self.load_more_btn.connect("clicked", self.on_load_more_clicked)
        content_box.append(self.load_more_btn)

        # Загружаем стартовую выдачу
        self.start_new_search("toplist")


    # ======= ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ========
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
            print(f"Ошибка загрузки миниатюры: {e}")
            return

        button = Gtk.Button()
        button.set_child(picture)
        button.set_margin_start(5)
        button.set_margin_end(5)
        button.set_margin_top(5)
        button.set_margin_bottom(5)
        button.connect("clicked", self.open_full_image, full_url)
        
        self.flowbox.append(button)

    def open_full_image(self, widget, url):
        win = FullImageWindow(self, url)
        win.present()


    # ======= ЛОГИКА ПОИСКА И ПАГИНАЦИИ ========
    def on_search_clicked(self, widget):
        query = self.entry.get_text().strip()
        self.start_new_search(query)

    def on_load_more_clicked(self, widget):
        self.current_page += 1
        self.load_wallpapers(self.current_query, self.current_page)

    def start_new_search(self, query):
        self.current_page = 1
        self.current_query = query
        
        # Очищаем старые результаты
        while True:
            child = self.flowbox.get_first_child()
            if child is None:
                break
            self.flowbox.remove(child)
            
        self.load_more_btn.set_visible(False)
        self.load_wallpapers(query, 1)

    def load_wallpapers(self, query, page):
        def worker():
            params = {
                "q": query, 
                "categories": "111", 
                "purity": "100", 
                "sorting": "relevance",
                "page": page  # <--- ПЕРЕДАЕМ НОМЕР СТРАНИЦЫ
            }
            try:
                print(f"Загрузка: '{query}', страница {page}...")
                # Блокируем кнопку пока грузится
                GLib.idle_add(self.load_more_btn.set_sensitive, False)
                GLib.idle_add(self.load_more_btn.set_label, "Загрузка...")

                response = requests.get(API_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json().get("data", [])
                meta = response.json().get("meta", {})

                if not data and page == 1:
                    print("Ничего не найдено.")
                
                # Добавляем картинки
                for w in data:
                    thumbs = w.get("thumbs", {})
                    thumb_url = thumbs.get("large") or thumbs.get("original")
                    full_url = w.get("path")
                    
                    if thumb_url and full_url:
                        GLib.idle_add(self.add_wallpaper, thumb_url, full_url)

                # Проверяем, есть ли еще страницы
                last_page = meta.get("last_page", 1)
                has_more = page < last_page

                # Обновляем состояние кнопки
                GLib.idle_add(self.update_load_more_button, has_more)

            except Exception as e:
                print("Ошибка API:", e)
                GLib.idle_add(self.update_load_more_button, True) # Оставляем активной чтобы повторить

        threading.Thread(target=worker, daemon=True).start()

    def update_load_more_button(self, visible):
        self.load_more_btn.set_visible(visible)
        self.load_more_btn.set_sensitive(True)
        self.load_more_btn.set_label("Загрузить ещё...")


# ======== ОКНО ПОЛНОГО ПРОСМОТРА ========
class FullImageWindow(Gtk.Window):
    def __init__(self, parent, image_url):
        super().__init__(transient_for=parent)
        self.set_title("Просмотр изображения")
        self.set_default_size(1000, 700)
        self.image_url = image_url

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
            print(f"Загрузка оригинала: {self.image_url}")
            resp = requests.get(self.image_url, timeout=30)
            resp.raise_for_status()
            
            loader = GdkPixbuf.PixbufLoader()
            loader.write(resp.content)
            loader.close()
            pixbuf = loader.get_pixbuf()
            
            GLib.idle_add(self.update_image, pixbuf)
        except Exception as e:
            print("Ошибка загрузки фулла:", e)
            GLib.idle_add(self.spinner.stop)

    def update_image(self, pixbuf):
        texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        self.picture.set_paintable(texture)
        self.spinner.stop()
        self.spinner.set_visible(False)


if __name__ == "__main__":
    app = WallpaperViewer()
    app.run()
