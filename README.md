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
- 📥 Скачивание обоев локально
- 🎨 Установка обоев через xdg-desktop-portal / GSettings / D-Bus (кросс-платформенно)
- ✅ Корректная работа в Flatpak и Wayland
- 🖥 Оба интерфейса: Libadwaita (GNOME) и Qt Quick (Windows/KDE)

---

## 💻 Выбор интерфейса

При запуске приложение само определяет окружение:

```bash
# GNOME и прочие Linux — GTK (Libadwaita)
python3 -m wallhaven_viewer

# Windows и KDE Plasma — Qt (QML)
python3 -m wallhaven_viewer

# Принудительный выбор
python3 -m wallhaven_viewer --ui gtk
python3 -m wallhaven_viewer --ui qt
```

## 💻 Установка

### Python
### Рекомендуемые требованияя
- **Python 3.8 или выше**
- **GTK4** и **PyGObject**  
  На Linux (Ubuntu/Debian) установите через:

  ```bash
  sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0
  ```

  ```bash
  pip install gi requests
  ````

*(**Примечание:** Для работы с PyGObject в некоторых окружениях может потребоваться `pip install pygobject`)*

#### Qt-интерфейс (Windows / KDE Plasma)

```bash
pip install PySide6 requests dbus-python
```

#### 2\. Запуск приложения

Просто запустите основной скрипт:

```bash
python3 main.py
# или
python3 -m wallhaven_viewer
```
### Flatpak

Скачайте готовый пакет из **GitHub Releases**:

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


### Native

#### Зависимости

**Ubuntu 24.04+**

```bash
sudo apt install python3 python3-gi python3-dbus gir1.2-gtk-4.0 gir1.2-adw-1 python3-requests

```
**Arch Linux**
```bash
sudo pacman -S python python-gobject gtk4 libadwaita python-dbus python-requests
```
**Запуск**
```bash
git clone https://github.com/<your-username>/wallhaven-viewer.git
cd wallhaven-viewer
python main.py
```
-----

## ⚙️ Настройка и использование

### 🔍 Панель поиска и фильтров

- **Поле ввода:** Используйте для ввода ключевых слов (например, `cyberpunk`, `nature`).
- **Категории и Чистота (Purity):** Используйте кнопки-переключатели (`General`, `Anime`, `People` и т.д.) для настройки типа контента.
- **Сортировка (Sort):** Выберите режим сортировки: `Toplist` (Лучшее за период), `Date Added` (Недавно добавленное) или `Relevance` (Актуальность).

### 🔑 API Ключ (Для контента 18+)

Если вы хотите видеть контент с пометкой **Sketchy** или **NSFW**, вам потребуется API-ключ от Wallhaven.

1. Зарегистрируйтесь на [wallhaven.cc].
2. Перейдите в настройки аккаунта и скопируйте ваш API-ключ.
3. В приложении нажмите на кнопку **Настройки** (шестеренка) в заголовке.
4. Вставьте ключ в поле **API Ключ**.

### 📁 Папка для сохранения

В окне настроек вы можете указать **Папку для сохранения**. Если поле оставить пустым, программа будет спрашивать, куда сохранить файл, при каждой загрузке.

-----

# ⚙️ Настройка

## 🔑 API-ключ (необязательно, но рекомендуется)

Для доступа к NSFW и Sketchy контенту:

1. Зарегистрируйтесь на wallhaven.cc.
2. Перейдите в **Настройки профиля → API Key**.
3. Скопируйте ключ и вставьте его в поле **API Ключ** в настройках приложения (через иконку шестерёнки).


---

# 🖼️ Скриншоты

<div align="center">
<img width="1250" height="900" alt="изображение" src="https://github.com/user-attachments/assets/b8b01b03-a894-490b-a720-4947a3efcc21" />


<img width="450" height="421" alt="изображение" src="https://github.com/user-attachments/assets/c6281763-fd80-4c3e-8d04-9014218661a2" />

</div>

---

# 🛠️ Архитектура и технологии

**Python 3** — основной язык
**GTK 4 / Libadwaita** — интерфейс для GNOME (через PyGObject)
**Qt 6 / QML** — интерфейс для Windows и KDE Plasma (через PySide6)
**requests** — HTTP-запросы к Wallhaven API
**threading** — фоновая загрузка миниатюр и изображений
**caching** — локальное кэширование для производительности

```
src/wallhaven_viewer/
├── core/        # Общая логика (0% кода UI): API, настройки, кэш, модели, установка обоев
├── ui_gtk/      # GTK4 + Libadwaita интерфейс (GNOME, большинство Linux)
├── ui_qt/       # Qt6 / PySide6 + QML интерфейс (Windows, KDE Plasma)
├── __main__.py  # Точка входа с автоопределением UI (--ui gtk|qt)
└── main.py      # Обёртка для обратной совместимости
```

---

# 📄 Лицензия

Данный проект распространяется под лицензией MIT.
Подробности — в файле LICENSE.

---

# 🙌 Благодарности

- Спасибо [wallhaven.cc](https://wallhaven.cc)
 за мощное и удобное API!
-  GNOME / GTK / Libadwaita

- xdg-desktop-portal

---

🚀 Улучшайте ваш рабочий стол — одним кликом.
