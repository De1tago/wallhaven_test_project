import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root

    title: "Настройки"
    width: 480
    height: 360
    flags: Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowTitleHint
    modality: Qt.NonModal
    color: cContent

    // Явно задаём палитру, чтобы поля, текст и кнопки соответствовали
    // теме Breeze (иначе рисуются в дефолтной светлой раскраске
    // QtQuick.Controls).
    palette.window: cPanel
    palette.windowText: cText
    palette.base: cField
    palette.text: cText
    palette.button: cPanel
    palette.buttonText: cText
    palette.highlight: cAccent
    palette.highlightedText: "#fcfcfc"
    palette.placeholderText: cMuted

    function save() {
        backend.apiKey = apiKeyField.text
        backend.downloadPath = pathField.text
        backend.columns = colsSpin.value
        root.close()
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
                placeholderText: "Не выбрана (по умолчанию: Загрузки/Wallhaven)"
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
            AppButton {
                id: browseBtn
                text: "Обзор…"
                implicitHeight: 36
                implicitWidth: 96
                onClicked: folderDialog.open()
            }
            AppButton {
                id: clearBtn
                text: "Очистить"
                implicitHeight: 36
                implicitWidth: 96
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

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Item { Layout.fillWidth: true }
            AppButton {
                id: cancelBtn
                text: "Отмена"
                implicitHeight: 36
                implicitWidth: 100
                onClicked: root.close()
            }
            AppButton {
                id: saveBtn
                text: "Сохранить"
                implicitHeight: 36
                implicitWidth: 100
                accent: true
                onClicked: root.save()
            }
        }
    }

    FolderDialog {
        id: folderDialog
        title: "Выберите папку для сохранения"

        onAccepted: {
            // toLocalFile() корректно преобразует file:///C:/... в C:/...
            // (без ведущего слэша, иначе на Windows путь невалиден).
            pathField.text = selectedFolder.toLocalFile()
        }
    }
}
