// A lightweight per-device identity for commenting — no login wall, just a
// handle stashed in localStorage so the same person's comments look
// consistent across visits. Not an auth system: anyone can pick any handle,
// same trust level the app already gives tips and reactions.
const KEY = "fantasy-media:fan-handle";

function normalize(raw) {
  const trimmed = (raw || "").trim().slice(0, 24);
  if (!trimmed) return null;
  return trimmed.startsWith("@") ? trimmed : `@${trimmed}`;
}

function randomHandle() {
  return `@fan${Math.floor(1000 + Math.random() * 9000)}`;
}

export function getFanHandle() {
  try {
    const stored = localStorage.getItem(KEY);
    if (stored) return stored;
    const fresh = randomHandle();
    localStorage.setItem(KEY, fresh);
    return fresh;
  } catch {
    return randomHandle(); // storage blocked (private mode, etc.) — still usable, just not remembered
  }
}

export function setFanHandle(raw) {
  const clean = normalize(raw);
  if (!clean) return getFanHandle();
  try {
    localStorage.setItem(KEY, clean);
  } catch {
    // storage blocked — the handle still works for this one comment
  }
  return clean;
}
