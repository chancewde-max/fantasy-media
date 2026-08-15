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
  const [hint, setHint] = useState("");

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
      // Note: NOT alert() — iOS Safari silently swallows alert()/confirm()
      // when the app is running installed (standalone) from the Home
      // Screen, which is exactly the case this button most needs to work
      // in. Inline text is the only thing guaranteed visible everywhere.
      setErr(e.message || "Couldn't enable notifications.");
      setState(Notification.permission === "denied" ? "denied" : "unsubscribed");
    }
  }

  if (state === "unsupported") return null;

  if (state === "ios-needs-install") {
    return (
      <div className="notify-wrap">
        <button className="notify-btn notify-hint" onClick={() => setHint((h) => !h)}>
          🔕 <span className="notify-label">Add to Home Screen to enable</span>
        </button>
        {hint && (
          <div className="notify-banner">
            1. Tap the Share button in Safari
            <br />
            2. Tap "Add to Home Screen"
            <br />
            3. Open Fantasy Media from that new home screen icon
            <br />
            4. Tap "Enable notifications" again from there
          </div>
        )}
      </div>
    );
  }

  const label =
    state === "subscribed" ? "Notifications on" :
    state === "denied" ? "Notifications blocked" :
    state === "working" ? "Enabling…" :
    "Enable notifications";

  return (
    <div className="notify-wrap">
      <button
        className="notify-btn"
        onClick={onClick}
        disabled={state !== "unsubscribed"}
      >
        {state === "subscribed" ? "🔔" : "🔕"} <span className="notify-label">{label}</span>
      </button>
      {err && <div className="notify-banner notify-banner-err">{err}</div>}
    </div>
  );
}
