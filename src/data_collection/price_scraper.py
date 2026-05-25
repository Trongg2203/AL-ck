"""
Price Scraper - Thu thập giá nguyên liệu từ WinMart hoặc sử dụng giá mặc định
Author: AI Meal Planning System
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
import time
from tqdm import tqdm
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)

# WinMart Configuration
WINMART_SEARCH_URL = "https://winmart.vn/search"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
}

# Default prices (VNĐ per kg) - fallback khi không scrape được
DEFAULT_PRICES = {
    "ức gà": 85000,
    "đùi gà": 75000,
    "thịt bò": 220000,
    "cá hồi": 350000,
    "cá thu": 120000,
    "tôm": 180000,
    "trứng gà": 35000,  # per 10 trứng
    "sữa tươi": 28000,  # per liter
    "cơm gạo": 20000,
    "khoai lang": 15000,
    "yến mạch": 45000,
    "bánh mì": 25000,
    "bơ": 85000,
    "dầu olive": 150000,
    "rau xanh": 20000,
    "cà chua": 18000,
    "dưa chuột": 15000,
    "chuối": 20000,
    "táo": 60000,
}


def search_winmart_product(keyword: str) -> Optional[Dict]:
    """
    Tìm kiếm sản phẩm trên WinMart và lấy giá
    
    Args:
        keyword: Tên nguyên liệu cần tìm
        
    Returns:
        Dict chứa thông tin sản phẩm hoặc None nếu không tìm thấy
    """
    try:
        # WinMart có thể cần JS rendering, tạm thời return None để dùng default
        # Nếu muốn scrape thực sự, cần dùng Selenium
        
        logger.info(f"Đang tìm '{keyword}' trên WinMart...")
        
        # Attempt to scrape (simplified - may not work due to JS)
        params = {'q': keyword}
        response = requests.get(WINMART_SEARCH_URL, params=params, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"Không thể truy cập WinMart (status={response.status_code})")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find product (cấu trúc có thể thay đổi)
        # Đây là ví dụ - cần inspect HTML thực tế để chính xác
        product = soup.find('div', class_='product-item')
        
        if not product:
            logger.warning(f"Không tìm thấy sản phẩm '{keyword}' trên WinMart")
            return None
        
        # Extract price (cần điều chỉnh selector cho đúng)
        price_elem = product.find('span', class_='price')
        if not price_elem:
            return None
            
        price_text = price_elem.text.strip().replace('đ', '').replace(',', '').replace('.', '')
        price = int(price_text)
        
        logger.info(f"✓ Tìm thấy '{keyword}': {price:,}đ")
        
        return {
            'name': keyword,
            'price_vnd': price,
            'unit': 'kg',
            'source': 'WinMart'
        }
        
    except requests.RequestException as e:
        logger.warning(f"Lỗi kết nối WinMart cho '{keyword}': {e}")
        return None
    except Exception as e:
        logger.warning(f"Lỗi khi scrape '{keyword}': {e}")
        return None


def fetch_ingredient_prices(ingredients_list: Optional[List[str]] = None) -> Dict[str, float]:
    """
    Lấy giá của danh sách nguyên liệu
    
    Args:
        ingredients_list: Danh sách tên nguyên liệu
        
    Returns:
        Dict mapping từ ingredient → price (VNĐ)
    """
    if ingredients_list is None:
        ingredients_list = list(DEFAULT_PRICES.keys())
    
    prices = {}
    
    logger.info(f"Đang fetch giá cho {len(ingredients_list)} nguyên liệu...")
    
    for ingredient in tqdm(ingredients_list, desc="Lấy giá nguyên liệu"):
        # Try scraping from WinMart
        product_info = search_winmart_product(ingredient)
        
        if product_info:
            prices[ingredient] = product_info['price_vnd']
        else:
            # Fallback to default price
            default_price = DEFAULT_PRICES.get(ingredient, 50000)  # 50k mặc định
            prices[ingredient] = default_price
            logger.info(f"Dùng giá mặc định cho '{ingredient}': {default_price:,}đ")
        
        # Delay to avoid rate limiting
        time.sleep(2)
    
    logger.info(f"✓ Đã lấy giá cho {len(prices)} nguyên liệu")
    return prices


def save_prices_to_csv(prices: Dict[str, float], filename: str = "ingredient_prices.csv") -> None:
    """
    Lưu giá nguyên liệu vào CSV
    
    Args:
        prices: Dict chứa giá nguyên liệu
        filename: Tên file CSV
    """
    try:
        # Prepare data
        data = []
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        for ingredient, price in prices.items():
            data.append({
                'ingredient': ingredient,
                'price_vnd_per_kg': price,
                'source': 'Default' if ingredient in DEFAULT_PRICES else 'WinMart',
                'date': current_date
            })
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Save to CSV
        data_dir = Path(__file__).parent.parent.parent / "data" / "raw"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = data_dir / filename
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        logger.info(f"\n{'='*50}")
        logger.info(f"✓ Đã lưu giá {len(df)} nguyên liệu vào {filepath}")
        logger.info(f"  Giá trung bình: {df['price_vnd_per_kg'].mean():,.0f}đ/kg")
        logger.info(f"  Giá thấp nhất: {df['price_vnd_per_kg'].min():,.0f}đ/kg")
        logger.info(f"  Giá cao nhất: {df['price_vnd_per_kg'].max():,.0f}đ/kg")
        logger.info(f"{'='*50}\n")
        
    except Exception as e:
        logger.error(f"✗ Lỗi khi lưu CSV giá: {e}")
        raise


def main():
    """Main function để chạy price scraper"""
    logger.info("=" * 60)
    logger.info("BẮT ĐẦU THU THẬP GIÁ NGUYÊN LIỆU")
    logger.info("=" * 60)
    
    try:
        # Fetch prices (dùng default list)
        prices = fetch_ingredient_prices()
        
        # Save to CSV
        save_prices_to_csv(prices)
        
        logger.info("✓ Hoàn thành!")
        
    except Exception as e:
        logger.error(f"✗ Lỗi: {e}")
        raise


if __name__ == "__main__":
    # Setup logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(Path(__file__).parent.parent.parent / "logs" / "scraper.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    main()
