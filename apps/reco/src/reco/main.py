from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.handlers import recommend
from api.schemas import RecommendationRequest, RecommendationResponse

load_dotenv(dotenv_path="apps/reco/.env")

app = FastAPI(title="Reco Service", version="0.1.0")

# CORS設定を追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切なオリジンを指定してください
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "reco",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.post("/recommendations", response_model=RecommendationResponse)
def recommendations(req: RecommendationRequest):
    return recommend(req)
