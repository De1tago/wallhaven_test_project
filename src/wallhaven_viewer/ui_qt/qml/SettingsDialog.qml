import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

Dialog {
    id: root

    title: "Настройки"
    modal: true
    width: 460
    height: 320
    standardButtons: Dialog.Ok | Dialog.Cancel

    onAccepted: {
        backend.apiKey = apiKeyField.text
        backend.downloadPath = pathField.text
        backend.columns = colsSpin.value
    }

        ColumnLayout {
            anchors.fill: parent
            spacing: 12

            Label { text: "API Ключ (для NSFW/Sketchy):" }
            TextField {
                id: apiKeyField
                Layout.fillWidth: true
                text: backend.apiKey
                placeholderText: "Вставьте ключ из wallhaven.cc"
                background: Rectangle {
                    radius: 6
                    color: cField
                    border.width: 1
                    border.color: cBorder
                }
            }

            Label { text: "Папка для сохранения:" }
            RowLayout {
                Layout.fillWidth: true
                spacing: 6

                TextField {
                    id: pathField
                    Layout.fillWidth: true
                    text: backend.downloadPath
                    placeholderText: "Не выбрана (спрашивать каждый раз)"
                    background: Rectangle {
                        radius: 6
                        color: cField
                        border.width: 1
                        border.color: cBorder
                    }
                }
                AccentButton {
                    text: "Обзор…"
                    onClicked: folderDialog.open()
                }
                Button {
                    text: "Очистить"
                    onClicked: pathField.text = ""
                }
            }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Label { text: "Колонок в сетке:" }
            SpinBox {
                id: colsSpin
                from: 2
                to: 10
                value: backend.columns
            }
            Item { Layout.fillWidth: true }
        }
    }

    FolderDialog {
        id: folderDialog
        title: "Выберите папку для сохранения"

        onAccepted: {
            var path = selectedFolder.toString()
            if (path.startsWith("file://")) {
                path = path.slice(7)
            }
            pathField.text = path
        }
    }
}