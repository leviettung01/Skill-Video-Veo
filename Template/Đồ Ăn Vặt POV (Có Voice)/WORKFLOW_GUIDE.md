# QUY TRÌNH TEMPLATE: ĐỒ ĂN VẶT POV (CÓ VOICE REVIEW • TIMELINE SYNC • 60 FPS)

## 1. Điểm Nổi Bật
- **Góc quay POV trực diện mặt bàn/quầy (`character_id = ""`)**: Không cần nhân vật nhà xưởng đứng thuyết trình; tập trung 100% vào sản phẩm thật và bàn tay tương tác tự nhiên.
- **Kịch bản Voice Review chọn từ danh sách Voice (`voice_id`)**: Chọn giọng đọc từ `voices_and_characters.json` (`nv1`, `nv2`, hoặc giọng tùy chỉnh).
- **Kiểm soát câu từ chuẩn Policy TikTok Shop**: Có Hook 3s đầu cuốn hút, tập trung miêu tả hương vị thơm ngon, độ giòn/dẻo, quy cách đóng gói và ưu đãi giỏ hàng mà tuyệt đối không dính từ cấm (không cam kết 100%, không nói quá, không tuyên bố y tế/giảm cân).
- **Đồng bộ Timeline kép (`[0.0-3.5s]`, `[3.5-7.0s]`, `[7.0-10.0s]`)**: Cả chuyển động Hình ảnh/Camera (`VISUAL & CAMERA TIMELINE`) và Lời thoại (`VOICEOVER TIMELINE`) đều chia theo 3 mốc thời gian khớp nhau hoàn toàn.
- **Kế thừa phân cảnh (Scene Inheritance) & Khóa sản phẩm tuyệt đối (Strict Product Lock)**:
  - Cảnh 1 (0–10s) -> Cảnh 2 (10–20s, kế thừa cuối Cảnh 1, push-in cận cảnh) -> Cảnh 3 (20–30s, kế thừa cuối Cảnh 2, pull-back Hero & chỉ nhẹ về giỏ hàng góc trái).
  - Giữ nguyên 100% ngoại quan sản phẩm như ảnh tham chiếu (`prod_1.jpg`), không tự ý xé bao bì hay tự bịa nhân bên trong.
- **Random 8 Background Đồ Ăn Vặt**: Tự động random ngẫu nhiên 1 trong 8 bối cảnh từ `role_skills/DoAnVat.MD` cho mỗi video và khóa cố định xuyên suốt 3 cảnh của video đó.
- **Render Final 60 FPS + Karaoke Subtitles**: Mọi video xuất ra đều đạt **1080p 60 FPS** kèm phụ đề Karaoke (`ass`) và khung ảnh sản phẩm góc trên bên trái.

