import { useState } from 'react'
import './SaveScenarioModal.css'

export default function SaveScenarioModal({ onSave, onCancel }) {
  const [name, setName] = useState('')
  const maxLen = 30

  function handleSubmit(e) {
    e.preventDefault()
    const trimmed = name.trim()
    if (trimmed.length >= 1) onSave(trimmed)
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Save scenario">
      <div className="modal-box card">
        <h2 className="modal-title">Save Scenario</h2>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="scenario-name">Name</label>
            <input
              id="scenario-name"
              type="text"
              value={name}
              maxLength={maxLen}
              autoFocus
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Night mode"
            />
            <span className="char-count">{name.length}/{maxLen}</span>
          </div>
          <div className="modal-actions">
            <button type="button" onClick={onCancel}>Cancel</button>
            <button type="submit" className="active" disabled={name.trim().length < 1}>
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
