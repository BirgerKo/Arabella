import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Page {
    id: root
    title: "Scenarios"

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
            ToolButton {
                text: "+"
                onClicked: saveDialog.open()
            }
        }
    }

    ListView {
        anchors.fill: parent
        model: ScenarioVM
        spacing: 0

        delegate: SwipeDelegate {
            width: parent ? parent.width : 0
            text: model.name
            onClicked: {
                applyDialog.scenarioName = model.name
                applyDialog.open()
            }

            swipe.right: RowLayout {
                anchors.fill: parent
                spacing: 0

                Button {
                    Layout.fillHeight: true
                    text: "Rename"
                    background: Rectangle { color: "steelblue" }
                    contentItem: Label { text: "Rename"; color: "white"; horizontalAlignment: Text.AlignHCenter }
                    onClicked: {
                        renameDialog.scenarioName = model.name
                        renameDialog.open()
                    }
                }
                Button {
                    Layout.fillHeight: true
                    text: "Delete"
                    background: Rectangle { color: "#e74c3c" }
                    contentItem: Label { text: "Delete"; color: "white"; horizontalAlignment: Text.AlignHCenter }
                    onClicked: ScenarioVM.deleteScenario(model.name)
                }
            }
        }

        Label {
            anchors.centerIn: parent
            visible: ScenarioVM.rowCount() === 0
            text: "No scenarios saved yet.\nTap + to save the current state."
            horizontalAlignment: Text.AlignHCenter
            color: "gray"
        }
    }

    // ── Quick-slot assignment ─────────────────────────────────────────────
    GroupBox {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 16 }
        title: "Quick Slots"

        RowLayout {
            width: parent.width
            spacing: 8

            Repeater {
                model: ScenarioVM.quickSlots
                delegate: Button {
                    Layout.fillWidth: true
                    text: modelData || "—"
                    flat: modelData === ""
                    onPressAndHold: quickSlotMenu.openFor(index)
                    onClicked: {
                        if (modelData !== "")
                            ScenarioVM.applyQuickSlot(index, DeviceVM.deviceId)
                    }
                }
            }
        }
    }

    // ── Save current state dialog ─────────────────────────────────────────
    Dialog {
        id: saveDialog
        title: "Save Scenario"
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel

        onAccepted: {
            if (nameField.text.trim() !== "")
                ScenarioVM.saveCurrentState(nameField.text.trim(),
                                            DeviceVM.deviceId,
                                            DeviceVM.lastState)
        }

        TextField {
            id: nameField
            anchors.fill: parent
            placeholderText: "Scenario name"
        }
    }

    // ── Apply confirm dialog ──────────────────────────────────────────────
    Dialog {
        id: applyDialog
        property string scenarioName: ""
        title: 'Apply "' + scenarioName + '"'
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Yes | Dialog.No

        Label {
            text: "Apply this scenario to " + DeviceVM.deviceId + "?"
            wrapMode: Text.WordWrap
            width: parent.width
        }

        onAccepted: ScenarioVM.applyScenario(scenarioName, DeviceVM.deviceId)
    }

    // ── Rename dialog ─────────────────────────────────────────────────────
    Dialog {
        id: renameDialog
        property string scenarioName: ""
        title: "Rename Scenario"
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel

        onOpened: renameField.text = scenarioName

        onAccepted: {
            if (renameField.text.trim() !== "" && renameField.text !== scenarioName)
                ScenarioVM.renameScenario(scenarioName, renameField.text.trim())
        }

        TextField {
            id: renameField
            anchors.fill: parent
            placeholderText: "New name"
        }
    }

    // ── Quick-slot assignment menu ────────────────────────────────────────
    Menu {
        id: quickSlotMenu
        property int targetSlot: 0
        function openFor(slot) { targetSlot = slot; open() }

        Repeater {
            model: ScenarioVM
            MenuItem {
                text: model.name
                onTriggered: ScenarioVM.setQuickSlot(quickSlotMenu.targetSlot, model.name)
            }
        }
        MenuItem { text: "Clear"; onTriggered: ScenarioVM.setQuickSlot(quickSlotMenu.targetSlot, "") }
    }
}
