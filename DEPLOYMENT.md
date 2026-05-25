# 🚀 DEPLOYMENT GUIDE - AI MEAL PLANNING SYSTEM

## Hướng dẫn triển khai hệ thống

---

## 📦 OPTION 1: Local Python Application

### Requirements
- Python 3.8+
- pip package manager

### Installation Steps

```bash
# 1. Clone hoặc download project
cd c:\Users\PC\Desktop\AI_ck

# 2. Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Collect data
python src/data_collection/nutrition_scraper.py

# 5. Run demo
python example_usage.py
```

### Usage
```python
# Import và sử dụng trong code của bạn
from src.utils.calculator import get_user_metrics
from src.meal_planner.recommender import recommend_meals
```

---

## 🌐 OPTION 2: Web Application (Streamlit)

### Create Streamlit App

Tạo file `app.py`:

```python
import streamlit as st
from src.utils.calculator import get_user_metrics
from src.meal_planner.recommender import load_nutrition_data, recommend_meals

st.title("🏋️ AI Meal Planning System")
st.write("Gợi ý thực đơn cho người tập gym")

# Sidebar - User Input
st.sidebar.header("Thông tin của bạn")
name = st.sidebar.text_input("Tên", "User")
gender = st.sidebar.selectbox("Giới tính", ["Nam", "Nữ"])
age = st.sidebar.number_input("Tuổi", 18, 80, 25)
height = st.sidebar.number_input("Chiều cao (cm)", 140, 220, 170)
weight = st.sidebar.number_input("Cân nặng (kg)", 40, 150, 65)

activity = st.sidebar.selectbox("Mức độ vận động", [
    "sedentary", "light", "moderate", "active", "very_active"
])

goal = st.sidebar.selectbox("Mục tiêu", ["cutting", "bulking", "maintain"])

# Calculate button
if st.sidebar.button("Tính toán & Gợi ý"):
    user = {
        'name': name,
        'gender': gender,
        'age': age,
        'height_cm': height,
        'weight_kg': weight,
        'activity_level': activity,
        'goal': goal,
        'protein_pct': 0.40,
        'carbs_pct': 0.30,
        'fat_pct': 0.30
    }
    
    # Calculate metrics
    metrics = get_user_metrics(user)
    
    # Display metrics
    st.header("📊 Thông tin của bạn")
    col1, col2, col3 = st.columns(3)
    col1.metric("BMI", f"{metrics['bmi']}")
    col2.metric("TDEE", f"{metrics['tdee']:.0f} cal")
    col3.metric("Target", f"{metrics['target_calories']:.0f} cal")
    
    # Recommend meals
    user.update(metrics)
    df = load_nutrition_data()
    meal_plan = recommend_meals(df, user)
    
    # Display meal plan
    st.header("🍽️ Thực đơn gợi ý")
    for meal_name, meal_data in meal_plan.items():
        if meal_name != 'tổng_kết':
            st.subheader(f"{meal_name.title()}")
            st.write(f"**{meal_data['món']}**")
            st.write(f"Calories: {meal_data['calories']:.0f} kcal")
            st.write(f"Protein: {meal_data['protein']}g | Carbs: {meal_data['carbs']}g | Fat: {meal_data['fat']}g")
```

### Run Streamlit
```bash
pip install streamlit
streamlit run app.py
```

---

## 🐳 OPTION 3: Docker Container

### Create Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-collect data
RUN python src/data_collection/nutrition_scraper.py

CMD ["python", "example_usage.py"]
```

### Build & Run
```bash
docker build -t meal-planner .
docker run meal-planner
```

---

## ☁️ OPTION 4: Cloud Deployment (Heroku)

### 1. Create Procfile
```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

### 2. Create runtime.txt
```
python-3.10.0
```

### 3. Deploy
```bash
heroku create meal-planner-app
git push heroku main
```

---

## 📱 OPTION 5: API Service (FastAPI)

### Create API Server

Tạo file `api.py`:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from src.utils.calculator import get_user_metrics
from src.meal_planner.recommender import load_nutrition_data, recommend_meals

app = FastAPI(title="AI Meal Planning API")

# Load data once at startup
df = load_nutrition_data()

class UserProfile(BaseModel):
    name: str
    gender: str
    age: int
    height_cm: float
    weight_kg: float
    activity_level: str
    goal: str
    protein_pct: float = 0.40
    carbs_pct: float = 0.30
    fat_pct: float = 0.30

@app.post("/recommend")
def get_recommendation(user: UserProfile):
    user_dict = user.dict()
    metrics = get_user_metrics(user_dict)
    user_dict.update(metrics)
    
    meal_plan = recommend_meals(df, user_dict)
    return meal_plan

@app.get("/")
def root():
    return {"message": "AI Meal Planning API - Ready!"}
```

### Run API
```bash
pip install fastapi uvicorn
uvicorn api:app --reload
```

### Test API
```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "gender": "Nam",
    "age": 25,
    "height_cm": 175,
    "weight_kg": 70,
    "activity_level": "moderate",
    "goal": "cutting"
  }'
```

---

## 🔐 PRODUCTION CONSIDERATIONS

### Security
- [ ] Add API authentication (JWT tokens)
- [ ] Rate limiting
- [ ] Input validation
- [ ] HTTPS/SSL

### Performance
- [ ] Cache nutrition data
- [ ] Database for user profiles
- [ ] Redis for session management
- [ ] CDN for static assets

### Monitoring
- [ ] Logging (structured logs)
- [ ] Error tracking (Sentry)
- [ ] Performance monitoring (New Relic)
- [ ] Usage analytics

### Scalability
- [ ] Horizontal scaling (load balancer)
- [ ] Database optimization
- [ ] Caching strategy
- [ ] Async processing for heavy tasks

---

## 📊 RECOMMENDED STACK

### For Simple Use
- **Local Python script** ✅ Fastest to deploy
- Run directly: `python example_usage.py`

### For Web App
- **Streamlit** ✅ Easy to build, good for MVP
- Deploy on Streamlit Cloud (free)

### For Production
- **FastAPI + React** ✅ Professional, scalable
- Backend: FastAPI (Python)
- Frontend: React/Next.js
- Database: PostgreSQL
- Cache: Redis
- Deploy: AWS/GCP/Azure

---

## 🎯 QUICK DEPLOYMENT CHECKLIST

- [ ] Test locally first
- [ ] Collect nutrition data
- [ ] Set up environment variables
- [ ] Configure logging
- [ ] Add error handling
- [ ] Test with different users
- [ ] Write documentation
- [ ] Set up monitoring
- [ ] Plan for updates
- [ ] Backup data

---

## 📞 SUPPORT

Nếu gặp vấn đề khi deploy:
1. Check logs trong `logs/scraper.log`
2. Verify dependencies: `pip list`
3. Test individual modules: `python test_system.py`
4. Check data files exist: `data/raw/nutrition_data.csv`

---

**Happy Deploying! 🚀**
