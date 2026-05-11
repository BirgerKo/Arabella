import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Three-button mode selector: Ventilation / Heat Recovery / Supply.
RowLayout {
    id: root

    property int mode: 0
    signal modeSelected(int mode)

    spacing: 8

    Repeater {
        model: ["Ventilation", "Heat Recovery", "Supply"]

        Button {
            Layout.fillWidth: true
            text: modelData
            highlighted: root.mode === index
            onClicked: root.modeSelected(index)
        }
    }
}
