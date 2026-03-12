/**
 * API client — wraps fetch for REST endpoints and manages the WebSocket
 * connection for real-time state updates.
 */

const BASE = '/api'

async function request(method, path, body) {
  const opts = {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  }
  const res = await fetch(`${BASE}${path}`, opts)
  if (res.status === 204) return null
  const json = await res.json()
  if (!res.ok) throw new Error(json.detail ?? res.statusText)
  return json
}

export const api = {
  getState:      ()           => request('GET',    '/state'),
  scanDevices:   ()           => request('GET',    '/devices'),
  connect:       (body)       => request('POST',   '/connect', body),
  disconnect:    ()           => request('DELETE', '/connect'),

  setPower:  (on)             => request('POST', '/command/power',  { on }),
  setSpeed:  (speed)          => request('POST', '/command/speed',  { speed }),
  setMode:   (mode)           => request('POST', '/command/mode',   { mode }),
  setBoost:  (on)             => request('POST', '/command/boost',  { on }),

  listScenarios:   ()           => request('GET',    '/scenarios'),
  saveScenario:    (name)       => request('POST',   '/scenarios',       { name }),
  updateScenario:  (name, body) => request('PUT',    `/scenarios/${encodeURIComponent(name)}`, body),
  deleteScenario:  (name)       => request('DELETE', `/scenarios/${encodeURIComponent(name)}`),
  applyScenario:   (name)       => request('POST',   `/scenarios/${encodeURIComponent(name)}/apply`),
  getQuickSlots:   (deviceId)   => request('GET',    `/scenarios/quick-slots/${encodeURIComponent(deviceId)}`),
  setQuickSlots:   (deviceId, slots) =>
    request('PUT', `/scenarios/quick-slots/${encodeURIComponent(deviceId)}`, { slots }),
}

/** Open a WebSocket and call onMessage(parsedJson) on each server push. */
export function openWebSocket(onMessage, onClose) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${proto}://${location.host}/ws`)
  ws.onmessage = (ev) => {
    try { onMessage(JSON.parse(ev.data)) } catch { /* ignore parse errors */ }
  }
  ws.onclose = () => onClose?.()
  return ws
}
