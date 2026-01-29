"use client";

import {useState} from "react";
import {useRouter} from "next/navigation";
import {supabase} from "../../lib/supabaseClient";

type Mode = "popular" | "balanced" | "diverse";

export default function RecommendRunPage() {
    const router = useRouter();

    const [mode, setMode] = useState<Mode>("balanced");
    const [budgetMin, setBudgetMin] = useState<number | "">("");
    const [budgetMax, setBudgetMax] = useState<number | "">("");
    const [eventId, setEventId] = useState<string>("");
    const [recipientId, setRecipientId] = useState<string>("");
    const [featuresLike, setFeaturesLike] = useState<string>("");
    const [featuresNotLike, setFeaturesNotLike] = useState<string>("");
    const [featuresNg, setFeaturesNg] = useState<string>("");

    const [loading, setLoading] = useState(false);
    const [err, setErr] = useState<string | null>(null);

    function toList(s: string): string[] {
        return s
            .split(",")
            .map((x) => x.trim())
            .filter((x) => x.length > 0);
    }

    async function onSubmit() {
        try {
            setErr(null);
            setLoading(true);

            const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
            if(!baseUrl) throw new Error("NEXT_PUBLIC_API_BASE_URL is not set");

            // 1) Supabase session -> access_token
            const {data: sessionData, error: sessionErr} = await supabase.auth.getSession();
            if(sessionErr) throw sessionErr;

            const token = sessionData.session?.access_token;
            if(!token) throw new Error("No session / access_token. Please sign in.");

            // 2) API payload（MVP最小）
            const payload: any = {
                mode,
                eventId: eventId.trim() === "" ? null : eventId.trim(),
                recipientId: recipientId.trim() === "" ? null : recipientId.trim(),
                budgetMin: budgetMin === "" ? null : budgetMin,
                budgetMax: budgetMax === "" ? null : budgetMax,
                featuresLike: toList(featuresLike),
                featuresNotLike: toList(featuresNotLike),
                featuresNg: toList(featuresNg),
            };

            // 3) POST /recommendations
            const res = await fetch(`${baseUrl}/recommendations`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify(payload),
            });

            const text = await res.text();
            if (!res.ok) {
                let message = text;
                try {
                    const parsed = JSON.parse(text);
                    message = parsed?.message ?? message;
                } catch {
                    // keep raw text
                }
                throw new Error(`API error ${res.status}: ${message}`);
            }

            const data = JSON.parse(text);

            // apiのレスポンスに recommendationId が入っている前提
            const recommendationId = data.recommendationId;
            if(!recommendationId) throw new Error("recommendationId is missing in response");

            router.push(`/recommendations/${recommendationId}`);
        }catch (e: any) {
            setErr(e?.message ?? String(e));
        }finally {
            setLoading(false);
        }
    }

    return (
        <main style={{padding: 16, maxWidth:720}}>
            <h1>Run Recommendation</h1>

            <div style={{marginTop:16}}>
                <label>mode</label>
                <div>
                    <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
                        <option value="popular">popular</option>
                        <option value="balanced">balanced</option>
                        <option value="diverse">diverse</option>
                    </select>
                </div>
            </div>

            <div style={{marginTop:16}}>
                <label>budgetMin</label>
                <div>
                    <input 
                        type="number"
                        value={budgetMin}
                        onChange={(e) => setBudgetMin(e.target.value === "" ? "" : Number(e.target.value))}
                        placeholder="e.g. 3000"
                    />
                </div>
            </div>

            <div style={{marginTop:16}}>
                <label>budgetMax</label>
                <div>
                    <input 
                        type="number"
                        value={budgetMax}
                        onChange={(e) => setBudgetMax(e.target.value === "" ? "" : Number(e.target.value))}
                        placeholder="e.g. 8000"
                    />
                </div>
            </div>

            <div style={{marginTop:16}}>
                <label>eventId (optional)</label>
                <div>
                    <input
                        type="text"
                        value={eventId}
                        onChange={(e) => setEventId(e.target.value)}
                        placeholder="uuid"
                        style={{width: "100%"}}
                    />
                </div>
            </div>

            <div style={{marginTop:16}}>
                <label>recipientId (optional)</label>
                <div>
                    <input
                        type="text"
                        value={recipientId}
                        onChange={(e) => setRecipientId(e.target.value)}
                        placeholder="uuid"
                        style={{width: "100%"}}
                    />
                </div>
            </div>

            <div style={{marginTop:16}}>
                <label>featuresLike (comma separated)</label>
                <div>
                    <input 
                        type="text"
                        value={featuresLike}
                        onChange={(e) => setFeaturesLike(e.target.value)}
                        placeholder="e.g. coffee, simple, premium"
                        style={{width: "100%"}}
                    />
                </div>
            </div>

            <div style={{marginTop:16}}>
                <label>featuresNotLike (comma separated)</label>
                <div>
                    <input 
                        type="text"
                        value={featuresNotLike}
                        onChange={(e) => setFeaturesNotLike(e.target.value)}
                        placeholder="e.g. sweet, loud"
                        style={{width: "100%"}}
                    />
                </div>
            </div>

            <div style={{marginTop:16}}>
                <label>featuresNg (comma separated)</label>
                <div>
                    <input 
                        type="text"
                        value={featuresNg}
                        onChange={(e) => setFeaturesNg(e.target.value)}
                        placeholder="e.g. alcohol, pork"
                        style={{width: "100%"}}
                    />
                </div>
            </div>

            <div style={{marginTop: 20}}>
                <button onClick={onSubmit} disabled={loading}>
                    {loading ? "Running..." : "Run"}
                </button>
            </div>

            {err && (
                <pre style={{marginTop: 16, background:"#555555", padding: 12, overflowX: "auto"}}>
                    Error: {err}
                </pre>
            )}
        </main>
    );
}
