export default async function handler(request, response) {
  if (request.method !== 'GET') return response.status(405).json({ error: 'method not allowed' });
  const origin = process.env.BACKEND_ORIGIN;
  if (!origin) return response.status(503).json({ error: 'backend not configured' });
  const limit = Math.min(1000, Math.max(1, Number(request.query.limit) || 30));
  try {
    const upstream = await fetch(`${origin.replace(/\/$/, '')}/api/messages?limit=${limit}`, {
      headers: { accept: 'application/json' },
      signal: AbortSignal.timeout(8000),
    });
    const body = await upstream.text();
    response.setHeader('Cache-Control', 'no-store');
    response.setHeader('Content-Type', 'application/json');
    return response.status(upstream.status).send(body);
  } catch {
    return response.status(502).json({ error: 'backend unavailable' });
  }
}
