import { useState, useEffect } from 'react'
import { api } from '../api.js'
import './ConnectDialog.css'

export default function ConnectDialog({ onConnect, onCancel }) {
  const [discovered, setDiscovered] = useState([])
  const [scanning, setScanning] = useState(false)
  const [ip, setIp] = useState('')
  const [deviceId, setDeviceId] = useState('')
  const [password, setPassword] = useState('1111')
  const [error, setError] = useState(null)
  const [connecting, setConnecting] = useState(false)

  useEffect(() => { scan() }, [])

  async function scan() {
    setScanning(true)
    setError(null)
    try {
      const devices = await api.scanDevices()
      setDiscovered(devices)
    } catch (e) {
      setError(e.message)
    } finally {
      setScanning(false)
    }
  }

  async function connect(connIp, connId, connPw) {
    setConnecting(true)
    setError(null)
    try {
      const state = await api.connect({ ip: connIp, device_id: connId, password: connPw })
      onConnect(state)
    } catch (e) {
      setError(e.message)
      setConnecting(false)
    }
  }

  function handleManualSubmit(e) {
    e.preventDefault()
    connect(ip.trim(), deviceId.trim(), password)
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Connect to device">
      <div className="connect-box card">
        <h2 className="modal-title">Connect to Device</h2>

        <section className="connect-section">
          <div className="section-header">
            <span className="section-title">Discovered</span>
            <button onClick={scan} disabled={scanning} className="rescan-btn">
              {scanning ? 'Scanning…' : 'Rescan'}
            </button>
          </div>
          {discovered.length === 0 && !scanning && (
            <p className="empty-msg">No devices found. Try a manual entry below.</p>
          )}
          <ul className="device-list">
            {discovered.map((d) => (
              <li key={d.ip}>
                <button
                  className="device-item"
                  disabled={connecting}
                  onClick={() => connect(d.ip, d.device_id, '1111')}
                >
                  <span className="dev-name">{d.device_id || d.unit_type_name}</span>
                  <span className="dev-ip">{d.ip}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="connect-section">
          <div className="section-title">Manual Entry</div>
          <form onSubmit={handleManualSubmit} className="manual-form">
            <input
              type="text"
              placeholder="IP address"
              value={ip}
              onChange={(e) => setIp(e.target.value)}
              required
            />
            <input
              type="text"
              placeholder="Device ID"
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Password (default: 1111)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <p className="connect-error">{error}</p>}
            <div className="modal-actions">
              <button type="button" onClick={onCancel} disabled={connecting}>Cancel</button>
              <button type="submit" className="active" disabled={connecting}>
                {connecting ? 'Connecting…' : 'Connect'}
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  )
}
