"""
Food AI For Gym Members — FastAPI Entry Point
Run: uvicorn main:app --host 0.0.0.0 --port 8001 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.meal_plan import router as meal_plan_router
import logging
import os

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Food AI For Gym Members",
    description="AI service tạo thực đơn 7 ngày cá nhân hóa cho người tập gym.",
    version="1.0.0",
)

# ─── CORS ────────────────────────────────────────────────────────────────────
_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(meal_plan_router)


# ─── Health check ────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "version": "1.0.0"}
