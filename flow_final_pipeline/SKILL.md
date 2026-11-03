---
name: flow-final-pipeline
version: 1.0.0
description: Quy trình full luồng Google Flow ra video final: viết kịch bản bán hàng theo công thức kho mẫu (hook + thang giá), tạo ảnh tham chiếu 1 ảnh duy nhất, tạo các cảnh 10s từ ảnh đó với voice timeline, nối final + subtitle 1 dòng karaoke + ảnh bao bì cuối. Mỗi sản phẩm 4 final (mỗi nhân vật 2 video: V1 hook A, V2 hook C).
language: vi-VN
---

# FLOW FINAL PIPELINE — Kịch bản + Prompt + Render Final

Quy trình khép kín từ thông tin sản phẩm đến video final 30s, không bước thừa.

## Tổng quan 4 bước

| Bước | Việc | File chi tiết |
|------|------|---------------|
| B1 | Viết kịch bản 2 phiên bản (V1 hook A, V2 hook C), mỗi bản 3 cảnh × 10s | `KICH_BAN.md` |
| B2 | Tạo 1 ảnh tham chiếu duy nhất (Nano Banana): nhân vật cầm sản phẩm trong bối cảnh ngành hàng | `PROMPT_TEMPLATES.md` |
| B3 | Tạo từng cảnh 10s từ đúng 1 chip ảnh tham chiếu + chip voice, prompt "Animate this reference photo..." + voice TIMELINE | `PROMPT_TEMPLATES.md` |
| B4 | Nối cảnh + subtitle 1 dòng karaoke + 3 ảnh bao bì cuối → final 30s | `RENDER.md` + `scripts/build_final.py` |

## Luật cứng (không phá vỡ)

1. **Không bịa thông tin**: tên, giá, tính năng, quà tặng chỉ lấy từ dữ liệu sản phẩm đã xác minh (PDP/shop/ảnh user gửi). Không suy diễn bao bì từ khối lượng.
2. **Luật giá**: KHÔNG bao giờ khẳng định giá cố định ("giá là…", "chỉ…K", "giảm còn…K"). Luôn dùng thang "Giá không phải là [X] đâu, không phải là [Y]… [Z]K cũng không luôn" rồi chốt "mỗi tài khoản một giá".
3. **Đếm từ trước khi gửi prompt**: mỗi cảnh 44–48 từ nói (giọng nhanh ~4,7 từ/giây) hoặc 28–32 từ (giọng thường ~3 từ/giây). Số đọc thành chữ khi đếm: 89K = 4 từ (tám mươi chín nghìn), 200 = 2 từ (hai trăm), 10kg = 4 từ (mười ki lô gam). Cảnh quá dài → voice bị cắt/rối. ĐÃ TỪNG SAI: gửi cảnh 61 từ/10s.
4. **Chip @ thật**: gõ @ → chờ hộp chọn → chọn đúng ảnh → "Thêm vào câu lệnh" → kiểm tra chip hiện hình thu nhỏ kèm tên thật. Chữ "@..." gõ tay không phải chip. Dán chữ prompt TRƯỚC, gắn chip SAU.
5. **Đã gọi @ thì không mô tả lại bằng chữ**: sau chip chỉ viết "use this reference, keep exactly as shown, do not change it in any way". Mô tả bằng chữ sẽ thắng ảnh tham chiếu.
6. **Không chữ "TikTok" trong prompt**; negative luôn có: no watermark, no logo, no username, no on-screen text, no music.
7. **Chế độ full luồng**: không kiểm tra trùng voice, không tự ý xóa clip vào thùng rác — cứ tạo ra video final là được.

## Cấu hình video

- Model: Omni 1.1 Flash (Omni Flash), ingredients-to-video, dọc 9:16, 720p, 10 giây, x1.
- Ảnh tham chiếu: Nano Banana, 9:16.
- Mỗi nhân vật 1 dự án Flow riêng; gọi nhân vật bằng @ trực tiếp, không upload ảnh nhân vật.

## Đầu vào mỗi sản phẩm

- Ảnh sản phẩm (2–6 ảnh rõ nét, có bao bì, nhiều góc) + tên + giá + tính năng chính từ nguồn xác minh.
- Nếu công cụ lấy thông tin TikTok lỗi → xin user gửi ảnh + tên, không bịa.

## Đầu ra mỗi sản phẩm

4 file final 30s: `{id}-nv1-v1-final-30s.mp4`, `{id}-nv1-v2-final-30s.mp4`, `{id}-nv2-v1-final-30s.mp4`, `{id}-nv2-v2-final-30s.mp4` — mỗi file: 720×1280, nối 3 cảnh, subtitle 1 dòng karaoke, 3 ảnh bao bì gốc nối tiếp 7s cuối góc trên trái.
