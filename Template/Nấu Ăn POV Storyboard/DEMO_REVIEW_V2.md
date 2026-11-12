# Demo V2 đã tạo và kiểm tra

Project: `pov_cooking_v2_20261110`. Final: `final_videos/pov_cooking_v2_20261110_final.mp4`, 22.57 giây, 1080×1920, có audio. Xuất 60fps từ nguồn model 24fps; không phải tạo chuyển động native 60fps.

Master thực thi đã sửa: crop ngay trong storyboard, góc máy theo thao tác, bát kính và điểm tiếp xúc rõ, highlight ngà trung tính, màu món có phân lớp, cảnh kết gắp tôm ngay trên nồi. Thêm câu mở đầu mô tả frame toàn màn hình cụ thể và ràng buộc một tay/một dụng cụ cho dự án mới.

Ba storyboard native 1536×2752 đã được xem và upload lại. Tổng 4 job video trả phí: ba clip chính và một take sửa riêng clip đầu. Take đầu lộ lưới đã được giữ lại làm bằng chứng lỗi; không dùng trong final. Take thay thế mở trực tiếp bằng rót dầu toàn màn hình. Không tạo lại ảnh cho lần sửa clip đầu.

Đã bỏ 1.25s mở đầu clip ba vì thao tác hai cặp đũa đối nhau không đẹp; final cắt từ cảnh ngô/nấm sang thời điểm tôm đã chín. Vì vậy final không còn đủ 18 thao tác như kế hoạch ban đầu. Các source thô và lịch sử UUID vẫn được giữ trong project. File `finalize_reviewed_demo.py` tái tạo lựa chọn take và dựng final, không gọi nhà cung cấp.

Đã xem storyboard, contact sheets các clip, frame đầu take sửa và bản ghép; FFmpeg giải mã toàn bộ final thành công. Bảy kiểm thử offline đạt. Vẫn có diễn giải khác của model về lượng nguyên liệu, độ cao góc máy và dụng cụ giữa shot; không cam kết giống tuyệt đối video tham khảo.

Demo trong Chợ Template #005 đã thay bằng V2; endpoint mở demo trỏ sang project V2. Demo V1 được giữ nguyên ở project cũ.
