# ROLE SKILL: FLOW FINAL PIPELINE (VEO GOOGLE FLOW OMNI FLASH 10S — 6 VIDEOS / SẢN PHẨM)

Quy trình khép kín từ thông tin sản phẩm TikTok Shop đến **6 Video Final 30s** (`2 Nhân vật × 3 Kịch bản = 6 Video Final`, dọc `9:16`, `720p`):
1. **Bước 1 (Kịch bản B1 — 6 Video / Sản phẩm)**:
   - Nhân vật 1 (`NV1`): `V1` (Kịch bản 1: Trợ Giá Sàn), `V3` (Kịch bản 2: Báo Động Giá Xưởng / Luxury), `V5` (Kịch bản 3: Xả Kho Lô Mới).
   - Nhân vật 2 (`NV2`): `V2` (Kịch bản 1: Giá Sốc Tận Xưởng), `V4` (Kịch bản 2: Không Qua Trung Gian), `V6` (Kịch bản 3: Săn Deal Tận Gốc).
   - Mỗi kịch bản gồm 3 phân cảnh × 10s, 44–48 từ đọc/cảnh, áp dụng luật thang giá giảm dần ở Cảnh 2, chia 3 mốc `TIMELINE` kết thúc tại `10.0s`.
2. **Bước 2 (Tạo 6 Ảnh Tham Chiếu 9:16 riêng biệt `v1-refimg.jpg` .. `v6-refimg.jpg` bằng Nano Banana 2.1 — Tải chất lượng 2K `1536x2752`)**:
   - Mỗi Video Final có **1 ảnh tham chiếu và 1 bối cảnh riêng** (`V1`: Dây chuyền lắp ráp chính, `V2`: Phòng kiểm định QC, `V3`: Tổng kho pallet, `V4`: Showroom trưng bày mẫu, `V5`: Xưởng chế tác nguyên liệu, `V6`: Khu băng chuyền đóng gói tự động).
   - Gắn đúng **1 ảnh nhân vật (`NV1` / `NV2`)** + **1 ảnh sản phẩm đơn chiếc (chọn 1 phân loại hiển thị đầu tiên, không chọn ảnh ghép nhiều mẫu)**.
   - **Cấu trúc Prompt Ảnh**: Chỉ mô tả **Nhân vật + Trang phục + Bối cảnh + Hành động cầm sản phẩm + Biểu cảm + Chi tiết xung quanh**. Không mô tả lại màu sắc hay chi tiết sản phẩm bằng chữ, không viết `"no logo"` (để giữ nguyên logo/họa tiết gốc trên sản phẩm), yêu cầu lấy nguyên sản phẩm từ ảnh tham chiếu với tỉ lệ kích thước thật so với cơ thể người.
   - **Chất lượng tải Ảnh Ref**: Tải ảnh tham chiếu nhân vật cầm sản phẩm ở độ phân giải **2K (`1536x2752`)** qua RPC `SPrCad` (`ts=1`) để video đầu ra sắc nét nhất.
3. **Bước 3 (Tạo 3 Phân cảnh Video 10s B3 qua Google Flow Omni Flash, delay 15s giữa các request — Tải chất lượng 1080p `1080x1920`)**:
   - Đưa **CẢ 2 ẢNH THAM CHIẾU** vào `ref_list` của `MZZa6b`: `[Ảnh Ref Nhân vật cầm sản phẩm (ref_uuid), Ảnh Sản phẩm mẫu đơn chiếc (prod_uuid)]` + giọng nói tùy chỉnh (`voice_id`).
   - **Cấu trúc Prompt Video Ngắn Gọn (Chống biến dạng sản phẩm)**: Không mô tả lại trang phục, bối cảnh hay chi tiết sản phẩm bằng chữ. Chỉ yêu cầu bắt đầu trực tiếp từ ảnh tham chiếu ở trên, giữ nguyên 100% nhân vật + sản phẩm trên tay + bối cảnh, kèm `ACTION` ngắn gọn và `VOICE` theo 3 mốc `TIMELINE` kết thúc tại `10.0s`.
   - Sau khi render xong phân cảnh video, nâng cấp và tải về ở độ phân giải **1080p (`1080x1920`)** qua RPC `p0UkFb` (`veo_3_1_upsampler_1080p`).
4. **Bước 4 (Ghép nối Final 30s 1080p + Subtitle Karaoke + Slide Ảnh Phân Loại 20s Cuối B4)**:
   - Dùng FFmpeg (`flow_final_pipeline/scripts/build_final.py`) nối 3 cảnh 10s thành video 30s chuẩn **Full HD 1080p (`1080x1920`)**, đốt phụ đề `.ass` karaoke 1 dòng chữ in hoa (`#FFE066`), và trình chiếu **slide ảnh các phân loại sản phẩm (`390x390` ở góc trên trái `30:30`) trong suốt 20 giây cuối (`10.0s–30.0s`)**, xuất trực tiếp ra thư mục `final_videos/`.


