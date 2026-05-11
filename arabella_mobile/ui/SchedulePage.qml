import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Page {
    id: root
    title: "Schedule"

    Component.onCompleted: ScheduleVM.load()

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
            Switch {
                checked: DeviceVM.scheduleEnabled
                onToggled: DeviceVM.setScheduleEnabled(checked)
                padding: 8
            }
        }
    }

    // ── Loading / error states ────────────────────────────────────────────
    BusyIndicator {
        anchors.centerIn: parent
        running: ScheduleVM.loading
    }

    Label {
        anchors.centerIn: parent
        visible: !ScheduleVM.loading && ScheduleVM.lastError !== ""
        text: ScheduleVM.lastError
        color: "red"
        wrapMode: Text.WordWrap
        width: parent.width - 32
    }

    // ── Schedule grid ─────────────────────────────────────────────────────
    ListView {
        anchors.fill: parent
        visible: ScheduleVM.loaded

        model: 8     // 8 day-groups

        section.property: "day"
        section.criteria: ViewSection.FullString
        section.delegate: SectionHeader { text: dayName(section) }

        delegate: ColumnLayout {
            width: parent ? parent.width : 0
            spacing: 0

            Repeater {
                model: 4   // 4 periods per day

                delegate: ItemDelegate {
                    Layout.fillWidth: true
                    required property int index

                    property var period: periodFor(modelData, index + 1)

                    text: "Period " + (index + 1)
                    trailing: Label {
                        text: period ? (period.speed === 0 ? "Off" : "Speed " + period.speed)
                                       + "  until "
                                       + Qt.formatTime(new Date(0, 0, 0, period.endHours, period.endMinutes), "hh:mm")
                                     : "—"
                        color: "gray"
                    }
                    onClicked: periodEditor.open(modelData, index + 1, period)
                }
            }
        }
    }

    // ── Period editor sheet ───────────────────────────────────────────────
    Drawer {
        id: periodEditor
        edge: Qt.BottomEdge
        width: parent.width
        height: editorColumn.implicitHeight + 40

        property int  editDay    : 0
        property int  editPeriod : 1
        property int  editSpeed  : 0
        property int  editEndH   : 0
        property int  editEndM   : 0

        function open(day, period, data) {
            editDay    = day
            editPeriod = period
            editSpeed  = data ? data.speed      : 0
            editEndH   = data ? data.endHours   : 0
            editEndM   = data ? data.endMinutes : 0
            periodEditor.open()
        }

        ColumnLayout {
            id: editorColumn
            width: parent.width
            anchors.top: parent.top
            anchors.topMargin: 20
            spacing: 12
            padding: 16

            Label {
                text: "Period " + periodEditor.editPeriod + " — " + dayName(periodEditor.editDay)
                font.bold: true
            }

            RowLayout {
                Label { text: "Speed" }
                Item { Layout.fillWidth: true }
                ComboBox {
                    model: ["Off", "Speed 1", "Speed 2", "Speed 3"]
                    currentIndex: periodEditor.editSpeed
                    onActivated: (i) => periodEditor.editSpeed = i
                }
            }

            RowLayout {
                Label { text: "End time" }
                Item { Layout.fillWidth: true }
                SpinBox { from: 0; to: 23; value: periodEditor.editEndH; onValueModified: periodEditor.editEndH = value }
                Label { text: ":" }
                SpinBox { from: 0; to: 59; value: periodEditor.editEndM; onValueModified: periodEditor.editEndM = value }
            }

            Button {
                Layout.fillWidth: true
                text: "Save"
                onClicked: {
                    ScheduleVM.setPeriod(periodEditor.editDay, periodEditor.editPeriod,
                                         periodEditor.editSpeed,
                                         periodEditor.editEndH, periodEditor.editEndM)
                    periodEditor.close()
                }
            }
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────
    function dayName(day) {
        return ["Mon","Tue","Wed","Thu","Fri","Sat","Sun","All"][day] || "Day " + day
    }

    function periodFor(day, period) {
        for (let i = 0; i < ScheduleVM.rowCount(); ++i) {
            const idx = ScheduleVM.index(i, 0)
            if (ScheduleVM.data(idx, Qt.UserRole + 1) === day &&
                ScheduleVM.data(idx, Qt.UserRole + 2) === period)
                return {
                    speed:      ScheduleVM.data(idx, Qt.UserRole + 3),
                    endHours:   ScheduleVM.data(idx, Qt.UserRole + 4),
                    endMinutes: ScheduleVM.data(idx, Qt.UserRole + 5),
                }
        }
        return null
    }
}
