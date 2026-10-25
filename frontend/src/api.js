// Thin wrappers around the FastAPI endpoints. Every call accepts an
// AbortSignal so stale requests can be cancelled when the user keeps typing.

async function request(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`Server answered ${res.status}`);
  return res.json();
}

export const getHealth = (signal) => request("/api/health", { signal });

export const getStarters = (signal) => request("/api/starters", { signal });

export const getSuggestions = (q, signal) =>
  request(`/api/suggest?q=${encodeURIComponent(q)}`, { signal });

export const getRecommendations = (body, signal) =>
  request("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
