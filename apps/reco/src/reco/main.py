import logging
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from reco.api.handlers import recommend
from reco.api.schemas import RecommendationRequest, RecommendationResponse

load_dotenv(dotenv_path="apps/reco/.env")

# ログ設定（標準出力へ出力、エラー調査を容易にする）
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reco Service", version="0.1.0")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """未捕捉の例外をログ出力して 500 を返す"""
    logger.exception(
        "unhandled exception path=%s method=%s error=%s",
        request.url.path,
        request.method,
        exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )

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
