import './QuickScenarios.css'

export default function QuickScenarios({ slots, disabled, onApply }) {
  return (
    <div className="quick-scenarios">
      {slots.map((name, i) => (
        <button
          key={i}
          className={`quick-slot ${name ? 'assigned' : ''}`}
          disabled={disabled || !name}
          onClick={() => name && onApply(name)}
          title={name ?? `Q${i + 1} (empty)`}
          aria-label={name ? `Apply scenario ${name}` : `Quick slot ${i + 1} empty`}
        >
          <span className="slot-label">Q{i + 1}</span>
          {name && <span className="slot-name">{name}</span>}
        </button>
      ))}
    </div>
  )
}
