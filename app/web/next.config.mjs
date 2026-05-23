// Backend stays the FastAPI contract authority (see plans/v2-nextjs-migration/
// design.md). The browser calls same-origin `/api/*`; this rewrite proxies to
// the FastAPI dev server, mirroring the Vite dev proxy (`/api → :8000`) and
// sidestepping CORS. Override the backend origin with API_PROXY_TARGET.
const API_TARGET = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${API_TARGET}/api/:path*` }]
  },
}

export default nextConfig
