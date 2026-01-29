import {supabaseAdmin} from "@/lib/supabase";

export type SaveRecoArgs = {
    userId: string;

    // context （保存したい条件一式）
    context: {
        eventId?: string | null;
        recipientId?: string | null;
        budgetMin?: number | null;
        budgetMax?: number | null;

        featuresLike: string[];
        featuresNotLike: string[];
        featuresNg: string[];

        embeddingContext: string;
        embeddingModel: string;
        embeddingVersion: number;
        contextHash: string;

        // pgvector は当面 null
        contextVector?: null;
    };

    // recommendation header
    algorithm: string;
    params: any; //jsob

    //recommendation items
    items: Array<{
        itemId: string;
        rank: number;
        score: number;
        vectorScore?: number | null;
        rerankScore?: number | null;
        reason?: any;
    }>;
};

export async function saveRecommendation(args: SaveRecoArgs) {
    // 1) context upsert (同一条件は再利用)
    const {data:ctx, error: ctxErr} = await supabaseAdmin
        .schema("apl")
        .from("context")
        .upsert(
            {
                user_id: args.userId,
                event_id: args.context.eventId,
                recipient_id: args.context.recipientId,
                budget_min: args.context.budgetMin,
                budget_max: args.context.budgetMax,
                features_like: args.context.featuresLike,
                features_not_like: args.context.featuresNotLike,
                features_ng: args.context.featuresNg,
                context_text: args.context.embeddingContext,
                context_vector: null,
                embedding_model: args.context.embeddingModel,
                embedding_version: args.context.embeddingVersion,
                context_hash: args.context.contextHash,
            },
            {onConflict: "context_hash"}
        )
        .select("id")
        .single();
    
    if(ctxErr) throw ctxErr;
    const contextId = ctx.id as string;
    
    // 2) recommendation insert (ヘッダー)
    const {data: rec, error: recErr} = await supabaseAdmin
        .schema("apl")
        .from("recommendation")
        .insert({
            user_id: args.userId,
            context_id: contextId,
            algorithm: args.algorithm,
            params: args.params,
        })
        .select("id")
        .single();
    
    if(recErr) throw recErr;
    const recommendationId = rec.id as string;

    // 3) recommendation_item insert (明細)
    const rows = args.items.map((item) => ({
        recommendation_id: recommendationId,
        item_id: item.itemId,
        rank: item.rank,
        score: item.score,
        vector_score: item.vectorScore ?? null,
        rerank_score: item.rerankScore ?? null,
        reason: item.reason ?? null,
    }));

    const {error: recItemsErr} = await supabaseAdmin
        .schema("apl")
        .from("recommendation_item")
        .insert(rows)
        .select("id");
    
    if(recItemsErr) throw recItemsErr;

    return {contextId, recommendationId};
};
