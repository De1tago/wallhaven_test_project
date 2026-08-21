import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root

    title: "О программе"
    width: 420
    height: 280
    flags: Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowTitleHint
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

        Label {
            text: "Wallhaven Viewer"
            font.pixelSize: 20
            font.bold: true
            color: cText
        }
        Label {
            text: "Просмотр и скачивание обоев с wallhaven.cc"
            color: cMuted
            wrapMode: Text.WordWrap
        }
        Item { Layout.fillHeight: true }
        Label {
            text: "Версия 1.0"
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
            Button {
                id: closeBtn
                text: "Закрыть"
                implicitHeight: 36
                implicitWidth: 100
                palette.buttonText: cText
                background: Rectangle {
                    radius: 4
                    color: closeBtn.down ? Qt.darker(cPanel, 1.08)
                          : closeBtn.hovered ? Qt.lighter(cPanel, 1.12)
                          : cPanel
                    border.width: closeBtn.activeFocus ? 2 : 1
                    border.color: closeBtn.activeFocus ? cAccent : cBorderSoft
                }
                contentItem: Label {
                    text: closeBtn.text
                    color: cText
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: root.close()
            }
        }
    }
}
