import { useRef, useState, useEffect } from 'react'
import HumidityControl from './HumidityControl.jsx'
import RpmDisplay from './RpmDisplay.jsx'
import ScenarioManager from './ScenarioManager.jsx'
import './FanDetailsModal.css'

// ── Scenario dropdown (create-new / add-to-existing) ─────────────────────────

function ScenarioDropdown({ scenarios, disabled, onCreateNew, onAddToExisting }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  function handleCreateNew() {
    setOpen(false)
    onCreateNew()
  }

  function handleAddTo(name) {
    setOpen(false)
    onAddToExisting(name)
  }

  return (
    <div className="scenario-dropdown" ref={ref}>
      <button
        className="save-scenario-btn"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="true"
        aria-expanded={open}
      >
        Scenario ▾
      </button>
      {open && (
        <div className="scenario-menu">
          <button className="scenario-menu-item" onClick={handleCreateNew}>
            Create new scenario…
          </button>
          {scenarios.length > 0 && (
            <>
              <div className="scenario-menu-divider" />
              <div className="scenario-menu-label">Add to existing</div>
              {scenarios.map((s) => (
                <button
                  key={s.name}
                  className="scenario-menu-item scenario-menu-item--indent"
                  onClick={() => handleAddTo(s.name)}
                >
                  {s.name}
                </button>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ── FanDetailsModal ───────────────────────────────────────────────────────────

export default function FanDetailsModal({
  deviceState,
  disabled,
  scenarios,
  quickSlots,
  onBoost,
  onHumiditySensor,
  onHumidityThreshold,
  onScheduleEnable,
  onScheduleEdit,
  onSyncRtc,
  onCreateNewScenario,
  onAddToExisting,
  onApplyScenario,
  onDeleteScenario,
  onSetQuickSlot,
  onClose,
}) {
  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Fan details"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="fan-details-modal">
        <div className="fan-details-header">
          <div>
            <span className="fan-details-name">{deviceState?.device_id ?? '—'}</span>
            {deviceState?.ip && (
              <span className="fan-details-ip"> · {deviceState.ip}</span>
            )}
          </div>
          <button
            className="fan-details-close"
            onClick={onClose}
            aria-label="Close details"
          >
            ✕
          </button>
        </div>

        <div className="fan-details-body">
          {/* Boost */}
          <div className="detail-section">
            <div className="card-title">Boost</div>
            <button
              className={deviceState?.boost_active ? 'active boost-btn' : 'boost-btn'}
              disabled={disabled}
              onClick={onBoost}
              aria-pressed={!!deviceState?.boost_active}
              style={
                deviceState?.boost_active
                  ? { borderColor: 'var(--warning)', background: 'color-mix(in srgb, var(--warning) 15%, var(--surface2))' }
                  : {}
              }
            >
              Boost: {deviceState?.boost_active ? 'ON' : 'OFF'}
            </button>
          </div>

          {/* Humidity */}
          <HumidityControl
            humiditySensor={deviceState?.humidity_sensor ?? null}
            humidityThreshold={deviceState?.humidity_threshold ?? null}
            currentHumidity={deviceState?.current_humidity ?? null}
            disabled={disabled}
            onSensorChange={onHumiditySensor}
            onThresholdChange={onHumidityThreshold}
          />

          {/* RPM */}
          <RpmDisplay
            fan1Rpm={deviceState?.fan1_rpm ?? null}
            fan2Rpm={deviceState?.fan2_rpm ?? null}
          />

          {/* Schedule */}
          <div className="detail-section">
            <div className="card-title">Schedule</div>
            <div className="schedule-controls">
              <button
                className={deviceState?.weekly_schedule_enabled ? 'active schedule-toggle' : 'schedule-toggle'}
                disabled={disabled}
                onClick={onScheduleEnable}
                aria-pressed={!!deviceState?.weekly_schedule_enabled}
              >
                Schedule: {deviceState?.weekly_schedule_enabled ? 'ON' : 'OFF'}
              </button>
              <button
                className="schedule-edit-btn"
                disabled={disabled}
                onClick={onScheduleEdit}
              >
                Edit…
              </button>
              <button
                className="sync-rtc-btn"
                disabled={disabled}
                onClick={onSyncRtc}
                title="Synchronise device clock to this computer's time"
              >
                Sync RTC
              </button>
            </div>
            {deviceState?.rtc_time && (
              <div className="rtc-display">
                🕐 {deviceState.rtc_time}
                {deviceState.rtc_calendar && <span> · {deviceState.rtc_calendar}</span>}
              </div>
            )}
          </div>

          {/* Scenarios */}
          <div className="detail-section">
            <div className="card-title">Scenarios</div>
            <ScenarioDropdown
              scenarios={scenarios}
              disabled={disabled}
              onCreateNew={onCreateNewScenario}
              onAddToExisting={onAddToExisting}
            />
            <ScenarioManager
              scenarios={scenarios}
              quickSlots={quickSlots}
              onApply={onApplyScenario}
              onDelete={onDeleteScenario}
              onSetQuickSlot={onSetQuickSlot}
              disabled={disabled}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
