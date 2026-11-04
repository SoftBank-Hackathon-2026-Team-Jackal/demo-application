export default async function handler(request, response) {
  if (request.method !== 'GET' && request.method !== 'POST') {
    return response.status(405).json({ error: 'method not allowed' });
  }
  const origin = process.env.BACKEND_ORIGIN;
  if (!origin) return response.status(503).json({ error: 'backend not configured' });
  const isPost = request.method === 'POST';
  const limit = Math.min(1000, Math.max(1, Number(request.query?.limit) || 30));
  const url = `${origin.replace(/\/$/, '')}/api/messages${isPost ? '' : `?limit=${limit}`}`;
  const headers = { accept: 'application/json' };
  if (isPost) {
    headers['content-type'] = 'application/json';
    const token = request.headers['x-demo-write-token'];
    if (token) headers['x-demo-write-token'] = token;
  }
  try {
    const upstream = await fetch(url, {
      method: request.method,
      headers,
      ...(isPost ? { body: typeof request.body === 'string' ? request.body : JSON.stringify(request.body ?? {}) } : {}),
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
