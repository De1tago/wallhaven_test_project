"""
Qt-интерфейс Wallhaven Viewer — бэкенд для QML (PySide6).

Слой между общим ядром (core/) и QML-представлениями: модель списка обоев,
поиск с пагинацией, скачивание и установка обоев, настройки.
"""

import glob
import os
import threading
from pathlib import Path

import requests
from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    Property,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication

from wallhaven_viewer.core.api import WallhavenAPI
from wallhaven_viewer.core.cache import extract_wallpaper_id
from wallhaven_viewer.core.config import (
    RESOLUTION_OPTIONS,
    RATIO_OPTIONS,
    SORT_OPTIONS,
    load_settings,
    save_settings,
)
from wallhaven_viewer.core.models import WallpaperItem
from wallhaven_viewer.core.wallpaper_setter import set_desktop_wallpaper


class WallpaperListModel(QAbstractListModel):
    """Модель списка обоев для QML GridView/ListView."""

    Role = {
        "WallpaperId": Qt.UserRole + 1,
        "Thumb": Qt.UserRole + 2,
        "FullUrl": Qt.UserRole + 3,
        "LocalPath": Qt.UserRole + 4,
        "LocalUrl": Qt.UserRole + 5,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._items)

    def data(self, index, role):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role == self.Role["WallpaperId"]:
            return item.wallpaper_id
        if role == self.Role["Thumb"]:
            return item.thumb_url
        if role == self.Role["FullUrl"]:
            return item.full_url
        if role == self.Role["LocalPath"]:
            return item.local_path or ""
        if role == self.Role["LocalUrl"]:
            from PySide6.QtCore import QUrl

            if item.local_path:
                return QUrl.fromLocalFile(item.local_path).toString()
            return ""
        return None

    def roleNames(self):
        return {
            self.Role["WallpaperId"]: b"wallpaperId",
            self.Role["Thumb"]: b"thumb",
            self.Role["FullUrl"]: b"fullUrl",
            self.Role["LocalPath"]: b"localPath",
            self.Role["LocalUrl"]: b"localUrl",
        }

    def set_items(self, items):
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def append_items(self, items):
        if not items:
            return
        start = len(self._items)
        self.beginInsertRows(QModelIndex(), start, start + len(items) - 1)
        self._items.extend(items)
        self.endInsertRows()

    def refresh_local_paths(self, downloaded_files):
        """Обновляет localPath у элементов по новому списку скачанных файлов."""
        changed = False
        for i, item in enumerate(self._items):
            new_path = downloaded_files.get(item.wallpaper_id)
            if item.local_path != new_path:
                item.local_path = new_path
                changed = True
        if changed:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(max(0, len(self._items) - 1), 0),
            )


class Backend(QObject):
    """QObject-бэкенд, экспортируемый в QML как свойство `backend`."""

    # Сигналы для QML
    infoMessage = Signal(str)
    searchStarted = Signal()
    searchFinished = Signal()
    saved = Signal(str, str)  # (path, error) — path пуст при ошибке
    wallpaperSet = Signal(str)  # результат установки обоев (описание)

    # Notify-сигналы для свойств настроек
    columnsChanged = Signal()
    queryChanged = Signal()
    sortIndexChanged = Signal()
    resolutionIndexChanged = Signal()
    ratioIndexChanged = Signal()
    catGeneralChanged = Signal()
    catAnimeChanged = Signal()
    catPeopleChanged = Signal()
    puritySfwChanged = Signal()
    puritySketchyChanged = Signal()
    purityNsfwChanged = Signal()
    apiKeyChanged = Signal()
    downloadPathChanged = Signal()
    downloadedModeChanged = Signal()
    isDarkChanged = Signal()
    hasMoreChanged = Signal()

    # Внутренний сигнал завершения поиска (отправляется из фонового потока)
    _search_done = Signal(bool, object, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = WallpaperListModel(self)
        self._settings = load_settings()

        self._query = self._settings.get("last_query", "")
        self._page = 1
        self._loading = False
        self._has_more = True
        self._downloaded_mode = False
        self.downloaded_files = {}

        self._search_done.connect(self._on_search_done)

        # Следим за сменой системной темы (для режима "system")
        app = QGuiApplication.instance()
        if app is not None:
            style_hints = app.styleHints()
            style_hints.colorSchemeChanged.connect(self._on_system_scheme_changed)

        self.scan_downloaded()
        threading.Thread(target=self._cleanup_cache_async, daemon=True).start()

    # ------------------------------------------------------------------
    # Хелперы
    # ------------------------------------------------------------------
    def _persist(self):
        try:
            save_settings(self._settings)
        except Exception:
            pass

    def _effective_settings(self):
        return {**self._settings, **self.get_current_search_state()}

    def get_current_search_state(self):
        return {
            "last_query": self._query,
            "cat_general": str(self.catGeneral).lower(),
            "cat_anime": str(self.catAnime).lower(),
            "cat_people": str(self.catPeople).lower(),
            "purity_sfw": str(self.puritySfw).lower(),
            "purity_sketchy": str(self.puritySketchy).lower(),
            "purity_nsfw": str(self.purityNsfw).lower(),
            "sort_index": str(self.sortIndex),
            "resolution_index": str(self.resolutionIndex),
            "ratio_index": str(self.ratioIndex),
        }

    def _cleanup_cache_async(self):
        from wallhaven_viewer.core.cache import clean_cache

        try:
            clean_cache(7, 300)
        except Exception:
            pass

    def scan_downloaded(self):
        """Сканирует папку загрузок и индексирует файлы по ID обоев."""
        self.downloaded_files = {}
        raw = self._normalize_path(self._settings.get("download_path", ""))
        download_path = raw if raw else self._default_download_dir()
        if download_path and os.path.isdir(download_path):
            for ext in ("*.jpg", "*.jpeg", "*.png"):
                for file_path in glob.glob(os.path.join(download_path, ext)):
                    w_id = extract_wallpaper_id(os.path.basename(file_path))
                    if w_id:
                        self.downloaded_files[w_id] = file_path
        self._model.refresh_local_paths(self.downloaded_files)

    # ------------------------------------------------------------------
    # Свойства настроек (доступны из QML через backend.<name>)
    # ------------------------------------------------------------------
    @Property(int, notify=columnsChanged)
    def columns(self):
        return int(self._settings.get("columns", 4))

    @columns.setter
    def columns(self, value):
        self._settings["columns"] = str(int(value))
        self._persist()
        self.columnsChanged.emit()

    @Property(str, notify=queryChanged)
    def query(self):
        return self._query

    @query.setter
    def query(self, value):
        self._query = value
        self.queryChanged.emit()

    @Property(int, notify=sortIndexChanged)
    def sortIndex(self):
        return int(self._settings.get("sort_index", 5))

    @sortIndex.setter
    def sortIndex(self, value):
        self._settings["sort_index"] = str(int(value))
        self._persist()
        self.sortIndexChanged.emit()

    @Property(int, notify=resolutionIndexChanged)
    def resolutionIndex(self):
        return int(self._settings.get("resolution_index", 0))

    @resolutionIndex.setter
    def resolutionIndex(self, value):
        self._settings["resolution_index"] = str(int(value))
        self._persist()
        self.resolutionIndexChanged.emit()

    @Property(int, notify=ratioIndexChanged)
    def ratioIndex(self):
        return int(self._settings.get("ratio_index", 0))

    @ratioIndex.setter
    def ratioIndex(self, value):
        self._settings["ratio_index"] = str(int(value))
        self._persist()
        self.ratioIndexChanged.emit()

    @Property(bool, notify=catGeneralChanged)
    def catGeneral(self):
        return self._settings.get("cat_general", "true").lower() == "true"

    @catGeneral.setter
    def catGeneral(self, value):
        self._settings["cat_general"] = "true" if value else "false"
        self._persist()
        self.catGeneralChanged.emit()

    @Property(bool, notify=catAnimeChanged)
    def catAnime(self):
        return self._settings.get("cat_anime", "true").lower() == "true"

    @catAnime.setter
    def catAnime(self, value):
        self._settings["cat_anime"] = "true" if value else "false"
        self._persist()
        self.catAnimeChanged.emit()

    @Property(bool, notify=catPeopleChanged)
    def catPeople(self):
        return self._settings.get("cat_people", "true").lower() == "true"

    @catPeople.setter
    def catPeople(self, value):
        self._settings["cat_people"] = "true" if value else "false"
        self._persist()
        self.catPeopleChanged.emit()

    @Property(bool, notify=puritySfwChanged)
    def puritySfw(self):
        return self._settings.get("purity_sfw", "true").lower() == "true"

    @puritySfw.setter
    def puritySfw(self, value):
        self._settings["purity_sfw"] = "true" if value else "false"
        self._persist()
        self.puritySfwChanged.emit()

    @Property(bool, notify=puritySketchyChanged)
    def puritySketchy(self):
        return self._settings.get("purity_sketchy", "false").lower() == "true"

    @puritySketchy.setter
    def puritySketchy(self, value):
        api_key = self._settings.get("api_key", "")
        if value and not api_key:
            self.infoMessage.emit("Для Sketchy-контента нужен API-ключ (Настройки)")
            self.puritySketchyChanged.emit()  # возвращаем переключатель в прежнее положение
            return
        self._settings["purity_sketchy"] = "true" if value else "false"
        self._persist()
        self.puritySketchyChanged.emit()

    @Property(bool, notify=purityNsfwChanged)
    def purityNsfw(self):
        return self._settings.get("purity_nsfw", "false").lower() == "true"

    @purityNsfw.setter
    def purityNsfw(self, value):
        api_key = self._settings.get("api_key", "")
        if value and not api_key:
            self.infoMessage.emit("Для NSFW-контента нужен API-ключ (Настройки)")
            self.purityNsfwChanged.emit()  # возвращаем переключатель в прежнее положение
            return
        self._settings["purity_nsfw"] = "true" if value else "false"
        self._persist()
        self.purityNsfwChanged.emit()

    @Property(str, notify=apiKeyChanged)
    def apiKey(self):
        return self._settings.get("api_key", "")

    @apiKey.setter
    def apiKey(self, value):
        self._settings["api_key"] = value.strip()
        self._persist()
        self.apiKeyChanged.emit()

    @Property(str, notify=downloadPathChanged)
    def downloadPath(self):
        return self._settings.get("download_path", "")

    @downloadPath.setter
    def downloadPath(self, value):
        self._settings["download_path"] = self._normalize_path(value)
        self._persist()
        self.downloadPathChanged.emit()
        self.scan_downloaded()

    @staticmethod
    def _normalize_path(path):
        """Приводит путь из QML (возможно, с префиксом file:// и ведущим
        слэшем перед буквой диска на Windows, например ``/C:/...``) к
        корректному локальному пути."""
        path = (path or "").strip()
        if not path:
            return path
        if path.startswith("file://"):
            path = path[7:]
        # Windows: "/C:/Users/..." -> "C:/Users/..."
        if len(path) > 2 and path[0] == "/" and path[2] == ":":
            path = path[1:]
        return path

    @Property(bool, notify=downloadedModeChanged)
    def downloadedMode(self):
        return self._downloaded_mode

    @downloadedMode.setter
    def downloadedMode(self, value):
        self._downloaded_mode = bool(value)
        self.downloadedModeChanged.emit()

    @Property(bool, notify=hasMoreChanged)
    def hasMore(self):
        return self._has_more

    @Property(bool, notify=isDarkChanged)
    def isDark(self):
        """Эффективная тема: только определение из системы."""
        app = QGuiApplication.instance()
        if app is not None:
            try:
                scheme = app.styleHints().colorScheme()
            except Exception:
                scheme = Qt.ColorScheme.Unknown
            if scheme == Qt.ColorScheme.Dark:
                return True
            if scheme == Qt.ColorScheme.Light:
                return False
        # Qt не определил схему (Unknown) — пробуем системные настройки
        return self._system_dark_gnome()

    @staticmethod
    def _system_dark_gnome():
        """Определяет тёмную тему: gsettings (GNOME/niri и др.) + GTK-файлы."""
        import subprocess

        def _run(cmd):
            try:
                out = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=3
                )
                return out.stdout.strip().strip("'")
            except Exception:
                return None

        # gsettings: color-scheme (GNOME 42+)
        scheme = _run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"])
        if scheme == "prefer-dark":
            return True
        if scheme == "default":
            return False
        # gsettings: gtk-theme (например, adw-gtk3-dark)
        theme = _run(["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"])
        if theme and "dark" in theme.lower():
            return True

        from pathlib import Path as P

        config_home = os.environ.get("XDG_CONFIG_HOME", str(P.home() / ".config"))
        for rel in ("gtk-3.0/settings.ini", "gtk-4.0/settings.ini"):
            ini = P(config_home) / rel
            if ini.exists():
                try:
                    for line in ini.read_text(encoding="utf-8", errors="ignore").splitlines():
                        line = line.strip()
                        if line.startswith("gtk-application-prefer-dark-theme"):
                            return line.split("=", 1)[1].strip() in ("1", "true", "True")
                except OSError:
                    continue
        return False

    def _on_system_scheme_changed(self):
        """Системная тема сменилась — пересчитываем isDark."""
        self.isDarkChanged.emit()

    @Property(QObject, constant=True)
    def wallpaperModel(self):
        return self._model

    @Property(list, constant=True)
    def sortLabels(self):
        return SORT_OPTIONS

    @Property(list, constant=True)
    def resolutionLabels(self):
        return [label for label, _ in RESOLUTION_OPTIONS]

    @Property(list, constant=True)
    def ratioLabels(self):
        return [label for label, _ in RATIO_OPTIONS]

    # ------------------------------------------------------------------
    # Методы, вызываемые из QML
    # ------------------------------------------------------------------
    @Slot(str)
    def search(self, query):
        """Начинает новый поиск с первой страницы."""
        self._query = query.strip()
        self._settings["last_query"] = self._query
        self._persist()
        self._page = 1
        self._has_more = True
        self.hasMoreChanged.emit()
        self._loading = True
        self.searchStarted.emit()

        if self._downloaded_mode:
            self._load_downloaded_items()
        else:
            settings = self._effective_settings()
            threading.Thread(
                target=self._search_worker,
                args=(self._query, 1, settings, True),
                daemon=True,
            ).start()

    @Slot()
    def loadMore(self):
        """Подгружает следующую страницу (бесконечная прокрутка)."""
        if self._loading or not self._has_more or self._downloaded_mode:
            return
        self._page += 1
        self._loading = True
        self.searchStarted.emit()
        settings = self._effective_settings()
        threading.Thread(
            target=self._search_worker,
            args=(self._query, self._page, settings, False),
            daemon=True,
        ).start()

    def _search_worker(self, query, page, settings, reset):
        try:
            data, meta = WallhavenAPI.search_wallpapers(query, page, settings)
        except Exception:
            data, meta = None, None

        if data is None:
            if reset:
                self._search_done.emit(True, [], False)
                self.infoMessage.emit("Ошибка загрузки: проверьте подключение к интернету")
            else:
                self._search_done.emit(False, [], False)
            return

        items = []
        for raw in data:
            item = WallpaperItem.from_api(raw)
            if item:
                item.local_path = self.downloaded_files.get(item.wallpaper_id)
                items.append(item)

        last_page = (meta or {}).get("last_page", 1) if meta else 1
        has_more = bool(items) and page < last_page
        if reset and not items:
            self.infoMessage.emit("Ничего не найдено")
        self._search_done.emit(reset, items, has_more)

    def _load_downloaded_items(self):
        items = []
        for w_id, local_path in sorted(self.downloaded_files.items()):
            items.append(
                WallpaperItem(
                    wallpaper_id=w_id,
                    thumb_url=Path(local_path).as_uri(),
                    full_url=WallhavenAPI.build_wallpaper_url(w_id),
                    local_path=local_path,
                )
            )
        self._search_done.emit(True, items, False)

    @Slot(bool, object, bool)
    def _on_search_done(self, reset, items, has_more):
        if reset:
            self._model.set_items(items)
        else:
            self._model.append_items(items)
        self._has_more = has_more
        self._loading = False
        self.hasMoreChanged.emit()
        self.searchFinished.emit()

    @Slot(str, str, str)
    def saveTo(self, url, wallpaper_id, destination):
        """Скачивает полное изображение и сохраняет его. Сигнал saved(path, error)."""

        def worker():
            try:
                if destination and destination.strip():
                    local_path = self._normalize_path(destination)
                else:
                    # Имя файла берём с сайта (basename URL), например
                    # wallhaven-xxxxxxxx.jpg — так же, как на Linux.
                    basename = url.rsplit("/", 1)[-1]
                    if not basename or "." not in basename:
                        ext = url.rsplit(".", 1)[-1].lower() if "." in url else "jpg"
                        if ext not in ("jpg", "jpeg", "png"):
                            ext = "jpg"
                        basename = f"{wallpaper_id}.{ext}"

                    download_path = self._normalize_path(
                        self._settings.get("download_path", "")
                    )
                    if not download_path:
                        # Папка не указана в настройках — используем папку
                        # «Wallhaven» внутри стандартных «Загрузок». Запрашивать
                        # имя файла не нужно (как на Linux с настроенным путём).
                        download_path = self._default_download_dir()
                    # Уважаем выбор пользователя: даже если указанной папки
                    # ещё нет — создаём её, а не подменяем дефолтом.
                    os.makedirs(download_path, exist_ok=True)
                    local_path = os.path.join(download_path, basename)

                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(resp.content)

                self._write_sidecar(local_path, wallpaper_id)
                self.scan_downloaded()
                self.saved.emit(local_path, "")
            except Exception as e:
                self.saved.emit("", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _default_download_dir(self):
        """Возвращает папку для сохранения по умолчанию (…/Wallhaven)."""
        try:
            candidates = []
            env = os.environ.get("XDG_DOWNLOAD_DIR")
            if env:
                candidates.append(Path(env))
            # Стандартные папки загрузок/документов (Windows, Linux, macOS)
            candidates.append(Path.home() / "Downloads")
            candidates.append(Path.home() / "Загрузки")
            candidates.append(Path.home() / "Documents")
            candidates.append(Path.home() / "Документы")
            for c in candidates:
                if c.is_dir():
                    return str(c / "Wallhaven")
            return str(Path.home() / "Wallhaven")
        except Exception:
            return str(Path.home() / "Wallhaven")

    def _write_sidecar(self, image_path, wallpaper_id):
        """Записывает sidecar-метаданные (в кэш-директорию)."""
        try:
            import json

            from wallhaven_viewer.core.cache import get_sidecar_path_for_image

            info = WallhavenAPI.get_wallpaper_info(wallpaper_id, timeout=5)
            if not info:
                return
            sidecar = get_sidecar_path_for_image(image_path)
            if not sidecar:
                return
            tags = [
                t.get("name") if isinstance(t, dict) else str(t)
                for t in (info.get("tags") or [])
            ]
            file_size = info.get("file_size") or 0
            try:
                size_str = f"{float(file_size) / (1024 * 1024):.2f} MB"
            except Exception:
                size_str = str(file_size)
            meta = {
                "size": size_str,
                "uploader": info.get("uploaded_by") or info.get("uploader") or "",
                "views": info.get("views"),
                "favorites": info.get("favorites") or info.get("favourites"),
                "resolution": info.get("resolution"),
            }
            with open(sidecar, "w", encoding="utf-8") as sf:
                json.dump({"meta": meta, "tags": tags}, sf, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @Slot(str)
    def setWallpaper(self, local_path):
        """Устанавливает локальный файл в качестве обоев рабочего стола."""
        if not local_path or not os.path.exists(local_path):
            self.wallpaperSet.emit("Нет локального файла — сначала сохраните обои")
            return
        try:
            if set_desktop_wallpaper(local_path):
                self.wallpaperSet.emit("Обои установлены")
            else:
                self.wallpaperSet.emit(
                    "Не удалось установить обои: нет портала или поддерживаемого окружения"
                )
        except Exception as e:
            self.wallpaperSet.emit(f"Ошибка установки обоев: {e}")

    @Slot(str)
    def openInBrowser(self, wallpaper_id):
        """Открывает страницу обоев в системном браузере."""
        from PySide6.QtGui import QDesktopServices

        try:
            QDesktopServices.openUrl(f"https://wallhaven.cc/w/{wallpaper_id}")
        except Exception:
            pass