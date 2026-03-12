import { useReducer, useEffect, useCallback } from 'react'
import { api, openWebSocket } from './api.js'
import DeviceHeader from './components/DeviceHeader.jsx'
import PowerButton from './components/PowerButton.jsx'
import SpeedControl from './components/SpeedControl.jsx'
import ModeSelector from './components/ModeSelector.jsx'
import QuickScenarios from './components/QuickScenarios.jsx'
import ScenarioManager from './components/ScenarioManager.jsx'
import SaveScenarioModal from './components/SaveScenarioModal.jsx'
import ConnectDialog from './components/ConnectDialog.jsx'
import StatusBar from './components/StatusBar.jsx'
import './App.css'

// ── Reducer ───────────────────────────────────────────────────────────────────

const INITIAL = {
  deviceState: null,   // DeviceStateResponse | null
  scenarios:   [],
  quickSlots:  [null, null, null],
  showConnect: true,
  showSave:    false,
  busy:        false,
  wsConnected: false,
}

function reducer(state, action) {
  switch (action.type) {
    case 'DEVICE_STATE':
      return { ...state, deviceState: action.payload, showConnect: false }
    case 'SCENARIOS':
      return { ...state, scenarios: action.payload }
    case 'QUICK_SLOTS':
      return { ...state, quickSlots: action.payload }
    case 'SHOW_CONNECT':
      return { ...state, showConnect: true }
    case 'HIDE_CONNECT':
      return { ...state, showConnect: false }
    case 'SHOW_SAVE':
      return { ...state, showSave: true }
    case 'HIDE_SAVE':
      return { ...state, showSave: false }
    case 'BUSY':
      return { ...state, busy: action.payload }
    case 'WS_CONNECTED':
      return { ...state, wsConnected: action.payload }
    default:
      return state
  }
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function App() {
  const [state, dispatch] = useReducer(reducer, INITIAL)
  const { deviceState, scenarios, quickSlots, showConnect, showSave, busy } = state

  // Load initial state and scenarios on mount
  useEffect(() => {
    api.getState()
      .then((s) => dispatch({ type: 'DEVICE_STATE', payload: s }))
      .catch(() => dispatch({ type: 'SHOW_CONNECT' }))

    api.listScenarios()
      .then((list) => dispatch({ type: 'SCENARIOS', payload: list }))
      .catch(() => {})
  }, [])

  // Load quick slots whenever connected device changes
  useEffect(() => {
    if (!deviceState?.device_id) return
    api.getQuickSlots(deviceState.device_id)
      .then((r) => dispatch({ type: 'QUICK_SLOTS', payload: r.slots }))
      .catch(() => {})
  }, [deviceState?.device_id])

  // WebSocket for real-time state updates
  useEffect(() => {
    let ws = openWebSocket(
      (msg) => {
        if (msg.type === 'state') dispatch({ type: 'DEVICE_STATE', payload: msg.data })
      },
      () => dispatch({ type: 'WS_CONNECTED', payload: false }),
    )
    dispatch({ type: 'WS_CONNECTED', payload: true })
    return () => ws.close()
  }, [])

  // ── Command helpers ─────────────────────────────────────────────────────────

  async function run(fn) {
    dispatch({ type: 'BUSY', payload: true })
    try { await fn() } finally { dispatch({ type: 'BUSY', payload: false }) }
  }

  const handlePower    = useCallback(() => run(() => api.setPower(!deviceState?.power)), [deviceState])
  const handleSpeed    = useCallback((s) => run(() => api.setSpeed(s)), [])
  const handleMode     = useCallback((m) => run(() => api.setMode(m)), [])
  const handleBoost    = useCallback(() => run(() => api.setBoost(!deviceState?.boost_active)), [deviceState])
  const handleApply    = useCallback((name) => run(() => api.applyScenario(name)), [])
  const handleDelete   = useCallback(async (name) => {
    await api.deleteScenario(name)
    const list = await api.listScenarios()
    dispatch({ type: 'SCENARIOS', payload: list })
  }, [])

  const handleConnect = useCallback((newState) => {
    dispatch({ type: 'DEVICE_STATE', payload: newState })
  }, [])

  const handleSaveScenario = useCallback(async (name) => {
    await api.saveScenario(name)
    const list = await api.listScenarios()
    dispatch({ type: 'SCENARIOS', payload: list })
    dispatch({ type: 'HIDE_SAVE' })
  }, [])

  const handleSetQuickSlots = useCallback(async (slots) => {
    if (!deviceState?.device_id) return
    const r = await api.setQuickSlots(deviceState.device_id, slots)
    dispatch({ type: 'QUICK_SLOTS', payload: r.slots })
  }, [deviceState?.device_id])

  const connected = !!deviceState?.connected
  const disabled  = !connected || busy

  return (
    <div className="app-shell">
      {showConnect && (
        <ConnectDialog
          onConnect={handleConnect}
          onCancel={connected ? () => dispatch({ type: 'HIDE_CONNECT' }) : undefined}
        />
      )}
      {showSave && (
        <SaveScenarioModal
          onSave={handleSaveScenario}
          onCancel={() => dispatch({ type: 'HIDE_SAVE' })}
        />
      )}

      <div className="app-content">
        <DeviceHeader
          deviceId={deviceState?.device_id}
          ip={deviceState?.ip}
          onSwitchClick={() => dispatch({ type: 'SHOW_CONNECT' })}
        />

        <div className="two-col">
          {/* LEFT: controls */}
          <div className="col-left">
            <PowerButton
              isOn={!!deviceState?.power}
              disabled={disabled}
              onClick={handlePower}
            />
            <SpeedControl
              speed={deviceState?.speed ?? null}
              manualSpeed={deviceState?.manual_speed ?? null}
              disabled={disabled}
              onSpeedChange={handleSpeed}
            />
            <ModeSelector
              mode={deviceState?.operation_mode ?? null}
              disabled={disabled}
              onModeChange={handleMode}
            />
            <div className="boost-row">
              <button
                className={deviceState?.boost_active ? 'active boost-btn' : 'boost-btn'}
                disabled={disabled}
                onClick={handleBoost}
                aria-pressed={!!deviceState?.boost_active}
                style={deviceState?.boost_active ? { borderColor: 'var(--warning)', background: 'color-mix(in srgb, var(--warning) 15%, var(--surface2))' } : {}}
              >
                Boost: {deviceState?.boost_active ? 'ON' : 'OFF'}
              </button>
            </div>
            <div className="quick-row">
              <div className="card-title">Quick scenarios</div>
              <QuickScenarios
                slots={quickSlots}
                disabled={disabled}
                onApply={handleApply}
              />
            </div>
            <button
              className="save-scenario-btn"
              disabled={disabled}
              onClick={() => dispatch({ type: 'SHOW_SAVE' })}
            >
              Save as Scenario
            </button>
          </div>

          {/* RIGHT: scenario manager */}
          <div className="col-right">
            <ScenarioManager
              scenarios={scenarios}
              quickSlots={quickSlots}
              onApply={handleApply}
              onDelete={handleDelete}
              onSetQuickSlot={handleSetQuickSlots}
              disabled={disabled}
            />
          </div>
        </div>
      </div>

      <StatusBar
        connected={connected}
        deviceId={deviceState?.device_id}
        ip={deviceState?.ip}
      />
    </div>
  )
}
