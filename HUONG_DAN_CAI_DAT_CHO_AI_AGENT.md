# ⚡ HƯỚNG DẪN CHI TIẾT CHO AI AGENT & KHÁCH HÀNG (CÀI ĐẶT TỪ A–Z TRÊN MÁY MỚI)

> **Thương hiệu & Tác giả:** **Lê Việt Tùng - SkillAutoVeo**
> - 📞 **Zalo hỗ trợ:** [0915967790](https://zalo.me/0915967790)
> - 🌐 **Facebook:** [https://www.facebook.com/tungbinh.38/](https://www.facebook.com/tungbinh.38/)
> - 🧩 **Tên Extension Chrome đồng bộ:** `LeVietTung_autoveo` (Nằm tại `Extension Recapcha/LeVietTung_autoveo`)

---

## 💬 PHẦN 1: CÂU LỆNH MẪU (PROMPT) ĐỂ KHÁCH HÀNG GỬI CHO AI AGENT TRÊN MÁY MỚI

Khi gửi bộ thư mục **`Skill Video Veo`** này sang một máy tính mới, khách hàng chỉ cần mở AI Agent (Antigravity, Cursor, Windsurf, Claude Code, Trae...) tại thư mục này và **copy-paste nguyên văn câu lệnh dưới đây** gửi cho AI Agent:

```text
Hãy đọc file HUONG_DAN_CAI_DAT_CHO_AI_AGENT.md và SKILL.md trong thư mục hiện tại, sau đó tự động kiểm tra và cài đặt toàn bộ môi trường, thư viện Python, FFmpeg, Playwright Chromium, kiểm tra Extension LeVietTung_autoveo cùng toàn bộ dữ liệu cho máy mới bằng lệnh `python setup_and_verify_agent.py --install`, rồi khởi chạy Web Studio của Lê Việt Tùng - SkillAutoVeo ở cổng 8456 giúp tôi.
```

---

## 🤖 PHẦN 2: QUY TRÌNH TỰ ĐỘNG DÀNH CHO AI AGENT (AI AGENT RUNBOOK)

> **CHỈ THỊ DÀNH CHO AI AGENT:**
> Nếu bạn là AI Agent đang chạy trên máy của khách hàng, hãy thực hiện tuần tự các bước dưới đây một cách tự động (không bỏ bước) để máy tính mới sẵn sàng 100%. Toàn bộ mã nguồn, trình thu thập sản phẩm TikTok (`tiktok_crawler`), trọng số AI giải Captcha BoxPhone (`08102026_detect.torchscript`), Extension Chrome (`Extension Recapcha/LeVietTung_autoveo`), và Template (`Template/Nhà Xưởng`) đều đã được đóng gói độc lập 100% bên trong thư mục này.

### Bước 1: Kiểm tra & Cài đặt Python (3.10 – 3.12) và FFmpeg (Nếu máy mới chưa có)

1. Kiểm tra Python:
   ```powershell
   python --version
   ```
   - Nếu máy chưa có Python, AI Agent tự động cài qua `winget`:
     ```powershell
     winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
     ```
2. Kiểm tra FFmpeg (bắt buộc để ghép & hậu kỳ video 1080p 9:16):
   ```powershell
   ffmpeg -version
   ```
   - Nếu máy chưa có `ffmpeg`, AI Agent tự động cài qua `winget`:
     ```powershell
     winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
     ```

---

### Bước 2: Chạy Script Tự Động Cài Đặt Toàn Bộ Thư Viện & Trình Duyệt

Tại thư mục gốc của Skill (`Skill Video Veo`), AI Agent chạy lệnh:

```powershell
python setup_and_verify_agent.py --install
```

Lệnh này sẽ tự động thực hiện 4 tác vụ:
1. Cài đặt toàn bộ thư viện trong `requirements.txt` (`requests`, `curl_cffi`, `Pillow`, `opencv-python`, `numpy`, `playwright`, `PyQt6`, `torch`, `urllib3`).
2. Tự động kiểm tra từng module Python và cài bù nếu thiếu bất kỳ gói nào.
3. Cài đặt trình duyệt nhân Chromium cho Playwright:
   ```powershell
   python -m playwright install chromium
   ```
4. Tự động khởi tạo đầy đủ các thư mục dữ liệu cục bộ (`data/`, `cookies/`, `profiles/`, `flow_final_pipeline/projects/`, `flow_final_pipeline/final_videos/`, `accounts.json`, `veo3_config.json`).

---

### Bước 3: Kiểm Tra Trạng Thái Toàn Hệ Thống (Healthcheck)

Sau khi cài xong, AI Agent chạy lệnh kiểm tra:

```powershell
python setup_and_verify_agent.py --verify
```

Đảm bảo tất cả các mục sau đều báo **`✅ Sẵn sàng`**:
- `Extension Chrome`: `Extension Recapcha/LeVietTung_autoveo` (`✅ Sẵn sàng`)
- `BoxPhone Captcha YOLO`: `tiktok_crawler/boxphone_captcha/weights/08102026_detect.torchscript` (`✅ Sẵn sàng`)
- `Template Nhà Xưởng`: `Template/Nhà Xưởng/template_config.json` (`✅ Sẵn sàng`)
- `Thư Viện Nhân Vật`: `flow_final_pipeline/characters/` (`✅ Sẵn sàng`)
- `TẤT CẢ THƯ VIỆN PYTHON LÕI ĐÃ ĐƯỢC CÀI ĐẶT ĐẦY ĐỦ!`

---

### Bước 4: Cài Đặt Extension Chrome `LeVietTung_autoveo` & Đăng Nhập Google Flow

Hệ thống đi kèm Extension độc quyền **`LeVietTung_autoveo`** (đã đồng bộ màu sắc Đen Carbon – Vàng Hoàng Gia & thương hiệu **Lê Việt Tùng - SkillAutoVeo**) tại thư mục:
`Extension Recapcha/LeVietTung_autoveo`

Có **2 cách** để nạp Extension:
- **Cách Tự Động (Khuyên dùng):**
  1. Mở giao diện Web Studio (`http://127.0.0.1:8456`) -> vào tab **`🔑 Tài Khoản & Flow`**.
  2. Điền tên Profile (ví dụ: `leviettung04`) và bấm **`🔑 Mở Chrome Đăng Nhập`**.
  3. Tool sẽ tự động mở Chrome kèm cờ `--load-extension=".../Extension Recapcha/LeVietTung_autoveo"`.
- **Cách Thủ Công (Nếu nạp vào Chrome sẵn có):**
  1. Mở trình duyệt Chrome, truy cập địa chỉ: `chrome://extensions/`
  2. Bật công tắc **Developer mode (Chế độ dành cho nhà phát triển)** ở góc trên bên phải.
  3. Bấm nút **Load unpacked (Tải tiện ích đã giải nén)** ở góc trên bên trái.
  4. Chọn đúng thư mục: `Extension Recapcha/LeVietTung_autoveo` bên trong folder Skill này.
  5. Mở trang `https://labs.google/fx/vi/tools/flow` hoặc bấm nút **🌐 Mở Tab Google Flow** trên Extension, bật công tắc **ON** để đèn trạng thái chuyển sang màu Xanh lá.

---

### Bước 5: Khởi Chạy Giao Diện Web Studio & Sử Dụng Qua AI Agent

1. **Khởi chạy Web Studio (`Lê Việt Tùng - SkillAutoVeo`):**
   ```powershell
   python -u server.py --port 8456
   ```
   *(Hoặc nhấp đúp vào file `Chay_Skill_Web.bat`)*
   Giao diện Web Studio sẽ mở tại: **`http://127.0.0.1:8456`**

2. **Các câu lệnh AI Agent sử dụng hằng ngày để tạo Video cho khách hàng:**
   - **Tự động Crawl sản phẩm từ Link/ID TikTok + Sinh kịch bản + Render 6 Video Final (theo Template Nhà Xưởng):**
     ```powershell
     python veo_skill_cli.py create-video --url "https://shop.tiktok.com/vn/pdp/1738086213622335480" --template nha_xuong --videos-per-char 3 --workers 3
     ```
   - **Chỉ Crawl thông tin & bộ ảnh sản phẩm TikTok (Cách 1 API tự động chuyển Cách 2 Browser + giải Captcha BoxPhone):**
     ```powershell
     python veo_skill_cli.py crawl-product --url "https://vt.tiktok.com/ZS..." --method auto
     ```
   - **Cài đặt số lượng video trên mỗi nhân vật / sản phẩm:**
     ```powershell
     python veo_skill_cli.py set-videos-per-char --count 3
     ```
   - **Tạo ảnh Character Sheet 6 góc hoặc ảnh Nhân vật cầm sản phẩm (Nano Banana 2K / ChatGPT Image):**
     ```powershell
     python veo_skill_cli.py gen-char-image --mode character_sheet --model nano_banana --template sheet_6_views_standard --appearance "young Vietnamese woman, long black hair, factory supervisor vest"
     ```

---

## 📞 THÔNG TIN LIÊN HỆ & HỖ TRỢ BẢN QUYỀN

- **Tác giả:** **Lê Việt Tùng - SkillAutoVeo**
- **Zalo:** [0915967790](https://zalo.me/0915967790)
- **Facebook:** [https://www.facebook.com/tungbinh.38/](https://www.facebook.com/tungbinh.38/)

