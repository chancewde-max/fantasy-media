import { supabase, LEAGUE_ID } from "./supabaseClient";

// VAPID public keys are meant to be public (they identify the app to the
// push service, they don't authenticate anything) — safe to bake in like the
// Supabase anon key. Must match VAPID_PRIVATE_KEY on the bot.
const VAPID_PUBLIC_KEY =
  import.meta.env.VITE_VAPID_PUBLIC_KEY ||
  "BDh5hs8dmmDwHG4KaMfcS8MtlVkak_Oh-t7yUe2I3fS2q5ZvLz6TKnwV7-S0aR6lNdtysU6rmWtJzILKSyUIk44";

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export function pushSupported() {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export async function getPushState() {
  if (!pushSupported()) return "unsupported";
  if (Notification.permission === "denied") return "denied";
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = reg ? await reg.pushManager.getSubscription() : null;
  return sub ? "subscribed" : "unsubscribed";
}

function withTimeout(promise, ms, step) {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`Timed out at: ${step}`)), ms)
    ),
  ]);
}

// Every step is labeled so a failure says exactly where it happened —
// "permission", "service worker", "subscribe", "save" all fail in
// different, non-obvious ways (especially on iOS), and a bare error message
// isn't enough to tell them apart from the outside.
export async function enablePush() {
  if (!pushSupported()) throw new Error("Push not supported on this browser.");

  let permission;
  try {
    permission = await Notification.requestPermission();
  } catch (e) {
    throw new Error(`[permission] ${e.message || e}`);
  }
  if (permission !== "granted") throw new Error(`[permission] not granted (${permission})`);

  let reg;
  try {
    reg = await withTimeout(navigator.serviceWorker.register("/sw.js"), 10000, "service worker register");
    await withTimeout(navigator.serviceWorker.ready, 10000, "service worker ready");
  } catch (e) {
    throw new Error(`[service worker] ${e.message || e}`);
  }

  let sub;
  try {
    sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await withTimeout(
        reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
        }),
        10000,
        "subscribe"
      );
    }
  } catch (e) {
    throw new Error(`[subscribe] ${e.name || ""} ${e.message || e}`.trim());
  }

  try {
    const json = sub.toJSON();
    // ignoreDuplicates (ON CONFLICT DO NOTHING), not merge-duplicates (DO
    // UPDATE) — an upsert's "or update" half needs SELECT rights in
    // Postgres to check the existing row, and this table deliberately has
    // no SELECT policy (so the anon key can register a device but never
    // read back the full subscriber list). DO NOTHING sidesteps that
    // entirely, and is all we need anyway: the same endpoint always
    // carries the same keys, so there's nothing to actually update.
    const { error } = await supabase.from("push_subscriptions").upsert(
      {
        league_id: LEAGUE_ID,
        endpoint: json.endpoint,
        p256dh: json.keys.p256dh,
        auth: json.keys.auth,
      },
      { onConflict: "endpoint", ignoreDuplicates: true }
    );
    if (error) throw error;
  } catch (e) {
    throw new Error(`[save] ${e.message || e}`);
  }

  return sub;
}
