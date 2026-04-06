import './DeviceHeader.css'

export default function DeviceHeader({ deviceId, ip, onSwitchClick, onDetailsClick }) {
  const connected = !!deviceId
  return (
    <header className="device-header">
      <div className="device-info">
        <span className="device-name" title={ip || ''}>
          {deviceId || '—'}
        </span>
      </div>
      <button
        className="details-btn"
        onClick={onDetailsClick}
        disabled={!connected}
      >
        Details…
      </button>
      <button className="switch-btn" onClick={onSwitchClick}>
        Switch…
      </button>
    </header>
  )
}
