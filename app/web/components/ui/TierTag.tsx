// The one Free/Pro tier tag — a filled pill that marks whether a predictor /
// engine / tool is on the free tier or is a premium ("Pro") engine. Extracted
// so the report stops drawing this in two dialects (CalibratedInSilicoTable's
// filled TierTag vs LossOfFunctionBlock's bare coloured-text tier suffix);
// the sweep's "one evidence vocabulary" theme — standardise on the filled pill.
// Colour is the warn (Pro) / teal (Free) tint set, never the --cls-* verdict ramp.

export function TierTag({ tier }: { tier: 'Free' | 'Pro' }) {
  const isPro = tier === 'Pro'
  return (
    <span
      title={
        isPro
          ? 'Premium engine — shown in full on this account; gated on the free tier at launch.'
          : 'Included on the free tier.'
      }
      style={{
        fontSize: 9.5,
        fontWeight: 700,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        padding: '0.5px 5px',
        borderRadius: 999,
        border: `0.5px solid ${isPro ? 'var(--warn-bdr)' : 'var(--teal-bdr)'}`,
        background: isPro ? 'var(--warn-tint)' : 'var(--teal-tint)',
        color: isPro ? 'var(--warn-text)' : 'var(--teal-deep)',
        whiteSpace: 'nowrap',
      }}
    >
      {tier}
    </span>
  )
}
