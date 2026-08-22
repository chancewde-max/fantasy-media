import { useState } from "react";
import { supabase } from "../supabaseClient";
import { getFanHandle, setFanHandle } from "../fanIdentity";

// Shared composer dropped into every card type. Posts through the
// post_fan_comment RPC (schema_v8) since the app has no login and the
// comments table's RLS write policy needs a real auth.uid() otherwise.
export default function CommentComposer({ postId, onPosted, dark }) {
  const [handle, setHandle] = useState(getFanHandle());
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(false);

  function rename() {
    const next = window.prompt("Comment as:", handle);
    if (next != null) setHandle(setFanHandle(next));
  }

  async function submit(e) {
    e.preventDefault();
    const body = text.trim();
    if (!body || busy) return;
    setBusy(true);
    setErr(false);
    const { error } = await supabase.rpc("post_fan_comment", {
      p_post_id: postId,
      p_handle: handle,
      p_body: body,
    });
    setBusy(false);
    if (error) {
      setErr(true);
      return;
    }
    setText("");
    onPosted();
  }

  return (
    <form
      className={`comment-composer${dark ? " on-dark" : ""}`}
      onSubmit={submit}
    >
      <button
        type="button"
        className="comment-composer-handle"
        onClick={rename}
        title="Tap to change how you're identified"
      >
        {handle}
      </button>
      <input
        type="text"
        maxLength={280}
        placeholder="Give your take…"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button type="submit" disabled={busy || !text.trim()}>
        {busy ? "…" : "Post"}
      </button>
      {err && <span className="comment-composer-err">Couldn't post — try again</span>}
    </form>
  );
}
