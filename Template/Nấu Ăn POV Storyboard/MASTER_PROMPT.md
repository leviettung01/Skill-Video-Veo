# Master prompt V2 — POV cooking

Master thực thi nằm ở `flow_final_pipeline/scripts/cooking_storyboard_engine.py`: `CONTINUITY`, `COMPOSITION`, `shot_direction()` và `build_prompts()`. Mọi dự án mới ghi `master_prompt_version`; không thay prompt/ref của các job cũ đang có.

## Đầu vào

Tên món, trạng thái đầu clip và đúng sáu hành động mỗi clip. Mỗi hành động phải xác định nguyên liệu, công cụ, chuyển động và trạng thái kết thúc. Không bổ sung nguyên liệu ngoài công thức. Chuyển thời gian nấu bằng hard cut có chủ ý, không biến sống thành chín giữa thao tác liên tục.

## Cấu trúc prompt ảnh

1. Một sheet dọc 9:16, sáu ô bằng nhau, 2 cột × 3 hàng, đọc trái sang phải rồi từ trên xuống.
2. Khóa nhận diện nồi ngà, bếp trắng, ánh sáng cửa sổ bên trái, highlight trung tính, màu món có phân lớp, tay và dụng cụ.
3. Mỗi ô ghi hành động và hướng máy theo chức năng: rót → dòng và điểm chạm; thả → quỹ đạo rơi; khuấy → đầu dụng cụ tiếp xúc; sôi → mặt nước; hero → đồ ăn nâng lên gần ống kính.
4. Khóa crop ngay trong ảnh: cắt qua thành nồi, không thấy cả vành nồi/hai tay cầm/toàn bếp. Chủ thể là thức ăn và thao tác, không phải đồ nội thất.
5. Chọn khoảnh khắc giữa thao tác; nhìn thấy nguồn, vật chuyển động và đích. Không dùng ảnh tĩnh sau thao tác để thay ảnh hành động.

## Cấu trúc prompt video

Sáu shot toàn màn hình, mỗi shot khớp ô ảnh và mốc thời gian, hard cut. Bắt đầu đúng thao tác, thực hiện một chuyển động rõ rồi kết khi vật liệu ổn định. Không hiển thị grid từ frame đầu, không orbit/zoom out/morph transition. Giữ trạng thái nguyên liệu qua các shot. Dùng âm thanh nấu ăn đúng thao tác.

## Cổng chất lượng

Xem storyboard native 2K trước khi chạy video. 2K không thay cho kiểm tra crop, màu, trạng thái và hình thể. Upload lại đúng ảnh đã duyệt, lưu UUID và hash. Xem video thực tế trước khi cập nhật demo; không coi job thành công hay xuất 60fps là bằng chứng mỹ thuật đạt.
