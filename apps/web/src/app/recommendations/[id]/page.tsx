"use client";

import {useEffect, useState} from "react";
import Link from "next/link";
import {useParams} from "next/navigation";
import ItemCardGrid from "../../../components/recommend/ItemCardGrid";

type Item = {
  itemId: string;
  rank: number;
  score?: number;
  itemName?: string;
  itemUrl?: string;
  affiliateUrl?: string;
  priceYen?: number | null;
  imageUrl?: string | null;
  reason?: unknown;
};

type RecommendationDetailResponse = {
  header?: { id?: string; created_at?: string };
  context?: { context_text?: string };
  items?: Item[];
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

        const res = await fetch(`${baseUrl}/recommendations/${id}`, {
          method: "GET",
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

  if(err) {
    return (
      <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
        <div className="mx-auto max-w-4xl px-4 py-8">
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-800 dark:border-red-800 dark:bg-red-950/50 dark:text-red-200">
            <h1 className="text-lg font-semibold">エラー</h1>
            <p className="mt-2">{err}</p>
          </div>
        </div>
      </main>
    );
  }

  if(!id) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-900">
        <p className="text-slate-600 dark:text-slate-400">読み込み中...</p>
      </main>
    );
  }

  if(!data) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-900">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
      </main>
    );
  }

  const items = data.items ?? [];

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8">
          <Link
            href="/recommend"
            className="mb-4 inline-flex items-center text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
          >
            ← レコメンドを実行
          </Link>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            レコメンド結果
          </h1>
          {data.header?.created_at && (
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              {new Date(data.header.created_at).toLocaleString("ja-JP")}
            </p>
          )}
        </header>

        {data.context?.context_text && (
          <section className="mb-8 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <h2 className="mb-2 text-sm font-medium text-slate-500 dark:text-slate-400">
              検索条件
            </h2>
            <p className="text-slate-700 dark:text-slate-300">
              {data.context.context_text}
            </p>
          </section>
        )}

        <section>
          <h2 className="mb-6 text-lg font-semibold text-slate-800 dark:text-slate-200">
            おすすめ商品（{items.length}件）
          </h2>
          <ItemCardGrid items={items} />
        </section>
      </div>
    </main>
  );
}
