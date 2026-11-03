# RENDER VIDEO FINAL — Nối cảnh + Subtitle + Overlay

## Chuẩn final

- 720×1280, h264 + aac, 30s (3 cảnh × 10s), faststart.
- Subtitle: **đúng 1 dòng**, VIẾT HOA, trắng trước khi đọc → vàng nhạt `#FFE066` tức thì khi đọc tới (`\k`, không quét gradient), fade vào/ra 150ms, viền đen, dưới giữa MarginV 150, font DejaVu Sans Bold 32px.
- Mỗi câu subtitle ≤ 28 ký tự (đo thật ≤ 587px trong khung 720px).
- 7s cuối: **3 ảnh sản phẩm gốc** (không tự vẽ) hiển thị **nối tiếp**, mỗi ảnh ~2,33s, 260×260, góc trên trái (x=20, y=20), không che mặt và subtitle.

## Quy trình ffmpeg (1 lệnh)

Dùng **concat filter** (không dùng concat demuxer — vỡ với clip 24fps mới):

```
[0:v][1:v][2:v]concat=n=3:v=1:a=0[vcat];
[0:a][1:a][2:a]concat=n=3:v=0:a=1[acat];
[vcat]ass='final.ass'[vsub];
[3:v]scale=260:260[ov1]; [4:v]scale=260:260[ov2]; [5:v]scale=260:260[ov3];
[vsub][ov1]overlay=20:20:enable='between(t,23,25.34)'[v1];
[v1][ov2]overlay=20:20:enable='between(t,25.34,27.67)'[v2];
[v2][ov3]overlay=20:20:enable='between(t,27.67,30)'[vout]
```

Audio re-encode AAC 128k. Xem `scripts/build_final.py` — script tự động toàn bộ.

## Cách dùng build_final.py

Chuẩn bị file spec JSON cho 1 video final:

```json
{
  "scenes": [
    {"file": "s1.mp4", "words": 46,
     "phrases": [["CÁI NÀY LÀ CHO CÁC BÁC NÀY.", 7],
                 ["TIKTOK NGƯỜI TA CHO", 3]]},
    {"file": "s2.mp4", "words": 47, "phrases": [...]},
    {"file": "s3.mp4", "words": 45, "phrases": [...]}
  ],
  "overlays": ["ref1.webp", "ref2.webp", "ref3.webp"],
  "output": "1738...-nv2-v1-final-30s.mp4"
}
```

- `words`: tổng số từ NÓI của cảnh (số đã đọc thành chữ, dùng chia thời gian đều).
- `phrases`: từng câu subtitle [TEXT VIẾT HOA ≤28 ký tự, số từ nói trong câu].
- Script sinh file `.ass` (karaoke `\k` chia đều theo từ), chạy ffmpeg, kiểm tra đầu ra 720×1280.

```bash
python3 scripts/build_final.py spec-nv2-v1.json
```

## Chia câu subtitle

- Tách thoại thành nhiều câu ngắn, mỗi câu là 1 dòng subtitle duy nhất.
- Số trong subtitle giữ nguyên dạng chữ số ("200", "100K") cho gọn; thời gian chia theo số từ NÓI (số đã đọc thành chữ).
- Thời gian mỗi câu = (số từ nói của câu / tổng từ nói của cảnh) × 10s, cộng dồn từ đầu cảnh.

## Kiểm tra sau render (nhanh, không whisper ở chế độ full luồng)

- `ffprobe`: 720×1280, h264 + aac, ~30s.
- Xem 3 frame (giữa mỗi cảnh): đúng nhân vật, đúng sản phẩm, subtitle 1 dòng hiện đúng, overlay 3 ảnh hiện ở 7s cuối.
- Không xóa clip khỏi dự án Flow trong mọi trường hợp.
