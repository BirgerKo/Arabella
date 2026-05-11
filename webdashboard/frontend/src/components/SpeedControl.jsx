import { useState, useEffect } from 'react'
import './SpeedControl.css'

const PRESETS = [1, 2, 3]

export default function SpeedControl({ speed, manualSpeed, disabled, onSpeedChange }) {
  const isManual = speed === 255
  const [sliderVal, setSliderVal] = useState(manualSpeed ?? 128)

  useEffect(() => {
    if (manualSpeed != null) setSliderVal(manualSpeed)
  }, [manualSpeed])

  function handlePreset(preset) {
    onSpeedChange(preset)
  }

  function handleSliderChange(e) {
    setSliderVal(Number(e.target.value))
  }

  function handleSliderCommit(e) {
    onSpeedChange(Number(e.target.value))
  }

  function handleManualMode() {
    onSpeedChange(sliderVal)
  }

  return (
    <div className="card">
      <div className="card-title">Speed</div>
      <div className="speed-presets">
        {PRESETS.map((p) => (
          <button
            key={p}
            className={speed === p ? 'active' : ''}
            disabled={disabled}
            onClick={() => handlePreset(p)}
            aria-pressed={speed === p}
          >
            {p}
          </button>
        ))}
        <button
          className={isManual ? 'active' : ''}
          disabled={disabled}
          onClick={handleManualMode}
          aria-pressed={isManual}
        >
          Manual
        </button>
      </div>
      {isManual && (
        <div className="speed-manual">
          <input
            type="range"
            min={0}
            max={255}
            value={sliderVal}
            disabled={disabled}
            onChange={handleSliderChange}
            onMouseUp={handleSliderCommit}
            onTouchEnd={handleSliderCommit}
            aria-label="Manual speed"
          />
          <span className="speed-value">{sliderVal}</span>
        </div>
      )}
    </div>
  )
}
