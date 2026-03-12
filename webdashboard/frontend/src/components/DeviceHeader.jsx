import './DeviceHeader.css'

export default function DeviceHeader({ deviceId, ip, onSwitchClick }) {
  return (
    <header className="device-header">
      <div className="device-info">
        <span className="device-name">{deviceId || '—'}</span>
        {ip && <span className="device-ip">{ip}</span>}
      </div>
      <button className="switch-btn" onClick={onSwitchClick}>
        Switch…
      </button>
    </header>
  )
}
