"""
Модели данных приложения (независимы от UI-тулкита).
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Tag:
    """Тег обоев (из API Wallhaven)."""

    name: str
    slug: str = ""
    namespace: Optional[str] = None

    @classmethod
    def from_api(cls, raw) -> "Tag":
        if isinstance(raw, dict):
            return cls(
                name=str(raw.get("name", "")),
                slug=str(raw.get("slug", "")),
                namespace=raw.get("namespace"),
            )
        return cls(name=str(raw))


@dataclass
class WallpaperItem:
    """Одна запись с обоями (превью + полноразмерный URL + метаданные)."""

    wallpaper_id: str
    thumb_url: str
    full_url: str
    path: str = ""
    extension: str = ""
    resolution: str = ""
    width: int = 0
    height: int = 0
    colors: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    local_path: Optional[str] = None

    @classmethod
    def from_api(cls, raw) -> Optional["WallpaperItem"]:
        try:
            w_id = raw.get("id")
            if not w_id:
                return None
            thumbs = raw.get("thumbs", {}) or {}
            thumb = thumbs.get("large") or thumbs.get("original") or ""
            full = raw.get("path") or ""
            if not thumb or not full:
                return None
            return cls(
                wallpaper_id=w_id,
                thumb_url=thumb,
                full_url=full,
                path=raw.get("url", ""),
                extension=raw.get("file_type", "").replace("image/", ""),
                resolution=raw.get("resolution", ""),
                width=int(raw.get("dimension_x") or 0),
                height=int(raw.get("dimension_y") or 0),
                colors=raw.get("colors", []) or [],
                tags=[Tag.from_api(t) for t in (raw.get("tags") or [])],
            )
        except Exception:
            return None

    @property
    def is_downloaded(self) -> bool:
        return bool(self.local_path) and os.path.exists(self.local_path)


@dataclass
class SearchMeta:
    """Метаданные страницы поиска Wallhaven API."""

    current_page: int = 1
    last_page: int = 1
    total: int = 0
    seed: str = ""

    @classmethod
    def from_api(cls, raw) -> "SearchMeta":
        if not isinstance(raw, dict):
            return cls()
        return cls(
            current_page=int(raw.get("current_page") or 1),
            last_page=int(raw.get("last_page") or 1),
            total=int(raw.get("total") or 0),
            seed=str(raw.get("seed") or ""),
        )


@dataclass
class WallpaperInfo:
    """Полная информация об обоях (для окна полноразмерного просмотра)."""

    wallpaper_id: str
    resolution: str = ""
    file_size: int = 0
    views: int = 0
    favorites: int = 0
    uploader: str = ""
    tags: list = field(default_factory=list)

    @classmethod
    def from_api(cls, raw) -> Optional["WallpaperInfo"]:
        if not isinstance(raw, dict):
            return None
        try:
            uploader = (
                raw.get("uploaded_by")
                or raw.get("uploader")
                or (raw.get("user") or {}).get("username")
                or ""
            )
            return cls(
                wallpaper_id=str(raw.get("id", "")),
                resolution=str(raw.get("resolution", "")),
                file_size=int(raw.get("file_size") or 0),
                views=int(raw.get("views") or 0),
                favorites=int(raw.get("favorites") or raw.get("favourites") or 0),
                uploader=str(uploader),
                tags=[Tag.from_api(t) for t in (raw.get("tags") or [])],
            )
        except Exception:
            return None