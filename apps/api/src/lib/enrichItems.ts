import { supabaseAdmin } from "@/lib/supabase";

export type EnrichedItem = {
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

/**
 * item_ids に対応する item 詳細と item_image を取得し、
 * items に itemName, itemUrl, affiliateUrl, priceYen, imageUrl を付与する
 */
export async function enrichItemsWithDetails(
  items: Array<{ itemId: string; rank: number; score?: number; reason?: unknown }>
): Promise<EnrichedItem[]> {
  const itemIds = [...new Set(items.map((i) => i.itemId).filter(Boolean))];
  if (itemIds.length === 0) return items as EnrichedItem[];

  const [itemRes, imageRes] = await Promise.all([
    supabaseAdmin
      .schema("apl")
      .from("item")
      .select("id, item_name, item_url, affiliate_url")
      .in("id", itemIds),
    supabaseAdmin
      .schema("apl")
      .from("item_image")
      .select("item_id, url, size, sort_order")
      .in("item_id", itemIds)
      .order("sort_order", { ascending: true }),
  ]);

  const itemMap = new Map<string, { itemName: string; itemUrl: string; affiliateUrl: string }>();
  for (const r of itemRes.data ?? []) {
    const id = r?.id;
    if (id) {
      itemMap.set(id, {
        itemName: r.item_name ?? "",
        itemUrl: r.item_url ?? "",
        affiliateUrl: r.affiliate_url ?? r.item_url ?? "",
      });
    }
  }

  const imageMap = new Map<string, string>();
  const seen = new Set<string>();
  for (const r of imageRes.data ?? []) {
    const id = r?.item_id;
    if (id && !seen.has(id)) {
      seen.add(id);
      imageMap.set(id, r.url ?? "");
    }
  }

  const priceRes = await supabaseAdmin
    .schema("apl")
    .from("item_features")
    .select("item_id, price_yen")
    .in("item_id", itemIds);
  const priceMap = new Map<string, number | null>();
  for (const r of priceRes.data ?? []) {
    const id = r?.item_id;
    if (id) priceMap.set(id, r.price_yen ?? null);
  }

  return items.map((it) => {
    const item = itemMap.get(it.itemId);
    const imageUrl = imageMap.get(it.itemId) ?? null;
    const priceYen = priceMap.get(it.itemId) ?? null;
    return {
      ...it,
      itemName: item?.itemName ?? "",
      itemUrl: item?.itemUrl ?? "",
      affiliateUrl: item?.affiliateUrl ?? "",
      priceYen,
      imageUrl,
      reason: it.reason,
    };
  });
}
