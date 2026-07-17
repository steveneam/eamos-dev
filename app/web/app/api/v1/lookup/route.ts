const API_TARGET = (process.env.API_PROXY_TARGET ?? 'http://localhost:8532').replace(/\/$/, '')

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function POST(request: Request): Promise<Response> {
  const body = await request.text()

  try {
    const upstream = await fetch(`${API_TARGET}/api/v1/lookup`, {
      method: 'POST',
      headers: {
        accept: request.headers.get('accept') ?? 'application/json',
        'content-type': request.headers.get('content-type') ?? 'application/json',
      },
      body,
      signal: AbortSignal.timeout(120_000),
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
    const message = error instanceof Error ? error.message : 'lookup proxy failed'
    return new Response(`Lookup proxy failed: ${message}`, {
      status: 502,
      headers: {
        'cache-control': 'no-store',
        'content-type': 'text/plain; charset=utf-8',
      },
    })
  }
}
