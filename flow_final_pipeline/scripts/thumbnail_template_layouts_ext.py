# -*- coding: utf-8 -*-
"""
🎨 BỘ MỞ RỘNG 12 STYLE LAYOUT THUMBNAIL MỚI (PHÂN TÍCH TỪ 59 ẢNH TRONG 5 BẢNG MẪU TIKTOK AFFILIATE)
Bao gồm:
  1. `left_pills_3scene_bar`        (Sheet 1 H1C1, H1C3, H3C1, H3C3: 4 Pill Ưu Điểm Trái + 3 Ô Tình Huống/Chất Liệu Đáy)
  2. `cookware_set_4breakdown`      (Sheet 1 H1C2, Sheet 2 H4C1..C3: Bộ Gia Dụng + 4 Pill Trái + 4 Ô Phân Tích Từng Món Đáy)
  3. `multicooker_3food_tabs`       (Sheet 1 H3C2: Thiết Bị Đa Năng + 4 Pill Trái + 3 Khung Ảnh Kết Quả Có Tab Màu HẤP/NẤU/GIỮ ẤM)
  4. `medical_tech_5metrics`        (Sheet 1 H2C1, H2C2: Thiết Bị Y Tế/Điện Tử + 5 Huy Hiệu Chỉ Số Kỹ Thuật Trái + 3 Icon Đáy)
  5. `mens_luxury_dark_gold`        (Sheet 1 H4C1, Sheet 2 H3C2: Nam Lịch Lãm Đen-Vàng Kim + 2 Khung Lớn Fullbox + 3 Huy Hiệu Tròn Đáy)
  6. `fresh_shield_5layers`         (Sheet 1 H4C2, H4C3: 3 Khiên Bảo Vệ Góc Trên + 5 Pill Trái + Vòng Tròn Thao Tác + 2 Ảnh Phụ)
  7. `size_lineup_comparison`       (Sheet 2 H2C1, H3C1: So Sánh 4 Kích Cỡ / Chế Độ Sáng Xếp Ngang + Bảng Tick Ưu Điểm)
  8. `model_flatlay_swatch_dots`    (Sheet 2 H2C2: Mẫu Mặc + Khung Ảnh Trải Sàn SP Rời + Vòng Tròn Zoom Sợi Vải + 5 Chấm Màu Phân Loại)
  9. `pov_hands_pointer_arrows`     (Sheet 3 H1..H4: Đôi Tay Cầm SP POV / Manocanh + 4 Mũi Tên Nét Đứt Chỉ Thẳng Vào Chi Tiết SP)
 10. `influencer_3circle_left_music`(Sheet 4 H2C1, H2C2, H3C1, H3C3: Creator Mặc Thử + Cột Dọc 3 Vòng Zoom Trái + Giỏ Hàng Vàng)
 11. `mega_6grid_bag_showcase`      (Sheet 5 H3C2, H4C2: Túi Xách Đa Ngăn + Lưới 6 Ô Chi Tiết Mọi Ngăn Khóa Xếp 2 Tầng Dưới Đáy)
"""
import os
import math
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance


def draw_top_commercial_headline_banner(
    canvas: Image.Image,
    title_main: str,
    subtitle_pill: str,
    price_badge: str,
    palette: dict,
    load_font_fn,
    fit_text_fn,
    style_variant: str = "pastel_3d",
) -> Image.Image:
    """
    Vẽ cụm Tiêu đề 3D Thương Mại + Băng rôn Phụ đề + Huy hiệu Giá ở vùng đỉnh (`y=32..310`)
    theo đúng phong cách của 5 bảng mẫu TikTok Affiliate.
    """
    ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(ov)
    acc = palette.get("accent_rgb", (251, 191, 36))
    pill_bg = palette.get("pill_bg", (219, 39, 119))
    cta_bg = palette.get("cta_bg", (220, 38, 38))

    # Làm dịu nhẹ vùng đỉnh 280px để chữ nổi bật 100%
    is_dark_theme = style_variant in ("dark_gold", "flash_deal", "tech_dark")
    for y in range(0, 290):
        ratio = 1.0 - (y / 290.0)
        if is_dark_theme:
            alpha = int(175 * (ratio ** 1.3))
            draw.line([(0, y), (1080, y)], fill=(10, 15, 28, alpha))
        else:
            alpha = int(150 * (ratio ** 1.3))
            draw.line([(0, y), (1080, y)], fill=(255, 250, 245, alpha))

    f_title = load_font_fn(54, bold=True)
    f_sub = load_font_fn(25, bold=True)
    f_price = load_font_fn(30, bold=True)

    # 1. Tiêu đề chính có viền đậm + bóng đổ
    t_str = fit_text_fn(draw, (title_main or "SIÊU PHẨM CHÍNH HÃNG").upper(), f_title, 980)
    tb = draw.textbbox((0, 0), t_str, font=f_title)
    tw = tb[2] - tb[0]
    tx = max(36, (1080 - tw) // 2)
    ty = 42

    # Viền stroke dày
    stroke_col = (15, 23, 42, 245) if is_dark_theme else (255, 255, 255, 250)
    main_col = (254, 240, 138, 255) if is_dark_theme else (pill_bg[0], pill_bg[1], pill_bg[2], 255)
    draw.text((tx + 4, ty + 6), t_str, font=f_title, fill=(0, 0, 0, 165))
    for dx in (-4, -2, 0, 2, 4):
        for dy in (-4, -2, 0, 2, 4):
            if dx != 0 or dy != 0:
                draw.text((tx + dx, ty + dy), t_str, font=f_title, fill=stroke_col)
    draw.text((tx, ty), t_str, font=f_title, fill=main_col)

    # 2. Băng rôn ribbon phụ đề dưới tiêu đề (`y=122..172`)
    if subtitle_pill:
        s_str = fit_text_fn(draw, f"♦ {subtitle_pill} ♦", f_sub, 860)
        sb = draw.textbbox((0, 0), s_str, font=f_sub)
        sw = (sb[2] - sb[0]) + 56
        sx = (1080 - sw) // 2
        sy = 122
        draw.rounded_rectangle(
            [sx + 3, sy + 4, sx + sw + 3, sy + 50 + 4],
            radius=25,
            fill=(0, 0, 0, 120),
        )
        draw.rounded_rectangle(
            [sx, sy, sx + sw, sy + 50],
            radius=25,
            fill=pill_bg + (245,),
            outline=(255, 255, 255, 255),
            width=3,
        )
        draw.text((sx + 28, sy + 10), s_str, font=f_sub, fill=(255, 255, 255, 255))

    # 3. Huy hiệu Giá hoặc Cam Kết ở góc phải trên (`x=730..1048, y=190..278`)
    if price_badge:
        p_str = fit_text_fn(draw, price_badge, f_price, 290)
        pb = draw.textbbox((0, 0), p_str, font=f_price)
        pw = max(210, (pb[2] - pb[0]) + 46)
        px = 1048 - pw
        py = 192
        draw.rounded_rectangle(
            [px + 3, py + 5, px + pw + 3, py + 68 + 5],
            radius=34,
            fill=(0, 0, 0, 150),
        )
        draw.rounded_rectangle(
            [px, py, px + pw, py + 68],
            radius=34,
            fill=cta_bg + (250,),
            outline=acc + (255,),
            width=4,
        )
        ptx = px + (pw - (pb[2] - pb[0])) // 2
        draw.text((ptx + 1, py + 17), p_str, font=f_price, fill=(0, 0, 0, 180))
        draw.text((ptx, py + 15), p_str, font=f_price, fill=(255, 255, 255, 255))

    return Image.alpha_composite(canvas, ov)


def draw_left_vertical_feature_pills(
    canvas: Image.Image,
    pill_items: list,
    palette: dict,
    load_font_fn,
    fit_text_fn,
    start_y: int = 690,
    pill_w: int = 296,
    pill_h: int = 66,
    gap_y: int = 12,
    is_dark: bool = False,
) -> Image.Image:
    """
    Vẽ cột dọc 4-5 Pill Ưu Điểm gọn gàng ở rìa trái vùng thân dưới (`x=18..314, y>=690`)
    đảm bảo Safe Zone tuyệt đối không đè lên đầu hay gương mặt nhân vật ở trung tâm.
    """
    ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(ov)
    acc = palette.get("accent_rgb", (236, 72, 153))
    pill_bg = palette.get("pill_bg", (219, 39, 119))

    # Khóa Safe Zone: đặt dưới vùng đầu/mặt (`y >= 685`) và thu gọn chiều ngang (`<= 300px`)
    safe_start_y = max(685, int(start_y))
    safe_pill_w = min(300, int(pill_w))
    safe_pill_h = min(68, int(pill_h))
    safe_gap_y = min(13, int(gap_y))

    f_code = load_font_fn(18, bold=True)
    f_main = load_font_fn(19, bold=True)
    f_sub = load_font_fn(15, bold=False)

    for idx, item in enumerate(pill_items):
        if isinstance(item, (list, tuple)) and len(item) >= 3:
            icon_txt, title_txt, sub_txt = str(item[0]), str(item[1]), str(item[2])
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            icon_txt, title_txt, sub_txt = f"0{idx+1}", str(item[0]), str(item[1])
        else:
            icon_txt, title_txt, sub_txt = f"0{idx+1}", str(item), "Chất lượng kiểm định"

        x1 = 18
        y1 = safe_start_y + idx * (safe_pill_h + safe_gap_y)
        if y1 + safe_pill_h > 1320:
            break
        x2 = x1 + safe_pill_w
        y2 = y1 + safe_pill_h

        # Đổ bóng
        draw.rounded_rectangle([x1 + 3, y1 + 5, x2 + 3, y2 + 5], radius=safe_pill_h // 2, fill=(0, 0, 0, 125))
        bg_fill = (17, 24, 39, 232) if is_dark else (255, 255, 255, 242)
        border_col = acc + (255,) if is_dark else pill_bg + (235,)
        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=safe_pill_h // 2,
            fill=bg_fill,
            outline=border_col,
            width=3,
        )

        # Vòng tròn icon bên trái
        r_ic = (safe_pill_h - 14) // 2
        cx = x1 + 7 + r_ic
        cy = y1 + safe_pill_h // 2
        draw.ellipse(
            [cx - r_ic, cy - r_ic, cx + r_ic, cy + r_ic],
            fill=pill_bg + (255,),
            outline=(255, 255, 255, 255),
            width=2,
        )
        cb = draw.textbbox((0, 0), icon_txt, font=f_code)
        draw.text(
            (cx - (cb[2] - cb[0]) // 2, cy - (cb[3] - cb[1]) // 2 - 2),
            icon_txt,
            font=f_code,
            fill=(255, 255, 255, 255),
        )

        # Text chính & phụ bên phải vòng tròn
        tx = x1 + safe_pill_h + 4
        max_tw = safe_pill_w - safe_pill_h - 16
        m_fit = fit_text_fn(draw, title_txt, f_main, max_tw)
        s_fit = fit_text_fn(draw, sub_txt, f_sub, max_tw)
        t_col = (254, 243, 199, 255) if is_dark else (17, 24, 39, 255)
        s_col = (203, 213, 225, 255) if is_dark else (75, 85, 99, 255)
        draw.text((tx, y1 + 10), m_fit, font=f_main, fill=t_col)
        draw.text((tx, y1 + 37), s_fit, font=f_sub, fill=s_col)

    return Image.alpha_composite(canvas, ov)


def render_extended_layout(
    layout_type: str,
    canvas: Image.Image,
    chosen_prods: list,
    photo_meta: list,
    labels: dict,
    palette: dict,
    smart_crop_fn,
    make_card_fn,
    make_circle_fn,
    load_font_fn,
    fit_text_fn,
) -> Image.Image:
    """
    Xử lý 11 `layout_type` mở rộng mới cho `composite_template_product_insets`.
    Trả về `canvas` đã ghép đầy đủ cụm ảnh sản phẩm thực tế + callouts theo đúng style.
    """
    acc = palette["accent_rgb"]
    pill_bg = palette["pill_bg"]
    pill_text = palette["pill_text"]
    card_border = palette["card_border"]
    five_icons = labels.get("five_icons") or []

    # ── 1. LEFT PILLS + 3 SCENE/DETAIL BAR (Sheet 1 H1C1, H1C3, H3C1, H3C3) ──
    if layout_type == "left_pills_3scene_bar":
        canvas = draw_left_vertical_feature_pills(
            canvas,
            five_icons[:4],
            palette,
            load_font_fn,
            fit_text_fn,
            start_y=390,
            pill_w=382,
            pill_h=78,
            gap_y=16,
            is_dark=False,
        )
        # Huy hiệu Trái Tim / Starburst bên trái dưới (`x=26..246, y=1352..1720`) + 3 khung vuông bên phải
        ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        f_b = load_font_fn(22, bold=True)
        f_s = load_font_fn(18, bold=True)
        # Thẻ Huy Hiệu Cam Kết bên trái
        d.rounded_rectangle([26, 1348, 256, 1726], radius=28, fill=pill_bg + (245,), outline=(255, 255, 255, 255), width=4)
        d.ellipse([76, 1372, 206, 1502], fill=(255, 255, 255, 245), outline=acc + (255,), width=4)
        d.text((108, 1418), "100%", font=load_font_fn(28, bold=True), fill=pill_bg + (255,))
        for idx_t, l_str in enumerate(["CHUẨN HÌNH", "BỀN ĐẸP", "ĐỔI TRẢ 7N", "FREESHIP"]):
            tb = d.textbbox((0, 0), l_str, font=f_s)
            d.text((141 - (tb[2] - tb[0]) // 2, 1522 + idx_t * 44), l_str, font=f_s, fill=(255, 255, 255, 255))
        canvas = Image.alpha_composite(canvas, ov)

        xs = [276, 536, 796]
        for idx in range(3):
            im_p = smart_crop_fn(chosen_prods[idx % len(chosen_prods)], 246, 380)
            card_p = make_card_fn(
                im_p, 246, 380, 22,
                card_border, 5,
                photo_meta[idx][0],
                photo_meta[idx][1],
                pill_bg, pill_text, acc,
            )
            canvas.alpha_composite(card_p, (xs[idx] - 10, 1342))
        return canvas

    # ── 2. COOKWARE / HOME SET 4-ITEM BREAKDOWN BAR (Sheet 1 H1C2, Sheet 2 H4) ──
    if layout_type == "cookware_set_4breakdown":
        canvas = draw_left_vertical_feature_pills(
            canvas,
            five_icons[:4],
            palette,
            load_font_fn,
            fit_text_fn,
            start_y=400,
            pill_w=375,
            pill_h=76,
            gap_y=16,
            is_dark=False,
        )
        # 4 khung Oval/Bo tròn đứng cạnh nhau dưới đáy (`x=24..1056`)
        xs = [24, 280, 536, 792]
        four_prods = [chosen_prods[i % len(chosen_prods)] for i in range(4)]
        four_badges = [
            photo_meta[0][0],
            photo_meta[1][0],
            photo_meta[2][0],
            "♦ TRỌN BỘ COMBO",
        ]
        four_labels = [
            photo_meta[0][1],
            photo_meta[1][1],
            photo_meta[2][1],
            "Đầy đủ phụ kiện đi kèm",
        ]
        for idx in range(4):
            im_p = smart_crop_fn(four_prods[idx], 242, 382)
            card_p = make_card_fn(
                im_p, 242, 382, 36,
                card_border, 5,
                four_badges[idx],
                four_labels[idx],
                pill_bg, pill_text, acc,
            )
            canvas.alpha_composite(card_p, (xs[idx] - 10, 1342))
        return canvas

    # ── 3. MULTICOOKER / APPLIANCE 3 COLORED FUNCTION TABS (Sheet 1 H3C2) ──
    if layout_type == "multicooker_3food_tabs":
        canvas = draw_left_vertical_feature_pills(
            canvas,
            five_icons[:4],
            palette,
            load_font_fn,
            fit_text_fn,
            start_y=400,
            pill_w=380,
            pill_h=76,
            gap_y=16,
            is_dark=False,
        )
        tab_colors = [
            (37, 99, 235),   # Xanh Blue: CÔNG NĂNG 1
            (22, 163, 74),   # Xanh Lá: CÔNG NĂNG 2
            (147, 51, 234),  # Tím: CÔNG NĂNG 3
        ]
        xs = [30, 381, 732]
        for idx in range(3):
            im_p = smart_crop_fn(chosen_prods[idx % len(chosen_prods)], 318, 385)
            card_p = make_card_fn(
                im_p, 318, 385, 24,
                (255, 255, 255), 5,
                photo_meta[idx][0],
                photo_meta[idx][1],
                tab_colors[idx], (255, 255, 255), acc,
            )
            canvas.alpha_composite(card_p, (xs[idx] - 10, 1342))
        return canvas

    # ── 4. MEDICAL / SMART TECH 5 METRIC BADGES (Sheet 1 H2C1, H2C2) ──
    if layout_type == "medical_tech_5metrics":
        canvas = draw_left_vertical_feature_pills(
            canvas,
            five_icons[:5],
            palette,
            load_font_fn,
            fit_text_fn,
            start_y=360,
            pill_w=390,
            pill_h=74,
            gap_y=14,
            is_dark=False,
        )
        xs = [30, 381, 732]
        for idx in range(3):
            im_p = smart_crop_fn(chosen_prods[idx % len(chosen_prods)], 318, 385)
            card_p = make_card_fn(
                im_p, 318, 385, 22,
                card_border, 5,
                photo_meta[idx][0],
                photo_meta[idx][1],
                pill_bg, pill_text, acc,
            )
            canvas.alpha_composite(card_p, (xs[idx] - 10, 1342))
        return canvas

    # ── 5. MEN'S LUXURY DARK & GOLD + 2 LARGE CARDS + MEDALLIONS (Sheet 1 H4C1) ──
    if layout_type == "mens_luxury_dark_gold":
        canvas = draw_left_vertical_feature_pills(
            canvas,
            five_icons[:4],
            palette,
            load_font_fn,
            fit_text_fn,
            start_y=410,
            pill_w=385,
            pill_h=76,
            gap_y=16,
            is_dark=True,
        )
        # 2 Khung Lớn Viền Vàng Kim + 1 Vòng Tròn Giữa
        im_l = smart_crop_fn(chosen_prods[0], 484, 385)
        card_l = make_card_fn(
            im_l, 484, 385, 22,
            (253, 224, 71), 5,
            photo_meta[0][0],
            photo_meta[0][1],
            pill_bg, pill_text, acc,
        )
        canvas.alpha_composite(card_l, (22, 1342))

        im_r = smart_crop_fn(chosen_prods[1 % len(chosen_prods)], 484, 385)
        card_r = make_card_fn(
            im_r, 484, 385, 22,
            (253, 224, 71), 5,
            photo_meta[1][0],
            photo_meta[1][1],
            pill_bg, pill_text, acc,
        )
        canvas.alpha_composite(card_r, (554, 1342))

        im_c = smart_crop_fn(chosen_prods[2 % len(chosen_prods)], 164, 164)
        circ_c = make_circle_fn(
            im_c, 164,
            ring_color=(250, 204, 21),
            outer_color=(255, 255, 255),
            badge_text="VIP",
            caption_text="",
            pill_bg=pill_bg,
        )
        canvas.alpha_composite(circ_c, (446, 1440))
        return canvas

    # ── 6. FRESH SHIELD 5 LAYERS + ACTION CIRCLE + 2 CARDS (Sheet 1 H4C2, H4C3) ──
    if layout_type == "fresh_shield_5layers":
        canvas = draw_left_vertical_feature_pills(
            canvas,
            five_icons[:5],
            palette,
            load_font_fn,
            fit_text_fn,
            start_y=360,
            pill_w=380,
            pill_h=72,
            gap_y=14,
            is_dark=False,
        )
        # Bên trái dưới: 1 Vòng Tròn Thao Tác Lớn (`312px`), Bên phải dưới: 2 Thẻ Chữ Nhật (`330x380`)
        im_c = smart_crop_fn(chosen_prods[0], 312, 312)
        circ_l = make_circle_fn(
            im_c, 312,
            ring_color=acc,
            outer_color=(255, 255, 255),
            badge_text=photo_meta[0][0],
            caption_text=photo_meta[0][1],
            pill_bg=pill_bg,
        )
        canvas.alpha_composite(circ_l, (24, 1342))

        for idx_r, x_pos in enumerate([376, 722], 1):
            im_p = smart_crop_fn(chosen_prods[idx_r % len(chosen_prods)], 324, 382)
            card_p = make_card_fn(
                im_p, 324, 382, 24,
                card_border, 5,
                photo_meta[idx_r % 3][0],
                photo_meta[idx_r % 3][1],
                pill_bg, pill_text, acc,
            )
            canvas.alpha_composite(card_p, (x_pos - 10, 1342))
        return canvas

    # ── 7. MULTI-SIZE / MULTI-MODE LINEUP COMPARISON (Sheet 2 H2C1, H3C1) ──
    if layout_type == "size_lineup_comparison":
        # 4 cột xếp theo chiều cao tăng dần mô phỏng bảng so sánh Size / Phân loại
        xs = [24, 280, 536, 792]
        heights = [310, 336, 362, 388]
        size_tags = ["♦ CỠ NHỎ / LẺ", "♦ CỠ VỪA / BỘ", "♦ CỠ LỚN / VIP", "♦ COMBO ĐẠI"]
        for idx in range(4):
            h_card = heights[idx]
            y_card = 1342 + (388 - h_card)
            im_p = smart_crop_fn(chosen_prods[idx % len(chosen_prods)], 242, h_card)
            card_p = make_card_fn(
                im_p, 242, h_card, 22,
                card_border, 5,
                size_tags[idx],
                photo_meta[idx % 3][1],
                pill_bg, pill_text, acc,
            )
            canvas.alpha_composite(card_p, (xs[idx] - 10, y_card))
        return canvas

    # ── 8. MODEL + FLATLAY CUTOUT + FABRIC SWATCH CIRCLE + 5 COLOR DOTS (Sheet 2 H2C2) ──
    if layout_type == "model_flatlay_swatch_dots":
        # Bên trái dưới: 1 Khung Flatlay SP Lớn (`440x385`), Giữa: Vòng Tròn Zoom Sợi Vải (`250px`), Phải: Khung SP + 5 Chấm Màu
        im_flat = smart_crop_fn(chosen_prods[0], 430, 385)
        card_flat = make_card_fn(
            im_flat, 430, 385, 26,
            (255, 255, 255), 7,
            photo_meta[0][0],
            photo_meta[0][1],
            pill_bg, pill_text, acc,
        )
        canvas.alpha_composite(card_flat, (20, 1342))

        im_zoom = smart_crop_fn(chosen_prods[1 % len(chosen_prods)], 256, 256)
        circ_zoom = make_circle_fn(
            im_zoom, 256,
            ring_color=acc,
            outer_color=(255, 255, 255),
            badge_text="♦ CHẤT VẢI / SỢI",
            caption_text=photo_meta[1][1],
            pill_bg=pill_bg,
        )
        canvas.alpha_composite(circ_zoom, (466, 1352))

        im_r = smart_crop_fn(chosen_prods[2 % len(chosen_prods)], 296, 290)
        card_r = make_card_fn(
            im_r, 296, 290, 22,
            (255, 255, 255), 5,
            photo_meta[2][0],
            photo_meta[2][1],
            pill_bg, pill_text, acc,
        )
        canvas.alpha_composite(card_r, (746, 1342))

        # Vẽ 5 chấm tròn bảng màu (`Color Swatch Dots`) tại `x=755..1040, y=1662..1722`
        ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        swatch_cols = [
            (250, 245, 240),  # Kem
            (153, 27, 27),    # Đỏ đô
            (156, 163, 175),  # Xám
            (244, 114, 182),  # Hồng
            (24, 24, 27),     # Đen
        ]
        for s_i, sc in enumerate(swatch_cols):
            cx = 778 + s_i * 58
            cy = 1692
            d.ellipse([cx - 24, cy - 24, cx + 24, cy + 24], fill=(0, 0, 0, 120))
            d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=sc + (255,), outline=(255, 255, 255, 255), width=4)
        canvas = Image.alpha_composite(canvas, ov)
        return canvas

    # ── 9. POV HANDS / MANNEQUIN + 4 POINTER CALLOUT ARROWS (Sheet 3 H1..H4) ──
    if layout_type == "pov_hands_pointer_arrows":
        ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        f_pt = load_font_fn(21, bold=True)
        f_ps = load_font_fn(17, bold=False)

        # 4 thẻ Callout ở 4 góc vùng thân dưới (Safe Zone y>=700, không chạm đầu nhân vật) chỉ vào sản phẩm ở giữa (`540, 840`)
        callouts = [
            (20, 700, 312, 788, (312, 748), (455, 810), five_icons[0] if len(five_icons) > 0 else ("01", "Chất Liệu Cao Cấp", "Mềm mịn bền đẹp")),
            (768, 700, 1060, 788, (768, 748), (625, 810), five_icons[1] if len(five_icons) > 1 else ("02", "Thiết Kế Tinh Xảo", "Từng đường nét")),
            (20, 990, 312, 1078, (312, 1030), (455, 910), five_icons[2] if len(five_icons) > 2 else ("03", "Cực Kỳ Tiện Lợi", "Dễ dùng mỗi ngày")),
            (768, 990, 1060, 1078, (768, 1030), (625, 910), five_icons[3] if len(five_icons) > 3 else ("04", "Chuẩn Hàng Xưởng", "Cam kết y hình")),
        ]
        for x1, y1, x2, y2, p_start, p_end, ic_tuple in callouts:
            _, t_m, t_s = ic_tuple
            # Đường chấm nét đứt + đầu mũi tên tròn
            steps = 14
            for st in range(steps):
                if st % 2 == 0:
                    xa = int(p_start[0] + (p_end[0] - p_start[0]) * (st / float(steps)))
                    ya = int(p_start[1] + (p_end[1] - p_start[1]) * (st / float(steps)))
                    xb = int(p_start[0] + (p_end[0] - p_start[0]) * ((st + 1) / float(steps)))
                    yb = int(p_start[1] + (p_end[1] - p_start[1]) * ((st + 1) / float(steps)))
                    d.line([(xa, ya), (xb, yb)], fill=(255, 255, 255, 240), width=5)
                    d.line([(xa, ya), (xb, yb)], fill=pill_bg + (255,), width=3)
            d.ellipse([p_end[0] - 9, p_end[1] - 9, p_end[0] + 9, p_end[1] + 9], fill=acc + (255,), outline=(255, 255, 255, 255), width=3)

            # Hộp nhãn Coquette Pastel
            d.rounded_rectangle([x1 + 3, y1 + 4, x2 + 3, y2 + 4], radius=22, fill=(0, 0, 0, 115))
            d.rounded_rectangle([x1, y1, x2, y2], radius=22, fill=(255, 252, 248, 245), outline=pill_bg + (245,), width=3)
            m_fit = fit_text_fn(d, f"♦ {t_m}", f_pt, (x2 - x1) - 24)
            s_fit = fit_text_fn(d, t_s, f_ps, (x2 - x1) - 24)
            d.text((x1 + 14, y1 + 14), m_fit, font=f_pt, fill=pill_bg + (255,))
            d.text((x1 + 16, y1 + 48), s_fit, font=f_ps, fill=(55, 65, 81, 255))

        canvas = Image.alpha_composite(canvas, ov)

        xs = [30, 381, 732]
        for idx in range(3):
            im_p = smart_crop_fn(chosen_prods[idx % len(chosen_prods)], 318, 385)
            card_p = make_card_fn(
                im_p, 318, 385, 26,
                (255, 255, 255), 6,
                photo_meta[idx][0],
                photo_meta[idx][1],
                pill_bg, pill_text, acc,
            )
            canvas.alpha_composite(card_p, (xs[idx] - 10, 1342))
        return canvas

    # ── 10. INFLUENCER OOTD + 3 VERTICAL LEFT CIRCLE ZOOMS + MUSIC BAR (Sheet 4) ──
    if layout_type == "influencer_3circle_left_music":
        # Cột dọc 3 Vòng Tròn Zoom bên trái (`x=16..212, y=440..1180`, Safe Zone không chạm mặt)
        ys_left = [440, 695, 950]
        for idx in range(3):
            im_z = smart_crop_fn(chosen_prods[idx % len(chosen_prods)], 196, 196)
            circ_z = make_circle_fn(
                im_z, 196,
                ring_color=acc,
                outer_color=(255, 255, 255),
                badge_text=photo_meta[idx][0],
                caption_text=photo_meta[idx][1],
                pill_bg=pill_bg,
            )
            canvas.alpha_composite(circ_z, (16, ys_left[idx]))

        # Dưới đáy (`y=1342..1730`): 2 Khung Ảnh Lớn + Nhãn Giỏ Hàng Vàng TikTok
        im_a = smart_crop_fn(chosen_prods[0], 484, 385)
        card_a = make_card_fn(
            im_a, 484, 385, 24,
            (255, 255, 255), 5,
            photo_meta[0][0],
            photo_meta[0][1],
            pill_bg, pill_text, acc,
        )
        canvas.alpha_composite(card_a, (22, 1342))

        im_b = smart_crop_fn(chosen_prods[1 % len(chosen_prods)], 484, 385)
        card_b = make_card_fn(
            im_b, 484, 385, 24,
            (255, 255, 255), 5,
            photo_meta[1][0],
            photo_meta[1][1],
            pill_bg, pill_text, acc,
        )
        canvas.alpha_composite(card_b, (554, 1342))
        return canvas

    # ── 11. MEGA 6-GRID (2 ROWS x 3 COLS) BAG & ACCESSORY SHOWCASE (Sheet 5 H3C2) ──
    if layout_type == "mega_6grid_bag_showcase":
        canvas = draw_left_vertical_feature_pills(
            canvas,
            five_icons[:4],
            palette,
            load_font_fn,
            fit_text_fn,
            start_y=390,
            pill_w=375,
            pill_h=74,
            gap_y=14,
            is_dark=False,
        )
        # Lưới 6 Ô Chi Tiết Xếp 2 Tầng (`2 hàng x 3 cột = 6 khung ảnh 318x186`) tại `y=1340..1735`
        xs = [30, 381, 732]
        ys = [1340, 1540]
        six_badges = [
            photo_meta[0][0],
            photo_meta[1][0],
            photo_meta[2][0],
            "♦ GÓC NGHIÊNG SP",
            "♦ CHI TIẾT BÊN TRONG",
            "♦ ĐÓNG GÓI CHUẨN",
        ]
        six_labels = [
            photo_meta[0][1],
            photo_meta[1][1],
            photo_meta[2][1],
            "Form chuẩn chắc chắn",
            "Rộng rãi tiện dụng",
            "Giao hàng nguyên hộp",
        ]
        idx_6 = 0
        for r_i in range(2):
            for c_i in range(3):
                p_path = chosen_prods[idx_6 % len(chosen_prods)]
                im_cell = smart_crop_fn(p_path, 318, 186)
                # Xoay/crop nhẹ các ô tầng 2 nếu ít hơn 6 ảnh để 6 ô luôn khác góc nhìn
                if idx_6 >= len(chosen_prods):
                    w_c, h_c = im_cell.size
                    sub_box = (int(w_c * 0.08), int(h_c * 0.08), int(w_c * 0.92), int(h_c * 0.92))
                    im_cell = im_cell.crop(sub_box).resize((318, 186), Image.Resampling.LANCZOS)
                card_cell = make_card_fn(
                    im_cell, 318, 186, 18,
                    card_border, 4,
                    six_badges[idx_6],
                    six_labels[idx_6],
                    pill_bg, pill_text, acc,
                )
                canvas.alpha_composite(card_cell, (xs[c_i] - 10, ys[r_i]))
                idx_6 += 1
        return canvas

    return canvas
