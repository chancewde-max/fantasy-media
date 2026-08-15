import { useState } from "react";
import { supabase } from "../supabaseClient";

function timeAgo(iso) {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "now";
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}

export default function ESPNCard({ post, onChange }) {
  const [open, setOpen] = useState(false);
  const comments = post.comments || [];
  const reactions = post.reactions || [];

  async function react() {
    await supabase.from("reactions").insert({ post_id: post.id, emoji: "❤️" });
    onChange();
  }

  return (
    <article className="espn-card">
      <div className="espn-topbar">
        <span className="espn-logo">ESPN</span>
        <span className="espn-tag">BREAKING NEWS</span>
        <span className="espn-time">{timeAgo(post.created_at)}</span>
      </div>

      <div className="espn-body">{post.body}</div>

      <div className="espn-foot">
        <span className="espn-source">{post.author_handle || "ESPN"} Fantasy</span>
        <div className="espn-actions">
          <button className="espn-act" onClick={react}>
            ❤️ {reactions.length || ""}
          </button>
          <button className="espn-act" onClick={() => setOpen((o) => !o)}>
            💬 {comments.length || ""}
          </button>
        </div>
      </div>

      {open && comments.length > 0 && (
        <div className="espn-comments">
          {comments
            .slice()
            .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
            .map((c) => (
              <div className="espn-comment" key={c.id}>
                <span className="espn-chandle">{c.author_handle || "@fan"}</span>{" "}
                {c.body}
              </div>
            ))}
        </div>
      )}
    </article>
  );
}
