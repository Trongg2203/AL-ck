"""
HƯỚNG DẪN SỬ DỤNG VÀ TEST HỆ THỐNG AI MEAL PLANNING
====================================================

File này hướng dẫn chi tiết cách sử dụng và test các tính năng AI.

Author: AI Meal Planning System
Date: 2025-10-17
"""

print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║        🏋️  AI MEAL PLANNING SYSTEM - HƯỚNG DẪN SỬ DỤNG             ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝

📚 MỤC LỤC:
-----------
1. Cài đặt và Setup
2. Cách chạy Test Cases
3. Cách tạo User Profile
4. Giải thích các tham số
5. Troubleshooting

═══════════════════════════════════════════════════════════════════════

📦 1. CÀI ĐẶT VÀ SETUP
═══════════════════════════════════════════════════════════════════════

Bước 1: Cài đặt dependencies
-----------------------------
$ pip install -r requirements.txt

Packages cần thiết:
- pandas        : Xử lý data
- numpy         : Tính toán
- PuLP          : Linear Programming (AI optimization)
- requests      : HTTP requests
- beautifulsoup4: Web scraping

Bước 2: Thu thập dữ liệu món ăn
--------------------------------
$ python src/data_collection/nutrition_scraper.py

File output: data/raw/nutrition_data.csv (~200 món ăn)


═══════════════════════════════════════════════════════════════════════

🧪 2. CÁCH CHẠY TEST CASES
═══════════════════════════════════════════════════════════════════════

A. Chạy TẤT CẢ test cases (Khuyến nghị)
----------------------------------------
$ python test_ai_features.py

Kết quả:
- Test 10 kịch bản khác nhau
- In ra thông tin chi tiết từng test
- Tổng kết cuối cùng: X/10 tests passed

B. Chạy từng test case riêng lẻ
-------------------------------
Mở file test_ai_features.py, chỉnh sửa phần cuối:

if __name__ == "__main__":
    # Chạy 1 test cụ thể
    test_case_1_cutting_male()
    # hoặc
    test_case_4_with_allergens()

C. Demo nhanh với data mẫu
---------------------------
$ python test_data_samples.py

Xem danh sách 17 profiles mẫu + demo quick test

D. Demo user datchu784
----------------------
$ python example_usage.py

Demo hoàn chỉnh cho user datchu784


═══════════════════════════════════════════════════════════════════════

👤 3. CÁCH TẠO USER PROFILE
═══════════════════════════════════════════════════════════════════════

Template cơ bản:
----------------
user_profile = {
    # THÔNG TIN CÁ NHÂN (Required)
    'name': 'TênUser',              # Tên
    'gender': 'Nam',                # 'Nam' hoặc 'Nữ'
    'age': 25,                      # Tuổi
    'height_cm': 170,               # Chiều cao (cm)
    'weight_kg': 65,                # Cân nặng (kg)
    
    # MỨC ĐỘ VẬN ĐỘNG (Required)
    'activity_level': 'moderate',
    
    # MỤC TIÊU (Required)
    'goal': 'cutting',
    
    # MACROS (Required)
    'protein_pct': 0.40,            # 40% Protein
    'carbs_pct': 0.30,              # 30% Carbs
    'fat_pct': 0.30,                # 30% Fat (Tổng = 100%)
    
    # PREFERENCES (Optional)
    'allergens': [],                # Danh sách món dị ứng
    'disliked_dishes': []           # Danh sách món không thích
}


═══════════════════════════════════════════════════════════════════════

📊 4. GIẢI THÍCH CÁC THAM SỐ
═══════════════════════════════════════════════════════════════════════

A. ACTIVITY LEVEL (Mức độ vận động)
------------------------------------
'sedentary'    : Ít vận động, ngồi nhiều (x1.2)
'light'        : Nhẹ, tập 1-3 ngày/tuần (x1.375)
'moderate'     : Trung bình, tập 3-5 ngày/tuần (x1.55)
'active'       : Nặng, tập 6-7 ngày/tuần (x1.725)
'very_active'  : Rất nặng, tập 2 buổi/ngày (x1.9)

B. GOAL (Mục tiêu)
------------------
'cutting'  : Giảm mỡ (-500 cal/ngày = -0.5kg/tuần)
'bulking'  : Tăng cơ (+300 cal/ngày = +0.3kg/tuần)
'maintain' : Duy trì (= TDEE)

C. MACROS PERCENTAGES
----------------------
Tổng protein_pct + carbs_pct + fat_pct PHẢI = 1.0 (100%)

Gợi ý theo mục tiêu:

Cutting (Giảm mỡ):
- Protein: 40% (cao để giữ cơ)
- Carbs: 30% (thấp)
- Fat: 30%

Bulking (Tăng cơ):
- Protein: 35%
- Carbs: 45% (cao để năng lượng)
- Fat: 20%

Maintain (Duy trì):
- Protein: 30%
- Carbs: 40%
- Fat: 30%

Keto Diet:
- Protein: 30%
- Carbs: 10% (rất thấp)
- Fat: 60% (rất cao)

D. ALLERGENS & DISLIKED DISHES
-------------------------------
Ví dụ:
'allergens': ['tôm', 'cua', 'mực']
'disliked_dishes': ['trứng', 'sữa chua', 'cháo']

Hệ thống sẽ lọc các món có chứa từ khóa này.


═══════════════════════════════════════════════════════════════════════

🔍 5. HIỂU KẾT QUẢ OUTPUT
═══════════════════════════════════════════════════════════════════════

A. METRICS OUTPUT
-----------------
BMI     : Body Mass Index (chỉ số khối cơ thể)
          < 18.5: Thiếu cân
          18.5-24.9: Bình thường
          25-29.9: Thừa cân
          ≥ 30: Béo phì

BMR     : Basal Metabolic Rate (năng lượng cơ bản cơ thể cần)
TDEE    : Total Daily Energy Expenditure (tổng năng lượng tiêu thụ)
Target  : Số calories cần ăn mỗi ngày để đạt mục tiêu

B. MEAL PLAN OUTPUT
-------------------
Mỗi bữa có:
- Món: Tên món ăn
- Calories: Lượng calo
- Protein/Carbs/Fat: Lượng macro (gram)
- Giá ước tính: Giá tiền (VNĐ)

Tổng kết:
- Total vs Target: So sánh tổng vs mục tiêu
- Deviation: Độ lệch (%)
  < 10%: Rất tốt ✅
  10-20%: Chấp nhận được ⚠️
  > 20%: Cần điều chỉnh ❌

C. AI METHODS
-------------
Auto mode sẽ tự chọn:
1. Linear Programming (LP): Tối ưu hóa toán học
   - Chính xác cao
   - Tìm solution tốt nhất
   - Có thể fail nếu không feasible

2. Greedy (Simple): Thuật toán tham lam
   - Nhanh, đơn giản
   - Luôn có kết quả
   - Độ chính xác thấp hơn LP


═══════════════════════════════════════════════════════════════════════

🎯 6. EXAMPLES - VÍ DỤ CỤ THỂ
═══════════════════════════════════════════════════════════════════════

Example 1: User cơ bản
----------------------
from test_data_samples import CUTTING_MALE
from src.utils.calculator import get_user_metrics
from src.meal_planner.recommender import load_nutrition_data, recommend_meals

# Load profile
profile = CUTTING_MALE

# Calculate metrics
metrics = get_user_metrics(profile)
print(f"Target calories: {metrics['target_calories']} cal")

# Generate meal plan
df = load_nutrition_data()
meal_plan = recommend_meals(df, metrics, method='auto')

# Print result
for meal, data in meal_plan.items():
    if meal != 'tổng_kết':
        print(f"{meal}: {data['món']}")


Example 2: Custom profile với allergens
----------------------------------------
my_profile = {
    'name': 'MyName',
    'gender': 'Nam',
    'age': 25,
    'height_cm': 175,
    'weight_kg': 70,
    'activity_level': 'moderate',
    'goal': 'cutting',
    'protein_pct': 0.40,
    'carbs_pct': 0.30,
    'fat_pct': 0.30,
    'allergens': ['tôm', 'cua'],  # Dị ứng hải sản
    'disliked_dishes': ['trứng']   # Không thích trứng
}

# Tính toán và gợi ý
metrics = get_user_metrics(my_profile)
df = load_nutrition_data()
meal_plan = recommend_meals(df, metrics)


Example 3: So sánh 2 phương pháp
---------------------------------
# Linear Programming
meal_plan_lp = recommend_meals(df, metrics, method='lp')

# Greedy
meal_plan_greedy = recommend_meals(df, metrics, method='simple')

# Compare
print(f"LP Deviation: {meal_plan_lp['tổng_kết']['deviation']}%")
print(f"Greedy Deviation: {meal_plan_greedy['tổng_kết']['deviation']}%")


═══════════════════════════════════════════════════════════════════════

❓ 7. TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════

Problem: "Không tìm thấy file nutrition_data.csv"
Solution: Chạy scraper trước:
$ python src/data_collection/nutrition_scraper.py

---

Problem: "Tổng % macros phải = 100%"
Solution: Kiểm tra lại protein_pct + carbs_pct + fat_pct = 1.0

---

Problem: "Không đủ món ăn sau khi lọc preferences"
Solution: 
- Giảm số lượng allergens/disliked_dishes
- Hoặc update thêm data món ăn

---

Problem: "LP failed, fallback to simple method"
Solution: Bình thường! Hệ thống tự động dùng Greedy nếu LP không tìm được solution

---

Problem: Deviation quá cao (>20%)
Solution:
- Điều chỉnh macros percentages
- Thử method='lp' để tối ưu hơn
- Kiểm tra data có đủ món phù hợp không

---

Problem: Import error
Solution:
$ pip install -r requirements.txt


═══════════════════════════════════════════════════════════════════════

📝 8. CÁCH TEST CÁC TÍNH NĂNG
═══════════════════════════════════════════════════════════════════════

✅ Test 1: Tính toán metrics cơ bản
$ python -c "from test_ai_features import test_case_1_cutting_male; test_case_1_cutting_male()"

✅ Test 2: Gợi ý thực đơn Bulking
$ python -c "from test_ai_features import test_case_2_bulking_male; test_case_2_bulking_male()"

✅ Test 3: Lọc allergens
$ python -c "from test_ai_features import test_case_4_with_allergens; test_case_4_with_allergens()"

✅ Test 4: Edge cases
$ python -c "from test_ai_features import test_case_10_edge_cases; test_case_10_edge_cases()"

✅ Test tất cả (Recommended)
$ python test_ai_features.py


═══════════════════════════════════════════════════════════════════════

💡 9. TIPS & BEST PRACTICES
═══════════════════════════════════════════════════════════════════════

1. Luôn validate macros percentages = 100%
2. Dùng 'auto' method để hệ thống tự chọn thuật toán tốt nhất
3. Kiểm tra BMI trước khi set goal
4. Update allergens/disliked_dishes cụ thể
5. Test với nhiều profiles khác nhau
6. Kiểm tra deviation trong kết quả
7. Review món ăn được gợi ý có hợp lý không


═══════════════════════════════════════════════════════════════════════

📞 10. SUPPORT & DOCUMENTATION
═══════════════════════════════════════════════════════════════════════

Tài liệu đầy đủ:
- README.md          : Tổng quan hệ thống
- QUICKSTART.py      : Quick start guide
- SUMMARY.md         : Tóm tắt tính năng
- DEPLOYMENT.md      : Hướng dẫn deploy

Test files:
- test_ai_features.py    : 10 test cases đầy đủ
- test_data_samples.py   : 17 profiles mẫu
- test_system.py         : System tests
- example_usage.py       : Demo user datchu784


═══════════════════════════════════════════════════════════════════════

🎉 HAPPY TESTING!
═══════════════════════════════════════════════════════════════════════
""")


# Quick command reference
def show_commands():
    """Hiển thị các lệnh thường dùng"""
    commands = {
        "Setup": [
            "pip install -r requirements.txt",
            "python src/data_collection/nutrition_scraper.py"
        ],
        "Run Tests": [
            "python test_ai_features.py",
            "python test_data_samples.py",
            "python example_usage.py"
        ],
        "Quick Test": [
            "python -c \"from test_data_samples import list_all_profiles; list_all_profiles()\"",
            "python -c \"from test_ai_features import test_case_1_cutting_male; test_case_1_cutting_male()\""
        ]
    }
    
    print("\n" + "="*70)
    print("⚡ QUICK COMMANDS REFERENCE")
    print("="*70 + "\n")
    
    for category, cmds in commands.items():
        print(f"📌 {category}:")
        for cmd in cmds:
            print(f"  $ {cmd}")
        print()


if __name__ == "__main__":
    # Hiển thị hướng dẫn
    pass
    
    # Uncomment để xem commands
    # show_commands()

