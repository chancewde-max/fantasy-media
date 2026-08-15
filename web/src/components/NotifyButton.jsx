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
      const message = e.message || "Couldn't enable notifications.";
      setErr(message);
      // title/tooltip never shows on mobile taps — alert is blunt but the
      // only thing guaranteed visible on every phone.
      alert(message);
      setState(Notification.permission === "denied" ? "denied" : "unsubscribed");
    }
  }

  if (state === "unsupported") return null;

  if (state === "ios-needs-install") {
    return (
      <button
        className="notify-btn notify-hint"
        onClick={() =>
          alert(
            "iPhone notifications need the app installed first:\n\n" +
              "1. Tap the Share button in Safari\n" +
              "2. Tap \"Add to Home Screen\"\n" +
              "3. Open Fantasy Media from that new home screen icon\n" +
              "4. Tap \"Enable notifications\" again from there"
          )
        }
      >
        🔕 <span className="notify-label">Add to Home Screen to enable</span>
      </button>
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
