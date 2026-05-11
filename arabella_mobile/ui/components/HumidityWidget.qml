import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Humidity sensor on/off toggle + threshold slider + current reading.
ColumnLayout {
    id: root
    spacing: 12

    property int sensorMode: 0        // 0 = off, 1 = internal, 2 = external
    property int threshold:  60       // 40–80 %RH
    property int current:    0        // live reading (0 when unavailable)

    signal sensorModeChanged(int mode)
    signal thresholdChanged(int rh)

    // ── Sensor on/off ────────────────────────────────────────────────────
    RowLayout {
        Layout.fillWidth: true
        Label { text: "Humidity Sensor" }
        Item  { Layout.fillWidth: true }
        ComboBox {
            model: ["Off", "Internal", "External"]
            currentIndex: root.sensorMode
            onActivated: (i) => root.sensorModeChanged(i)
        }
    }

    // ── Threshold slider ─────────────────────────────────────────────────
    ColumnLayout {
        Layout.fillWidth: true
        visible: root.sensorMode !== 0

        RowLayout {
            Label { text: "Threshold" }
            Item  { Layout.fillWidth: true }
            Label { text: root.threshold + " %RH"; font.bold: true }
        }
        Slider {
            Layout.fillWidth: true
            from: 40; to: 80; stepSize: 1
            value: root.threshold
            onMoved: root.thresholdChanged(Math.round(value))
        }
    }

    // ── Current reading ──────────────────────────────────────────────────
    RowLayout {
        Layout.fillWidth: true
        visible: root.sensorMode !== 0 && root.current > 0
        Label { text: "Current Humidity" }
        Item  { Layout.fillWidth: true }
        Label { text: root.current + " %RH"; font.bold: true }
    }
}
