export type ZoomStep = -2 | -1 | 0 | 1 | 2

export interface SequenceZoomSetting {
  step: ZoomStep
  label: string
  basesPerRow: number
  baseW: number
}

export const DEFAULT_ZOOM_STEP: ZoomStep = 0
export const DEFAULT_BASES_PER_ROW = 102

export const ZOOM_SETTINGS: readonly SequenceZoomSetting[] = [
  { step: -2, label: 'Zoom -2', basesPerRow: 150, baseW: 8 },
  { step: -1, label: 'Zoom -1', basesPerRow: 126, baseW: 10 },
  { step: 0, label: 'Default', basesPerRow: DEFAULT_BASES_PER_ROW, baseW: 12 },
  { step: 1, label: 'Zoom +1', basesPerRow: 78, baseW: 16 },
  { step: 2, label: 'Zoom +2', basesPerRow: 54, baseW: 20 },
]

export const ZOOM_SETTINGS_BY_STEP: Record<ZoomStep, SequenceZoomSetting> =
  ZOOM_SETTINGS.reduce(
    (acc, setting) => {
      acc[setting.step] = setting
      return acc
    },
    {} as Record<ZoomStep, SequenceZoomSetting>,
  )
