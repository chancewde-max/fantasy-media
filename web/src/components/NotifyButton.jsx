import { useEffect, useState } from "react";
import { pushSupported, getPushState, enablePush } from "../push.js";

export default function NotifyButton() {
  const [state, setState] = useState("checking"); // checking | unsupported | denied | unsubscribed | subscribed | working
  const [err, setErr] = useState("");

  useEffect(() => {
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
