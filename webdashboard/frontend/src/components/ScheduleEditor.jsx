import { useState, useCallback, useEffect } from 'react'
import './ScheduleEditor.css'

const DAY_LABELS = [
  'Weekdays', 'Monday', 'Tuesday', 'Wednesday',
  'Thursday', 'Friday', 'Saturday', 'Sunday',
]
const SPEED_LABELS = ['Standby', 'Speed 1', 'Speed 2', 'Speed 3']
const NUM_PERIODS = 4

function buildInitialPeriods() {
  return DAY_LABELS.map(() =>
    Array.from({ length: NUM_PERIODS }, () => ({ speed: 0, end_h: 0, end_m: 0 }))
  )
}

function PeriodCell({ value, onChange }) {
  const timeStr = `${String(value.end_h).padStart(2, '0')}:${String(value.end_m).padStart(2, '0')}`

  function handleSpeed(e) {
    onChange({ ...value, speed: Number(e.target.value) })
  }

  function handleTime(e) {
    const [h, m] = e.target.value.split(':').map(Number)
    onChange({ ...value, end_h: h ?? 0, end_m: m ?? 0 })
  }

  return (
    <div className="period-cell">
      <select value={value.speed} onChange={handleSpeed} className="period-speed">
        {SPEED_LABELS.map((label, i) => (
          <option key={i} value={i}>{label}</option>
        ))}
      </select>
      <input
        type="time"
        value={timeStr}
        onChange={handleTime}
        className="period-time"
        aria-label="End time"
      />
    </div>
  )
}

export default function ScheduleEditor({ initialPeriods, onApply, onClose, busy }) {
  const [periods, setPeriods] = useState(buildInitialPeriods)

  useEffect(() => {
    if (initialPeriods) setPeriods(initialPeriods)
  }, [initialPeriods])

  const handleCellChange = useCallback((dayIdx, periodIdx, value) => {
    setPeriods((prev) => {
      const next = prev.map((row) => [...row])
      next[dayIdx][periodIdx] = value
      return next
    })
  }, [])

  async function handleApply() {
    for (let d = 0; d < DAY_LABELS.length; d++) {
      for (let p = 0; p < NUM_PERIODS; p++) {
        const { speed, end_h, end_m } = periods[d][p]
        await onApply(d, p + 1, speed, end_h, end_m)
      }
    }
    onClose()
  }

  if (!initialPeriods) {
    return (
      <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Weekly schedule editor">
        <div className="modal-box schedule-modal card">
          <h2 className="modal-title">Weekly Schedule</h2>
          <p>Loading schedule from device…</p>
          <div className="modal-actions">
            <button type="button" onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Weekly schedule editor">
      <div className="modal-box schedule-modal card">
        <h2 className="modal-title">Weekly Schedule</h2>
        <p className="schedule-hint">
          Set the end time and fan speed for each period within a day.
          Periods run in sequence and together cover 24 hours.
        </p>

        <div className="schedule-table-wrapper">
          <table className="schedule-table">
            <thead>
              <tr>
                <th>Day</th>
                {Array.from({ length: NUM_PERIODS }, (_, i) => (
                  <th key={i}>Period {i + 1}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {DAY_LABELS.map((day, dayIdx) => (
                <tr key={dayIdx}>
                  <td className="day-label">{day}</td>
                  {Array.from({ length: NUM_PERIODS }, (_, periodIdx) => (
                    <td key={periodIdx}>
                      <PeriodCell
                        value={periods[dayIdx][periodIdx]}
                        onChange={(v) => handleCellChange(dayIdx, periodIdx, v)}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="modal-actions">
          <button type="button" onClick={onClose}>Close</button>
          <button
            type="button"
            className="active"
            disabled={busy}
            onClick={handleApply}
          >
            Apply to device
          </button>
        </div>
      </div>
    </div>
  )
}
