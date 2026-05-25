"""
Recommender - AI gợi ý món ăn (Content-based + Collaborative Filtering)
Author: AI Meal Planning System

Hai chiến lược chính:
  1. Content-based (Linear Programming / Greedy) — Cold start, user mới
  2. Collaborative Filtering (SVD) — User đã có ≥ 5 ratings
  3. Hybrid — Kết hợp CF predictions + ràng buộc dinh dưỡng
"""

import io
import os
import sys
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
from pulp import *

# CF imports — load FunkSVD class từ training script
try:
    import sys as _sys
    import importlib.util as _ilu
    _script = Path(__file__).parent.parent.parent / "train_collaborative_filter.py"
    if _script.exists():
        _spec = _ilu.spec_from_file_location("train_cf", _script)
        _mod  = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        FunkSVD = _mod.FunkSVD
        _CF_AVAILABLE = True
    else:
        _CF_AVAILABLE = False
except Exception:
    _CF_AVAILABLE = False

import logging

logger = logging.getLogger(__name__)


def load_nutrition_data(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Load dữ liệu dinh dưỡng từ CSV
    
    Args:
        filepath: Đường dẫn file CSV, nếu None sẽ dùng path mặc định
        
    Returns:
        DataFrame chứa dữ liệu món ăn
    """
    if filepath is None:
        # Default path
        filepath = Path(__file__).parent.parent.parent / "data" / "raw" / "nutrition_data.csv"
    
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        logger.info(f"✓ Load {len(df)} món ăn từ {filepath}")
        return df
    except FileNotFoundError:
        logger.error(f"✗ Không tìm thấy file: {filepath}")
        raise
    except Exception as e:
        logger.error(f"✗ Lỗi khi load data: {e}")
        raise


def filter_dishes_by_preferences(df: pd.DataFrame, user_profile: Dict) -> pd.DataFrame:
    """
    Lọc món ăn theo preferences của user
    
    Args:
        df: DataFrame chứa món ăn
        user_profile: Dict chứa preferences
            - allergens: List các allergens cần tránh
            - disliked_dishes: List món không thích
            
    Returns:
        DataFrame đã được lọc
    """
    filtered_df = df.copy()
    
    # Filter by allergens (nếu có)
    allergens = user_profile.get('allergens', [])
    if allergens:
        for allergen in allergens:
            # Simple string matching in dish name
            filtered_df = filtered_df[~filtered_df['name_vi'].str.contains(allergen, case=False, na=False)]
        logger.info(f"Lọc allergens: {allergens}")
    
    # Filter by disliked dishes
    disliked = user_profile.get('disliked_dishes', [])
    if disliked:
        for dish in disliked:
            filtered_df = filtered_df[~filtered_df['name_vi'].str.contains(dish, case=False, na=False)]
        logger.info(f"Lọc món không thích: {disliked}")
    
    logger.info(f"Còn lại {len(filtered_df)} món sau khi lọc")
    return filtered_df


def recommend_meals_simple(df: pd.DataFrame, user_profile: Dict) -> Dict:
    """
    Gợi ý thực đơn bằng phương pháp greedy/rule-based
    Đơn giản hơn Linear Programming nhưng nhanh và dễ implement
    
    Args:
        df: DataFrame chứa món ăn
        user_profile: Dict chứa target metrics
            - target_calories
            - protein_g
            - carbs_g
            - fat_g
            
    Returns:
        Dict chứa thực đơn 3 bữa + tổng kết
    """
    target_cal = user_profile.get('target_calories', 2000)
    target_protein = user_profile.get('protein_g', 200)
    target_carbs = user_profile.get('carbs_g', 150)
    target_fat = user_profile.get('fat_g', 67)
    
    # Tạo bản copy để tránh SettingWithCopyWarning
    df = df.copy()
    
    # Phân bổ cho 3 bữa
    meal_distribution = {
        'sáng': {'cal_pct': 0.25, 'protein_pct': 0.25},
        'trưa': {'cal_pct': 0.40, 'protein_pct': 0.40},
        'tối': {'cal_pct': 0.35, 'protein_pct': 0.35}
    }
    
    meal_plan = {}
    
    for meal_name, distribution in meal_distribution.items():
        target_meal_cal = target_cal * distribution['cal_pct']
        target_meal_protein = target_protein * distribution['protein_pct']
        
        # Tìm món gần nhất với target
        df['cal_diff'] = abs(df['calories'] - target_meal_cal)
        df['protein_diff'] = abs(df['protein_g'] - target_meal_protein)
        
        # Score: ưu tiên calories match, sau đó protein
        df['score'] = df['cal_diff'] + df['protein_diff'] * 0.5
        
        # Chọn món có score thấp nhất
        best_dish = df.nsmallest(1, 'score').iloc[0]
        
        meal_plan[meal_name] = {
            'món': best_dish['name_vi'],
            'calories': round(best_dish['calories'], 0),
            'protein': round(best_dish['protein_g'], 1),
            'carbs': round(best_dish['carbs_g'], 1),
            'fat': round(best_dish['fat_g'], 1),
            'giá_ước_tính': 35000  # Placeholder
        }
        
        # Loại món đã chọn để không trùng
        df = df[df['code'] != best_dish['code']]
    
    # Tổng kết
    total_cal = sum(meal['calories'] for meal in meal_plan.values())
    total_protein = sum(meal['protein'] for meal in meal_plan.values())
    total_carbs = sum(meal['carbs'] for meal in meal_plan.values())
    total_fat = sum(meal['fat'] for meal in meal_plan.values())
    
    # Tính % deviation
    cal_dev = abs(total_cal - target_cal) / target_cal * 100
    protein_dev = abs(total_protein - target_protein) / target_protein * 100
    avg_deviation = (cal_dev + protein_dev) / 2
    
    meal_plan['tổng_kết'] = {
        'total_calories': total_cal,
        'target_calories': target_cal,
        'total_protein': total_protein,
        'target_protein': target_protein,
        'total_carbs': total_carbs,
        'target_carbs': target_carbs,
        'total_fat': total_fat,
        'target_fat': target_fat,
        'deviation': round(avg_deviation, 1)
    }
    
    return meal_plan


def recommend_meals_linear_programming(df: pd.DataFrame, user_profile: Dict) -> Optional[Dict]:
    """
    Gợi ý thực đơn sử dụng Linear Programming với PuLP
    Tối ưu hóa để đạt target calories và macros
    
    Args:
        df: DataFrame chứa món ăn
        user_profile: Dict chứa target metrics
            
    Returns:
        Dict chứa thực đơn tối ưu hoặc None nếu không feasible
    """
    try:
        target_cal = user_profile.get('target_calories', 2000)
        target_protein = user_profile.get('protein_g', 200)
        target_carbs = user_profile.get('carbs_g', 150)
        target_fat = user_profile.get('fat_g', 67)
        
        # Create problem
        prob = LpProblem("Meal_Planning", LpMinimize)
        
        # Variables: x[i,j] = 1 nếu chọn món i cho bữa j
        meals = ['sáng', 'trưa', 'tối']
        dishes = list(df.index)
        
        # Decision variables
        x = LpVariable.dicts("dish", 
                            ((i, j) for i in dishes for j in meals),
                            cat='Binary')
        
        # Objective: Minimize deviation from target
        # Deviation variables
        cal_dev_pos = LpVariable("cal_dev_pos", lowBound=0)
        cal_dev_neg = LpVariable("cal_dev_neg", lowBound=0)
        protein_dev_pos = LpVariable("protein_dev_pos", lowBound=0)
        protein_dev_neg = LpVariable("protein_dev_neg", lowBound=0)
        
        # Objective function: minimize total deviation
        prob += cal_dev_pos + cal_dev_neg + protein_dev_pos + protein_dev_neg
        
        # Constraints
        
        # 1. Mỗi bữa chọn đúng 1 món
        for meal in meals:
            prob += lpSum([x[i, meal] for i in dishes]) == 1
        
        # 2. Mỗi món chỉ được chọn tối đa 1 lần
        for i in dishes:
            prob += lpSum([x[i, meal] for meal in meals]) <= 1
        
        # 3. Calories constraint với deviation
        total_calories = lpSum([df.loc[i, 'calories'] * x[i, j] 
                               for i in dishes for j in meals])
        prob += total_calories - cal_dev_pos + cal_dev_neg == target_cal
        
        # 4. Protein constraint với deviation
        total_protein = lpSum([df.loc[i, 'protein_g'] * x[i, j] 
                              for i in dishes for j in meals])
        prob += total_protein - protein_dev_pos + protein_dev_neg == target_protein
        
        # 5. Soft constraints cho carbs và fat (không bắt buộc strict)
        total_carbs = lpSum([df.loc[i, 'carbs_g'] * x[i, j] 
                            for i in dishes for j in meals])
        total_fat = lpSum([df.loc[i, 'fat_g'] * x[i, j] 
                          for i in dishes for j in meals])
        
        # Carbs trong khoảng ±20%
        prob += total_carbs >= target_carbs * 0.8
        prob += total_carbs <= target_carbs * 1.2
        
        # Fat trong khoảng ±20%
        prob += total_fat >= target_fat * 0.8
        prob += total_fat <= target_fat * 1.2
        
        # Solve
        prob.solve(PULP_CBC_CMD(msg=0))
        
        # Check if solution found
        if LpStatus[prob.status] != 'Optimal':
            logger.warning("Không tìm được giải pháp tối ưu, fallback sang greedy")
            return None
        
        # Extract solution
        meal_plan = {}
        
        for meal in meals:
            for i in dishes:
                if x[i, meal].varValue == 1:
                    dish_data = df.loc[i]
                    meal_plan[meal] = {
                        'món': dish_data['name_vi'],
                        'calories': round(dish_data['calories'], 0),
                        'protein': round(dish_data['protein_g'], 1),
                        'carbs': round(dish_data['carbs_g'], 1),
                        'fat': round(dish_data['fat_g'], 1),
                        'giá_ước_tính': 35000
                    }
        
        # Tổng kết
        total_cal = sum(meal['calories'] for meal in meal_plan.values())
        total_protein = sum(meal['protein'] for meal in meal_plan.values())
        total_carbs = sum(meal['carbs'] for meal in meal_plan.values())
        total_fat = sum(meal['fat'] for meal in meal_plan.values())
        
        cal_dev = abs(total_cal - target_cal) / target_cal * 100
        protein_dev = abs(total_protein - target_protein) / target_protein * 100
        avg_deviation = (cal_dev + protein_dev) / 2
        
        meal_plan['tổng_kết'] = {
            'total_calories': total_cal,
            'target_calories': target_cal,
            'total_protein': total_protein,
            'target_protein': target_protein,
            'total_carbs': total_carbs,
            'target_carbs': target_carbs,
            'total_fat': total_fat,
            'target_fat': target_fat,
            'deviation': round(avg_deviation, 1)
        }
        
        logger.info(f"✓ Tìm được thực đơn tối ưu (deviation: {avg_deviation:.1f}%)")
        return meal_plan
        
    except Exception as e:
        logger.error(f"✗ Lỗi khi chạy LP: {e}")
        return None


def recommend_meals(df: pd.DataFrame, user_profile: Dict, method: str = 'auto') -> Dict:
    """
    Main function để gợi ý thực đơn
    Tự động chọn phương pháp phù hợp
    
    Args:
        df: DataFrame chứa món ăn
        user_profile: Dict chứa user info và targets
        method: 'lp' (linear programming), 'simple' (greedy), 'auto' (tự chọn)
        
    Returns:
        Dict chứa thực đơn gợi ý
    """
    # Filter dishes theo preferences
    filtered_df = filter_dishes_by_preferences(df, user_profile)
    
    if len(filtered_df) < 3:
        raise ValueError("Không đủ món ăn sau khi lọc preferences!")
    
    # Chọn phương pháp
    if method == 'lp':
        result = recommend_meals_linear_programming(filtered_df, user_profile)
        if result is None:
            logger.warning("LP failed, fallback to simple method")
            result = recommend_meals_simple(filtered_df, user_profile)
    elif method == 'simple':
        result = recommend_meals_simple(filtered_df, user_profile)
    else:  # auto
        # Try LP first, fallback to simple if fails
        result = recommend_meals_linear_programming(filtered_df, user_profile)
        if result is None:
            result = recommend_meals_simple(filtered_df, user_profile)
    
    return result


# ══════════════════════════════════════════════════════════════════
# COLLABORATIVE FILTERING FUNCTIONS
# ══════════════════════════════════════════════════════════════════

# Đường dẫn model mặc định
_MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "cf_svd_model.pkl"

# Cache model trong bộ nhớ (load 1 lần duy nhất)
_svd_model_cache: Optional[object] = None


def load_cf_model(model_path: Optional[str] = None) -> Optional[object]:
    """
    Load FunkSVD model từ file .pkl.
    Cache trong biến module để tránh load nhiều lần.

    Returns:
        FunkSVD model object, hoặc None nếu chưa train.
    """
    global _svd_model_cache

    if _svd_model_cache is not None:
        return _svd_model_cache

    path = Path(model_path) if model_path else _MODEL_PATH
    if not path.exists():
        logger.warning(f"CF model chưa được train. File không tồn tại: {path}")
        return None

    try:
        with open(path, "rb") as f:
            payload = pickle.load(f)
        _svd_model_cache = payload["model"]
        meta = payload.get("metadata", {})
        logger.info(
            f"✓ Loaded CF model (RMSE={meta.get('cv_rmse', '?'):.4f}, "
            f"trained on {meta.get('n_ratings', '?')} ratings)"
        )
        return _svd_model_cache
    except Exception as e:
        logger.error(f"Lỗi khi load CF model: {e}")
        return None


def get_cf_food_scores(
    user_id: str,
    candidate_food_ids: List[str],
    model=None,
) -> Dict[str, float]:
    """
    Dùng FunkSVD model để dự đoán rating của user cho từng food.

    Args:
        user_id:           ID của user (string, như trong DB).
        candidate_food_ids: Danh sách food_id cần dự đoán.
        model:             FunkSVD model (nếu None sẽ tự load).

    Returns:
        Dict {food_id: predicted_rating} — rating trong thang 1–5.
    """
    if model is None:
        model = load_cf_model()
    if model is None:
        return {}

    # FunkSVD có predict_batch cho tốc độ
    if hasattr(model, "predict_batch"):
        return model.predict_batch(user_id, candidate_food_ids)

    # Fallback: loop từng food
    return {fid: model.predict(user_id, fid) for fid in candidate_food_ids}


def recommend_cf_top_n(
    user_id: str,
    all_foods_df: pd.DataFrame,
    rated_food_ids: List[str],
    n: int = 20,
    model=None,
) -> pd.DataFrame:
    """
    Gợi ý top-N món ăn cho user bằng Collaborative Filtering (SVD).

    Args:
        user_id:        ID của user.
        all_foods_df:   DataFrame chứa tất cả foods (cột: id, name, calories, ...).
        rated_food_ids: Danh sách food_id user đã từng đánh giá (loại khỏi kết quả).
        n:              Số món gợi ý muốn trả về.
        model:          SVD model (None = auto-load).

    Returns:
        DataFrame gồm top-N foods, sắp xếp theo predicted_rating giảm dần.
        Thêm cột 'predicted_rating'.
    """
    if model is None:
        model = load_cf_model()

    # Fallback: nếu không có model → trả về empty DataFrame
    if model is None:
        logger.warning(f"CF model không khả dụng cho user {user_id}. Dùng content-based.")
        return pd.DataFrame()

    # Lọc ra các foods user chưa đánh giá
    unrated_df = all_foods_df[~all_foods_df["id"].isin(rated_food_ids)].copy()
    if unrated_df.empty:
        logger.info(f"User {user_id} đã đánh giá hết tất cả foods.")
        return pd.DataFrame()

    # Dự đoán rating — dùng predict_batch nếu có
    if hasattr(model, "predict_batch"):
        scores = model.predict_batch(user_id, unrated_df["id"].tolist())
        unrated_df["predicted_rating"] = unrated_df["id"].map(scores)
    else:
        unrated_df["predicted_rating"] = unrated_df["id"].apply(
            lambda fid: model.predict(user_id, fid)
        )

    # Sắp xếp và trả về top-N
    result = unrated_df.nlargest(n, "predicted_rating").reset_index(drop=True)
    logger.info(
        f"CF gợi ý {len(result)} món cho user {user_id} "
        f"(top rated: {result.iloc[0]['name']} = {result.iloc[0]['predicted_rating']:.2f}⭐)"
    )
    return result


def decide_recommendation_strategy(n_user_ratings: int) -> str:
    """
    Quyết định chiến lược gợi ý dựa trên số ratings user đã có.

    Ngưỡng:
      < 5  ratings → content_based (cold start, dùng dinh dưỡng)
      5–14 ratings → hybrid       (CF + content-based, 50/50)
      ≥ 15 ratings → collaborative (CF chủ yếu + kiểm tra dinh dưỡng)

    Returns:
        'content_based' | 'hybrid' | 'collaborative'
    """
    if n_user_ratings < 5:
        return "content_based"
    elif n_user_ratings < 15:
        return "hybrid"
    else:
        return "collaborative"


def recommend_hybrid(
    user_id: str,
    all_foods_df: pd.DataFrame,
    rated_food_ids: List[str],
    user_profile: Dict,
    n_cf: int = 30,
    n_final: int = 21,
    model=None,
) -> pd.DataFrame:
    """
    Hybrid recommendation: kết hợp CF + ràng buộc dinh dưỡng.

    Luồng:
      1. CF → top-30 món theo predicted_rating
      2. Trong 30 món đó, lọc theo ràng buộc dinh dưỡng (goal)
      3. Trả về 21 món tốt nhất (7 ngày × 3 bữa)

    Args:
        user_id:        ID user.
        all_foods_df:   Tất cả foods.
        rated_food_ids: Foods user đã rate.
        user_profile:   Dict chứa goal_type, target_calories, v.v.
        n_cf:           Số món lấy từ CF trước khi filter.
        n_final:        Số món cuối cùng trả về.
        model:          SVD model.

    Returns:
        DataFrame gồm n_final foods phù hợp nhất.
    """
    # Bước 1: Lấy top-N từ CF
    cf_results = recommend_cf_top_n(user_id, all_foods_df, rated_food_ids, n=n_cf, model=model)

    if cf_results.empty:
        # Fallback: dùng content-based hoàn toàn
        logger.info(f"Hybrid fallback to content-based cho user {user_id}")
        return all_foods_df.sample(n=min(n_final, len(all_foods_df)))

    goal = user_profile.get("goal_type", 2)  # default: maintaining
    target_cal = float(user_profile.get("target_calories", 2000))

    # Bước 2: Áp dụng trọng số dinh dưỡng theo goal
    def nutrition_score(row):
        cal     = max(1.0, float(row["calories"]))
        protein = float(row["protein"])
        fat     = float(row["fat"])
        density = protein / cal * 100

        if goal == 0:   # cutting
            return density * 1.5 - (cal / target_cal) * 0.5
        elif goal == 1: # bulking
            return (cal / max(1, target_cal / 3)) * 0.5 + protein * 0.05
        else:           # maintaining
            return -(abs(cal - target_cal / 3) / target_cal) + protein * 0.02

    cf_results["nutrition_score"] = cf_results.apply(nutrition_score, axis=1)

    # Bước 3: Kết hợp CF score + nutrition score (trọng số 60/40)
    max_cf = cf_results["predicted_rating"].max()
    max_ns = cf_results["nutrition_score"].abs().max() or 1
    cf_results["combined_score"] = (
        (cf_results["predicted_rating"] / max_cf) * 0.60
        + (cf_results["nutrition_score"] / max_ns) * 0.40
    )

    return cf_results.nlargest(n_final, "combined_score").reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════
# Test function
# ══════════════════════════════════════════════════════════════════

# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test load data
    try:
        df = load_nutrition_data()
        print(f"Loaded {len(df)} dishes")
        print(df.head())
    except Exception as e:
        print(f"Error: {e}")

