import QtQuick
import QtQuick.Controls

// Circular power button that toggles on/off state.
RoundButton {
    id: root

    property bool on: false
    signal toggled()

    width: 72
    height: 72
    radius: 36

    background: Rectangle {
        radius: root.radius
        color:  root.on ? "#27ae60" : "#7f8c8d"
        border.color: Qt.lighter(color, 1.15)
        border.width: 2
    }

    contentItem: Text {
        text: "⏻"
        font.pixelSize: 28
        color: "white"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment:   Text.AlignVCenter
    }

    onClicked: root.toggled()
}
