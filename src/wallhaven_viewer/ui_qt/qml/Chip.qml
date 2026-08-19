import QtQuick
import QtQuick.Controls

Item {
    id: root
    property alias text: label.text
    property bool checked: false
    signal toggled(bool checked)

    implicitWidth: label.width + 28
    implicitHeight: 32

    // flat — режим для сегментированных групп: без собственной рамки
    // и скруглений (их задаёт контейнер Segmented).
    property bool flat: false

    // Активное состояние — фирменный голубой Breeze (#3daee9):
    // лёгкая голубая подсветка фона + акцентная рамка.
    property color checkedColor: Qt.rgba(61 / 255, 174 / 255, 233 / 255, 0.22)
    property color hoverColor: cIsDark ? Qt.lighter(cPanel, 1.18)
                                       : Qt.darker(cPanel, 1.04)

    Rectangle {
        anchors.fill: parent
        radius: root.flat ? 0 : 4
        color: root.checked ? root.checkedColor
              : (root.hovered ? root.hoverColor : cPanel)
        border.width: root.flat ? 0 : 1
        border.color: root.checked ? cAccent : cBorderSoft

        Label {
            id: label
            anchors.centerIn: parent
            font.pixelSize: 12
            color: cText
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
