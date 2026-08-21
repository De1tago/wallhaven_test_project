"""
Qt6 (PySide6 / QML) интерфейс Wallhaven Viewer.
"""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from wallhaven_viewer.ui_qt.backend import Backend


# Реальные цвета темы Breeze (KDE). Используются чтобы Qt-интерфейс
# выглядел как нативный Breeze даже вне окружения Plasma.
BREEZE_LIGHT = {
    "window": "#eff0f1",
    "base": "#fcfcfc",
    "text": "#31363b",
    "border": "#c4c8cb",
    "placeholder": "#626d73",
    "accent": "#3daee9",
}
BREEZE_DARK = {
    "window": "#31363b",
    "base": "#1d2023",
    "text": "#eff0f1",
    "border": "#54585b",
    "placeholder": "#8a9095",
    "accent": "#3daee9",
}


def _apply_breeze_theme(app, dark):
    """
    Применяем стиль Fusion (кроссплатформенный и уважает QPalette) и
    подставляем настоящую палитру Breeze. Все цвета интерфейса в QML
    берутся из общих свойств контекста (cBg, cText, …), поэтому внешний
    вид автоматически соответствует теме Breeze (светлой или тёмной).
    """
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPalette

    scheme = BREEZE_DARK if dark else BREEZE_LIGHT

    app.styleHints().setColorScheme(
        Qt.ColorScheme.Dark if dark else Qt.ColorScheme.Light
    )

    pal = QPalette()
    window = QColor(scheme["window"])
    base = QColor(scheme["base"])
    text = QColor(scheme["text"])
    accent = QColor(scheme["accent"])
    border = QColor(scheme["border"])

    pal.setColor(QPalette.Window, window)
    pal.setColor(QPalette.WindowText, text)
    pal.setColor(QPalette.Base, base)
    pal.setColor(QPalette.AlternateBase, window)
    pal.setColor(QPalette.Text, text)
    pal.setColor(QPalette.Button, window)
    pal.setColor(QPalette.ButtonText, text)
    pal.setColor(QPalette.Highlight, accent)
    pal.setColor(QPalette.HighlightedText, QColor("#fcfcfc"))
    pal.setColor(QPalette.ToolTipBase, QColor("#31363b") if not dark else window)
    pal.setColor(QPalette.ToolTipText, QColor("#eff0f1") if not dark else text)
    pal.setColor(QPalette.PlaceholderText, QColor(scheme["placeholder"]))
    pal.setColor(QPalette.Link, accent)
    mid = border
    pal.setColor(QPalette.Light, window.lighter(110))
    pal.setColor(QPalette.Midlight, window.lighter(105))
    pal.setColor(QPalette.Mid, mid)
    pal.setColor(QPalette.Dark, window.darker(115))
    pal.setColor(QPalette.Shadow, QColor("#000000"))
    pal.setColor(QPalette.BrightText, QColor("#ff5252"))
    pal.setColor(QPalette.Disabled, QPalette.WindowText, text.darker(160))
    pal.setColor(QPalette.Disabled, QPalette.Text, text.darker(160))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, text.darker(160))

    app.setPalette(pal)

    return scheme, dark


class WallhavenQtApp:
    """Оболочка Qt-приложения: создаёт QGuiApplication, грузит Main.qml."""

    def __init__(self, argv=None):
        self._argv = list(argv) if argv is not None else list(sys.argv)

    def _load_breeze_icons(self):
        """Регистрирует иконочную тему Breeze для Qt.

        Иконки берутся из bundled-ресурса ``breeze-icons.rcc`` (рядом с
        модулем), либо из системы (``/usr/share/icons/breeze``). Ресурс
        монтируется с префиксом ``/breeze``, чтобы Qt находил тему
        ``breeze`` по стандартному пути ``<search>/breeze/index.theme``.
        Если тема Breeze недоступна — Qt использует системную тему.
        """
        from PySide6.QtCore import QResource, QDir, QStandardPaths
        from PySide6.QtGui import QIcon

        here = Path(__file__).resolve().parent
        candidates = [
            here / "resources" / "breeze-icons.rcc",
            Path("/usr/share/icons/breeze/breeze-icons.rcc"),
            Path("/app/share/icons/breeze/breeze-icons.rcc"),  # Flatpak
        ]

        rcc_registered = False
        for candidate in candidates:
            if candidate.exists() and QResource.registerResource(
                str(candidate), "/breeze"
            ):
                rcc_registered = True
                break

        # Системные каталоги иконок (GenericData/icons + ~/.local/share/icons)
        data_dirs = QStandardPaths.standardLocations(
            QStandardPaths.StandardLocation.GenericDataLocation
        )
        system_icon_dirs = [os.path.join(d, "icons") for d in data_dirs]
        system_icon_dirs += [
            str(Path.home() / ".local" / "share" / "icons"),
            "/usr/share/icons",
        ]

        # ":/" позволяет резолвить тему из зарегистрированного .rcc,
        # системные пути — подхватить нативную тему Breeze, если она есть.
        QIcon.setThemeSearchPaths([":/"] + system_icon_dirs)

        breeze_in_system = any(
            QDir(os.path.join(d, "breeze")).exists() for d in system_icon_dirs
        )

        if rcc_registered or breeze_in_system:
            QIcon.setThemeName("breeze")

    def run(self):
        # Стиль QtQuick.Controls.
        # По умолчанию — Fusion (кроссплатформенный, уважает палитру),
        # поэтому интерфейс выглядит как Breeze. Чтобы подхватить нативную
        # системную тему (qt6ct/Kvantum, KvBreeze/KvLibadwaita и т.п.),
        # задайте переменную окружения, например:
        #   QT_QUICK_CONTROLS_STYLE=org.kde.desktop   (или Material/Universal)
        #   WALLHAVEN_QT_STYLE=Fusion
        # Если стиль задан извне — не перезаписываем его.
        forced_style = os.environ.get("WALLHAVEN_QT_STYLE") \
            or os.environ.get("QT_QUICK_CONTROLS_STYLE")
        if forced_style:
            os.environ["QT_QUICK_CONTROLS_STYLE"] = forced_style
        else:
            os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Fusion")

        # Если пользователь хочет использовать системную палитру
        # (qt6ct/Kvantum), не навязываем свою Breeze-палитру — берём
        # цвета прямо из палитры приложения.
        use_system_theme = os.environ.get("WALLHAVEN_SYSTEM_THEME") == "1"

        app = QGuiApplication(self._argv)
        app.setApplicationName("Wallhaven Viewer")
        app.setOrganizationName("Wallhaven")
        app.setApplicationDisplayName("Wallhaven Viewer")

        # Подключаем нативные иконки темы Breeze. Сам иконочный пакет
        # (breeze-icons.rcc) поставляется вместе с приложением, поэтому
        # иконки отображаются везде — даже под GNOME/в Flatpak, где
        # системной темы Breeze нет. При её отсутствии используется
        # системная тема (например, Adwaita) как запасной вариант.
        self._load_breeze_icons()

        engine = QQmlApplicationEngine()

        backend = Backend()

        engine.rootContext().setContextProperty("backend", backend)

        # На Linux берём нативные иконки темы (Breeze/Adwaita и т.п.),
        # на Windows и прочих ОС — подгружаем из файлов (папка qml/icons),
        # т.к. там нет системной темы значков.
        engine.rootContext().setContextProperty(
            "useFileIcons", not sys.platform.startswith("linux")
        )

        from PySide6.QtGui import QColor

        # Применяем палитру и общие цвета темы. Вызывается при старте
        # и при каждой смене системной светлой/тёмной темы.
        ctx = engine.rootContext()

        def apply_theme():
            if use_system_theme:
                # Берём цвета из актуальной палитры приложения
                # (её задаёт системный движок тем qt6ct/Kvantum).
                pal = app.palette()
                is_dark = (pal.color(pal.Window).lightness()
                           < pal.color(pal.WindowText).lightness())
                ctx.setContextProperty("cIsDark", is_dark)
                ctx.setContextProperty("cBg", pal.color(pal.Window))
                ctx.setContextProperty("cPanel", pal.color(pal.Window))
                ctx.setContextProperty("cText", pal.color(pal.WindowText))
                ctx.setContextProperty("cField", pal.color(pal.Base))
                ctx.setContextProperty("cBorder", pal.color(pal.Mid))
                ctx.setContextProperty("cMuted", pal.color(pal.PlaceholderText))
                ctx.setContextProperty("cAccent", pal.color(pal.Highlight))
                # Тонкая рамка элементов (чуть светлее фона панели)
                ctx.setContextProperty("cBorderSoft", pal.color(pal.Mid).lighter(115)
                                       if is_dark else pal.color(pal.Mid))
                # Фон области контента — чуть темнее панелей (глубина)
                ctx.setContextProperty("cContent",
                                       pal.color(pal.Window).darker(112)
                                       if is_dark else
                                       pal.color(pal.Window).lighter(103))
            else:
                scheme, is_dark = _apply_breeze_theme(app, backend.isDark)
                ctx.setContextProperty("cIsDark", is_dark)
                ctx.setContextProperty("cBg", QColor(scheme["window"]))
                ctx.setContextProperty("cPanel", QColor(scheme["window"]))
                ctx.setContextProperty("cText", QColor(scheme["text"]))
                ctx.setContextProperty("cField", QColor(scheme["base"]))
                ctx.setContextProperty("cBorder", QColor(scheme["border"]))
                ctx.setContextProperty("cMuted", QColor(scheme["placeholder"]))
                ctx.setContextProperty("cAccent", QColor(scheme["accent"]))
                # Тонкая рамка элементов в духе Breeze
                ctx.setContextProperty("cBorderSoft",
                                       QColor("#76797c") if is_dark
                                       else QColor("#c4c8cb"))
                # Область контента чуть темнее панелей
                ctx.setContextProperty("cContent",
                                       QColor("#232629") if is_dark
                                       else QColor("#e7eaec"))

        apply_theme()

        # Адаптивное переключение: реагируем на смену темы в системе.
        backend.isDarkChanged.connect(apply_theme)

        qml_dir = Path(__file__).resolve().parent / "qml"
        main_qml = qml_dir / "Main.qml"
        if not main_qml.exists():
            print(f"[Error] Файл интерфейса не найден: {main_qml}")
            return 1

        engine.load(QUrl.fromLocalFile(str(main_qml)))

        if not engine.rootObjects():
            print("[Error] Не удалось загрузить Main.qml")
            return 1

        # Небольшая задержка перед первым поиском — окно уже отрисовано
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, lambda: backend.search(backend.query))

        return app.exec()