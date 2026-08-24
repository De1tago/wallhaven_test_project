import QtQuick
import QtQuick.Controls

// Единая кнопка в стиле выпадающих списков (разрешение/соотношение/сортировка):
// радиус 4, фон как у поля ввода (cField), тонкая рамка cBorderSoft,
// акцентная рамка при фокусе. Для основных действий (accent: true) —
// заливка акцентным цветом, тот же радиус и отступы.
Button {
    id: root

    property color bgColor: cField
    property color borderColor: cBorderSoft
    property color textColor: cText
    property color accentColor: cAccent
    property bool accent: false

    padding: 6
    leftPadding: 14
    rightPadding: 14
    topPadding: 8
    bottomPadding: 8
    font.pixelSize: 13

    background: Rectangle {
        radius: 4
        color: {
            if (root.accent) {
                return root.down ? Qt.darker(root.accentColor, 1.12)
                     : root.hovered ? Qt.lighter(root.accentColor, 1.12)
                     : root.accentColor
            }
            return root.down ? Qt.darker(root.bgColor, 1.05)
                 : root.hovered
                   ? (cIsDark ? Qt.lighter(root.bgColor, 1.06)
                              : Qt.darker(root.bgColor, 1.04))
                   : root.bgColor
        }
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus ? root.accentColor
                     : (root.accent ? Qt.darker(root.accentColor, 1.2)
                                    : root.borderColor)
    }

    contentItem: Label {
        text: root.text
        color: root.accent ? "#fcfcfc" : root.textColor
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
}
