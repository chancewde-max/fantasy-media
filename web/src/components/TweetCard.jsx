import { useState } from "react";
import { supabase } from "../supabaseClient";
import CommentComposer from "./CommentComposer.jsx";

// Stable-per-handle fake profile photo (a real-looking but not-a-real-person
// stock face) so accounts feel like accounts, not initials in a circle.
function avatarUrl(seed, size) {
  return `https://i.pravatar.cc/${size}?u=${encodeURIComponent(seed)}`;
}

function timeAgo(iso) {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "now";
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  const d = new Date(iso);
  return `${d.toLocaleString("en-US", { month: "short" })} ${d.getDate()}`;
}

function displayName(handle) {
  return handle
    .replace(/^@/, "")
    .split(/[_.]/)
    .filter(Boolean)
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

function ReplyIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18">
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        d="M1.751 10c0-4.42 3.584-8 8.005-8h4.366c4.49 0 8.129 3.64 8.129 8.13 0 2.96-1.607 5.68-4.196 7.11l-8.054 4.46v-3.69h-.067c-4.49.1-8.183-3.51-8.183-8.01Z"
      />
    </svg>
  );
}

function RetweetIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18">
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        d="M4.5 3.88v8.62a3 3 0 0 0 3 3h10.37l-3.44 3.44 1.06 1.06L20.94 15l-5.45-5.45-1.06 1.06 3.44 3.44H7.5a1 1 0 0 1-1-1V3.88ZM19.5 20.12v-8.62a3 3 0 0 0-3-3H6.13l3.44-3.44-1.06-1.06L3.06 9l5.45 5.45 1.06-1.06-3.44-3.44H16.5a1 1 0 0 1 1 1v8.62Z"
      />
    </svg>
  );
}

function HeartIcon({ liked }) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18">
      <path
        fill={liked ? "#f91880" : "none"}
        stroke={liked ? "#f91880" : "currentColor"}
        strokeWidth="2"
        d="M16.792 3.904A4.989 4.989 0 0 1 21.5 9.122c0 3.072-2.652 4.959-5.197 7.222-2.512 2.243-3.865 3.469-4.303 3.752-.477-.309-2.143-1.823-4.303-3.752C5.141 14.072 2.5 12.167 2.5 9.122a4.989 4.989 0 0 1 4.708-5.218 4.21 4.21 0 0 1 3.675 1.941c.84 1.175.98 1.763 1.12 1.763s.278-.588 1.11-1.766a4.17 4.17 0 0 1 3.679-1.938Z"
      />
    </svg>
  );
}

// The two recurring pundit accounts get a distinct badge avatar instead of
// the random stock-photo look every other handle gets — a deliberate choice:
// no real photo of the real people, just a consistent "recurring segment"
// look so they read as fixed characters, not one-off fans.
const PUNDIT_AVATARS = {
  "@danorlovsky7": { initials: "DO", from: "#1e3a8a", to: "#3b82f6" },
  "@stephenasmith": { initials: "SA", from: "#7c2d12", to: "#f97316" },
};

function PunditAvatar({ handle }) {
  const p = PUNDIT_AVATARS[handle.toLowerCase()];
  return (
    <span
      className="tw-avatar tw-avatar-pundit"
      style={{ background: `linear-gradient(135deg, ${p.from}, ${p.to})` }}
    >
      {p.initials}
      <span className="tw-avatar-mic" aria-hidden="true">🎙️</span>
    </span>
  );
}

function ShareIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18">
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        d="M12 2.59l5.7 5.7-1.41 1.42L13 6.41V16h-2V6.41l-3.3 3.3-1.41-1.42L12 2.59zM21 15l-.02 3.51c0 1.38-1.12 2.49-2.5 2.49H5.5C4.11 21 3 19.88 3 18.5V15h2v3.5c0 .28.22.5.5.5h12.98c.28 0 .5-.22.5-.5L19 15h2z"
      />
    </svg>
  );
}

export default function TweetCard({ post, onChange }) {
  const [open, setOpen] = useState(false);
  const [liked, setLiked] = useState(false);
  const comments = post.comments || [];
  const reactions = post.reactions || [];
  const handle = post.author_handle || "@fan";
  const name = displayName(handle);
  const isPundit = Boolean(PUNDIT_AVATARS[handle.toLowerCase()]);

  async function react() {
    setLiked(true);
    await supabase.from("reactions").insert({ post_id: post.id, emoji: "❤️" });
    onChange();
  }

  return (
    <article className="tw-card">
      <div className="tw-body-row">
        {isPundit ? (
          <PunditAvatar handle={handle} />
        ) : (
          <img className="tw-avatar" src={avatarUrl(handle, 80)} alt="" />
        )}
        <div className="tw-main">
          <div className="tw-head">
            <span className="tw-display">{name}</span>
            <span className="tw-handle">{handle}</span>
            <span className="tw-dot">·</span>
            <span className="tw-time">{timeAgo(post.created_at)}</span>
          </div>
          <div className="tw-text">{post.body}</div>
          {post.metadata?.gif_url && (
            <img className="tw-gif" src={post.metadata.gif_url} alt="" loading="lazy" />
          )}
          <div className="tw-actions">
            <button
              className="tw-icon"
              onClick={() => setOpen((o) => !o)}
              aria-label="Reply"
            >
              <ReplyIcon />
              {comments.length > 0 && <span>{comments.length}</span>}
            </button>
            <span className="tw-icon tw-static" aria-hidden="true">
              <RetweetIcon />
            </span>
            <button className="tw-icon" onClick={react} aria-label="Like">
              <HeartIcon liked={liked} />
              {reactions.length > 0 && <span>{reactions.length}</span>}
            </button>
            <span className="tw-icon tw-static" aria-hidden="true">
              <ShareIcon />
            </span>
          </div>
        </div>
      </div>

      {open && (
        <div className="tw-comments">
          {comments
            .slice()
            .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
            .map((c) => (
              <div className="tw-comment" key={c.id}>
                <span className="tw-chandle">{c.author_handle || "@fan"}</span>{" "}
                {c.body}
              </div>
            ))}
          <CommentComposer postId={post.id} onPosted={onChange} dark />
        </div>
      )}
    </article>
  );
}
