"use client";

import {useState, useEffect} from "react";
import {supabase} from "../../lib/supabaseClient";
import Link from "next/link";

type RecommendationRow = {
    id: string;
    context_id: string;
    algorithm: string;
    created_at: string;
    params: any;
};

export default function RecommendationPage() {
    const [items, setItems] = useState<RecommendationRow[]>([]);
    const [err, setErr] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function run() {
            try {
                const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
                if (!baseUrl) throw new Error("NEXT_PUBLIC_API_BASE_URL is not set");

                const {data: sessionData, error: sessionErr} = await supabase.auth.getSession();
                if(sessionErr) throw sessionErr;

                const token = sessionData.session?.access_token;
                if (!token) throw new Error("No session / access_token. Please sign in.");

                const res = await fetch(`${baseUrl}/recommendations/list?page=1&pageSize=30`,{
                    method: "GET",
                    headers: {Authorization: `Bearer ${token}`},
                    cache: "no-store"
                });
            
                const text = await res.text();
                if(!res.ok) throw new Error(`API error ${res.status}: ${text}`);

                const data = JSON.parse(text);
                setItems(Array.isArray(data.items) ? data.items : []);
            }catch (e: any) {
                setErr(e?.message ?? String(e));
            }finally {
                setLoading(false);
            }
        }
        run();
    }, []);

    if(err) return <pre style={{padding: 16}}>Error: {err}</pre>;
    if(loading) return <div style={{padding:16}}>Loading...</div>;

    return (
        <main style={{padding: 16}}>
            <h1>Recommendations</h1>

            {items.length === 0 ? (
                <p style={{marginTop:16}}>No recommendations yet.</p>
            ) : (
                <table style={{width: "100%", borderCollapse: "collapse", marginTop:16}}>
                    <thead>
                        <tr>
                            <th style={{borderBottom: "1px solid #ddd", textAlign: "left"}}>created_at</th>
                            <th style={{borderBottom: "1px solid #ddd", textAlign: "left"}}>algorithm</th>
                            <th style={{borderBottom: "1px solid #ddd", textAlign: "left"}}>id</th>
                            <th style={{borderBottom: "1px solid #ddd"}}></th>
                        </tr>
                    </thead>
                    <tbody>
                        {items.map((r) => (
                            <tr key={r.id}>
                                <td style={{padding: 8, borderBottom: "1px solid #eee"}}>
                                    {new Date(r.created_at).toLocaleString()}
                                </td>
                                <td style={{padding: 8, borderBottom: "1px solid #eee"}}>{r.algorithm}</td>
                                <td style={{padding: 8, borderBottom: "1px solid #eee", fontFamily: "monospace"}}>{r.id}</td>
                                <td style={{padding: 8, borderBottom: "1px solid #eee"}}>
                                    <Link href={`/recommendations/${r.id}`}>Open</Link>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </main>
    );
};
