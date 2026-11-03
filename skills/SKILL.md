---
name: skill-video-veo
description: >-
  Use this skill when the user wants to generate product or story videos (single or bulk/mass products)
  using Role Skills (.MD), Google Flow (Veo 3.1 / Nano Banana 2 / Imagen 4), or Grok/CLIProxy,
  or wants to open/manage the Skill Video Veo Local Web Dashboard, Role Skills, or Accounts.
---

# ⚡ Lê Việt Tùng - SkillAutoVeo — AI Agent Brain × Multi-Threaded Video Engine

> **Thương hiệu & Tác giả:** **Lê Việt Tùng - SkillAutoVeo**
> - 📞 **Zalo:** [0915967790](https://zalo.me/0915967790)
> - 🌐 **Facebook:** [https://www.facebook.com/tungbinh.38/](https://www.facebook.com/tungbinh.38/)
> - 🧩 **Extension Chrome đi kèm:** `LeVietTung_autoveo` (`Extension Recapcha/LeVietTung_autoveo`)
> - 📖 **Hướng dẫn cài đặt cho AI Agent trên máy mới:** Xem chi tiết tại [`HUONG_DAN_CAI_DAT_CHO_AI_AGENT.md`](./HUONG_DAN_CAI_DAT_CHO_AI_AGENT.md)

---

## 0. Cài Đặt Tự Động Cho Máy Mới (Dành Cho AI Agent Của Khách Hàng)

Nếu đang chạy trên một máy tính mới lần đầu tiên, **AI Agent chỉ cần chạy duy nhất 1 lệnh sau** tại thư mục gốc của Skill để tự động cài đặt toàn bộ thư viện Python (`requirements.txt`, `torch`, `opencv-python`, `playwright`, `curl_cffi`, `PyQt6`, ...), trình duyệt Chromium, và kiểm tra toàn bộ thành phần:

```powershell
python setup_and_verify_agent.py --install
```

Để kiểm tra nhanh trạng thái sẵn sàng của máy:
```powershell
python setup_and_verify_agent.py --verify
```

---

Trong kiến trúc **Lê Việt Tùng - SkillAutoVeo**, **AI Agent (Antigravity / Codex / Cursor)** đóng vai trò là **BỘ NÃO ĐIỀU KHIỂN**:
1. **Người dùng** chỉ cần quản lý Tài khoản, Role Skill (`.MD`), xem Dashboard/Dự án trên **Giao diện Web Local nhân Microsoft Edge** (`http://127.0.0.1:8456`) và ra lệnh trực tiếp trong khung chat của AI Agent.
2. **AI Agent** đọc nội dung **Role Skill (`.MD`)**, quan sát ảnh/thông tin của từng sản phẩm, tự biên soạn kịch bản phân cảnh (`image_prompt`, `video_prompt` chuẩn tiếng Anh theo quy định của Role Skill) rồi truyền gói JSON xuống **Engine Đa Luồng (`veo_skill_cli.py`)**.
3. **Engine Đa Luồng** thực thi tốc độ cao qua các tài khoản đã đăng nhập:
   - **Bước 1 (Đa luồng Tạo Ảnh)**: Vẽ ảnh từng phân cảnh từ `image_prompt` + tham chiếu ảnh sản phẩm gốc (`product_image_path`).
   - **Bước 2 (Đa luồng Tạo Video I2V)**: Dựng video chuyển động cho từng phân cảnh từ ảnh phân cảnh vừa tạo + `video_prompt`.
   - **Bước 3 (Ghép Video Final)**: Tự động nối các phân cảnh bằng FFmpeg thành file `FINAL_<tên_sản_phẩm>.mp4`.

---

## 1. Quy Trình Nhanh 1 Bước: Gửi Link / ID Sản Phẩm + Mã Số Template (`001`, `002`, `003`)

Mỗi Template trong **Chợ Template & Role Skill (`Template/`)** có một **Mã số định danh độc nhất (`code`)** tích hợp sẵn `ROLE_SKILL.md`, `generator.py` và Video Demo Final 1080p 60 FPS:
- **`001`** (`Template/Nhà Xưởng`): **Nhà Xưởng (Báo Giá Tận Xưởng & Kiểm Định QC — Có Nhân Vật + Voice + Sub Karaoke 60 FPS)**
- **`002`** (`Template/Đồ Ăn Vặt POV (Có Voice)`): **Đồ Ăn Vặt & Ẩm Thực POV (Có Voice Review + Bày Biện Món Ăn + Sub Karaoke 60 FPS)**
- **`003`** (`Template/Đồ Ăn Vặt`): **Đồ Ăn Vặt & Pha Chế UGC (Cận Cảnh Bàn Tay & Topping + Sub Karaoke 60 FPS)**

Khi người dùng chỉ cần nói: *"Tạo các sản phẩm cho ID 1731391379899778653 theo template 002"* hoặc gửi **Link/ID sản phẩm TikTok** kèm **Mã Template (`001`, `002`, `003`)**:

```powershell
python "flow_final_pipeline/scripts/product_crawler_bridge.py" "<LINK_HOAC_ID_SAN_PHAM>" --template 001 --run
```
*(Tham số `--template` chấp nhận cả mã số `001`, `002`, `003`, `#001`, `template 001` hoặc tên thư mục `Nhà Xưởng`, `Đồ Ăn Vặt POV (Có Voice)`, `Đồ Ăn Vặt`).*

Quy trình tự động thực hiện trọn gói:
1. **Tự động lấy thông tin & tải bộ ảnh sản phẩm** (nếu chưa có sẵn trong `projects/<pid>/product_images/`):
   - Kiểm tra cache trong `tiktok_web/runtime/data/product_images/<pid>` trước.
   - **Cách 1 (`--method auto` / `spaiauto`)**: Tải qua SPAI Auto API (`tools.spaiauto.com/api.php`), nếu lỗi tự động fallback sang Cách 2.
   - **Cách 2 (`--method browser`)**: Mở Chrome TikTokShop (`tiktok_chrome_profile`) + Tự động giải Captcha bằng BoxPhone YOLO.
   - Chuyển đổi toàn bộ ảnh về `projects/<pid>/product_images/prod_1.jpg`..`prod_N.jpg` và lưu `info.json`.
2. **Đọc cấu hình Thư Viện Nhân Vật (`flow_final_pipeline/voices_and_characters.json`) & Template (`Template/<Tên Template>`)**:
   - Lấy danh sách nhân vật đang bật (`nv1`, `nv2`, ...) và cấu hình `videos_per_character` (mặc định 3 video / nhân vật = 6 video / sản phẩm).
   - Tự động sinh `prompts.json` và `spec_*.json` theo đúng quy tắc trong `Template/<Tên Template>/generator.py`.
3. **Chạy Đa Luồng Tạo Ảnh Ref 2K + Video 1080p (`run_all_7_videos_mt.py`)**:
   - Tạo ảnh tham chiếu 9:16 bằng `Nano Banana 2.1 (BELUGA)` và tải bản **2K (`1536x2752`)** qua `SPrCad`.
   - Kiểm tra ảnh tham chiếu AI và ảnh sản phẩm gốc, sau đó gửi 2 ảnh tham chiếu (`[Ảnh Ref Nhân Vật 2K, Ảnh Sản Phẩm Gốc]`) + `Voice ID` lên `Veo 3.1 Omni Flash`, upsample **1080p** (`p0UkFb`) và ghép FFmpeg ra `final_videos/{pid}_{nv1/nv2}_v{1..N}.mp4`.

---

## 2. Khởi động Giao Diện Web Local (Nhân Microsoft Edge — `http://127.0.0.1:8456`)

Khi người dùng muốn mở giao diện quản lý:
```powershell
python "server.py"
```
Giao diện gồm 7 phân mục trực quan:
1. **📊 Studio Dự Án**: Theo dõi tiến độ đa luồng, xem kịch bản, đối chiếu Ảnh Sản Phẩm Mẫu vs Ảnh Ref AI 2K vs Video Final 1080p, mở folder `final_videos/` và dọn dẹp dữ liệu render cũ sau khi đã upload.
2. **🛍️ Crawl Sản Phẩm**: Dán Link/ID sản phẩm TikTok (đơn lẻ hoặc hàng loạt), bấm tải theo **Cách 1 (SPAI Auto 1→2)** hoặc **Cách 2 (Browser TikTokShop + Captcha BoxPhone)**, xem chi tiết/chọn ảnh mẫu AI và bấm **🎬 Tạo Video** với Template tuỳ chọn (`Template/Nhà Xưởng`, `Template/Đồ Ăn Vặt`, ...).
3. **🏪 Chợ Template Video**: Xem trực tiếp **Video Demo 9:16**, **Ảnh Storyboard/Ref 2K mẫu**, **Sơ đồ quy trình 4 bước**, **Kịch bản phân cảnh chi tiết** và **Sản phẩm mẫu** của từng Template (`Template/Nhà Xưởng`, `Template/Đồ Ăn Vặt`), đọc tài liệu `.MD` và bấm chọn sử dụng ngay.
4. **👤 Nhân Vật (Tích hợp Giọng Đọc & 4 Mẫu Character Sheet AI)**:
   - Giao diện tối giản, chuyên nghiệp: Quản lý danh sách nhân vật mẫu (`NV1 • Nữ Tư Vấn Xưởng`, `NV2 • Nữ Chốt Sale Năng Lượng`, `NV3 • Nam Mẫu Thời Trang`) và thêm nhân vật mới.
   - **Tích hợp chọn Giọng Đọc ngay trong từng nhân vật**: Chọn từ **Kho Giọng Việt Nam Đã Custom** hoặc **30 Giọng Gốc Google Flow**, bấm **`🔊 Nghe thử`** bằng câu thoại tiếng Việt, bấm **`✏️ Custom`** hoặc **`➕ Mới`** để Tool tự động kết nối Google Flow tạo giọng đọc mới và lưu mẫu âm thanh tiếng Việt về máy.
   - **4 Mẫu Character Sheet Chuẩn Studio (`Template/Character_Sheet_Templates`)**:
     - `Mẫu #01 • Chuẩn Studio 6 Góc (3 Toàn Thân + 3 Cận Mặt)`
     - `Mẫu #02 • Hoạt Hình 3D Pixar (Turnaround + T-Pose + Biểu Cảm)`
     - `Mẫu #03 • Lookbook & 5 Macro Zoom (4 Toàn Thân + 5 Chi Tiết)`
     - `Mẫu #04 • Thời Trang & Phim AI (1 Chân Dung Lớn + 3 Toàn Thân)`
   - **Trình xem ảnh Fullscreen Lightbox & Zoom Studio**: Bấm vào bất kỳ ảnh nhân vật, sản phẩm hay ảnh Ref 2K để xem toàn màn hình, lăn chuột phóng to 50%–500%, kéo thả soi chi tiết và tải ảnh gốc.
5. **🌐 Tổng Quan Matrix**: Xem toàn bộ sản phẩm × các video trên cùng 1 màn hình.
6. **📜 Role Skill (`.MD`)**: Quản lý các file `.MD` định nghĩa quy tắc kịch bản.
7. **🔑 Tài Khoản & Flow**: Quản lý tài khoản Google Flow / Veo 3 và Grok / CLIProxy.

---

## 2.5. Hệ Thống Giọng Đọc & Quy Tắc AI Agent Chọn Giọng Đọc (`voices_and_characters.json`)

Toàn bộ danh sách Nhân vật và Kho Giọng Đọc được lưu tại [`flow_final_pipeline/voices_and_characters.json`](./flow_final_pipeline/voices_and_characters.json) và quản lý qua [`flow_final_pipeline/scripts/character_library_manager.py`](./flow_final_pipeline/scripts/character_library_manager.py):

1. **Làm sao lấy danh sách giọng đọc?**
   - **Kho 8 Giọng Đọc Affiliate Việt Nam (`voices`)**: Đã phân loại sẵn theo Vùng miền (`north`, `south`, `central`), Giới tính (`female`, `male`) và Tone năng lượng (`high_energy_sale`, `warm_trustworthy`, `sweet_foodie`, `calm_story`).
   - **16 Giọng Built-in Google Flow (`builtin_flow_voices`)**: Gồm `erinome`, `zephyr`, `leda`, `laomedeia`, `autonoe`, `kore`, `sulafat`, `aoede`, `callirhoe`, `vindemiatrix`, `orus`, `puck`, `fenrir`, `charon`, `enceladus`, `iapetus` (kèm link WAV nghe thử trực tiếp từ Google Static).
   - **Quét tự động từ Google Flow (`scan_and_sync_flow_voices()`)**: Quét toàn bộ dự án trong `projects/*/prompts.json` và tài khoản Google Flow để thu thập các `UUID Voice Ingredient` mới vào kho.

2. **Làm sao tạo hoặc custom giọng đọc mới (Bắc/Nam, Nam/Nữ, Năng lượng)?**
   - Google Flow (`Veo 3.1 Omni Flash`) điều khiển giọng nói qua **Cơ chế Kết hợp Kép (Dual Voice Control)**:
     - **Tầng 1 — `voice_id` (`voice_list = [[voice_id]]`)**: Truyền `UUID Voice Ingredient` (36 ký tự, ví dụ `27f51973-e290-4a38-bd7a-9d6fbe81b2f6` hoặc `75a3d14a-ed10-4bdc-862c-44adb02a5562`) hoặc tên giọng chuẩn Google Flow (`erinome`, `orus`, `puck`, `sulafat`, ...).
     - **Tầng 2 — `voice_prompt_en` + `dialect_markers_vn`**: Tự động sinh chuỗi chỉ dẫn âm học tiếng Anh (ví dụ: `"Southern Vietnamese female voice (Saigon accent), sweet, cheerful, friendly foodie & lifestyle reviewer tone, fast-paced 4.6 words/sec"`) kết hợp từ đệm vùng miền (`nhé, nha, cực kỳ, chuẩn đét` cho Miền Bắc; `nghen, nè, mê chữ ê kéo dài, xuất sắc luôn` cho Miền Nam) nhúng trực tiếp vào trường `VOICE` / `VOICEOVER TIMELINE` của `video_prompt`.

3. **Gắn cố định giọng đọc cho nhân vật (`lock_voice_to_character`)**:
   - Mỗi nhân vật (`nv1`, `nv2`, ...) có trường `voice_key`, `voice_id`, `voice_prompt_en`, `voice_region` và `lock_voice_to_character: true`. Khi bật khóa cố định, mọi video sử dụng nhân vật đó đều tự động dùng đúng giọng đọc và phương ngữ đã gắn.

4. **AI Agent dựa vào đâu để khuyến nghị và chọn giọng đọc cho từng Video?**
   - AI Agent sử dụng hàm `recommend_voice_for_product(product_name, template_name, target_region)` (hoặc endpoint `POST /api/characters/recommend-voice`) dựa trên **4 Trụ Cột Phân Tích**:
     1. **Ngành hàng & Từ khóa Sản phẩm**:
        - *Đồ ăn vặt, kho quẹt, bánh tráng, cơm cháy, trà sữa, mỹ phẩm*: Ưu tiên giọng **Nữ trẻ trung, cuốn miệng hoặc ngọt ngào** (`v7_nu_bac_genz_foodie`, `v3_nu_nam_foodie`, `nv2`).
        - *Gia dụng, inox, bàn chải, kệ, cây lau nhà, xưởng sản xuất*: Ưu tiên giọng **Nữ/Nam uy tín tư vấn xưởng hoặc năng lượng chốt đơn** (`nv1`, `nv2`, `v5_nam_bac_chuyen_gia`).
        - *Đặc sản vùng miền, quà biếu, thảo mộc*: Ưu tiên giọng **Truyền cảm, dịu dàng** (`v8_nu_trung_truyen_cam`, `nv1`).
     2. **Loại Template & Góc quay (`001`, `002`, `003`)**:
        - **Template `001` (`Nhà Xưởng`)**: Bắt buộc lấy giọng đã khóa cố định theo từng nhân vật (`nv1`, `nv2`) để khớp khẩu hình lip-sync với gương mặt nhân vật trên màn hình.
        - **Template `002` (`Đồ Ăn Vặt POV Có Voice`)**: Không lộ mặt nhân vật nên cho phép chọn bất kỳ giọng nào trong 8 giọng (`selected_voice_key`), mặc định ưu tiên giọng Foodie (`v7_nu_bac_genz_foodie`, `v3_nu_nam_foodie`, `nv2`).
        - **Template `003` (`Đồ Ăn Vặt ASMR`)**: Tắt Voiceover người nói, tập trung 100% âm thanh ASMR vật lý + Sub Karaoke 60 FPS.
     3. **Tệp khách hàng & Vùng miền mục tiêu (`north` / `south` / `central`)**: Tự động đồng bộ cả `voice_prompt_en` (`Hanoi accent` vs `Saigon accent`) và từ ngữ cảm thán trong kịch bản tiếng Việt.
     4. **Nhịp độ cảm xúc theo phân cảnh**: Cảnh 1 (Hook 0–8s) đẩy năng lượng cao tạo tò mò; Cảnh 2–3 (Demo/Review) giữ giọng rõ chữ, tốc độ chuẩn `4.6 từ/giây` (32–36 từ / 8 giây) để không bị cắt câu cuối.

---

## 3. Quy Trình Xử Lý Số Lượng Lớn Sản Phẩm Tuỳ Chỉnh (Dành Cho AI Agent)

Khi người dùng ra lệnh tạo video cho 1 hoặc hàng loạt sản phẩm (ví dụ: *"Tạo video cho toàn bộ sản phẩm trong thư mục `D:\SanPham` theo Role Skill `DoAnVat.MD`"* hoặc *"Chạy dự án `Chiến dịch Sản Phẩm Mới`"*), AI Agent thực hiện tuần tự 4 bước sau:

### Bước 1: Kiểm tra trạng thái Tài khoản, Dự án & Đọc Role Skill
Chạy lệnh kiểm tra trạng thái hệ thống và đọc nội dung file Role Skill (`.MD`) được yêu cầu:
```powershell
python "Skill Video Veo/veo_skill_cli.py" status
python "Skill Video Veo/veo_skill_cli.py" read-role --file "DoAnVat.MD"
```
> **Lưu ý chọn Model Video Google Flow**: Kiểm tra trường `available_video_models` và `has_low_priority_lite` trong output của `status`. Chỉ dùng `Veo 3.1 - Lite [Lower Priority]` nếu tài khoản có `has_low_priority_lite: true`, ngược lại dùng `Veo 3.1 - Fast` hoặc `Veo 3.1 - Lite`.

### Bước 2: Nhập danh sách sản phẩm (nếu người dùng đưa thư mục mới) và lấy danh sách chờ (`list-pending`)
- Nếu người dùng cung cấp đường dẫn thư mục chứa ảnh sản phẩm:
  ```powershell
  python "Skill Video Veo/veo_skill_cli.py" import-folder --project "Ten_Du_An" --folder "D:\DuongDan\ThuMucAnh" --role "DoAnVat.MD" --img-model "Nano Banana 2" --vid-model "Veo 3.1 - Fast" --aspect "9:16" --scenes 4
  ```
- Lấy danh sách các sản phẩm cần AI Agent lên kịch bản:
  ```powershell
  python "Skill Video Veo/veo_skill_cli.py" list-pending --project "Ten_Du_An"
  ```

### Bước 3: AI Agent đóng vai Bộ Não sinh Kịch Bản & Prompt cho từng sản phẩm
- Với mỗi sản phẩm trong `pending_products`:
  1. Dùng công cụ `read_file` xem ảnh sản phẩm gốc (`product_image_path`) nếu cần nhận diện chính xác màu sắc, bao bì, kết cấu sản phẩm.
  2. Tuân thủ **100% quy tắc trong file Role Skill (`.MD`)** để viết `scenes` (mặc định 4 phân cảnh).
  3. Mỗi phân cảnh bắt buộc có đủ:
     - `scene_number`: Số thứ tự cảnh (`1, 2, 3, ...`)
     - `scene_title`: Tiêu đề phân cảnh
     - `scene_description`: Mô tả ngắn phân cảnh (tiếng Việt)
     - `image_prompt`: Prompt tạo ảnh chi tiết (tiếng Anh, mô tả rõ bố cục, ánh sáng, bối cảnh theo Role Skill, giữ nguyên nhận diện sản phẩm gốc)
     - `video_prompt`: Prompt chuyển động I2V chi tiết (tiếng Anh, mô tả chuyển động camera dolly/pan/zoom, chuyển động vật lý và âm thanh SFX/BGM, không có chữ/subtitles)
- **Mẹo xử lý số lượng cực lớn (10 - 100+ sản phẩm)**:
  - Nếu dự án có nhiều sản phẩm (ví dụ > 10 sản phẩm), AI Agent có thể chia nhóm (mỗi nhóm 5-10 sản phẩm) hoặc dùng `invoke_subagent` song song để soạn JSON kịch bản nhanh chóng, sau đó gộp vào file `prompts_payload.json`.

### Bước 4: Truyền Prompt xuống Engine và kích hoạt chạy Đa Luồng xuất Video Final
Ghi toàn bộ kịch bản ra một file JSON tạm (ví dụ `Skill Video Veo/projects/prompts_payload.json`) theo định dạng:
```json
{
  "products": [
    {
      "product_id": "prod_xxxx",
      "product_name": "Khô gà lá chanh",
      "scenes": [
        {
          "scene_number": 1,
          "scene_title": "Hook - Cận cảnh mở gói",
          "scene_description": "Cận cảnh xé túi khô gà lá chanh giòn rụm trên bàn gỗ",
          "image_prompt": "Close-up product photography of the exact input chicken jerky pack on a warm rustic wooden table...",
          "video_prompt": "Slow push-in camera movement focusing on the crispy golden chicken strips, subtle steam and lime leaf motion, SFX: crisp tearing and crunching sound, upbeat acoustic background music."
        }
      ]
    }
  ]
}
```
Sau đó gọi lệnh nạp prompt và chạy đa luồng (`--auto-run`):
```powershell
python "Skill Video Veo/veo_skill_cli.py" submit-prompts --project "Ten_Du_An" --payload-file "Skill Video Veo/projects/prompts_payload.json" --auto-run --product-workers 2 --scene-workers 3
```
- Lệnh này sẽ tự động chạy đa luồng: **Tạo Ảnh các cảnh song song -> Tạo Video I2V song song -> Ghép FFmpeg ra Video Final (`.mp4`)** và cập nhật trực tiếp lên giao diện Web Local (`http://127.0.0.1:8456`).

