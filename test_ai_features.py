"""
TEST CASES CHO HỆ THỐNG AI MEAL PLANNING - ENHANCED VERSION
===========================================================

File này chứa các test case đa dạng với hiển thị chi tiết món ăn
Author: AI Meal Planning System
Date: 2025-11-27 (Updated)
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from src.utils.calculator import get_user_metrics, print_user_metrics
from src.meal_planner.recommender import load_nutrition_data, recommend_meals
import logging

# Setup logging
logging.basicConfig(
    level=logging.WARNING,  # Giảm log spam
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """In section header đẹp"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_test_result(test_name: str, passed: bool, details: str = ""):
    """In kết quả test"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status}: {test_name}")
    if details:
        print(f"  → {details}")


def print_meal_plan(meal_plan: dict):
    """Hàm helper để in thực đơn chi tiết"""
    if not meal_plan:
        print("❌ Không tạo được thực đơn")
        return False
    
    print("\n📋 THỰC ĐƠN GỢI Ý:")
    print("-" * 80)
    
    for meal_name, meal_data in meal_plan.items():
        if meal_name != 'tổng_kết':
            print(f"\n  🍽️  {meal_name.upper()}:")
            print(f"      Món: {meal_data['món']}")
            print(f"      Calories: {meal_data['calories']} kcal")
            print(f"      Protein: {meal_data['protein']}g | "
                  f"Carbs: {meal_data['carbs']}g | "
                  f"Fat: {meal_data['fat']}g")
    
    print("\n" + "-" * 80)
    summary = meal_plan['tổng_kết']
    print(f"  📊 Tổng | {summary['total_calories']:.0f}/{summary['target_calories']:.0f}cal | "
          f"Độ lệch: {summary['deviation']:.1f}%")
    
    # Validate deviation
    if abs(summary['deviation']) > 15:
        print(f"  ⚠️  Warning: Độ lệch cao ({summary['deviation']:.1f}%)")
    
    return True


def test_data_loading():
    """Test 0: Kiểm tra load dữ liệu"""
    print_section("TEST 0: LOAD DỮ LIỆU")
    
    try:
        df = load_nutrition_data()
        print(f"✅ Đã load {len(df)} món ăn")
        print(f"   Categories: {df['category'].nunique()} loại")
        print(f"   Calories range: {df['calories'].min():.1f} - {df['calories'].max():.1f} kcal")
        print(f"   Protein range: {df['protein_g'].min():.1f} - {df['protein_g'].max():.1f}g")
        
        # Check for data quality
        zero_carbs = len(df[df['carbs_g'] == 0.0])
        if zero_carbs > 0:
            print(f"   ⚠️  Có {zero_carbs} món có carbs=0 (cần review)")
        
        return True
    except Exception as e:
        print(f"❌ Lỗi load data: {e}")
        return False


def test_case_1_cutting(df):
    """Test 1: Nam 22 tuổi - Cutting"""
    print_section("TEST 1: NAM 22 TUỔI - CUTTING")
    
    user = {
        'name': 'Nguyễn Văn A',
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
    
    try:
        metrics = get_user_metrics(user)
        user.update(metrics)
        print_user_metrics(user)
        
        meal_plan = recommend_meals(df, user, method='auto')
        success = print_meal_plan(meal_plan)
        
        # Validate
        if success:
            deviation = abs(meal_plan['tổng_kết']['deviation'])
            print_test_result("Cutting 22 tuổi", deviation < 15, 
                            f"Deviation: {deviation:.1f}%")
            return deviation < 15
        return False
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False


def test_case_2_bulking(df):
    """Test 2: Nam 25 tuổi - Bulking"""
    print_section("TEST 2: NAM 25 TUỔI - BULKING")
    
    user = {
        'name': 'Trần Văn B',
        'gender': 'Nam',
        'age': 25,
        'height_cm': 175,
        'weight_kg': 70,
        'activity_level': 'active',
        'goal': 'bulking',
        'protein_pct': 0.30,
        'carbs_pct': 0.50,
        'fat_pct': 0.20
    }
    
    try:
        metrics = get_user_metrics(user)
        user.update(metrics)
        print_user_metrics(user)
        
        meal_plan = recommend_meals(df, user, method='auto')
        success = print_meal_plan(meal_plan)
        
        if success:
            deviation = abs(meal_plan['tổng_kết']['deviation'])
            print_test_result("Bulking 25 tuổi", deviation < 15,
                            f"Deviation: {deviation:.1f}%")
            return deviation < 15
        return False
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False


def test_case_3_female_cutting(df):
    """Test 3: Nữ 24 tuổi - Cutting"""
    print_section("TEST 3: NỮ 24 TUỔI - CUTTING")
    
    user = {
        'name': 'Nguyễn Thị C',
        'gender': 'Nữ',
        'age': 24,
        'height_cm': 160,
        'weight_kg': 52,
        'activity_level': 'light',
        'goal': 'cutting',
        'protein_pct': 0.35,
        'carbs_pct': 0.40,
        'fat_pct': 0.25
    }
    
    try:
        metrics = get_user_metrics(user)
        user.update(metrics)
        print_user_metrics(user)
        
        meal_plan = recommend_meals(df, user, method='auto')
        success = print_meal_plan(meal_plan)
        
        if success:
            deviation = abs(meal_plan['tổng_kết']['deviation'])
            print_test_result("Nữ Cutting", deviation < 15,
                            f"Deviation: {deviation:.1f}%")
            return deviation < 15
        return False
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False


def test_case_4_maintain(df):
    """Test 4: Nam 30 tuổi - Maintain"""
    print_section("TEST 4: NAM 30 TUỔI - MAINTAIN")
    
    user = {
        'name': 'Lê Văn D',
        'gender': 'Nam',
        'age': 30,
        'height_cm': 172,
        'weight_kg': 68,
        'activity_level': 'moderate',
        'goal': 'maintain',
        'protein_pct': 0.30,
        'carbs_pct': 0.40,
        'fat_pct': 0.30
    }
    
    try:
        metrics = get_user_metrics(user)
        user.update(metrics)
        print_user_metrics(user)
        
        meal_plan = recommend_meals(df, user, method='auto')
        success = print_meal_plan(meal_plan)
        
        if success:
            deviation = abs(meal_plan['tổng_kết']['deviation'])
            print_test_result("Maintain 30 tuổi", deviation < 15,
                            f"Deviation: {deviation:.1f}%")
            return deviation < 15
        return False
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False


def test_case_5_sedentary(df):
    """Test 5: Sedentary Lifestyle - Low calories"""
    print_section("TEST 5: SEDENTARY LIFESTYLE")
    
    user = {
        'name': 'Hoàng Thị F',
        'gender': 'Nữ',
        'age': 26,
        'height_cm': 158,
        'weight_kg': 48,
        'activity_level': 'sedentary',
        'goal': 'cutting',
        'protein_pct': 0.35,
        'carbs_pct': 0.35,
        'fat_pct': 0.30
    }
    
    try:
        metrics = get_user_metrics(user)
        user.update(metrics)
        print_user_metrics(user)
        
        meal_plan = recommend_meals(df, user, method='auto')
        success = print_meal_plan(meal_plan)
        
        if success:
            deviation = abs(meal_plan['tổng_kết']['deviation'])
            print_test_result("Sedentary", deviation < 15,
                            f"Deviation: {deviation:.1f}%")
            return deviation < 15
        return False
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False


def show_menu():
    """Hiển thị menu chọn test case"""
    print("\n" + "=" * 80)
    print("  🏋️  AI MEAL PLANNING SYSTEM - TEST CASES")
    print("=" * 80)
    print("\n📋 CHỌN TEST CASE:\n")
    print("  0. ✅ Kiểm tra load dữ liệu")
    print("  1. 👨 Nam 22 tuổi - Cutting (giảm cân)")
    print("  2. 💪 Nam 25 tuổi - Bulking (tăng cân)")
    print("  3. 👩 Nữ 24 tuổi - Cutting (giảm cân)")
    print("  4. ⚖️  Nam 30 tuổi - Maintain (duy trì)")
    print("  5. 🪑 Sedentary Lifestyle - Ít vận động")
    print("  6. 🔄 Chạy TẤT CẢ test cases")
    print("  7. ❌ Thoát")
    print("\n" + "=" * 80)


def run_single_test(choice: int, df):
    """Chạy một test case cụ thể"""
    test_functions = {
        0: lambda: test_data_loading(),
        1: lambda: test_case_1_cutting(df),
        2: lambda: test_case_2_bulking(df),
        3: lambda: test_case_3_female_cutting(df),
        4: lambda: test_case_4_maintain(df),
        5: lambda: test_case_5_sedentary(df),
    }
    
    if choice in test_functions:
        return test_functions[choice]()
    return False


def run_all_tests(df):
    """Chạy tất cả test cases"""
    print_section("CHẠY TẤT CẢ TEST CASES")
    
    test_results = []
    
    test_results.append(("Cutting 22 tuổi", test_case_1_cutting(df)))
    test_results.append(("Bulking 25 tuổi", test_case_2_bulking(df)))
    test_results.append(("Nữ Cutting", test_case_3_female_cutting(df)))
    test_results.append(("Maintain 30 tuổi", test_case_4_maintain(df)))
    test_results.append(("Sedentary", test_case_5_sedentary(df)))
    
    # Calculate stats
    passed_tests = sum(1 for _, result in test_results if result)
    failed_tests = len(test_results) - passed_tests
    total_tests = len(test_results)
    
    # Summary
    print_section("TỔNG KẾT")
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"✅ Passed: {passed_tests}/{total_tests} tests ({success_rate:.1f}%)")
    print(f"❌ Failed: {failed_tests}/{total_tests} tests")
    
    if failed_tests == 0:
        print("\n🎉 TẤT CẢ TEST CASES ĐỀU PASS!")
        print("   Hệ thống AI Meal Planning hoạt động tốt!")
    else:
        print("\n⚠️  MỘT SỐ TEST CASES THẤT BẠI - CẦN KIỂM TRA!")
        print(f"   Success rate: {success_rate:.1f}%")
        print("\nCác test thất bại:")
        for name, result in test_results:
            if not result:
                print(f"  • {name}")
    
    print("\n" + "=" * 80)


def main():
    """Main test runner với interactive menu"""
    print("\n" + "🏋️ " * 25)
    print("  AI MEAL PLANNING SYSTEM - INTERACTIVE TESTS")
    print("🏋️ " * 25)
    
    # Load data first
    print("\n⏳ Đang load dữ liệu...")
    try:
        df = load_nutrition_data()
        print(f"✅ Đã load {len(df)} món ăn thành công!")
    except Exception as e:
        print(f"❌ Lỗi load dữ liệu: {e}")
        return
    
    # Interactive loop
    while True:
        show_menu()
        
        try:
            choice = input("\n👉 Nhập số (0-8): ").strip()
            
            if not choice.isdigit():
                print("❌ Vui lòng nhập số từ 0-7!")
                input("\n⏎  Nhấn Enter để tiếp tục...")
                continue
            
            choice = int(choice)
            
            if choice == 7:
                print("\n👋 Tạm biệt! Cảm ơn đã sử dụng hệ thống!")
                break
            elif choice == 6:
                run_all_tests(df)
                input("\n⏎  Nhấn Enter để quay lại menu...")
            elif 0 <= choice <= 5:
                result = run_single_test(choice, df)
                if result:
                    print("\n✅ Test case PASSED!")
                else:
                    print("\n❌ Test case FAILED!")
                input("\n⏎  Nhấn Enter để quay lại menu...")
            else:
                print("❌ Số không hợp lệ! Vui lòng chọn từ 0-7")
                input("\n⏎  Nhấn Enter để tiếp tục...")
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Đã hủy! Quay lại menu...")
            continue
        except Exception as e:
            print(f"\n❌ Lỗi: {e}")
            input("\n⏎  Nhấn Enter để tiếp tục...")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test bị ngắt bởi người dùng")
    except Exception as e:
        print(f"\n\n❌ Lỗi nghiêm trọng: {e}")
        import traceback
        traceback.print_exc()
