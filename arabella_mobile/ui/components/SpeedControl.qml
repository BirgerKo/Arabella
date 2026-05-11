import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Three-button speed selector (1 / 2 / 3).
RowLayout {
    id: root

    property int speed: 1
    signal speedSelected(int speed)

    spacing: 8

    Repeater {
        model: [1, 2, 3]

        Button {
            Layout.fillWidth: true
            text: "Speed " + modelData
            highlighted: root.speed === modelData
            onClicked: root.speedSelected(modelData)
        }
    }
}
