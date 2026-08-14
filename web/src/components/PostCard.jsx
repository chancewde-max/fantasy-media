import { useState } from "react";
import { supabase } from "../supabaseClient";

const STYLES = {
  espn_notification: { tag: "ESPN", cls: "card-espn", icon: "🚨" },
  tweet: { tag: "Tweet", cls: "card-tweet", icon: "🐦" },
  instagram: { tag: "Insta", cls: "card-insta", icon: "📸" },
  insider_report: { tag: "Insider", cls: "card-insider", icon: "🕵️" },
};

function timeAgo(iso) {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "now";
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}

export default function PostCard({ post, onChange }) {
  const meta = STYLES[post.type] || STYLES.tweet;
  const [open, setOpen] = useState(false);
  const comments = post.comments || [];
  const reactions = post.reactions || [];

  async function react() {
    const { data: u } = await supabase.auth.getUser();
    const uid = u?.user?.id;
    if (!uid) return;
    const mine = reactions.find((r) => r.user_id === uid && r.emoji === "❤️");
    if (mine) {
      await supabase.from("reactions").delete().eq("id", mine.id);
    } else {
      await supabase
        .from("reactions")
        .insert({ post_id: post.id, emoji: "❤️", user_id: uid });
    }
    onChange();
  }

  return (
    <article className={`card ${meta.cls}`}>
      <div className="card-head">
        <span className="avatar">{meta.icon}</span>
        <span className="author">{post.author_handle || meta.tag}</span>
        <span className="pill">{meta.tag}</span>
        <span className="time">{timeAgo(post.created_at)}</span>
      </div>

      <div className="card-body">{post.body}</div>

      {post.image_url && (
        <img className="card-img" src={post.image_url} alt="" loading="lazy" />
      )}

      <div className="card-actions">
        <button className="act" onClick={react}>
          ❤️ {reactions.length || ""}
        </button>
        <button className="act" onClick={() => setOpen((o) => !o)}>
          💬 {comments.length || ""}
        </button>
      </div>

      {open && comments.length > 0 && (
        <div className="comments">
          {comments
            .slice()
            .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
            .map((c) => (
              <div className="comment" key={c.id}>
                <span className="chandle">{c.author_handle || "@fan"}</span>{" "}
                {c.body}
              </div>
            ))}
        </div>
      )}
    </article>
  );
}
