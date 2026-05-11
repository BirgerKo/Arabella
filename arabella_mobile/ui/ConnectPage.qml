import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Page {
    id: root
    title: "Connect"

    header: ToolBar {
        Label {
            anchors.centerIn: parent
            text: root.title
            font.bold: true
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 0

            // ── Manual entry ─────────────────────────────────────────────
            GroupBox {
                Layout.fillWidth: true
                Layout.margins: 16
                title: "Manual Connection"

                ColumnLayout {
                    width: parent.width
                    spacing: 12

                    TextField {
                        id: ipField
                        Layout.fillWidth: true
                        placeholderText: "IP Address"
                        inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
                        KeyNavigation.tab: idField
                    }
                    TextField {
                        id: idField
                        Layout.fillWidth: true
                        placeholderText: "Device ID (16 chars)"
                        inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
                        KeyNavigation.tab: pwdField
                    }
                    TextField {
                        id: pwdField
                        Layout.fillWidth: true
                        placeholderText: "Password"
                        echoMode: TextInput.Password
                        onAccepted: connectBtn.clicked()
                    }
                    Button {
                        id: connectBtn
                        Layout.fillWidth: true
                        text: "Connect"
                        enabled: ipField.text.length > 0 && idField.text.length === 16
                        onClicked: DeviceVM.connectToDevice(
                            ipField.text.trim(), idField.text.trim(), pwdField.text)
                    }
                }
            }

            // ── Discovery ────────────────────────────────────────────────
            GroupBox {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                title: "Discover Fans"

                ColumnLayout {
                    width: parent.width

                    Button {
                        Layout.fillWidth: true
                        text: DeviceVM.discovering ? "Searching…" : "Search Network"
                        enabled: !DeviceVM.discovering
                        onClicked: DeviceVM.startDiscovery()
                    }

                    BusyIndicator {
                        Layout.alignment: Qt.AlignHCenter
                        running: DeviceVM.discovering
                        visible: running
                    }

                    Repeater {
                        model: DeviceVM.discoveredDevices
                        delegate: ItemDelegate {
                            Layout.fillWidth: true
                            text: (modelData.label || modelData.deviceId)
                                  + " — " + modelData.ip
                                  + "\n" + modelData.unitTypeName
                            onClicked: DeviceVM.connectToDevice(
                                modelData.ip, modelData.deviceId, "")
                        }
                    }
                }
            }

            // ── Recent devices ───────────────────────────────────────────
            GroupBox {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                Layout.bottomMargin: 16
                title: "Recent"
                visible: DeviceVM.historyEntries.length > 0

                ColumnLayout {
                    width: parent.width

                    Repeater {
                        model: DeviceVM.historyEntries
                        delegate: SwipeDelegate {
                            Layout.fillWidth: true
                            text: (modelData.label || modelData.deviceId)
                                  + " — " + modelData.ip
                            onClicked: {
                                ipField.text  = modelData.ip
                                idField.text  = modelData.deviceId
                                pwdField.text = modelData.password
                            }
                            swipe.right: Label {
                                anchors.fill: parent
                                text: "Delete"
                                color: "white"
                                background: Rectangle { color: "red" }
                                padding: 12
                                verticalAlignment: Label.AlignVCenter
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: DeviceVM.removeFromHistory(modelData.deviceId)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ── Connection progress overlay ──────────────────────────────────────
    BusyIndicator {
        anchors.centerIn: parent
        running: DeviceVM.statusText === "Connecting…"
    }
}
