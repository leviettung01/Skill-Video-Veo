# 👗 ROLE SKILL — TEMPLATE #004: MOTION CONTROL VIDEO FASHION (OMNI FLASH THAY ĐỒ THEO NHẠC & VIDEO THAM CHIẾU)

## 1. Mục Tiêu Cốt Lõi

### Bắt buộc giữ kịch bản template và chip ảnh từng bộ đồ

Khi chạy một FVT đã có phân tích, giữ `i2v_choreography_precomputed` và các khối động tác của template; chỉ thay ảnh nhân vật, phòng, mô tả sản phẩm và gán bộ đồ tại các mốc. Không thay toàn bộ bằng prompt tự viết, không dùng bảng ghép để thay các product sheet gốc. Mỗi lệnh đổi bộ đồ phải có media segment trỏ đúng ảnh bộ đồ đó và UUID ấy phải có trong danh sách ảnh gửi kèm. Trước khi gửi job, kiểm tra `submitted_prompt_audit` chứa chip đã mã hóa đúng; thiếu UUID phải dừng, không biến chip thành tên file chữ thường. Cảnh nối tiếp bắt buộc upload được frame cuối của cảnh trước; không tự thay bằng ảnh phòng ban đầu khi upload lỗi. Bản render sửa phải giữ riêng để bảo toàn kết quả cũ.
Template **#004 — Motion Control Video Fashion** được thiết kế chuyên biệt cho các video **Lookbook Thời Trang, OOTD Biến Hình Thay Đồ Theo Beat Nhạc** sử dụng khả năng **Tham Chiếu Video (Video Reference)** độc quyền của model **Omni 1.1 Flash (`abra_edit` / `6s`, `8s`, `10s`)** trên Google Flow:
- **1 Ảnh Nhân Vật Gốc chuẩn 2K (`1536x2752` / `2048x3639`)**: Đặt nhân vật cố định trong một bối cảnh đẹp (phòng ngủ ấm cúng, studio thời trang, cửa hàng luxury...). Ảnh bắt buộc đạt chuẩn **2K** để gương mặt nhân vật trong video giữ được độ nét chân thực tuyệt đối.
- **1 Bảng Nhân Vật / Character Sheet 2K (Tùy chọn)**: Giúp khóa chuẩn tỷ lệ cơ thể và form dáng khi mặc các bộ trang phục.
- **1 Video Tham Chiếu Chuyển Động & Nhạc (Reference Motion Video)**: Video mẫu có sẵn điệu nhảy / động tác tạo dáng thời trang và nhạc nền bắt trend.
- **Nhiều Bộ Đồ / Outfit Product Sheets chuẩn 2K (`Outfit 1`, `Outfit 2`, `Outfit 3`, ...)**: Các ảnh tách nền hoặc bảng chi tiết từng bộ trang phục + phụ kiện cần thay đổi theo nhạc.

---

## 2. Quy Trình Tự Động Hóa 5 Bước Chuẩn Xác

### Bước 1: Phân Tích Thời Lượng Video Tham Chiếu & Chia Khít Cho 8s Hoặc 10s
Vì trên Google Flow chỉ có model **Omni Flash** mới hỗ trợ đính kèm Video Tham Chiếu (với các mốc thời lượng chuẩn `6s`, `8s`, `10s`), hệ thống tự động đọc thời lượng thực tế $D$ của video gốc bằng `ffprobe` và chọn phương án chia tối ưu:
- **Video ~16 giây (VD `16.28s`)** $\rightarrow$ Chia thành **2 phân cảnh × 8 giây (`16s`)**.
- **Video ~20 giây (VD `20.0s`)** $\rightarrow$ Chia thành **2 phân cảnh × 10 giây (`20s`)**.
- **Video ~24 giây (VD `24.0s`)** $\rightarrow$ Chia thành **3 phân cảnh × 8 giây (`24s`)**.
- **Video ~30 giây (VD `30.0s`)** $\rightarrow$ Chia thành **3 phân cảnh × 10 giây (`30s`)**.

Hệ thống dùng FFmpeg **cắt rời trực tiếp Video Tham Chiếu thành từng file video phân cảnh** (`ref_clip_s1_8s.mp4`, `ref_clip_s2_8s.mp4`, ...) đồng thời tách riêng file **Nhạc Gốc Master (`ref_master_audio.m4a`)**.

---

### Bước 2: Phân Tích Nhịp Beat Nhạc & Điểm Chuyển Cảnh Để Xác Định Mốc Giây Thay Đồ
Trong mỗi phân cảnh đã cắt (`0.00s -> 8.00s` hoặc `0.00s -> 10.00s`), tool kết hợp:
1. **Quét chuyển cảnh hình ảnh (`ffmpeg scdet`)**: Phát hiện chính xác tích tắc video gốc giật chuyển cảnh / đổi tư thế tạo dáng.
2. **Quét đỉnh năng lượng âm thanh (`Audio Beat Onset`)**: Bắt đúng nhịp trống bass rơi để gán mốc giây thay đồ (`4:04` ở Phân cảnh 1; `3:04` và `6:12` ở Phân cảnh 2).

---

### Bước 3: Tạo Ảnh Ref Nhân Vật 2K Nối Tiếp Giữa Các Phân Cảnh (Continuity 2K Character Ref)
Để video nét căng chuẩn 2K và không bị đứt gãy trang phục khi chuyển từ Phân cảnh 1 sang Phân cảnh 2:
- **Phân cảnh 1 (`0s - 8s`)**: Mở đầu bằng **Ảnh Nhân Vật Gốc 2K** (`07_Nhan_Vat_Basic_Phong_Ngu_2K.png`), đến giây `4:04` đổi sang **Bộ Đồ 1** (`03_Product_Sheet_Quan_Xanh_2K.png`).
- **Phân cảnh 2 (`8s - 16s`)**: Mở đầu bằng **Ảnh Ref Nhân Vật 2K đang mặc sẵn Bộ Đồ 1 trong đúng phòng ngủ đó** (được tạo bằng Nano Banana 2.1 `ogiZ0b` từ `Ảnh Nhân Vật Gốc 2K + Ảnh Bộ Đồ 1 2K`, sau đó tải xuống bản 2K qua `SPrCad` và upload lại qua `maseQ`). Nhờ vậy, giây `0:00` của Phân cảnh 2 nối liền mạch 100% với giây `8:00` của Phân cảnh 1!

---

### Bước 4: Cấu Trúc Prompt Theo Timeline + Inline Asset Mention Chips Chuẩn Google Flow (`jIps6`)
Hệ thống hỗ trợ 2 chế độ Prompt đều gắn trực tiếp **Inline Media Mention Chip** (`[None, [[media_uuid, filename]]]`) vào đúng vị trí trong câu lệnh:

#### Chế độ 1: Timeline Chi Tiết (Timeline Motion-Control Pro — Mặc Định Khuyên Dùng)
- **Phân cảnh 1 (`0.00s - 8.00s`)**:
  > `Bắt đầu video với ảnh 1 [07_Nhan_Vat_Basic_Phong_Ngu_2K.png] , nhân vật có hành động, thần thái biểu cảm và nhịp chuyển động cơ thể giống hệt như video tham chiếu, giữ nguyên 100% bối cảnh căn phòng và ánh sáng tự nhiên của ảnh 1. TIMELINE THEO NHẠC: [0:00 - 4:04] Nhân vật mặc bộ đồ như ảnh mở đầu và thực hiện đúng động tác theo video gốc. Tại giây 4:04 (đúng nhịp beat chuyển cảnh), nhân vật lập tức mặc bộ đồ [03_Product_Sheet_Quan_Xanh_2K.png] (áo yếm vàng vạt xòe peplum kèm vòng cổ hoa đỏ, quần dài ống suông rộng màu xanh coban đậm, túi xách vàng và giày sneaker vàng) chuẩn tỷ lệ cơ thể và form trang phục như bảng tham chiếu [01_Character_Sheet_4_Outfits_2K.png] và từ [4:04 - 8:00] tiếp tục có hành động tạo dáng thời trang mượt mà như video gốc. Giữ gương mặt nhân vật sắc nét chuẩn 2K, không biến dạng tay hay trang phục. Dùng nhạc của video gốc luôn.`

- **Phân cảnh 2 (`8.00s - 16.00s` | Clip 2 `0.00s - 8.00s`)**:
  > `Nhân vật [continuity_char_outfit_1_quan_xanh_2K.jpg] có hành động, biểu cảm và nhịp nhún nhảy theo nhạc giống hệt như video tham chiếu, giữ nguyên 100% bối cảnh căn phòng của ảnh mở đầu. TIMELINE THEO NHẠC: [0:00 - 3:04] Nhân vật mặc bộ đồ như ảnh mở đầu và thực hiện đúng động tác theo video gốc. Tại giây 3:04 (đúng nhịp beat chuyển cảnh), nhân vật lập tức mặc bộ đồ [04_Product_Sheet_Vay_Vang_2K.png] (váy ngắn cổ yếm xếp tầng phồng màu vàng bơ, dây buộc tóc scrunchie vàng, túi kẹp nách quai nhún bèo vàng, tất trắng và giày búp bê vàng), tiếp tục tạo dáng từ [3:04 - 6:12]. Đến giây 6:12 (nhịp beat chuyển cảnh tiếp theo), nhân vật lập tức mặc bộ đồ [06_Product_Sheet_Quan_Be_2K.png] (áo yếm vàng vạt xòe, quần tây ống rộng xếp ly màu be kem, mắt kính gọng hồng pastel, vòng tay vàng và giày búp bê vàng) chuẩn tỷ lệ cơ thể và form trang phục như bảng tham chiếu [01_Character_Sheet_4_Outfits_2K.png] và từ [6:12 - 8:00] tiếp tục có hành động tạo dáng thời trang mượt mà như video gốc. Giữ gương mặt nhân vật sắc nét chuẩn 2K, không biến dạng tay hay trang phục. Dùng nhạc của video gốc luôn.`

#### Chế độ 2: Ngắn Gọn Chuẩn Google Flow (Concise Flow Chip Style)
- **Phân cảnh 1**:
  > `Bắt đầu video với ảnh 1 [07_Nhan_Vat_Basic_Phong_Ngu_2K.png] , nhân vật có hành động như video, giữ nguyên bối cảnh của ảnh 1, Tại giây 4:04, nhân vật mặc bộ đồ [03_Product_Sheet_Quan_Xanh_2K.png] và tiếp tục có hành động như video. Dùng nhạc của video gốc luôn`
- **Phân cảnh 2**:
  > `Nhân vật [continuity_char_outfit_1_quan_xanh_2K.jpg] có hành động như video , đến giây thứ 3:04 nhân vật mặc bộ đồ [04_Product_Sheet_Vay_Vang_2K.png] , đến giây 6:12 nhân vật mặc bộ đồ [06_Product_Sheet_Quan_Be_2K.png] và tiếp tục có hành động như video. Dùng nhạc của video gốc luôn`

