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
