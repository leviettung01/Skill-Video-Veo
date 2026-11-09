# -*- coding: utf-8 -*-
"""
Engine Độc Lập Cho 2 Hệ Thống Tùy Chọn Trong Prompt Render AI Video:
  1. HỆ THỐNG GÓC MÁY, HẬU CẢNH UY TÍN & ĐẠO DIỄN B-ROLL CẬN SẢN PHẨM (`camera_broll_settings`):
     - Khắc phục triệt để lỗi góc máy quá cận: Sử dụng góc máy `Medium-Full 35mm Equivalent (f/4.5 environmental depth of field)`
       lấy từ ngang đùi/hông trở lên ở khoảng cách 2.2m, giúp thấy rõ toàn cảnh Nhà xưởng / Kho hàng kệ cao / Dây chuyền sản xuất /
       Cửa hàng chính hãng / Showroom Luxury phía sau để tạo độ uy tín tối đa, đồng thời giữ nguyên da thật có lỗ chân lông & nét mặt.
     - Hỗ trợ tích chọn Đạo diễn Đa Góc Máy `SHOT 1 -> SHOT 2 (Hard Cut 50mm Macro Product Insert) -> SHOT 3`:
       + SHOT 1 (0.0s - 1.6s): Góc Medium-Full 35mm tại xưởng/cửa hàng, nhân vật nhìn thẳng camera mở lời tự nhiên.
       + SHOT 2 (1.6s - 5.5s): Hard cut sang góc cận 50mm Macro trượt ngang dọc theo sản phẩm thật từ [PRODUCT REFERENCE IMAGE],
         phô diễn chất liệu, bề mặt, công năng trong khi nhân vật đọc Voiceover, hậu cảnh xưởng vẫn hiện nhẹ phía sau.
       + SHOT 3 (5.5s - 10.0s): Hard cut quay lại góc Medium-Full 35mm ban đầu, nhân vật mở hai tay / chỉ vào sản phẩm và chốt câu.

  2. HỆ THỐNG HIỆU ỨNG VISUAL FX TRỰC TIẾP TRONG PROMPT RENDER AI VIDEO (`video_edit_fx_settings` — Tách biệt với Góc máy):
     - Mô tả chi tiết hiệu ứng thị giác trực tiếp trong Prompt của Model AI (Google Flow Veo 3.1 / Grok) để AI tự sinh hiệu ứng
       mượt mà trong không gian 3D của video (KHÔNG vẽ đè hình Pillow hậu kỳ gây rối mắt).
     - Tuyệt đối KHÔNG mô tả thêm Subtitle hay chữ nổi trong Prompt AI vì hệ thống đã có Kho Template Subtitle chuyên nghiệp ở bước xuất video!
"""
import os
import re
import json


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CẤU HÌNH MẶC ĐỊNH CHO 2 HỆ THỐNG PROMPT AI RIÊNG BIỆT (GÓC MÁY B-ROLL & HIỆU ỨNG AI FX)
# ═══════════════════════════════════════════════════════════════════════════════

BACKGROUND_CREDIBILITY_STYLES = [
    {
        "id": "auto_template",
        "name": "🔄 Tự động theo Kịch bản (Xưởng SX / Kho Pallet / Phòng QC / Showroom)",
        "setting_en": "",
        "bg_short_en": "the spacious industrial workshop, towering warehouse racks, and organized workbenches",
    },
    {
        "id": "warehouse_racks",
        "name": "📦 Tổng Kho Hàng & Kệ Pallet Cao Tầng (Sẵn hàng số lượng lớn)",
        "setting_en": (
            "standing behind a wide foreground packing and display table stacked with neat retail product units in a vast, high-ceiling "
            "industrial dispatch warehouse; towering orange-and-blue steel pallet racks loaded with shipping cartons, yellow floor safety lines, "
            "and a warehouse forklift are clearly visible in sharp environmental depth behind"
        ),
        "bg_short_en": "the towering orange-and-blue warehouse pallet racks, stacked shipping cartons, and foreground packing table",
    },
    {
        "id": "factory_line",
        "name": "⚙️ Nhà Máy & Dây Chuyền Sản Xuất (Băng chuyền, máy móc, kỹ thuật viên)",
        "setting_en": (
            "standing behind a wide stainless-steel inspection and display workbench in an expansive, brightly lit modern manufacturing factory; "
            "active assembly conveyor lines, grey metal parts racks, industrial overhead lighting, and factory technicians in uniform "
            "are clearly visible across the deep workshop floor behind"
        ),
        "bg_short_en": "the grey metal racks, active factory assembly conveyor lines, and stainless-steel workbench",
    },
    {
        "id": "qc_laboratory",
        "name": "🔬 Phòng Kiểm Định Chất Lượng QC & R&D (Chuẩn kỹ thuật uy tín)",
        "setting_en": (
            "standing behind a wide white quality-inspection counter in a spacious glass-walled Quality Control (QC) & R&D center; "
            "organized product sample shelves, precision testing instruments, quality certification boards, and QC engineers "
            "are clearly visible in the bright laboratory behind"
        ),
        "bg_short_en": "the organized QC sample shelves, precision testing instruments, and white inspection counter",
    },
    {
        "id": "flagship_store",
        "name": "🏬 Cửa Hàng Chính Hãng / Siêu Thị Trưng Bày Rộng Rãi",
        "setting_en": (
            "standing behind a neat display counter in a spacious, brightly lit official flagship retail store; "
            "rows of neatly arranged product display shelves, signage, and clean store aisles are clearly visible in the background"
        ),
        "bg_short_en": "the official retail store display shelves, bright aisles, and foreground counter",
    },
    {
        "id": "luxury_boutique",
        "name": "✨ Cửa Hàng Luxury / Showroom Cao Cấp (Đèn hắt sang trọng, tủ kính)",
        "setting_en": (
            "standing behind a sleek marble-and-brass presentation counter in an upscale luxury flagship boutique showroom; "
            "warm architectural cove lighting, illuminated glass display cabinets, wooden accent walls, and high-end showroom decor "
            "are clearly visible in the background"
        ),
        "bg_short_en": "the illuminated luxury showroom glass cabinets, warm architectural lighting, and marble display counter",
    },
    {
        "id": "modern_enterprise",
        "name": "🏢 Văn Phòng / Hành Lang Doanh Nghiệp Hiện Đại (Như Video Mẫu)",
        "setting_en": (
            "standing in a bright, spacious modern glass-walled corporate headquarters corridor with polished wooden floors, "
            "floor-to-ceiling windows, indoor greenery, sleek office desks, and architectural ceiling lights stretching deep into the background"
        ),
        "bg_short_en": "the bright glass-walled corporate corridor, wooden floor, and modern office interior",
    },
]

DEFAULT_CAMERA_BROLL_SETTINGS = {
    # 1. Góc máy rộng lấy trọn hậu cảnh uy tín (Khắc phục lỗi góc máy quá cận)
    "cam_wide_credible_bg": True,
    "background_environment_type": "auto_template",
    # 2. Chế độ Đạo diễn Đa Góc Máy & Chuyển Cảnh B-Roll Cận Sản Phẩm (SHOT 1 -> SHOT 2 -> SHOT 3)
    "enable_multishot_broll": True,
    "broll_shot_structure_3cuts": True,     # Chia cảnh thành SHOT 1 (0-1.6s Wide) -> SHOT 2 (1.6-5.5s Hard Cut Macro Insert) -> SHOT 3 (5.5-10s Wide)
    "broll_macro_sliding_pan": True,        # SHOT 2 trượt máy 50mm Macro dọc theo sản phẩm thật từ [PRODUCT REFERENCE IMAGE]
    "broll_hand_func_demo": True,           # B-Roll cận cảnh bàn tay test công năng / chất liệu sản phẩm khi nói tới USP
    "broll_angle_variety": True,            # Đổi góc máy cận giữa các cảnh (Low-Angle Hero / 45-Degree Detail / Top-Down)
    "broll_dynamic_camera_motion": False,   # Máy quay Steadicam tiến nhẹ theo nhân vật (Tuỳ chọn)
}

DEFAULT_VIDEO_EDIT_FX_SETTINGS = {
    # Công tắc tổng bật/tắt Mô tả Hiệu Ứng Visual FX trực tiếp trong Prompt Render AI Video
    # (Tuyệt đối KHÔNG vẽ đè hậu kỳ Pillow và KHÔNG mô tả thêm Subtitle trong Prompt AI)
    "enable_video_edit_fx": True,
    "fx_floating_3d_icons_badges": True,    # 1. Icon 3D Hologram Nổi Quanh Vai (Bánh răng 3D, Khiên chất lượng, Hạt sao phát sáng — Không chữ)
    "fx_glass_hud_panels": True,            # 2. Khung Kính Hologram Trong Suốt & Tia Sáng Công Nghệ (Hover nhẹ trong không gian 3D — Không chữ)
    "fx_neon_swoosh_ticks": True,           # 3. Vệt Sáng Neon & Tia Sáng Viền Lướt Dọc Sản Phẩm (Glowing Neon Light Ribbon & Specular Sweep)
    "fx_glass_player_progress_card": True,  # 4. Hiệu Ứng Ánh Sáng Studio & Hạt Bokeh Vàng Điện Ảnh (Cinematic Rim Light & Golden Micro-Bokeh)
    "fx_pip_broll_cutaway": True,           # 5. Vòng Tròn Kính Lúp Quang Học Phóng Đại Chất Liệu Sản Phẩm (Optical Macro Magnifier Ring — Không chữ)
    "fx_center_pop_keywords": False,        # 6. Tắt chữ nổi AI (Vì đã dùng Kho Template Subtitle chuyên nghiệp ở bước Render Video)
}


def get_bg_style_by_id(bg_id: str) -> dict:
    q = (bg_id or "auto_template").strip().lower()
    for b in BACKGROUND_CREDIBILITY_STYLES:
        if b["id"] == q:
            return b
    return BACKGROUND_CREDIBILITY_STYLES[0]


def _upgrade_setting_en_for_credible_background(raw_setting_en: str, bg_type: str = "auto_template") -> tuple:
    """
    Đảm bảo mô tả bối cảnh (`setting_en`) luôn hiển thị RÕ NÉT, RỘNG RÃI toàn cảnh
    Nhà xưởng / Kho hàng / Dây chuyền / Cửa hàng / Showroom Luxury ở phía sau (không bị xóa phông mù mịt).
    Trả về `(upgraded_setting_en, bg_short_en)`.
    """
    bg_obj = get_bg_style_by_id(bg_type)
    if bg_obj["id"] != "auto_template" and bg_obj.get("setting_en"):
        return bg_obj["setting_en"], bg_obj["bg_short_en"]

    s = (raw_setting_en or "").strip()
    if not s:
        s = (
            "standing behind a wide foreground packing and display worktable with neatly stacked product units in a spacious, "
            "high-ceiling manufacturing workshop and dispatch warehouse with towering pallet racks, active assembly lines, "
            "and organized inventory shelves clearly visible in deep environmental focus behind"
        )
    else:
        s = re.sub(
            r"softly blurred in (?:creamy (?:optical )?bokeh|shallow depth-of-field bokeh)(?: in the background| behind her| behind him)?",
            "clearly visible with crisp architectural depth across the spacious facility behind",
            s,
            flags=re.I,
        )
        s = re.sub(
            r"with creamy background bokeh",
            "with deep, authentic environmental clarity showing the full scale of the facility behind",
            s,
            flags=re.I,
        )

    s_low = s.lower()
    if "pallet" in s_low or "warehouse" in s_low:
        bg_short = "the towering orange-and-blue warehouse pallet racks, stacked shipping cartons, and foreground packing table"
    elif "qc" in s_low or "laboratory" in s_low or "testing" in s_low:
        bg_short = "the organized QC sample shelves, testing instruments, and clean inspection workbench"
    elif "showroom" in s_low or "boutique" in s_low:
        bg_short = "the illuminated official showroom display shelves and foreground presentation counter"
    elif "conveyor" in s_low or "fulfillment" in s_low:
        bg_short = "the roller conveyor belts, neatly taped shipping boxes, and stainless-steel packing station"
    else:
        bg_short = "the grey metal workshop racks, active production lines, stacked export cartons, and foreground workbench"

    return s, bg_short


# ═══════════════════════════════════════════════════════════════════════════════
# 2. BUILDER CHO PROMPT ẢNH REF 2K (GÓC TRUNG-TOÀN CẢNH 35MM RÕ HẬU CẢNH UY TÍN)
# ═══════════════════════════════════════════════════════════════════════════════

def build_credible_environment_ref_prompt(
    ck: str,
    appearance_en: str,
    outfit_en: str,
    setting_en: str,
    prod_type_en: str,
    prod_scale_en: str,
    gender: str = "female",
    cam_settings: dict = None,
) -> str:
    """
    Xây dựng Prompt Ảnh Reference 2K (1536x2752):
      - Khi `cam_wide_credible_bg=True` (Mặc định): Dùng góc máy `Medium-Full 3/4-Body Environmental Shot (35mm lens at f/4.5, camera at 2.2m distance)`
        lấy từ ngang đùi/hông trở lên, nhân vật chiếm ~45% bề ngang khung hình, giúp thấy RÕ TOÀN CẢNH Nhà xưởng / Kho hàng kệ cao /
        Dây chuyền sản xuất / Cửa hàng / Showroom Luxury đằng sau để tạo độ uy tín tuyệt đối, đồng thời giữ nguyên da thật có lỗ chân lông!
    """
    cfg = {**DEFAULT_CAMERA_BROLL_SETTINGS, **(cam_settings or {})}
    wide_env = bool(cfg.get("cam_wide_credible_bg", True))
    bg_type = str(cfg.get("background_environment_type") or "auto_template")
    upgraded_setting, _ = _upgrade_setting_en_for_credible_background(setting_en, bg_type)

    is_male = (gender or "").lower() == "male" or "nv3" in (ck or "").lower()
    app_low = (appearance_en or "").lower()
    has_glasses = (
        ("nv1" in (ck or "").lower())
        or ("framed glasses" in app_low and "no glasses" not in app_low and "without glasses" not in app_low)
    )

    if is_male:
        skin_and_details = (
            "Detailed visible natural skin pores and authentic masculine epidermal micro-texture (zero plastic or waxy smoothing), "
            "healthy warm-fair complexion with subtle natural light reflection on the bridge of the nose, cheekbones, and forehead; "
            "matching skin tone across face, neck, forearms, and hands. Sharp masculine jawline, naturally groomed eyebrows, "
            "and expressive dark eyes with crisp dual catchlights."
        )
        physique_block = (
            "PHYSIQUE: Athletic, mature adult masculine proportions with broad shoulders, toned chest, V-taper torso, and natural confident posture."
        )
        pose_block = (
            "Expression / Pose: Warm, charismatic, approachable smile toward the camera, lips gently parted as if speaking naturally, "
            "subtle head tilt, torso turned slightly (5-8 degrees) for relaxed masculine asymmetry rather than a stiff frontal pose."
        )
    else:
        glasses_clause = (
            " She wears thin, lightweight black-framed glasses with crystal-clear anti-reflective lenses — zero white glare or distortion over her eyes."
            if has_glasses
            else ""
        )
        skin_and_details = (
            "Detailed visible natural skin pores and lifelike epidermal micro-texture (absolutely zero plastic or airbrushed doll skin), "
            "radiant rosy dewy Douyin glass-skin finish with subtle specular light reflection on the bridge of her nose, cheeks, and forehead. "
            "Her face, neck, and hands match in the same fair, radiant skin tone without any unevenness. "
            "Makeup: Fresh Korean soft-glam luminous makeup, soft pink blush across the cheeks and a touch of blush on the nose tip for a youthful look, "
            "subtle aegyosal under bright expressive dark-brown eyes with crisp catchlights, wispy curled eyelashes, thin defined winged eyeliner, "
            "naturally brushed eyebrows, and glossy ombré lips with a nude-pink base blending into cherry-blossom red lip tint in the center."
            + glasses_clause
        )
        physique_block = (
            "PHYSIQUE: Full, mature adult feminine proportions with natural womanly curves, C-cup natural bust, using 90-60-90 proportions, "
            "natural upper-body volume, relatively slender waist, and graceful feminine posture."
        )
        pose_block = (
            "Expression / Pose: Warm, charming, friendly smile looking directly into the camera lens, lips gently parted, "
            "subtle head tilt, torso turned slightly (5-10 degrees three-quarter angle), gently relaxed neck and one shoulder slightly closer to the camera "
            "for relaxed feminine asymmetry (NOT a stiff frontal mannequin pose)."
        )

    if wide_env:
        framing_header = (
            "Subject & Identity: A hyper-photorealistic vertical 9:16 MEDIUM-FULL ENVIRONMENTAL SHOT "
            "(framed from mid-thigh/hips up to generous overhead ceiling space, camera positioned at 2.2 meters distance with a 35mm wide-angle lens "
            "so the presenter occupies ~45% of the frame width and the expansive credible workshop/warehouse/store background is clearly visible around them) "
            f"of the exact same person from the attached character reference image ({appearance_en}), "
            "preserving their original facial identity, bone structure, and features 100% without altering facial identity. "
        )
        camera_footer = (
            "Camera & Lighting: Shot on Sony A7R V full-frame camera with 35mm f/1.4 GM wide-angle environmental lens stopped down to f/4.5 "
            "(combining crisp facial micro-detail with deep, recognizable environmental depth of field so the warehouse racks, production lines, "
            "or showroom shelves behind remain authentic and clearly visible, NOT blurred out), "
            "natural industrial overhead daylight balanced with soft front key fill illuminating the face evenly without harsh shadows, "
            "subtle organic sensor grain, and true-to-life color rendering. "
        )
    else:
        framing_header = (
            "Subject & Identity: A hyper-photorealistic vertical 9:16 medium upper-body portrait "
            "(framed from top of head with natural headroom to waist/hips, camera at 1.5 meters distance) "
            f"of the exact same person from the attached character reference image ({appearance_en}), "
            "preserving their original facial identity, bone structure, and features 100% without altering facial identity. "
        )
        camera_footer = (
            "Camera & Lighting: Shot on Sony A7R V full-frame camera with 35mm f/1.4 GM lens at f/2.8, "
            "soft diffused key lighting from the front-left combined with gentle fill light illuminating the face evenly, "
            "natural environmental depth of field, subtle organic sensor grain, and true-to-life color rendering. "
        )

    return (
        framing_header
        + f"Outfit & Credible Background Environment: {outfit_en}, {upgraded_setting}. "
        + f"Skin & Makeup: {skin_and_details} "
        + f"{physique_block} "
        + f"{pose_block} "
        + f"Product Action & Foreground Display Lock: Clean, natural hands holding and presenting the exact {prod_type_en} from the attached product reference image "
        + f"at waist-to-chest level facing the camera ({prod_scale_en}, NOT oversized), with neatly stacked authentic retail product packages on the foreground table. "
        + "Keep the product 100% identical to the product reference image (preserve exact shape, material texture, weave, color, logo, and labels without redesigning). "
        + camera_footer
        + "Ultra-high resolution 2K (1536x2752), indistinguishable from a genuine photograph, zero AI-generated appearance. "
        + "Negative prompt: extreme close-up, zoomed-in face filling the frame, blurry unrecognizable background, AI look, CGI, 3D render, plastic skin, "
        + "waxy airbrushed face, doll face, stiff pose, frontal passport pose, unnatural symmetry, dead eyes, crossed eyes, blurry eyes, opaque glasses glare, "
        + "altered facial identity, giant oversized product, redesigned product, extra fingers, deformed hands, cut-off head, random text, watermark."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. BUILDER CHO HIỆU ỨNG VISUAL FX TRONG PROMPT RENDER AI VIDEO (KHÔNG SUBTITLE/TEXT)
# ═══════════════════════════════════════════════════════════════════════════════

def build_ai_prompt_visual_fx_clauses(
    scene_idx: int,
    prod_type_en: str = "authentic product",
    fx_settings: dict = None,
) -> dict:
    """
    Sinh các mô tả hiệu ứng Visual FX bằng tiếng Anh chi tiết để nhúng trực tiếp vào Prompt
    của Model AI tạo video (Veo 3.1 / Grok).
    QUY TẮC VÀNG:
      - Mô tả hiệu ứng ánh sáng, icon 3D hologram, khung kính trong suốt, vệt sáng neon, kính lúp quang học
        hòa quyện tự nhiên trong không gian 3D của video.
      - TUYỆT ĐỐI KHÔNG mô tả thêm subtitle hay chữ nổi trên màn hình (`zero on-screen text, no AI subtitles`)
        vì hệ thống đã có Kho Template Subtitle tiếng Việt chuyên nghiệp ở bước xuất video!
    """
    cfg = {**DEFAULT_VIDEO_EDIT_FX_SETTINGS, **(fx_settings or {})}
    if not cfg.get("enable_video_edit_fx", True):
        return {"shot1_fx": "", "shot2_fx": "", "shot3_fx": "", "single_shot_fx": ""}

    s1_parts = []
    s2_parts = []
    s3_parts = []

    # 1. Icon 3D Hologram Nổi Quanh Vai (Không chữ)
    if cfg.get("fx_floating_3d_icons_badges", True):
        if scene_idx == 1:
            s1_parts.append(
                "Subtle, sleek 3D translucent holographic icons (tiny glossy micro-gears and a soft glowing quality shield emblem, "
                "strictly icon-only with zero text) float gently in mid-air beside the presenter's upper shoulder with natural depth-of-field parallax."
            )
        elif scene_idx == 2:
            s1_parts.append(
                "Delicate 3D floating golden star emblems and a clean glowing checkmark badge hover softly in the air beside the presenter (purely visual icons, no text)."
            )
        else:
            s3_parts.append(
                "A clean, subtle 3D glowing quality verification shield icon floats softly near the product display (zero text or letters)."
            )

    # 2. Khung Kính Hologram Trong Suốt & Tia Sáng Công Nghệ (Không chữ)
    if cfg.get("fx_glass_hud_panels", True):
        if scene_idx in (1, 3):
            s3_parts.append(
                "Minimalist, translucent glassmorphism HUD accent frames with thin glowing cyan rim borders hover subtly in the background space "
                "to the side without covering the presenter's face or hands, completely free of any text or numbers."
            )
        else:
            s1_parts.append(
                "A sleek, subtle translucent glass frame with a soft cyan edge glow accents the background space beside the presenter without any text."
            )

    # 3. Vệt Sáng Neon & Tia Sáng Viền Lướt Dọc Sản Phẩm (Neon Swoosh & Specular Sweep)
    if cfg.get("fx_neon_swoosh_ticks", True):
        s2_parts.append(
            f"A smooth, cinematic glowing emerald-and-cyan light trail and subtle specular highlight sweep trace gracefully along the edges of the {prod_type_en} "
            "to accentuate its craftsmanship."
        )
        s3_parts.append(
            "A soft, brief glowing neon arc sweeps cleanly underneath the product as the presenter gestures toward the shopping cart."
        )

    # 4. Hiệu Ứng Ánh Sáng Studio & Hạt Bokeh Vàng Điện Ảnh (Cinematic Rim Light & Golden Micro-Bokeh)
    if cfg.get("fx_glass_player_progress_card", True):
        s2_parts.append(
            "Warm commercial studio rim-lighting flares and delicate floating golden micro-bokeh light particles shimmer softly around the workbench."
        )

    # 5. Vòng Tròn Kính Lúp Quang Học Phóng Đại Chất Liệu Sản Phẩm (Optical Macro Magnifier Ring)
    if cfg.get("fx_pip_broll_cutaway", True):
        s2_parts.append(
            f"A clean circular optical magnifier ring callout hovers beside the {prod_type_en}, optically zooming into its authentic surface weave "
            "and material micro-texture from [PRODUCT REFERENCE IMAGE] with a thin glowing border and zero text."
        )

    shot1_fx = (" " + " ".join(s1_parts)) if s1_parts else ""
    shot2_fx = (" " + " ".join(s2_parts)) if s2_parts else ""
    shot3_fx = (" " + " ".join(s3_parts)) if s3_parts else ""
    all_parts = (s1_parts + s2_parts + s3_parts)[:3]
    single_fx = (" VISUAL EFFECTS (AI-rendered in-scene, zero text/subtitles): " + " ".join(all_parts)) if all_parts else ""

    return {
        "shot1_fx": shot1_fx,
        "shot2_fx": shot2_fx,
        "shot3_fx": shot3_fx,
        "single_shot_fx": single_fx,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 4. BUILDER CHO PROMPT VIDEO ĐA GÓC MÁY + HIỆU ỨNG AI FX (SHOT 1 -> 2 -> 3)
# ═══════════════════════════════════════════════════════════════════════════════

def build_scene_video_prompt_with_broll(
    scene_idx: int,
    timed_lines: list,
    scene_actions: dict = None,
    voice_prompt_en: str = "",
    prod_type_en: str = "authentic product",
    setting_en: str = "",
    cam_settings: dict = None,
    fx_settings: dict = None,
    style_label: str = "",
    **kwargs,
) -> str:
    """
    Xây dựng Prompt Video 10s cho từng phân cảnh:
      - Phần 1 (`cam_settings`): Đạo diễn Góc máy `Medium-Full 35mm` rõ hậu cảnh Nhà xưởng/Kho/Showroom
        và chuyển cảnh 3 nhịp `SHOT 1 (0.0-1.6s) -> SHOT 2 (1.6-5.5s Hard Cut 50mm Macro Product Insert) -> SHOT 3 (5.5-10.0s)`.
      - Phần 2 (`fx_settings`): Nhúng mô tả Hiệu ứng Visual FX chi tiết trực tiếp vào Prompt AI Video
        (Icon 3D hologram, khung kính mờ, tia sáng viền neon, kính lúp quang học cận chất liệu) — TUYỆT ĐỐI KHÔNG mô tả thêm
        subtitle/text trong prompt vì video đã có hệ thống Render Phụ Đề chuyên nghiệp!
    """
    cfg = {**DEFAULT_CAMERA_BROLL_SETTINGS, **(cam_settings or {})}
    fx_clauses = build_ai_prompt_visual_fx_clauses(scene_idx, prod_type_en=prod_type_en, fx_settings=fx_settings)

    wide_env = bool(cfg.get("cam_wide_credible_bg", True))
    enable_broll = bool(cfg.get("enable_multishot_broll", True))
    use_3cuts = bool(cfg.get("broll_shot_structure_3cuts", True))
    use_macro_pan = bool(cfg.get("broll_macro_sliding_pan", True))
    use_func_demo = bool(cfg.get("broll_hand_func_demo", True))
    use_angle_var = bool(cfg.get("broll_angle_variety", True))
    use_dyn_motion = bool(cfg.get("broll_dynamic_camera_motion", False))
    bg_type = str(cfg.get("background_environment_type") or "auto_template")

    _, bg_short_en = _upgrade_setting_en_for_credible_background(setting_en, bg_type)
    voice_block = "\n".join(timed_lines)
    voice_dir = f" ({voice_prompt_en})" if voice_prompt_en else ""

    base_lens_desc = (
        "Medium-full eye-level shot, 35mm equivalent (f/4.5 environmental depth of field showing the presenter from mid-thigh/waist up "
        f"and keeping {bg_short_en} clearly visible behind for authentic factory/store credibility)"
        if wide_env
        else "Medium upper-body eye-level shot, 35mm equivalent"
    )
    motion_clause = (
        " Subtle, smooth Steadicam gimbal push-in adds natural commercial energy."
        if use_dyn_motion
        else " Do not move the foreground table or change the workshop/store layout."
    )

    if enable_broll and use_3cuts:
        if scene_idx == 1:
            shot1_window = "0.0 to 1.6 seconds"
            shot2_window = "1.6 to 5.4 seconds"
            shot3_window = "5.4 to 10.0 seconds"
            shot1_desc = (
                f"{base_lens_desc}. Match the reference image layout exactly: {bg_short_en} in the exact same background position, "
                f"neat product stacks on the foreground table, presenter holding the exact {prod_type_en} at waist-to-chest level. "
                "The presenter looks directly into the camera, smiles with energetic surprise and begins speaking immediately with accurate Vietnamese lip-sync."
                + motion_clause
                + fx_clauses["shot1_fx"]
            )
            if use_macro_pan:
                shot2_desc = (
                    f"Hard cut to a low-angle 50mm macro product insert from the same camera side. Slowly slide laterally along the real {prod_type_en} "
                    "held in hand and stacked on the workbench. Reveal the exact surface finish, weave/material micro-texture, stitching, and authentic packaging "
                    f"from [PRODUCT REFERENCE IMAGE]. Keep every part physically correct and 100% identical in shape and color. "
                    f"The presenter continues seamlessly as voiceover; {bg_short_en} remain softly visible in the background."
                    + fx_clauses["shot2_fx"]
                )
            else:
                shot2_desc = (
                    f"Hard cut to a crisp 50mm close-up product insert of the real {prod_type_en} from [PRODUCT REFERENCE IMAGE], "
                    f"highlighting its authentic material texture and craftsmanship while the presenter continues as voiceover with {bg_short_en} in the background."
                    + fx_clauses["shot2_fx"]
                )
            shot3_desc = (
                "Hard cut back to the exact same medium-full 35mm composition as Shot 1. The presenter opens one hand toward the product, "
                "raises their eyebrows in playful confidence, then gestures briefly toward the bottom-left shopping cart while finishing the sentence. "
                "Keep the product, presenter identity, and background layout in the exact same position and orientation."
                + fx_clauses["shot3_fx"]
            )

        elif scene_idx == 2:
            shot1_window = "0.0 to 1.8 seconds"
            shot2_window = "1.8 to 5.5 seconds"
            shot3_window = "5.5 to 10.0 seconds"
            angle_tag = "45-degree angled 50mm macro product B-roll insert" if use_angle_var else "low-angle 50mm macro product insert"
            shot1_desc = (
                f"{base_lens_desc}. Match the workshop/store layout and presenter appearance 100% from the reference image: {bg_short_en} clearly visible behind. "
                "The presenter looks directly into the camera with playful disbelief when stating the price comparison, shaking one finger lightly."
                + motion_clause
                + fx_clauses["shot1_fx"]
            )
            shot2_desc = (
                f"Hard cut to a {angle_tag} focusing on the real {prod_type_en} and stacked factory-direct bundles on the workbench. "
                "Slowly pan across the authentic material details, edges, and neat multi-pack stacks from [PRODUCT REFERENCE IMAGE], "
                "keeping every physical detail sharp and accurate while the presenter continues speaking as voiceover."
                + fx_clauses["shot2_fx"]
            )
            shot3_desc = (
                "Hard cut back to the same medium-full 35mm composition as Shot 1. The presenter smiles warmly, holds the product steady, "
                "and points clearly toward the bottom-left corner shopping cart icon to invite viewers to check their account price."
                + fx_clauses["shot3_fx"]
            )

        else:
            shot1_window = "0.0 to 1.5 seconds"
            shot2_window = "1.5 to 5.8 seconds"
            shot3_window = "5.8 to 10.0 seconds"
            shot1_desc = (
                f"{base_lens_desc}. Match the reference image layout exactly with {bg_short_en} behind. "
                f"The presenter looks into the camera with confident reassurance while presenting the {prod_type_en}."
                + fx_clauses["shot1_fx"]
            )
            if use_func_demo:
                shot2_desc = (
                    f"Hard cut to an eye-level 50mm macro functional B-roll insert from the same camera side: clean hands actively demonstrating "
                    f"the real {prod_type_en} from [PRODUCT REFERENCE IMAGE] — flexing, inspecting, and showcasing its durable construction, "
                    "premium surface texture, and practical utility up close. Keep the product 100% physically accurate with zero morphing. "
                    f"The presenter continues seamlessly as voiceover; {bg_short_en} remain softly visible behind."
                    + fx_clauses["shot2_fx"]
                )
            else:
                shot2_desc = (
                    f"Hard cut to a 50mm macro product insert sliding slowly across the real {prod_type_en} from [PRODUCT REFERENCE IMAGE] "
                    "to showcase its build quality and finish while the presenter continues as voiceover."
                    + fx_clauses["shot2_fx"]
                )
            shot3_desc = (
                "Hard cut back to the same medium-full 35mm composition as Shot 1. The presenter gives a bright, trustworthy closing smile, "
                "nods reassuringly, and holds the exact product steady until the clip ends at 10.0 seconds."
                + fx_clauses["shot3_fx"]
            )

        multi_shot_block = (
            f"SHOT 1 — {shot1_window}:\n{shot1_desc}\n\n"
            f"SHOT 2 — {shot2_window}:\n{shot2_desc}\n\n"
            f"SHOT 3 — {shot3_window}:\n{shot3_desc}"
        )
        header_line = (
            "A hyper-photorealistic 10-second vertical 9:16 commercial video starting directly from the provided 2K reference image, "
            "directed with 3 clean multi-angle cuts (Medium-Full 35mm Credible Environment -> 50mm Macro Product B-Roll Insert -> Medium-Full 35mm). "
            "Preserve 100% of the character's exact facial identity, visible natural skin pores, rosy dewy glass-skin texture, "
            "the exact product from [PRODUCT REFERENCE IMAGE], and the credible background environment."
        )
        body_section = multi_shot_block

    else:
        action_str = scene_actions.get(str(scene_idx)) or scene_actions.get(1) or (
            "The presenter looks directly into the camera lens with a warm, charming, energetic smile and lifelike eye contact, "
            "speaking naturally with accurate Vietnamese lip-sync while holding the exact product from the reference image steady at waist-to-chest level."
        )
        header_line = (
            "A hyper-photorealistic 10-second vertical 9:16 video starting directly from the provided 2K reference image, "
            f"{base_lens_desc}. Preserve 100% of the character's exact facial identity, visible natural skin pores, "
            f"the exact {prod_type_en} in hand, the items on the foreground table, and {bg_short_en} in the background — "
            "do not zoom in excessively on the face and do not blur out the credible workshop/store environment."
        )
        body_section = f"ACTION: {action_str}{motion_clause}{fx_clauses['single_shot_fx']}"

    return (
        f"{header_line}\n\n"
        f"{body_section}\n\n"
        f"VOICE{voice_dir} — read the dialogue in 3 timed segments exactly as marked. Keep a steady, even pace so each segment "
        "fills its time window. Finish the last word exactly at 10.0 seconds. Read each word exactly once — "
        "no repetition, no looping, no added words, then stay silent:\n"
        f"{voice_block}\n\n"
        "No on-screen text, no AI subtitles, no floating words, no background music, no watermark.\n"
        "Negative: on-screen text, subtitles, captions, floating words, cluttered HUD covering face, extreme close-up face crop, "
        "lost background environment, AI plastic skin, waxy face, altered face, crossed or blurry eyes, glasses glare, warped mouth, "
        "changed product, altered product design, repeating voice, looping dialogue, second voice pass"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. CẬP NHẬT NHANH `prompts.json` CỦA DỰ ÁN VỚI GÓC MÁY B-ROLL & HIỆU ỨNG AI FX
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_timed_dialogue_lines(prompt_text: str) -> list:
    matches = re.findall(r'^\[[0-9.]+-[0-9.]+s\]\s*".*"$', prompt_text or "", flags=re.MULTILINE)
    if len(matches) >= 3:
        return matches[:3]
    out = []
    for ln in (prompt_text or "").splitlines():
        ln_s = ln.strip()
        if ln_s.startswith("[") and "s]" in ln_s:
            out.append(ln_s)
    return out[:3]


def _extract_voice_prompt_from_scene_prompt(prompt_text: str) -> str:
    m = re.search(r"VOICE\s*\((.*?)\)\s*—\s*read the dialogue", prompt_text or "", flags=re.S)
    if m:
        return m.group(1).strip()
    return ""


def upgrade_project_prompts_with_camera_broll(
    pid: str,
    projects_dir: str,
    cam_settings: dict = None,
    fx_settings: dict = None,
) -> dict:
    """
    Cập nhật lại toàn bộ `ref_image_prompt` (sang góc Medium-Full 35mm rõ hậu cảnh Nhà xưởng/Kho/Showroom)
    và `scenes[i]["prompt"]` (sang cấu trúc `SHOT 1 -> SHOT 2 Macro B-Roll Insert -> SHOT 3` + Hiệu ứng AI Visual FX không chữ)
    trong `projects/<pid>/prompts.json` và `spec_*.json`.
    """
    pdir = os.path.join(projects_dir, str(pid))
    prompts_path = os.path.join(pdir, "prompts.json")
    if not os.path.isfile(prompts_path):
        return {"ok": False, "error": f"Không tìm thấy {prompts_path}"}

    cfg = {**DEFAULT_CAMERA_BROLL_SETTINGS, **(cam_settings or {})}
    fx_cfg = {**DEFAULT_VIDEO_EDIT_FX_SETTINGS, **(fx_settings or {})}
    data = json.load(open(prompts_path, "r", encoding="utf-8"))
    pname = data.get("product_name") or ""

    ws_dir = os.path.dirname(os.path.abspath(projects_dir))
    vc_path = os.path.join(ws_dir, "flow_final_pipeline", "voices_and_characters.json")
    chars_data = json.load(open(vc_path, "r", encoding="utf-8")) if os.path.isfile(vc_path) else {}
    chars_dict = chars_data.get("characters", {})
    voices_dict = chars_data.get("voices", {})

    tpl_cfg_path = os.path.join(ws_dir, "Template", "Nhà Xưởng", "template_config.json")
    tpl_cfg = json.load(open(tpl_cfg_path, "r", encoding="utf-8")) if os.path.isfile(tpl_cfg_path) else {}
    char_presets_map = tpl_cfg.get("character_presets", {})
    scene_actions = tpl_cfg.get("scene_actions", {})

    text_low = pname.lower()
    if "khăn lưới" in text_low or "rửa chén" in text_low or "miếng cọ" in text_low:
        prod_type_en = "20x20cm silver diamond-weave metal mesh dishwashing cloth"
        prod_scale_en = "true-to-life 20x20cm palm-sized flexible mesh dishcloth held naturally between both hands"
    elif "cân tiểu ly" in text_low or "cân điện tử" in text_low:
        prod_type_en = "compact stainless-steel digital kitchen scale"
        prod_scale_en = "true-to-life compact 18x14cm hand-held digital scale relative to the hands and body"
    elif "thắt lưng" in text_low or "dây nịt" in text_low:
        prod_type_en = "men's belt with metal buckle"
        prod_scale_en = "true-to-life palm-sized coiled belt and gift box scale relative to the hands and body"
    else:
        prod_type_en = "authentic product item"
        prod_scale_en = "true-to-life natural hand-held scale relative to the hands and body"

    updated_variants = 0
    updated_scenes = 0

    for vkey, v_info in (data.get("videos") or {}).items():
        ck = (v_info.get("character") or "nv1").lower()
        cval = chars_dict.get(ck, {})
        voice_key = cval.get("default_voice", ck)
        v_obj = voices_dict.get(voice_key, {})
        voice_gender = cval.get("voice_gender") or v_obj.get("gender") or ("male" if "nv3" in ck else "female")
        voice_prompt_en = cval.get("voice_prompt_en") or v_obj.get("voice_prompt_en", "")
        appearance_en = cval.get("appearance_en") or ""

        presets = char_presets_map.get(ck) or []
        preset_match = next(
            (p for p in presets if p.get("legacy_vkey") == vkey or p.get("char_v") == v_info.get("char_v")),
            presets[0] if presets else {},
        )
        outfit_en = preset_match.get("outfit_en") or "wearing a smart open tailored blazer over a fitted knit top"
        setting_en = preset_match.get("setting_en") or ""

        new_ref_prompt = build_credible_environment_ref_prompt(
            ck=ck,
            appearance_en=appearance_en,
            outfit_en=outfit_en,
            setting_en=setting_en,
            prod_type_en=prod_type_en,
            prod_scale_en=prod_scale_en,
            gender=voice_gender,
            cam_settings=cfg,
        )
        v_info["ref_image_prompt"] = new_ref_prompt
        v_info["camera_broll_settings"] = cfg
        v_info["video_edit_fx_settings"] = fx_cfg
        updated_variants += 1

        for idx_s, sc in enumerate(v_info.get("scenes") or [], start=1):
            old_p = sc.get("prompt") or ""
            timed = _extract_timed_dialogue_lines(old_p)
            vp_en = voice_prompt_en or _extract_voice_prompt_from_scene_prompt(old_p)
            if timed:
                sc["prompt"] = build_scene_video_prompt_with_broll(
                    scene_idx=idx_s,
                    timed_lines=timed,
                    scene_actions=scene_actions,
                    voice_prompt_en=vp_en,
                    prod_type_en=prod_type_en,
                    setting_en=setting_en,
                    cam_settings=cfg,
                    fx_settings=fx_cfg,
                )
                updated_scenes += 1

        spec_p = os.path.join(pdir, f"spec_{vkey}.json")
        if os.path.isfile(spec_p):
            try:
                sp_obj = json.load(open(spec_p, "r", encoding="utf-8"))
                sp_obj["product_name"] = pname
                sp_obj["camera_broll_settings"] = cfg
                sp_obj["video_edit_fx_settings"] = fx_cfg
                with open(spec_p, "w", encoding="utf-8") as sf:
                    json.dump(sp_obj, sf, ensure_ascii=False, indent=2)
            except Exception:
                pass

    if "v1" in (data.get("videos") or {}):
        data["ref_img_prompt_nv1"] = data["videos"]["v1"]["ref_image_prompt"]
    if "v2" in (data.get("videos") or {}):
        data["ref_img_prompt_nv2"] = data["videos"]["v2"]["ref_image_prompt"]
    data["camera_broll_settings"] = cfg
    data["video_edit_fx_settings"] = fx_cfg

    with open(prompts_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "ok": True,
        "pid": pid,
        "updated_variants": updated_variants,
        "updated_scenes": updated_scenes,
        "camera_broll_settings": cfg,
        "video_edit_fx_settings": fx_cfg,
    }


def render_edit_fx_overlays_for_video(*args, **kwargs) -> list:
    """
    Đã loại bỏ hoàn toàn việc vẽ đè hình Pillow hậu kỳ lên video (vì hiệu ứng được mô tả trực tiếp
    trong Prompt Render AI Video và phụ đề được xử lý bởi Kho Template Subtitle chuyên nghiệp).
    """
    return []
