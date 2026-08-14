import { useState } from "react";
import { supabase } from "../supabaseClient";

export default function Login() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [err, setErr] = useState("");

  async function send(e) {
    e.preventDefault();
    setErr("");
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    });
    if (error) setErr(error.message);
    else setSent(true);
  }

  return (
    <div className="center">
      <div className="login-card">
        <div className="logo big">🏈 Fantasy Media</div>
        <p className="muted">Your league's media circus. Sign in to get in.</p>
        {sent ? (
          <p className="ok">
            Check your email for a magic link ✉️
            <br />
            Tap it on this device to sign in.
          </p>
        ) : (
          <form onSubmit={send}>
            <input
              type="email"
              required
              placeholder="you@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <button type="submit" className="primary">
              Send magic link
            </button>
            {err && <p className="err">{err}</p>}
          </form>
        )}
      </div>
    </div>
  );
}
