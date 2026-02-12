"use client";

import {useEffect, useState} from "react";
import {useParams} from "next/navigation";
import {supabase} from "../../../lib/supabaseClient";

type RecommendationDetailResponse = {
    header?: unknown;
    context?: unknown;
    items?: unknown;
};

export default function RecommendationDetailPage() {
    const params = useParams();
    const id = typeof params?.id === "string" ? params.id : undefined;

    const [data, setData] = useState<RecommendationDetailResponse | null>(null);
    const [err, setErr] = useState<string | null>(null);

    useEffect(() => {
        async function run() {
            try {
                if(!id) return;
                const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
                if (!baseUrl) throw new Error("NEXT_PUBLIC_API_BASE_URL is not set");

                const {data: sessionData, error: sessionErr} = await supabase.auth.getSession();
                if (sessionErr) throw sessionErr;

                const token = sessionData.session?.access_token;
                if(!token) throw new Error("No session / access_token. Please sign in.");

                const res = await fetch(`${baseUrl}/recommendations/${id}`, {
                    method: "GET",
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                    cache: "no-store"
                });

                const text = await res.text();
                if (!res.ok) throw new Error(`API error ${res.status}: ${text}`);

                setData(JSON.parse(text) as RecommendationDetailResponse);
            } catch (e: unknown) {
                setErr(e instanceof Error ? e.message : String(e));
            }
        }

        run();
    }, [id]);

    if(err) return <pre style={{padding:16}}>Error: {err}</pre>;
    if(!id) return <div style={{padding:16}}>Loading route...</div>;
    if(!data) return <div style={{padding:16}}>Loading...</div>;

    return (
        <main style={{padding:16}}>
            <h1>Recommendation Detail</h1>

            <section style={{marginTop:16}}>
                <h2>Header</h2>
                <pre style={{background:"#555555", padding:12, overflowX: "auto"}}>
                    {JSON.stringify(data.header, null, 2)}
                </pre>
            </section>

            <section style={{marginTop:16}}>
                <h2>Context</h2>
                <pre style={{background:"#555555", padding:12, overflowX:"auto"}}>
                    {JSON.stringify(data.context, null, 2)}
                </pre>
            </section>

            <section style={{marginTop:16}}>
                <h2>Items</h2>
                <pre style={{background:"#555555", padding:12,overflowX:"auto"}}>
                    {JSON.stringify(data.items, null, 2)}
                </pre>
            </section>
        </main>
    );
}
