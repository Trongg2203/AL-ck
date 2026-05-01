# 📸 Image Assets

Thư mục chứa hình ảnh cho món ăn và nguyên liệu.

## 📁 Cấu trúc

```
images/
├── dishes/         # Ảnh món ăn chính
├── ingredients/    # Ảnh nguyên liệu
├── thumbnails/     # Ảnh thumbnail (nhỏ gọn)
└── README.md       # File này
```

## 📋 Quy ước đặt tên

### Món ăn (dishes/)
- Format: `{name_vi_slug}.png` hoặc `.jpg`
- VD: `qua_coc_dam.png`, `com_tam_suon_nuong.jpg`
- Nhiều ảnh: `qua_coc_dam_1.png`, `qua_coc_dam_2.png`

### Nguyên liệu (ingredients/)
- Format: `{ingredient_name}.png`
- VD: `banh_quay.png`, `duong.png`, `thit_ba_chi.jpg`

### Thumbnails (thumbnails/)
- Format: `{name_vi_slug}_thumb.png`
- Kích thước khuyến nghị: 200x200px
- VD: `qua_coc_dam_thumb.png`

## 🎨 Khuyến nghị kỹ thuật

- **Format**: PNG (có transparency) hoặc JPG (nén tốt)
- **Kích thước món ăn**: 800x600px hoặc 1024x768px
- **Kích thước thumbnail**: 200x200px
- **Dung lượng**: < 500KB/ảnh để load nhanh

## 💡 Lấy ảnh từ đâu?

1. **Chụp tự chế biến** (best quality, authentic)
2. **Viện Dinh Dưỡng** (nếu họ có API images)
3. **Food blogs Việt** (nhớ xin phép hoặc credit)
4. **Stock photos** (Unsplash, Pexels - tìm Vietnamese food)

## 🔗 Sử dụng trong JSON

```json
{
  "name_vi": "Quả cóc dầm",
  "images": [
    "data/images/dishes/qua_coc_dam.png",
    "data/images/dishes/qua_coc_dam_closeup.png"
  ],
  "thumbnail": "data/images/thumbnails/qua_coc_dam_thumb.png"
}
```

## 📝 Notes

- Tất cả path là **relative** từ root project
- Nếu thiếu ảnh → UI hiển thị placeholder
- Có thể dùng URL external nếu host trên CDN
