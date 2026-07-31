// Thin wrapper around the HTTP API.

async function request(url, options) {
  const res = await fetch(url, options);
  let data = {};
  try {
    data = await res.json();
  } catch (err) {
    data = { ok: false, error: `Invalid server response (${res.status})` };
  }
  return data;
}

export function fetchState(gameId) {
  return request(`/api/state?game_id=${encodeURIComponent(gameId)}`);
}

export function sendAction(gameId, player, action) {
  return request("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ game_id: gameId, player, action })
  });
}

export function fetchUnitTypes() {
  return request("/api/unit_types");
}
