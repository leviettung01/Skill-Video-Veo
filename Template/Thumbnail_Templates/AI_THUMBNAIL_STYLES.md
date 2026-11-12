# Thumbnail AI — bộ style theo ảnh mẫu

Phân tích 29 ảnh trong `ảnh mẫu thumbnail/`; bảng liên hệ tên file và thứ tự nằm tại `audit_results/thumbnail_index.txt`. Các ảnh 2, 12, 13, 18, 19 là ảnh chụp màn hình danh mục, dùng để hiểu hệ phong cách, không sao chép chữ, logo, giá hoặc bố cục của giao diện đó.

## Quy trình bắt buộc

1. Xem ảnh sản phẩm gốc, nhân vật nếu có, khung hình video và thông tin đã xác minh. Chọn một style dưới đây theo ngành hàng và mục đích. Ưu tiên tài liệu người dùng cung cấp; không tự bịa giá, ưu đãi, công dụng hay chứng nhận.
2. Dùng model tạo ảnh AI thực sự: gửi prompt cùng các ảnh tham chiếu sẵn có với vai trò rõ ràng (sản phẩm: giữ hình dáng, màu, nhãn; nhân vật: giữ khuôn mặt, tóc, trang phục; bối cảnh: khớp video). Chỉ dùng nhân vật khi dự án có nhân vật hoặc người dùng yêu cầu. Với món nấu ăn dùng món và cảnh quay làm tham chiếu, không gán sản phẩm hay presenter giả.
3. Sinh một ảnh thumbnail hoàn chỉnh 9:16, với bố cục, bối cảnh, ánh sáng, vật thể và chữ được thiết kế theo style đã chọn. Yêu cầu đúng nguyên văn tiêu đề ngắn tiếng Việt và dấu; chữ ít, tương phản cao, nằm trong vùng an toàn. Không dùng chữ hoặc nhãn sai sự thật.
4. Xem ảnh thực tế: tính đúng sản phẩm và nhân vật, hình thể tự nhiên, chữ đúng dấu, bố cục rõ trên điện thoại. Nếu chữ sai có thể sửa bằng công cụ ảnh hoặc overlay cục bộ sau khi AI đã tạo toàn bộ ảnh; overlay không được thay thế bước sinh ảnh AI. Ghi provider, style, prompt, ref và đường dẫn. Không tự động gửi lại job có phí thất bại.
5. Lưu bản thumbnail riêng, giữ video gốc; chỉ ghép 0,1s đầu khi người dùng yêu cầu hoặc cấu hình dự án yêu cầu. Xác minh frame đầu, thời lượng, âm thanh và liên kết Studio/Matrix.

## Prompt chung

`Create one polished vertical 9:16 Vietnamese [industry] thumbnail. The supplied product references define exact product appearance, shape, material, label and colors. The supplied character reference, if present, defines the same face, hair and outfit. Integrate these naturally into [scene] in the chosen style: [STYLE PROMPT]. Use persuasive, accurate visual hierarchy, readable mobile composition and realistic physical details. Exact headline: "[HEADLINE]". Optional verified supporting text: "[VERIFIED TEXT]". No invented pricing, claims, brands or logos, no malformed hands, no extra products, no illegible pseudo-text, no watermark. Preserve clear safe margins.`

Điền `[VERIFIED TEXT]` chỉ khi có dữ liệu nguồn; bỏ toàn bộ dòng nếu không có. Các mẫu sau bổ sung vào `[STYLE PROMPT]`, không mặc định thêm nhân vật/giá.

## Các style

| ID | Nguồn tham khảo | Ngành phù hợp | Prompt style riêng |
|---|---|---|---|
| kawaii_pastel | 3, 4, 6, 7, 10, 17 | Dép, phụ kiện, đồ trẻ em | `Playful pastel pink or mint tactile paper backdrop, large centered hero product, delicate flower doodles and tiny hand-drawn icons, soft studio light, rounded display type, generous spacing, tasteful product callouts.` |
| korean_scrapbook | 14–16, 23 | Túi, giày, phụ kiện nữ | `Korean scrapbook editorial with cream kraft paper, torn-paper edges, tasteful ribbons, a single oversized product hero, optional small authentic detail inset, handwritten accents and warm soft light; avoid clutter.` |
| fashion_lookbook | 5, 8, 9, 11 | Trang phục, đồ ngủ | `Elegant beige fashion lookbook, full-length referenced model wearing the exact outfit, soft interior studio, restrained garment detail insets, refined editorial type and clean aligned information blocks.` |
| streetwear_flash | 21 | Streetwear, quần áo unisex | `High-contrast dynamic streetwear campaign, bold condensed typography, graphic black white and red accents, strong full-body pose and product silhouette, energetic but clear visual hierarchy; show prices only when verified.` |
| fashion_review | 26–28 | Thời trang, giày | `Authentic creator fashion review cover, referenced model prominently displaying the exact item, natural indoor backdrop, one carefully placed garment detail image, crisp headline and concise factual callouts, contemporary editorial layout.` |
| kitchen_minimal | 20 | Gia dụng, dụng cụ bếp | `Premium warm ivory kitchen product advertising, coordinated pastel palette, exact product prominently displayed on a light wood counter, sunlit window, refined serif headline, restrained supporting copy and clean negative space.` |
| product_multicolor | 22 | Dép, hàng nhiều màu | `Soft neutral catalog photography, accurate verified color variants arranged in a balanced row, gentle fabric and wood textures, clear lead product and minimal rounded callouts; do not invent variants.` |
| skincare_creator | 25 | Mỹ phẩm, chăm sóc cá nhân | `Bright beauty creator cover, authentic reference model holding exact packaging, fresh pink and white backdrop, flattering soft light, legible title and verified facts only, neat small accent icons, no invented effects or claims.` |
| jewelry_nature | 29 | Trang sức, phụ kiện | `Fresh elegant botanical jewelry advertising, faithful macro close-up of the exact jewelry, soft green and ivory palette, diffused daylight, refined product detail insets and understated typography.` |
| food_editorial | Phát triển cho món ăn từ yêu cầu hiện tại | Món ăn, đồ uống | `Appetizing high-end food editorial photography, hero dish large and sharp, natural ingredients and cooking environment consistent with references, gentle steam and realistic textures, dark or warm contrasting background, bold Vietnamese title with generous safe margins; no presenter unless provided.` |
| direct_retail | 1, 24 | Hàng tiêu dùng, ưu đãi đã xác minh | `Direct-response retail cover with the supplied presenter and exact product, strong concise headline, structured contrast panels and a clean product hero. Show an offer or price only if provided and verified; avoid fabricated urgency.` |

Không sao chép thương hiệu, người mẫu, chữ, giá hoặc sản phẩm trong ảnh mẫu. Chọn style theo nội dung, có thể pha trộn tối đa hai style khi phù hợp, và lưu ID style thực tế.


## Catalog đang dùng trong Tool (AI v3)

`ai_styles.json` là nguồn cho 13 thẻ style trong Cài đặt và Thumbnail Studio. Thẻ cũ được ánh xạ bằng alias để giữ dự án; không hiển thị trong gallery mới. Thêm `pastel_pov_handmade` theo ảnh Lavender & Lace đã duyệt và `home_creator` cho gia dụng có người thật. Mỗi style có prompt riêng, ngành hàng, chế độ chủ thể và ảnh tham khảo. Ảnh tham khảo không phải kết quả đã tạo cho sản phẩm hiện tại. Chế độ POV không dùng ảnh chân dung; chế độ có người phải có ảnh người thật của dự án. Prompt không được bỏ qua ảnh sản phẩm hoặc cảnh video để thay bằng người mẫu ngẫu nhiên.


## Demo mới từ project có sẵn

Đọc [PROJECT_STYLE_PROMPTS.md](PROJECT_STYLE_PROMPTS.md) để xem ba style mới, ảnh nguồn, cấu trúc prompt và prompt thực tế: Creator xưởng · Editorial sạch; Phụ kiện nam · Quiet Luxury; Ẩm thực · Macro tạp chí. Danh mục hiện có 16 style AI.
