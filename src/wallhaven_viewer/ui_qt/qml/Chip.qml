import QtQuick
import QtQuick.Controls

Item {
    id: root
    property alias text: label.text
    property bool checked: false
    signal toggled(bool checked)

    implicitWidth: label.width + 28
    implicitHeight: 34

    // flat — режим для сегментированных групп: без собственной рамки
    // (её задаёт контейнер Segmented), разделители — тонкие вертикальные
    // линии между сегментами (showRightDivider).
    property bool flat: false
    property bool showRightDivider: true
    // Скругление внешних углов крайних сегментов (совпадает с рамкой
    // контейнера), чтобы не было квадратных углов по краям группы.
    property bool leftRounded: false
    property bool rightRounded: false

    // Тот же визуальный язык, что у AppButton/выпадающих списков:
    // фон как у поля (cField), рамка cBorderSoft, акцент при выборе.
    property color bgColor: cField
    property color borderColor: cBorderSoft
    property color textColor: cText
    property color accentColor: cAccent
    readonly property int _corner: 4

    Rectangle {
        anchors.fill: parent
        radius: root._corner
        topLeftRadius: root.flat ? (root.leftRounded ? root._corner : 0) : root._corner
        bottomLeftRadius: root.flat ? (root.leftRounded ? root._corner : 0) : root._corner
        topRightRadius: root.flat ? (root.rightRounded ? root._corner : 0) : root._corner
        bottomRightRadius: root.flat ? (root.rightRounded ? root._corner : 0) : root._corner
        color: {
            if (root.checked)
                return root.accentColor
            if (root.hovered)
                return cIsDark ? Qt.lighter(root.bgColor, 1.06)
                               : Qt.darker(root.bgColor, 1.04)
            return root.flat ? "transparent" : root.bgColor
        }
        border.width: root.flat ? 0 : 1
        border.color: root.checked ? Qt.darker(root.accentColor, 1.2)
                                    : root.borderColor

        Label {
            id: label
            anchors.centerIn: parent
            font.pixelSize: 12
            color: root.checked ? "#fcfcfc" : root.textColor
        }
    }

    // Вертикальный разделитель между сегментами (вместо квадратной рамки)
    Rectangle {
        visible: root.flat && root.showRightDivider
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 1
        color: root.borderColor
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
