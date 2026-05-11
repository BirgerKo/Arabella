import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Page {
    id: root
    title: DeviceVM.deviceId || "Dashboard"

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 8
            anchors.rightMargin: 8

            Label {
                Layout.fillWidth: true
                text: root.title
                font.bold: true
                elide: Text.ElideRight
            }

            ToolButton {
                text: "⋯"
                onClicked: overflowMenu.open()
                Menu {
                    id: overflowMenu
                    MenuItem { text: "Details…";   onTriggered: ApplicationWindow.window.showDetails() }
                    MenuItem { text: "Schedule…";  onTriggered: ApplicationWindow.window.showSchedule() }
                    MenuItem { text: "Scenarios…"; onTriggered: ApplicationWindow.window.showScenarios() }
                    MenuSeparator {}
                    MenuItem { text: "Disconnect"; onTriggered: DeviceVM.disconnectFromDevice() }
                }
            }
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 0

            // ── Power + status ───────────────────────────────────────────
            GroupBox {
                Layout.fillWidth: true
                Layout.margins: 16

                RowLayout {
                    width: parent.width

                    PowerButton {
                        on: DeviceVM.power
                        onToggled: DeviceVM.setPower(!DeviceVM.power)
                    }

                    ColumnLayout {
                        Layout.leftMargin: 16
                        Label {
                            text: DeviceVM.power ? "On" : "Off"
                            font.bold: true
                        }
                        Label {
                            text: "IP: " + DeviceVM.deviceIp
                            font.pixelSize: 12
                            color: "gray"
                        }
                        Label {
                            visible: DeviceVM.firmwareVersion !== ""
                            text: "FW " + DeviceVM.firmwareVersion
                            font.pixelSize: 12
                            color: "gray"
                        }
                    }

                    Item { Layout.fillWidth: true }

                    RpmDisplay {
                        fan1Rpm: DeviceVM.fan1Rpm
                        fan2Rpm: DeviceVM.fan2Rpm
                    }
                }
            }

            // ── Speed ────────────────────────────────────────────────────
            GroupBox {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                title: "Speed"

                SpeedControl {
                    width: parent.width
                    speed: DeviceVM.speed
                    onSpeedSelected: (s) => DeviceVM.setSpeed(s)
                }
            }

            // ── Mode ─────────────────────────────────────────────────────
            GroupBox {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                title: "Mode"

                ModeSelector {
                    width: parent.width
                    mode: DeviceVM.mode
                    onModeSelected: (m) => DeviceVM.setMode(m)
                }
            }

            // ── Schedule toggle ──────────────────────────────────────────
            ItemDelegate {
                Layout.fillWidth: true
                Layout.leftMargin: 8
                Layout.rightMargin: 8
                text: "Weekly Schedule"

                Switch {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    checked: DeviceVM.scheduleEnabled
                    onToggled: DeviceVM.setScheduleEnabled(checked)
                }
            }

            // ── Quick scenarios ──────────────────────────────────────────
            GroupBox {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                Layout.bottomMargin: 16
                title: "Quick Scenarios"

                RowLayout {
                    width: parent.width
                    spacing: 8

                    Repeater {
                        model: ScenarioVM.quickSlots
                        delegate: Button {
                            Layout.fillWidth: true
                            text: modelData || "—"
                            enabled: modelData !== ""
                            flat: modelData === ""
                            onClicked: ScenarioVM.applyQuickSlot(index, DeviceVM.deviceId)
                        }
                    }
                }
            }
        }
    }
}
