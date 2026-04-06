import './ModeSelector.css'

const MODES = [
  { value: 0, label: 'Ventilation' },
  { value: 1, label: 'Heat Recovery' },
  { value: 2, label: 'Supply' },
]

export default function ModeSelector({
  mode, disabled, onModeChange,
  scheduleEnabled, onScheduleToggle,
}) {
  return (
    <div className="card">
      <div className="card-title">Mode</div>
      <div className="mode-buttons">
        {MODES.map(({ value, label }) => (
          <button
            key={value}
            className={mode === value ? 'active' : ''}
            disabled={disabled}
            onClick={() => onModeChange(value)}
            aria-pressed={mode === value}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="mode-schedule-row">
        <button
          className={scheduleEnabled ? 'active schedule-toggle' : 'schedule-toggle'}
          disabled={disabled}
          onClick={onScheduleToggle}
          aria-pressed={!!scheduleEnabled}
        >
          <span className="schedule-toggle-label">Schedule</span>
          <span className="schedule-toggle-state">{scheduleEnabled ? 'ON' : 'OFF'}</span>
        </button>
      </div>
    </div>
  )
}
