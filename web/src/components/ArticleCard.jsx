import { useState } from "react";
import { supabase } from "../supabaseClient";

function timeAgo(iso) {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "now";
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}

export default function ArticleCard({ post, onChange }) {
  const [open, setOpen] = useState(false);
  const comments = post.comments || [];
  const reactions = post.reactions || [];
  const headline = post.metadata?.headline;

  async function react() {
    await supabase.from("reactions").insert({ post_id: post.id, emoji: "❤️" });
    onChange();
  }

  return (
    <article className="article-card">
      <div className="article-kicker">
        Fantasy Media Desk <span className="article-dot">·</span>{" "}
        {timeAgo(post.created_at)}
      </div>

      {headline && <div className="article-headline">{headline}</div>}
      <div className="article-body">{post.body}</div>

      <div className="article-foot">
        <button className="article-act" onClick={react}>
          ❤️ {reactions.length || ""}
        </button>
        <button className="article-act" onClick={() => setOpen((o) => !o)}>
          💬 {comments.length || ""}
        </button>
      </div>

      {open && comments.length > 0 && (
        <div className="article-comments">
          {comments
            .slice()
            .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
            .map((c) => (
              <div className="article-comment" key={c.id}>
                <span className="article-chandle">{c.author_handle || "@fan"}</span>{" "}
                {c.body}
              </div>
            ))}
        </div>
      )}
    </article>
  );
}
