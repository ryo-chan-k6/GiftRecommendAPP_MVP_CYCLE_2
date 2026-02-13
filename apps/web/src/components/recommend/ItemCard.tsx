"use client";

type ItemCardProps = {
  rank: number;
  itemName: string;
  itemUrl?: string;
  affiliateUrl?: string;
  priceYen?: number | null;
  imageUrl?: string | null;
  score?: number;
};

export default function ItemCard({
  rank,
  itemName,
  itemUrl,
  affiliateUrl,
  priceYen,
  imageUrl,
  score,
}: ItemCardProps) {
  const linkUrl = affiliateUrl || itemUrl || "#";

  return (
    <a
      href={linkUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="group block rounded-xl border border-[var(--border)] bg-[var(--background)] p-4 shadow-sm transition-all hover:border-[var(--border-muted)] hover:shadow-md"
    >
      <div className="relative aspect-square w-full overflow-hidden rounded-lg bg-[var(--border)]">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={itemName}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-[var(--foreground)]/40 text-sm">
            画像なし
          </div>
        )}
        <span className="absolute left-2 top-2 rounded-full bg-black/70 px-2 py-0.5 text-xs font-medium text-white">
          #{rank}
        </span>
      </div>
      <div className="mt-3 space-y-1">
        <h3 className="line-clamp-2 text-sm font-medium text-[var(--foreground)] group-hover:underline">
          {itemName || "商品名なし"}
        </h3>
        {priceYen != null && (
          <p className="text-base font-semibold text-[var(--foreground)]">
            ¥{priceYen.toLocaleString()}
          </p>
        )}
        {score != null && (
          <p className="text-xs text-[var(--foreground)]/60">スコア: {score.toFixed(2)}</p>
        )}
      </div>
    </a>
  );
}
