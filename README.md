# 🖼️ Wallhaven Desktop Viewer
<div align="center">
<img width="256" height="256" alt="cc wallhaven Viewer" src="https://github.com/user-attachments/assets/f0a354e0-a335-4ce4-95b1-7f5cf115c489" />
</div>

**Современный и производительный просмотрщик обоев для рабочего стола на Python, GTK4 и Qt6.**

Wallhaven Desktop Viewer — это лёгкое и красивое приложение, позволяющее искать, просматривать и скачивать высококачественные обои с [wallhaven.cc](https://wallhaven.cc) напрямую, без необходимости открывать браузер.

Интерфейс построен по паттерну **Core + Pluggable Frontends**: общее ядро (`core/`) не зависит от тулкита, а два сменных интерфейса (`ui_gtk/` и `ui_qt/`) выбираются автоматически:

- **GTK4 + Libadwaita** — нативно для GNOME и большинства Linux-окружений;
- **Qt6 / PySide6 (QML)** — нативно для Windows и KDE Plasma.

---

## ✨ Особенности

- 🔍 Поиск обоев через Wallhaven API
- 🗂 Фильтрация по категориям, соотношению сторон и разрешению
- 📥 Скачивание обоев локально с автоматическим именем файла (как на сайте: `wallhaven-<id>.jpg`)
- ✅ Автоматическая подсветка скачанных обоев и вкладка «Только скачанные»
- 🏷 Просмотр тегов обоев и поиск по тегу одним кликом (в окне предпросмотра)
- 🎨 Установка обоев через xdg-desktop-portal / GSettings / D-Bus (кросс-платформенно)
- 🎯 Единый стиль интерфейса (кнопки, переключатели, выпадающие списки) на всех экранах
- ✅ Корректная работа в Flatpak и Wayland
- 🖥 Оба интерфейса: Libadwaita (GNOME) и Qt Quick (Windows/KDE)

---

## 💻 Выбор интерфейса

При запуске приложение само определяет окружение: на Linux используется GTK, на Windows и в прочих ОС — Qt. Принудительно выбрать интерфейс можно флагом:

```bash
# GNOME и прочие Linux — GTK (Libadwaita)
python3 -m wallhaven_viewer

# Windows и KDE Plasma — Qt (QML)
python3 -m wallhaven_viewer

# Принудительный выбор
python3 -m wallhaven_viewer --ui gtk
python3 -m wallhaven_viewer --ui qt
```

---

## 💻 Установка

### Python (рекомендуемые требования)

- **Python 3.8 или выше**
- **GTK4** и **PyGObject** — для Linux (GNOME/другие):
  ```bash
  # Ubuntu/Debian
  sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 python3-requests
  pip install requests
  ```
- **Qt6 / PySide6** — для Windows и KDE Plasma:
  ```bash
  pip install PySide6 requests dbus-python
  ```

#### Запуск

```bash
python3 main.py
# или
python3 -m wallhaven_viewer
```

### Flatpak

Готовый пакет из GitHub Releases:

```bash
flatpak install --user cc.wallhaven.Viewer.flatpak
```

### Windows (сборка бинарника)

Qt-интерфейс не требует GTK/Libadwaita, поэтому для Windows достаточно PySide6 и общего ядра. Сборка через PyInstaller:

```bash
pip install PySide6 requests dbus-python pyinstaller
pyinstaller --noconsole --onefile --name wallhaven-viewer ^
    --add-data "src/wallhaven_viewer/ui_qt/qml;ui_qt/qml" ^
    src/wallhaven_viewer/__main__.py
```

> Каталог `ui_qt/qml` (включая подпапку `icons/` с SVG-иконками) добавляется в сборку целиком, поэтому иконки доступны и в скомпилированном приложении.

---

## 🎨 Иконки интерфейса (кросс-платформенно)

Иконки кнопок и пунктов меню подбираются под платформу:

- **Linux** — нативные иконки системной темы: GTK берёт свои родные значки, а Qt использует тему рабочего окружения (Breeze/Adwaita и т.п., подключается через `breeze-icons.rcc` или системную тему).
- **Windows** и прочие ОС — иконки загружаются из встроенных SVG-файлов в `src/wallhaven_viewer/ui_qt/qml/icons/` (например, `refresh.svg`, `download.svg`, `menu.svg`, `search.svg`, `clear.svg`, `settings.svg`, `about.svg`). Это гарантирует корректное отображение даже при отсутствии системной темы значков.

Выбор режима (тема или файлы) определяется флагом `useFileIcons` в `ui_qt/app.py` и не требует ручной настройки.

---

## ⚙️ Настройка и использование

### 🔍 Панель поиска и фильтров

- **Поле ввода:** используйте для ввода ключевых слов (например, `cyberpunk`, `nature`).
- **Категории и Чистота (Purity):** группы переключателей `General`/`Anime`/`People` и `SFW`/`Sketchy`/`NSFW`. Активный сегмент подсвечивается акцентным цветом.
- **Сортировка (Sort):** выберите режим: `Toplist`, `Date Added`, `Relevance` и др.
- **Разрешение / Соотношение сторон:** выпадающие списки в стиле единой темы.

### 🏷 Теги обоев

В окне полноразмерного предпросмотра (Qt и GTK) под изображением отображаются теги обоев. Клик по тегу запускает поиск по этому тегу — так же, как в веб-интерфейсе wallhaven.cc.

### 🔑 API Ключ (для контента 18+)

Если вы хотите видеть контент с пометкой **Sketchy** или **NSFW**, вам потребуется API-ключ от Wallhaven.

1. Зарегистрируйтесь на [wallhaven.cc].
2. Перейдите в настройки аккаунта и скопируйте ваш API-ключ.
3. В приложении откройте меню (иконка «☰») → **Настройки** (шестерёнка).
4. Вставьте ключ в поле **API Ключ**.

### 📁 Папка для сохранения

В окне настроек можно указать **Папку для сохранения**. Поведение зависит от интерфейса:

- **Qt (Windows/KDE):** если папка не указана, обои сохраняются автоматически в `Wallhaven` внутри стандартной папки «Загрузки» (`~/Downloads/Wallhaven` на Linux, `XDG_DOWNLOAD_DIR` если задан, `Downloads\Wallhaven` на Windows) — запрос имени файла не показывается. Если папка указана — используется она (создаётся при необходимости). Имя файла берётся с сайта (`wallhaven-<id>.jpg`).
- **GTK (GNOME):** при пустой папке предлагается выбрать её при скачивании.

Пути нормализуются (учитываются особенности Windows, например ведущий слэш перед буквой диска `/C:/...`), поэтому скачивание корректно работает на обеих ОС.

### 📥 Вкладка «Скачанные обои»

Кнопка со значком загрузки в шапке переключает режим просмотра на уже скачанные обои. Скачанные карточки помечаются зелёной галочкой, а вкладка заполняется файлами из выбранной (или дефолтной) папки сохранения.

---

## 🛠️ Архитектура и технологии

**Python 3** — основной язык
**GTK 4 / Libadwaita** — интерфейс для GNOME (через PyGObject)
**Qt 6 / QML** — интерфейс для Windows и KDE Plasma (через PySide6)
**requests** — HTTP-запросы к Wallhaven API
**threading** — фоновая загрузка миниатюр, изображений и тегов
**caching** — локальное кэширование для производительности

```
src/wallhaven_viewer/
├── core/        # Общая логика (0% кода UI): API, настройки, кэш, модели, установка обоев
├── ui_gtk/      # GTK4 + Libadwaita интерфейс (GNOME, большинство Linux)
├── ui_qt/       # Qt6 / PySide6 + QML интерфейс (Windows, KDE Plasma)
│   ├── qml/
│   │   ├── AppButton.qml   # Единый компонент кнопки (стиль полей/списков)
│   │   ├── Chip.qml        # Сегмент фильтров (категории/рейтинг)
│   │   ├── Segmented.qml  # Контейнер сегментированных групп
│   │   ├── ThemeComboBox.qml # Выпадающие списки (единый стиль)
│   │   ├── WallpaperCard.qml # Карточка обоев (галочка «скачано»)
│   │   ├── FullImageView.qml # Окно предпросмотра (теги, скачивание)
│   │   ├── Main.qml        # Главное окно
│   │   ├── SettingsDialog.qml / AboutDialog.qml
│   │   └── icons/          # SVG-иконки для Windows/не-Linux
│   ├── resources/breeze-icons.rcc # Резервная тема Breeze для Linux/Qt
│   ├── app.py     # Точка входа Qt, выбор иконок (useFileIcons)
│   └── backend.py  # Логика Qt: поиск, скачивание, теги, сканирование папки
├── __main__.py  # Точка входа с автоопределением UI (--ui gtk|qt)
└── main.py      # Обёртка для обратной совместимости
```

Единый визуальный язык интерфейса задаётся компонентами `AppButton`, `Chip`, `Segmented` и `ThemeComboBox`: радиус 4, фон как у поля ввода, тонкая рамка, акцентный цвет при выборе/фокусе.

---

# 📄 Лицензия

Данный проект распространяется под лицензией MIT.
Подробности — в файле LICENSE.

---

# 🙌 Благодарности

- Спасибо [wallhaven.cc] за мощное и удобное API!
- GNOME / GTK / Libadwaita
- KDE / Qt / Breeze
- xdg-desktop-portal

🚀 Улучшайте ваш рабочий стол — одним кликом.
