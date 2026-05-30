import next from 'eslint-config-next'

// eslint-config-next@16 ships a native flat-config array (core-web-vitals +
// typescript + a `.next` ignore). Spread it, add our ignores, then tune
// severities for this codebase.
const eslintConfig = [
  { ignores: ['.next/**', 'node_modules/**', 'next-env.d.ts'] },
  ...next,
  {
    // React Compiler preview rules (react-hooks v7). The compiler is NOT enabled
    // in next.config.mjs, so these are advisory-only here — and they currently
    // mis-fire (e.g. `set-state-in-effect` on app/report/page.tsx, a Suspense
    // wrapper with no state). Keep them visible as warnings instead of letting
    // them block the gate. Revisit if/when we opt into the React Compiler.
    rules: {
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/preserve-manual-memoization': 'warn',
      'react-hooks/refs': 'warn',
      // Off by design: this is a genomics UI full of primes (5′/3′) and ordinary
      // prose contractions ("couldn't"). React escapes text correctly at
      // runtime, so this rule only generates copy-churn without catching bugs.
      'react/no-unescaped-entities': 'off',
    },
  },
]

export default eslintConfig
