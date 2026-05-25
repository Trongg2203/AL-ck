#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Food Image Downloader for Gym Nutrition App
============================================
Uses exact source images from Viện Dinh Dưỡng whenever the food id/code/name
matches the source API. If no exact source image exists, it generates a neutral
named placeholder instead of assigning an unrelated random category photo.

Stores images as:
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
from PIL import Image, ImageDraw, ImageFont

BASE_DIR      = Path(__file__).resolve().parent.parent
STORAGE_DIR   = BASE_DIR / "server-qlsv" / "public" / "uploads" / "foods"
DATA_DIR      = BASE_DIR / "AI_ck" / "data"
CSV_PATH      = DATA_DIR / "raw" / "nutrition_data.csv"
MANIFEST_PATH = DATA_DIR / "food_images_manifest.json"
API_RAW_PATH  = BASE_DIR / "AI_ck" / "api_raw_data.json"

SIZES = {"lg": (800, 600), "md": (400, 300), "xs": (100, 75)}
SOURCE_API_URL = "https://viendinhduong.vn/api/fe/tool/getPageFoodData"
SOURCE_IMAGE_BASE_URL = "https://viendinhduong.vn"
PLACEHOLDER_SOURCE = "generated-placeholder-v2"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# Keywords are matched diacritic-aware and by whole tokens (see
# get_meal_category). Keep Vietnamese diacritics so "cẩm" (in "thập cẩm")
# never collides with "cam" (orange), and "gạo" (rice) never collides with
# "gà" (chicken). Category order still controls priority; longer phrases are
# checked first inside each category.
MEAL_CATEGORY_MAP = [
    (["ức gà", "đùi gà", "lườn gà", "gà tây", "gà"], "Chicken"),
    (["cá hồi", "cá ngừ", "cá basa", "cá ba sa", "cá thu", "cá rô phi",
      "cá chép", "cá bống", "tôm", "mực", "cua", "ghẹ", "hàu", "ngao",
      "ốc", "trai", "sò điệp", "bạch tuộc", "hải sản", "cá"], "Seafood"),
    (["thịt bò", "phở bò", "bún bò", "sườn bò", "bít tết", "bulgogi",
      "bò nướng", "bò xào", "bò cuốn", "bò khô", "bò sốt", "bò nhừ",
      "bò xíu mại", "bì bò", "hủ tiếu bò", "nấu bò"], "Beef"),
    (["thịt heo", "thịt lợn", "sườn heo", "ba chỉ", "heo quay"], "Pork"),
    (["vịt"], "Lamb"),
    (["cơm", "gạo lứt", "gạo", "pasta", "mì ý", "mì quảng", "mì ống",
      "mì sợi", "mì xào", "mì gà", "mỳ chờ", "phở", "bún", "miến",
      "hủ tiếu", "bánh canh", "bánh đa", "bánh gạo", "xôi", "lúa mạch",
      "quinoa", "ramen", "udon", "pad thai", "bulgur", "noodle"], "Pasta"),
    (["đậu hũ", "đậu phụ", "tofu", "edamame", "đậu lăng", "đậu đen",
      "đậu xanh", "đậu gà", "đậu que", "rau", "bông cải", "măng tây",
      "nấm", "cà rốt", "cà chua", "cải xoăn", "cải xoong", "bắp cải",
      "xà lách", "khoai lang", "khoai tây", "củ cải", "bí đao", "bầu",
      "cần tây", "spinach", "kale", "dưa chuột", "dưa leo", "hummus",
      "guacamole", "salad", "kimchi"], "Vegetarian"),
    (["trứng vịt", "trứng gà", "trứng", "sữa chua", "sữa tươi", "sữa bò",
      "sữa dê", "sữa đậu", "sữa milo", "sữa bột", "phô mai",
      "váng sữa", "granola", "bánh mì", "bánh mỳ", "smoothie", "sinh tố", "protein",
      "đậu phộng", "hạt điều", "hạnh nhân", "bữa sáng", "yến mạch", "ngũ cốc",
      "pancake", "sandwich", "omelet", "shakshuka", "onigiri"], "Breakfast"),
    (["mật ong", "socola", "sô cô la", "cacao", "chuối", "táo", "cam",
      "nho", "dâu tây", "việt quất", "đu đủ", "dưa hấu", "xoài", "kiwi",
      "dâu đen", "avocado", "trái cây", "nước mía", "nước cam", "chè",
      "tào phớ", "caramen", "bánh trôi", "bánh quy", "sữa đặc"], "Dessert"),
]

# Legacy supplemental_foods entries near the bottom of this file are mostly
# typed without Vietnamese accents. Keep these aliases explicit instead of
# stripping accents globally, because broad ASCII tokens such as "cam", "bo",
# and "dau" are ambiguous.
LEGACY_ASCII_MEAL_CATEGORY_MAP = [
    (["uc ga", "dui ga", "luon ga", "thit ga", "ga tay", "pho ga", "ga"], "Chicken"),
    (["ca hoi", "ca ngu", "ca basa", "ca ba sa", "ca thu", "ca ro phi",
      "ca chep", "ca bong", "tom", "muc", "cua", "ghe", "hau", "ngao",
      "oc", "canh trai", "so diep", "bach tuoc", "hai san", "ca kho",
      "canh chua ca", "canh ca", "lau rau ca", "ca hap", "ca nuong",
      "ca sot"], "Seafood"),
    (["thit bo", "pho bo", "bun bo", "suon bo", "bit tet", "bo xao",
      "hu tieu bo", "mi y thit bo", "bulgogi bo"], "Beef"),
    (["thit heo", "thit lon", "suon heo", "thit ba chi", "heo quay",
      "heo"], "Pork"),
    (["thit vit", "vit"], "Lamb"),
    (["com", "gao lut", "gao", "pasta", "mi y", "mi quang", "mi ong",
      "mi soi", "mi xao", "mi ga", "my cho", "bun", "mien",
      "hu tieu", "banh canh", "banh da", "banh gao", "xoi", "lua mach",
      "quinoa", "ramen", "udon", "pad thai", "bulgar", "bulgur",
      "noodle"], "Pasta"),
    (["dau hu", "dau phu", "tofu", "edamame", "dau lang", "dau den",
      "dau xanh", "dau ga", "dau que", "rau", "bong cai", "mang tay",
      "nam", "ca rot", "ca chua", "su hao", "cai xoan", "bap cai", "xa lach",
      "khoai lang", "khoai tay", "cu cai", "bi dao", "bau", "can tay",
      "spinach", "kale", "dua chuot", "dua leo", "hummus", "guacamole",
      "salad", "kimchi"], "Vegetarian"),
    (["trung vit", "trung ga", "trung", "sua chua", "sua tuoi", "pho mai",
      "vang sua", "granola", "banh mi", "banh my", "smoothie", "sinh to", "protein",
      "dau phong", "hat dieu", "hanh nhan", "bua sang", "yen mach",
      "ngu coc", "pancake", "sandwich", "omelet", "shakshuka",
      "onigiri"], "Breakfast"),
    (["mat ong", "socola", "so co la", "cacao", "chuoi", "tao", "cam tuoi",
      "nuoc cam", "nho", "dau tay", "viet quat", "du du", "dua hau",
      "xoai", "kiwi", "bo avocado", "avocado", "trai cay", "nuoc mia",
      "che", "tao pho", "caramen", "banh troi", "banh quy", "sua dac"],
     "Dessert"),
]

CATEGORY_OVERRIDE_MAP = [
    (["đậu gà", "dau ga", "salad đậu gà", "salad dau ga"], "Vegetarian"),
    (["rau cần vịt"], "Vegetarian"),
    (["trứng gà", "trứng vịt", "trứng cút nướng", "trung ga", "trung vit",
      "trung cut nuong"], "Breakfast"),
]
FALLBACK_CATEGORY = "Miscellaneous"


def normalize(text):
    text = unicodedata.normalize("NFC", str(text)).casefold()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = text.replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def contains_phrase(tokens, phrase_tokens):
    if not phrase_tokens or len(phrase_tokens) > len(tokens):
        return False
    window_size = len(phrase_tokens)
    return any(
        tokens[i:i + window_size] == phrase_tokens
        for i in range(len(tokens) - window_size + 1)
    )


def find_best_category(normalized_name, category_map):
    tokens = normalized_name.split()
    for keywords, category in category_map:
        ordered_keywords = sorted(
            keywords,
            key=lambda keyword: len(normalize(keyword).split()),
            reverse=True,
        )
        for keyword in ordered_keywords:
            keyword_tokens = normalize(keyword).split()
            if contains_phrase(tokens, keyword_tokens):
                return category
    return None


def has_vietnamese_chars(text):
    return any(ord(char) > 127 for char in str(text))


def remove_diacritics(text):
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def lookup_key(text):
    return normalize(text)


def ascii_lookup_key(text):
    return normalize(remove_diacritics(text))


def get_meal_category(food_name):
    n = normalize(food_name)
    category = find_best_category(n, CATEGORY_OVERRIDE_MAP)
    if category:
        return category
    category_map = MEAL_CATEGORY_MAP if has_vietnamese_chars(food_name) else LEGACY_ASCII_MEAL_CATEGORY_MAP
    category = find_best_category(n, category_map)
    if category:
        return category
    return FALLBACK_CATEGORY


def generate_random_name(length=10):
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def full_source_image_url(path_or_url):
    if not path_or_url:
        return None
    if str(path_or_url).startswith(("http://", "https://")):
        return str(path_or_url)
    return SOURCE_IMAGE_BASE_URL + "/" + str(path_or_url).lstrip("/")


def fetch_source_dishes():
    try:
        resp = requests.get(
            SOURCE_API_URL,
            params={"page": 1, "pageSize": 2000},
            headers={**HEADERS, "Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        dishes = resp.json().get("data") or []
        if dishes:
            print(f"Loaded {len(dishes)} source-image records from Viện Dinh Dưỡng.", flush=True)
            return dishes
    except Exception as e:
        print(f"[warn] Could not fetch source API, falling back to local raw data: {e}", flush=True)

    if API_RAW_PATH.exists():
        with open(API_RAW_PATH, encoding="utf-8") as f:
            dishes = json.load(f).get("data") or []
        print(f"Loaded {len(dishes)} source-image records from local api_raw_data.json.", flush=True)
        return dishes

    return []


def build_source_image_index(dishes):
    index = {
        "id": {},
        "code": {},
        "name": {},
        "name_ascii": {},
    }
    for dish in dishes:
        image_url = full_source_image_url(dish.get("image"))
        if not image_url:
            continue

        dish_id = str(dish.get("_id") or dish.get("id") or "").strip()
        code = str(dish.get("code") or "").strip()
        name = str(dish.get("name_vi") or "").strip()

        if dish_id:
            index["id"].setdefault(dish_id, image_url)
        if code:
            index["code"].setdefault(code, image_url)
        if name:
            index["name"].setdefault(lookup_key(name), image_url)
            index["name_ascii"].setdefault(ascii_lookup_key(name), image_url)

    print(
        "Source image index: "
        f"{len(index['id'])} ids, {len(index['code'])} codes, {len(index['name'])} names.",
        flush=True,
    )
    return index


def find_source_image_url(food, source_index):
    food_id = str(food.get("id") or "").strip()
    code = str(food.get("code") or "").strip()
    name = str(food.get("name") or "").strip()

    if food_id and food_id in source_index["id"]:
        return source_index["id"][food_id]
    if code and code in source_index["code"]:
        return source_index["code"][code]

    name_key = lookup_key(name)
    if name_key in source_index["name"]:
        return source_index["name"][name_key]

    ascii_key = ascii_lookup_key(name)
    if ascii_key in source_index["name_ascii"]:
        return source_index["name_ascii"][ascii_key]

    return None


def load_font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\seguisb.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    words = str(text).split()
    if not words:
        return [""]

    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        width = draw.textbbox((0, 0), candidate, font=font)[2]
        if width <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:4]


def generate_placeholder_image_bytes(food_name, meal_category, category):
    img = Image.new("RGB", (800, 600), "#141414")
    draw = ImageDraw.Draw(img)

    palette = {
        "Chicken": ("#ffe3a3", "#5a3b08"),
        "Seafood": ("#b8efff", "#073f50"),
        "Beef": ("#ffd0c4", "#5d1409"),
        "Pork": ("#ffd7df", "#5b1726"),
        "Lamb": ("#ead8ff", "#37115d"),
        "Pasta": ("#fff0b3", "#51420a"),
        "Vegetarian": ("#c9f7c8", "#14521b"),
        "Breakfast": ("#ffe0ad", "#593300"),
        "Dessert": ("#ffd3ef", "#5d0d3a"),
        "Miscellaneous": ("#d8e0ea", "#26313d"),
    }
    accent, dark = palette.get(meal_category, palette["Miscellaneous"])

    draw.rectangle((0, 0, 800, 600), fill=dark)
    draw.ellipse((-150, -180, 420, 390), fill=accent)
    draw.ellipse((480, 280, 980, 760), fill="#ffffff")
    draw.rounded_rectangle((54, 64, 746, 536), radius=42, fill="#f7f4ee")

    # Simple plate mark: deliberately generic, because this is a truthful
    # fallback for foods that do not have an exact source photo.
    draw.ellipse((94, 104, 304, 314), fill="#ffffff", outline="#ded6c8", width=8)
    draw.ellipse((134, 144, 264, 274), fill=accent)
    draw.arc((358, 112, 430, 286), start=270, end=90, fill="#3a3a3a", width=8)
    draw.line((454, 112, 454, 286), fill="#3a3a3a", width=8)
    draw.line((474, 112, 474, 286), fill="#3a3a3a", width=8)

    title_font = load_font(46, bold=True)
    small_font = load_font(24)
    tag_font = load_font(22, bold=True)

    max_width = 640
    lines = wrap_text(draw, food_name, title_font, max_width)
    y = 342
    for line in lines:
        draw.text((80, y), line, fill="#171717", font=title_font)
        y += 54

    draw.rounded_rectangle((80, 472, 360, 514), radius=18, fill=accent)
    draw.text((104, 480), meal_category, fill=dark, font=tag_font)

    if category:
        category_text = str(category)[:34]
        draw.text((80, 522), category_text, fill="#5f5f5f", font=small_font)

    output = BytesIO()
    img.save(output, "JPEG", quality=90, optimize=True)
    return output.getvalue()


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
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name_vi", row.get("name", "")).strip()
            cat  = row.get("category", "").strip()
            if name:
                foods.append({
                    "id": row.get("id", "").strip(),
                    "code": row.get("code", "").strip(),
                    "name": name,
                    "category": cat,
                })
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

    source_index = build_source_image_index(fetch_source_dishes())

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    failed = []

    for idx, food in enumerate(unique_foods, 1):
        name     = food["name"]
        category = food.get("category", "")
        meal_cat = get_meal_category(name)
        source_url = find_source_image_url(food, source_index)
        expected_source = source_url or PLACEHOLDER_SOURCE

        if name in existing and existing[name].get("success"):
            previous = existing[name]
            previous_cat = previous.get("meal_category")
            previous_source = previous.get("image_source") or previous.get("source_url")
            if previous_cat == meal_cat and previous_source == expected_source:
                print(f"[{idx:3d}/{len(unique_foods)}] SKIP  {name}", flush=True)
                results.append(previous)
                continue
            print(
                f"[{idx:3d}/{len(unique_foods)}] REFRESH {name}",
                flush=True,
            )
            if previous_cat != meal_cat:
                print(f"          category changed: {previous_cat} -> {meal_cat}", flush=True)
            if previous_source != expected_source:
                print("          image source changed: category-random -> exact/placeholder", flush=True)
        else:
            print(f"[{idx:3d}/{len(unique_foods)}] {name}", flush=True)

        base_name = generate_random_name(10)
        source_label = "source-api" if source_url else "generated-placeholder"
        print(f"          -> {meal_cat}  {source_label}  file={base_name}", flush=True)

        img_bytes = None
        image_source = expected_source
        if source_url:
            img_bytes = download_image_bytes(source_url)
            if not img_bytes:
                print("          source image failed; using named placeholder", flush=True)
                image_source = PLACEHOLDER_SOURCE

        if not img_bytes:
            img_bytes = generate_placeholder_image_bytes(name, meal_cat, category)

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
            "image_source":  image_source,
            "source_url":    source_url,
            "success":      success,
        }
        results.append(entry)

        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump({"foods": results}, f, ensure_ascii=False, indent=2)

        if idx < len(unique_foods):
            time.sleep(random.uniform(0.4, 1.0))

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump({"foods": results}, f, ensure_ascii=False, indent=2)

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
