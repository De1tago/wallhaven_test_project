import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root

    width: 1200
    height: 850
    visible: true
    title: "Wallhaven Viewer"

    background: Rectangle {
        color: cContent
    }

    // Цвета темы Breeze приходят из общего контекста (cBg, cText, …)
    property bool isDark: cIsDark
    property color bgColor: cBg
    property color panelColor: cPanel
    property color textColor: cText
    property color borderColor: cBorder
    property color fieldColor: cField
    property color mutedText: cMuted
    property color accent: cAccent

    property bool loading: false
    property string infoText: ""
    property bool infoVisible: false

    function doSearch() {
        searchField.focus = false
        backend.search(searchField.text)
    }

    // Подгружает следующую страницу, если сетка не заполняет окно
    // (например, при небольшом размере окна первая страница помещается
    // целиком и событие atYEnd не срабатывает).
    function maybeLoadMore() {
        if (!backend.hasMore || root.loading)
            return
        if (grid.contentHeight <= grid.height + 4 && grid.count > 0)
            backend.loadMore()
    }

    function openFull(id, url, localPath) {
        var obj = fullViewComponent.createObject(null)
        obj.wallpaperId = id
        obj.fullUrl = url
        obj.localPath = localPath
        obj.visible = true
    }

    function showInfo(message) {
        infoText = message
        infoVisible = true
        infoTimer.restart()
    }

    // ------------------------------------------------------------------
    // Шапка
    // ------------------------------------------------------------------
    header: ColumnLayout {
        spacing: 0

        // Строка 1: навигация (обновить/скачанные) слева, распорка,
        // поиск прижат вправо, за ним — настройки. Классический
        // десктоп-каркас без перекоса веса.
        ToolBar {
            Layout.fillWidth: true
            topPadding: 10
            bottomPadding: 10
            leftPadding: 0
            rightPadding: 0
            background: Rectangle { color: root.bgColor }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 12

                ToolButton {
                    icon.name: "view-refresh-symbolic"
                    icon.color: root.textColor
                    implicitHeight: 34
                    Layout.alignment: Qt.AlignVCenter
                    onClicked: root.doSearch()
                    ToolTip.visible: hovered
                    ToolTip.text: "Обновить"
                    background: Rectangle {
                        radius: 4
                        color: parent.hovered ? Qt.lighter(root.panelColor, 1.12)
                              : "transparent"
                        border.width: 1
                        border.color: cBorderSoft
                    }
                }

                ToolButton {
                    checkable: true
                    checked: backend.downloadedMode
                    icon.name: "folder-download-symbolic"
                    icon.color: root.textColor
                    implicitHeight: 34
                    Layout.alignment: Qt.AlignVCenter
                    onToggled: {
                        backend.downloadedMode = checked
                        root.doSearch()
                    }
                    ToolTip.visible: hovered
                    ToolTip.text: "Только скачанные обои"
                    background: Rectangle {
                        radius: 4
                        color: parent.checked ? Qt.lighter(root.accent, 1.4)
                              : parent.hovered ? Qt.lighter(root.panelColor, 1.12)
                              : "transparent"
                        border.width: 1
                        border.color: parent.checked ? root.accent : cBorderSoft
                    }
                }

                // Распорка прижимает блок навигации влево, а поиск — вправо
                Item { Layout.fillWidth: true }

                TextField {
                    id: searchField
                    Layout.preferredWidth: 380
                    Layout.maximumWidth: 460
                    Layout.alignment: Qt.AlignVCenter
                    leftPadding: 36
                    rightPadding: 32
                    topPadding: 9
                    bottomPadding: 9
                    placeholderText: "Поиск обоев (например, cyberpunk)…"
                    text: backend.query
                    onAccepted: root.doSearch()
                    color: root.textColor
                    placeholderTextColor: root.mutedText
                    background: Rectangle {
                        radius: 4
                        color: root.fieldColor
                        border.width: searchField.activeFocus ? 2 : 1
                        border.color: searchField.activeFocus ? root.accent : cBorderSoft
                    }
                    // Интегрированная кнопка «Найти» внутри поля (magnifier)
                    ToolButton {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: 8
                        focusPolicy: Qt.NoFocus
                        icon.name: "system-search-symbolic"
                        icon.color: root.mutedText
                        onClicked: root.doSearch()
                        ToolTip.visible: hovered
                        ToolTip.text: "Найти"
                        background: Rectangle { color: "transparent" }
                    }
                    // Крестик очистки (аналог setClearButtonEnabled)
                    ToolButton {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.rightMargin: 4
                        focusPolicy: Qt.NoFocus
                        icon.name: "edit-clear-symbolic"
                        icon.color: root.mutedText
                        visible: searchField.text.length > 0
                        onClicked: { searchField.text = ""; searchField.forceActiveFocus() }
                        ToolTip.visible: hovered
                        ToolTip.text: "Очистить"
                        background: Rectangle { color: "transparent" }
                    }
                }

                // Без промежуточной распорки: поиск и меню прижаты
                // к правому краю (классика десктопа).
                ToolButton {
                    id: menuButton
                    icon.name: "application-menu-symbolic"
                    icon.color: root.textColor
                    implicitHeight: 34
                    Layout.alignment: Qt.AlignVCenter
                    onClicked: {
                        var br = menuButton.mapToItem(Overlay.overlay,
                                                      menuButton.width,
                                                      menuButton.height)
                        burgerMenu.x = Math.max(8, br.x - burgerMenu.width)
                        burgerMenu.y = br.y
                        burgerMenu.open()
                    }
                    ToolTip.visible: hovered
                    ToolTip.text: "Меню"
                    background: Rectangle {
                        radius: 4
                        color: parent.hovered ? Qt.lighter(root.panelColor, 1.12)
                              : "transparent"
                        border.width: 1
                        border.color: cBorderSoft
                    }

                    // Плавающее меню (Popup) с небольшим скруглением,
                    // как у кнопок/выпадающих списков. Кастомный фон
                    // у Menu ломает авторазмер в этой сборке Qt, поэтому
                    // используем Popup с собственным содержимым.
                    Popup {
                        id: burgerMenu
                        parent: Overlay.overlay
                        padding: 4
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                        background: Rectangle {
                            color: cPanel
                            radius: 4
                            border.width: 1
                            border.color: cBorderSoft
                        }

                        ColumnLayout {
                            spacing: 4

                            Button {
                                flat: true
                                icon.name: "settings-configure-symbolic"
                                icon.color: cText
                                text: "Настройки"
                                implicitWidth: 190
                                implicitHeight: 34
                                leftPadding: 12
                                rightPadding: 12
                                spacing: 10
                                palette.buttonText: cText
                                background: Rectangle {
                                    radius: 4
                                    color: parent.hovered
                                           ? Qt.lighter(cPanel, 1.12)
                                           : "transparent"
                                    border.width: 1
                                    border.color: cBorderSoft
                                }
                                onClicked: {
                                    burgerMenu.close()
                                    root.openFloating(settingsDialog)
                                }
                            }
                            Button {
                                flat: true
                                icon.name: "help-about-symbolic"
                                icon.color: cText
                                text: "О программе"
                                implicitWidth: 190
                                implicitHeight: 34
                                leftPadding: 12
                                rightPadding: 12
                                spacing: 10
                                palette.buttonText: cText
                                background: Rectangle {
                                    radius: 4
                                    color: parent.hovered
                                           ? Qt.lighter(cPanel, 1.12)
                                           : "transparent"
                                    border.width: 1
                                    border.color: cBorderSoft
                                }
                                onClicked: {
                                    burgerMenu.close()
                                    root.openFloating(aboutDialog)
                                }
                            }
                        }
                    }
                }
            }
        }

        // Строка 2: сегментированные группы (категории и рейтинг) слева,
        // распорка, затем выпадающие списки (сортировка/разрешение/ratio)
        // прижаты вправо. Ровный прямоугольный каркас.
        ToolBar {
            Layout.fillWidth: true
            topPadding: 10
            bottomPadding: 10
            leftPadding: 0
            rightPadding: 0
            background: Rectangle {
                color: root.bgColor
                // Чёткая, но тёмная разделительная линия под панелью
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: cContent
                }
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 16

                // Категории — сегментированная группа
                Segmented {
                    Chip {
                        flat: true
                        text: "General"
                        checked: backend.catGeneral
                        onToggled: { backend.catGeneral = checked; root.doSearch() }
                    }
                    Chip {
                        flat: true
                        text: "Anime"
                        checked: backend.catAnime
                        onToggled: { backend.catAnime = checked; root.doSearch() }
                    }
                    Chip {
                        flat: true
                        text: "People"
                        checked: backend.catPeople
                        onToggled: { backend.catPeople = checked; root.doSearch() }
                    }
                }

                // Рейтинг — сегментированная группа
                Segmented {
                    Chip {
                        flat: true
                        text: "SFW"
                        checked: backend.puritySfw
                        onToggled: { backend.puritySfw = checked; root.doSearch() }
                    }
                    Chip {
                        flat: true
                        text: "Sketchy"
                        checked: backend.puritySketchy
                        onToggled: { backend.puritySketchy = checked; root.doSearch() }
                    }
                    Chip {
                        flat: true
                        text: "NSFW"
                        checked: backend.purityNsfw
                        onToggled: { backend.purityNsfw = checked; root.doSearch() }
                    }
                }

                // Распорка между сегментированными группами слева и
                // выпадающими списками справа — ровный прямоугольный каркас.
                Item { Layout.fillWidth: true }

                ThemeComboBox {
                    id: sortBox
                    model: backend.sortLabels
                    currentIndex: backend.sortIndex
                    onActivated: { backend.sortIndex = currentIndex; root.doSearch() }
                    implicitWidth: 130
                }

                ThemeComboBox {
                    id: resBox
                    model: backend.resolutionLabels
                    currentIndex: backend.resolutionIndex
                    onActivated: { backend.resolutionIndex = currentIndex; root.doSearch() }
                    implicitWidth: 130
                }

                ThemeComboBox {
                    id: ratioBox
                    model: backend.ratioLabels
                    currentIndex: backend.ratioIndex
                    onActivated: { backend.ratioIndex = currentIndex; root.doSearch() }
                    implicitWidth: 120
                }
            }
        }
    }

    // ------------------------------------------------------------------
    // Сетка обоев
    // ------------------------------------------------------------------
    GridView {
        id: grid
        anchors.fill: parent

        model: backend.wallpaperModel
        cellWidth: Math.floor(width / Math.max(2, backend.columns))
        cellHeight: Math.floor(cellWidth * 0.7)
        clip: true
        cacheBuffer: 800

        delegate: WallpaperCard {
            width: grid.cellWidth
            height: grid.cellHeight
            wallpaperId: model.wallpaperId
            thumb: model.thumb
            fullUrl: model.fullUrl
            localPath: model.localPath
            onClicked: root.openFull(wallpaperId, fullUrl, localPath)
        }

        onAtYEndChanged: if (atYEnd) backend.loadMore()
        onHeightChanged: Qt.callLater(root.maybeLoadMore)

        BusyIndicator {
            anchors.centerIn: parent
            running: root.loading && grid.count === 0
            visible: root.loading && grid.count === 0
        }

        Label {
            anchors.centerIn: parent
            text: "Нет результатов"
            visible: !root.loading && grid.count === 0
            opacity: 0.6
        }
    }

    // ------------------------------------------------------------------
    // Нижняя панель статуса (пилюля)
    // ------------------------------------------------------------------
    Rectangle {
        id: infoBar
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.margins: 16
        width: Math.min(parent.width - 40, 600)
        height: infoLabel.implicitHeight + 24
        radius: 4
        color: root.panelColor
        border.color: cBorderSoft
        visible: root.infoVisible

        Label {
            id: infoLabel
            anchors.fill: parent
            anchors.margins: 12
            text: root.infoText
            color: root.textColor
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    Timer {
        id: infoTimer
        interval: 5000
        repeat: false
        onTriggered: root.infoVisible = false
    }

    // ------------------------------------------------------------------
    // Окно полноразмерного просмотра
    // ------------------------------------------------------------------
    Component {
        id: fullViewComponent

        FullImageView {
            downloadPath: backend.downloadPath
        }
    }

    // ------------------------------------------------------------------
    // Настройки
    // ------------------------------------------------------------------
    SettingsDialog { id: settingsDialog }
    AboutDialog { id: aboutDialog }

    // Показывает плавающее окно по центру главного окна
    // (вложенный Window автоматически transient, координаты
    // считаются относительно главного окна).
    function openFloating(win) {
        win.x = Math.round((root.width - win.width) / 2)
        win.y = Math.round((root.height - win.height) / 2)
        win.show()
        win.requestActivate()
    }

    Connections {
        target: backend

        function onSearchStarted() { root.loading = true }
        function onSearchFinished() {
            root.loading = false
            Qt.callLater(root.maybeLoadMore)
        }
        function onInfoMessage(message) { root.showInfo(message) }
        function onDownloadPathChanged() { if (!backend.downloadedMode) root.doSearch() }
    }

}
