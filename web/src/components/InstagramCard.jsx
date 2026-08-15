import { useState } from "react";
import { supabase } from "../supabaseClient";

function timeAgo(iso) {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function HeartIcon({ liked }) {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24">
      <path
        fill={liked ? "#ed4956" : "none"}
        stroke={liked ? "#ed4956" : "#fff"}
        strokeWidth="1.7"
        d="M16.792 3.904A4.989 4.989 0 0 1 21.5 9.122c0 3.072-2.652 4.959-5.197 7.222-2.512 2.243-3.865 3.469-4.303 3.752-.477-.309-2.143-1.823-4.303-3.752C5.141 14.072 2.5 12.167 2.5 9.122a4.989 4.989 0 0 1 4.708-5.218 4.21 4.21 0 0 1 3.675 1.941c.84 1.175.98 1.763 1.12 1.763s.278-.588 1.11-1.766a4.17 4.17 0 0 1 3.679-1.938Z"
      />
    </svg>
  );
}

function CommentIcon() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24">
      <path
        fill="none"
        stroke="#fff"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M20.656 17.008a9.993 9.993 0 1 0-3.59 3.615L22 22Z"
      />
    </svg>
  );
}

function ShareIcon() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24">
      <line
        fill="none"
        stroke="#fff"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
        x1="22"
        y1="3"
        x2="9.218"
        y2="10.083"
      />
      <polygon
        fill="none"
        stroke="#fff"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
        points="11.698 20.334 22 3.001 2 3.001 9.218 10.084 11.698 20.334"
      />
    </svg>
  );
}

function BookmarkIcon() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24">
      <polygon
        fill="none"
        stroke="#fff"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
        points="20 21 12 13.44 4 21 4 3 20 3 20 21"
      />
    </svg>
  );
}

export default function InstagramCard({ post, onChange }) {
  const [open, setOpen] = useState(false);
  const [liked, setLiked] = useState(false);
  const comments = post.comments || [];
  const reactions = post.reactions || [];
  const handle = (post.author_handle || "@LeagueGram").replace(/^@/, "");

  async function react() {
    setLiked(true);
    await supabase.from("reactions").insert({ post_id: post.id, emoji: "❤️" });
    onChange();
  }

  return (
    <article className="ig-card">
      <div className="ig-head">
        <span className="ig-avatar">
          <span className="ig-avatar-inner">{handle[0]?.toUpperCase() || "L"}</span>
        </span>
        <span className="ig-username">{handle}</span>
        <span className="ig-dots">•••</span>
      </div>

      {post.image_url && (
        <div className="ig-imgwrap">
          <img className="ig-img" src={post.image_url} alt="" loading="lazy" />
        </div>
      )}

      <div className="ig-actions">
        <div className="ig-actions-left">
          <button className="ig-icon" onClick={react} aria-label="Like">
            <HeartIcon liked={liked} />
          </button>
          <button
            className="ig-icon"
            onClick={() => setOpen((o) => !o)}
            aria-label="Comment"
          >
            <CommentIcon />
          </button>
          <span className="ig-icon" aria-hidden="true">
            <ShareIcon />
          </span>
        </div>
        <span className="ig-icon ig-save" aria-hidden="true">
          <BookmarkIcon />
        </span>
      </div>

      {reactions.length > 0 && (
        <div className="ig-likes">
          {reactions.length} {reactions.length === 1 ? "like" : "likes"}
        </div>
      )}

      <div className="ig-caption">
        <span className="ig-username">{handle}</span> {post.body}
      </div>

      {comments.length > 0 && (
        <button className="ig-viewcomments" onClick={() => setOpen((o) => !o)}>
          {open ? "Hide comments" : `View all ${comments.length} comments`}
        </button>
      )}

      {open && comments.length > 0 && (
        <div className="ig-comments">
          {comments
            .slice()
            .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
            .map((c) => (
              <div className="ig-comment" key={c.id}>
                <span className="ig-username">
                  {(c.author_handle || "@fan").replace(/^@/, "")}
                </span>{" "}
                {c.body}
              </div>
            ))}
        </div>
      )}

      <div className="ig-time">{timeAgo(post.created_at)}</div>
    </article>
  );
}
