import QtQuick
import QtQuick.Controls

Item {
    id: root
    property alias text: label.text
    property bool checked: false
    signal toggled(bool checked)

    implicitWidth: label.width + 28
    implicitHeight: 34

    // flat — режим для сегментированных групп: без собственного скругления
    // (его задаёт контейнер Segmented), но с тонкой рамкой-разделителем.
    property bool flat: false

    // Тот же визуальный язык, что у AppButton/выпадающих списков:
    // фон как у поля (cField), рамка cBorderSoft, акцент при выборе.
    property color bgColor: cField
    property color borderColor: cBorderSoft
    property color textColor: cText
    property color accentColor: cAccent

    Rectangle {
        anchors.fill: parent
        radius: root.flat ? 0 : 4
        color: {
            if (root.checked)
                return root.accentColor
            if (root.hovered)
                return cIsDark ? Qt.lighter(root.bgColor, 1.06)
                               : Qt.darker(root.bgColor, 1.04)
            return root.flat ? "transparent" : root.bgColor
        }
        border.width: 1
        border.color: root.checked ? Qt.darker(root.accentColor, 1.2)
                                    : root.borderColor

        Label {
            id: label
            anchors.centerIn: parent
            font.pixelSize: 12
            color: root.checked ? "#fcfcfc" : root.textColor
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
