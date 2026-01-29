import { Request, Response, NextFunction } from "express";
import { supabaseAdmin } from "@/lib/supabase";

/**
 * requireAuth の後に使う前提
 * req.user.id を使って user_profile.role を確認
 */

export async function requireAdmin(
  req: Request,
  res: Response,
  next: NextFunction
) {
  try {
    const userId = req.user?.id;
    if (!userId) {
      return res.status(401).json({ message: "Unauthorized" });
    }

    const { data, error } = await supabaseAdmin
      .schema("apl")
      .from("user_profile")
      .select("role")
      .eq("id", userId)
      .single();

    if (error) {
      console.error("requireAdmin query error:", error);
      return res.status(500).json({ message: "Failed to check role" });
    }

    if (!data) {
      return res.status(403).json({ messega: "Profile not found" });
    }

    if (data.role !== "ADMIN") {
      return res.status(403).json({ message: "ADMIN only" });
    }

    return next();
  } catch (e) {
    console.error("requireAdmin error: ", e);
    return res.status(500).json({ message: "Admin middleware failed" });
  }
}
