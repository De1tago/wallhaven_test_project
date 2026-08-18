import QtQuick
import QtQuick.Controls

Item {
    id: root
    property alias text: label.text
    property bool checked: false
    signal toggled(bool checked)
    property color accent: cAccent

    implicitWidth: label.width + 24
    implicitHeight: 30

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: root.checked ? root.accent
              : (cIsDark ? "#272b2f" : "#ffffff")
        border.width: 1
        border.color: root.checked ? root.accent
              : cBorder

        Label {
            id: label
            anchors.centerIn: parent
            font.pixelSize: 12
            color: root.checked ? "#ffffff"
                  : cText
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            root.checked = !root.checked
            root.toggled(root.checked)
        }
    }
}
