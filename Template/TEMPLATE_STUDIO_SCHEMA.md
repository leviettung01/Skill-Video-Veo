# Hướng Dẫn Thêm Template Mới Dùng Ngay Giao Diện Studio (#007, #008, ...)

Hệ thống **Universal Character + Product Studio** tự động đọc mọi thư mục nằm trong `Template/<Tên Template>/` mà **không cần sửa HTML hay JS thủ công**.

Khi bạn đẩy bản cập nhật lên Git (hoặc nén thư mục template thành `.zip` gửi khách), khách hàng chỉ cần bấm **⬇️ Cập Nhật Code & Template Mới** hoặc **📦 Cài Gói Template (.ZIP)** ngay trong **Chợ Template** là dùng được ngay trên giao diện!

---

## 1. Cấu trúc thư mục chuẩn của một Template mới

```text
Template/
└── 007_Bien_Hinh_Cong_So/        # Tên thư mục tuỳ ý (không bắt đầu bằng . hoặc _)
    ├── template_config.json        # Bắt buộc: khai báo mã, tên, kịch bản presets
    ├── ROLE_SKILL.md               # Tuỳ chọn: mô tả kỹ năng cho AI Agent / người dùng xem
    ├── PROMPT_TEMPLATES.md         # Tuỳ chọn: tài liệu tham khảo
    ├── demo_videos/
    │   ├── kich_ban_a.mp4          # Video demo 9:16 cho preset "kich_ban_a"
    │   └── kich_ban_b.mp4          # Video demo 9:16 cho preset "kich_ban_b"
    └── demo_images/                # Tuỳ chọn: ảnh minh hoạ hiển thị trong Chợ Template
```

---

## 2. Schema file `template_config.json`

Đặt `"ui_studio": "transform"` (hoặc `"pipeline_kind": "fashion_transformation"`) và khai báo `"presets"`. Hệ thống tự sinh **Thẻ chọn kịch bản**, **Khung tải ảnh Nhân vật + Sản phẩm**, **Trình phát Video Mẫu**, **Model 2K**, và **Tiến trình render 5 bước**.

```json
{
  "code": "007",
  "id": "office_glowup_studio",
  "name": "Biến hình Công sở & Dạ tiệc",
  "subtitle": "2 cảnh 8s · Chọn nhân vật + trang phục 2K · Ghép nhạc khớp beat",
  "category": "Thời Trang / Lifestyle",
  "badge": "STUDIO NV + SP",
  "price_label": "Miễn Phí • Sẵn Sàng",
  "ui_studio": "transform",
  "pipeline_kind": "fashion_transformation",
  "supports_character": true,
  "supports_product": true,
  "character_label": "Nhân vật tham chiếu",
  "product_label": "Trang phục biến hình",
  "scenes_per_video": 2,
  "scene_duration_sec": 8,
  "video_aspect": "9:16",
  "has_subtitles": false,
  "product_prompt": "Extract the complete fashion outfit and ALL visible accessories and footwear into an ultra-clean 2-column knolling studio flat-lay on pure seamless white (#FFFFFF) with invisible ghost-mannequin volume on Left Column and stacked accessories/footwear on Right Column...",
  "presets": {
    "office_night": {
      "title": "Tăng ca → Dạ tiệc",
      "icon": "💼",
      "badge": "Bàn làm việc → Sảnh tiệc",
      "transition_style": "night_flash",
      "demo": "kich_ban_a.mp4",
      "summary": "Đóng laptop ngoài bàn làm việc → bàn tay che kín màn hình → bước vào sảnh tiệc khớp drop nhạc.",
      "before": "Opening scene description (subject wearing everyday outfit holding prop)...",
      "work": "Mid-clip action (1.8s-4.8s) leading up to eye contact...",
      "cover": "Blocking action (4.8s-6.7s) filling 100% camera frame to pitch-black...",
      "after": "Glam reveal environment setting (lighting, camera framing)...",
      "reveal_open": "0.0s-1.6s emergence out of darkness into full outfit reveal...",
      "reveal_mid": "1.6s-5.2s confident runway walk and brisk turn...",
      "reveal_end": "5.2s-8.0s sharp full-body hero pose showcase..."
    }
  }
}
```

### Ghi chú nhanh các tuỳ chọn nâng cao trong từng `preset`
- `"transition_style"`: `"sunlit"` (nắng ấm chuyển cảnh trắng-vàng) hoặc `"night_flash"` (tiệc tối bùng sáng flash hổ phách).
- `"has_dialogue"`: đặt `true` nếu kịch bản có lời thoại nhân vật (hệ thống sẽ bỏ ràng buộc cấm thoại `"or spoken dialogue"` trong prompt Veo để AI sinh khẩu hình và diễn xuất khớp thoại). `"dialogue_line"` ghi câu thoại chuẩn để hiển thị & tham chiếu.
- `"cover_item"`, `"work_open"`, `"work_label"`, `"cover_label"`: tuỳ biến từng đoạn `[0.0s–1.8s]`, `[1.8s–4.8s]`, `[4.8s–6.7s]` của Cảnh 1 mà vẫn giữ nguyên cấu trúc chuyển cảnh che kín khung `[6.7s–8.0s]`.
- `"scene1_title"`, `"scene2_title"`: đổi tên tiêu đề cảnh hiển thị.
- `"scenes"`: mảng 2 object `[{"id": "s1", "title": "...", "image_prompt": "...", "prompt": "..."}, ...]` nếu muốn tự viết 100% prompt thô thay cho các mảnh `before / work / cover / after / reveal_*`.
- `"demo"`: tên file nằm trong `demo_videos/` của chính thư mục template này (ví dụ `"kich_ban_a.mp4"`).
