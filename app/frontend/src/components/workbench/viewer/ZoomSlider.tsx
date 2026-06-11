import { ZOOM_SETTINGS, type ZoomStep } from './zoom-config'

interface ZoomSliderProps {
  zoomStep: ZoomStep
  onZoomStep: (step: ZoomStep) => void
}

export function ZoomSlider({ zoomStep, onZoomStep }: ZoomSliderProps) {
  return (
    <div className="sv-zoombar">
      <div className="zoom-slider" role="group" aria-label="Sequence row zoom">
        {ZOOM_SETTINGS.map((setting) => (
          <button
            key={setting.step}
            type="button"
            className={`zoom-step${setting.step === zoomStep ? ' active' : ''}`}
            aria-pressed={setting.step === zoomStep}
            aria-label={`${setting.label}, ${setting.basesPerRow} nucleotides per row`}
            title={`${setting.label}: ${setting.basesPerRow} nt/row`}
            onClick={() => onZoomStep(setting.step)}
          >
            {setting.step === 0
              ? 'Default'
              : setting.step > 0
                ? `+${setting.step}`
                : setting.step}
          </button>
        ))}
      </div>
    </div>
  )
}
