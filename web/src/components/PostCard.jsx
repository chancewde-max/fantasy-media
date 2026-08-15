import { useState } from "react";
import { supabase } from "../supabaseClient";
import InstagramCard from "./InstagramCard.jsx";
import ESPNCard from "./ESPNCard.jsx";
import TweetCard from "./TweetCard.jsx";

function timeAgo(iso) {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "now";
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}

export default function PostCard({ post, onChange }) {
  if (post.type === "instagram") {
    return <InstagramCard post={post} onChange={onChange} />;
  }
  if (post.type === "espn_notification") {
    return <ESPNCard post={post} onChange={onChange} />;
  }
  if (post.type === "tweet") {
    return <TweetCard post={post} onChange={onChange} />;
  }

  // insider_report — a plainer card, source stays anonymous by design.
  const [open, setOpen] = useState(false);
  const comments = post.comments || [];
  const reactions = post.reactions || [];

  async function react() {
    await supabase.from("reactions").insert({ post_id: post.id, emoji: "❤️" });
    onChange();
  }

  return (
    <article className="card card-insider">
      <div className="card-head">
        <span className="avatar">🕵️</span>
        <span className="author">{post.author_handle || "Insider"}</span>
        <span className="pill">Insider</span>
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
