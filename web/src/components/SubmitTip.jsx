import { useState } from "react";
import { supabase, LEAGUE_ID } from "../supabaseClient";

export default function SubmitTip() {
  const [text, setText] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setStatus("");
    const { error } = await supabase
      .from("tips")
      .insert({ league_id: LEAGUE_ID, raw_text: text.trim() });
    setBusy(false);
    if (error) {
      setStatus("err:" + error.message);
    } else {
      setText("");
      setStatus("ok");
    }
  }

  return (
    <div className="tip-tab">
      <h2>🕵️ Drop a tip to the Insider</h2>
      <p className="muted">
        Anonymous. The Insider only runs a rumor once <b>2+ managers</b> report
        the same thing — reports drop once a day. No one sees who tipped.
      </p>
      <form onSubmit={submit}>
        <textarea
          rows={4}
          placeholder="heard Team Chaos is shopping their RB1…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button className="primary" disabled={busy} type="submit">
          {busy ? "Sending…" : "Send anonymously"}
        </button>
      </form>
      {status === "ok" && (
        <p className="ok">Tip received 🤫 If it's corroborated, it'll surface.</p>
      )}
      {status.startsWith("err:") && <p className="err">{status.slice(4)}</p>}
    </div>
  );
}
