"""
Nutrition Scraper - Thu thập dữ liệu dinh dưỡng món ăn từ API Viện Dinh Dưỡng
Author: AI Meal Planning System
"""

import requests
import pandas as pd
import logging
import time
from tqdm import tqdm
from pathlib import Path
from typing import Optional, List, Dict
import os

# Setup logging
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = "https://viendinhduong.vn/api/fe/tool/getPageFoodData"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json'
}

# Category keywords không phù hợp cho gym (match theo substring, không cần khớp tuyệt đối)
EXCLUDED_CATEGORIES = [
    "đồ ngọt", "kẹo", "bánh kẹo",
    "nước ngọt", "giải khát", "bia", "rượu", "cồn",
    "fast food", "đồ ăn nhanh", "burger", "pizza",
    "chè", "kem", "caramen", "lẩu", "chế biến sẵn"
]

# Name keywords để loại các món có mật độ dinh dưỡng kém cho người tập gym
EXCLUDED_NAME_KEYWORDS = [
    "kem", "chè", "caramen", "trà sữa", "soda", "nước ngọt", "nước tăng lực",
    "rượu", "bia", "cocktail", "mocktail", "siro", "syrup",
    "kẹo", "bánh kẹo", "bánh ngọt", "socola", "chocolate",
    "chiên", "rán", "chiên giòn", "chiên xù", "chiên bơ", "chiên đường phố",
    "khoai tây chiên", "xúc xích", "lạp xưởng", "snack", "lẩu"
]


def fetch_dishes_page(page: int, page_size: int = 50) -> Optional[Dict]:
    """
    Gọi API để lấy dữ liệu món ăn theo trang
    
    Args:
        page: Số trang cần lấy (bắt đầu từ 1)
        page_size: Số món ăn mỗi trang
        
    Returns:
        Dict chứa data và total, hoặc None nếu có lỗi
    """
    try:
        params = {
            'page': page,
            'pageSize': page_size
        }
        
        logger.info(f"Đang fetch trang {page} (page_size={page_size})...")
        
        response = requests.get(
            API_BASE_URL, 
            params=params, 
            headers=HEADERS, 
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"✓ Lấy được {len(data.get('data', []))} món từ trang {page}")
        
        return data
        
    except requests.RequestException as e:
        logger.error(f"✗ Lỗi khi fetch trang {page}: {e}")
        return None
    except Exception as e:
        logger.error(f"✗ Lỗi không xác định: {e}")
        return None


def extract_nutrition_data(dish: Dict) -> tuple[Optional[Dict], Optional[Dict]]:
    """
    Trích xuất và làm sạch dữ liệu dinh dưỡng từ raw JSON
    
    Args:
        dish: Dict chứa thông tin món ăn từ API
        
    Returns:
        Tuple (valid_dish, incomplete_dish):
        - valid_dish: Dict với dữ liệu đầy đủ, hoặc None
        - incomplete_dish: Dict món thiếu calories, hoặc None
    """
    try:
        # Extract basic info
        dish_id = dish.get("_id", "")
        code = dish.get("code", "")
        name_vi = dish.get("name_vi", "").strip()
        category = dish.get("category_name", "Khác")
        
        # Kiểm tra calories - cẩn thận với nhiều kiểu dữ liệu
        total_energy_raw = dish.get("total_energy")
        
        # Check nếu có giá trị calories hợp lệ
        has_calories = False
        calories = 0.0
        
        if total_energy_raw is not None and total_energy_raw != "":
            try:
                calories = float(total_energy_raw)
                if calories > 0:
                    has_calories = True
            except (ValueError, TypeError):
                pass
        
        # Extract macros từ nutritional_components
        nutritional_components = dish.get("nutritional_components", [])
        
        protein_g = 0.0
        carbs_g = 0.0
        fat_g = 0.0
        
        for component in nutritional_components:
            component_name_vi = component.get("name", "").lower()
            component_name_en = component.get("nameEn", "").lower()
            amount_raw = component.get("amount", 0)
            
            # Handle empty string or invalid values
            try:
                amount = float(amount_raw) if amount_raw else 0.0
            except (ValueError, TypeError):
                amount = 0.0
            
            # Check both Vietnamese and English names
            name_combined = f"{component_name_vi} {component_name_en}"
            
            if "protein" in name_combined or "đạm" in name_combined:
                protein_g = amount
            elif "carbohydrate" in name_combined or "carb" in name_combined or "glucid" in name_combined:
                carbs_g = amount
            elif "fat" in name_combined or "lipid" in name_combined or "béo" in name_combined:
                fat_g = amount
        
        # Validate name
        if not name_vi:
            return None, None
        
        # Filter out nutritional components (not actual dishes)
        # These are micronutrients that got mixed in the API response
        invalid_names = [
            'năng lượng', 'energy', 'protein', 'chất đạm', 'fat', 'chất béo',
            'carbohydrate', 'glucid', 'vitamin', 'calcium', 'canxi', 'iron', 'sắt',
            'zinc', 'kẽm', 'sodium', 'natri', 'potassium', 'kali', 'magnesium', 'magie',
            'cholesterol', 'fiber', 'chất xơ', 'mufa', 'pufa'
        ]
        
        name_lower = name_vi.lower().strip()
        if any(invalid in name_lower for invalid in invalid_names) or len(name_vi.strip()) < 4:
            logger.debug(f"Skipping invalid dish: '{name_vi}'")
            return None, None
            
        if protein_g < 0 or carbs_g < 0 or fat_g < 0:
            return None, None
        
        dish_data = {
            "id": dish_id,
            "code": code,
            "name_vi": name_vi,
            "category": category,
            "calories": round(calories, 1) if has_calories else None,
            "protein_g": round(protein_g, 1),
            "carbs_g": round(carbs_g, 1),
            "fat_g": round(fat_g, 1)
        }
        
        # Tách riêng món có đủ calories và món thiếu calories
        if has_calories and calories > 0:
            return dish_data, None
        else:
            return None, dish_data
        
    except (KeyError, ValueError, TypeError) as e:
        logger.warning(f"Lỗi khi parse món ăn: {e}")
        return None, None


def filter_gym_friendly_dishes(dishes: List[Dict]) -> List[Dict]:
    """
    Lọc các món ăn phù hợp cho người tập gym.

    Tiêu chí:
    - Loại category thuộc nhóm đồ ngọt/đồ uống/fastfood.
    - Loại tên món có từ khóa món tráng miệng, đồ chiên rán, đồ uống có đường/cồn.
    - Giữ món có cấu hình dinh dưỡng hợp lý cho cutting/bulking/maintaining.
    """
    filtered = []
    excluded_by_category = 0
    excluded_by_name = 0
    excluded_by_nutrition = 0

    for dish in dishes:
        category = str(dish.get("category", "")).lower()
        name_vi = str(dish.get("name_vi", "")).lower()

        if any(excluded in category for excluded in EXCLUDED_CATEGORIES):
            excluded_by_category += 1
            continue

        if any(keyword in name_vi for keyword in EXCLUDED_NAME_KEYWORDS):
            excluded_by_name += 1
            continue

        protein = float(dish.get("protein_g", 0) or 0)
        carbs = float(dish.get("carbs_g", 0) or 0)
        fat = float(dish.get("fat_g", 0) or 0)
        calories = float(dish.get("calories", 0) or 0)

        if calories <= 0:
            excluded_by_nutrition += 1
            continue

        # Loại outlier sai scale khẩu phần (thường là phần ăn nhóm hoặc dữ liệu lỗi).
        if calories > 900 or protein > 90 or fat > 70 or carbs > 140:
            excluded_by_nutrition += 1
            continue

        # Loại món "empty calories": đạm quá thấp nhưng năng lượng cao.
        if protein < 2 and calories > 220:
            excluded_by_nutrition += 1
            continue

        high_protein_option = protein >= 12
        moderate_option = (80 <= calories <= 700) and (fat <= 30) and (carbs <= 90)

        if high_protein_option or moderate_option:
            filtered.append(dish)
        else:
            excluded_by_nutrition += 1

    logger.info(
        "Lọc từ %d → %d món gym-friendly (category=%d, name=%d, nutrition=%d)",
        len(dishes), len(filtered), excluded_by_category, excluded_by_name, excluded_by_nutrition
    )
    return filtered


def fetch_all_dishes(max_dishes: int = 500, categories_filter: Optional[List[str]] = None) -> tuple[List[Dict], List[Dict]]:
    """
    Fetch tất cả món ăn từ API (lấy 1 lần với page_size lớn)
    
    Args:
        max_dishes: Số món tối đa cần lấy (default 500 để lấy hết ~383 món)
        categories_filter: Danh sách categories cần lọc (nếu có)
        
    Returns:
        Tuple (valid_dishes, incomplete_dishes):
        - valid_dishes: Món có đủ calories (đã filter gym-friendly)
        - incomplete_dishes: Món thiếu calories
    """
    valid_dishes = []
    incomplete_dishes = []
    page_size = 500  # Lấy hết trong 1 lần
    max_retries = 3
    
    logger.info(f"Bắt đầu fetch dữ liệu (page_size={page_size})...")
    
    # Retry logic
    response_data = None
    for attempt in range(max_retries):
        response_data = fetch_dishes_page(page=1, page_size=page_size)
        
        if response_data:
            break
            
        if attempt < max_retries - 1:
            logger.warning(f"Retry {attempt + 1}/{max_retries}...")
            time.sleep(2)
    
    if not response_data:
        logger.error(f"Không thể fetch dữ liệu sau {max_retries} lần thử")
        return [], []
    
    # Get total from API
    total_available = response_data.get("total", 0)
    logger.info(f"API có tổng {total_available} món ăn")
    
    # Extract dishes
    raw_dishes = response_data.get("data", [])
    
    with tqdm(total=len(raw_dishes), desc="Đang xử lý dữ liệu") as pbar:
        for raw_dish in raw_dishes:
            valid_dish, incomplete_dish = extract_nutrition_data(raw_dish)
            if valid_dish:
                valid_dishes.append(valid_dish)
            if incomplete_dish:
                incomplete_dishes.append(incomplete_dish)
            pbar.update(1)
    
    logger.info(f"✓ Món có đủ dữ liệu: {len(valid_dishes)}")
    logger.info(f"⚠ Món thiếu calories: {len(incomplete_dishes)}")
    
    # Apply gym-friendly filter on valid dishes only
    filtered_dishes = filter_gym_friendly_dishes(valid_dishes)
    
    return filtered_dishes, incomplete_dishes


def save_to_csv(dishes: List[Dict], filename: str = "nutrition_data.csv") -> None:
    """
    Lưu dữ liệu món ăn vào CSV file
    
    Args:
        dishes: List các món ăn
        filename: Tên file CSV
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame(dishes)
        
        # Remove duplicates based on name_vi (giữ món có code mới nhất)
        # Sắp xếp theo calories giảm dần trước khi drop để ưu tiên món có calories cao hơn
        df = df.sort_values('calories', ascending=False)
        df = df.drop_duplicates(subset=['name_vi'], keep='first')
        
        # Sort by calories tăng dần cho output
        df = df.sort_values('calories', ascending=True)
        
        # Save to CSV
        data_dir = Path(__file__).parent.parent.parent / "data" / "raw"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = data_dir / filename
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        # Print summary
        logger.info(f"\n{'='*50}")
        logger.info(f"✓ Đã lưu {len(df)} món ăn vào {filepath}")
        logger.info(f"{'='*50}")
        logger.info(f"Thống kê:")
        logger.info(f"  - Calories: {df['calories'].min():.1f} - {df['calories'].max():.1f} kcal")
        logger.info(f"  - Protein: {df['protein_g'].min():.1f} - {df['protein_g'].max():.1f} g")
        logger.info(f"  - Categories: {df['category'].nunique()} loại")
        logger.info(f"{'='*50}\n")
        
    except Exception as e:
        logger.error(f"✗ Lỗi khi lưu CSV: {e}")
        raise


def save_incomplete_to_csv(dishes: List[Dict], filename: str = "incomplete_data.csv") -> None:
    """
    Lưu dữ liệu món ăn thiếu calories vào CSV file riêng
    
    Args:
        dishes: List các món ăn thiếu calories
        filename: Tên file CSV
    """
    try:
        if not dishes:
            logger.info("⚠ Không có món nào thiếu calories")
            return
            
        # Convert to DataFrame
        df = pd.DataFrame(dishes)
        
        # Remove duplicates based on code
        df = df.drop_duplicates(subset=['code'], keep='first')
        
        # Sort by name
        df = df.sort_values('name_vi', ascending=True)
        
        # Save to CSV
        data_dir = Path(__file__).parent.parent.parent / "data" / "raw"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = data_dir / filename
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        # Print summary
        logger.info(f"\n{'='*50}")
        logger.info(f"⚠ Đã lưu {len(df)} món thiếu calories vào {filepath}")
        logger.info(f"{'='*50}")
        logger.info(f"Thống kê:")
        logger.info(f"  - Protein: {df['protein_g'].min():.1f} - {df['protein_g'].max():.1f} g")
        logger.info(f"  - Carbs: {df['carbs_g'].min():.1f} - {df['carbs_g'].max():.1f} g")
        logger.info(f"  - Fat: {df['fat_g'].min():.1f} - {df['fat_g'].max():.1f} g")
        logger.info(f"  - Categories: {df['category'].nunique()} loại")
        logger.info(f"{'='*50}\n")
        
    except Exception as e:
        logger.error(f"✗ Lỗi khi lưu CSV: {e}")
        raise


def main():
    """Main function để chạy scraper"""
    logger.info("=" * 60)
    logger.info("BẮT ĐẦU THU THẬP DỮ LIỆU DINH DƯỠNG")
    logger.info("=" * 60)
    
    try:
        # Fetch dishes (lấy toàn bộ ~383 món)
        valid_dishes, incomplete_dishes = fetch_all_dishes(max_dishes=500)
        
        if not valid_dishes:
            logger.warning("Không lấy được món nào có đủ dữ liệu!")
        else:
            # Save valid dishes to CSV
            save_to_csv(valid_dishes)
        
        # Save incomplete dishes to separate CSV
        if incomplete_dishes:
            save_incomplete_to_csv(incomplete_dishes)
        
        logger.info("✓ Hoàn thành!")
        
    except Exception as e:
        logger.error(f"✗ Lỗi: {e}")
        raise


if __name__ == "__main__":
    main()
