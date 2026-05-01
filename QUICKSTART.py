"""
Quick Start Guide - AI Meal Planning System
Hướng dẫn nhanh để bắt đầu sử dụng hệ thống
"""

# =============================================================================
# BƯỚC 1: CÀI ĐẶT
# =============================================================================

# 1.1. Cài đặt dependencies
"""
pip install -r requirements.txt
"""

# 1.2. Kiểm tra cài đặt
"""
python -c "import pandas, pulp, requests; print('✓ All dependencies OK!')"
"""

# =============================================================================
# BƯỚC 2: THU THẬP DỮ LIỆU
# =============================================================================

# 2.1. Lấy dữ liệu món ăn từ Viện Dinh Dưỡng
"""
python src/data_collection/nutrition_scraper.py
"""
# → File: data/raw/nutrition_data.csv (~200 món)

# 2.2. Lấy giá nguyên liệu (optional)
"""
python src/data_collection/price_scraper.py
"""
# → File: data/raw/ingredient_prices.csv

# =============================================================================
# BƯỚC 3: CHẠY DEMO
# =============================================================================

"""
python example_usage.py
"""

# =============================================================================
# BƯỚC 4: SỬ DỤNG TRONG CODE
# =============================================================================

from src.utils.calculator import get_user_metrics
from src.meal_planner.recommender import load_nutrition_data, recommend_meals

# Định nghĩa user profile
user = {
    'name': 'Your Name',
    'gender': 'Nam',  # hoặc 'Nữ'
    'age': 25,
    'height_cm': 175,
    'weight_kg': 70,
    'activity_level': 'moderate',  # sedentary/light/moderate/active/very_active
    'goal': 'cutting',  # cutting/bulking/maintain
    'protein_pct': 0.40,  # 40% protein
    'carbs_pct': 0.30,    # 30% carbs
    'fat_pct': 0.30,      # 30% fat
    'allergens': [],
    'disliked_dishes': []
}

# Tính metrics
metrics = get_user_metrics(user)
user.update(metrics)

# Load dữ liệu
df = load_nutrition_data()

# Gợi ý thực đơn
meal_plan = recommend_meals(df, user, method='simple')

# In kết quả
print("Thực đơn hôm nay:")
for meal, data in meal_plan.items():
    if meal != 'tổng_kết':
        print(f"{meal}: {data['món']} - {data['calories']:.0f} cal")

# =============================================================================
# CUSTOMIZATION
# =============================================================================

# Thay đổi mục tiêu
user['goal'] = 'bulking'  # Tăng cơ
metrics = get_user_metrics(user)

# Thay đổi macros ratio
user['protein_pct'] = 0.35
user['carbs_pct'] = 0.45
user['fat_pct'] = 0.20

# Thêm allergens
user['allergens'] = ['tôm', 'cua', 'sò']

# Thêm món không thích
user['disliked_dishes'] = ['gan', 'lòng', 'dồi']

# Chọn phương pháp gợi ý
meal_plan = recommend_meals(df, user, method='lp')  # Linear Programming
# hoặc
meal_plan = recommend_meals(df, user, method='simple')  # Greedy
# hoặc
meal_plan = recommend_meals(df, user, method='auto')  # Tự động chọn

# =============================================================================
# TROUBLESHOOTING
# =============================================================================

# Lỗi: "Module not found"
# → Cài lại: pip install -r requirements.txt

# Lỗi: "File not found nutrition_data.csv"
# → Chạy: python src/data_collection/nutrition_scraper.py

# Warning: SettingWithCopyWarning
# → Có thể ignore, không ảnh hưởng kết quả

# Thực đơn không tối ưu
# → Thử tăng số món ăn trong database
# → Điều chỉnh preferences (allergens, disliked_dishes)

# =============================================================================
# PROJECT STRUCTURE
# =============================================================================

"""
gym-meal-planner/
├── src/
│   ├── data_collection/
│   │   ├── nutrition_scraper.py    # Thu thập dữ liệu món ăn
│   │   └── price_scraper.py        # Thu thập giá nguyên liệu
│   ├── meal_planner/
│   │   └── recommender.py          # AI gợi ý thực đơn
│   └── utils/
│       └── calculator.py           # Tính BMI, BMR, TDEE
├── data/
│   ├── raw/
│   │   ├── nutrition_data.csv      # Dữ liệu món ăn
│   │   └── ingredient_prices.csv   # Giá nguyên liệu
│   └── processed/
├── logs/
│   └── scraper.log                 # Log file
├── example_usage.py                # Demo script
├── QUICKSTART.py                   # File này
├── requirements.txt                # Dependencies
└── README.md                       # Documentation
"""

# =============================================================================
# NEXT STEPS
# =============================================================================

# 1. Tạo weekly meal plan (thực đơn cả tuần)
# 2. Tạo web interface với Streamlit
# 3. Export thực đơn ra PDF
# 4. Tích hợp với grocery shopping list
# 5. Add meal prep instructions

print("✅ Xem file này để biết cách sử dụng nhanh!")
