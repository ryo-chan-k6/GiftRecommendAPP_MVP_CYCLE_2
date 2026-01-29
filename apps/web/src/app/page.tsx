"use client";

import { useEffect, useState } from "react";

type HealthResponse = {
  status: string;
  service: string;
  timestamp: string;
};

export default function HomePage() {
  const [healthAPI, setHealthAPI] = useState<HealthResponse | null>(null);
  const [errorAPI, setErrorAPI] = useState<string | null>(null);

  const [healthReco, setHealthReco] = useState<HealthResponse | null>(null);
  const [errorReco, setErrorReco] = useState<string | null>(null);

  useEffect(() => {
    const fetchHealthAPI = async () => {
      try {
        console.log("🔄 API へのリクエスト開始: http://localhost:3001/health");
        const resAPI = await fetch("http://localhost:3001/health");

        console.log("📡 API レスポンス:", {
          status: resAPI.status,
          statusText: resAPI.statusText,
          ok: resAPI.ok,
          headers: Object.fromEntries(resAPI.headers.entries()),
        });

        if (!resAPI.ok) {
          const errorText = await resAPI.text();
          console.error("❌ API エラー:", {
            status: resAPI.status,
            statusText: resAPI.statusText,
            body: errorText,
          });
          throw new Error(`HTTP error: ${resAPI.status} ${resAPI.statusText}`);
        }

        const dataAPI: HealthResponse = await resAPI.json();
        console.log("✅ API レスポンスデータ:", dataAPI);
        setHealthAPI(dataAPI);
      } catch (err) {
        console.error("❌ API 例外:", err);
        setErrorAPI((err as Error).message);
      }
    };

    const fetchHealthReco = async () => {
      try {
        console.log("🔄 Reco へのリクエスト開始: http://localhost:3002/health");
        const resReco = await fetch("http://localhost:3002/health");

        console.log("📡 Reco レスポンス:", {
          status: resReco.status,
          statusText: resReco.statusText,
          ok: resReco.ok,
          headers: Object.fromEntries(resReco.headers.entries()),
        });

        if (!resReco.ok) {
          const errorText = await resReco.text();
          console.error("❌ Reco エラー:", {
            status: resReco.status,
            statusText: resReco.statusText,
            body: errorText,
          });
          throw new Error(
            `HTTP error: ${resReco.status} ${resReco.statusText}`
          );
        }

        const dataReco: HealthResponse = await resReco.json();
        console.log("✅ Reco レスポンスデータ:", dataReco);
        setHealthReco(dataReco);
      } catch (err) {
        console.error("❌ Reco 例外:", err);
        setErrorReco((err as Error).message);
      }
    };

    fetchHealthAPI();
    fetchHealthReco();
  }, []);

  return (
    <main style={{ padding: 24 }}>
      <h1>Health Check</h1>
      <h1>==============================</h1>
      <h2>API Health Check</h2>

      {errorAPI && <p style={{ color: "red" }}>Error: {errorAPI}</p>}

      {!errorAPI && !healthAPI && <p>Loading API ...</p>}
      {healthAPI && (
        <div>
          <p>Status: {healthAPI.status}</p>
          <p>Service: {healthAPI.service}</p>
          <p>Timestamp: {healthAPI.timestamp}</p>
        </div>
      )}

      <h1>==============================</h1>
      <h2>Reco Health Check</h2>

      {errorReco && <p style={{ color: "red" }}>Error: {errorReco}</p>}

      {!errorReco && !healthReco && <p>Loading Reco ...</p>}

      {healthReco && (
        <div>
          <p>Status: {healthReco.status}</p>
          <p>Service: {healthReco.service}</p>
          <p>Timestamp: {healthReco.timestamp}</p>
        </div>
      )}
      </main>
  );
}
