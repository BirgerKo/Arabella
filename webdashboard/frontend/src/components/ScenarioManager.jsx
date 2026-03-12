import './ScenarioManager.css'

const SLOT_OPTIONS = [null, 'Q1', 'Q2', 'Q3']

function slotIndex(slots, name) {
  return slots.indexOf(name)
}

export default function ScenarioManager({
  scenarios,
  quickSlots,
  onApply,
  onDelete,
  onSetQuickSlot,
  disabled,
}) {
  if (scenarios.length === 0) {
    return (
      <div className="card scenario-manager">
        <div className="card-title">Scenarios</div>
        <p className="empty-msg">No scenarios saved yet.</p>
      </div>
    )
  }

  return (
    <div className="card scenario-manager">
      <div className="card-title">Scenarios</div>
      <ul className="scenario-list">
        {scenarios.map((s) => {
          const assignedSlot = slotIndex(quickSlots, s.name)
          return (
            <li key={s.name} className="scenario-row">
              <span className="scenario-name">{s.name}</span>
              <div className="scenario-actions">
                <select
                  className="slot-select"
                  value={assignedSlot >= 0 ? `Q${assignedSlot + 1}` : ''}
                  aria-label={`Quick slot for ${s.name}`}
                  onChange={(e) => {
                    const val = e.target.value
                    const newSlots = [...quickSlots]
                    // Clear old assignment
                    const old = slotIndex(newSlots, s.name)
                    if (old >= 0) newSlots[old] = null
                    if (val) {
                      const idx = SLOT_OPTIONS.indexOf(val) - 1
                      newSlots[idx] = s.name
                    }
                    onSetQuickSlot(newSlots)
                  }}
                >
                  <option value="">—</option>
                  <option value="Q1">Q1</option>
                  <option value="Q2">Q2</option>
                  <option value="Q3">Q3</option>
                </select>
                <button
                  disabled={disabled}
                  onClick={() => onApply(s.name)}
                  aria-label={`Apply ${s.name}`}
                  title="Apply"
                >
                  ▶
                </button>
                <button
                  className="danger"
                  onClick={() => onDelete(s.name)}
                  aria-label={`Delete ${s.name}`}
                  title="Delete"
                >
                  ✕
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
