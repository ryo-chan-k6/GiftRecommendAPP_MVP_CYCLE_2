import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { createClient } from "@supabase/supabase-js";
import recommendationsRouter from "@/routes/recommendations";
import adminRouter from "@/routes/admin";

dotenv.config();

const supabaseUrl = process.env.SUPABASE_URL || "";
const supabaseKey =
  process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || "";
const supabase =
  supabaseUrl && supabaseKey ? createClient(supabaseUrl, supabaseKey) : null;

const app = express();
app.use(express.json());
app.use(
  cors({
    origin: true,
    credentials: true,
  })
);

app.get("/health", async (_req, res) => {
  const health = {
    status: "ok",
    service: "api",
    timestamp: new Date().toISOString(),
    supabase: null as { connected: boolean; error?: string } | null,
  };
  return res.json(health);
});

app.use("/recommendations", recommendationsRouter);
app.use("/admin", adminRouter);

const PORT = Number(process.env.PORT) || 3001;

app.listen(PORT, () => {
  console.log(`🚀 API server running at http://localhost:${PORT}`);
});
