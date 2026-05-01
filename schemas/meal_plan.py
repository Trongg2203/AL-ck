"""
Pydantic schemas cho FastAPI endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class FoodItem(BaseModel):
    id: str
    category_id: str
    name: str
    serving_size: float
    serving_unit: str = "g"
    calories: float
    protein: float
    carbs: float
    fat: float
    meal_type: int = 0          # 0=any, 1=breakfast, 2=lunch, 3=dinner, 4=snack
    popularity_score: int = 0


class GenerateMealPlanRequest(BaseModel):
    user_id: str
    goal_type: int              # 0=cutting, 1=bulking, 2=maintaining
    target_calories: float
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    allergens: List[str] = Field(default_factory=list)
    disliked_foods: List[str] = Field(default_factory=list)
    foods: List[FoodItem]
    rated_food_ids: List[str] = Field(default_factory=list)   # Foods user has rated (for CF)
    n_user_ratings: int = 0                                    # Total ratings count (decides strategy)


class MealItem(BaseModel):
    food_id: str
    food_name: str
    meal_type: int              # 1=breakfast, 2=lunch, 3=dinner, 4=snack
    servings: float
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float


class DayPlan(BaseModel):
    day_number: int             # 1-7
    meals: List[MealItem]
    day_calories: float
    day_protein: float
    day_carbs: float
    day_fat: float


class GenerateMealPlanResponse(BaseModel):
    generation_method: int      # 0=hybrid, 1=content_based, 2=collaborative
    days: List[DayPlan]
    weekly_avg_calories: float
    weekly_avg_protein: float
    weekly_avg_carbs: float
    weekly_avg_fat: float


class RatingMatrixItem(BaseModel):
    user_id: str
    food_id: str
    rating: int


class HealthResponse(BaseModel):
    status: str
    version: str
