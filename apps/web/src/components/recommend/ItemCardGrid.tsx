"use client";

import ItemCard from "./ItemCard";

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

type ItemCardGridProps = {
  items: Item[];
};

export default function ItemCardGrid({ items }: ItemCardGridProps) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {items.map((item) => (
        <ItemCard
          key={item.itemId}
          rank={item.rank}
          itemName={item.itemName ?? ""}
          itemUrl={item.itemUrl}
          affiliateUrl={item.affiliateUrl}
          priceYen={item.priceYen}
          imageUrl={item.imageUrl}
          score={item.score}
        />
      ))}
    </div>
  );
}
