import { Router, Request, Response } from "express";
import { requireAuth } from "../middlewares/requireAuth";
import {
  ALGORITHM_OVERRIDES,
  AlgorithmOverride,
  MODES,
} from "@/types/recommendation";
import { isAdmin } from "@/lib/admin";
import {supabaseAdmin} from "@/lib/supabase";
import {saveRecommendation} from "@/lib/recommendationRepo";
import {computeContextHash} from "@/lib/contextHash";

const router = Router();

router.post("/", requireAuth, async (req: Request, res: Response) => {
  try {
    const recoBaseUrl = process.env.RECO_BASE_URL;
    if (!recoBaseUrl) return res.status(500).json({ message: "RECO_BASE_URL is not set" });

    const userId = req.user?.id;
    if(!userId) return res.status(401).json({message: "Unauthenticated"});

    const body = req.body ?? {};

    const mode = body.mode;
    if (!MODES.includes(mode)) return res.status(400).json({message: "Invalid mode", allowed: MODES});

    // algorithmOverrride は ADMIN のみ許可（必要なときだけチェック）
    let algorithmOverride: string | null = null;
    if (body.algorithmOverride != null) {
      if(!ALGORITHM_OVERRIDES.includes(body.algorithmOverride)) {
        return res.status(400).json({message: "Invalid algorithmOverride", allowed: ALGORITHM_OVERRIDES})
      }
      const ok = await isAdmin(userId);
      if(!ok) return res.status(403).json({message: "algorithmOverride is allowed for ADMIN only"});
      algorithmOverride = body.algorithmOverride;
    }

    // reco へ送る payload (最低限)
    const recoPayload: any = {};
    recoPayload.mode = mode;
    recoPayload.eventId = body.eventId ?? null;
    recoPayload.recipientId = body.recipientId ?? null;
    recoPayload.budgetMin = body.budgetMin ?? null;
    recoPayload.budgetMax = body.budgetMax ?? null;
    recoPayload.featuresLike = body.featuresLike ?? [];
    recoPayload.featuresNotLike = body.featuresNotLike ?? [];
    recoPayload.featuresNg = body.featuresNg ?? [];
    if(algorithmOverride) recoPayload.algorithmOverride = algorithmOverride;

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
      userId: userId,
      eventId: body.eventId ?? null,
      recipientId: body.recipientId ?? null,
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

    // DB 保存
    const saved = await saveRecommendation({
      userId,
      context: {
        eventId: body.eventId ?? null,
        recipientId: body.recipientId ?? null,
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

    return res.status(200).json({
      recommendationId: saved.recommendationId,
      contextId: saved.contextId,
      mode: mode,
      resolvedAlgorithm: {
        name: resolvedAlgorithm,
        params: recoData.resolved?.params ?? {},
      },
      items: recoData.items,
    });
  } catch (err) {
    console.log("recommendations error:", err);
    return res.status(500).json({message: "Internal Server Error"});
  }
});
router.get("/list", requireAuth, async (req: Request, res:Response) => {
  try {
    const userId = req.user?.id;
    if(!userId) return res.status(401).json({message: "Unauthenticated"});

    const page = Math.max(1, Number(req.query.page ?? 1));
    const pageSize = Math.min(100, Math.max(1, Number(req.query.pageSize ?? 20)));
    const from = (page - 1) * pageSize;
    const to = from + pageSize - 1;

    // recommendation 一覧（合計件数も取る）
    const {data, error, count} = await supabaseAdmin
      .schema("apl")
      .from("recommendation")
      .select("id, user_id, context_id, algorithm, params, created_at", {count: "exact"})
      .eq("user_id", userId)
      .order("created_at", {ascending: false})
      .range(from, to)

    if(error) throw error;

    return res.status(200).json({
      items: data ?? [],
      page,
      pageSize,
      totalItems: count ?? 0,
      totalPages: Math.ceil((count ?? 0) / pageSize),
      hasNext: from + pageSize < (count ?? 0),
    });
  }catch (e) {
    console.log("GET /recommendations/list error:", e);
    return res.status(500).json({message: "Internal Server Error"});
  }
});

router.get("/:id", requireAuth, async(req: Request, res: Response) => {
  try {
      const userId = req.user?.id;
      if(!userId) return res.status(401).json({messaage: "Unauthenticated"});

      const id = req.params.id;

      // 1) header 取得
      const {data: header, error: hErr} = await supabaseAdmin
          .schema("apl")
          .from("recommendation")
          .select("*")
          .eq("id",id)
          .single();
      
      if(hErr) throw hErr;
      if(!header) return res.status(404).json({message: "Not found"});

      // 2) 自分のものだけ
      if(header.user_id !== userId) return res.status(403).json({message: "Forbidden"});

      // 3) items 取得
      const {data:items, error:iErr} = await supabaseAdmin
          .schema("apl")
          .from("recommendation_item")
          .select("*")
          .eq("recommendation_id", id)
          .order("rank", { ascending: true });
      
          if(iErr) throw iErr;
      
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
              items: items ?? [],
          });
  }catch(e) {
      console.error("GET /recommendations/:id", e);
      return res.status(500).json({ message: "Internal Server Error" });
  }
});

export default router;
