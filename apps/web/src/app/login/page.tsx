"use client";

import { useState } from "react";
import { supabase } from "../../lib/supabaseClient";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState<string>("");

  const onLogin = async () => {
    setMsg("");

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      setMsg(`Login failed: ${error.message}`);
      return;
    }

    // session が取れたらログイン成功
    const accessToken = data.session?.access_token;
    setMsg(`Login success. token (head): ${accessToken?.slice(0, 20)}...`);
  };

  const onLogout = async () => {
    await supabase.auth.signOut();
    setMsg("Logged out.");
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>Login</h1>

      <div style={{ display: "grid", gap: 8, maxWidth: 360 }}>
        <input
          placeholder="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ padding: 8 }}
        />
        <input
          placeholder="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ padding: 8 }}
        />

        <button onClick={onLogin} style={{ padding: 8 }}>
          Login
        </button>
        <button onClick={onLogout} style={{ padding: 8 }}>
          Logout
        </button>

        <p>{msg}</p>
        <a href="/register" className="text-blue-600 hover:underline">
          新規登録
        </a>
        <a href="/recommend">Go to Recommend</a>
        <a href="/recommendations">Recommendations List</a>
      </div>
    </main>
  );
}
