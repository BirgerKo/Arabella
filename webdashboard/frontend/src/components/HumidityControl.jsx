import { useState, useEffect } from 'react'
import './HumidityControl.css'

const SENSOR_MODES = [
  { value: 0, label: 'Off' },
  { value: 1, label: 'On' },
  { value: 2, label: 'Invert' },
]

export default function HumidityControl({
  humiditySensor,
  humidityThreshold,
  currentHumidity,
  disabled,
  onSensorChange,
  onThresholdChange,
}) {
  const serverThreshold = humidityThreshold ?? 60
  const [sliderVal, setSliderVal] = useState(serverThreshold)

  // Keep slider in sync when server state changes
  useEffect(() => { setSliderVal(serverThreshold) }, [serverThreshold])

  function handleThresholdCommit(e) {
    onThresholdChange(Number(e.target.value))
  }

  return (
    <div className="card">
      <div className="card-title">Humidity</div>
      <div className="humidity-sensor-row">
        {SENSOR_MODES.map(({ value, label }) => (
          <button
            key={value}
            className={humiditySensor === value ? 'active' : ''}
            disabled={disabled}
            onClick={() => onSensorChange(value)}
            aria-pressed={humiditySensor === value}
          >
            {label}
          </button>
        ))}
      </div>
      {humiditySensor !== 0 && (
        <div className="humidity-threshold-row">
          <label>Threshold: {sliderVal}%</label>
          <input
            type="range"
            min={40}
            max={80}
            value={sliderVal}
            disabled={disabled}
            onChange={(e) => setSliderVal(Number(e.target.value))}
            onMouseUp={handleThresholdCommit}
            onTouchEnd={handleThresholdCommit}
            aria-label="Humidity threshold"
          />
        </div>
      )}
      {currentHumidity != null && (
        <div className="humidity-current">
          Current: <span className="humidity-value">{currentHumidity}%</span>
        </div>
      )}
    </div>
  )
}
