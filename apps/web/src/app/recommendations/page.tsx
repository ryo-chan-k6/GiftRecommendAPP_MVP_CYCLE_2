"use client";

import Link from "next/link";

export default function RecommendationPage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="mx-auto max-w-2xl px-4 py-16 sm:px-6">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-700 dark:bg-slate-800">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            レコメンド履歴
          </h1>
          <p className="mt-4 text-slate-600 dark:text-slate-400">
            MVP では履歴一覧は利用できません。認証なしのため「自分の」履歴を取得する手段がありません。
          </p>
          <p className="mt-6">
            <Link
              href="/recommend"
              className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white shadow-md transition-colors hover:bg-blue-700"
            >
              レコメンドを実行
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
