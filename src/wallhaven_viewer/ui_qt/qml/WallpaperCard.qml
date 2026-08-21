import QtQuick
import QtQuick.Controls
import QtQuick.Effects

Item {
    id: root

    property string wallpaperId: ""
    property string thumb: ""
    property string fullUrl: ""
    property string localPath: ""
    property string localUrl: ""

    signal clicked()

    property color accent: cAccent

    Rectangle {
        id: card
        anchors.fill: parent
        anchors.margins: 6
        radius: 12
        color: cIsDark ? "#272b2f" : "#ececec"
        clip: true

        Image {
            id: img
            anchors.fill: parent
            source: localPath.length > 0 ? localUrl : thumb
            asynchronous: true
            cache: true
            fillMode: Image.PreserveAspectCrop
            visible: status !== Image.Error

            onStatusChanged: {
                if (status === Image.Error) {
                    loader.visible = false
                    errorLabel.visible = true
                }
            }
        }

        Rectangle {
            id: loader
            anchors.centerIn: parent
            width: 28
            height: 28
            radius: 14
            color: "#33000000"

            BusyIndicator {
                anchors.fill: parent
                running: true
            }
            visible: img.status === Image.Loading
        }

        Label {
            id: errorLabel
            anchors.centerIn: parent
            text: "Нет превью"
            visible: false
            opacity: 0.7
        }

        // Затемнение при наведении + подпись
        Rectangle {
            id: overlay
            anchors.fill: parent
            color: "#000000"
            opacity: 0
            radius: 12

            Label {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 10
                text: root.wallpaperId
                color: "#ffffff"
                font.pixelSize: 11
                opacity: 0.85
                elide: Text.ElideRight
            }
        }

        // Значок «скачано»
        Rectangle {
            visible: localPath.length > 0
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 10
            width: 18
            height: 18
            radius: 9
            color: "#2ecc71"

            Text {
                anchors.centerIn: parent
                text: "✓"
                font.pixelSize: 11
                color: "white"
            }
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            onEntered: overlay.opacity = 0.3
            onExited: overlay.opacity = 0
            onClicked: root.clicked()
        }
    }

    // Мягкая тень для объёма
    MultiEffect {
        source: card
        anchors.fill: card
        shadowEnabled: true
        shadowColor: "#000000"
        shadowBlur: 0.35
        shadowOpacity: cIsDark ? 0.55 : 0.18
        shadowVerticalOffset: 3
    }
}
