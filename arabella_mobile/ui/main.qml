import QtQuick
import QtQuick.Controls

ApplicationWindow {
    id: root
    width: 390
    height: 844
    visible: true
    title: "Arabella"

    // ── Navigation stack ─────────────────────────────────────────────────────
    StackView {
        id: stack
        anchors.fill: parent
        initialItem: DeviceVM.connected ? dashboardPage : connectPage
    }

    // ── Error banner ─────────────────────────────────────────────────────────
    Rectangle {
        id: errorBanner
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: visible ? errorLabel.implicitHeight + 24 : 0
        color: "#c0392b"
        visible: false
        z: 100

        Label {
            id: errorLabel
            anchors.centerIn: parent
            text: DeviceVM.lastError
            color: "white"
            wrapMode: Text.WordWrap
            width: parent.width - 32
        }

        Timer {
            id: errorTimer
            interval: 4000
            onTriggered: errorBanner.visible = false
        }
    }

    Connections {
        target: DeviceVM
        function onConnectionError(message) {
            errorBanner.visible = true
            errorTimer.restart()
        }
        function onLastErrorChanged() {
            if (DeviceVM.lastError !== "") {
                errorBanner.visible = true
                errorTimer.restart()
            }
        }
        function onConnectionChanged() {
            if (DeviceVM.connected)
                stack.replace(null, dashboardPage)
            else
                stack.replace(null, connectPage)
        }
    }

    // ── Page components ──────────────────────────────────────────────────────
    Component { id: connectPage;   ConnectPage   {} }
    Component { id: dashboardPage; DashboardPage {} }
    Component { id: detailsPage;   DetailsPage   {} }
    Component { id: schedulePage;  SchedulePage  {} }
    Component { id: scenarioPage;  ScenarioPage  {} }

    // ── Global navigation helpers (called by pages) ──────────────────────────
    function showDetails()  { stack.push(detailsPage)  }
    function showSchedule() { stack.push(schedulePage) }
    function showScenarios(){ stack.push(scenarioPage) }
    function goBack()       { stack.pop() }
}
