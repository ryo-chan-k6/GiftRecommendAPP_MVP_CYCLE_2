import type { Request, Response, NextFunction } from "express";
import { supabaseAuth } from "../lib/supabase";

export type AuthedUser = {
  id: string;
  email?: string;
};

declare global {
  namespace Express {
    interface Request {
      user?: AuthedUser;
    }
  }
}

/**
 * Autorization: Bearer <access_token>
 * を検証して req.user を作る
 */
export async function requireAuth(
  req: Request,
  res: Response,
  next: NextFunction
) {
  try {
    const authHeader = req.header("Authorization") ?? "";
    const m = authHeader.match(/^Bearer\s+(.+)$/i);

    if (!m) {
      return res
        .status(401)
        .json({ message: "Missing Autorization Bearer token" });
    }

    const accessToken = m[1];

    // Supabaseへ問い合わせてトークン検証 + user取得
    const { data, error } = await supabaseAuth.auth.getUser(accessToken);

    if (error || !data?.user) {
      return res.status(401).json({ message: "Invalid or expired token" });
    }

    req.user = {
      id: data.user.id,
      email: data.user.email ?? undefined,
    };

    return next();
  } catch (e) {
    console.log("requireAuth error:", e);
    return res.status(500).json({ message: "Auth middleware failed" });
  }
}
