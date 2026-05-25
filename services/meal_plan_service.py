"""
MealPlanService — Tạo meal plan 7 ngày cá nhân hóa.

Thuật toán (Content-based / Hybrid / Collaborative Filtering):
1. Lọc món ăn: loại bỏ allergens & disliked_foods.
2. Quyết định strategy dựa trên số ratings của user:
   - < 5 ratings  → content_based (cold start)
   - 5–14 ratings → hybrid (CF 60% + content 40%)
   - ≥ 15 ratings → collaborative (CF 80% + content 20%)
3. Phân bổ mỗi ngày thành 3 bữa chính (sáng 25%, trưa 40%, tối 35%).
4. Chọn món dựa trên combined score (CF + dinh dưỡng).
5. Chống trùng lặp: mỗi món chỉ được dùng tối đa 2 lần trong 7 ngày.
6. Điều chỉnh servings để đạt target calo cho từng bữa.
7. Trả về cấu trúc days[] theo schema Laravel yêu cầu.
"""

import random
import logging
from typing import List, Dict, Optional

from schemas.meal_plan import (
    FoodItem,
    GenerateMealPlanRequest,
    GenerateMealPlanResponse,
    DayPlan,
    MealItem,
)

# CF imports — graceful fallback nếu recommender không khả dụng
try:
    from src.meal_planner.recommender import (
        decide_recommendation_strategy,
        get_cf_food_scores,
        load_cf_model,
    )
    _CF_MODULE_AVAILABLE = True
except ImportError:
    _CF_MODULE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Phân bổ calo theo bữa
MEAL_DISTRIBUTION = {
    1: 0.25,   # breakfast
    2: 0.40,   # lunch
    3: 0.35,   # dinner
}

# Macro priority weights theo goal_type
# goal 0=cutting: ưu tiên protein cao, fat thấp
# goal 1=bulking: ưu tiên carbs cao, protein vừa
# goal 2=maintaining: cân bằng
MACRO_WEIGHTS = {
    0: {"protein": 0.5, "carbs": 0.3, "fat": 0.2},   # cutting
    1: {"protein": 0.3, "carbs": 0.5, "fat": 0.2},   # bulking
    2: {"protein": 0.35, "carbs": 0.40, "fat": 0.25}, # maintaining
}

# CF blend weights: how much CF score influences selection
CF_BLEND = {
    "content_based":  0.0,   # pure content
    "hybrid":         0.6,   # 60% CF + 40% content
    "collaborative":  0.8,   # 80% CF + 20% content
}

# Maps strategy → generation_method int
STRATEGY_TO_METHOD = {
    "content_based": 1,
    "hybrid":        0,
    "collaborative": 2,
}

MIN_FOODS_PER_MEAL = 3   # Số món tối thiểu để chọn được bữa đó


class MealPlanService:

    def generate(self, payload: GenerateMealPlanRequest) -> GenerateMealPlanResponse:
        """
        Entry point: tạo meal plan 7 ngày.
        """
        foods = payload.foods
        if not foods:
            raise ValueError("Không có dữ liệu món ăn. Hãy import dữ liệu vào DB trước.")

        # Bước 1 — Lọc allergens & disliked
        foods = self._filter_foods(foods, payload.allergens, payload.disliked_foods)

        if len(foods) < MIN_FOODS_PER_MEAL * 3:
            raise ValueError(
                f"Không đủ món ăn sau khi lọc (còn {len(foods)} món). "
                "Hãy giảm bớt điều kiện lọc hoặc bổ sung thêm món vào DB."
            )

        # Bước 2 — Quyết định strategy (content / hybrid / collaborative)
        strategy = "content_based"
        cf_scores: Dict[str, float] = {}

        if _CF_MODULE_AVAILABLE:
            strategy = decide_recommendation_strategy(payload.n_user_ratings)
            cf_blend = CF_BLEND.get(strategy, 0.0)

            if cf_blend > 0:
                # Load CF model và lấy predicted scores cho tất cả foods
                cf_model = load_cf_model()
                if cf_model is not None:
                    all_food_ids = [f.id for f in foods]
                    cf_scores = get_cf_food_scores(payload.user_id, all_food_ids, cf_model)
                    logger.info(
                        "CF strategy=%s | user=%s | rated=%d | cf_scores=%d foods",
                        strategy, payload.user_id, payload.n_user_ratings, len(cf_scores),
                    )
                else:
                    # Model chưa train → fallback về content_based
                    strategy = "content_based"
                    cf_blend = 0.0
                    logger.warning("CF model không khả dụng, fallback sang content_based")
            else:
                cf_blend = 0.0
        else:
            cf_blend = 0.0
            logger.info("CF module không available, dùng content_based")

        generation_method = STRATEGY_TO_METHOD.get(strategy, 1)

        # Đặt usage_count = 0 cho từng món
        usage_count: Dict[str, int] = {f.id: 0 for f in foods}
        max_uses = max(2, 14 // len(foods) + 1)

        weights = MACRO_WEIGHTS.get(payload.goal_type, MACRO_WEIGHTS[2])

        days: List[DayPlan] = []

        for day_number in range(1, 8):
            day_meals: List[MealItem] = []
            # food_ids already used *today* — used to avoid repeating the same
            # dish across breakfast/lunch/dinner of a single day.
            day_used: set = set()
            day_cal = day_prot = day_carbs = day_fat = 0.0

            for meal_type, cal_ratio in MEAL_DISTRIBUTION.items():
                target_cal = payload.target_calories * cal_ratio

                # 1) Prefer foods NOT used today and under the weekly cap.
                candidates = self._get_candidates(
                    foods, meal_type, usage_count, max_uses, exclude_ids=day_used
                )

                # 2) Relax the weekly cap, but still avoid same-day repeats.
                if not candidates:
                    candidates = self._get_candidates(
                        foods, meal_type, usage_count, max_uses * 2, exclude_ids=day_used
                    )

                # 3) Last resort only: allow a food already used today — i.e. when
                #    there is genuinely no other option left for this meal.
                if not candidates:
                    candidates = self._get_candidates(
                        foods, meal_type, usage_count, max_uses * 2
                    )

                if not candidates:
                    logger.warning("Day %d, meal_type %d: không đủ candidates", day_number, meal_type)
                    continue

                # Chọn món tốt nhất theo combined score (content + CF)
                best = self._pick_best(
                    candidates, target_cal, weights, payload,
                    cf_scores=cf_scores, cf_blend=cf_blend,
                )

                # Tính servings để đạt target calo
                servings = self._calc_servings(best, target_cal)
                servings = round(max(0.5, min(servings, 5.0)), 2)

                total_cal  = round(best.calories * servings, 2)
                total_prot = round(best.protein * servings, 2)
                total_carb = round(best.carbs * servings, 2)
                total_fat  = round(best.fat * servings, 2)

                day_meals.append(MealItem(
                    food_id=best.id,
                    food_name=best.name,
                    meal_type=meal_type,
                    servings=servings,
                    total_calories=total_cal,
                    total_protein=total_prot,
                    total_carbs=total_carb,
                    total_fat=total_fat,
                ))

                usage_count[best.id] += 1
                day_used.add(best.id)
                day_cal   += total_cal
                day_prot  += total_prot
                day_carbs += total_carb
                day_fat   += total_fat

            days.append(DayPlan(
                day_number=day_number,
                meals=day_meals,
                day_calories=round(day_cal, 2),
                day_protein=round(day_prot, 2),
                day_carbs=round(day_carbs, 2),
                day_fat=round(day_fat, 2),
            ))

        # Tính trung bình tuần
        n = len(days) or 1
        avg_cal   = round(sum(d.day_calories for d in days) / n, 2)
        avg_prot  = round(sum(d.day_protein for d in days) / n, 2)
        avg_carbs = round(sum(d.day_carbs for d in days) / n, 2)
        avg_fat   = round(sum(d.day_fat for d in days) / n, 2)

        logger.info(
            "Generated 7-day meal plan | user=%s | strategy=%s | avg_cal=%.1f (target=%.1f)",
            payload.user_id, strategy, avg_cal, payload.target_calories,
        )

        return GenerateMealPlanResponse(
            generation_method=generation_method,
            days=days,
            weekly_avg_calories=avg_cal,
            weekly_avg_protein=avg_prot,
            weekly_avg_carbs=avg_carbs,
            weekly_avg_fat=avg_fat,
        )

    # ─── Private helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _filter_foods(
        foods: List[FoodItem],
        allergens: List[str],
        disliked: List[str],
    ) -> List[FoodItem]:
        """Lọc bỏ món có chứa allergen hoặc trong danh sách không thích."""
        filtered = []
        block_terms = [t.lower() for t in allergens + disliked]
        for f in foods:
            name_lower = f.name.lower()
            if not any(term in name_lower for term in block_terms):
                filtered.append(f)
        logger.info(
            "Filtered foods: %d → %d (blocked terms: %s)",
            len(foods), len(filtered), block_terms,
        )
        return filtered

    @staticmethod
    def _get_candidates(
        foods: List[FoodItem],
        meal_type: int,
        usage_count: Dict[str, int],
        max_uses: int,
        exclude_ids: Optional[set] = None,
    ) -> List[FoodItem]:
        """
        Lấy candidates cho meal_type cụ thể,
        lọc theo meal_type (0=any, hoặc đúng meal_type),
        chưa vượt max_uses, và không nằm trong exclude_ids
        (dùng để tránh lặp món trong cùng một ngày).
        """
        exclude_ids = exclude_ids or set()
        return [
            f for f in foods
            if (f.meal_type == 0 or f.meal_type == meal_type)
            and usage_count.get(f.id, 0) < max_uses
            and f.id not in exclude_ids
            and f.calories > 0
        ]

    @staticmethod
    def _pick_best(
        candidates: List[FoodItem],
        target_cal: float,
        weights: Dict[str, float],
        payload: GenerateMealPlanRequest,
        cf_scores: Dict[str, float] = None,
        cf_blend: float = 0.0,
    ) -> FoodItem:
        """
        Score từng candidate bằng combined score:
          content_score = macro_fit - cal_penalty + popularity_bonus
          cf_score      = predicted_rating từ FunkSVD (thang 1–5, normalize về 0–1)
          final_score   = (1 - cf_blend) * content_score + cf_blend * cf_score + jitter
        """
        if cf_scores is None:
            cf_scores = {}

        target_prot  = payload.protein_grams / 3 or 1
        target_carbs = payload.carbs_grams / 3 or 1
        target_fat   = payload.fat_grams / 3 or 1

        scored = []
        for food in candidates:
            # Content-based score
            prot_score  = min(food.protein / target_prot, 1.5)  * weights["protein"]
            carbs_score = min(food.carbs / target_carbs, 1.5) * weights["carbs"]
            fat_score   = min(food.fat / target_fat, 1.5)     * weights["fat"]

            cal_dev     = abs(food.calories - target_cal) / (target_cal or 1)
            cal_penalty = cal_dev * 0.3
            pop_bonus   = min(food.popularity_score / 100, 0.2)

            content_score = prot_score + carbs_score + fat_score - cal_penalty + pop_bonus

            # CF score (normalize 1–5 → 0–1)
            if cf_blend > 0 and food.id in cf_scores:
                raw_cf = cf_scores[food.id]
                cf_score = (min(max(raw_cf, 1.0), 5.0) - 1.0) / 4.0
            else:
                cf_score = 0.0

            # Combined score
            jitter      = random.uniform(0, 0.05)
            total_score = (1 - cf_blend) * content_score + cf_blend * cf_score + jitter

            scored.append((total_score, food))

        # Chọn top-3 rồi random → vừa tối ưu vừa đa dạng
        scored.sort(key=lambda x: x[0], reverse=True)
        top_k = scored[: min(3, len(scored))]
        return random.choice(top_k)[1]

    @staticmethod
    def _calc_servings(food: FoodItem, target_cal: float) -> float:
        """Tính số serving cần để đạt target calo."""
        if food.calories <= 0:
            return 1.0
        return target_cal / food.calories
