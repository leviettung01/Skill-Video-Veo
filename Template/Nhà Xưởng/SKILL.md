# TEMPLATE: NHÀ XƯỞNG (XẢ KHO TẬN GỐC) — QUY TRÌNH TẠO VIDEO 30s

Template **Nhà Xưởng** tạo bộ video TikTok Shop Affiliate 30 giây (3 cảnh × 10s, dọc 9:16, 1080p) theo phong cách **Nhân vật đứng tại Nhà xưởng / Phòng kiểm định QC / Tổng kho Pallet / Showroom trưng bày / Khu đóng gói xuất xưởng** cầm trực tiếp sản phẩm trên tay và giới thiệu ưu đãi trợ giá tận xưởng.

---

## 1. Cấu trúc thư mục Template `Template/Nhà Xưởng`

- `template_config.json` — Cấu hình bối cảnh, trang phục, hành động từng cảnh, số lượng video mặc định mỗi nhân vật (`default_videos_per_character: 3`).
- `SKILL.md` — Tài liệu quy trình tổng thể của Template Nhà Xưởng.
- `KICH_BAN.md` — Quy tắc viết kịch bản 3 cảnh × 10s (Hook Trợ Giá / Giá Sốc -> Neo Giá 3 Tầng -> USP & CTA Giỏ Hàng).
- `PROMPT_TEMPLATES.md` — Công thức Prompt tạo Ảnh Tham Chiếu 2K (`Nano Banana 2.1 / BELUGA`) và Prompt Video 10s (`Veo 3.1 Omni Flash`).
- `RENDER.md` — Quy tắc ghép 3 cảnh 10s + Subtitle Karaoke 1 dòng + Slide ảnh sản phẩm 4s cuối bằng FFmpeg.
- `generator.py` — Script tự động phân tích thông tin sản phẩm (`info.json` + ảnh sản phẩm) và sinh `prompts.json` + `spec_v*.json` theo số lượng nhân vật và số video/nhân vật được cấu hình.

---

## 2. Quy trình tự động từ Link / ID Sản phẩm

1. **Nhận Link / ID sản phẩm**:
   - Kiểm tra xem `projects/<pid>/product_images/info.json` và `prod_1.jpg` đã có sẵn chưa.
   - Nếu chưa có: Tự động crawl thông tin & tải bộ ảnh sản phẩm qua:
     - **Cách 1 (Primary)**: SPAI Auto API (`tools.spaiauto.com/api.php`).
     - **Cách 2 (Fallback)**: Trình duyệt Chrome TikTokShop (`tiktok_chrome_profile`) + Giải Captcha tự động (`BoxPhone YOLO`).
2. **Chọn lọc ảnh sản phẩm tham chiếu**:
   - Chọn 1 ảnh đơn chiếc rõ nét nhất làm `primary_product_refs` (để AI tạo ảnh nhân vật cầm sản phẩm không bị nhân bản nhiều món).
   - Chọn tối đa 5 ảnh đẹp nhất làm `slide_overlay_files` (hiển thị ở 4 giây cuối video).
3. **Sinh kịch bản & Prompt (`Template/Nhà Xưởng/generator.py`)**:
   - Đọc danh sách nhân vật đang bật trong `flow_final_pipeline/voices_and_characters.json` và số lượng video trên mỗi nhân vật (`videos_per_character`).
   - Tự động sinh `prompts.json` và `spec_*.json` trong `projects/<pid>/`.
4. **Chạy Pipeline Đa Luồng (`run_all_7_videos_mt.py`)**:
   - Tạo ảnh tham chiếu 9:16 với `Nano Banana 2.1 (BELUGA)` và tải xuống bản **2K (`1536x2752`)** qua `SPrCad`.
   - Render 3 cảnh video 10s với **2 ảnh tham chiếu** (`[Ảnh Ref Nhân vật 2K, Ảnh Sản phẩm gốc]`) + `Voice ID` -> Upsample lên **1080p** (`p0UkFb`).
   - Ghép FFmpeg Final 30s (`build_final.py`) và xuất ra `final_videos/{pid}_{nv1/nv2}_v{1..N}.mp4`.

