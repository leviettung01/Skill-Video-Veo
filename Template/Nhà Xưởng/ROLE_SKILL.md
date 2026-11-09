# ROLE SKILL: FLOW FINAL PIPELINE (VEO GOOGLE FLOW OMNI FLASH 10S — HYPER-REALISTIC 2K REF & 1080P VIDEO)

Quy trình khép kín từ thông tin sản phẩm TikTok Shop đến **Video Final 30s** (`1080x1920`, `60fps`):
1. **Bước 1 (Kịch bản B1 — Đa Nhân Vật × Đa Kịch Bản / Sản phẩm)**:
   - Nhân vật 1 (`NV1`): `V1` (Kịch bản 1: Trợ Giá Sàn), `V3` (`nv1_v2` — Kịch bản 2: Báo Động Giá Xưởng), `V5` (`nv1_v3` — Kịch bản 3: Xả Kho Lô Mới).
   - Nhân vật 2 (`NV2`): `V2` (`nv2_v1` — Kịch bản 1: Giá Sốc Tận Xưởng), `V4` (`nv2_v2` — Kịch bản 2: Không Qua Trung Gian), `V6` (`nv2_v3` — Kịch bản 3: Săn Deal Tận Gốc).
   - Nhân vật 3 (`NV3` — Nam): `nv3_v1`, `nv3_v2`, `nv3_v3`.
   - Mỗi kịch bản gồm 3 phân cảnh × 10s, 42–48 từ đọc/cảnh, áp dụng luật thang giá giảm dần ở Cảnh 2, chia 3 mốc `TIMELINE` kết thúc tại `10.0s`.
2. **Bước 2 (Tạo Ảnh Tham Chiếu 9:16 2K `1536x2752` Hyper-Photorealistic bằng Nano Banana 2.1 `BELUGA`)**:
   - **Cấu trúc Prompt Ảnh Ref 2K Chuẩn Siêu Thực (6 Khối)**:
     1. `Subject & Identity`: Cận trung nửa người trên (`close-medium upper-body portrait`, từ đỉnh đầu có headroom tự nhiên tới ngang eo/hông, khoảng cách máy `1.2m`) để gương mặt nhân vật chiếm tỉ lệ lớn, sắc nét từng chi tiết, khóa 100% đường nét khuôn mặt từ Character Reference.
     2. `Skin & Makeup`: Lỗ chân lông tự nhiên nhìn thấy rõ (`detailed visible natural skin pores`), kết cấu biểu bì thật, hiệu ứng da căng bóng `Douyin glass-skin` phản chiếu ánh sáng nhẹ trên sống mũi, gò má và trán; tông da trắng hồng đều màu giữa mặt, cổ và bàn tay; trang điểm Hàn/Douyin trong trẻo (má hồng phớt, bọng mắt `aegyosal` tự nhiên, mi cong tơi, eyeliner mảnh, môi bóng `ombré` hồng anh đào; kính gọng mảnh chống lóa trong suốt 100% với NV1).
     3. `PHYSIQUE`: Tỷ lệ cơ thể người trưởng thành quyến rũ, tự nhiên (`90-60-90 feminine proportions, C-cup natural bust, slender waist` với nữ; hoặc dáng thể thao vai rộng nam tính với nam).
     4. `Expression / Pose`: Nụ cười tươi tự nhiên, đầu hơi nghiêng nhẹ, thân người xoay nhẹ góc `5-10 độ` (`relaxed asymmetry`, tuyệt đối không đứng đơ đối xứng như ma-nơ-canh).
     5. `Product Action & Lock`: Cầm và giới thiệu đúng sản phẩm thật từ Product Reference ở tầm ngực–eo với tỉ lệ kích thước chuẩn thực tế (`NOT oversized`), giữ nguyên 100% kiểu dáng, chất liệu, màu sắc, logo.
     6. `Camera, Lens & Lighting + Negative Prompt`: Chụp bằng `Sony A7R V` + ống kính `50mm f/1.4 GM` tại `f/2.0` kết hợp chất ảnh chân thật của `iPhone 16 Pro`, ánh sáng `soft diffused key light + fill light` chiếu sáng đều gương mặt không bóng gắt, xóa phông bokeh quang học mượt mà; kèm `Negative prompt` chống da nhựa AI, chống mắt lác/mờ, chống lóa kính.
   - **Upsample 2K & Upload Ngược 2K Lên Flow**: Sau khi tạo ảnh qua `ogiZ0b`, gọi `SPrCad` (`ts=1`) để tải bản **2K (`1536x2752`)** về máy, đồng thời upload bản 2K (`1536x2752`, JPEG quality 96) lên Google Flow qua `maseQ` để lấy `uuid_2k` truyền trực tiếp cho bước tạo video.
3. **Bước 3 (Tạo 3 Phân cảnh Video 10s qua Google Flow Veo 3.1 `abra_r2v_10s` — Tải chất lượng 1080p `1080x1920`)**:
   - **Khóa Đơn Ảnh Tham Chiếu 2K (`[[None, ref_uuid]]`)**: Khi đã có ảnh Ref 2K nhân vật cầm sẵn sản phẩm (`ref_uuid`), **CHỈ truyền duy nhất `[[None, ref_uuid]]`** vào `MZZa6b` (không truyền thêm `prod_uuid` lần 2) để Veo 3.1 khóa chặt 100% vào khung hình 2K gốc, không tự ý tổng hợp lại làm biến dạng khuôn mặt, mắt kính hay đổi màu ánh sáng.
   - Sau khi render xong phân cảnh video, nâng cấp và tải về ở độ phân giải **1080p (`1080x1920`)** qua RPC `p0UkFb` (`veo_3_1_upsampler_1080p`).
4. **Bước 4 (Ghép nối Final 30s 1080p 60FPS + Subtitle Karaoke + Slide Ảnh Phân Loại 20s Cuối)**:
   - Dùng FFmpeg (`flow_final_pipeline/scripts/build_final.py`) nối 3 cảnh 10s thành video 30s chuẩn **Full HD 1080p (`1080x1920`, 60fps)** kèm phụ đề Karaoke và Slide ảnh sản phẩm, xuất ra `final_videos/`.
