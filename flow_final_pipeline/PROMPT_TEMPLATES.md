# CẤU TRÚC PROMPT — Ảnh tham chiếu + Cảnh video

## B2. Prompt ảnh tham chiếu (Nano Banana 2.1, 9:16)

Gắn đúng **1 chip nhân vật** + **1 chip ảnh sản phẩm đơn chiếc (phân loại đầu tiên, tuyệt đối không chọn ảnh ghép nhiều mẫu)**.
- **Nguyên tắc vàng**:
  1. Chỉ mô tả: **Nhân vật + Trang phục + Bối cảnh + Hành động cầm sản phẩm + Biểu cảm + Chi tiết xung quanh**.
  2. **KHÔNG mô tả lại màu sắc hay chi tiết thiết kế của sản phẩm bằng chữ** — chỉ yêu cầu lấy nguyên sản phẩm từ ảnh tham chiếu (`holding and presenting the exact product from the product reference image, keep the product 100% identical as shown in the reference, do not redesign or change it in any way`).
  3. **KHÔNG viết `"no logo"` hay `"no text"`** để tránh AI tự ý xóa mất logo/hoạ tiết in trên chính sản phẩm.

```
Photorealistic vertical 9:16 medium-wide standing photo (framed from head to hips, camera at 2 meters distance): the exact same woman from the character reference ([đặc điểm tóc, kính/không kính], identical face), wearing [trang phục lịch sự theo bối cảnh], standing behind a worktable in [bối cảnh xưởng/phòng QC/kho/showroom + chi tiết xung quanh, công nhân phía sau]. She looks at the camera with a warm, friendly smile while holding and presenting the exact [tên loại sản phẩm ngắn gọn] from the product reference image in her hands at waist level facing the camera. Keep the product exactly as shown in the product reference image (true-to-life hand-held scale relative to her hands and body, NOT oversized, do not redesign or alter the product in any way), keep her face identical.
```

**Bối cảnh + trang phục do AI thiết kế theo ngành hàng & Đa Phong Cách (Multi-Style)**, không dùng 1 bối cảnh cứng nhắc:
- **Style 1 — Xưởng Sản Xuất Tận Gốc (`Factory / Craft Workshop`)**:
  - Bối cảnh: Xưởng lắp ráp / xưởng chế tác (`assembly factory / craft workshop with workers behind, display table in front`).
  - Trang phục: Áo vest xanh navy + sơ mi xanh nhạt + quần âu đen (`navy blazer + light blue shirt + black trousers`).
  - Phù hợp: Nhấn mạnh "xả kho tận xưởng", "giá gốc nhà máy".
- **Style 2 — Cửa Hàng Quà Tặng Cao Cấp (`Luxury Boutique / High-End Gift Store`)**:
  - Bối cảnh: Showroom / cửa hàng quà tặng sang trọng (`high-end luxury menswear and gift boutique with warm golden lighting, marble-and-glass display counters, illuminated wooden shelves with luxury gift boxes blurred behind`).
  - Trang phục: Áo blazer trắng/kem thanh lịch khoác ngoài áo lụa + quần âu đen (`elegant white tailored blazer over a silk blouse and black trousers`).
  - Cách cầm sản phẩm: Hai tay nâng hộp quà tặng cao cấp mở nắp lót nhung trắng (`open dark navy luxury gift box lined with white velvet`) hướng về camera, thấy rõ trọn bộ sản phẩm bên trong (ví dụ: **Bộ quà tặng Thắt lưng da khóa tự động bên trái + Đồng hồ nam mạ vàng bên phải**).
- **Style 3 — Kết Hợp Cận Cảnh B-Roll + Nhân Vật Giới Thiệu (`Macro B-Roll + Presenter Cutaway`)**:
  - Đoạn mở đầu `[0.0-3.5s]` mở bằng góc cận cảnh (close-up beauty view) làm nổi bật chi tiết bộ sản phẩm (mặt khóa xoay, vân da, mặt đồng hồ mạ vàng), sau đó `[3.5-10.0s]` kéo máy mượt mà (hoặc chuyển cảnh) về góc trung cảnh đứng (medium standing shot) của nhân vật đang cầm hộp quà / thao tác thử sản phẩm trên tay.

**Quy tắc bắt buộc với Sản phẩm Combo / Bộ Quà Tặng (Mua 1 Tặng 1)**:
- Trước khi tạo ảnh tham chiếu, PHẢI kiểm tra kỹ ảnh đầu tiên của sản phẩm (`prod_1.jpg`). Nếu sản phẩm là **Bộ quà tặng / Mua 1 Tặng 1** (ví dụ: Thắt lưng tặng kèm Đồng hồ, Bếp hồng ngoại tặng kèm Vỉ nướng), bắt buộc đưa đầy đủ cả sản phẩm chính lẫn quà tặng (đặt trong hộp quà sang trọng hoặc đặt cạnh nhau) vào cả **Prompt Ảnh Tham Chiếu (B2)** và **Prompt Cảnh Video (B3)**, tuyệt đối không bỏ sót món quà tặng kèm.

**Tỉ lệ sản phẩm/cơ thể & Khung hình đứng**:
- Luôn dùng khung hình **Medium-wide standing shot** (thấy từ đầu qua hông đứng sau bàn trưng bày hoặc nâng hộp quà trước ngực/eo, tuyệt đối không zoom cận mặt).
- Sản phẩm phải đúng kích thước thật so với tay người (`Keep the product at realistic true-to-life size relative to her hands and body`).

## B3. Prompt cảnh video (Omni 1.1 Flash, ingredients-to-video, 9:16, 10s, Upscale 1080p)

Mỗi cảnh gắn đủ **2 chip ảnh tham chiếu** (`ref_list = [[None, ref_image_uuid], [None, prod_image_uuid]]` — gồm cả **Ảnh Ref Nhân vật cầm sản phẩm 2K** và **Ảnh Sản phẩm mẫu đơn chiếc**) + **1 chip giọng nói tuỳ chỉnh** (`[[voice_id]]`).
Tuyệt đối **KHÔNG mô tả lại trang phục, bối cảnh hay chi tiết thiết kế sản phẩm bằng chữ** trong prompt video để tránh AI tự vẽ lại làm sai lệch sản phẩm:

```
A 10-second vertical 9:16 video starting directly from the provided reference image, one continuous medium shot, front-facing camera. Keep the character, the exact product in her hands, the items on the table, and the background 100% unchanged from the reference image — do not alter, redesign, or replace the product's shape, color, pattern, or logo.

ACTION: The woman looks directly at the camera with a confident, energetic expression, naturally speaking while holding the exact product from the reference image steady at waist level, tilting it slightly toward the camera to showcase it, then keeping the presenting pose at the end.

VOICE — read the dialogue in 3 timed segments exactly as marked. Keep a steady, even pace so each segment fills its time window. Finish the last word exactly at 10.0 seconds. Read each word exactly once — no repetition, no looping, no added words, then stay silent:
[0.0-X.Xs] "[thoại đoạn 1 nguyên văn]"
[X.X-Y.Ys] "[thoại đoạn 2 nguyên văn]"
[Y.Y-10.0s] "[thoại đoạn 3 nguyên văn]"

No background music, no watermark.
Negative: changed product, altered product design, repeating voice, looping dialogue, second voice pass, rushed reading, changed face
```

**Chỉ nhấn mạnh giá** ("emphasize the price") khi cảnh đó thực sự có giá trong thoại — nếu không, model tự bịa giá.

## Quy tắc chip @ (bắt buộc)

1. Gõ @ → chờ hộp lựa chọn → gõ đúng tên ảnh → chọn đúng ảnh → "Thêm vào câu lệnh".
2. Kiểm tra chip hiện thành hình thu nhỏ kèm tên thật mới được gửi.
3. Chữ "@..." gõ tay KHÔNG phải chip — clip nào chỉ có chữ @ thì xóa làm lại.
4. Không gắn tất cả chip lên đầu prompt: đến dòng Character mới gọi chip nhân vật, đến dòng Product mới gọi chip sản phẩm.
5. Không cần tải ảnh về máy — kéo thả trực tiếp vào khung prompt được.

## Kiểm tra trước khi gửi mỗi cảnh

- [ ] Tên model đúng Omni 1.1 Flash, 9:16, 720p, 10s, x1
- [ ] Tổng từ thoại trong 44–48 (giọng nhanh) / 28–32 (giọng thường) — ĐÃ ĐẾM
- [ ] Timeline 3 mốc tỉ lệ theo số từ, từ cuối rơi đúng 10.0s
- [ ] Chip @ là chip thật (hình thu nhỏ), không phải chữ gõ tay
- [ ] Không có chữ "TikTok", không mô tả lại sản phẩm bằng chữ sau chip


---

## 4. TEMPLATE #004: MOTION CONTROL VIDEO FASHION (OMNI FLASH THAY ĐỒ THEO NHẠC & VIDEO THAM CHIẾU)

### 4.1. Nguyên Tắc Cốt Lõi
- **Đầu vào chuẩn 2K**:
  1. **Ảnh Nhân Vật Gốc 2K (`07_Nhan_Vat_Basic_Phong_Ngu_2K.png` — `1536x2752` / `2048x3639`)**: Nhân vật đứng trong bối cảnh phòng ngủ/studio cố định, gương mặt rõ nét từng lỗ chân lông chuẩn 2K.
  2. **Bảng Nhân Vật 2K (`01_Character_Sheet_4_Outfits_2K.png`)**: Khóa tỷ lệ cơ thể 3 vòng và form dáng khi mặc các bộ đồ.
  3. **Video Tham Chiếu Chuyển Động & Nhạc (`reference_motion_source.mp4`)**: Video mẫu chứa động tác nhảy/tạo dáng và nhạc nền.
  4. **Bộ Sưu Tập Trang Phục 2K (`03_Product_Sheet_Quan_Xanh_2K.png`, `04_Product_Sheet_Vay_Vang_2K.png`, `06_Product_Sheet_Quan_Be_2K.png`)**.
- **Chia cắt thời lượng tự động cho Omni Flash (`6s`, `8s`, `10s`)**:
  - Vì chỉ có model **Omni 1.1 Flash (`abra_edit` / `jIps6`)** mới hỗ trợ đính kèm Video Tham Chiếu, tool tự động phân tích độ dài video gốc để chia khít cho **8s** hoặc **10s** (VD: `16.28s -> 2 phân cảnh × 8s = 16s`; `20s -> 2 phân cảnh × 10s = 20s`).
  - Tự động cắt rời video tham chiếu thành từng file phân cảnh (`ref_clip_s1_8s.mp4`, `ref_clip_s2_8s.mp4`) và tách nhạc gốc (`ref_master_audio.m4a`).
- **Tạo Ảnh Ref Nhân Vật 2K Nối Tiếp Giữa Các Phân Cảnh (Continuity 2K Character Ref)**:
  - Để Phân cảnh 2 bắt đầu mượt mà không bị nhảy trang phục ở giây `8.00s`, tool dùng `Ảnh Nhân Vật Gốc 2K + Ảnh Bộ Đồ 1 2K` tạo ra **Ảnh Ref Nhân Vật 2K đang mặc Bộ Đồ 1 trong đúng phòng ngủ đó** làm ảnh mở đầu Phân cảnh 2.

### 4.2. Mẫu Timeline Prompt Kèm Inline Asset Chips (Đã Tối Ưu Theo Video Mẫu 16s)
- **Phân Cảnh 1 (`0.00s - 8.00s` | Đổi Bộ Đồ 1 tại giây `4:04`)**:
  > `Bắt đầu video với ảnh 1 [07_Nhan_Vat_Basic_Phong_Ngu_2K.png] , nhân vật có hành động, thần thái biểu cảm và nhịp chuyển động cơ thể giống hệt như video tham chiếu, giữ nguyên 100% bối cảnh căn phòng và ánh sáng tự nhiên của ảnh 1. TIMELINE THEO NHẠC: [0:00 - 4:04] Nhân vật mặc bộ đồ như ảnh mở đầu và thực hiện đúng động tác theo video gốc. Tại giây 4:04 (đúng nhịp beat chuyển cảnh), nhân vật lập tức mặc bộ đồ [03_Product_Sheet_Quan_Xanh_2K.png] (áo yếm vàng vạt xòe peplum kèm vòng cổ hoa đỏ, quần dài ống suông rộng màu xanh coban đậm, túi xách vàng và giày sneaker vàng) chuẩn tỷ lệ cơ thể và form trang phục như bảng tham chiếu [01_Character_Sheet_4_Outfits_2K.png] và từ [4:04 - 8:00] tiếp tục có hành động tạo dáng thời trang mượt mà như video gốc. Giữ gương mặt nhân vật sắc nét chuẩn 2K, không biến dạng tay hay trang phục. Dùng nhạc của video gốc luôn.`

- **Phân Cảnh 2 (`8.00s - 16.00s` | Clip 2 `0.00s - 8.00s` | Đổi Bộ Đồ 2 tại `3:04` & Bộ Đồ 3 tại `6:12`)**:
  > `Nhân vật [continuity_char_outfit_1_quan_xanh_2K.jpg] có hành động, biểu cảm và nhịp nhún nhảy theo nhạc giống hệt như video tham chiếu, giữ nguyên 100% bối cảnh căn phòng của ảnh mở đầu. TIMELINE THEO NHẠC: [0:00 - 3:04] Nhân vật mặc bộ đồ như ảnh mở đầu và thực hiện đúng động tác theo video gốc. Tại giây 3:04 (đúng nhịp beat chuyển cảnh), nhân vật lập tức mặc bộ đồ [04_Product_Sheet_Vay_Vang_2K.png] (váy ngắn cổ yếm xếp tầng phồng màu vàng bơ, dây buộc tóc scrunchie vàng, túi kẹp nách quai nhún bèo vàng, tất trắng và giày búp bê vàng), tiếp tục tạo dáng từ [3:04 - 6:12]. Đến giây 6:12 (nhịp beat chuyển cảnh tiếp theo), nhân vật lập tức mặc bộ đồ [06_Product_Sheet_Quan_Be_2K.png] (áo yếm vàng vạt xòe, quần tây ống rộng xếp ly màu be kem, mắt kính gọng hồng pastel, vòng tay vàng và giày búp bê vàng) chuẩn tỷ lệ cơ thể và form trang phục như bảng tham chiếu [01_Character_Sheet_4_Outfits_2K.png] và từ [6:12 - 8:00] tiếp tục có hành động tạo dáng thời trang mượt mà như video gốc. Giữ gương mặt nhân vật sắc nét chuẩn 2K, không biến dạng tay hay trang phục. Dùng nhạc của video gốc luôn.`
