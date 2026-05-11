import { useReducer, useEffect, useCallback, useRef, useState } from 'react'
import { api, openWebSocket } from './api.js'
import DeviceHeader from './components/DeviceHeader.jsx'
import PowerButton from './components/PowerButton.jsx'
import SpeedControl from './components/SpeedControl.jsx'
import ModeSelector from './components/ModeSelector.jsx'
import QuickScenarios from './components/QuickScenarios.jsx'
import SaveScenarioModal from './components/SaveScenarioModal.jsx'
import ConnectDialog from './components/ConnectDialog.jsx'
import StatusBar from './components/StatusBar.jsx'
import ScheduleEditor from './components/ScheduleEditor.jsx'
import FanDetailsModal from './components/FanDetailsModal.jsx'
import './App.css'

// ── Reducer ───────────────────────────────────────────────────────────────────

const INITIAL = {
  deviceState:     null,   // DeviceStateResponse | null
  scenarios:       [],
  quickSlots:      [null, null, null],
  schedulePeriods: null,   // null = not loaded; array = loaded from device
  showConnect:     true,
  showSave:        false,
  showSchedule:    false,
  showDetails:     false,
  busy:            false,
  wsConnected:     false,
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
    case 'SHOW_SCHEDULE':
      return { ...state, showSchedule: true, schedulePeriods: null }
    case 'SCHEDULE_LOADED':
      return { ...state, schedulePeriods: action.payload }
    case 'HIDE_SCHEDULE':
      return { ...state, showSchedule: false, schedulePeriods: null }
    case 'SHOW_DETAILS':
      return { ...state, showDetails: true }
    case 'HIDE_DETAILS':
      return { ...state, showDetails: false }
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
  const { deviceState, scenarios, quickSlots, schedulePeriods, showConnect, showSave, showSchedule, showDetails, busy } = state

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
    try { await fn() }
    catch (e) { console.error('Command failed:', e) }
    finally { dispatch({ type: 'BUSY', payload: false }) }
  }

  const handlePower             = useCallback(() => run(() => api.setPower(!deviceState?.power)), [deviceState])
  const handleSpeed             = useCallback((s) => run(() => api.setSpeed(s)), [])
  const handleMode              = useCallback((m) => run(() => api.setMode(m)), [])
  const handleBoost             = useCallback(() => run(() => api.setBoost(!deviceState?.boost_active)), [deviceState])
  const handleHumiditySensor    = useCallback((s) => run(() => api.setHumiditySensor(s)), [])
  const handleHumidityThreshold = useCallback((t) => run(() => api.setHumidityThreshold(t)), [])
  const handleApply             = useCallback((name) => run(() => api.applyScenario(name)), [])
  const handleDelete            = useCallback(async (name) => {
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

  const handleAddToScenario = useCallback(async (name) => {
    await run(() => api.addFanToScenario(name))
    const list = await api.listScenarios()
    dispatch({ type: 'SCENARIOS', payload: list })
  }, [])

  const handleSetQuickSlots = useCallback(async (slots) => {
    if (!deviceState?.device_id) return
    const r = await api.setQuickSlots(deviceState.device_id, slots)
    dispatch({ type: 'QUICK_SLOTS', payload: r.slots })
  }, [deviceState?.device_id])

  const handleScheduleEnable = useCallback(
    () => run(() => api.enableSchedule(!deviceState?.weekly_schedule_enabled)),
    [deviceState?.weekly_schedule_enabled],
  )

  const handleSetSchedulePeriod = useCallback(
    (day, period, speed, end_h, end_m) => api.setSchedulePeriod(day, period, speed, end_h, end_m),
    [],
  )

  const handleSyncRtc = useCallback(() => run(() => api.syncRtc()), [])

  const handleScheduleEdit = useCallback(async () => {
    dispatch({ type: 'SHOW_SCHEDULE' })
    try {
      const data = await api.getSchedule()
      dispatch({ type: 'SCHEDULE_LOADED', payload: data.periods })
    } catch (e) {
      console.error('Failed to load schedule:', e)
    }
  }, [])

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
      {showDetails && (
        <FanDetailsModal
          deviceState={deviceState}
          disabled={disabled}
          scenarios={scenarios}
          quickSlots={quickSlots}
          onBoost={handleBoost}
          onHumiditySensor={handleHumiditySensor}
          onHumidityThreshold={handleHumidityThreshold}
          onScheduleEnable={handleScheduleEnable}
          onScheduleEdit={handleScheduleEdit}
          onSyncRtc={handleSyncRtc}
          onCreateNewScenario={() => dispatch({ type: 'SHOW_SAVE' })}
          onAddToExisting={handleAddToScenario}
          onApplyScenario={handleApply}
          onDeleteScenario={handleDelete}
          onSetQuickSlot={handleSetQuickSlots}
          onClose={() => dispatch({ type: 'HIDE_DETAILS' })}
        />
      )}
      {showSave && (
        <SaveScenarioModal
          onSave={handleSaveScenario}
          onCancel={() => dispatch({ type: 'HIDE_SAVE' })}
        />
      )}
      {showSchedule && (
        <ScheduleEditor
          initialPeriods={schedulePeriods}
          onApply={handleSetSchedulePeriod}
          onClose={() => dispatch({ type: 'HIDE_SCHEDULE' })}
          busy={busy}
        />
      )}

      <div className="app-content">
        <DeviceHeader
          deviceId={deviceState?.device_id}
          ip={deviceState?.ip}
          onSwitchClick={() => dispatch({ type: 'SHOW_CONNECT' })}
          onDetailsClick={() => dispatch({ type: 'SHOW_DETAILS' })}
        />

        <div className="col-main">
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
            scheduleEnabled={deviceState?.weekly_schedule_enabled ?? false}
            onScheduleToggle={handleScheduleEnable}
          />
          <div className="quick-row">
            <div className="card-title">Quick scenarios</div>
            <QuickScenarios
              slots={quickSlots}
              disabled={disabled}
              onApply={handleApply}
            />
          </div>
          {connected && (
            <div className="device-info-row">
              <span className="device-info-id">{deviceState?.device_id}</span>
              {deviceState?.ip && (
                <span className="device-info-ip">{deviceState.ip}</span>
              )}
            </div>
          )}
        </div>
      </div>

      <StatusBar
        connected={connected}
        deviceId={deviceState?.device_id}
        ip={deviceState?.ip}
        alarmStatus={deviceState?.alarm_status}
        alarmName={deviceState?.alarm_name}
      />
    </div>
  )
}
