# 🏋️ AI MEAL PLANNING SYSTEM - HỆ THỐNG GỢI Ý THỰC ĐƠN CHO NGƯỜI TẬP GYM

## 📖 Giới thiệu

Hệ thống AI Meal Planning được thiết kế đặc biệt cho người Việt Nam tập gym, giúp:
- ✅ Tính toán chỉ số dinh dưỡng cá nhân (BMI, BMR, TDEE)
- ✅ Gợi ý thực đơn phù hợp với mục tiêu (Cutting/Bulking/Maintain)
- ✅ Tối ưu hóa macros (Protein, Carbs, Fat)
- ✅ Sử dụng món ăn Việt Nam từ Viện Dinh Dưỡng Quốc Gia
- ✅ Ước tính giá thành món ăn

## 🎯 User Demo: datchu784
- **Thông tin**: Nam, 22 tuổi, 170cm, 65kg
- **Mục tiêu**: Cutting (giảm mỡ) - giảm 0.5kg/tuần
- **Target**: 2000 cal/ngày
- **Macros**: Protein 40%, Carbs 30%, Fat 30%

## 📂 Cấu trúc Project

```
gym-meal-planner/
├── src/
│   ├── data_collection/
│   │   ├── nutrition_scraper.py    # Scraper dữ liệu món ăn
│   │   └── price_scraper.py        # Scraper giá nguyên liệu
│   ├── meal_planner/
│   │   └── recommender.py          # AI gợi ý thực đơn
│   └── utils/
│       └── calculator.py           # Tính toán BMI, BMR, TDEE
├── data/
│   ├── raw/                        # Dữ liệu thô
│   │   ├── nutrition_data.csv
│   │   └── ingredient_prices.csv
│   └── processed/                  # Dữ liệu đã xử lý
├── logs/                           # Log files
├── tests/                          # Unit tests
├── example_usage.py                # Demo script
├── requirements.txt                # Dependencies
└── README.md                       # Tài liệu này
```

## 🚀 Cài đặt

### 1. Cài đặt Python Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `requests` - HTTP requests
- `beautifulsoup4` - Web scraping
- `pandas` - Data processing
- `numpy` - Numerical computing
- `PuLP` - Linear Programming optimization
- `tqdm` - Progress bars

### 2. Thu thập dữ liệu món ăn

Chạy scraper để lấy dữ liệu từ API Viện Dinh Dưỡng:

```bash
python src/data_collection/nutrition_scraper.py
```

Scraper sẽ:
- Lấy ~200 món ăn từ API Viện Dinh Dưỡng
- Lọc các món phù hợp cho gym (loại bỏ đồ ngọt, fast food)
- Lưu vào `data/raw/nutrition_data.csv`

### 3. Thu thập giá nguyên liệu (Optional)

```bash
python src/data_collection/price_scraper.py
```

Lưu ý: Scraper này sử dụng giá mặc định vì WinMart cần JS rendering (Selenium).

## 💻 Sử dụng

### Demo nhanh

```bash
python example_usage.py
```

### Sử dụng trong code

```python
from src.utils.calculator import get_user_metrics
from src.meal_planner.recommender import load_nutrition_data, recommend_meals

# 1. Định nghĩa user profile
user_profile = {
    'name': 'datchu784',
    'gender': 'Nam',
    'age': 22,
    'height_cm': 170,
    'weight_kg': 65,
    'activity_level': 'moderate',  # sedentary/light/moderate/active/very_active
    'goal': 'cutting',  # cutting/bulking/maintain
    'protein_pct': 0.40,
    'carbs_pct': 0.30,
    'fat_pct': 0.30,
    'allergens': [],  # VD: ['tôm', 'cua']
    'disliked_dishes': []  # VD: ['gan', 'lòng']
}

# 2. Tính toán metrics
metrics = get_user_metrics(user_profile)
user_profile.update(metrics)

# 3. Load dữ liệu món ăn
df = load_nutrition_data()

# 4. Gợi ý thực đơn
meal_plan = recommend_meals(df, user_profile, method='simple')

# 5. Hiển thị kết quả
print(meal_plan)
```

## 📊 Output Mẫu

```
==================================================
🍽️  THỰC ĐƠN GỢI Ý CHO HÔM NAY
==================================================

🍳 BỮA SÁNG:
  Món: Phở gà trộn
  Calories: 525 kcal
  Protein: 30.4g | Carbs: 68.0g | Fat: 14.6g
  Giá ước tính: 35,000đ

🍱 BỮA TRƯA:
  Món: Cơm gà xối mỡ
  Calories: 650 kcal
  Protein: 40.0g | Carbs: 75.0g | Fat: 18.0g
  Giá ước tính: 40,000đ

🥗 BỮA TỐI:
  Món: Salad ức gà
  Calories: 400 kcal
  Protein: 45.0g | Carbs: 20.0g | Fat: 15.0g
  Giá ước tính: 35,000đ

==================================================
📊 TỔNG KẾT:
  Tổng Calories: 1575 / 2000 cal
  Tổng Protein: 115 / 200g
  Tổng Carbs: 163 / 150g
  Tổng Fat: 48 / 67g
  Độ lệch: 8.5%

✅ Thực đơn phù hợp với mục tiêu
==================================================
```

## 🔧 API Reference

### 1. Calculator Module (`src/utils/calculator.py`)

#### `calculate_bmi(height_cm, weight_kg)`
Tính chỉ số BMI.

#### `calculate_bmr(weight_kg, height_cm, age, gender)`
Tính BMR theo công thức Mifflin-St Jeor.

#### `calculate_tdee(bmr, activity_level)`
Tính TDEE dựa trên mức độ vận động.

#### `calculate_target_calories(tdee, goal)`
Tính target calories theo mục tiêu:
- `cutting`: TDEE - 500 cal
- `bulking`: TDEE + 300 cal
- `maintain`: TDEE

#### `calculate_macros(target_calories, protein_pct, carbs_pct, fat_pct)`
Tính macros (gram) từ target calories và tỷ lệ %.

#### `get_user_metrics(user_profile)`
Tính toán tất cả metrics cho user.

### 2. Recommender Module (`src/meal_planner/recommender.py`)

#### `load_nutrition_data(filepath=None)`
Load dữ liệu món ăn từ CSV.

#### `filter_dishes_by_preferences(df, user_profile)`
Lọc món ăn theo allergens và preferences.

#### `recommend_meals_simple(df, user_profile)`
Gợi ý thực đơn bằng phương pháp greedy (nhanh, đơn giản).

#### `recommend_meals_linear_programming(df, user_profile)`
Gợi ý thực đơn bằng Linear Programming (tối ưu hơn).

#### `recommend_meals(df, user_profile, method='auto')`
Main function gợi ý thực đơn:
- `method='lp'`: Dùng Linear Programming
- `method='simple'`: Dùng greedy
- `method='auto'`: Tự động chọn (thử LP trước, fallback sang simple)

### 3. Scraper Modules

#### Nutrition Scraper (`src/data_collection/nutrition_scraper.py`)

```python
from src.data_collection.nutrition_scraper import fetch_all_dishes, save_to_csv

# Lấy 200 món ăn
dishes = fetch_all_dishes(max_dishes=200)

# Lưu vào CSV
save_to_csv(dishes, filename="nutrition_data.csv")
```

#### Price Scraper (`src/data_collection/price_scraper.py`)

```python
from src.data_collection.price_scraper import fetch_ingredient_prices, save_prices_to_csv

# Lấy giá nguyên liệu
prices = fetch_ingredient_prices()

# Lưu vào CSV
save_prices_to_csv(prices, filename="ingredient_prices.csv")
```

## 📝 Data Sources

- **Nutrition Data**: [Viện Dinh Dưỡng Quốc Gia](https://viendinhduong.vn)
  - API: `https://viendinhduong.vn/api/fe/tool/getPageFoodData`
  - ~200 món ăn Việt Nam với thông tin dinh dưỡng đầy đủ

- **Price Data**: WinMart + Default estimates
  - Giá nguyên liệu từ WinMart (hoặc giá mặc định)

## 🎯 Features

### ✅ Đã hoàn thành
- [x] Tính toán metrics cá nhân (BMI, BMR, TDEE)
- [x] Scraper dữ liệu món ăn từ Viện Dinh Dưỡng
- [x] Gợi ý thực đơn bằng greedy algorithm
- [x] Gợi ý thực đơn bằng Linear Programming
- [x] Lọc món ăn theo allergens và preferences
- [x] Demo script đầy đủ

### 🚧 Có thể mở rộng
- [ ] Generate weekly meal plan (thực đơn cả tuần)
- [ ] Web interface (Flask/Streamlit)
- [ ] Mobile app
- [ ] Tích hợp với fitness trackers
- [ ] Grocery shopping list generator
- [ ] Meal prep instructions

## 🔬 Algorithm Details

### Simple Method (Greedy)
1. Phân bổ calories và protein cho 3 bữa (25%, 40%, 35%)
2. Với mỗi bữa, tìm món có calories và protein gần target nhất
3. Loại món đã chọn để tránh trùng lặp

### Linear Programming Method
Sử dụng PuLP để tối ưu hóa:

**Variables:**
- `x[i,j]` = 1 nếu chọn món i cho bữa j, else 0

**Objective:**
- Minimize deviation từ target calories và macros

**Constraints:**
- Mỗi bữa chọn đúng 1 món
- Mỗi món chỉ được chọn tối đa 1 lần
- Tổng calories ≈ target ± deviation
- Tổng protein ≈ target ± deviation
- Carbs và fat trong khoảng ±20%

## 🐛 Troubleshooting

### Lỗi: "Import pandas could not be resolved"
```bash
pip install pandas
```

### Lỗi: "Không tìm thấy file nutrition_data.csv"
```bash
python src/data_collection/nutrition_scraper.py
```

### Lỗi: LP không tìm được solution
- Hệ thống tự động fallback sang simple method
- Hoặc thử tăng số món ăn bằng cách chạy scraper với max_dishes lớn hơn

### API Viện Dinh Dưỡng không hoạt động
- Kiểm tra kết nối internet
- API có thể bị rate limit, thử tăng delay giữa các requests
- Hoặc dùng dữ liệu mẫu có sẵn trong demo

## 📄 License

MIT License - Free to use for personal and educational purposes.

## 👨‍💻 Author

AI Meal Planning System
- Designed for Vietnamese gym-goers
- Data from Viện Dinh Dưỡng Quốc Gia

## 🙏 Credits

- **Viện Dinh Dưỡng Quốc Gia** - Nutrition data
- **PuLP** - Linear Programming library
- **Pandas** - Data processing

---

## 📞 Support

Nếu có vấn đề hoặc câu hỏi, vui lòng:
1. Kiểm tra phần Troubleshooting
2. Xem log file trong `logs/scraper.log`
3. Chạy demo với dữ liệu mẫu để test

---

**🎉 Chúc bạn tập luyện hiệu quả và đạt được mục tiêu!**
