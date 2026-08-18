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

    def run(self):
        # Используем Fusion: кроссплатформенный стиль, который уважает
        # заданную палитру, поэтому интерфейс выглядит как Breeze.
        os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Fusion")

        app = QGuiApplication(self._argv)
        app.setApplicationName("Wallhaven Viewer")
        app.setOrganizationName("Wallhaven")
        app.setApplicationDisplayName("Wallhaven Viewer")

        engine = QQmlApplicationEngine()

        backend = Backend()

        engine.rootContext().setContextProperty("backend", backend)

        from PySide6.QtGui import QColor

        # Применяем палитру Breeze и общие цвета темы. Вызывается при
        # старте и при каждой смене системной светлой/тёмной темы.
        ctx = engine.rootContext()

        def apply_theme():
            scheme, is_dark = _apply_breeze_theme(app, backend.isDark)
            ctx.setContextProperty("cIsDark", is_dark)
            ctx.setContextProperty("cBg", QColor(scheme["window"]))
            ctx.setContextProperty("cPanel", QColor(scheme["window"]))
            ctx.setContextProperty("cText", QColor(scheme["text"]))
            ctx.setContextProperty("cField", QColor(scheme["base"]))
            ctx.setContextProperty("cBorder", QColor(scheme["border"]))
            ctx.setContextProperty("cMuted", QColor(scheme["placeholder"]))
            ctx.setContextProperty("cAccent", QColor(scheme["accent"]))

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