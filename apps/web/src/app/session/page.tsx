"use client";

import { useState, useEffect } from "react";
import { supabase } from "../../lib/supabaseClient";

export default function SessionPage() {
  const [token, setToken] = useState<string>("");

  useEffect(() => {
    (async () => {
      const { data } = await supabase.auth.getSession();
      setToken(data.session?.access_token ?? "");
    })();
  }, []);

  return (
    <main style={{ padding: 24 }}>
      <h1>Session</h1>
      <p>access_token:</p>
      <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
        {token || "(no session)"}
      </pre>
    </main>
  );
}
