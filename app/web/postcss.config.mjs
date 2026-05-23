// Tailwind v4 via the PostCSS plugin (Next.js integration). The Vite app uses
// `@tailwindcss/vite`; the CSS itself (`@import "tailwindcss"` + `@theme inline`
// + `:root` tokens in app/globals.css) is identical.
const config = {
  plugins: {
    '@tailwindcss/postcss': {},
  },
}

export default config
