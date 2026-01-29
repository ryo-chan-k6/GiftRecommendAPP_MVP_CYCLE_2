import { Router } from "express";
import { requireAuth } from "@/middlewares/requireAuth";
import { requireAdmin } from "@/middlewares/requireAdmin";

const router = Router();

router.get("/ping", requireAuth, requireAdmin, (_req, res) => {
  res.status(200).json({ status: "ok", admin: true });
});

export default router;
