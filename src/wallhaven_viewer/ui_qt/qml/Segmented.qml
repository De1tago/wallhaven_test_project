import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Контейнер для сегментированных кнопок (Segmented Control) в духе Breeze:
// общая скруглённая рамка, внутренние перегородки, без зазоров между
// кнопками. Дочерние элементы (чипы/кнопки) помещаются внутрь RowLayout.
Rectangle {
    id: root

    radius: 4
    color: cField
    border.width: 1
    border.color: cBorderSoft
    clip: true

    implicitWidth: row.implicitWidth
    implicitHeight: row.implicitHeight

    // Дочерние элементы (объявленные внутри Segmented) попадают в row.
    default property alias contents: row.children

    RowLayout {
        id: row
        anchors.fill: parent
        spacing: 0
    }
}
