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
        self.entry.set_placeholder_text("Введите запрос (например: cyberpunk, nature)...")
        self.entry.set_hexpand(True)
        self.entry.connect("activate", self.on_search_clicked) # Поиск по Enter
        search_box.append(self.entry)

        btn = Gtk.Button(label="Поиск")
        btn.connect("clicked", self.on_search_clicked)
        search_box.append(btn)

        # === Область прокрутки и сетка ===
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        vbox.append(scrolled)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(4) # Количество картинок в ряд
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.set_child(self.flowbox)

        # Загружаем стартовую выдачу
        self.load_wallpapers("toplist")


    # ======= ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ========
    @staticmethod
    def load_pixbuf_from_bytes(img_bytes):
        loader = GdkPixbuf.PixbufLoader()
        loader.write(img_bytes)
        loader.close()
        return loader.get_pixbuf()

    def add_wallpaper(self, thumb_url, full_url):
        """Создает карточку с картинкой"""
        try:
            # 1. Загружаем байты
            img_data = requests.get(thumb_url, timeout=10).content
            # 2. Создаем Pixbuf
            pixbuf = self.load_pixbuf_from_bytes(img_data)
            
            # 3. GTK4 требует Texture вместо Pixbuf для отображения
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            
            # 4. Используем Gtk.Picture для умного масштабирования
            picture = Gtk.Picture.new_for_paintable(texture)
            picture.set_content_fit(Gtk.ContentFit.COVER) # Заполнить квадратик
            picture.set_size_request(280, 200) # Размер миниатюры в сетке
            
        except Exception as e:
            print(f"Ошибка загрузки миниатюры: {e}")
            return

        button = Gtk.Button()
        button.set_child(picture)
        button.set_margin_start(5)
        button.set_margin_end(5)
        button.set_margin_top(5)
        button.set_margin_bottom(5)
        
        # Передаем full_url для открытия
        button.connect("clicked", self.open_full_image, full_url)
        
        self.flowbox.append(button)


    def open_full_image(self, widget, url):
        win = FullImageWindow(self, url)
        win.present()


    # ======= ПОИСК ========
    def on_search_clicked(self, widget):
        query = self.entry.get_text().strip()
        self.load_wallpapers(query)

    def load_wallpapers(self, query):
        # Безопасная очистка FlowBox в GTK4
        while True:
            child = self.flowbox.get_first_child()
            if child is None:
                break
            self.flowbox.remove(child)

        def worker():
            # Параметры поиска Wallhaven
            params = {
                "q": query, 
                "categories": "111", 
                "purity": "100", # Только SFW (безопасные)
                "sorting": "relevance"
            }
            try:
                print(f"Запрос к API: {query}...")
                response = requests.get(API_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json().get("data", [])

                if not data:
                    print("Ничего не найдено.")

                for w in data:
                    thumbs = w.get("thumbs", {})
                    # ВАЖНО: Берем 'large' для четкости в сетке
                    thumb_url = thumbs.get("large") or thumbs.get("original")
                    full_url = w.get("path")
                    
                    if thumb_url and full_url:
                        GLib.idle_add(self.add_wallpaper, thumb_url, full_url)

            except Exception as e:
                print("Ошибка API:", e)

        threading.Thread(target=worker, daemon=True).start()


# ======== ОКНО ПОЛНОГО ПРОСМОТРА ========
class FullImageWindow(Gtk.Window):
    def __init__(self, parent, image_url):
        super().__init__(transient_for=parent)
        self.set_title("Просмотр изображения")
        self.set_default_size(1000, 700)
        self.image_url = image_url

        # Используем Overlay для наложения спиннера поверх картинки
        overlay = Gtk.Overlay()
        self.set_child(overlay)

        # Gtk.Picture автоматически масштабирует контент
        self.picture = Gtk.Picture()
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN) # Вписать целиком
        self.picture.set_can_shrink(True) 
        overlay.set_child(self.picture)

        # Индикатор загрузки
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