import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root

    property string fullUrl: ""
    property string wallpaperId: ""
    property string localPath: ""
    property string downloadPath: ""

    width: 1000
    height: 700
    minimumWidth: 400
    minimumHeight: 300
    title: "Wallhaven — ID: " + wallpaperId
    modality: Qt.WindowModal
    color: cBg

    palette.window: cPanel
    palette.windowText: cText
    palette.base: cField
    palette.text: cText
    palette.button: cPanel
    palette.buttonText: cText
    palette.highlight: cAccent
    palette.highlightedText: "#fcfcfc"
    palette.placeholderText: cMuted

    property bool isDark: cIsDark
    property color textColor: cText
    property color borderColor: cBorder
    property color accent: cAccent

    onLocalPathChanged: {
        statusLabel.text = localPath.length > 0
            ? "Скачано: " + localPath
            : ""
    }

    onWallpaperIdChanged: {
        tagsModel.clear()
        if (root.wallpaperId.length > 0)
            backend.loadTags(root.wallpaperId)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#111111"
            radius: 12
            clip: true

            Image {
                id: img
                anchors.fill: parent
                source: root.fullUrl
                asynchronous: true
                fillMode: Image.PreserveAspectFit
                cache: false

                onStatusChanged: {
                    if (status === Image.Error) {
                        loader.visible = false
                        errorLabel.visible = true
                    }
                }
            }

            Rectangle {
                id: loader
                anchors.centerIn: parent
                width: 48
                height: 48
                radius: 24
                color: "#55000000"
                visible: img.status === Image.Loading

                BusyIndicator {
                    anchors.fill: parent
                    running: true
                }
            }

            Label {
                id: errorLabel
                anchors.centerIn: parent
                text: "Не удалось загрузить изображение"
                visible: false
            }
        }

        Label {
            id: statusLabel
            Layout.fillWidth: true
            color: root.textColor
            elide: Text.ElideMiddle
            opacity: 0.8
        }

        // Теги обоев (как в GTK-версии): клик по тегу ищет по нему
        Flow {
            id: tagsFlow
            Layout.fillWidth: true
            spacing: 6
            visible: tagsModel.count > 0

            Repeater {
                model: tagsModel
                delegate: Button {
                    text: model.name
                    flat: true
                    implicitHeight: 30
                    leftPadding: 12
                    rightPadding: 12
                    palette.buttonText: cAccent
                    background: Rectangle {
                        radius: 15
                        color: parent.hovered
                               ? Qt.lighter(cAccent, 1.4)
                               : Qt.lighter(cPanel, 1.06)
                        border.width: 1
                        border.color: cBorderSoft
                    }
                    onClicked: backend.searchByTag(model.name)
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            AccentButton {
                text: "Сохранить"
                enabled: img.status === Image.Ready
                onClicked: backend.saveTo(root.fullUrl, root.wallpaperId, "")
            }

            AccentButton {
                text: "Установить обоями"
                enabled: root.localPath.length > 0
                onClicked: backend.setWallpaper(root.localPath)
            }

            Button {
                text: "Открыть на сайте"
                onClicked: backend.openInBrowser(root.wallpaperId)
            }

            Item { Layout.fillWidth: true }

            Button {
                text: "Закрыть"
                onClicked: root.close()
            }
        }
    }

    // Диалог сохранения — используется, если папка по умолчанию не задана
    FileDialog {
        id: saveDialog
        title: "Сохранить обои"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "jpg"
        nameFilters: ["Изображения (*.jpg *.jpeg *.png)"]

        onAccepted: {
            var path = selectedFile.toString()
            if (path.startsWith("file://")) {
                path = path.slice(7)
            }
            backend.saveTo(root.fullUrl, root.wallpaperId, path)
        }
    }

    ListModel { id: tagsModel }

    Connections {
        target: backend

        function onTagsLoaded(id, names) {
            if (id !== root.wallpaperId)
                return
            tagsModel.clear()
            for (var i = 0; i < names.length; i++)
                tagsModel.append({ name: names[i] })
        }

        function onSaved(path, error) {
            if (path.length > 0) {
                root.localPath = path
            } else {
                statusLabel.text = "Ошибка сохранения: " + error
            }
        }

        function onWallpaperSet(message) {
            statusLabel.text = message
        }
    }
}
