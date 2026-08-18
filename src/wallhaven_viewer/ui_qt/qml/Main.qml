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
        color: root.bgColor
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

        // Строка поиска и действий
        ToolBar {
            Layout.fillWidth: true
            background: Rectangle { color: root.bgColor }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 10

                ToolButton {
                    icon.name: "view-refresh"
                    onClicked: root.doSearch()
                    ToolTip.visible: hovered
                    ToolTip.text: "Обновить"
                }

                TextField {
                    id: searchField
                    Layout.fillWidth: true
                    leftPadding: 34
                    placeholderText: "Поиск обоев (например, cyberpunk)…"
                    text: backend.query
                    onAccepted: root.doSearch()
                    background: Rectangle {
                        radius: 8
                        color: root.fieldColor
                        border.width: 1
                        border.color: root.borderColor
                    }
                    // Интегрированная кнопка «Найти» внутри поля (magnifier)
                    ToolButton {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        focusPolicy: Qt.NoFocus
                        icon.name: "system-search"
                        onClicked: root.doSearch()
                        ToolTip.visible: hovered
                        ToolTip.text: "Найти"
                        background: Rectangle { color: "transparent" }
                    }
                }

                ToolButton {
                    checkable: true
                    checked: backend.downloadedMode
                    icon.name: "folder-download"
                    onToggled: {
                        backend.downloadedMode = checked
                        root.doSearch()
                    }
                    ToolTip.visible: hovered
                    ToolTip.text: "Только скачанные обои"
                }

                ToolButton {
                    icon.name: "preferences-system"
                    onClicked: settingsDialog.open()
                    ToolTip.visible: hovered
                    ToolTip.text: "Настройки"
                }
            }
        }

        // Строка фильтров
        ToolBar {
            Layout.fillWidth: true
            background: Rectangle {
                color: root.bgColor
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: root.borderColor
                }
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 8

                Chip {
                    text: "General"
                    checked: backend.catGeneral
                    onToggled: { backend.catGeneral = checked; root.doSearch() }
                }
                Chip {
                    text: "Anime"
                    checked: backend.catAnime
                    onToggled: { backend.catAnime = checked; root.doSearch() }
                }
                Chip {
                    text: "People"
                    checked: backend.catPeople
                    onToggled: { backend.catPeople = checked; root.doSearch() }
                }

                Rectangle { width: 1; height: 22; color: root.borderColor }

                Chip {
                    text: "SFW"
                    checked: backend.puritySfw
                    onToggled: { backend.puritySfw = checked; root.doSearch() }
                }
                Chip {
                    text: "Sketchy"
                    checked: backend.puritySketchy
                    onToggled: { backend.puritySketchy = checked; root.doSearch() }
                }
                Chip {
                    text: "NSFW"
                    checked: backend.purityNsfw
                    onToggled: { backend.purityNsfw = checked; root.doSearch() }
                }

                Item { Layout.fillWidth: true }

                ComboBox {
                    id: sortBox
                    model: backend.sortLabels
                    currentIndex: backend.sortIndex
                    onActivated: { backend.sortIndex = currentIndex; root.doSearch() }
                    implicitWidth: 140
                }

                ComboBox {
                    id: resBox
                    model: backend.resolutionLabels
                    currentIndex: backend.resolutionIndex
                    onActivated: { backend.resolutionIndex = currentIndex; root.doSearch() }
                    implicitWidth: 150
                }

                ComboBox {
                    id: ratioBox
                    model: backend.ratioLabels
                    currentIndex: backend.ratioIndex
                    onActivated: { backend.ratioIndex = currentIndex; root.doSearch() }
                    implicitWidth: 130
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
        radius: height / 2
        color: root.panelColor
        border.color: root.borderColor
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
    SettingsDialog {
        id: settingsDialog
        parent: Overlay.overlay
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

    Component.onCompleted: {
        root.showInfo("Готово")
    }
}
