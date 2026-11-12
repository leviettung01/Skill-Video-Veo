# Template 005 — Nấu ăn POV bằng Storyboard 2K (Tự sinh kịch bản + Voice / ASMR)

Master prompt hiện hành: V2, đọc `MASTER_PROMPT.md`; bản prompt thực tế xuất trong `GENERATED_PROMPTS_V2.md`. Crop cận phải đạt ngay ở ảnh, màu nước/sốt và điểm tiếp xúc phải rõ; không duyệt chỉ dựa vào độ phân giải. Góc máy chọn theo thao tác. Cảnh kết giữ thành phẩm trong nồi/chảo và gắp lên gần máy.

Nguồn quy trình: `SOURCE_SOP.md` do người dùng cung cấp. Demo đã tạo trước khi đăng ký Template: lẩu Thái tôm nấm, 3 clip 8s, mỗi clip sáu shot. Video thực tế 23,808s do thời lượng clip Flow, 1080×1920, 60fps và có audio.

## Quy trình chuẩn

1. Chốt tên món ăn, 9:16, số clip (mặc định 3 clip × 8s) và chế độ âm thanh: chọn giọng đọc tiếng Việt trong Thư Viện Voice (`audio_mode="voice"`) hoặc giữ âm thanh nấu tự nhiên không lời (`audio_mode="asmr"`). Không nhân vật nhà xưởng, không chèn thumbnail bán hàng tự động.
2. Sinh đúng sáu thao tác theo trình tự nấu cho mỗi clip 8s (`cooking_recipe_ai.py` tự sinh theo kỹ thuật chế biến của từng món ăn hoặc người dùng tự chỉnh). Mỗi shot một hành động, không quay ngược trạng thái chín/sống, không trộn lẫn màu nước sốt/nguyên liệu của món khác.
3. Tạo riêng một storyboard sáu ô 2 cột × 3 hàng cho từng clip. Giữ nồi/chảo, gian bếp, bàn tay, dụng cụ và ánh sáng. Storyboard kế tiếp dùng storyboard trước làm tham chiếu nhận diện, không sao chép lại hành động cũ.
4. Tải 2K thật bằng `SPrCad`. Phải xác minh kích thước tối thiểu 1500×2600; không dùng resize cục bộ làm bằng chứng 2K. Upload lại ảnh 2K bằng `maseQ` vào đúng dự án Flow của tài khoản đang chọn, lưu hash `sha256` và `uploaded_2k_uuid`.
5. Ở chế độ tự động (`stage="auto"`), ngay sau khi đủ Storyboard 2K gốc đã re-upload, hệ thống chuyển thẳng sang tạo video 8s; ở chế độ kiểm duyệt từng bước (`stage="storyboards"` → `stage="video"`), người dùng xem ảnh 2K và tích xác nhận trước khi gửi job video.
6. Mỗi clip dùng đúng `uploaded_2k_uuid` của storyboard tương ứng và chỉ một ảnh ref. Không dùng ảnh sản phẩm. Gắn `voice_id` tương ứng với tài khoản khi chọn `audio_mode=voice`. Câu lệnh video nói rõ storyboard chỉ là bản đồ hành động, tuyệt đối không hiển thị lưới, kể cả frame đầu.
7. Nhịp shot: 0–1,3; 1,3–2,6; 2,6–3,9; 3,9–5,2; 5,2–6,5; 6,5–8s. Cận cảnh hành động, hard cut, SFX đúng thao tác.
8. Upscale từng clip lên 1080p, ghép 60fps giữ nguyên đồng bộ âm thanh (và tùy chọn đốt phụ đề tiếng Việt sạch sẽ ở hậu kỳ nếu người dùng tích chọn). Không tự gửi lại mọi clip khi chỉ một clip lỗi.

## Cách dùng trên tool

- **Chạy 1-Click ra thẳng Video Final (Khuyên dùng):** Bấm nút **🍲 Nấu Ăn POV** trên thanh điều hướng (hoặc **Chợ Template → Dùng Template #005**) → **gõ tên món ăn** → **chọn giọng đọc trong danh sách Thư Viện Voice** (có nút **🔊 Nghe thử**, hoặc chọn *Chỉ ASMR*) → **chọn tài khoản Google Flow trong danh sách sẵn có** → bấm **🚀 Tạo Video Final Luôn**.
- **Chạy kiểm duyệt từng bước (Tiết kiệm credit):** Mở mục *🛠️ Tùy chỉnh sâu kịch bản / Chạy kiểm duyệt từng bước* → **1. Lưu dự án** → **2. Chỉ tạo Storyboard 2K & upload lại** → xem/tải ảnh 2K → tích xác nhận → **3. Tạo Video 8s & Ghép Final**.

Nút **▶️ Xem Demo V2** chỉ đọc ảnh/video đã có, không gửi job hoặc trừ thêm credit.

## Cách dùng bằng Agent/CLI

Không dùng `product_crawler_bridge.py` cho món ăn/công thức.

```powershell
# Cách 1: Tự sinh kịch bản từ tên món + chọn giọng đọc + chạy thẳng ra Video Final 1080p 60FPS
python flow_final_pipeline/scripts/cooking_storyboard_engine.py --dish "Sườn xào chua ngọt" --voice voice_nu_nam_am_thuc --profile leviettung04 --stage auto

# Cách 2: Chạy tách bước để xem và duyệt Storyboard 2K trước khi gửi job video
python flow_final_pipeline/scripts/cooking_storyboard_engine.py cooking_my_recipe --stage prepare --dish "Thịt kho tàu trứng cút" --voice voice_nu_bac_food_genz
python flow_final_pipeline/scripts/cooking_storyboard_engine.py cooking_my_recipe --stage storyboards --profile <profile>
# Xem và xác minh các storyboard 2K trước bước tiếp theo:
python flow_final_pipeline/scripts/cooking_storyboard_engine.py cooking_my_recipe --stage video --profile <profile>
```

`cooking_recipe.json`: `dish`, `dish_en`, `clips` (1–6 clip); mỗi clip có `title`, `start_state`, `actions` đúng sáu chuỗi (và `voiceover` gồm 3 câu tiếng Việt khi `audio_mode="voice"`). Xem `recipe_demo.json` làm mẫu. Dùng project ID mới nếu thay công thức. Khi mất mạng, giữ UUID và tiếp tục job đã gửi; không xóa UUID để retry tự động.

## Giới hạn chất lượng

Video model có thể đơn giản hóa thao tác, đổi nhẹ dụng cụ hoặc rút ngắn vài frame. Kiểm tra video thực tế, không suy luận chất lượng từ thông báo thành công. Nếu model trộn ô/lộ lưới, dùng phương án dự phòng tạo từng shot riêng; chỉ làm sau khi cân nhắc credit, không tự nhân lên 18 job.

## Phiên bản có voice — đạo diễn và biên tập

Hai lựa chọn: `audio_mode: asmr` giữ bản không lời; `audio_mode: voice` dùng `voice_id` chọn từ Thư Viện Giọng Đọc và `voiceover` gồm ba câu tiếng Việt cho từng clip. Không thêm gương mặt hay người dẫn lên hình. Chọn cùng một giọng cho cả video; không dùng lời chào bán, giá hay CTA giỏ hàng khi làm công thức.

### Kịch bản trước, prompt sau

Chốt công thức, thứ tự nấu và trạng thái kết thúc. Không bịa nhiệt độ, thời gian nấu hoặc tác dụng sức khỏe. Mở bằng một lợi ích cảm quan cụ thể đi cùng thao tác thật; phần giữa giải thích bước quan trọng; kết bằng thành phẩm và mẹo thưởng thức phù hợp. Lời dẫn không đọc tên mọi nguyên liệu như danh sách và không lặp hook ở mỗi clip.

Mỗi clip 8s vẫn có sáu shot. Gom lời dẫn thành ba nhịp: 0–2,6s ứng với shot 1–2; 2,6–5,2s ứng với shot 3–4; 5,2–7,7s ứng với shot 5–6. Mỗi nhịp ưu tiên 6–10 từ tiếng Việt (tối đa 15 từ theo bộ tách khoảng trắng của engine); viết số và đơn vị thành chữ. Chừa đuôi câu, không tăng tốc ép lời.

Trong recipe: `audio_mode="voice"`, `voice_id="<giọng đã chọn>"`; mỗi clip thêm `voiceover=["câu nhịp một", "câu nhịp hai", "câu nhịp ba"]`. Engine xuất VISUAL timeline sáu shot và VOICEOVER timeline ba nhịp với lời tiếng Việt trong dấu nháy, hướng dẫn máy bằng tiếng Anh. ASMR làm nền nhỏ dưới giọng; không nhạc và không sinh chữ AI trong video (nếu cần phụ đề sẽ đốt bằng FFmpeg/libass sạch sẽ ở bước hậu kỳ).
