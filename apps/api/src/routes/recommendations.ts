import { Router, Request, Response } from "express";
import { optionalAuth } from "../middlewares/optionalAuth";
import {
  ALGORITHM_OVERRIDES,
  AlgorithmOverride,
  MODES,
} from "@/types/recommendation";
import { isAdmin } from "@/lib/admin";
import {supabaseAdmin} from "@/lib/supabase";
import {saveRecommendation} from "@/lib/recommendationRepo";
import {computeContextHash} from "@/lib/contextHash";
import {enrichItemsWithDetails} from "@/lib/enrichItems";

const router = Router();

router.post("/", optionalAuth, async (req: Request, res: Response) => {
  try {
    const recoBaseUrl = process.env.RECO_BASE_URL;
    if (!recoBaseUrl) return res.status(500).json({ message: "RECO_BASE_URL is not set" });

    const userId = req.user?.id ?? null;
    const body = req.body ?? {};

    const mode = body.mode;
    if (!MODES.includes(mode)) return res.status(400).json({message: "Invalid mode", allowed: MODES});

    // algorithmOverride は ADMIN のみ許可（認証ありの場合のみ）
    let algorithmOverride: string | null = null;
    if (body.algorithmOverride != null) {
      if(!ALGORITHM_OVERRIDES.includes(body.algorithmOverride)) {
        return res.status(400).json({message: "Invalid algorithmOverride", allowed: ALGORITHM_OVERRIDES})
      }
      if (userId) {
        const ok = await isAdmin(userId);
        if(!ok) return res.status(403).json({message: "algorithmOverride is allowed for ADMIN only"});
      } else {
        return res.status(401).json({message: "algorithmOverride requires authentication"});
      }
      algorithmOverride = body.algorithmOverride;
    }

    // reco へ送る payload
    const recoPayload: Record<string, unknown> = {
      mode,
      eventName: body.eventName ?? null,
      recipientDescription: body.recipientDescription ?? null,
      budgetMin: body.budgetMin ?? null,
      budgetMax: body.budgetMax ?? null,
      featuresLike: body.featuresLike ?? [],
      featuresNotLike: body.featuresNotLike ?? [],
      featuresNg: body.featuresNg ?? [],
      ...(algorithmOverride && { algorithmOverride }),
    };

    const recoRes = await fetch(`${recoBaseUrl}/recommendations`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(recoPayload),
    });

    const text = await recoRes.text();
    if(!recoRes.ok) return res.status(recoRes.status).json({message: "Reco service error", detail: text});

    const recoData = JSON.parse(text);

    // resolved.algorithm を必ず確定（ログ調査用）
    const resolvedAlgorithm =
      recoData?.resolved?.name ?? algorithmOverride ?? "vector_ranked_mmr";
    
    const embeddingContext = recoData?.context?.contextText ?? "";
    const embeddingModel =
      recoData?.context?.embeddingModel ?? "text-embedding-3-small";
    const embeddingVersion =
      recoData?.context?.embeddingVersion ?? 1;

    const contextHash = computeContextHash({
      userId,
      eventName: body.eventName ?? null,
      recipientDescription: body.recipientDescription ?? null,
      mode: mode,
      budgetMin: body.budgetMin ?? null,
      budgetMax: body.budgetMax ?? null,
      featuresLike: body.featuresLike ?? [],
      featuresNotLike: body.featuresNotLike ?? [],
      featuresNg: body.featuresNg ?? [],
      embeddingModel: embeddingModel,
      embeddingVersion: embeddingVersion,
      embeddingContext: embeddingContext,
    });

    // reco items -> DB rows
    const recoItems = Array.isArray(recoData.items) ? recoData.items : [];
    const items = recoItems.map((it: any, idx: number) => ({
      itemId: it.itemId,
      rank: idx + 1,
      score: it.score,
      vectorScore: it.vectorScore ?? null,
      rerankScore: it.rerankScore ?? null,
      reason: it.reason ?? null,
    }));

    // DB 保存（認証なしの場合は user_id=null）
    const saved = await saveRecommendation({
      userId,
      context: {
        eventId: null,
        recipientId: null,
        budgetMin: body.budgetMin ?? null,
        budgetMax: body.budgetMax ?? null,
        featuresLike: body.featuresLike ?? [],
        featuresNotLike: body.featuresNotLike ?? [],
        featuresNg: body.featuresNg ?? [],
        embeddingContext,
        embeddingModel,
        embeddingVersion,
        contextHash,
        contextVector: recoData?.context?.contextVector ?? null,
      },
      algorithm: resolvedAlgorithm,
      params: {
        mode,
        algorithmOverride,
      },
      items,
    });

    const enrichedItems = await enrichItemsWithDetails(
      recoData.items.map((it: any) => ({
        itemId: it.itemId,
        rank: it.rank ?? 0,
        score: it.score,
        reason: it.reason,
      }))
    );
    const itemsWithDetails = enrichedItems.map((e, i) => ({
      ...e,
      itemName: e.itemName || recoData.items[i]?.itemName,
      itemUrl: e.itemUrl || recoData.items[i]?.itemUrl,
      affiliateUrl: e.affiliateUrl || recoData.items[i]?.affiliateUrl,
      priceYen: e.priceYen ?? recoData.items[i]?.priceYen,
    }));

    return res.status(200).json({
      recommendationId: saved.recommendationId,
      contextId: saved.contextId,
      mode: mode,
      resolvedAlgorithm: {
        name: resolvedAlgorithm,
        params: recoData.resolved?.params ?? {},
      },
      items: itemsWithDetails,
    });
  } catch (err) {
    console.log("recommendations error:", err);
    return res.status(500).json({message: "Internal Server Error"});
  }
});
router.get("/list", (_req: Request, res: Response) => {
  // MVP では非提供（認証なしのため「自分の」一覧は取得不可）
  return res.status(404).json({message: "Not available in MVP"});
});

router.get("/:id", async(req: Request, res: Response) => {
  try {
      const id = req.params.id;

      // 1) header 取得（認証不要、recommendationId を知っていれば誰でも閲覧可能）
      const {data: header, error: hErr} = await supabaseAdmin
          .schema("apl")
          .from("recommendation")
          .select("*")
          .eq("id", id)
          .single();
      
      if(hErr) throw hErr;
      if(!header) return res.status(404).json({message: "Not found"});

      // 3) items 取得
      const {data: items, error: iErr} = await supabaseAdmin
          .schema("apl")
          .from("recommendation_item")
          .select("*")
          .eq("recommendation_id", id)
          .order("rank", { ascending: true });
      
      if(iErr) throw iErr;

      const rawItems = (items ?? []).map((r: any) => ({
        itemId: r.item_id,
        rank: r.rank ?? 0,
        score: r.score,
        reason: r.reason,
      }));
      const enrichedItems = await enrichItemsWithDetails(rawItems);
      
      // 4) context も返す（UI で表示・デバッグが便利）
      const {data: ctx, error: cErr} = await supabaseAdmin
          .schema("apl")
          .from("context")
          .select("*")
          .eq("id", header.context_id)
          .maybeSingle();
      
      if(cErr) throw cErr;
      
      return res.status(200).json({
          header,
          context: ctx,
          items: enrichedItems,
      });
  }catch(e) {
      console.error("GET /recommendations/:id", e);
      return res.status(500).json({ message: "Internal Server Error" });
  }
});

export default router;
