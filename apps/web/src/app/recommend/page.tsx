"use client";

import {useState} from "react";
import Link from "next/link";
import ItemCardGrid from "../../components/recommend/ItemCardGrid";

type Mode = "popular" | "balanced" | "diverse";

type RecommendedItem = {
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

type RecommendationResult = {
  recommendationId: string;
  mode: string;
  resolvedAlgorithm?: unknown;
  items: RecommendedItem[];
};

export default function RecommendRunPage() {
  const [mode, setMode] = useState<Mode>("balanced");
  const [budgetMin, setBudgetMin] = useState<number | "">("");
  const [budgetMax, setBudgetMax] = useState<number | "">("");
  const [eventName, setEventName] = useState<string>("");
  const [recipientDescription, setRecipientDescription] = useState<string>("");
  const [featuresLike, setFeaturesLike] = useState<string>("");
  const [featuresNotLike, setFeaturesNotLike] = useState<string>("");
  const [featuresNg, setFeaturesNg] = useState<string>("");

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<RecommendationResult | null>(null);

  function toList(s: string): string[] {
    return s
      .split(",")
      .map((x) => x.trim())
      .filter((x) => x.length > 0);
  }

  async function onSubmit() {
    try {
      setErr(null);
      setResult(null);
      setLoading(true);

      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      if(!baseUrl) throw new Error("NEXT_PUBLIC_API_BASE_URL is not set");

      const payload = {
        mode,
        eventName: eventName.trim() === "" ? null : eventName.trim(),
        recipientDescription: recipientDescription.trim() === "" ? null : recipientDescription.trim(),
        budgetMin: budgetMin === "" ? null : budgetMin,
        budgetMax: budgetMax === "" ? null : budgetMax,
        featuresLike: toList(featuresLike),
        featuresNotLike: toList(featuresNotLike),
        featuresNg: toList(featuresNg),
      };

      const apiUrl = `${baseUrl.replace(/\/$/, "")}/recommendations`;
      const res = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const text = await res.text();
      if (!res.ok) {
        let message = text;
        try {
          const parsed = JSON.parse(text) as { message?: string };
          message = parsed?.message ?? message;
        } catch {
          // keep raw text
        }
        // 404 の場合はリクエスト先を表示（デバッグ用）
        const urlHint = res.status === 404 ? ` (URL: ${apiUrl})` : "";
        throw new Error(`API error ${res.status}: ${message}${urlHint}`);
      }

      const data = JSON.parse(text) as RecommendationResult;
      if(!data.recommendationId) throw new Error("recommendationId is missing in response");

      setResult(data);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-10">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            ギフトレコメンド
          </h1>
          <p className="mt-2 text-slate-600 dark:text-slate-400">
            条件を入力して、ぴったりのギフトを見つけましょう
          </p>
        </header>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800 sm:p-8">
          <h2 className="mb-6 text-lg font-semibold text-slate-800 dark:text-slate-200">
            条件を入力
          </h2>

          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                レコメンドモード
              </label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as Mode)}
                className="w-full rounded-lg border border-slate-300 px-4 py-2.5 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
              >
                <option value="popular">人気重視</option>
                <option value="balanced">バランス</option>
                <option value="diverse">多様性重視</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  予算下限（円）
                </label>
                <input
                  type="number"
                  value={budgetMin}
                  onChange={(e) => setBudgetMin(e.target.value === "" ? "" : Number(e.target.value))}
                  placeholder="3000"
                  className="w-full rounded-lg border border-slate-300 px-4 py-2.5 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  予算上限（円）
                </label>
                <input
                  type="number"
                  value={budgetMax}
                  onChange={(e) => setBudgetMax(e.target.value === "" ? "" : Number(e.target.value))}
                  placeholder="8000"
                  className="w-full rounded-lg border border-slate-300 px-4 py-2.5 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                />
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                イベント（任意）
              </label>
              <input
                type="text"
                value={eventName}
                onChange={(e) => setEventName(e.target.value)}
                placeholder="例: 父の日、誕生日"
                className="w-full rounded-lg border border-slate-300 px-4 py-2.5 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                贈り先（任意）
              </label>
              <input
                type="text"
                value={recipientDescription}
                onChange={(e) => setRecipientDescription(e.target.value)}
                placeholder="例: 父、友人、上司"
                className="w-full rounded-lg border border-slate-300 px-4 py-2.5 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                好みの特徴（カンマ区切り）
              </label>
              <input
                type="text"
                value={featuresLike}
                onChange={(e) => setFeaturesLike(e.target.value)}
                placeholder="例: 落ち着いた, 実用的, 黒"
                className="w-full rounded-lg border border-slate-300 px-4 py-2.5 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                避けたい特徴（カンマ区切り）
              </label>
              <input
                type="text"
                value={featuresNotLike}
                onChange={(e) => setFeaturesNotLike(e.target.value)}
                placeholder="例: 派手"
                className="w-full rounded-lg border border-slate-300 px-4 py-2.5 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                NG条件（カンマ区切り）
              </label>
              <input
                type="text"
                value={featuresNg}
                onChange={(e) => setFeaturesNg(e.target.value)}
                placeholder="例: 生もの"
                className="w-full rounded-lg border border-slate-300 px-4 py-2.5 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
              />
            </div>
          </div>

          <div className="mt-8">
            <button
              onClick={onSubmit}
              disabled={loading}
              className="w-full rounded-xl bg-blue-600 px-6 py-3.5 font-semibold text-white shadow-md transition-colors hover:bg-blue-700 disabled:bg-slate-400 sm:w-auto sm:px-10"
            >
              {loading ? "レコメンド実行中..." : "レコメンドを実行"}
            </button>
          </div>
        </section>

        {err && (
          <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-800 dark:bg-red-950/50 dark:text-red-200">
            <p className="font-medium">エラー</p>
            <p className="mt-1 text-sm">{err}</p>
          </div>
        )}

        {result && (
          <section className="mt-10">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                レコメンド結果
              </h2>
              <Link
                href={`/recommendations/${result.recommendationId}`}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
              >
                この結果を共有・ブックマーク
              </Link>
            </div>
            <ItemCardGrid items={result.items} />
          </section>
        )}
      </div>
    </main>
  );
}
