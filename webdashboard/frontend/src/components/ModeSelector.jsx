import './ModeSelector.css'

const MODES = [
  { value: 0, label: 'Ventilation' },
  { value: 1, label: 'Heat Recovery' },
  { value: 2, label: 'Supply' },
]

export default function ModeSelector({ mode, disabled, onModeChange }) {
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
    </div>
  )
}
