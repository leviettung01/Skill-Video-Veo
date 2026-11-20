# Nhật Ký Cập Nhật & Nâng Cấp Hệ Thống (`Skill Video Veo`)

Tài liệu này tổng hợp đầy đủ các nâng cấp về **kiến trúc Request + Extension reCAPTCHA**, **tối ưu đa luồng & phần cứng**, **Template 006 (Biến hình / Omni 1.1 Flash)** và **hệ thống phân loại – xử lý lỗi Google Flow / Google Vids** vừa được triển khai và kiểm thử.

---

## 1. Kiến trúc Request-Only + Token/Cookie Đa Tài Khoản + Extension Giải reCAPTCHA

### Mục tiêu thiết kế
- Tách biệt hoàn toàn **tài khoản Google Flow tạo video/ảnh** (quản lý bằng cookies/token theo từng profile Chrome) khỏi **Extension giải reCAPTCHA** (chỉ đóng vai trò pool mint token reCAPTCHA độc lập, không cần đăng nhập từng tài khoản Flow vào trình duyệt chạy ẩn).
- Toàn bộ request tạo ảnh/video (`maseQ`, `ogiZ0b`, `Z9cAtf`, `YhhmEf`, `eb1hJf`, `MZZa6b`, `as29s`) gửi trực tiếp qua HTTP, hỗ trợ chạy song song nhiều tài khoản cùng lúc.

### Thay đổi chính
- **Extension `LeVietTung_autoveo` (v2.3.0)** — [`Extension Recapcha/LeVietTung_autoveo/`](Extension%20Recapcha/LeVietTung_autoveo/manifest.json):
  - **Tab Pool Song Song (`background.js`)**: Tự duy trì nhóm tab giải reCAPTCHA trên Google Flow (`DEFAULT_FLOW_POOL_TARGET = 4`, co giãn động `2..8` tab qua `CaptchaBridge.apply_concurrency_settings()`), phân bổ vào các tab rảnh nhất (`acquireFlowTab`).
  - **Làm sạch dấu vết & xoay phiên chống tụt trust (`background.js`)**:
    - `clearTabRecaptchaStorage()`: xóa các khóa `_grecaptcha`, `grecaptcha`, `rc::` trong `localStorage` và `sessionStorage`.
    - `clearRecaptchaCookieAnchor()`: dọn cookie anchor reCAPTCHA.
    - `rotateTabSession()`: chủ động xoay URL tab định kỳ sau mỗi `PROACTIVE_ROTATE_EVERY = 8` lần mint token.
    - `nudgeWindowGeometry()`: thay đổi nhẹ kích thước/vị trí cửa sổ chạy nền (`width`, `height`, `left`, `top`) khi tab không focus.
  - **Chống token trùng & cách ly tab lỗi (`background.js`)**: Lưu tập `recentIssuedTokens` để loại bỏ `DUPLICATE_TOKEN` / `INVALID_TOKEN_LENGTH`; đẩy tab lỗi vào `tabCooldownUntil` (`TAB_COOLDOWN_MS = 20_000`) và tự xoay phiên mới.
  - **Gộp yêu cầu Reset (`_runCoalescedReset`)**: Khi nhiều luồng báo lỗi cùng lúc, các lệnh `soft_reset` / `hard_reset` được gộp thành một lượt reset duy nhất thay vì reset dồn dập.
- **Cầu nối HTTP & Tự động làm mới Token/Session**:
  - `fetch_flow_wiz_http()` trong [`grok_video_tool.py`](grok_video_tool.py): lấy `WIZ_global_data` (`SNlM0e`, `cfb2h`, `FdrFJe`) qua HTTP (`curl_cffi`, `impersonate="chrome131"`) trực tiếp từ cookie của tài khoản mà không phải mở Chrome ẩn cho mỗi request.
  - `CaptchaBridge` trong [`grok_video_tool.py`](grok_video_tool.py): điều phối nhịp cấp reCAPTCHA theo từng tài khoản (`request_recaptcha_for_account`, `_reserve_account_dispatch_time`), kết hợp khóa chống reset liên hoàn `MIN_RESET_COOLDOWN_SEC = 20.0` cho `notify_failure()` và `notify_recaptcha_score_dead()`.
  - `GoogleTokenRefreshWorker` + các endpoint `/api/flow/token_manager_status`, `/api/flow/token_manager_toggle`, `/api/flow/extract_session`, `/api/accounts/refresh-google`, `/api/accounts/sync-google-profiles` trong [`server.py`](server.py): quản lý và làm mới token/session theo từng profile (kèm `_AUTO_REFRESH_COOLDOWN` tránh refresh dồn dập).

---

## 2. Tối Ưu Đa Luồng Song Song & Cấu Hình Tự Động / Tùy Chỉnh (`Optimal` / `Max` / `Custom`)

### Tính toán công suất tự động (`engine_settings_manager.py`)
Trong [`flow_final_pipeline/scripts/engine_settings_manager.py`](flow_final_pipeline/scripts/engine_settings_manager.py), thêm `compute_flow_concurrency_profile()` và `get_effective_flow_concurrency()` tính toán thông số chạy đồng bộ cho mọi engine dựa trên số tài khoản Flow hợp lệ (`A`) và số tab Extension sẵn sàng (`T`):

| Chế độ (`flow_concurrency_mode`) | Đặc tính | Delay / 1 TK (`submit_delay_sec`) | Inflight / TK | Trần tổng Inflight | Worker gửi API (`flow_api_workers`) |
| --- | --- | --- | --- | --- | --- |
| **`optimal`** *(Mặc định)* | Nhanh vừa đủ, hạn chế 429 & giữ điểm reCAPTCHA | `5.0s` (1 TK) · `4.5s` (2–3 TK) · `4.0s` (≥4 TK) | `4–5` | Tối đa `80` (`A × per_acc`) | Tối đa `24` |
| **`max`** | Tốc độ tối đa trước ngưỡng siết tần suất | `2.5s` (1 TK) · `2.0s` (≥2 TK) | `7–8` | Tối đa `120` (`A × per_acc`) | Tối đa `36` |
| **`custom`** | Tùy chỉnh tay từng thông số trên Web UI | `1.0s – 60.0s` | `1 – 20` | `1 – 120` | `1 – 40` |

Các tham số cấu hình đầy đủ trong `DEFAULT_ENGINE_SETTINGS`:
- `flow_concurrency_mode`, `auto_flow_concurrency`, `multi_account_enabled`
- `flow_api_workers`, `max_inflight_per_account`, `max_total_inflight`
- `submit_delay_sec`, `global_submit_stagger_sec`, `parallel_products`
- `upscale_download_workers`, `extension_pool_tabs`

### Tách luồng tải/upscale 1080p để không chặn request tạo mới
- Trong [`flow_final_pipeline/scripts/run_all_7_videos_mt.py`](flow_final_pipeline/scripts/run_all_7_videos_mt.py): tách rõ giới hạn `MAX_INFLIGHT` (tạo mới 720p/ảnh) và `UPSCALE_DL_WORKERS` (upscale/tải `1080p`), đồng thời mở rộng `poll_pool` (`max(16, MAX_INFLIGHT + UPSCALE_DL_WORKERS)`). Khi luồng `1080p` đang chờ tải, các slot tạo mới vẫn tiếp tục gửi request song song và ngược lại.
- Đồng bộ cấu hình `get_effective_flow_concurrency()` sang [`veo_skill_cli.py`](veo_skill_cli.py), [`transform_engine.py`](flow_final_pipeline/scripts/transform_engine.py), [`cooking_storyboard_engine.py`](flow_final_pipeline/scripts/cooking_storyboard_engine.py), [`flow_workflow_engine.py`](flow_final_pipeline/scripts/flow_workflow_engine.py).
- **Web UI** — [`static/index.html`](static/index.html): bổ sung bảng chọn `optimal` / `max` / `custom`, hiển thị live số tab Extension sẵn sàng (`ready_tabs`), ước lượng tốc độ `token/phút` và thông số chi tiết từng chế độ.

---

## 3. Cập Nhật Template #006 (Biến Hình Thời Trang — Làm Nông & Bán Cá)

Trong [`flow_final_pipeline/scripts/transform_engine.py`](flow_final_pipeline/scripts/transform_engine.py):
- **Model mặc định chuyển sang `Omni 1.1 Flash`** (`DEFAULT_VIDEO_MODEL = "Omni 1.1 Flash"`, hỗ trợ thêm `Omni Flash` và `Omni 1.2 Flash`) thay cho Veo 3.1 Fast.
- **Tối ưu Prompt Phân Cảnh 1 (Preset `fish` — Bán cá)**:
  - Chia nhịp khóa thời gian chặt chẽ: `0.0s–3.0s` đánh vảy cá thầm lặng → `3.0s–5.4s` cắt cảnh sang đôi nam nữ cũ đưa thiệp & chỉ một mình nhân vật nam thoại câu `"Tháng sau bọn anh cưới, rảnh thì qua chung vui nhé."` (nữ bên cạnh giữ im lặng) → `5.4s–6.4s` cận mặt nữ bán cá rưng rưng ngậm miệng → `6.4s–7.0s` đưa lòng bàn tay đeo găng cao su hồng khép kín 4 ngón áp sát che `100%` ống kính.
- **Tối ưu Prompt Phân Cảnh 2 (Preset `fish` — Biến hình VIP & Xế hộp)**:
  - Khóa tỷ lệ thực tế cho xe **Mercedes-Maybach S-Class** cỡ lớn (~5.4m dài, nóc xe ~1.50m ngang tầm mắt/cằm người đứng cạnh), đặt nhân vật chính đứng phía trước cửa xe mở (~1.5m tách biệt trên lối đi đá hoa cương bằng phẳng, không chồng lấn thân xe).
  - Bổ sung ràng buộc vật lý cho 4 vệ sĩ mặc vest đen đầy đủ tiến vào từ hai trụ đá ngoài rìa, **tuyệt đối không đi xuyên thân xe, cửa xe hay nóc xe**.
- **Hậu kỳ FFmpeg chuẩn hóa hình – tiếng (`_detect_occlusion_peak`, `_detect_fish_scene_cuts`, `_build_scene1_video_filter`, `_build_audio_spec`, `export`)**:
  - Tự động phát hiện đúng hai điểm chuyển cảnh và căn thời điểm khớp thoại với audio gốc của `02_ban_ca.mp4` để lời thoại khớp hình hoàn toàn trước khi cắt sang điệp khúc tại mốc `8.0s` (khắc phục lỗi thoại bị trễ sang cảnh sau).
  - Siết điều kiện cắt che ống kính (`min_y < 36.0`, `min_dark >= 0.72`, `tail_y - min_y >= 22.0`) để tránh nhận nhầm cảnh cận mặt tối hoặc găng tay sáng màu gây kéo giãn slow-motion, kết hợp zoom ép kín lòng bàn tay và đóng đen sạch tại `7.76s`.

---

## 4. Hệ Thống Phân Loại Lỗi Toàn Cục & Xử Lý Lỗi Nội Dung Không Hợp Lệ (Google Flow / Google Vids)

### 4.1. Phân loại lỗi chuẩn 6 nhóm & Sổ cái Cooldown dùng chung
Trong [`grok_video_tool.py`](grok_video_tool.py):
- `classify_flow_error()` phân chia rạch ròi mọi lỗi từ API thành 6 nhóm hành động:
  1. `content_policy`: Lỗi nội dung / chính sách an toàn / tham số không hợp lệ (`HTTP 400`, `INVALID_ARGUMENT`, `PUBLIC_ERROR_UNSAFE_GENERATION`, `PUBLIC_ERROR_MINOR_UPLOAD`, `PUBLIC_ERROR_AUDIO_FILTERED`, `PUBLIC_ERROR_PROMINENT_PEOPLE_FILTER_FAILED`, `POLICY_VIOLATION`, `SAFETY_ERROR`, `GENERATION_FAILED`, mã render `as29s` `code=3..8` không phải `INTERNAL`).
  2. `account_quota`: Hết credit / quota ngày / không có quyền model (`USER_QUOTA_REACHED`, `CREDITS_EXHAUSTED`, `MODEL_ACCESS_DENIED`) -> cooldown mặc định `900s`.
  3. `account_auth`: Hết hạn cookie / token / 401 / thiếu `SNlM0e` / `CookieMismatch` -> cooldown mặc định `180s`.
  4. `rate_limit`: `HTTP 429` / `RESOURCE_EXHAUSTED` / `HIGH_TRAFFIC` / `THROTTLED` -> cooldown mặc định `120s`.
  5. `captcha_score`: `PUBLIC_ERROR_UNUSUAL_ACTIVITY` / `RECAPTCHA` / `CAPTCHA_TIMEOUT` / `NO_FLOW_TAB` -> cooldown mặc định `45s`.
  6. `transient`: Lỗi mạng / HTTP `5xx` / `PUBLIC_ERROR_INTERNAL` / `UNAVAILABLE` / timeout -> cooldown mặc định `15s`.
- **Cooldown toàn cục (`_FLOW_ACCOUNT_COOLDOWNS`)**: Dùng chung giữa các engine qua `mark_flow_account_cooldown()`, `clear_flow_account_cooldown()`, `is_flow_account_in_cooldown()`, `sort_flow_candidates_by_health()` — tài khoản khỏe luôn được xếp lên đầu, tài khoản hồi phục hoặc chạy thành công sẽ tự được gỡ cooldown ngay.
- **CDN Micro-Retry (`_cdn_get_with_retry`)**: Tự động thử lại tối đa `3` lần khi tải ảnh/video từ Google CDN gặp rớt gói hoặc HTTP `5xx`.

### 4.2. Bắt lỗi từ chối nội dung (`as29s` / RPC / Vids) & Tự làm dịu an toàn 1 lần
- **Trích xuất sâu lỗi render `as29s` (`extract_flow_as29s_error`)**:
  - Quét đầy đủ các vị trí Google Flow ẩn mã trạng thái (`inner_p[5][8][0]`, `inner_p[0][0][5][8][0]`, `inner_p[0][0][3]`, `inner_p[5][7][0]`) và phát hiện mọi token `PUBLIC_ERROR_*`, `POLICY_VIOLATION`, `SAFETY_ERROR`, `SAFETY_FILTER`, `GENERATION_FAILED`, `INVALID_ARGUMENT`, `REJECTED`, `PROHIBITED` (kể cả khi `inner_p[5][7]` rỗng).
  - Nâng cấp `_parse_batchexecute_wrb()` để giữ cả chuỗi mô tả đọc được từ `wrb.fr` / `er` kèm payload gốc.
  - Chuẩn hóa thứ tự ưu tiên trong `classify_flow_error()` để log tiếng Việt (như *"Google Flow từ chối tạo video: HTTP 429..."*) không che lấp lỗi `rate_limit`/`account_quota`/`account_auth`/`captcha_score`, đồng thời giữ `PUBLIC_ERROR_INTERNAL`/`UNAVAILABLE` ở nhóm `transient`.
- **Phân nhánh chi tiết 8 loại từ chối & Diễn giải tiếng Việt**:
  - `classify_content_rejection_subtype()`: phân biệt `minor_upload`, `prominent_people`, `audio_filtered`, `sexual_safety`, `violence_danger`, `copyright_ip`, `invalid_input`, `unsafe_generation`.
  - `describe_flow_error_vi()`: trả thông báo tiếng Việt rõ nguyên nhân và gợi ý chỉnh sửa (giữ nguyên mã `[PUBLIC_ERROR_...]` / `code=...`) để hiển thị trực tiếp lên Web UI (`job.error`, `status_detail`, `error_msg`).
- **Tự làm dịu prompt an toàn tối đa 1 lần (`sanitize_prompt_for_flow_policy`)**:
  - Tự động chuyển ngữ các từ nhạy cảm dễ gây nhầm (ví dụ từ khóa dao/bếp, máu/sắc đỏ, bikini/trang phục, girl/boy/tuổi tác, tên thương hiệu, câu thoại gắt...) và thêm ngữ cảnh studio thương mại an toàn khi bị chặn ở bước tạo ảnh/video.
  - **Thử lại tối đa 1 lần trên CÙNG tài khoản**:
    - Nếu thành công -> đi tiếp bình thường.
    - Nếu vẫn bị chặn, hoặc lỗi xảy ra ngay khi **upload ảnh gốc `maseQ`** (như `PUBLIC_ERROR_MINOR_UPLOAD` do pixel ảnh), hoặc lỗi **`invalid_input` (HTTP 400)** -> **dừng ngay lập tức**, **không xoay sang tài khoản khác** và **không gắn cooldown oan cho pool tài khoản**.
  - Ở `_run_veo_flow_batchexecute`, khi `ogiZ0b` bị từ chối vì `content_policy`, `account_quota`, `account_auth` hoặc `rate_limit` thì không gọi nối tiếp sang `Z9cAtf` tránh lãng phí reCAPTCHA token.

### Danh sách file engine đã áp dụng đồng bộ
- [`grok_video_tool.py`](grok_video_tool.py)
- [`flow_final_pipeline/scripts/fashion_motion_control_engine.py`](flow_final_pipeline/scripts/fashion_motion_control_engine.py) *(vá đồng thời `NameError: gvt` ở `_mark_flow_profile_unhealthy` / `_mark_flow_profile_healthy` / `_is_flow_profile_unhealthy` và chặn xoay profile khi gặp `content_policy`)*
- [`flow_final_pipeline/scripts/run_all_7_videos_mt.py`](flow_final_pipeline/scripts/run_all_7_videos_mt.py)
- [`flow_final_pipeline/scripts/google_vids_client.py`](flow_final_pipeline/scripts/google_vids_client.py) *(tách xử lý HTTP `400` / safety filter rỗng URL khỏi `401/403` auth, chỉ thử làm dịu 1 lần trên cùng profile trước khi dừng cả pool)*
- [`veo_skill_cli.py`](veo_skill_cli.py)
- [`flow_final_pipeline/scripts/transform_engine.py`](flow_final_pipeline/scripts/transform_engine.py)
- [`flow_final_pipeline/scripts/cooking_storyboard_engine.py`](flow_final_pipeline/scripts/cooking_storyboard_engine.py)
- [`flow_final_pipeline/scripts/flow_workflow_engine.py`](flow_final_pipeline/scripts/flow_workflow_engine.py)

---

## 5. Khôi Phục & Tự Động Vá Web UI (`static/index.html` + `server.py`)

- **Nguyên nhân giao diện đứng/không bấm được**: Phần cuối file [`static/index.html`](static/index.html) từng bị bản nháp chưa lưu trong editor cắt cụt (`...[truncated for diff preview]`), làm thiếu thẻ đóng `</script>` và toàn bộ các thẻ `<script src="...">` phía dưới (`studio_app_part2.js`, `cooking_studio.js`, `template_explorer.js`, `workflow_studio.js`). Do đó toàn bộ JavaScript khởi tạo giao diện (`STATE`, `switchTab`, nút điều hướng...) bị lỗi cú pháp và không thực thi khi mở trình duyệt.
- **Khắc phục**:
  - Khôi phục đầy đủ phần đuôi hàm điều phối (`runProjectBatch`, `deleteProject`, `openFolder`, `pickFolderFromComputer`, `openFolderEncoded`, `openFileEncoded`) kèm thẻ đóng `</script>`, CSS và toàn bộ script mô-đun ở cuối [`static/index.html`](static/index.html).
  - Bổ sung sẵn `<script src="/static/transform_studio.js?v=20261115_1"></script>` ngay lúc tải trang để `window.openTransformStudio` sẵn sàng tức thì khi mở Template #006 (`modalTransformStudio`).
  - Bổ sung cơ chế tự phục hồi `_load_valid_index_html()` trong [`server.py`](server.py) kết hợp file dự phòng [`static/_index_tail_recovery.html`](static/_index_tail_recovery.html): mỗi khi khởi động server hoặc phục vụ `/` (`/index.html`), nếu phát hiện `static/index.html` bị cắt cụt hay thiếu `</html>`, server tự động ghép phần đuôi chuẩn, ghi lại file sạch và trả HTML đầy đủ cho trình duyệt.

---

## 6. Kiểm Thử & Xác Minh Thực Tế

- **Unit Test Suite** — [`tests/test_transform_and_flow_tier2.py`](tests/test_transform_and_flow_tier2.py) và toàn bộ thư mục `tests/`:
  - Chạy `python -m unittest discover -s tests -v`: **`92/92 tests passed (OK)`** trong `51.147s` (0 lỗi, 0 skip).
  - Kiểm tra cú pháp `python -m py_compile` cho `server.py` và kiểm toán phát hành `python audit_release.py` (`69` file Python, `0` lỗi cú pháp, `0` API thiếu).
  - Kiểm tra cú pháp JavaScript (`node --check`) cho tất cả file JS trong dự án và block inline của [`static/index.html`](static/index.html): **0 lỗi**.
- **Kiểm thử giao diện thực tế bằng Playwright Chromium trên `http://127.0.0.1:8456/`**:
  - Nạp đủ dữ liệu thực: `DỰ ÁN STUDIO (48 dự án)`, `Tài khoản: 5/5`.
  - `STATE`, `switchTab`, `renderFlowConcurrencySummary`, `window.openTransformStudio`, `window.openCookingStudio` khởi tạo đầy đủ.
  - Bấm chuyển qua toàn bộ 9 tab điều hướng chính (`dashboard`, `fashion`, `workflow`, `products`, `templates`, `characters`, `accounts`, `settings`, `matrix`), kiểm tra bảng chọn cấu hình đa luồng `#selFlowConcurrencyMode` (`optimal`, `5` TK Flow, `6` tab Extension) và mở modal Template #006 `#modalTransformStudio`: **0 `pageerror`**, **0 `console.error`**, **0 lỗi HTTP API/static**.
