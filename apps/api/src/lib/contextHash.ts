import crypto from "crypto";

function normArr(xs: unknown): string[] {
    if (!Array.isArray(xs)) return [];
    return xs
        .map((v) => String(v ?? "").trim())
        .filter((s) => s.length > 0)
        .sort((a, b) => a.localeCompare(b));
}

export function computeContextHash(input: {
    userId: string;
    eventId?: string | null;
    recipientId?: string | null;
    mode: string;
    budgetMin?: number | null;
    budgetMax?: number | null;
    featuresLike?: unknown;
    featuresNotLike?: unknown;
    featuresNg?: unknown;
    embeddingModel: string;
    embeddingVersion: number;
    embeddingContext: string;
}): string {
    const payload = {
        userId: input.userId,
        eventId: input.eventId ?? null,
        recipientId: input.recipientId ?? null,
        mode: input.mode,
        budgetMin: input.budgetMin ?? null,
        budgetMax: input.budgetMax ?? null,
        featuresLike: normArr(input.featuresLike),
        featuresNotLike: normArr(input.featuresNotLike),
        featuresNg: normArr(input.featuresNg),
        embeddingModel: input.embeddingModel,
        embeddingVersion: input.embeddingVersion,
        embeddingContext: input.embeddingContext,
    };
    
    return crypto.createHash("sha256").update(JSON.stringify(payload)).digest("hex");
}
