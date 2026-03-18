import './RpmDisplay.css'

export default function RpmDisplay({ fan1Rpm, fan2Rpm }) {
  return (
    <div className="card rpm-card">
      <div className="card-title">Fan RPM</div>
      <div className="rpm-row">
        <span className="rpm-label">Fan 1</span>
        <span className="rpm-value">{fan1Rpm ?? '—'}</span>
      </div>
      <div className="rpm-row">
        <span className="rpm-label">Fan 2</span>
        <span className="rpm-value">{fan2Rpm ?? '—'}</span>
      </div>
    </div>
  )
}
