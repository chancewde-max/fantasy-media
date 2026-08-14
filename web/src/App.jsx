import { useEffect, useState } from "react";
import { supabase, LEAGUE_ID } from "./supabaseClient";
import Login from "./components/Login.jsx";
import Feed from "./components/Feed.jsx";
import SubmitTip from "./components/SubmitTip.jsx";

export default function App() {
  const [session, setSession] = useState(null);
  const [ready, setReady] = useState(false);
  const [tab, setTab] = useState("feed");

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setReady(true);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  // Once logged in, make sure the user is a member of the league so RLS
  // lets them read the feed. Insert-self is allowed by policy; ignore dupes.
  useEffect(() => {
    if (!session?.user) return;
    supabase
      .from("memberships")
      .upsert(
        { league_id: LEAGUE_ID, user_id: session.user.id },
        { onConflict: "league_id,user_id", ignoreDuplicates: true }
      )
      .then(() => {});
  }, [session]);

  if (!ready) return <div className="center muted">Loading…</div>;
  if (!session) return <Login />;

  return (
    <div className="app">
      <header className="topbar">
        <span className="logo">🏈 Fantasy Media</span>
        <button className="link" onClick={() => supabase.auth.signOut()}>
          Sign out
        </button>
      </header>

      <main className="content">
        {tab === "feed" ? <Feed /> : <SubmitTip />}
      </main>

      <nav className="tabbar">
        <button
          className={tab === "feed" ? "tab active" : "tab"}
          onClick={() => setTab("feed")}
        >
          <span className="tabicon">📰</span>
          Feed
        </button>
        <button
          className={tab === "tip" ? "tab active" : "tab"}
          onClick={() => setTab("tip")}
        >
          <span className="tabicon">🕵️</span>
          Submit Tip
        </button>
      </nav>
    </div>
  );
}
