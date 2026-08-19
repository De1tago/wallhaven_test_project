import QtQuick
import QtQuick.Controls

// Выпадающий список, оформленный в палитре Breeze. Используется
// стандартный popup ComboBox (чтобы открытие/выбор работали корректно),
// а стилизуются только фон, делегаты, индикатор и рамка фокуса.
ComboBox {
    id: control

    property color bgColor: cField
    property color panelColor: cPanel
    property color borderColor: cBorderSoft
    property color textColor: cText
    property color mutedColor: cMuted
    property color accentColor: cAccent

    padding: 6
    leftPadding: 12
    rightPadding: indicator.width + 14
    spacing: 4
    font.pixelSize: 13

    background: Rectangle {
        radius: 4
        color: control.bgColor
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? control.accentColor : control.borderColor
    }

    contentItem: Label {
        text: control.displayText
        color: control.textColor
        font: control.font
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.leftPadding
        rightPadding: control.rightPadding
        elide: Text.ElideRight
    }

    indicator: Canvas {
        id: canvas
        x: control.width - width - 10
        y: control.topPadding + (control.availableHeight - height) / 2
        width: 12
        height: 8
        enabled: false
        contextType: "2d"

        Connections {
            target: control
            function onPressedChanged() { canvas.requestPaint() }
        }

        onPaint: {
            context.reset()
            context.moveTo(0, 0)
            context.lineTo(width, 0)
            context.lineTo(width / 2, height)
            context.closePath()
            context.fillStyle = control.mutedColor
            context.fill()
        }
    }

    // Стиль пунктов списка
    delegate: ItemDelegate {
        width: control.width
        height: 34
        contentItem: Label {
            text: modelData
            color: control.textColor
            font: control.font
            verticalAlignment: Text.AlignVCenter
            leftPadding: 12
            elide: Text.ElideRight
        }
        highlighted: control.highlightedIndex === index
        background: Rectangle {
            color: highlighted ? control.bgColor : "transparent"
            radius: 4
        }
    }

    // Фон выпадающего списка
    popup.background: Rectangle {
        color: control.panelColor
        border.width: 1
        border.color: control.borderColor
        radius: 4
    }
}
