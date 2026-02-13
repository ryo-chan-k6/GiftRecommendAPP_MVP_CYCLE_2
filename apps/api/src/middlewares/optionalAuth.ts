import type { Request, Response, NextFunction } from "express";
import { supabaseAuth } from "../lib/supabase";

/**
 * Authorization: Bearer <access_token> があれば検証して req.user を設定する。
 * トークンがない・無効な場合は req.user を設定せず next() を呼ぶ（401 にはしない）。
 */
export async function optionalAuth(
  req: Request,
  _res: Response,
  next: NextFunction
) {
  try {
    const authHeader = req.header("Authorization") ?? "";
    const m = authHeader.match(/^Bearer\s+(.+)$/i);

    if (!m) return next();

    const accessToken = m[1];
    const { data, error } = await supabaseAuth.auth.getUser(accessToken);

    if (error || !data?.user) return next();

    req.user = {
      id: data.user.id,
      email: data.user.email ?? undefined,
    };

    return next();
  } catch {
    return next();
  }
}
