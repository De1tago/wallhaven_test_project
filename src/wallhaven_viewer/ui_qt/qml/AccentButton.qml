import QtQuick
import QtQuick.Controls

Button {
    id: root
    property color accent: cAccent

    background: Rectangle {
        radius: 8
        color: root.down ? Qt.darker(root.accent, 1.12)
              : root.hovered ? Qt.lighter(root.accent, 1.12)
              : root.accent
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
