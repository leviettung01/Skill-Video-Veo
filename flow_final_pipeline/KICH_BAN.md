# KỊCH BẢN — Công thức kho mẫu (11 kịch bản user duyệt 2026-11-01)

## 1. Ba kiểu hook mở đầu

**Hook A — "Cho / trợ giá"** (dùng cho V1):
> Cái này là cho các bác này. Cái này là TikTok người ta cho, chứ không phải là bán nữa rồi các bác ạ. Nguyên [mô tả ngắn sản phẩm] này đang được trợ giá cực rẻ.

**Hook B — "Cam kết sốc"** (chỉ dùng khi user yêu cầu riêng):
> Em sẽ làm con chó ăn cứt cho cả họ nhà các bác… Riêng em có sao nói vậy. Hàng tốt thì nói tốt, rẻ thì mình nói rẻ thôi.

**Hook C — "Giá sốc + bái phục"** (dùng cho V2):
> [GIÁ]K cho nguyên [sản phẩm] này các bác ơi. Ở đâu bán cái giá đó thì em cũng đến bái phục luôn, chứ tận xưởng cũng không thể nào rẻ như vậy được. Hôm nay kênh em được trợ giá rất rẻ luôn.

## 2. Khung thân bài (dùng chung)

1. **Thang giá đi xuống**: "Giá không phải là [X] đâu, không phải là [Y], … [Z]K cũng không luôn."
2. **Giá theo tài khoản**: "Mà mỗi tài khoản các bác sẽ thấy một giá khác nhau nha." / "Mỗi tài khoản một giá khác nhau nha."
3. **CTA giỏ hàng**: "Các bác bấm giỏ hàng góc trái, nếu thấy giá dưới [Z]K thì săn liền giúp em ạ."
4. **Khan hiếm** (1 câu): "Ưu đãi chớp nhoáng hôm nay thôi, hết là về giá gốc đó ạ."
5. **Mô tả sản phẩm**: chất liệu + tính năng thật → công dụng/đối tượng → câu chốt.

## 3. Luật giá (user chốt)

KHÔNG bao giờ khẳng định giá cố định. Không viết "giá là …", "chỉ …K", "giảm còn …K".
Luôn: thang giá đi xuống → chốt "mỗi tài khoản một giá". Câu điều kiện "nếu thấy giá dưới [Z]K" được phép (phụ thuộc giá user tự thấy).
Hook C được mở bằng [GIÁ]K theo đúng công thức mẫu (giá lấy từ dữ liệu xác minh, không bịa).

## 4. Cân độ dài theo giọng (QUAN TRỌNG)

| Giọng | Tốc độ đo được | Số từ/cảnh 10s |
|-------|----------------|----------------|
| Giọng thường (NV1 cũ, giọng Bắc chuẩn) | ~3 từ/giây | 28–32 từ |
| Giọng nhanh năng lượng (NV2 mới) | ~4,7 từ/giây | 44–48 từ |

**Cách đếm**: đếm theo khoảng trắng trên văn bản, nhưng số phải đọc thành chữ:
- 89K → "tám mươi chín nghìn" = 4 từ
- 200 → "hai trăm" = 2 từ; 150 → "một trăm năm mươi" = 4 từ; 100K → "một trăm nghìn" = 3 từ
- 10kg → "mười ki lô gam" = 4 từ; 25K → "hai mươi lăm nghìn" = 4 từ
- 2-3 ngày → "hai đến ba ngày" = 4 từ

**Bài học xương máu**: đã từng gửi prompt cảnh 61 từ/10s (quá ~30%) → voice chắc chắn hỏng. LUÔN đếm tổng từ mỗi cảnh trước khi gửi, giữ trong 44–48.

## 5. Voice TIMELINE (chống lặp voice)

Không dùng câu "đừng lặp lại" — vô ích khi thoại ngắn hơn clip. Chia thoại thành 3 đoạn gắn mốc thời gian, tỉ lệ theo số từ từng đoạn:

```
TIMELINE — read evenly, each segment exactly in its window, final word lands at 10.0s:
[0.0-3.6s] ...đoạn 1 (~17 từ)...
[3.6-7.2s] ...đoạn 2 (~17 từ)...
[7.2-10.0s] ...đoạn 3 (~10-14 từ)...
```

Kèm chỉ dẫn: "Read exactly these words once, no adding, no repeating, no inventing; when finished, smile and hold the product still." + ghi tốc độ đọc đo được ("speaking rate about 4.7 words per second").

Khóa danh tính trong prompt NGẮN GỌN 1–2 dòng (same woman, identical face, no glasses) — đoạn khóa dài có thể ảnh hưởng voice.

## 6. Cấu trúc 3 cảnh chuẩn (30s)

- **Cảnh 1**: Hook (A hoặc C) + giới thiệu sản phẩm đang được trợ giá.
- **Cảnh 2**: Thang giá + giá theo tài khoản + CTA giỏ hàng.
- **Cảnh 3**: Mô tả tính năng thật + khan hiếm + câu chốt.

Hành động mỗi cảnh đơn giản, đúng loại sản phẩm (giơ sản phẩm, đưa chi tiết lại gần camera, demo thao tác 1 chạm). Trạng thái cuối cảnh này = trạng thái đầu cảnh sau.

## 7. Câu cửa miệng đặc trưng (rắc vừa phải)

xịn sò · siêu hot · săn liền, săn lẹ · cực kỳ rẻ · các bác ơi/ạ · nha/nhá · "có sao nói vậy" · chốt ngay
