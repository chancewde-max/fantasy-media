import { useState } from "react";
import Feed from "./components/Feed.jsx";
import SubmitTip from "./components/SubmitTip.jsx";
import NotifyButton from "./components/NotifyButton.jsx";

export default function App() {
  const [tab, setTab] = useState("feed");

  return (
    <div className="app">
      <header className="topbar">
        <span className="logo">🏈 Fantasy Media</span>
        <NotifyButton />
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
