const API_TARGET = (process.env.API_PROXY_TARGET ?? 'http://localhost:8532').replace(/\/$/, '')

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

interface RouteContext {
  params: Promise<{ query_id?: string[] }>
}

function upstreamPath(parts: string[] | undefined): string {
  const encoded = (parts ?? []).map((part) => encodeURIComponent(part)).join('/')
  return `${API_TARGET}/api/v1/library/views/${encoded}`
}

async function proxyViewRequest(request: Request, context: RouteContext): Promise<Response> {
  const { query_id: queryId } = await context.params
  try {
    const upstream = await fetch(upstreamPath(queryId), {
      method: request.method,
      headers: { accept: request.headers.get('accept') ?? 'application/json' },
      signal: AbortSignal.timeout(30_000),
    })
    const text = await upstream.text()
    return new Response(text, {
      status: upstream.status,
      headers: {
        'cache-control': 'no-store',
        'content-type': upstream.headers.get('content-type') ?? 'application/json',
      },
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'view-count proxy failed'
    return new Response(`View-count proxy failed: ${message}`, {
      status: 502,
      headers: {
        'cache-control': 'no-store',
        'content-type': 'text/plain; charset=utf-8',
      },
    })
  }
}

export function GET(request: Request, context: RouteContext): Promise<Response> {
  return proxyViewRequest(request, context)
}

export function POST(request: Request, context: RouteContext): Promise<Response> {
  return proxyViewRequest(request, context)
}
