# Quy trình chuẩn làm video AI nấu ăn: Storyboard → Image-to-Video

## Nguyên tắc cốt lõi

Tạo **một ảnh storyboard dạng lưới cho mỗi đoạn video**, dùng ảnh đó làm tham chiếu hành động/thứ tự, rồi viết prompt video chia shot rõ ràng. Ảnh storyboard là bản đồ chỉ dẫn cho model, **không phải bố cục cần xuất hiện trong video**. Video đầu ra cần chuyển từng panel thành shot toàn khung hình.

Để dễ kiểm soát, chọn **8 giây cho mỗi clip**, **6 shot/clip**, video dọc **9:16**. Đây là cấu hình xuất hiện trong hướng dẫn mẫu; độ dài/độ phân giải cần đổi theo giới hạn công cụ đang dùng. Ví dụ video 24 giây có thể chia thành 3 đoạn × 8 giây, mỗi đoạn có storyboard và motion prompt riêng.

## SOP từng bước

### 1. Chốt brief và định dạng

Trước khi viết prompt, xác định:

- Món ăn và người xem mục tiêu.
- Nền tảng: Reel/TikTok/Shorts thường dùng khung dọc 9:16.
- Tổng thời lượng và số clip cần tạo.
- Phong cách: cận cảnh chân thực, quảng cáo món ăn, vlog bếp, hoạt hình, v.v.
- Thành phần phải giữ đúng: bao bì gia vị/thương hiệu, loại nồi, nguyên liệu, bàn tay/nhân vật, căn bếp.
- Âm thanh: ASMR nấu ăn, nhạc, lời thoại hay video không tiếng.

Nếu cần giữ chính xác một sản phẩm hoặc nhân vật, đưa ảnh tham chiếu phù hợp vào công cụ. Không nên kỳ vọng prompt chữ giữ chính xác logo, bao bì hoặc gương mặt.

### 2. Chia công thức thành các đoạn và hành động

Viết tiến trình nấu theo đúng thứ tự vật lý: chuẩn bị → xào/nấu nền → thêm nước/sốt → sôi → cho nguyên liệu chính → hoàn thiện/trình bày. Chia thành các đoạn 8 giây; mỗi đoạn có sáu hành động rõ ràng.

Mỗi shot chỉ nên có **một hành động chính**. Tránh ghép nhiều việc trong cùng shot, ví dụ “đổ dầu, cho sả, đảo hành, rồi thêm cà chua”. Ghi trạng thái nguyên liệu giữa các shot để không bị nhảy lùi từ chín sang sống.

### 3. Tạo storyboard ảnh

Với mỗi đoạn, tạo **một ảnh storyboard** gồm sáu panel, bố cục 2 cột × 3 hàng. Mỗi panel cần thể hiện một bước trong chuỗi. Giữ cố định nồi, bếp, tay, đạo cụ, ánh sáng, màu sắc và góc nhìn chung.

Sau khi tạo, kiểm tra: đủ sáu panel; đúng thứ tự; món/nồi/đạo cụ không đổi; panel không gộp nhiều hành động; trạng thái nguyên liệu hợp lý; không có chữ giả, bàn tay lỗi hoặc nguyên liệu bị nhân đôi. Nếu storyboard sai, sửa ảnh trước khi chuyển sang video.

### 4. Viết motion prompt cho đúng storyboard

Motion prompt phải đồng bộ với đúng ảnh storyboard đang dùng. Nêu rõ:

1. Đầu ra: một clip, tỉ lệ và thời lượng.
2. Vai trò của storyboard: tham chiếu thứ tự hành động, không được hiện cả lưới trong video.
3. Quy tắc liên tục: giữ nguyên nồi, bếp, tay, ánh sáng, đạo cụ và trạng thái món.
4. Nhịp dựng: sáu shot, khoảng thời gian từng shot, hard cut hay chuyển cảnh.
5. Mỗi shot: góc/cỡ máy, hành động nhìn thấy, chi tiết cần lấy nét, trạng thái kết thúc.
6. Chuyển động và âm thanh: hơi nước, dầu chảy, tiếng xèo, tiếng khuấy, tiếng rót.
7. Điều cần tránh: tay/ngón thừa, đồ vật biến dạng, nguyên liệu tự xuất hiện, nồi/bếp đổi, chữ/phụ đề giả.

Với sáu shot trong clip 8 giây, có thể dùng nhịp gần như sau: **0.0–1.3, 1.3–2.6, 2.6–3.9, 3.9–5.2, 5.2–6.5, 6.5–8.0 giây**. Điều chỉnh theo hành động; không cần ép mọi clip có nhịp giống hệt nếu một thao tác cần thời gian dài hơn.

### 5. Tạo image-to-video

Tải storyboard của đúng đoạn lên công cụ image-to-video, dán motion prompt tương ứng và chọn thời lượng/tỉ lệ/độ phân giải phù hợp. Trong reel tham khảo, giao diện hiển thị **Google Flow, Video · 720p · 8 giây**. Đây là thiết lập nhìn thấy trong video đó, không phải mặc định bắt buộc của mọi công cụ.

Tạo từng đoạn riêng để dễ sửa. Nếu công cụ không hiểu tốt lưới sáu panel hoặc trộn các cảnh, phương án dự phòng là cắt storyboard thành từng panel riêng, tạo clip ngắn cho từng panel rồi ghép trong trình dựng.

### 6. Kiểm tra và dựng

Xem lại từng clip ở tốc độ thường. Kiểm tra thứ tự thao tác, tính liên tục, hình dạng bàn tay/đũa/nồi, thức ăn có biến dạng hoặc tự đổi trạng thái không, và âm thanh có đúng hành động không. Tạo lại riêng clip/panel lỗi thay vì làm lại toàn bộ.

Ghép các đoạn theo thứ tự, thêm nhạc/voice-over/phụ đề ở phần dựng nếu cần. Nên thêm chữ bằng trình dựng thay vì yêu cầu video model sinh chữ trong cảnh; chữ AI thường sai chính tả hoặc méo.

## Cấu trúc prompt ảnh storyboard

Dùng cấu trúc khối sau; thay phần trong ngoặc vuông:

```text
Create ONE photorealistic vertical 9:16 storyboard contact sheet with EXACTLY SIX panels arranged in 2 columns × 3 rows, in chronological order. Each panel is a separate full-frame close-up showing one cooking action only.

DISH: [tên món].
SIX ACTIONS, in order:
1. [hành động 1]
2. [hành động 2]
3. [hành động 3]
4. [hành động 4]
5. [hành động 5]
6. [hành động 6]

CONTINUITY: Use the same [loại nồi], [bếp/căn bếp], [tay/nhân vật], [đạo cụ], [ánh sáng] and color palette in all six panels. Preserve the same ingredients and their cooking state from panel to panel. [Mô tả ảnh tham chiếu cần bám sát nếu có.]

CAMERA & STYLE: [photorealistic food photography / macro close-up / góc nhìn], appetizing natural color, soft [loại ánh sáng], clean composition, clear visible action in every panel.

LAYOUT: exactly six panels, 2 columns × 3 rows, thin clean dividers, consistent panel size. No other panels or collage layout.

AVOID: text, captions, labels, logos, watermarks, duplicated ingredients, extra fingers, malformed hands or utensils, changing pot/kitchen, inconsistent food state.
```

## Cấu trúc prompt video image-to-video

Dùng ảnh storyboard cùng đoạn prompt này. Thay hành động, góc máy, đạo cụ và âm thanh để khớp ảnh:

```text
Create ONE [8]-second vertical 9:16 cooking video from the supplied six-panel storyboard. Use the storyboard ONLY as a reference for the chronological action order. Convert the panels into six sequential FULL-SCREEN shots in panel order. Never show the storyboard grid or multiple panels at once. [Hard cuts / specified transitions].

CONTINUITY: Maintain the same [nồi], [bếp], [tay/nhân vật], [đạo cụ], [ánh sáng] and ingredient appearance throughout. Keep the food state consistent with the previous shot. Food or the immediate action fills 85–95% of the frame. [Macro look / no zoom out / camera movement].

SHOT 1, 0.0–1.3s: [góc + cỡ máy]. [Hành động bắt đầu ngay]. Focus on [chi tiết]. End with [trạng thái cuối].
SHOT 2, 1.3–2.6s: [góc + cỡ máy]. [Một hành động]. Focus on [chi tiết].
SHOT 3, 2.6–3.9s: [góc + cỡ máy]. [Một hành động]. Focus on [chi tiết].
SHOT 4, 3.9–5.2s: [góc + cỡ máy]. [Một hành động]. Focus on [chi tiết].
SHOT 5, 5.2–6.5s: [góc + cỡ máy]. [Một hành động]. Focus on [chi tiết].
SHOT 6, 6.5–8.0s: [góc + cỡ máy]. [Hành động/kết quả cuối]. End on [khung hình kết].

MOTION & AUDIO: Natural hand and food movement, realistic fluid physics, subtle steam. [ASMR: tiếng dầu xèo / tiếng rót / tiếng khuấy / tiếng sôi]. [No music, dialogue or subtitles / hoặc mô tả âm thanh muốn có].

AVOID: visible storyboard grid, text or subtitles, extra fingers, warped utensils, morphing ingredients, duplicated food, sudden changes of pot/kitchen, ingredients appearing without being added.
```

## Ví dụ hoàn chỉnh: storyboard đoạn đầu lẩu Thái

### Prompt ảnh

```text
Create ONE photorealistic vertical 9:16 storyboard contact sheet with EXACTLY SIX panels arranged in 2 columns × 3 rows, in chronological order. Each panel is a separate full-frame close-up showing one action in preparing Thai hotpot.

SIX ACTIONS, in order:
1. Pour a thin stream of cooking oil into a cream-colored pot.
2. Add crushed lemongrass to the oil; show tiny bubbles beginning to form.
3. Add sliced shallots; show them falling naturally into the pot.
4. Stir lemongrass and shallots with a wooden spatula until fragrant.
5. Add tomato wedges and stir them into the aromatics.
6. Pour water or broth into the tomato mixture; show the red broth beginning to simmer.

CONTINUITY: Keep the same cream-colored pot, white home kitchen, slender hands, wooden spatula and soft natural daylight in all panels. The ingredients progress logically; do not show cooked seafood yet.

CAMERA & STYLE: Photorealistic food photography, appetizing macro close-ups, warm natural colors, clear visible action, realistic ingredients and cookware.

LAYOUT: exactly six equally sized panels, 2 columns × 3 rows, thin clean dividers. No text, labels, captions or logos.

AVOID: extra fingers, malformed utensils, duplicated ingredients, changing pot or kitchen, inconsistent food state, decorative text or watermark.
```

### Prompt video

```text
Create ONE 8-second vertical 9:16 cooking video from the supplied six-panel storyboard. Use it ONLY as a reference for chronological action order. Convert the six panels into six sequential full-screen shots in panel order; never show the grid or multiple panels at once. Hard cuts. Maintain the same cream-colored pot, white kitchen, hands, wooden spatula and soft natural light. Macro food photography; food or immediate action fills 85–95% of every shot; no zoom out.

SHOT 1, 0.0–1.3s: 75° macro. Begin immediately as a thin stream of oil pours into the empty cream-colored pot; focus on the continuous stream.
SHOT 2, 1.3–2.6s: 70° macro. Drop crushed lemongrass into the oil; show fibers and tiny bubbles.
SHOT 3, 2.6–3.9s: 65° macro. Add sliced shallots; focus on the slices falling naturally.
SHOT 4, 3.9–5.2s: 60° macro. Stir the lemongrass and shallots with a wooden spatula; gentle sizzling.
SHOT 5, 5.2–6.5s: 65° macro. Add tomato wedges and stir; focus on the wedges softening and releasing juices.
SHOT 6, 6.5–8.0s: 55° macro. Pour broth into the pot; end as small bubbles appear and light steam rises.

Realistic hand movement, natural food physics and subtle steam. ASMR only: gentle sizzling, stirring and pouring; no music, dialogue or subtitles. No extra fingers, warped utensils, morphing ingredients, duplicated food or changes to the pot/kitchen.
```

## Checklist trước khi bấm tạo

- Ảnh storyboard và prompt video có cùng đúng sáu hành động, cùng thứ tự.
- Mỗi shot mô tả một hành động nhìn thấy được, không chỉ ghi tên món/định tính.
- Tổng thời gian các shot khớp thời lượng video.
- Thức ăn tiến triển theo logic nấu ăn; không nhảy từ chín về sống.
- Cảnh mở đầu có hành động ngay, cảnh kết thúc có khung hình chủ đích.
- Quy định rõ “không hiển thị storyboard grid” nếu đầu ra cần là video dựng thành các shot toàn màn hình.
- Tỉ lệ ảnh tham chiếu khớp tỉ lệ video; nếu lệch, tạo/crop ảnh phù hợp trước khi đưa vào tool.
- Chỉ thêm âm thanh mà mình muốn nhận; nếu cần nhạc hoặc phụ đề chính xác, xử lý riêng trong bước dựng.
