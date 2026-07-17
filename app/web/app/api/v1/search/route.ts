const API_TARGET = (process.env.API_PROXY_TARGET ?? 'http://localhost:8532').replace(/\/$/, '')

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

function proxyHeaders(request: Request): Headers {
  const headers = new Headers({
    accept: request.headers.get('accept') ?? 'application/json',
  })
  const authorization = request.headers.get('authorization')
  if (authorization) headers.set('authorization', authorization)
  return headers
}

function responseHeaders(upstream: Response): Headers {
  const headers = new Headers({
    'cache-control': 'no-store',
    'content-type': upstream.headers.get('content-type') ?? 'application/json',
  })
  const retryAfter = upstream.headers.get('retry-after')
  const authenticate = upstream.headers.get('www-authenticate')
  if (retryAfter) headers.set('retry-after', retryAfter)
  if (authenticate) headers.set('www-authenticate', authenticate)
  return headers
}

export async function GET(request: Request): Promise<Response> {
  const incoming = new URL(request.url)
  const upstreamUrl = `${API_TARGET}/api/v1/search${incoming.search}`

  try {
    const upstream = await fetch(upstreamUrl, {
      method: 'GET',
      headers: proxyHeaders(request),
      signal: AbortSignal.timeout(30_000),
    })
    const body = await upstream.arrayBuffer()
    return new Response(body, {
      status: upstream.status,
      headers: responseHeaders(upstream),
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'search proxy failed'
    return new Response(`Search proxy failed: ${message}`, {
      status: 502,
      headers: {
        'cache-control': 'no-store',
        'content-type': 'text/plain; charset=utf-8',
      },
    })
  }
}
