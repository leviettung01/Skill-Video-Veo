# Template 006 — Biến hình thời trang (Làm nông / Bán cá)

**Đầu vào:**
1. **Nhân vật tham chiếu** (từ Thư viện nhân vật NV1–NV5 hoặc tải ảnh khuôn mặt / Character Sheet từ máy) để khoá đồng nhất khuôn mặt và sắc da qua cả 2 cảnh.
2. **Ảnh quần áo cần biến hình** (từ kho sản phẩm hoặc tải từ máy).

**Cấu trúc ảnh 2K:**
1. `product_2k.jpg`: Tách bộ trang phục lên nền trắng tinh (`#FFFFFF`), bảo toàn chuẩn phom dáng, cổ áo, tay áo, tà váy và hoạ tiết.
2. `before_2k.jpg`: Nhân vật mặc trang phục lao động đúng bối cảnh (cầm cuốc ngoài vườn rau / đeo găng hồng đứng quầy cá), tay và đạo cụ thấy rõ. Nếu ảnh nhân vật gốc là Character Sheet nhiều ô, trích xuất duy nhất khuôn mặt và sinh MỘT khung 9:16 liền mạch.
3. `reveal_2k.jpg`: Giữ đúng khuôn mặt nhân vật tham chiếu và tỉ lệ cơ thể từ `before_2k.jpg`, khoác chính xác bộ đồ trong `product_2k.jpg` tại bối cảnh lột xác (trước cửa biệt thự nắng ấm / bên xế hộp đen buổi tối).

**Timeline Video & Kỹ thuật chuyển cảnh (9:16 · 30 FPS · 16s · Tốc độ thật 1.0x):**
- **Cảnh 1 (0–8s · Tốc độ 1.0x, phân rõ ai nói / ai im lặng + Vật che tiến sát kín 100% camera):**
  - **Làm nông (`01_lam_nong.mp4`):**
    - `0.0s–2.0s`: Cúi người vung cuốc cuốc đất thật sự ngoài vườn rau tốc độ 1.0x, giữ im lặng.
    - `2.0s–4.9s`: Dừng cuốc, tựa tay lên cán gỗ, gạt mồ hôi trán bằng cẳng tay và ngước nhìn điềm tĩnh vào ống kính (không thoại).
    - `4.9s–7.0s`: Hai tay nâng lưỡi cuốc dính đất tiến sát lại gần ống kính.
  - **Bán cá (`02_ban_ca.mp4` — khớp 100% timing cut & lời thoại):**
    - `0.0s–3.0s`: Cả nhân vật im lặng. Góc cao chợ cá: nhân vật chính (`Reference 1`) ngồi xổm đánh vảy cá tốc độ thật (`0–1.8s`); khoảng `1.8s–3.0s` đôi nam nữ cũ áo đen bước tới đứng cạnh sạp cầm thiệp cưới, giữ khung tới `3.0s` mới cắt cảnh.
    - `3.0s–5.4s`: Cắt góc cận trung qua vai nhân vật chính nhìn thẳng đôi nam nữ cũ (sau gáy nữ bán cá ở tiền cảnh trái): **CHỈ nam người yêu cũ** cười nửa miệng khinh khỉnh, chìa thiệp cưới và nói rõ tiếng Việt trọn trong `3.2s–5.3s`: *"Tháng sau bọn anh cưới, rảnh thì qua chung vui nhé."* Bạn gái mới đứng bên khoanh tay im lặng.
    - `5.4s–7.0s`: Cắt cận mặt nhân vật chính (`Reference 1`) mắt ngấn lệ rưng rưng nhìn ngược lên (âm thanh demo nói nốt *"Nhớ rửa tay cho sạch mùi cá."*). **Nhân vật chính TUYỆT ĐỐI im lặng mím môi run nhẹ, không mở miệng**, từ `6.8s` bắt đầu lao bàn tay găng hồng ướt thẳng về phía ống kính.
  - `7.0s–8.0s`: Bàn tay găng hồng áp **thẳng sát lên mặt kính ống kính** (không khựng giữa không trung), phóng đại macro out-of-focus phủ **kín 100% cả 4 cạnh màn hình** tới tối đen `7.78s–8.0s`. Hậu kỳ `_detect_fish_scene_cuts` cũng tự động đo 2 điểm cắt `(c1, c2)` và căn khớp với `02_ban_ca.mp4` để tránh lệch cảnh-thoại.
- **Cảnh 2 (8–16s · Biến hình VIP ngầu, lịch thiệp, quý phái — Steadicam lùi mượt 1.0x, đúng tỷ lệ xe thật & không xuyên xe):**
  - **Làm nông:** Bước dứt khoát từ cửa gỗ gụ biệt thự nắng ấm xuống thềm đá hoa cương, sải bước catwalk quý phái với nụ cười quyền lực, đầu–cổ–vai đồng nhất, giữ nguyên 100% đồ trong `product_2k.jpg`.
  - **Bán cá:** Xe sedan hạng sang cỡ lớn tỷ lệ thật (~5.4m dài, nóc xe ngang tầm mắt/cằm người đứng cạnh, bánh lớn đặt phẳng trên làn đường lái xe, KHÔNG thu nhỏ đồ chơi và KHÔNG đặt trên bậc thang) đỗ bên cạnh hành lang đá hoa cương phẳng rộng; cửa sau mở về phía lề đường, vệ sĩ giữ tay nắm cửa. Nhân vật đứng trước lối đi thoáng cách rõ thân xe (~58%–62% khung hình trong `reveal_2k.jpg`) rồi **sải bước thẳng về phía trước rời xa chiếc xe** (`0.0s–2.2s`), **4 vệ sĩ tiến từ 2 cột sảnh hai bên ngoài vào đội hình chữ V sau lưng** (`2.2s–4.8s` — **cấm xuyên thân xe/nắp capo**), Steadicam lùi mượt với flash phóng viên (`4.8s–8.0s`). Chất lượng 8K cinema film, no text/subtitles/logos/watermark.

**Âm thanh đồng bộ theo video demo (`demo_videos`):**
- **Làm nông (`01_lam_nong.mp4`):** 0–2.6s tiếng lao động đồng quê & nền trầm nhẹ → 2.6s vào verse → **điệp khúc bùng nổ (5.40s bản demo) rơi chuẩn tại giây `8.00s`**, kéo mượt tới `16.0s`.
- **Bán cá (`02_ban_ca.mp4`):** giữ nguyên nhịp âm thanh gốc từ video demo `0.00s–16.00s`: `0.00–2.8s` tiếng dao đánh vảy cá & chợ sáng → `2.8–7.8s` **trọn vẹn lời thoại nam gốc** (*"Tháng sau bọn anh cưới, rảnh thì qua chung vui nhé. Nhớ rửa tay cho sạch mùi cá."*) → **giây `7.80s–8.00s` bùng nổ đúng drop nhạc** (*"Vốn phận mình thân nữ nhi..."*) khớp trọn 8 giây bước xuống xế hộp lột xác.
