# ⚙️ QUY TRÌNH RENDER & HẬU KỲ: TEMPLATE ĐỒ ĂN VẶT & ĐỒ UỐNG UGC
**Tác giả:** Lê Việt Tùng - SkillAutoVeo (`Zalo: 0915967790`)

---

## 1. Sơ Đồ Pipeline 4 Bước Tự Động

```
[Bước 1: Crawl / Nhập Sản Phẩm TikTok]
   └── Tải ảnh gốc sản phẩm (túi bánh, hũ topping, cốc ăn liền) + tiêu đề + mô tả hương vị.
         ↓
[Bước 2: AI Director Phân Tích & Sinh Chuỗi Prompt Đồng Bộ (DoAnVat Generator)]
   └── Tự động khóa FIXED BACKGROUND + FIXED HAND + FIXED PRODUCT.
   └── Sinh 4 - 6 phân cảnh theo vòng đời sản phẩm: Pack Hero -> Mở gói -> Bày đĩa/Pha chế -> Cận cảnh nhân chảy/Sốt -> Thưởng thức.
         ↓
[Bước 3: Tạo Ảnh Storyboard 9:16 (2K) & Render Video Chuyển Động (1080p)]
   └── Tạo ảnh từng cảnh có gắn kèm ảnh sản phẩm gốc làm Reference để giữ chuẩn bao bì 100%.
   └── Render video 8s - 10s cho từng cảnh với chuyển động macro mượt mà (rót nước, tách vỏ bánh, khuấy đá) + âm thanh ASMR hoặc thoại.
         ↓
[Bước 4: Ghép Nối FFmpeg & Xuất Video Final 1080x1920]
   └── Nối các phân cảnh liên hoàn, cân chỉnh màu sắc tươi ngon, xuất file MP4 Final sẵn sàng đăng TikTok Shop / Reels.
```

---

## 2. Thông Số Kỹ Thuật Chuẩn
- **Tỉ lệ khung hình**: Dọc `9:16` (`1080x1920` FullHD).
- **Ảnh Storyboard mỗi cảnh**: Độ phân giải `2K (1536x2752)` hoặc `1024x1536`, bám sát ảnh sản phẩm gốc (`Strict Product Reference`).
- **Thời lượng mỗi cảnh**: `8 giây` - `10 giây` (Tổng thời lượng video Final: `30s - 48s`).
- **Tốc độ khung hình**: `30fps`, chuẩn nén `H.264 (libx264, crf 18)` + âm thanh `AAC 192kbps`.

