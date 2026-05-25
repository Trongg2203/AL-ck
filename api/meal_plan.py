"""
FastAPI router — Meal Plan endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from schemas.meal_plan import GenerateMealPlanRequest, GenerateMealPlanResponse
from services.meal_plan_service import MealPlanService
import logging
import os
import pickle

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Meal Plan"])

meal_plan_service = MealPlanService()

CF_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "cf_svd_model.pkl")


# ── Schemas for new endpoints ─────────────────────────────────────────────────

class RecommendTopNRequest(BaseModel):
    user_id: int
    food_ids: List[int]
    top_n: Optional[int] = 10


class FoodScore(BaseModel):
    food_id: int
    predicted_rating: float


class RecommendTopNResponse(BaseModel):
    user_id: int
    recommendations: List[FoodScore]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/generate-meal-plan", response_model=GenerateMealPlanResponse)
def generate_meal_plan(payload: GenerateMealPlanRequest):
    """
    Nhận dữ liệu user + danh sách món ăn từ Laravel,
    trả về meal plan 7 ngày cá nhân hóa.
    """
    try:
        result = meal_plan_service.generate(payload)
        return result
    except ValueError as e:
        logger.warning("Validation error in generate_meal_plan: %s", e)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in generate_meal_plan")
        raise HTTPException(status_code=500, detail="Internal AI service error.")


@router.get("/cf-status")
def cf_status():
    """
    Trả về trạng thái mô hình Collaborative Filtering (đã train chưa, metrics nếu có).
    """
    model_path = os.path.abspath(CF_MODEL_PATH)
    if not os.path.exists(model_path):
        return {"trained": False, "model_path": model_path, "metrics": None}

    try:
        with open(model_path, "rb") as f:
            model_data = pickle.load(f)
        metrics = model_data.get("metrics") if isinstance(model_data, dict) else None
        return {
            "trained": True,
            "model_path": model_path,
            "metrics": metrics,
        }
    except Exception as e:
        logger.exception("Error reading CF model")
        return {"trained": False, "error": str(e)}


@router.post("/recommend-top-n", response_model=RecommendTopNResponse)
def recommend_top_n(payload: RecommendTopNRequest):
    """
    Dự đoán rating cho danh sách food_ids theo user_id bằng CF model,
    trả về top-N món cao điểm nhất.
    """
    model_path = os.path.abspath(CF_MODEL_PATH)
    if not os.path.exists(model_path):
        raise HTTPException(status_code=503, detail="CF model chưa được train. Chạy train_collaborative_filter.py trước.")

    try:
        with open(model_path, "rb") as f:
            model_data = pickle.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể load CF model: {e}")

    # model_data should be a dict with 'model' key containing SVD object
    if isinstance(model_data, dict):
        model = model_data.get("model")
    else:
        model = model_data

    if model is None:
        raise HTTPException(status_code=500, detail="CF model không hợp lệ.")

    scores: List[FoodScore] = []
    for food_id in payload.food_ids:
        try:
            pred = model.predict(payload.user_id, food_id)
            scores.append(FoodScore(food_id=food_id, predicted_rating=round(float(pred), 4)))
        except Exception:
            scores.append(FoodScore(food_id=food_id, predicted_rating=3.0))

    scores.sort(key=lambda x: x.predicted_rating, reverse=True)
    top = scores[: payload.top_n]

    return RecommendTopNResponse(user_id=payload.user_id, recommendations=top)
