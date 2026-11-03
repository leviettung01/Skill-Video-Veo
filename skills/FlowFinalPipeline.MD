# FLOW FINAL PIPELINE — Kịch bản + Đa Phong Cách (Multi-Style) + Render Final 30s

Quy trình khép kín từ thông tin sản phẩm đến video final 30s trên Google Flow (Nano Banana 2.1 + Omni Flash 10s + Custom Voice + Karaoke Subtitle + Overlay 7s cuối).

## 1. Hệ thống Đa Phong Cách Video (Multi-Style System)

Tùy theo tính chất sản phẩm hoặc yêu cầu chiến dịch, có thể xuất nhiều phiên bản phong cách (Style) trên cùng một kịch bản Voice:

### Style 1 — Phong cách Xưởng Sản Xuất Tận Gốc (`Factory / Craft Workshop`)
- **Bối cảnh**: Xưởng lắp ráp / xưởng chế tác (`assembly factory / craft workshop with workers behind, display table in front`).
- **Trang phục**: Áo vest xanh navy + sơ mi xanh nhạt + quần âu đen (`navy blazer + light blue shirt + black trousers`).
- **Góc máy**: Trung cảnh đứng (`medium-wide standing shot`) sau bàn trưng bày.

### Style 2 — Phong cách Luxury Cửa Hàng Quà Tặng Cao Cấp (`Luxury Gift Boutique`)
- **Bối cảnh**: Nhà hàng / Cửa hàng quà tặng & thời trang cao cấp (`high-end luxury menswear and gift boutique with warm golden lighting, marble counters, glass display shelves, and luxury gift boxes with gold ribbons blurred behind`).
- **Trang phục**: Áo blazer trắng/kem thanh lịch khoác ngoài áo lụa + quần âu đen (`elegant white tailored blazer over a silk blouse and black trousers`).
- **Hình ảnh sản phẩm**: Nhân vật hai tay nâng **hộp quà tặng cao cấp mở nắp lót nhung trắng (`open dark navy luxury gift box lined with white velvet`)** hướng về phía camera, trưng bày trọn bộ sản phẩm bên trong (ví dụ: **Bộ quà tặng Mua 1 Tặng 1: Thắt lưng da đen khóa tự động bên ngăn trái + Đồng hồ nam mạ vàng bên ngăn phải**).

### Style 3 — Kết Hợp Cận Cảnh B-Roll + Nhân Vật Giới Thiệu (`Macro B-Roll + Presenter Cutaway`)
- **Cảnh 1 (`0-10s`)**: Mở đầu `[0.0-3.7s]` bằng góc cận cảnh (close-up beauty view) hộp quà tặng làm nổi bật chi tiết mặt khóa thắt lưng và mặt đồng hồ mạ vàng, sau đó `[3.7-10.0s]` kéo máy mượt mà về góc trung cảnh đứng của nhân vật đang cầm hộp quà giới thiệu.
- **Cảnh 2 (`10-20s`)**: Nhân vật cầm hộp quà mở nắp hướng về camera, chỉ tay vào từng món (thắt lưng & đồng hồ) trong `[0.0-6.0s]` rồi chỉ tay xuống giỏ hàng góc trái ở `[6.0-10.0s]`.
- **Cảnh 3 (`20-30s`)**: Nhân vật cầm hộp quà `[0.0-3.3s]`, nhấc dây thắt lưng da hạt & mặt khóa xoay đính đá lên cạnh đồng hồ mạ vàng để demo chi tiết chất liệu `[3.3-6.9s]`, kết thúc mỉm cười giữ nguyên tư thế `[6.9-10.0s]`.

---

## 2. Quy tắc bắt buộc với Sản phẩm Combo / Bộ Quà Tặng (Mua 1 Tặng 1)

- Luôn kiểm tra kỹ ảnh sản phẩm gốc (`prod_1.jpg`). Nếu sản phẩm là **Bộ quà tặng / Mua 1 Tặng 1** (ví dụ: Thắt lưng + Đồng hồ), bắt buộc đưa đầy đủ cả hai món vào **Ảnh Tham Chiếu 9:16** và **Prompt Cảnh Video 10s**, không được chỉ vẽ 1 món.
- Luôn dùng khung hình **Medium-wide standing shot** (thấy từ đầu qua hông, không zoom cận mặt) và giữ kích thước sản phẩm đúng tỉ lệ thật so với bàn tay và cơ thể nhân vật.

---

## 3. Cấu trúc Prompt Chuẩn

### A. Prompt Tạo Ảnh Tham Chiếu 9:16 (`Nano Banana 2.1` / `BELUGA`)
```text
Photorealistic vertical 9:16 photo: the exact same woman from the character reference ([mô tả tóc + kính/không kính], identical face), wearing [trang phục theo Style], standing in [bối cảnh theo Style: xưởng sản xuất / cửa hàng quà tặng cao cấp Luxury với ánh sáng vàng ấm và tủ kính trưng bày]. In her hands at chest-to-waist level, she holds [mô tả hộp quà / bộ sản phẩm đầy đủ hướng về camera]. Medium-wide standing shot showing her full upper body down to her hips (do not zoom in close-up). Keep the products at realistic true-to-life size relative to her hands and body, keep the products exactly as shown in the reference, keep her face identical. No text, no watermark, no logo.
```

### B. Prompt Tạo Cảnh Video 10s (`Omni Flash 10s` / `abra_r2v_10s` + Custom Voice)
```text
A 10-second vertical video, one continuous medium shot, front-facing camera. Setting: [bối cảnh theo Style]. A Vietnamese female sales presenter stands behind a display counter facing the camera, wearing [trang phục]. In her hands and on the counter in front of her is [mô tả bộ sản phẩm / hộp quà tặng].

The presenter is the exact same woman as the character reference: [mô tả tóc + kính/không kính], identical face. No face change, no hairstyle change.

VOICE — read the dialogue in 3 timed segments exactly as marked. Keep a steady, even pace so each segment fills its time window. Finish the last word exactly at 10.0 seconds. Read each word exactly once — no repetition, no looping, no added words, then stay silent:
[0.0-X.Xs] "[thoại đoạn 1]"
[X.X-Y.Ys] "[thoại đoạn 2]"
[Y.Y-10.0s] "[thoại đoạn 3]"

[Hướng dẫn hành động & góc máy theo từng phân đoạn]. End holding the presenting pose so the scene connects smoothly to the next scene. No background music, no on-screen text, no watermark, no logo.

Negative: repeating voice, looping dialogue, second voice pass, rushed reading, different woman, changed face
```

