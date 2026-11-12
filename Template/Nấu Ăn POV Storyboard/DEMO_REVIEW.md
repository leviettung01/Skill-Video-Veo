# Demo Template #005

Demo thực tế: lẩu Thái tôm nấm, 3 clip, tổng 23.808 giây; 1080×1920, 60 fps, có âm thanh nấu ăn.

- Ba storyboard 2 cột × 3 hàng được tải native 2K (1536×2752), sau đó upload lại. UUID, kích thước và hash được ghi trong `projects/pov_cooking_demo_20261110/cooking_manifest.json`.
- Đã tạo đúng 3 job video. Lỗi 401 khi đọc trạng thái được xử lý bằng cookie đúng phạm vi rồi tiếp tục job đã lưu, không gửi lại yêu cầu tạo video.
- Đã xem sáu mốc hình mỗi clip: các bước nấu xuất hiện toàn màn hình theo thứ tự, không xuất lưới storyboard trong video. Chi tiết tay/dụng cụ vẫn có thể được mô hình diễn giải khác nhẹ giữa các shot.
- FFmpeg giải mã toàn bộ final thành công. Sáu kiểm thử offline đều đạt; kiểm thử dùng mock, không tiêu credit.
- Giao diện Chợ Template hiển thị #005, mở được studio riêng, ba storyboard/clip và final. Nút tạo video bị khóa trước khi có ref và xác nhận đã xem storyboard. Đã kiểm tra phát final tới hết.

Sử dụng: Chợ Template → #005 → Dùng Template → tạo dự án từ công thức → tạo storyboard 2K & upload lại → xem ảnh và đánh dấu đã kiểm tra → tạo video & ghép final.

Demo có sẵn: chọn “Mở demo đã hoàn tất”; không cần tạo lại để xem.
