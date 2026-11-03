# PROMPT TEMPLATES — TEMPLATE NHÀ XƯỞNG

## 1. Prompt Tạo Ảnh Tham Chiếu 2K (`Nano Banana 2.1 / BELUGA`)

Đính kèm: `[character_id]` + `[1 ảnh sản phẩm đơn chiếc gốc]`.

```text
Photorealistic vertical 9:16 medium-wide standing photo (framed from head to hips, camera at 2 meters distance, NOT a close-up): the exact same woman from the character reference ({char_appearance_en}), {outfit_en}, {setting_en}. She looks directly at the camera with a warm, friendly, confident smile while holding and presenting the exact {product_type_en} from the product reference image in her hands at waist level facing the camera ({product_scale_en}, NOT oversized), with neat retail packaging boxes on the worktable beside her. Keep the product 100% identical as shown in the product reference image (keep all original product details, prints, logos, and true size intact, do not redesign or alter the product in any way), and keep her face identical.
```

---

## 2. Prompt Tạo Video 10s (`Veo 3.1 Omni Flash`)

Đính kèm: `[Ảnh Ref Nhân vật 2K vừa tạo, Ảnh Sản phẩm gốc]` + `[voice_id]`.
Không mô tả lại dài dòng ngoại hình hay bối cảnh để tránh AI tự vẽ lại sản phẩm; khóa chặt giữ nguyên 100% từ ảnh tham chiếu:

```text
A 10-second vertical 9:16 video starting directly from the provided reference image, one continuous medium shot, front-facing camera. Keep the character, the exact product in her hands, the items on the table, and the background 100% unchanged from the reference image — do not alter, redesign, or replace the product's shape, color, pattern, or logo.

ACTION: {scene_action_en}

VOICE — read the dialogue in 3 timed segments exactly as marked. Keep a steady, even pace so each segment fills its time window. Finish the last word exactly at 10.0 seconds. Read each word exactly once — no repetition, no looping, no added words, then stay silent:
[0.0-{t1}s] "{seg1}"
[{t1}-{t2}s] "{seg2}"
[{t2}-10.0s] "{seg3}"

No background music, no watermark.
Negative: changed product, altered product design, repeating voice, looping dialogue, second voice pass, rushed reading, changed face
```

