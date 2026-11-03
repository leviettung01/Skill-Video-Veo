# 🧩 CẤU TRÚC PROMPT: TEMPLATE ĐỒ ĂN VẶT & ĐỒ UỐNG UGC
**Tác giả:** Lê Việt Tùng - SkillAutoVeo (`Zalo: 0915967790`)

---

## 1. Các Khối Cố Định (Fixed Continuity Blocks)

### A. Khối Bối Cảnh 1 — Quầy Tiệm Ăn Vặt Hiện Đại Hà Nội (Mặc Định)
```text
Setting: a bright modern Vietnamese snack shop in Hanoi, large floor-to-ceiling glass storefront windows behind, green trees visible outside, passing motorbikes and cars softly blurred beyond the glass, clean glass display cabinets and neatly arranged product shelves inside, clean light-toned counter in the foreground, soft natural daytime light coming from the left through the glass, gentle realistic reflections on the glass surfaces, premium tidy warm inviting atmosphere. Vertical 9:16 realistic commercial UGC style.
```

### B. Khối Bối Cảnh 2 — Góc Bàn Học Gen Z Bên Cửa Sổ (Tuỳ Chọn Cho Đồ Uống / Topping)
```text
Setting: a cozy Gen Z study desk by a large apartment window, warm natural afternoon sunlight streaming through sheer white curtains from the left, an iPad placed on an acrylic stand playing a colorful classic Japanese cartoon, a minimalist white mechanical keyboard, pastel wireless mouse, aesthetic desk mat, small desk lamp turned on, neatly stacked notebooks and colorful highlighters, indoor plants adding fresh greenery, clean Scandinavian-inspired bedroom workspace, soft realistic lighting, cozy productive study atmosphere. Vertical 9:16 realistic commercial UGC style.
```

### C. Khối Bàn Tay Cố Định (Fixed Hand Block)
```text
a feminine hand with a glossy white glitter manicure, elegant natural pose
```

---

## 2. Mẫu `image_prompt` Chuẩn (Tạo Ảnh Tĩnh 9:16 Từ Ảnh Sản Phẩm Gốc)

```text
Use the uploaded product image as the strict product reference. Vertical 9:16 realistic commercial UGC image.
{FIXED_BACKGROUND_BLOCK}
Product Lock: the exact {PRODUCT_VISUAL_DESCRIPTION} from the uploaded reference, preserving exact packaging shape, colors, Vietnamese label text, logo, and proportions, no redesign, no invented fake text.
Scene Focus: {SCENE_FOCUS_INSTRUCTION} with {FIXED_HAND_BLOCK}.
Shallow depth of field, appetizing macro food texture, natural daylight. No extra logo, no extra brand names, no AI-generated random text, no watermark. Ultra realistic, photorealistic, 8K.
```

---

## 3. Mẫu `video_prompt` Chuẩn (Chuyển Động 8s - 10s Từ Ảnh Phân Cảnh)

```text
The product is {PRODUCT_VISUAL_DESCRIPTION}. 8-second vertical 9:16 realistic commercial UGC video clip.
Camera: {CAMERA_MOTION}.
Subject motion: {SUBJECT_MOTION}.
Lighting: soft natural daytime light from the left, warm gentle reflections, premium tidy mood unchanged throughout.
Ambient sound: {AMBIENT_SOUND}.
Keep the exact same setting, glass storefront, trees, counter, hand identity and authentic product packaging unchanged. No text overlays, no watermark. Photorealistic.
```

