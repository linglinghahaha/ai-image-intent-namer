// Minimal backend health + endpoints smoke check
const BASE = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch { json = text; }
  return { ok: res.ok, status: res.status, body: json };
}

(async () => {
  const health = await get('/api/v1/health');
  console.log('health', health);
  const profiles = await get('/api/v1/profiles');
  console.log('profiles', { ok: profiles.ok, status: profiles.status, keys: Object.keys(profiles.body || {}) });
  const templates = await get('/api/v1/templates');
  console.log('templates', { ok: templates.ok, status: templates.status, keys: Object.keys(templates.body || {}) });
  if (!health.ok) process.exit(1);
})();

