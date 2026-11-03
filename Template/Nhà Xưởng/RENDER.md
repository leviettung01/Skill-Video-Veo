# RENDER VIDEO FINAL — TEMPLATE NHÀ XƯỞNG

- **Độ phân giải đầu ra**: `1080×1920` (Full HD 9:16), H.264 + AAC 192k, 30 giây (ghép từ 3 cảnh 10s).
- **Tên file xuất**: `final_videos/{pid}_{nv1/nv2}_v{1/2/3...}.mp4`.
- **Phụ đề Karaoke (`.ass`)**:
  - Đúng 1 dòng tại mỗi thời điểm, chữ IN HOA, font Arial Bold, trắng chuyển vàng `#FFE066` theo nhịp đọc `\k`.
  - Mỗi cụm chữ ≤ 28 ký tự.
- **Hiệu ứng 4 giây cuối (26.0s – 30.0s)**:
  - Làm mờ nhẹ nền video (`boxblur`) và trình chiếu liên tiếp tối đa 5 ảnh sản phẩm gốc chính giữa màn hình (`860×860`, viền trắng + đổ bóng) kèm badge giá/tên sản phẩm nổi bật.
- **Script thực thi**: `flow_final_pipeline/scripts/build_final.py <path_to_spec_vX.json>`.

