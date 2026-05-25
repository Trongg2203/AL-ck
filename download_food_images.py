#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Food Image Downloader for Gym Nutrition App
============================================
Uses TheMealDB (free, no key required) to fetch real food photo URLs,
then downloads and stores them as:
  lg_{name}.jpg  800x600  (full size)
  md_{name}.jpg  400x300  (medium)
  xs_{name}.jpg  100x75   (thumbnail)

under server-qlsv/public/uploads/foods/
Manifest: AI_ck/data/food_images_manifest.json
"""

import re
import sys
import json
import time
import random
import string
import unicodedata
from io import BytesIO
from pathlib import Path

if sys.platform == "win32":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from PIL import Image

BASE_DIR      = Path(__file__).resolve().parent.parent
STORAGE_DIR   = BASE_DIR / "server-qlsv" / "public" / "uploads" / "foods"
DATA_DIR      = BASE_DIR / "AI_ck" / "data"
CSV_PATH      = DATA_DIR / "raw" / "nutrition_data.csv"
MANIFEST_PATH = DATA_DIR / "food_images_manifest.json"

SIZES = {"lg": (800, 600), "md": (400, 300), "xs": (100, 75)}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

MEAL_CATEGORY_MAP = [
    (["ga", "uc ga", "ga nuong", "ga luoc", "ga hap", "ga xao", "ga ran", "ga tan"], "Chicken"),
    (["ca hoi", "ca ngu", "ca ba sa", "ca thu", "ca ro phi", "ca kem",
      "tom", "muc", "cua", "hao", "ca viet", "hai san", "bach tuoc"], "Seafood"),
    (["thit bo", "bo xao", "pho bo", "bun bo", "suon bo", "bit tet"], "Beef"),
    (["thit heo", "thit lon", "suon heo", "thit ba chi", "heo quay"], "Pork"),
    (["thit vit", "vit", "thit ga tay", "ga tay"], "Lamb"),
    (["dau hu", "tofu", "edamame", "dau den", "dau lang", "dau xanh",
      "dau ga", "rau", "bong cai", "mang tay", "nam", "ca rot",
      "bap cai", "xa lach", "khoai lang", "khoai tay", "cu cai",
      "spinach", "kale"], "Vegetarian"),
    (["pasta", "mi y", "mi quang", "pho", "bun", "mien", "hu tieu",
      "banh canh", "mi ", "yen mach", "quinoa", "gao lut",
      "ramen", "udon", "pad thai"], "Pasta"),
    (["trung", "sua chua", "granola", "banh mi", "smoothie",
      "protein", "hat", "dau phong", "bua sang"], "Breakfast"),
    (["mat ong", "socola", "trai cay", "chuoi", "tao", "cam",
      "nho", "dau tay", "viet quat", "du du", "dua hau", "xoai",
      "bo avocado", "avocado", "kiwi"], "Dessert"),
]
FALLBACK_CATEGORY = "Miscellaneous"


def remove_diacritics(text):
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def normalize(text):
    text = remove_diacritics(text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def get_meal_category(food_name):
    n = normalize(food_name)
    for keywords, category in MEAL_CATEGORY_MAP:
        for kw in keywords:
            if kw in n:
                return category
    return FALLBACK_CATEGORY


def generate_random_name(length=10):
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def fetch_themealdb_thumbnails(category):
    url = f"https://www.themealdb.com/api/json/v1/1/filter.php?c={category}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            meals = resp.json().get("meals") or []
            return [m["strMealThumb"] + "/medium" for m in meals if m.get("strMealThumb")]
    except Exception as e:
        print(f"  [warn] TheMealDB {category}: {e}", flush=True)
    return []


def preload_category_images():
    categories = sorted({cat for _, cat in MEAL_CATEGORY_MAP} | {FALLBACK_CATEGORY})
    pool = {}
    print(f"Pre-loading TheMealDB images for {len(categories)} categories...", flush=True)
    for cat in categories:
        urls = fetch_themealdb_thumbnails(cat)
        pool[cat] = urls
        print(f"  {cat}: {len(urls)} images", flush=True)
        time.sleep(0.3)
    return pool


def download_image_bytes(url, retries=3):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 5000:
                try:
                    Image.open(BytesIO(resp.content)).verify()
                    return resp.content
                except Exception:
                    pass
        except requests.RequestException as e:
            print(f"    attempt {attempt+1} failed: {e}", flush=True)
        time.sleep(1)
    return None


def save_image_sizes(img_bytes, base_name):
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        img = Image.open(BytesIO(img_bytes)).convert("RGB")
    except Exception as e:
        print(f"    cannot open image: {e}", flush=True)
        return False
    ok = True
    for prefix, (w, h) in SIZES.items():
        target = STORAGE_DIR / f"{prefix}_{base_name}.jpg"
        resized = img.copy()
        resized.thumbnail((w, h), Image.LANCZOS)
        try:
            resized.save(target, "JPEG", quality=85, optimize=True)
        except Exception as e:
            print(f"    failed saving {prefix}: {e}", flush=True)
            ok = False
    return ok


def read_csv_foods():
    import csv
    foods = []
    if not CSV_PATH.exists():
        print(f"[warn] CSV not found: {CSV_PATH}", flush=True)
        return foods
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name_vi", row.get("name", "")).strip()
            cat  = row.get("category", "").strip()
            if name:
                foods.append({"name": name, "category": cat})
    return foods


def supplemental_foods():
    return [
        {"name": "Uc ga luoc",              "category": "Mon giam can"},
        {"name": "Ca hoi nuong",            "category": "Mon giam can"},
        {"name": "Bong cai xanh luoc",      "category": "Mon giam can"},
        {"name": "Trung ga luoc",           "category": "Mon giam can"},
        {"name": "Dau hu hap",              "category": "Mon giam can"},
        {"name": "Salad rau tron dau oliu", "category": "Mon giam can"},
        {"name": "Ca ngu dong hop",         "category": "Mon giam can"},
        {"name": "Sua chua khong duong",    "category": "Mon giam can"},
        {"name": "Rau xao toi",             "category": "Mon giam can"},
        {"name": "Sup rau cu",              "category": "Mon giam can"},
        {"name": "Cai xoan kale xao",       "category": "Mon giam can"},
        {"name": "Ca chua bi",              "category": "Mon giam can"},
        {"name": "Dua chuot",               "category": "Mon giam can"},
        {"name": "Ga hap gung",             "category": "Mon giam can"},
        {"name": "Canh bi dao",             "category": "Mon giam can"},
        {"name": "Ot chuong nhoi thit",     "category": "Mon giam can"},
        {"name": "Ca ro phi hap",           "category": "Mon giam can"},
        {"name": "Long trang trung chien",  "category": "Mon giam can"},
        {"name": "Sup bap cai",             "category": "Mon giam can"},
        {"name": "Can tay xao",             "category": "Mon giam can"},
        {"name": "Tom luoc",                "category": "Mon giam can"},
        {"name": "Nam xao toi",             "category": "Mon giam can"},
        {"name": "Thit bo bit tet nac",     "category": "Mon giam can"},
        {"name": "Ca thu nuong",            "category": "Mon giam can"},
        {"name": "Mang tay nuong",          "category": "Mon giam can"},
        {"name": "Com gao lut uc ga",       "category": "Mon da dang gym"},
        {"name": "Pho bo",                  "category": "Mon da dang gym"},
        {"name": "Bun ga",                  "category": "Mon da dang gym"},
        {"name": "Com chien trung",         "category": "Mon da dang gym"},
        {"name": "Ca hoi sot chanh",        "category": "Mon da dang gym"},
        {"name": "Dau hu chien sa",         "category": "Mon da dang gym"},
        {"name": "Tom nuong",               "category": "Mon da dang gym"},
        {"name": "Ga nuong mat ong",        "category": "Mon da dang gym"},
        {"name": "Ca ba sa kho to",         "category": "Mon da dang gym"},
        {"name": "Thit heo nac luoc",       "category": "Mon da dang gym"},
        {"name": "Muc xao rau",             "category": "Mon da dang gym"},
        {"name": "Com tam suon",            "category": "Mon da dang gym"},
        {"name": "Hu tieu bo",              "category": "Mon da dang gym"},
        {"name": "Bun bo hue",              "category": "Mon da dang gym"},
        {"name": "Chao ga",                 "category": "Mon da dang gym"},
        {"name": "Ca kho to",               "category": "Mon da dang gym"},
        {"name": "Ga rang muoi",            "category": "Mon da dang gym"},
        {"name": "Thit bo xao rau cu",      "category": "Mon da dang gym"},
        {"name": "Canh chua ca",            "category": "Mon da dang gym"},
        {"name": "Tom su hap sa",           "category": "Mon da dang gym"},
        {"name": "Com trang thit kho",      "category": "Mon da dang gym"},
        {"name": "Dau phu sot ca chua",     "category": "Mon da dang gym"},
        {"name": "Ga hap bia",              "category": "Mon da dang gym"},
        {"name": "Ca ngu ap chao",          "category": "Mon da dang gym"},
        {"name": "Rau xao thap cam",        "category": "Mon da dang gym"},
        {"name": "Bo xao nam",              "category": "Mon da dang gym"},
        {"name": "Chao dau xanh",           "category": "Mon da dang gym"},
        {"name": "Mi ga it beo",            "category": "Mon da dang gym"},
        {"name": "Lau rau ca",              "category": "Mon da dang gym"},
        {"name": "Cua hap bia",             "category": "Mon da dang gym"},
        {"name": "Trung cuon rau",          "category": "Mon da dang gym"},
        {"name": "Suon heo nuong",          "category": "Mon da dang gym"},
        {"name": "Xuc xich ga",             "category": "Mon da dang gym"},
        {"name": "Nom ga bap cai",          "category": "Mon da dang gym"},
        {"name": "Vit quay it da",          "category": "Mon da dang gym"},
        {"name": "Ca bong hap",             "category": "Mon da dang gym"},
        {"name": "So diep nuong",           "category": "Mon da dang gym"},
        {"name": "Com trang thit ba chi kho","category": "Mon tang can"},
        {"name": "Bun bo xao beo",          "category": "Mon tang can"},
        {"name": "Com nep ga beo",          "category": "Mon tang can"},
        {"name": "Trung chien bo",          "category": "Mon tang can"},
        {"name": "Chao thit bam beo",       "category": "Mon tang can"},
        {"name": "Mi xao bo thap cam",      "category": "Mon tang can"},
        {"name": "Com suon nuong mo",       "category": "Mon tang can"},
        {"name": "Thit kho hot vit",        "category": "Mon tang can"},
        {"name": "Ga ran bo toi",           "category": "Mon tang can"},
        {"name": "Bun thit nuong",          "category": "Mon tang can"},
        {"name": "Com chien hai san",       "category": "Mon tang can"},
        {"name": "Mi Y thit bo beo",        "category": "Mon tang can"},
        {"name": "Khoai lang nuong bo",     "category": "Mon tang can"},
        {"name": "Yen mach sua mat ong",    "category": "Mon tang can"},
        {"name": "Sinh to bo sua chuoi",    "category": "Mon tang can"},
        {"name": "Banh mi trung pho mai",   "category": "Mon tang can"},
        {"name": "Chao ga dau phong",       "category": "Mon tang can"},
        {"name": "Com tam suon bi cha",     "category": "Mon tang can"},
        {"name": "Thit heo quay",           "category": "Mon tang can"},
        {"name": "Vit nuong cam",           "category": "Mon tang can"},
        {"name": "Com ga hai nam",          "category": "Mon tang can"},
        {"name": "Bun rieu cua",            "category": "Mon tang can"},
        {"name": "Hu tieu Nam Vang",        "category": "Mon tang can"},
        {"name": "Ga nuong kieu Han",       "category": "Mon quoc te gym"},
        {"name": "Ca hoi sot cam",          "category": "Mon quoc te gym"},
        {"name": "Bibimbap chay",           "category": "Mon quoc te gym"},
        {"name": "Kimchi dau hu",           "category": "Mon quoc te gym"},
        {"name": "Pasta ga it beo",         "category": "Mon quoc te gym"},
        {"name": "Salad Hy Lap",            "category": "Mon quoc te gym"},
        {"name": "Bit tet bo nac",          "category": "Mon quoc te gym"},
        {"name": "Ga tay nuong",            "category": "Mon quoc te gym"},
        {"name": "Quinoa bowl rau cu",      "category": "Mon quoc te gym"},
        {"name": "Shakshuka trung",         "category": "Mon quoc te gym"},
        {"name": "Bap cai cuon thit",       "category": "Mon quoc te gym"},
        {"name": "So co la den",            "category": "Mon quoc te gym"},
        {"name": "Pad Thai ga",             "category": "Mon quoc te gym"},
        {"name": "Tom Yum hai san",         "category": "Mon quoc te gym"},
        {"name": "Som Tum ga",              "category": "Mon quoc te gym"},
        {"name": "Ga nuong kieu Thai",      "category": "Mon quoc te gym"},
        {"name": "Ca ngu sashimi",          "category": "Mon quoc te gym"},
        {"name": "Onigiri ga",              "category": "Mon quoc te gym"},
        {"name": "Miso soup dau hu",        "category": "Mon quoc te gym"},
        {"name": "Udon ga",                 "category": "Mon quoc te gym"},
        {"name": "Tempura tom it dau",      "category": "Mon quoc te gym"},
        {"name": "Teriyaki ga",             "category": "Mon quoc te gym"},
        {"name": "Taco ga",                 "category": "Mon quoc te gym"},
        {"name": "Burrito dau den",         "category": "Mon quoc te gym"},
        {"name": "Guacamole bo",            "category": "Mon quoc te gym"},
        {"name": "Bulgar wheat salad",      "category": "Mon quoc te gym"},
        {"name": "Com den Nhat",            "category": "Mon quoc te gym"},
        {"name": "Ramen ga it beo",         "category": "Mon quoc te gym"},
        {"name": "Edamame luoc",            "category": "Mon quoc te gym"},
        {"name": "Hummus rau cu",           "category": "Mon quoc te gym"},
        {"name": "Bua sang Dia Trung Hai",  "category": "Mon quoc te gym"},
        {"name": "Granola sua chua trai cay","category": "Mon quoc te gym"},
        {"name": "Banh protein yen mach",   "category": "Mon quoc te gym"},
        {"name": "Smoothie xanh detox",     "category": "Mon quoc te gym"},
        {"name": "Bulgogi bo Han",          "category": "Mon quoc te gym"},

        # ── Foods from DB not yet covered (exact Vietnamese names) ────────────
        {"name": "Bánh canh cua",               "category": "Món đa dạng gym"},
        {"name": "Bánh gạo + bơ đậu phộng",     "category": "Món tăng cân"},
        {"name": "Bánh hamburger thịt nạc",      "category": "Món tăng cân"},
        {"name": "Bánh mì đen nguyên cám",       "category": "Món đa dạng gym"},
        {"name": "Bánh mì trắng",                "category": "Món tăng cân"},
        {"name": "Bánh pancake protein",         "category": "Món tăng cân"},
        {"name": "Bánh quy bơ",                  "category": "Món tăng cân"},
        {"name": "Bánh sandwich ức gà",          "category": "Món đa dạng gym"},
        {"name": "Bơ (nửa trái)",                "category": "Món giảm cân"},
        {"name": "Bột cacao nguyên chất",        "category": "Món quốc tế gym"},
        {"name": "Bún bò rau nhiều thịt nạc",    "category": "Món đa dạng gym"},
        {"name": "Bún cá thu",                   "category": "Món đa dạng gym"},
        {"name": "Bún gà xay rau củ",            "category": "Món đa dạng gym"},
        {"name": "Cá ba sa kho tiêu ít dầu",     "category": "Món đa dạng gym"},
        {"name": "Cá chép hấp",                  "category": "Món giảm cân"},
        {"name": "Cà chua tươi",                 "category": "Món giảm cân"},
        {"name": "Cá hồi áp chảo ít dầu",        "category": "Món giảm cân"},
        {"name": "Cá hồi sốt teriyaki",          "category": "Món quốc tế gym"},
        {"name": "Cá ngừ hấp",                   "category": "Món giảm cân"},
        {"name": "Cà rốt luộc",                  "category": "Món giảm cân"},
        {"name": "Cải xoăn luộc",                "category": "Món giảm cân"},
        {"name": "Cam tươi",                     "category": "Món giảm cân"},
        {"name": "Canh gà + noodle nguyên hạt",  "category": "Món đa dạng gym"},
        {"name": "Canh thịt bò + rau",           "category": "Món đa dạng gym"},
        {"name": "Chuối + mật ong tự nhiên",     "category": "Món tăng cân"},
        {"name": "Chuối chín",                   "category": "Món tăng cân"},
        {"name": "Cơm chiên gà",                 "category": "Món đa dạng gym"},
        {"name": "Cơm chiên gà nạc",             "category": "Món đa dạng gym"},
        {"name": "Cơm tấm gà nướng bơ dầu",      "category": "Món tăng cân"},
        {"name": "Cơm trắng nấu",                "category": "Món đa dạng gym"},
        {"name": "Cua luộc nước muối",           "category": "Món giảm cân"},
        {"name": "Dầu dừa nguyên chất",          "category": "Món tăng cân"},
        {"name": "Dâu đen hầm",                  "category": "Món giảm cân"},
        {"name": "Dâu tây tươi",                 "category": "Món giảm cân"},
        {"name": "Dưa chuột tươi",               "category": "Món giảm cân"},
        {"name": "Dưa hấu tươi",                 "category": "Món giảm cân"},
        {"name": "Dùm gà hấp",                   "category": "Món giảm cân"},
        {"name": "Đậu hũ non hấp nấm",           "category": "Món giảm cân"},
        {"name": "Đậu hũ trắng hấp",             "category": "Món giảm cân"},
        {"name": "Đậu lăng hầm",                 "category": "Món giảm cân"},
        {"name": "Đậu phộng rang muối",          "category": "Món tăng cân"},
        {"name": "Đậu que luộc",                 "category": "Món giảm cân"},
        {"name": "Đu đủ tươi",                   "category": "Món giảm cân"},
        {"name": "Edamame hấp muối",             "category": "Món quốc tế gym"},
        {"name": "Gà cà ri xanh kiểu Thái",      "category": "Món quốc tế gym"},
        {"name": "Gà chiên không dầu + cơm",     "category": "Món đa dạng gym"},
        {"name": "Gà nạc chiên không dầu",       "category": "Món giảm cân"},
        {"name": "Gà xào rau củ lẫn lộn",        "category": "Món đa dạng gym"},
        {"name": "Gạo dẻo nấu",                  "category": "Món tăng cân"},
        {"name": "Gạo lứt + thịt nạc nướng",     "category": "Món đa dạng gym"},
        {"name": "Gạo lứt nấu",                  "category": "Món đa dạng gym"},
        {"name": "Granola + sữa tươi",            "category": "Món tăng cân"},
        {"name": "Granola ngũ cốc",              "category": "Món tăng cân"},
        {"name": "Hải sản nướng lẫn lộn",        "category": "Món đa dạng gym"},
        {"name": "Hạt điều rang",                "category": "Món tăng cân"},
        {"name": "Hạt hạnh nhân rang không muối","category": "Món giảm cân"},
        {"name": "Hỗn hợp hạt + hoa quả",        "category": "Món tăng cân"},
        {"name": "Hủ tiếu gà",                   "category": "Món đa dạng gym"},
        {"name": "Khoai lang luộc",              "category": "Món đa dạng gym"},
        {"name": "Khoai tây hấp",                "category": "Món đa dạng gym"},
        {"name": "Lòng trắng trứng luộc",        "category": "Món giảm cân"},
        {"name": "Lúa mạch nấu + cá hấp",        "category": "Món đa dạng gym"},
        {"name": "Mật ong nguyên chất",          "category": "Món tăng cân"},
        {"name": "Mì ống lứt + sốt cà chua",     "category": "Món đa dạng gym"},
        {"name": "Mì sợi nấu",                   "category": "Món đa dạng gym"},
        {"name": "Mì Ý sốt thịt bò nạc",         "category": "Món tăng cân"},
        {"name": "Miến gà nấm",                  "category": "Món đa dạng gym"},
        {"name": "Mực luộc tỏi ớt",             "category": "Món giảm cân"},
        {"name": "Nấm hương xào",                "category": "Món giảm cân"},
        {"name": "Nho tươi",                     "category": "Món giảm cân"},
        {"name": "Nước cam tươi",                "category": "Món đa dạng gym"},
        {"name": "Nước mía tươi",                "category": "Món tăng cân"},
        {"name": "Phở bò nạc",                   "category": "Món đa dạng gym"},
        {"name": "Phở gà",                       "category": "Món đa dạng gym"},
        {"name": "Phô mai cottage không béo",    "category": "Món giảm cân"},
        {"name": "Phô mai mozzarella",           "category": "Món tăng cân"},
        {"name": "Pizza topping gà + rau",        "category": "Món tăng cân"},
        {"name": "Quinoa nấu với rau + gà",       "category": "Món quốc tế gym"},
        {"name": "Rau cần vịt luộc",             "category": "Món giảm cân"},
        {"name": "Rau spinach hấp",              "category": "Món giảm cân"},
        {"name": "Salad cá ngừ dầu olive",        "category": "Món giảm cân"},
        {"name": "Salad đậu gà + rau tươi",       "category": "Món giảm cân"},
        {"name": "Salad gà nướng + rau xanh",     "category": "Món giảm cân"},
        {"name": "Salad tôm + dâu tây",           "category": "Món giảm cân"},
        {"name": "Sinh tố protein chuối",         "category": "Món tăng cân"},
        {"name": "Smoothie chuối + sữa",          "category": "Món tăng cân"},
        {"name": "Socola đen 70%",                "category": "Món quốc tế gym"},
        {"name": "Sữa chua Hy Lạp + ngũ cốc",    "category": "Món tăng cân"},
        {"name": "Sữa chua Hy Lạp không đường",   "category": "Món giảm cân"},
        {"name": "Sữa đặc 200ml",                 "category": "Món tăng cân"},
        {"name": "Sữa tươi không đường 200ml",    "category": "Món đa dạng gym"},
        {"name": "Sup đậu lăng + rau",            "category": "Món giảm cân"},
        {"name": "Sup hải sản + rau",             "category": "Món đa dạng gym"},
        {"name": "Taco cá nướng",                 "category": "Món quốc tế gym"},
        {"name": "Táo đỏ",                        "category": "Món giảm cân"},
        {"name": "Thịt bò kiểu Hàn nướng",        "category": "Món quốc tế gym"},
        {"name": "Thịt bò nạc hấp",              "category": "Món giảm cân"},
        {"name": "Thịt bò nướng",                "category": "Món đa dạng gym"},
        {"name": "Thịt bò xào cần tây",          "category": "Món giảm cân"},
        {"name": "Thịt gà rán giòn",             "category": "Món tăng cân"},
        {"name": "Thịt heo nạc hấp",             "category": "Món giảm cân"},
        {"name": "Thịt vịt nạc luộc",            "category": "Món giảm cân"},
        {"name": "Tôm hấp sả",                   "category": "Món giảm cân"},
        {"name": "Tôm luộc nước muối",           "category": "Món giảm cân"},
        {"name": "Trứng cút nướng",              "category": "Món đa dạng gym"},
        {"name": "Trứng cút nướng + khoai tây",  "category": "Món đa dạng gym"},
        {"name": "Trứng gà chiên",               "category": "Món đa dạng gym"},
        {"name": "Trứng gà xào tỏi",             "category": "Món đa dạng gym"},
        {"name": "Trứng omelet + rau cà chua",   "category": "Món đa dạng gym"},
        {"name": "Trứng trộn + bánh mì nguyên hạt","category": "Món đa dạng gym"},
        {"name": "Ức gà hấp gừng",               "category": "Món giảm cân"},
        {"name": "Ức gà nướng lá chanh",         "category": "Món giảm cân"},
        {"name": "Ức gà xào bông cải xanh",      "category": "Món giảm cân"},
        {"name": "Xà lách trộn dầu olive",       "category": "Món giảm cân"},
        {"name": "Yến mạch ngâm sữa không đường","category": "Món đa dạng gym"},
    ]


def main():
    print("=" * 60, flush=True)
    print("  Food Image Downloader - Gym Nutrition App", flush=True)
    print("=" * 60, flush=True)

    existing = {}
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            data = json.load(f)
        for entry in data.get("foods", []):
            existing[entry["food_name"]] = entry
        success_only = {k: v for k, v in existing.items() if v.get("success")}
        print(f"Resuming - {len(success_only)} succeeded, {len(existing)-len(success_only)} failed previously.\n", flush=True)

    all_foods = read_csv_foods() + supplemental_foods()
    seen = set()
    unique_foods = []
    for food in all_foods:
        name = food["name"]
        if name and name not in seen:
            seen.add(name)
            unique_foods.append(food)
    print(f"Total unique foods: {len(unique_foods)}\n", flush=True)

    image_pool = preload_category_images()
    pool_idx = {cat: 0 for cat in image_pool}

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    failed = []

    for idx, food in enumerate(unique_foods, 1):
        name     = food["name"]
        category = food.get("category", "")

        if name in existing and existing[name].get("success"):
            print(f"[{idx:3d}/{len(unique_foods)}] SKIP  {name}", flush=True)
            results.append(existing[name])
            continue

        meal_cat  = get_meal_category(name)
        base_name = generate_random_name(10)
        print(f"[{idx:3d}/{len(unique_foods)}] {name}", flush=True)
        print(f"          -> {meal_cat}  file={base_name}", flush=True)

        urls = image_pool.get(meal_cat, []) or image_pool.get(FALLBACK_CATEGORY, [])
        img_bytes = None
        if urls:
            url = urls[pool_idx.get(meal_cat, 0) % len(urls)]
            pool_idx[meal_cat] = pool_idx.get(meal_cat, 0) + 1
            img_bytes = download_image_bytes(url)

        success = False
        if img_bytes and save_image_sizes(img_bytes, base_name):
            success = True
            print(f"          saved OK", flush=True)
        else:
            failed.append(name)
            print(f"          FAILED", flush=True)

        entry = {
            "food_name":    name,
            "category":     category,
            "file_name":    base_name,
            "file_ext":     "jpg",
            "directory":    "foods",
            "meal_category": meal_cat,
            "success":      success,
        }
        results.append(entry)

        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump({"foods": results}, f, ensure_ascii=False, indent=2)

        if idx < len(unique_foods):
            time.sleep(random.uniform(0.4, 1.0))

    print("\n" + "=" * 60, flush=True)
    print(f"Done: {len(results)-len(failed)}/{len(results)} succeeded", flush=True)
    if failed:
        print(f"Failed ({len(failed)}):", flush=True)
        for n in failed[:20]:
            print(f"  - {n}", flush=True)
    print(f"Manifest: {MANIFEST_PATH}", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()