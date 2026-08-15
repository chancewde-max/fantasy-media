import { useEffect, useState } from "react";
import { pushSupported, getPushState, enablePush } from "../push.js";

// iOS Safari only allows Web Push for a PWA that's been added to the Home
// Screen — a plain browser tab silently can't do it, even though the APIs
// may technically exist. Catch that up front so the button explains why
// instead of failing mysteriously.
function isIOS() {
  return (
    /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
  );
}

function isStandalone() {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true
  );
}

export default function NotifyButton() {
  // checking | ios-needs-install | unsupported | denied | unsubscribed | subscribed | working
  const [state, setState] = useState("checking");
  const [err, setErr] = useState("");

  useEffect(() => {
    if (isIOS() && !isStandalone()) {
      setState("ios-needs-install");
      return;
    }
    if (!pushSupported()) {
      setState("unsupported");
      return;
    }
    getPushState().then(setState);
  }, []);

  async function onClick() {
    if (state !== "unsubscribed") return;
    setState("working");
    setErr("");
    try {
      await enablePush();
      setState("subscribed");
    } catch (e) {
      setErr(e.message || "Couldn't enable notifications.");
      setState(Notification.permission === "denied" ? "denied" : "unsubscribed");
    }
  }

  if (state === "unsupported") return null;

  if (state === "ios-needs-install") {
    return (
      <span
        className="notify-btn notify-hint"
        title="Tap Share, then 'Add to Home Screen', then open the app from your home screen icon to enable notifications."
      >
        🔕 <span className="notify-label">Add to Home Screen to enable</span>
      </span>
    );
  }

  const label =
    state === "subscribed" ? "Notifications on" :
    state === "denied" ? "Notifications blocked" :
    state === "working" ? "Enabling…" :
    "Enable notifications";

  return (
    <button
      className="notify-btn"
      onClick={onClick}
      disabled={state !== "unsubscribed"}
      title={err || label}
    >
      {state === "subscribed" ? "🔔" : "🔕"} <span className="notify-label">{label}</span>
    </button>
  );
}
