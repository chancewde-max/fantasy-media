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

export async function enablePush() {
  if (!pushSupported()) throw new Error("Push notifications aren't supported on this browser.");

  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Notification permission was not granted.");

  const reg = await navigator.serviceWorker.register("/sw.js");
  await navigator.serviceWorker.ready;

  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
    });
  }

  const json = sub.toJSON();
  const { error } = await supabase.from("push_subscriptions").upsert(
    {
      league_id: LEAGUE_ID,
      endpoint: json.endpoint,
      p256dh: json.keys.p256dh,
      auth: json.keys.auth,
    },
    { onConflict: "endpoint" }
  );
  if (error) throw error;
  return sub;
}
