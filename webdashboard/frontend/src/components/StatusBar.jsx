import './StatusBar.css'

export default function StatusBar({ connected, deviceId, ip }) {
  const ledColor = connected ? 'var(--success)' : 'var(--danger)'
  const label    = connected ? 'Connected' : 'Disconnected'

  return (
    <footer className="status-bar">
      <span
        className="status-led"
        style={{ background: ledColor, boxShadow: connected ? `0 0 6px ${ledColor}` : 'none' }}
        aria-label={label}
      />
      <span className="status-label">{label}</span>
      {connected && (
        <>
          <span className="status-sep">|</span>
          <span className="status-id">{deviceId}</span>
          <span className="status-sep">|</span>
          <span className="status-ip">{ip}</span>
        </>
      )}
    </footer>
  )
}
