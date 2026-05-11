import QtQuick
import QtQuick.Layouts

// Compact two-line RPM readout for Fan 1 and Fan 2.
ColumnLayout {
    id: root

    property int fan1Rpm: 0
    property int fan2Rpm: 0

    spacing: 2

    Repeater {
        model: [
            { label: "Fan 1", rpm: root.fan1Rpm },
            { label: "Fan 2", rpm: root.fan2Rpm },
        ]

        RowLayout {
            spacing: 6
            Text {
                text: modelData.label + ":"
                font.pixelSize: 12
                color: "#555"
            }
            Text {
                text: modelData.rpm > 0 ? modelData.rpm + " RPM" : "—"
                font.pixelSize: 12
                font.bold: true
            }
        }
    }
}
