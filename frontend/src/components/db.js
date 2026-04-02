// ── Simple session database using localStorage ──
// Each session: { id, title, repoUrl, messages: [{sender, text, ts}], createdAt, updatedAt }

const DB_KEY = "revai_sessions";

function loadAll() {
  try {
    return JSON.parse(localStorage.getItem(DB_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveAll(sessions) {
  localStorage.setItem(DB_KEY, JSON.stringify(sessions));
}

export function getAllSessions() {
  return loadAll().sort((a, b) => b.updatedAt - a.updatedAt);
}

export function getSession(id) {
  return loadAll().find(s => s.id === id) || null;
}

export function createSession(repoUrl = "") {
  const now = Date.now();
  const session = {
    id: now.toString(),
    title: repoUrl ? shortenUrl(repoUrl) : "New chat",
    repoUrl,
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
  const all = loadAll();
  all.unshift(session);
  saveAll(all);
  return session;
}

export function updateSession(id, patch) {
  const all = loadAll();
  const idx = all.findIndex(s => s.id === id);
  if (idx === -1) return null;
  all[idx] = { ...all[idx], ...patch, updatedAt: Date.now() };
  saveAll(all);
  return all[idx];
}

export function appendMessage(sessionId, message) {
  const all = loadAll();
  const idx = all.findIndex(s => s.id === sessionId);
  if (idx === -1) return;
  all[idx].messages.push({ ...message, ts: Date.now() });
  all[idx].updatedAt = Date.now();
  // Auto-title from first user message
  if (all[idx].messages.length === 1 && message.sender === "user") {
    all[idx].title = message.text.slice(0, 40) + (message.text.length > 40 ? "…" : "");
  }
  saveAll(all);
}

export function deleteSession(id) {
  saveAll(loadAll().filter(s => s.id !== id));
}

function shortenUrl(url) {
  try {
    const parts = url.replace("https://github.com/", "").split("/");
    return parts.slice(0, 2).join("/");
  } catch {
    return url.slice(0, 35);
  }
}