import QtQuick
import QtQuick.Controls

Button {
    id: root
    property color accent: cAccent

    padding: 6
    leftPadding: 14
    rightPadding: 14

    background: Rectangle {
        radius: 4
        color: root.down ? Qt.darker(root.accent, 1.12)
              : root.hovered ? Qt.lighter(root.accent, 1.12)
              : root.accent
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus ? "#ffffff" : Qt.darker(root.accent, 1.2)
    }

    contentItem: Label {
        text: root.text
        color: "#ffffff"
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
}
