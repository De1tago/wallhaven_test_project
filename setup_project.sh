#!/usr/bin/env bash
# setup_project.sh — автоматизирует перекладку файлов и правки после перехода
# на структуру Flatpak/libAdwaita.

set -euo pipefail

# ────────────────────────────── helpers ───────────────────────────────────────
move_if_exists() {
  local src="$1" dst="$2"
  if [[ -e "$src" ]]; then
    echo "▶ mv $src → $dst"
    mv "$src" "$dst"
  fi
}
# ─────────────────────────────── layout ───────────────────────────────────────
echo "📁 Готовим каталоги…"
mkdir -p src/wallhaven_viewer \
         data/{ui,css,icons/hicolor/256x256/apps,applications} \
         flatpak \
         scripts

# ─────────────────────────── move python files ───────────────────────────────
echo "🐍 Перемещаем Python-файлы…"
for f in api app config full_image_window image_loader main main_window settings_window utils; do
  move_if_exists "$f.py" "src/wallhaven_viewer/"
done
touch src/wallhaven_viewer/__init__.py

# ───────────────────────────── move assets ────────────────────────────────────
echo "📦 Перемещаем ресурсы…"
move_if_exists mainwindow.ui               data/ui/
move_if_exists fullimage.ui                data/ui/
move_if_exists style.css                   data/css/
move_if_exists app-icon.png                data/icons/hicolor/256x256/apps/cc.wallhaven.Viewer.png
move_if_exists cc.wallhaven.Viewer.desktop data/applications/
move_if_exists cc.wallhaven.Viewer.yml     flatpak/
move_if_exists wallhaven-viewer-wrapper.sh scripts/wallhaven-viewer

# ────────────────────────────── fix imports ───────────────────────────────────
echo "🔧 Обновляем импорты…"
find src/wallhaven_viewer -type f -name '*.py' | while read -r file; do
  sed -i -E \
    -e 's/^from (utils|api|config|image_loader|main_window|settings_window|full_image_window) /from wallhaven_viewer.\1 /' \
    -e 's/^from app import /from wallhaven_viewer.app import /' \
    "$file"
done

# ───────────────────────── create wrapper ─────────────────────────────────────
echo "📝 Создаём wrapper-скрипт…"
cat > scripts/wallhaven-viewer <<'EOS'
#!/usr/bin/env bash
exec python3 -m wallhaven_viewer "$@"
EOS
chmod +x scripts/wallhaven-viewer

# ─────────────────────── update .desktop & manifest ───────────────────────────
echo "🖼  Правим .desktop…"
if [[ -f data/applications/cc.wallhaven.Viewer.desktop ]]; then
  sed -i 's|^Exec=.*|Exec=wallhaven-viewer|' data/applications/cc.wallhaven.Viewer.desktop
  sed -i 's|^Icon=.*|Icon=cc.wallhaven.Viewer|' data/applications/cc.wallhaven.Viewer.desktop
fi

echo "🛠  Правим Flatpak-манифест…"
if [[ -f flatpak/cc.wallhaven.Viewer.yml ]]; then
  sed -i 's/^command: .*/command: python3 -m wallhaven_viewer/' flatpak/cc.wallhaven.Viewer.yml
fi

# ───────────────────── ensure PyGObject in requirements ───────────────────────
echo "📜 Обновляем requirements.txt…"
grep -qi '^PyGObject' requirements.txt || echo 'PyGObject' >> requirements.txt

echo -e "\n✅ Всё готово!\nЗапуск в dev-режиме:\n  PYTHONPATH=src python -m wallhaven_viewer\n"