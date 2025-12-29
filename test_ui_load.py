#!/usr/bin/env python3
"""
Тестовый скрипт для проверки загрузки UI элементов.
"""

import sys
sys.path.insert(0, '/home/vadim/Документы/wallhaven_test_project/src')

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk
from wallhaven_viewer.utils import resolve_path

def test_fullimage_ui():
    """Проверяет загрузку fullimage.ui"""
    try:
        ui_path = resolve_path("fullimage.ui")
        builder = Gtk.Builder.new_from_file(ui_path)
        
        # Проверяем ключевые элементы
        objects = [
            "full_image_window",
            "picture",
            "spinner",
            "save_btn",
            "set_wp_btn",
            "progress_bar",
            "meta_label",
            "tags_flowbox"
        ]
        
        for obj_id in objects:
            obj = builder.get_object(obj_id)
            status = "✅" if obj else "❌"
            print(f"{status} {obj_id}: {obj}")
        
        print("\n📋 fullimage.ui загружена успешно!")
        return True
    except Exception as e:
        print(f"❌ Ошибка загрузки fullimage.ui: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mainwindow_ui():
    """Проверяет загрузку mainwindow.ui"""
    try:
        ui_path = resolve_path("mainwindow.ui")
        builder = Gtk.Builder.new_from_file(ui_path)
        
        obj = builder.get_object("root")
        if obj:
            print("✅ mainwindow.ui загружена успешно!")
            return True
        else:
            print("❌ root контейнер не найден в mainwindow.ui")
            return False
    except Exception as e:
        print(f"❌ Ошибка загрузки mainwindow.ui: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Тестирование загрузки UI файлов...\n")
    
    result1 = test_fullimage_ui()
    print()
    result2 = test_mainwindow_ui()
    
    if result1 and result2:
        print("\n✅ Все проверки пройдены!")
        sys.exit(0)
    else:
        print("\n❌ Некоторые проверки не прошли")
        sys.exit(1)
