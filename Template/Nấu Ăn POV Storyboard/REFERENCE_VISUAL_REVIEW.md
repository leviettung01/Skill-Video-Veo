# Đối chiếu video người dùng — 10/11/2026

Nguồn: `C:/Users/ADMIN/Downloads/FDown.vn_Tai_video_Facebook_1080p_4c68.mp4`, 24.22 giây. Đã kiểm tra hình toàn video theo mốc 1 giây và đoạn demo từ 15 giây theo mốc 0.25 giây. Đây là video quay màn hình, không phải file render gốc; không suy luận được chất lượng render, tiêu cự hay thông số màu thực tế. Nhận xét dưới đây về hình và chuỗi hành động, không đánh giá âm thanh.

## Những điểm cần sửa từ demo đầu

| Yếu tố | Bản tham khảo quan sát được | Demo đầu của tool | Hướng sửa |
|---|---|---|---|
| Khung hình | Phần lớn là lòng nồi và hành động; thành nồi bị cắt, nền chỉ là dải nhỏ | Nhiều shot nhìn cả nồi, tay cầm, bếp đen và bàn | Khóa crop ngay trong từng ô storyboard, không đợi video tự zoom |
| Góc máy | Cận cao khi thả nguyên liệu, thấp hơn khi gắp đồ ăn; không đổi góc vô cớ | Góc cao lặp lại; công thức góc máy tính bằng số shot không phục vụ hành động | Chọn góc theo điểm tiếp xúc và hướng chuyển động |
| Nước lẩu | Đỏ cam đậm, vân dầu, phản sáng bóng, bọt sôi rõ | Nước khá nhạt, nhiều vùng phẳng | Mô tả lớp màu, vân dầu và bọt cụ thể; giữ nồi kem trung tính để màu món nổi |
| Dụng cụ | Bát kính nhìn thấy nguyên liệu trước khi đổ; đũa và thìa gỗ | Chai dầu, tay thả từng miếng, thêm muôi kim loại | Dùng một bộ dụng cụ có mục đích; ghi rõ công cụ nào cho từng shot |
| Hành động | Rót thành dòng, nghiêng bát, nguyên liệu rơi, khuấy tạo xoáy, gắp nâng lên | Mô tả hành động nhưng nhiều ô giống ảnh sau thao tác | Mỗi ô thể hiện giữa thao tác; prompt video có bắt đầu → chuyển động → điểm kết thúc |
| Kết | Gắp tôm và mực phía trên chính nồi lẩu | Múc sang bát nhỏ, đổi trọng tâm | Giữ hero trong nồi, nâng đồ ăn sát ống kính |

Tại khoảng 10 giây có thể đọc một prompt trên màn hình: sáu shot toàn màn hình, macro 85–100mm look, đồ ăn/hành động chiếm 85–95%, không zoom out; shot đầu là thành phẩm rồi chuyển về dầu và nguyên liệu. Đây là thông tin nguồn tham khảo, không phải bằng chứng model luôn tuân thủ.

## Quy tắc duyệt ảnh trước video

- Xem từng ô như một frame video độc lập: nếu còn thấy cả nồi/bếp rộng thì chưa đạt, dù file đã 2K.
- Khóa cùng kiểu nồi kem, ánh sáng cửa sổ mềm, màu nền trắng/ngà; chỉ vài dụng cụ gỗ mờ ở hậu cảnh. Màu ấm nhẹ, không phủ vàng toàn ảnh.
- Chốt một hành động chính, điểm tiếp xúc, công cụ, trạng thái nguyên liệu và crop cho từng shot.
- Giữ đỏ cà chua, vàng ngô, xanh rau tươi, hồng cam tôm; không tăng saturation toàn cảnh để bù ảnh nhạt.
- Không lấy vùng laptop, bàn phím, mũi tên hay chữ trong video hướng dẫn làm ảnh ref cho video nấu ăn.
- Ảnh crop từ video quay màn hình chỉ đủ tham khảo bố cục/màu; upscale không biến chúng thành ref 2K thật. Storyboard mới vẫn cần tạo rồi tải native 2K và upload lại.
- Nếu dùng cảnh thành phẩm làm hook rồi quay về nồi trống, phải ghi rõ đó là preview + hard cut về đầu quy trình; không để mô hình hiểu là đồ ăn biến mất trong một shot.

Bản prompt thử sửa nằm trong `PROMPT_REVISION_V2.md`. Chưa tạo video mới từ bản sửa này và chưa coi chất lượng hình mới là đã được xác minh.
