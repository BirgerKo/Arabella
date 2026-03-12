import './PowerButton.css'

export default function PowerButton({ isOn, disabled, onClick }) {
  return (
    <div className="power-btn-wrap">
      <button
        className={`power-btn ${isOn ? 'on' : 'off'}`}
        onClick={onClick}
        disabled={disabled}
        aria-pressed={isOn}
        aria-label={isOn ? 'Turn off' : 'Turn on'}
        title={isOn ? 'Turn off' : 'Turn on'}
      >
        {/* Power symbol SVG */}
        <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round">
          <path d="M12 3v9" />
          <path d="M5.636 5.636a9 9 0 1 0 12.728 0" />
        </svg>
      </button>
      <span className="power-label">{isOn ? 'ON' : 'OFF'}</span>
    </div>
  )
}
