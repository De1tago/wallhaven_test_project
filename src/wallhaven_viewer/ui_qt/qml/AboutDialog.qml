import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root

    title: "О программе"
    width: 420
    height: 280
    flags: Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint | Qt.WindowTitleHint
    modality: Qt.NonModal
    color: cContent

    palette.window: cPanel
    palette.windowText: cText
    palette.base: cField
    palette.text: cText
    palette.button: cPanel
    palette.buttonText: cText
    palette.highlight: cAccent
    palette.highlightedText: "#fcfcfc"
    palette.placeholderText: cMuted

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        Image {
            Layout.alignment: Qt.AlignHCenter
            source: "icons/app-icon.png"
            sourceSize.width: 96
            sourceSize.height: 96
        }

        Label {
            text: "Wallhaven Viewer"
            font.pixelSize: 20
            font.bold: true
            color: cText
            Layout.alignment: Qt.AlignHCenter
        }
        Label {
            text: "Просмотр и скачивание обоев с wallhaven.cc"
            color: cMuted
            wrapMode: Text.WordWrap
        }
        Item { Layout.fillHeight: true }
        Label {
            text: "Версия 5.0.0"
            color: cText
        }
        Label {
            text: "© 2026 Wallhaven Viewer"
            color: cMuted
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Item { Layout.fillWidth: true }
            AppButton {
                id: closeBtn
                text: "Закрыть"
                implicitHeight: 36
                implicitWidth: 100
                onClicked: root.close()
            }
        }
    }
}
