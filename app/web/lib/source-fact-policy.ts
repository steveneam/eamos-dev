import type {
  SourceFactPolicyEnvelope,
  SourcePolicyAction,
} from './backend'

export function sourceFactActionAllowed(
  fact: SourceFactPolicyEnvelope,
  action: SourcePolicyAction,
): boolean {
  const policyDecisions = fact.policy_decisions ?? []
  if (policyDecisions.length > 0) {
    const decisions = policyDecisions.filter(
      (decision) => decision.action === action,
    )
    return (
      decisions.length > 0 &&
      decisions.every((decision) => decision.outcome === 'allowed')
    )
  }

  if (action === 'public_serialize') {
    return fact.public_serialization_allowed === true
  }
  if (action === 'product_export') return fact.export_allowed === true
  if (action === 'cache') return fact.cache_allowed === true
  return false
}

export function productExportFacts<T extends SourceFactPolicyEnvelope>(
  facts: readonly T[] | null | undefined,
): T[] {
  return (facts ?? []).filter((fact) =>
    sourceFactActionAllowed(fact, 'product_export'),
  )
}
