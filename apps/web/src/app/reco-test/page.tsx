"use client";

import { useState } from "react";
import { supabase } from "../../lib/supabaseClient";

export default function RecoTestPage() {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string>("");

  const callApi = async () => {
    setError("");
    setResult(null);

    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;

    if (!token) {
      setError("No session. Please login first.");
      return;
    }

    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL;
    const res = await fetch(`${apiBase}/recommendations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ mode: "balanced" }),
    });
    console.log(data.session?.user?.id);

    const text = await res.text();
    if (!res.ok) {
      setError(`API error: ${res.status} ${text}`);
      return;
    }

    setResult(JSON.parse(text) as Record<string, unknown>);
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>Reco API Test</h1>
      <button onClick={callApi} style={{ padding: 8 }}>
        Call /recommendations
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {result != null ? (
        <pre style={{ whiteSpace: "pre-wrap" }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      ) : null}
    </main>
  );
}
