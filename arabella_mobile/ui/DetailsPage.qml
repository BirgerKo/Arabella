import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Page {
    id: root
    title: "Details"

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 8

            ToolButton {
                text: "‹ Back"
                onClicked: ApplicationWindow.window.goBack()
            }
            Label {
                Layout.fillWidth: true
                text: root.title
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
            }
            Item { width: 60 }
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 0

            // ── Boost ────────────────────────────────────────────────────
            GroupBox {
                Layout.fillWidth: true
                Layout.margins: 16
                title: "Boost"

                RowLayout {
                    width: parent.width
                    Label { text: "Boost Mode" }
                    Item { Layout.fillWidth: true }
                    Switch {
                        checked: DeviceVM.boostActive
                        onToggled: DeviceVM.setBoostStatus(checked)
                    }
                }
            }

            // ── Humidity ─────────────────────────────────────────────────
            GroupBox {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                title: "Humidity"

                HumidityWidget {
                    width: parent.width
                    sensorMode: DeviceVM.humiditySensor
                    threshold: DeviceVM.humidityThreshold
                    current: DeviceVM.currentHumidity
                    onSensorModeChanged: (s) => DeviceVM.setHumiditySensor(s)
                    onThresholdChanged:  (t) => DeviceVM.setHumidityThreshold(t)
                }
            }

            // ── RPM ──────────────────────────────────────────────────────
            GroupBox {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                title: "Fan Speed"

                RowLayout {
                    width: parent.width
                    spacing: 24

                    ColumnLayout {
                        Label { text: "Fan 1"; font.bold: true; Layout.alignment: Qt.AlignHCenter }
                        Label {
                            text: DeviceVM.fan1Rpm > 0 ? DeviceVM.fan1Rpm + " RPM" : "—"
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                    ColumnLayout {
                        Label { text: "Fan 2"; font.bold: true; Layout.alignment: Qt.AlignHCenter }
                        Label {
                            text: DeviceVM.fan2Rpm > 0 ? DeviceVM.fan2Rpm + " RPM" : "—"
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }
            }

            // ── Maintenance ──────────────────────────────────────────────
            GroupBox {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                title: "Maintenance"

                ColumnLayout {
                    width: parent.width

                    Label {
                        visible: DeviceVM.filterNeedsReplacement
                        text: "⚠ Filter replacement needed"
                        color: "orange"
                    }
                    Label {
                        visible: DeviceVM.alarmStatus !== 0
                        text: "⚠ Alarm active: " + DeviceVM.alarmStatus
                        color: "red"
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Reset Filter Timer"
                        onClicked: DeviceVM.resetFilterTimer()
                    }
                    Button {
                        Layout.fillWidth: true
                        text: "Reset Alarms"
                        visible: DeviceVM.alarmStatus !== 0
                        onClicked: DeviceVM.resetAlarms()
                    }
                }
            }

            // ── Clock ────────────────────────────────────────────────────
            GroupBox {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                Layout.bottomMargin: 16
                title: "Clock"

                Button {
                    width: parent.width
                    text: "Sync RTC to Device Time"
                    onClicked: DeviceVM.syncRtc()
                }
            }
        }
    }
}
