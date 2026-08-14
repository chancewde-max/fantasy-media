import { useCallback, useEffect, useState } from "react";
import { supabase, LEAGUE_ID } from "../supabaseClient";
import PostCard from "./PostCard.jsx";

export default function Feed() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    setErr("");
    const { data, error } = await supabase
      .from("posts")
      .select(
        "id,type,author_handle,body,image_url,metadata,created_at," +
          "comments(id,author_handle,body,is_ai,created_at)," +
          "reactions(id,emoji,user_id)"
      )
      .eq("league_id", LEAGUE_ID)
      .order("created_at", { ascending: false })
      .limit(100);
    if (error) setErr(error.message);
    else setPosts(data || []);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
    // Realtime: refresh when new posts land.
    const ch = supabase
      .channel("posts-feed")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "posts" },
        () => load()
      )
      .subscribe();
    return () => supabase.removeChannel(ch);
  }, [load]);

  if (loading) return <div className="center muted">Loading feed…</div>;
  if (err) return <div className="center err">{err}</div>;
  if (!posts.length)
    return (
      <div className="center muted">
        No posts yet. Once the league heats up, they'll show here. 🍿
      </div>
    );

  return (
    <div className="feed">
      {posts.map((p) => (
        <PostCard key={p.id} post={p} onChange={load} />
      ))}
    </div>
  );
}
