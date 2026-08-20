import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

Dialog {
    id: root

    title: "Настройки"
    modal: true
    width: 480
    height: 360
    standardButtons: Dialog.Ok | Dialog.Cancel

    // Явно задаём палитру диалога, чтобы фон, текст и кнопки
    // соответствовали теме Breeze (иначе диалог рисуется в дефолтной
    // светлой раскраске QtQuick.Controls).
    palette.window: cPanel
    palette.windowText: cText
    palette.base: cField
    palette.text: cText
    palette.button: cPanel
    palette.buttonText: cText
    palette.highlight: cAccent
    palette.highlightedText: "#fcfcfc"
    palette.placeholderText: cMuted

    // Фон диалога в цвет темы
    background: Rectangle {
        color: cPanel
        radius: 6
    }

    onAccepted: {
        backend.apiKey = apiKeyField.text
        backend.downloadPath = pathField.text
        backend.columns = colsSpin.value
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14

        Label {
            text: "API Ключ (для NSFW/Sketchy):"
            color: cText
        }
        TextField {
            id: apiKeyField
            Layout.fillWidth: true
            text: backend.apiKey
            placeholderText: "Вставьте ключ из wallhaven.cc"
            color: cText
            placeholderTextColor: cMuted
            leftPadding: 12
            rightPadding: 12
            topPadding: 9
            bottomPadding: 9
            background: Rectangle {
                radius: 4
                color: cField
                border.width: apiKeyField.activeFocus ? 2 : 1
                border.color: apiKeyField.activeFocus ? cAccent : cBorderSoft
            }
        }

        Label {
            text: "Папка для сохранения:"
            color: cText
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TextField {
                id: pathField
                Layout.fillWidth: true
                text: backend.downloadPath
                placeholderText: "Не выбрана (спрашивать каждый раз)"
                color: cText
                placeholderTextColor: cMuted
                leftPadding: 12
                rightPadding: 12
                topPadding: 9
                bottomPadding: 9
                background: Rectangle {
                    radius: 4
                    color: cField
                    border.width: pathField.activeFocus ? 2 : 1
                    border.color: pathField.activeFocus ? cAccent : cBorderSoft
                }
            }
            Button {
                id: browseBtn
                text: "Обзор…"
                implicitHeight: 36
                implicitWidth: 96
                palette.buttonText: cText
                background: Rectangle {
                    radius: 4
                    color: browseBtn.down ? Qt.darker(cPanel, 1.08)
                          : browseBtn.hovered ? Qt.lighter(cPanel, 1.12)
                          : cPanel
                    border.width: browseBtn.activeFocus ? 2 : 1
                    border.color: browseBtn.activeFocus ? cAccent : cBorderSoft
                }
                contentItem: Label {
                    text: browseBtn.text
                    color: cText
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: folderDialog.open()
            }
            Button {
                id: clearBtn
                text: "Очистить"
                implicitHeight: 36
                implicitWidth: 96
                palette.buttonText: cText
                background: Rectangle {
                    radius: 4
                    color: clearBtn.down ? Qt.darker(cPanel, 1.08)
                          : clearBtn.hovered ? Qt.lighter(cPanel, 1.12)
                          : cPanel
                    border.width: clearBtn.activeFocus ? 2 : 1
                    border.color: clearBtn.activeFocus ? cAccent : cBorderSoft
                }
                contentItem: Label {
                    text: clearBtn.text
                    color: cText
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: pathField.text = ""
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Label {
                text: "Колонок в сетке:"
                color: cText
            }
            SpinBox {
                id: colsSpin
                from: 2
                to: 10
                value: backend.columns
                implicitHeight: 36
                padding: 6
                leftPadding: 10
                rightPadding: 24
                topPadding: 8
                bottomPadding: 8
                palette.text: cText
                palette.buttonText: cText
                background: Rectangle {
                    radius: 4
                    color: cField
                    border.width: colsSpin.activeFocus ? 2 : 1
                    border.color: colsSpin.activeFocus ? cAccent : cBorderSoft
                }
            }
            Item { Layout.fillWidth: true }
        }

        Item { Layout.fillHeight: true }
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
