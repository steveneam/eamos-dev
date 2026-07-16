const ACCESS_POLICY_WARNING_RE =
  /(?:license|commercial|serialization|(?:^|_)(?:launch|gate)(?:_|$))/i

/** Keep operational/data warnings visible without resurfacing retired access policy. */
export function visibleProductWarnings(
  warnings: readonly string[] | null | undefined,
): string[] {
  return (warnings ?? []).filter(
    (warning) => !ACCESS_POLICY_WARNING_RE.test(warning),
  )
}
