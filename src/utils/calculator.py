"""
Calculator - Tính toán các chỉ số dinh dưỡng cho người tập gym
Author: AI Meal Planning System
"""

from typing import Dict


def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    """
    Tính chỉ số BMI (Body Mass Index)
    
    Args:
        height_cm: Chiều cao (cm)
        weight_kg: Cân nặng (kg)
        
    Returns:
        BMI value
    """
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)
    return round(bmi, 1)


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Tính BMR (Basal Metabolic Rate) - mức năng lượng cơ bản cơ thể cần
    Sử dụng công thức Mifflin-St Jeor
    
    Args:
        weight_kg: Cân nặng (kg)
        height_cm: Chiều cao (cm)
        age: Tuổi
        gender: Giới tính ('Nam' hoặc 'Nữ')
        
    Returns:
        BMR (calories/day)
    """
    # Mifflin-St Jeor formula
    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    
    if gender.lower() in ['nam', 'male', 'm']:
        bmr += 5
    else:
        bmr -= 161
    
    return round(bmr, 0)


def calculate_tdee(bmr: float, activity_level: str = 'moderate') -> float:
    """
    Tính TDEE (Total Daily Energy Expenditure) - tổng năng lượng tiêu thụ mỗi ngày
    
    Args:
        bmr: BMR value
        activity_level: Mức độ vận động
            - 'sedentary': Ít vận động (x1.2)
            - 'light': Nhẹ 1-3 ngày/tuần (x1.375)
            - 'moderate': Trung bình 3-5 ngày/tuần (x1.55)
            - 'active': Nặng 6-7 ngày/tuần (x1.725)
            - 'very_active': Rất nặng (x1.9)
            
    Returns:
        TDEE (calories/day)
    """
    activity_multipliers = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very_active': 1.9
    }
    
    multiplier = activity_multipliers.get(activity_level.lower(), 1.55)
    tdee = bmr * multiplier
    
    return round(tdee, 0)


def calculate_target_calories(tdee: float, goal: str) -> float:
    """
    Tính target calories dựa trên mục tiêu
    
    Args:
        tdee: TDEE value
        goal: Mục tiêu
            - 'cutting': Giảm mỡ (-500 cal = -0.5kg/tuần)
            - 'bulking': Tăng cơ (+300 cal = +0.3kg/tuần)
            - 'maintain': Duy trì (= TDEE)
            
    Returns:
        Target calories/day
    """
    if goal.lower() in ['cutting', 'cut', 'giảm mỡ']:
        return round(tdee - 500, 0)
    elif goal.lower() in ['bulking', 'bulk', 'tăng cơ']:
        return round(tdee + 300, 0)
    else:
        return round(tdee, 0)


def calculate_macros(target_calories: float, 
                     protein_pct: float = 0.40,
                     carbs_pct: float = 0.30, 
                     fat_pct: float = 0.30) -> Dict[str, float]:
    """
    Tính macros (Protein, Carbs, Fat) dựa trên target calories và tỷ lệ %
    
    Args:
        target_calories: Target calories/day
        protein_pct: % Protein (0.40 = 40%)
        carbs_pct: % Carbs (0.30 = 30%)
        fat_pct: % Fat (0.30 = 30%)
        
    Returns:
        Dict chứa protein_g, carbs_g, fat_g
    """
    # Validate percentages sum to 1
    total_pct = protein_pct + carbs_pct + fat_pct
    if abs(total_pct - 1.0) > 0.01:
        raise ValueError(f"Tổng % macros phải = 100% (hiện tại: {total_pct*100}%)")
    
    # Calories per gram
    PROTEIN_CAL_PER_G = 4
    CARBS_CAL_PER_G = 4
    FAT_CAL_PER_G = 9
    
    # Calculate grams
    protein_g = (target_calories * protein_pct) / PROTEIN_CAL_PER_G
    carbs_g = (target_calories * carbs_pct) / CARBS_CAL_PER_G
    fat_g = (target_calories * fat_pct) / FAT_CAL_PER_G
    
    return {
        'protein_g': round(protein_g, 0),
        'carbs_g': round(carbs_g, 0),
        'fat_g': round(fat_g, 0)
    }


def get_user_metrics(user_profile: Dict) -> Dict:
    """
    Tính toán tất cả metrics cho user
    
    Args:
        user_profile: Dict chứa thông tin user
            - name: Tên
            - gender: Giới tính ('Nam'/'Nữ')
            - age: Tuổi
            - height_cm: Chiều cao (cm)
            - weight_kg: Cân nặng (kg)
            - activity_level: Mức độ vận động
            - goal: Mục tiêu ('cutting'/'bulking'/'maintain')
            - protein_pct: % Protein (optional, default 0.40)
            - carbs_pct: % Carbs (optional, default 0.30)
            - fat_pct: % Fat (optional, default 0.30)
            
    Returns:
        Dict chứa tất cả metrics đã tính toán
    """
    # Extract user info
    name = user_profile.get('name', 'User')
    gender = user_profile.get('gender', 'Nam')
    age = user_profile.get('age', 25)
    height_cm = user_profile.get('height_cm', 170)
    weight_kg = user_profile.get('weight_kg', 65)
    activity_level = user_profile.get('activity_level', 'moderate')
    goal = user_profile.get('goal', 'cutting')
    
    # Macro percentages
    protein_pct = user_profile.get('protein_pct', 0.40)
    carbs_pct = user_profile.get('carbs_pct', 0.30)
    fat_pct = user_profile.get('fat_pct', 0.30)
    
    # Calculate metrics
    bmi = calculate_bmi(height_cm, weight_kg)
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    tdee = calculate_tdee(bmr, activity_level)
    target_calories = calculate_target_calories(tdee, goal)
    macros = calculate_macros(target_calories, protein_pct, carbs_pct, fat_pct)
    
    # Compile results
    metrics = {
        'name': name,
        'gender': gender,
        'age': age,
        'height_cm': height_cm,
        'weight_kg': weight_kg,
        'bmi': bmi,
        'bmr': bmr,
        'tdee': tdee,
        'activity_level': activity_level,
        'goal': goal,
        'target_calories': target_calories,
        'protein_g': macros['protein_g'],
        'carbs_g': macros['carbs_g'],
        'fat_g': macros['fat_g'],
        'protein_pct': protein_pct * 100,
        'carbs_pct': carbs_pct * 100,
        'fat_pct': fat_pct * 100
    }
    
    return metrics


def print_user_metrics(metrics: Dict) -> None:
    """
    In ra màn hình các metrics của user một cách đẹp mắt
    
    Args:
        metrics: Dict chứa metrics từ get_user_metrics()
    """
    print("\n" + "="*50)
    print("📊 THÔNG TIN VÀ CHỈ SỐ DINH DƯỠNG")
    print("="*50)
    
    print(f"\nThông tin người dùng: {metrics['name']}")
    print(f"  - Giới tính: {metrics['gender']}, {metrics['age']} tuổi")
    print(f"  - Chiều cao/Cân nặng: {metrics['height_cm']}cm / {metrics['weight_kg']}kg")
    print(f"  - BMI: {metrics['bmi']}")
    print(f"  - BMR: {metrics['bmr']:.0f} cal")
    print(f"  - TDEE: {metrics['tdee']:.0f} cal")
    print(f"  - Mục tiêu: {metrics['goal']}")
    print(f"  - Target Calories: {metrics['target_calories']:.0f} cal/ngày")
    
    print(f"\n  Macros target:")
    print(f"    • Protein: {metrics['protein_g']:.0f}g ({metrics['protein_pct']:.0f}%)")
    print(f"    • Carbs: {metrics['carbs_g']:.0f}g ({metrics['carbs_pct']:.0f}%)")
    print(f"    • Fat: {metrics['fat_g']:.0f}g ({metrics['fat_pct']:.0f}%)")
    
    print("="*50 + "\n")


# Test function
if __name__ == "__main__":
    # Test với user datchu784
    test_profile = {
        'name': 'datchu784',
        'gender': 'Nam',
        'age': 22,
        'height_cm': 170,
        'weight_kg': 65,
        'activity_level': 'moderate',
        'goal': 'cutting',
        'protein_pct': 0.40,
        'carbs_pct': 0.30,
        'fat_pct': 0.30
    }
    
    metrics = get_user_metrics(test_profile)
    print_user_metrics(metrics)
