# -*- coding: utf-8 -*-
"""
🎬 KHO TEMPLATE SUBTITLE & STUDIO TÙY CHỈNH PHỤ ĐỀ CHUYÊN NGHIỆP (`subtitle_template_engine.py`)
  - Mặc định giữ nguyên 100% chuẩn phụ đề hiện tại được người dùng yêu thích:
    + Font: DejaVu Sans / Arial Bold, cỡ chữ 48 (trên khung chuẩn 1080x1920)
    + Màu chính (Primary): Trắng (#FFFFFF) | Màu Karaoke / Highlight (Secondary): Vàng Gold (#FFE066)
    + Viền chữ (Outline): Đen (#000000) dày 3px, Bóng đổ (Shadow): 0px, Vị trí đáy MarginV: 225px
    + Hiệu ứng: Karaoke chạy từng từ (`karaoke_word`) + Fade-in/out (150ms) + Tự động IN HOA.
  - Cung cấp 16 Template Subtitle chuyên nghiệp chia theo 6 nhóm phong cách (kèm ảnh Demo 1080x1920 thực tế).
  - Hỗ trợ chế độ Tự Custom 100% thông số: Font, cỡ chữ, màu chính, màu highlight, màu viền, độ dày viền,
    độ sâu bóng, hộp nền (Background Pill/Box), độ mờ hộp nền, vị trí (MarginV, Alignment), khoảng cách chữ,
    IN HOA / Chữ thường, và 7 kiểu hiệu ứng chuyển động ASS.
"""
import os
import re
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
WS_DIR = os.path.abspath(os.path.join(PIPELINE_DIR, ".."))
SUB_TEMPLATES_DIR = os.path.join(WS_DIR, "Template", "Subtitle_Templates")
SUB_SAMPLES_DIR = os.path.join(SUB_TEMPLATES_DIR, "samples")
os.makedirs(SUB_SAMPLES_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DANH MỤC NHÓM PHONG CÁCH & CÁC TÙY CHỌN FONT / HIỆU ỨNG
# ═══════════════════════════════════════════════════════════════════════════════

SUBTITLE_CATEGORIES = [
    {"id": "karaoke_pro", "name": "⭐ Karaoke Chuẩn & Viral"},
    {"id": "tiktok_sales", "name": "🔥 Chốt Sale & Nhà Xưởng"},
    {"id": "box_banner", "name": "⬛ Hộp Nền & Dạ Quang"},
    {"id": "fashion_luxury", "name": "🌸 Thời Trang & Luxury"},
    {"id": "tech_modern", "name": "💎 Công Nghệ & 2 Dòng"},
    {"id": "cinema_clean", "name": "🎬 Điện Ảnh Tối Giản"},
]

AVAILABLE_SUBTITLE_FONTS = [
    {"id": "DejaVu Sans", "name": "DejaVu Sans (Mặc định chuẩn hiện tại — Sắc nét, rõ dấu Tiếng Việt)", "win_font": "arialbd.ttf"},
    {"id": "Arial", "name": "Arial Bold (Hiện đại, gọn gàng, chuẩn TikTok / CapCut)", "win_font": "arialbd.ttf"},
    {"id": "Segoe UI", "name": "Segoe UI Bold (Mềm mại, thanh lịch, dễ đọc trên điện thoại)", "win_font": "segoeuib.ttf"},
    {"id": "Tahoma", "name": "Tahoma Bold (Chữ dày, chân phương, cực hợp Nhà xưởng & Gia dụng)", "win_font": "tahomabd.ttf"},
    {"id": "Impact", "name": "Impact / Arial Black (Siêu đậm, báo giá Flash Sale cực mạnh)", "win_font": "impact.ttf"},
    {"id": "Verdana", "name": "Verdana Bold (Bề ngang rộng, thoáng mắt, hợp người lớn tuổi)", "win_font": "verdanab.ttf"},
    {"id": "Trebuchet MS", "name": "Trebuchet MS Bold (Trẻ trung, năng động, hợp GenZ & Creator)", "win_font": "trebucbd.ttf"},
    {"id": "Times New Roman", "name": "Times New Roman Bold (Cổ điển, sang trọng, hợp Showroom Luxury)", "win_font": "timesbd.ttf"},
]

SUBTITLE_ANIMATION_STYLES = [
    {
        "id": "karaoke_word",
        "name": "🎤 Karaoke Từng Từ Chuẩn Hiện Tại (Đổi màu Vàng Gold → Trắng theo nhịp đọc)",
    },
    {
        "id": "karaoke_smooth",
        "name": "🌊 Karaoke Trượt Mượt (Quét màu mượt từ trái sang phải trên từng từ — \\kf)",
    },
    {
        "id": "pop_karaoke",
        "name": "💥 Pop-In Nảy Nhẹ Khi Vào Câu + Karaoke Từng Từ (Tăng tương tác thị giác)",
    },
    {
        "id": "keyword_highlight",
        "name": "🏷️ Tự Động Tô Màu Từ Khóa Giá Bán & USP (18K, 20K, TẬN XƯỞNG, GIỎ HÀNG...)",
    },
    {
        "id": "dual_line_split",
        "name": "📑 Phụ Đề 2 Dòng Cân Đối (Dòng 1 Màu Chính + Dòng 2 Màu Highlight)",
    },
    {
        "id": "glow_neon",
        "name": "✨ Viền Phát Sáng Neon (Soft Glow Edge + Karaoke Hiện Đại)",
    },
    {
        "id": "clean_fade",
        "name": "🎬 Hiện Mượt Đơn Sắc (Fade In/Out Điện Ảnh — Không nhảy màu Karaoke)",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CẤU HÌNH SUBTITLE MẶC ĐỊNH (GIỮ NGUYÊN 100% CHUẨN HIỆN TẠI)
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_SUBTITLE_SETTINGS = {
    "enable_subtitles": True,
    "selection_mode": "preset",              # 'preset' | 'custom'
    "preset_id": "default_karaoke_gold",
    "font_family": "DejaVu Sans",
    "font_size": 48,
    "bold": True,
    "italic": False,
    "uppercase": True,
    "primary_color": "#FFFFFF",              # Màu chữ chính (Trắng)
    "secondary_color": "#FFE066",            # Màu chữ Karaoke / Highlight (Vàng Gold dịu chuẩn hiện tại)
    "outline_color": "#000000",              # Màu viền chữ (Đen)
    "outline_width": 3.0,                    # Độ dày viền (3px chuẩn hiện tại)
    "shadow_color": "#000000",               # Màu bóng đổ / hộp nền
    "shadow_opacity": 50,                    # Độ đậm bóng đổ (0 - 100%)
    "shadow_depth": 0.0,                     # Độ lệch bóng đổ (0px chuẩn hiện tại)
    "border_style": 1,                       # 1 = Viền chữ chuẩn | 3 = Hộp nền chữ nhật (Opaque/Semi-transparent Box)
    "box_bg_color": "#000000",               # Màu nền hộp khi border_style == 3
    "box_bg_opacity": 72,                    # Độ đậm nền hộp (0 - 100%)
    "alignment": 2,                          # 2 = Giữa-Dưới (Chuẩn TikTok) | 5 = Giữa màn hình | 8 = Giữa-Trên
    "margin_v": 225,                         # Khoảng cách từ đáy lên = 225px (Chuẩn hiện tại)
    "margin_h": 30,                          # Lề trái/phải = 30px
    "letter_spacing": 0.0,                   # Khoảng cách giữa các ký tự
    "animation_style": "karaoke_word",       # 'karaoke_word' | 'karaoke_smooth' | 'pop_karaoke' | 'keyword_highlight' | 'dual_line_split' | 'glow_neon' | 'clean_fade'
    "fade_in_ms": 150,
    "fade_out_ms": 150,
}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. KHO 16 TEMPLATE SUBTITLE CHUYÊN NGHIỆP (`SUBTITLE_TEMPLATES`)
# ═══════════════════════════════════════════════════════════════════════════════

SUBTITLE_TEMPLATES = [
    # 1. Mặc định hiện tại
    {
        "id": "default_karaoke_gold",
        "code": "SUB-001",
        "category": "karaoke_pro",
        "name": "⭐ #01. Mặc Định Hiện Tại — Karaoke Trắng & Vàng Gold (#FFE066)",
        "style_badge": "🎤 Karaoke Chuẩn Hiện Tại • Cỡ 48 • Viền Đen 3px",
        "description": "Phong cách phụ đề mặc định đang dùng: Chữ IN HOA cỡ 48, trắng tinh khiết kết hợp Karaoke vàng gold dịu (#FFE066), viền đen 3px sắc nét ở vị trí đáy 225px.",
        "recommended_for": "Mọi ngành hàng (Gia dụng, Nhà xưởng, Thời trang, Đồ ăn vặt)",
        "demo_line": "PHẨM KHĂN LƯỚI KIM LOẠI RỬA",
        "demo_highlight_words": ["LOẠI", "RỬA"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "default_karaoke_gold",
            "font_family": "DejaVu Sans",
            "font_size": 48,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFFFFF",
            "secondary_color": "#FFE066",
            "outline_color": "#000000",
            "outline_width": 3.0,
            "shadow_depth": 0.0,
            "border_style": 1,
            "alignment": 2,
            "margin_v": 225,
            "animation_style": "karaoke_word",
        },
    },
    # 2. CapCut Mint Viral
    {
        "id": "capcut_mint_viral",
        "code": "SUB-002",
        "category": "karaoke_pro",
        "name": "🌿 #02. CapCut Viral — Trắng & Xanh Mint (#86EFAC) Pop Nhẹ",
        "style_badge": "💥 Pop-In + Karaoke Xanh Mint • Cỡ 50",
        "description": "Phụ đề xu hướng CapCut Creator: Chữ trắng viền đen dày 3.5px, từ đang đọc sáng màu Xanh Mint (#86EFAC) kèm hiệu ứng nảy nhẹ khi chuyển câu.",
        "recommended_for": "Review Công nghệ, Gia dụng thông minh, Kênh xây nhân hiệu",
        "demo_line": "THẤY MỘT GIÁ KHÁC NHAU BẤM",
        "demo_highlight_words": ["NHAU", "BẤM"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "capcut_mint_viral",
            "font_family": "Arial",
            "font_size": 50,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFFFFF",
            "secondary_color": "#86EFAC",
            "outline_color": "#090D16",
            "outline_width": 3.5,
            "shadow_depth": 1.5,
            "border_style": 1,
            "alignment": 2,
            "margin_v": 230,
            "animation_style": "pop_karaoke",
        },
    },
    # 3. Karaoke Smooth Emerald
    {
        "id": "fresh_emerald_smooth",
        "code": "SUB-003",
        "category": "karaoke_pro",
        "name": "🍀 #03. Karaoke Trượt Mượt — Trắng & Xanh Ngọc Lục Bảo (#34D399)",
        "style_badge": "🌊 Quét Màu Mượt (\\kf) • Cỡ 48",
        "description": "Hiệu ứng quét màu mượt liên tục từ trái sang phải trên từng từ bằng tông Xanh Ngọc Lục Bảo tươi mát và chữ trắng viền đen.",
        "recommended_for": "Đồ bếp sạch, Thực phẩm, Sức khỏe, Mẹ & Bé",
        "demo_line": "SẠCH BÓNG DẦU MỠ KHÔNG TRẦY NỒI",
        "demo_highlight_words": ["KHÔNG", "TRẦY", "NỒI"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "fresh_emerald_smooth",
            "font_family": "Segoe UI",
            "font_size": 48,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFFFFF",
            "secondary_color": "#34D399",
            "outline_color": "#06281E",
            "outline_width": 3.2,
            "shadow_depth": 1.0,
            "border_style": 1,
            "alignment": 2,
            "margin_v": 225,
            "animation_style": "karaoke_smooth",
        },
    },
    # 4. TikTok Flash Sale Orange-Red
    {
        "id": "tiktok_flash_sale_orange",
        "code": "SUB-004",
        "category": "tiktok_sales",
        "name": "🔥 #04. TikTok Flash Sale — Vàng Rực (#FFE600) Viền Đỏ Đậm",
        "style_badge": "🔥 Chốt Đơn Giá Sốc • Cỡ 52 • Viền Đỏ 4px",
        "description": "Tông màu kích thích mua hàng mạnh nhất trên TikTok Shop: Chữ Vàng Rực (#FFE600) đổi sang Trắng khi đọc, bao quanh bởi viền Đỏ Đậm (#7F1D1D) dày 4px.",
        "recommended_for": "Video báo giá sốc, Xả kho, Deal 18K - 29K, Livestream cắt clip",
        "demo_line": "18K CHO SIÊU PHẨM KHĂN LƯỚI",
        "demo_highlight_words": ["18K", "SIÊU", "PHẨM"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "tiktok_flash_sale_orange",
            "font_family": "Arial",
            "font_size": 52,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFE600",
            "secondary_color": "#FFFFFF",
            "outline_color": "#7F1D1D",
            "outline_width": 4.0,
            "shadow_depth": 2.0,
            "border_style": 1,
            "alignment": 2,
            "margin_v": 230,
            "animation_style": "pop_karaoke",
        },
    },
    # 5. Factory Industrial Amber
    {
        "id": "factory_industrial_amber",
        "code": "SUB-005",
        "category": "tiktok_sales",
        "name": "🏭 #05. Nhà Xưởng Uy Tín — Trắng & Cam Hổ Phách (#F59E0B) Viền Dày",
        "style_badge": "🏭 Chuẩn Kho Xưởng • Font Tahoma 49 • Viền 4px",
        "description": "Thiết kế riêng cho bối cảnh Nhà xưởng / Kho pallet nhiều chi tiết: Font Tahoma nét dày, chữ Trắng kết hợp Cam Hổ Phách (#F59E0B) và viền đen 4px nổi bật tuyệt đối.",
        "recommended_for": "Template #001 Nhà Xưởng, Đồ cơ khí, Gia dụng inox, Phụ kiện ô tô",
        "demo_line": "XUẤT TRỰC TIẾP TẠI XƯỞNG KHÔNG QUA TRUNG GIAN",
        "demo_highlight_words": ["TẠI", "XƯỞNG"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "factory_industrial_amber",
            "font_family": "Tahoma",
            "font_size": 49,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFFFFF",
            "secondary_color": "#F59E0B",
            "outline_color": "#000000",
            "outline_width": 4.0,
            "shadow_depth": 2.0,
            "border_style": 1,
            "alignment": 2,
            "margin_v": 225,
            "animation_style": "karaoke_word",
        },
    },
    # 6. Hormozi Keyword Pop
    {
        "id": "hormozi_keyword_pop",
        "code": "SUB-006",
        "category": "tiktok_sales",
        "name": "⚡ #06. Hormozi Creator Pro — Tự Tô Màu Từ Khóa Giá & Chốt Đơn",
        "style_badge": "🏷️ Highlight Giá & USP • Cỡ 52 • Bóng Đổ Sâu",
        "description": "Tự động nhận diện các con số báo giá (18K, 20K, 50%), từ khóa 'TẬN XƯỞNG', 'GIỎ HÀNG', 'MIỄN PHÍ' để tô màu Vàng Chanh (#FACC15) và phóng nhẹ nổi bật.",
        "recommended_for": "Video so sánh giá 3 tầng, Video review phân tích lợi ích",
        "demo_line": "GIÁ XƯỞNG CHỈ 18K BẤM GIỎ HÀNG NGAY",
        "demo_highlight_words": ["18K", "GIỎ", "HÀNG"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "hormozi_keyword_pop",
            "font_family": "Segoe UI",
            "font_size": 52,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFFFFF",
            "secondary_color": "#FACC15",
            "outline_color": "#000000",
            "outline_width": 3.8,
            "shadow_depth": 2.5,
            "border_style": 1,
            "alignment": 2,
            "margin_v": 235,
            "animation_style": "keyword_highlight",
        },
    },
    # 7. Pill Box Dark News
    {
        "id": "pill_box_dark_news",
        "code": "SUB-007",
        "category": "box_banner",
        "name": "⬛ #07. Hộp Đen Bán Trong Suốt — Chữ Trắng & Vàng Gold (Chuyên Gia)",
        "style_badge": "⬛ Có Hộp Nền Đen Mờ • Cỡ 44 • Dễ Đọc 100%",
        "description": "Đặt phụ đề trong dải hộp nền đen mờ sang trọng (opacity 75%), giúp chữ Trắng và Vàng Gold đọc rõ 100% ngay cả khi nhân vật mặc áo trắng hoặc nền sáng.",
        "recommended_for": "Dược sĩ, Bác sĩ, Chuyên gia kỹ thuật, Đồ công nghệ, Sách",
        "demo_line": "MẪU KHĂN LƯỚI KIM LOẠI RỬA CHÉN ĐA NĂNG",
        "demo_highlight_words": ["ĐA", "NĂNG"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "pill_box_dark_news",
            "font_family": "Segoe UI",
            "font_size": 44,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFFFFF",
            "secondary_color": "#FFE066",
            "outline_color": "#0F172A",
            "outline_width": 1.5,
            "shadow_depth": 0.0,
            "border_style": 3,
            "box_bg_color": "#0F172A",
            "box_bg_opacity": 78,
            "alignment": 2,
            "margin_v": 225,
            "animation_style": "karaoke_word",
        },
    },
    # 8. Pill Box Red Deal
    {
        "id": "pill_box_red_deal",
        "code": "SUB-008",
        "category": "box_banner",
        "name": "🟥 #08. Hộp Đỏ Săn Deal TikTok — Chữ Trắng & Vàng Trên Nền Đỏ",
        "style_badge": "🟥 Hộp Nền Đỏ Nổi Bật • Cỡ 45 • Chốt Sale",
        "description": "Dải băng nền Đỏ tươi thương mại (#DC2626) kết hợp chữ Trắng và Karaoke Vàng Nhạt (#FEF08A), tạo cảm giác khẩn cấp săn sale giờ vàng.",
        "recommended_for": "Chiến dịch Flash Sale, Ngày đôi 11.11 / 12.12, Xả hàng tồn kho",
        "demo_line": "TRỢ GIÁ SÀN TIKTOK CHỈ CÒN 18K HÔM NAY",
        "demo_highlight_words": ["18K", "HÔM", "NAY"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "pill_box_red_deal",
            "font_family": "Arial",
            "font_size": 45,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFFFFF",
            "secondary_color": "#FEF08A",
            "outline_color": "#991B1B",
            "outline_width": 1.5,
            "shadow_depth": 0.0,
            "border_style": 3,
            "box_bg_color": "#DC2626",
            "box_bg_opacity": 86,
            "alignment": 2,
            "margin_v": 225,
            "animation_style": "karaoke_word",
        },
    },
    # 9. Highlighter Yellow Black
    {
        "id": "highlighter_yellow_black",
        "code": "SUB-009",
        "category": "box_banner",
        "name": "🖍️ #09. Bút Dạ Quang Vàng Chanh — Nền Vàng (#FACC15) Chữ Đen Đậm",
        "style_badge": "🖍️ Nền Vàng Chữ Đen • Cỡ 44 • Cực Bắt Mắt",
        "description": "Phong cách bút dạ quang tô sáng: Hộp nền Vàng Chanh rực rỡ (#FACC15) đi cùng chữ Đen đậm (#0F172A) và từ khóa Đỏ Đậm (#B91C1C).",
        "recommended_for": "Đồ gia dụng tiện ích, Mẹo vặt nhà cửa, Dụng cụ sửa chữa",
        "demo_line": "MUA 1 COMBO DÙNG BỀN CẢ NĂM KHÔNG HỎNG",
        "demo_highlight_words": ["CẢ", "NĂM"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "highlighter_yellow_black",
            "font_family": "Arial",
            "font_size": 44,
            "bold": True,
            "uppercase": True,
            "primary_color": "#0F172A",
            "secondary_color": "#B91C1C",
            "outline_color": "#FACC15",
            "outline_width": 1.5,
            "shadow_depth": 0.0,
            "border_style": 3,
            "box_bg_color": "#FACC15",
            "box_bg_opacity": 90,
            "alignment": 2,
            "margin_v": 225,
            "animation_style": "karaoke_word",
        },
    },
    # 10. Pastel Coquette Pink
    {
        "id": "pastel_coquette_pink",
        "code": "SUB-010",
        "category": "fashion_luxury",
        "name": "🌸 #10. Pastel Coquette — Trắng & Hồng Phấn Viền Hồng Dâu (#9D174D)",
        "style_badge": "🌸 Mỹ Phẩm & Thời Trang Nữ • Cỡ 47 • Mềm Mại",
        "description": "Tông màu ngọt ngào chuẩn Hàn Quốc: Chữ Trắng kết hợp Karaoke Hồng Phấn (#FBCFE8) trên nền viền Hồng Dâu đậm (#9D174D) tôn da và trang phục.",
        "recommended_for": "Thời trang nữ, Đầm thiết kế, Mỹ phẩm, Phụ kiện kẹp tóc, Túi ví Cute",
        "demo_line": "CHẤT VẢI MỀM MỊN LÊN FORM CỰC XINH",
        "demo_highlight_words": ["CỰC", "XINH"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "pastel_coquette_pink",
            "font_family": "Segoe UI",
            "font_size": 47,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFFFFF",
            "secondary_color": "#FBCFE8",
            "outline_color": "#9D174D",
            "outline_width": 3.4,
            "shadow_depth": 1.2,
            "border_style": 1,
            "alignment": 2,
            "margin_v": 225,
            "animation_style": "karaoke_smooth",
        },
    },
    # 11. Luxury Champagne Gold
    {
        "id": "luxury_champagne_gold",
        "code": "SUB-011",
        "category": "fashion_luxury",
        "name": "✨ #11. Luxury Showroom — Vàng Champagne (#FDE68A) Viền Nâu Đen",
        "style_badge": "✨ Sang Trọng Lịch Lãm • Cỡ 46 • Đồ Da & Nam",
        "description": "Phối màu Champagne & Espresso cao cấp: Chữ Trắng Kem (#FFFBEB) chuyển Karaoke Vàng Champagne (#FDE68A), viền Nâu Đen đậm (#1C1917).",
        "recommended_for": "Giày tây nam, Thắt lưng da, Ví da, Đồng hồ, Nước hoa, Showroom Luxury",
        "demo_line": "BẢO HÀNH CHÍNH HÃNG KIỂM TRA TRƯỚC KHI NHẬN",
        "demo_highlight_words": ["CHÍNH", "HÃNG"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "luxury_champagne_gold",
            "font_family": "Segoe UI",
            "font_size": 46,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFFBEB",
            "secondary_color": "#FCD34D",
            "outline_color": "#1C1917",
            "outline_width": 3.4,
            "shadow_depth": 1.8,
            "border_style": 1,
            "alignment": 2,
            "margin_v": 225,
            "animation_style": "karaoke_word",
        },
    },
    # 12. GenZ Purple Pink Pop
    {
        "id": "genz_purple_pink_pop",
        "code": "SUB-012",
        "category": "fashion_luxury",
        "name": "🎵 #12. GenZ Sticker Pop — Trắng & Hồng Neon (#F472B6) Viền Tím Than",
        "style_badge": "🎵 GenZ OOTD & Đồ Ăn Vặt • Cỡ 50 • Năng Động",
        "description": "Phong cách trẻ trung bắt trend TikTok GenZ: Chữ Trắng cỡ 50 + Highlight Hồng Neon (#F472B6), viền Tím Than đậm (#2E1065) dày 3.8px kèm hiệu ứng nảy chữ.",
        "recommended_for": "Quần Jogger, Đồ ngủ Pijama, Giày Sneaker, Đồ ăn vặt (#002, #003)",
        "demo_line": "CẦM TRÊN TAY MỚI THẤY ĐỘ XỊN CỦA NÓ",
        "demo_highlight_words": ["ĐỘ", "XỊN"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "genz_purple_pink_pop",
            "font_family": "Trebuchet MS",
            "font_size": 50,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFFFFF",
            "secondary_color": "#F472B6",
            "outline_color": "#2E1065",
            "outline_width": 3.8,
            "shadow_depth": 1.8,
            "border_style": 1,
            "alignment": 2,
            "margin_v": 225,
            "animation_style": "pop_karaoke",
        },
    },
    # 13. Cyber Neon Cyan
    {
        "id": "cyber_neon_cyan",
        "code": "SUB-013",
        "category": "tech_modern",
        "name": "💎 #13. Tech Neon Cyan — Chữ Trắng Phát Sáng Xanh Điện Tử (#22D3EE)",
        "style_badge": "💎 Neon Glow Hiện Đại • Cỡ 48 • Điện Tử & Y Tế",
        "description": "Hiệu ứng phát sáng viền xanh công nghệ: Chữ Trắng kết hợp Karaoke Xanh Cyan (#22D3EE) và viền Xanh Đen (#083344) có hiệu ứng Glow nhẹ.",
        "recommended_for": "Cân điện tử, Máy đo y tế, Đèn LED, Thiết bị điện gia dụng",
        "demo_line": "ĐỘ BỀN VƯỢT TRỘI TÁI SỬ DỤNG HÀNG TRĂM LẦN",
        "demo_highlight_words": ["VƯỢT", "TRỘI"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "cyber_neon_cyan",
            "font_family": "Segoe UI",
            "font_size": 48,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFFFFF",
            "secondary_color": "#22D3EE",
            "outline_color": "#083344",
            "outline_width": 3.6,
            "shadow_depth": 1.5,
            "border_style": 1,
            "alignment": 2,
            "margin_v": 225,
            "animation_style": "glow_neon",
        },
    },
    # 14. Dual Line Gold Split
    {
        "id": "dual_line_gold_split",
        "code": "SUB-014",
        "category": "tech_modern",
        "name": "📑 #14. Phụ Đề 2 Tầng (Dual-Line) — Dòng Trên Trắng & Dòng Dưới Vàng Gold",
        "style_badge": "📑 Tự Chia 2 Dòng Cân Đối • Cỡ 48 • Rõ Ràng",
        "description": "Tự động ngắt mỗi cụm thoại thành 2 dòng ngắn gọn ở giữa đáy: Dòng 1 màu Trắng (#FFFFFF), Dòng 2 màu Vàng Gold (#FFE066), không bao giờ tràn lề ngang.",
        "recommended_for": "Câu thoại dài, Video thuyết minh chi tiết công năng sản phẩm",
        "demo_line": "CÁI NÀY LÀ CHO CÁC BÁC\nXẢ KHO TẬN GỐC CHỈ 18K",
        "demo_highlight_words": ["XẢ", "KHO", "TẬN", "GỐC", "CHỈ", "18K"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "dual_line_gold_split",
            "font_family": "Arial",
            "font_size": 48,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFFFFF",
            "secondary_color": "#FFE066",
            "outline_color": "#000000",
            "outline_width": 3.5,
            "shadow_depth": 1.5,
            "border_style": 1,
            "alignment": 2,
            "margin_v": 220,
            "animation_style": "dual_line_split",
        },
    },
    # 15. Center Product Focus
    {
        "id": "center_product_focus",
        "code": "SUB-015",
        "category": "tech_modern",
        "name": "🎯 #15. Vị Trí Cao Ngang Tay Cầm SP (MarginV 420) — Chữ Lớn Cỡ 52",
        "style_badge": "🎯 Nằm Ngay Dưới Sản Phẩm • Cỡ 52 • Thu Hút Mắt",
        "description": "Đặt phụ đề cao hơn (MarginV = 420px, ngay dưới bàn tay cầm sản phẩm) để mắt người xem vừa nhìn sản phẩm vừa đọc chữ cùng lúc mà không phải liếc xuống đáy.",
        "recommended_for": "Video B-Roll cận cảnh sản phẩm, Video unbox trên bàn",
        "demo_line": "LƯỚI KIM LOẠI DỆT KIM CƯƠNG SIÊU BỀN",
        "demo_highlight_words": ["KIM", "CƯƠNG", "SIÊU", "BỀN"],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "center_product_focus",
            "font_family": "Arial",
            "font_size": 52,
            "bold": True,
            "uppercase": True,
            "primary_color": "#FFFFFF",
            "secondary_color": "#FFE066",
            "outline_color": "#000000",
            "outline_width": 3.8,
            "shadow_depth": 2.0,
            "border_style": 1,
            "alignment": 2,
            "margin_v": 420,
            "animation_style": "pop_karaoke",
        },
    },
    # 16. Cinema Minimal Warm
    {
        "id": "cinema_minimal_warm",
        "code": "SUB-016",
        "category": "cinema_clean",
        "name": "🎬 #16. Điện Ảnh Tối Giản (Cinema) — Vàng Nhạt Cỡ 42 Không Nhảy Màu",
        "style_badge": "🎬 Fade Mượt Đơn Sắc • Cỡ 42 • Tinh Tế",
        "description": "Phụ đề phim điện ảnh tinh tế: Chữ Vàng Nhạt (#FEF08A) cỡ 42 vừa phải, viền đen mỏng 2.4px, chỉ Fade-in/out mượt mà, giữ khung hình sạch tuyệt đối.",
        "recommended_for": "Showroom cao cấp, Thời trang thiết kế, Review nhẹ nhàng sâu lắng",
        "demo_line": "Phiếu bảo hành đi kèm trong từng kiện hàng xuất xưởng",
        "demo_highlight_words": [],
        "settings": {
            **DEFAULT_SUBTITLE_SETTINGS,
            "preset_id": "cinema_minimal_warm",
            "font_family": "Segoe UI",
            "font_size": 42,
            "bold": True,
            "uppercase": False,
            "primary_color": "#FEF08A",
            "secondary_color": "#FEF08A",
            "outline_color": "#000000",
            "outline_width": 2.4,
            "shadow_depth": 1.0,
            "border_style": 1,
            "alignment": 2,
            "margin_v": 215,
            "animation_style": "clean_fade",
        },
    },
]


def get_subtitle_template_by_id(preset_id: str) -> dict:
    q = (preset_id or "default_karaoke_gold").strip().lower()
    for tpl in SUBTITLE_TEMPLATES:
        if tpl["id"].lower() == q or tpl.get("code", "").lower() == q:
            return tpl
    return SUBTITLE_TEMPLATES[0]


def resolve_subtitle_settings(raw_settings: dict = None) -> dict:
    """
    Hợp nhất cấu hình Subtitle:
      - Nếu `selection_mode == 'preset'` (mặc định): Lấy thông số gốc từ `preset_id` trong `SUBTITLE_TEMPLATES`,
        nhưng vẫn giữ cờ `enable_subtitles` theo người dùng chọn.
      - Nếu `selection_mode == 'custom'`: Lấy toàn bộ thông số tùy chỉnh của người dùng.
    """
    base = dict(DEFAULT_SUBTITLE_SETTINGS)
    if not isinstance(raw_settings, dict):
        return base

    mode = str(raw_settings.get("selection_mode") or "preset").strip().lower()
    preset_id = str(raw_settings.get("preset_id") or "default_karaoke_gold").strip()
    tpl = get_subtitle_template_by_id(preset_id)

    if mode == "preset" and tpl:
        resolved = dict(tpl.get("settings") or DEFAULT_SUBTITLE_SETTINGS)
        resolved["enable_subtitles"] = bool(raw_settings.get("enable_subtitles", True))
        resolved["selection_mode"] = "preset"
        resolved["preset_id"] = tpl["id"]
        return resolved

    # Chế độ Custom (hoặc ghi đè chi tiết)
    if tpl and isinstance(tpl.get("settings"), dict):
        base.update(tpl["settings"])
    for k, v in raw_settings.items():
        if k in base and v is not None:
            base[k] = v

    base["enable_subtitles"] = bool(base.get("enable_subtitles", True))
    base["selection_mode"] = "custom" if mode == "custom" else "preset"
    base["font_size"] = max(24, min(84, int(float(base.get("font_size") or 48))))
    base["bold"] = bool(base.get("bold", True))
    base["italic"] = bool(base.get("italic", False))
    base["uppercase"] = bool(base.get("uppercase", True))
    base["outline_width"] = max(0.0, min(10.0, round(float(base.get("outline_width") if base.get("outline_width") is not None else 3.0), 1)))
    base["shadow_depth"] = max(0.0, min(10.0, round(float(base.get("shadow_depth") if base.get("shadow_depth") is not None else 0.0), 1)))
    base["shadow_opacity"] = max(0, min(100, int(float(base.get("shadow_opacity") if base.get("shadow_opacity") is not None else 50))))
    base["border_style"] = 3 if int(base.get("border_style") or 1) == 3 else 1
    base["box_bg_opacity"] = max(10, min(100, int(float(base.get("box_bg_opacity") if base.get("box_bg_opacity") is not None else 72))))
    base["alignment"] = int(base.get("alignment") or 2)
    if base["alignment"] not in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        base["alignment"] = 2
    base["margin_v"] = max(40, min(900, int(float(base.get("margin_v") if base.get("margin_v") is not None else 225))))
    base["margin_h"] = max(10, min(200, int(float(base.get("margin_h") if base.get("margin_h") is not None else 30))))
    base["letter_spacing"] = max(-2.0, min(10.0, round(float(base.get("letter_spacing") or 0.0), 1)))
    base["fade_in_ms"] = max(0, min(800, int(float(base.get("fade_in_ms") if base.get("fade_in_ms") is not None else 150))))
    base["fade_out_ms"] = max(0, min(800, int(float(base.get("fade_out_ms") if base.get("fade_out_ms") is not None else 150))))
    return base


# ═══════════════════════════════════════════════════════════════════════════════
# 4. BỘ CHUYỂN ĐỔI MÀU HEX SANG MÃ MÀU ASS (`&HAABBGGRR`) & TRÌNH SINH FILE `.ASS`
# ═══════════════════════════════════════════════════════════════════════════════

def hex_to_rgb(hex_str: str, default: tuple = (255, 255, 255)) -> tuple:
    s = str(hex_str or "").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) == 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except Exception:
            pass
    return default


def hex_to_ass_color(hex_str: str, opacity_pct: int = 100, with_trailing_amp: bool = False) -> str:
    """
    Chuyển mã màu `#RRGGBB` + độ đậm `opacity_pct` (0..100%) sang chuẩn SubStation Alpha `&HAABBGGRR`
    (Trong ASS: AA=00 là đặc 100%, AA=FF là trong suốt 100%).
    """
    r, g, b = hex_to_rgb(hex_str)
    op = max(0, min(100, int(opacity_pct)))
    alpha = int(round((100 - op) * 255 / 100.0))
    code = f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"
    return (code + "&") if with_trailing_amp else code


def _ts_ass(s: float) -> str:
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"


def _format_phrase_for_animation(
    text_str: str,
    dur: float,
    cfg: dict,
) -> str:
    """
    Sinh chuỗi nội dung Dialogue ASS cho 1 cụm câu dựa theo `animation_style`:
      - `karaoke_word`: `{\fad(in,out)}{\k...}word ` (Mặc định chuẩn hiện tại)
      - `karaoke_smooth`: `{\fad(in,out)}{\kf...}word `
      - `pop_karaoke`: `{\fad(in,out)\fscx114\fscy114\t(0,150,\fscx100\fscy100)}{\k...}word `
      - `keyword_highlight`: Tô màu `secondary_color` cho các từ khóa số/giá/USP + Karaoke
      - `dual_line_split`: Ngắt thành 2 dòng (dòng 1 màu `primary_color`, dòng 2 màu `secondary_color`)
      - `glow_neon`: Thêm `{\blur1.8}` + Karaoke
      - `clean_fade`: Chỉ `{\fad(in,out)}` đơn sắc không nhảy chữ
    """
    s = (text_str or "").strip()
    if not s:
        return ""
    if cfg.get("uppercase", True):
        s = s.upper()

    anim = str(cfg.get("animation_style") or "karaoke_word").strip().lower()
    f_in = int(cfg.get("fade_in_ms") if cfg.get("fade_in_ms") is not None else 150)
    f_out = int(cfg.get("fade_out_ms") if cfg.get("fade_out_ms") is not None else 150)
    fad_tag = f"\\fad({f_in},{f_out})" if (f_in > 0 or f_out > 0) else ""

    toks = s.split()
    if not toks:
        return ""
    kcs = max(1, int(round(dur * 100 / max(1, len(toks)))))

    if anim == "clean_fade":
        return f"{{{fad_tag}}}{s}" if fad_tag else s

    if anim == "dual_line_split":
        c_pri = hex_to_ass_color(cfg.get("primary_color", "#FFFFFF"), 100, with_trailing_amp=True)
        c_sec = hex_to_ass_color(cfg.get("secondary_color", "#FFE066"), 100, with_trailing_amp=True)
        if len(toks) <= 2:
            return f"{{{fad_tag}\\c{c_sec}}}{s}"
        mid = max(1, len(toks) // 2)
        line1 = " ".join(toks[:mid])
        line2 = " ".join(toks[mid:])
        return f"{{{fad_tag}\\c{c_pri}}}{line1}\\N{{\\c{c_sec}}}{line2}"

    if anim == "keyword_highlight":
        c_pri = hex_to_ass_color(cfg.get("primary_color", "#FFFFFF"), 100, with_trailing_amp=True)
        c_sec = hex_to_ass_color(cfg.get("secondary_color", "#FACC15"), 100, with_trailing_amp=True)
        kw_re = re.compile(
            r"(\d+K|\d+%|\d+|GIỎ|HÀNG|XƯỞNG|GỐC|SIÊU|PHẨM|MIỄN|PHÍ|SHIP|NGAY|BỀN|ĐA|NĂNG|RẺ|SỐC)",
            flags=re.I,
        )
        parts = []
        for idx_w, w in enumerate(toks):
            is_kw = bool(kw_re.search(w)) or (idx_w >= len(toks) - 2 and len(toks) >= 4)
            col = c_sec if is_kw else c_pri
            parts.append(f"{{\\c{col}}}{w}")
        pop_tag = "\\fscx112\\fscy112\\t(0,150,\\fscx100\\fscy100)"
        return f"{{{fad_tag}{pop_tag}}}" + " ".join(parts)

    if anim == "karaoke_smooth":
        ktxt = "".join(f"{{\\kf{kcs}}}{w} " for w in toks).rstrip()
        return f"{{{fad_tag}}}{ktxt}" if fad_tag else ktxt

    if anim == "pop_karaoke":
        pop_tag = "\\fscx114\\fscy114\\t(0,155,\\fscx100\\fscy100)"
        ktxt = "".join(f"{{\\k{kcs}}}{w} " for w in toks).rstrip()
        return f"{{{fad_tag}{pop_tag}}}{ktxt}"

    if anim == "glow_neon":
        ktxt = "".join(f"{{\\k{kcs}}}{w} " for w in toks).rstrip()
        return f"{{{fad_tag}\\blur1.6}}{ktxt}"

    # Mặc định chuẩn hiện tại (`karaoke_word`): `{\fad(150,150)}{\k...}`
    ktxt = "".join(f"{{\\k{kcs}}}{w} " for w in toks).rstrip()
    return f"{{{fad_tag}}}{ktxt}" if fad_tag else ktxt


def build_ass_from_subtitle_settings(
    spec: dict,
    ass_path: str,
    scene_durations: list,
    subtitle_settings: dict = None,
) -> str:
    """
    Sinh file phụ đề `.ass` (1080x1920) từ `subtitle_settings` (chọn từ Kho Template hoặc Tự Custom).
    Tuyệt đối KHÔNG sinh thêm lớp chữ giữa ngực trùng lặp, giữ khung hình sạch và chuyên nghiệp 100%!
    """
    cfg = resolve_subtitle_settings(subtitle_settings)
    enable_sub = bool(cfg.get("enable_subtitles", True))

    font_name = str(cfg.get("font_family") or "DejaVu Sans").strip()
    font_size = int(cfg.get("font_size") or 48)
    bold_flag = -1 if cfg.get("bold", True) else 0
    italic_flag = -1 if cfg.get("italic", False) else 0
    spacing = float(cfg.get("letter_spacing") or 0.0)
    border_style = 3 if int(cfg.get("border_style") or 1) == 3 else 1
    outline_w = float(cfg.get("outline_width") if cfg.get("outline_width") is not None else 3.0)
    shadow_d = float(cfg.get("shadow_depth") if cfg.get("shadow_depth") is not None else 0.0)
    align = int(cfg.get("alignment") or 2)
    margin_v = int(cfg.get("margin_v") if cfg.get("margin_v") is not None else 225)
    margin_h = int(cfg.get("margin_h") if cfg.get("margin_h") is not None else 30)

    pri_ass = hex_to_ass_color(cfg.get("primary_color", "#FFFFFF"), 100)
    sec_ass = hex_to_ass_color(cfg.get("secondary_color", "#FFE066"), 100)

    if border_style == 3:
        # Khi dùng Hộp Nền (`BorderStyle = 3`), libass vẽ hộp nền bằng `OutlineColour` + `BackColour`
        box_hex = cfg.get("box_bg_color") or "#000000"
        box_op = int(cfg.get("box_bg_opacity") if cfg.get("box_bg_opacity") is not None else 75)
        out_ass = hex_to_ass_color(box_hex, box_op)
        back_ass = hex_to_ass_color(box_hex, box_op)
        outline_w = max(8.0, outline_w)
        shadow_d = 0.0
    else:
        out_ass = hex_to_ass_color(cfg.get("outline_color", "#000000"), 100)
        sh_op = int(cfg.get("shadow_opacity") if cfg.get("shadow_opacity") is not None else 50)
        back_ass = hex_to_ass_color(cfg.get("shadow_color", "#000000"), sh_op)

    L = [
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\n\n",
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n",
        f"Style: Sub,{font_name},{font_size},{pri_ass},{sec_ass},{out_ass},{back_ass},"
        f"{bold_flag},{italic_flag},0,0,100,100,{spacing:g},0,{border_style},{outline_w:g},{shadow_d:g},"
        f"{align},{margin_h},{margin_h},{margin_v},1\n\n",
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
    ]

    if enable_sub:
        off = 0.0
        for i, sc in enumerate(spec.get("scenes") or []):
            sc_dur = scene_durations[i] if i < len(scene_durations) else 10.0
            phrases = sc.get("phrases") or []
            total = sum(max(1, sw) for _, sw in phrases) or max(1, sc.get("words", 10))
            t = off
            for _, (text, sw) in enumerate(phrases):
                text_str = str(text or "").strip()
                if not text_str:
                    continue
                dur = (max(1, sw) / float(total)) * sc_dur
                formatted_line = _format_phrase_for_animation(text_str, dur, cfg)
                if formatted_line:
                    L.append(
                        f"Dialogue: 0,{_ts_ass(t)},{_ts_ass(t + dur)},Sub,,0,0,0,,{formatted_line}\n"
                    )
                t += dur
            off += sc_dur

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("".join(L))
    return ass_path


# ═══════════════════════════════════════════════════════════════════════════════
# 5. BỘ RENDER 16 ẢNH DEMO SUBTITLE 1080x1920 ĐỂ XEM TRỰC QUAN & FULL LIGHTBOX
# ═══════════════════════════════════════════════════════════════════════════════

def _load_pil_font_for_sub(font_family: str, size: int, bold: bool = True):
    f_low = (font_family or "").lower()
    win_candidates = []
    if "segoe" in f_low:
        win_candidates.append(r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf")
    elif "tahoma" in f_low:
        win_candidates.append(r"C:\Windows\Fonts\tahomabd.ttf" if bold else r"C:\Windows\Fonts\tahoma.ttf")
    elif "impact" in f_low:
        win_candidates.append(r"C:\Windows\Fonts\impact.ttf")
    elif "verdana" in f_low:
        win_candidates.append(r"C:\Windows\Fonts\verdanab.ttf" if bold else r"C:\Windows\Fonts\verdana.ttf")
    elif "trebuchet" in f_low:
        win_candidates.append(r"C:\Windows\Fonts\trebucbd.ttf" if bold else r"C:\Windows\Fonts\trebuc.ttf")
    elif "times" in f_low:
        win_candidates.append(r"C:\Windows\Fonts\timesbd.ttf" if bold else r"C:\Windows\Fonts\times.ttf")
    win_candidates.extend([
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\tahomabd.ttf",
    ])
    for fp in win_candidates:
        if os.path.isfile(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_subtitle_template_demo_image(
    template_obj: dict,
    bg_image_path: str = "",
    out_path: str = "",
) -> str:
    """
    Render ảnh Demo 1080x1920 sắc nét cho 1 Template Subtitle trên nền khung hình Video thật
    (kèm khung ảnh sản phẩm góc trái trên như video xuất thực tế + nhãn thông số ở góc phải trên
    + dòng phụ đề Karaoke hiển thị chính xác ở toạ độ `MarginV`).
    """
    W, H = 1080, 1920
    if not bg_image_path or not os.path.isfile(bg_image_path):
        for cand in (
            os.path.join(WS_DIR, "projects", "1736467481808438427", "v1-refimg.jpg"),
            os.path.join(WS_DIR, "projects", "1736467481808438427", "v3-refimg.jpg"),
            os.path.join(WS_DIR, "Template", "Thumbnail_Templates", "samples", "ai_bases", "ai_base_fashion_sweater_model.jpg"),
        ):
            if os.path.isfile(cand):
                bg_image_path = cand
                break

    if bg_image_path and os.path.isfile(bg_image_path):
        with Image.open(bg_image_path) as raw:
            im = raw.convert("RGB")
            sc = max(W / float(max(1, im.width)), H / float(max(1, im.height)))
            nw, nh = int(round(im.width * sc)), int(round(im.height * sc))
            im = im.resize((nw, nh), Image.Resampling.LANCZOS)
            left, top = (nw - W) // 2, (nh - H) // 2
            canvas = im.crop((left, top, left + W, top + H)).convert("RGBA")
    else:
        canvas = Image.new("RGBA", (W, H), (22, 30, 46, 255))

    # Gắn nhẹ khung ảnh sản phẩm góc trên bên trái (340x340) giống hệt video thực tế
    prod_cand = os.path.join(WS_DIR, "projects", "1736467481808438427", "product_images", "prod_1.jpg")
    if os.path.isfile(prod_cand):
        try:
            with Image.open(prod_cand) as pim:
                p_sq = pim.convert("RGB").resize((330, 330), Image.Resampling.LANCZOS).convert("RGBA")
                canvas.paste(p_sq, (30, 30))
        except Exception:
            pass

    # Thẻ thông tin nhỏ gọn ở góc trên bên phải để người dùng biết đang xem Demo của Template nào
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    cfg = template_obj.get("settings") or DEFAULT_SUBTITLE_SETTINGS

    d.rounded_rectangle([385, 30, 1050, 172], radius=18, fill=(9, 13, 22, 215), outline=(251, 191, 36, 220), width=2)
    f_badge = _load_pil_font_for_sub("Segoe UI", 22, bold=True)
    f_meta = _load_pil_font_for_sub("Segoe UI", 18, bold=False)
    tpl_title = re.sub(r"^[^\w#]+", "", str(template_obj.get("name") or "")).strip()
    if len(tpl_title) > 46:
        tpl_title = tpl_title[:44] + "…"
    d.text((405, 46), f"♦ DEMO SUBTITLE • {template_obj.get('code', 'SUB')}", font=f_badge, fill=(253, 224, 71, 255))
    d.text((405, 82), tpl_title, font=f_badge, fill=(255, 255, 255, 255))
    meta_str = f"Font: {cfg.get('font_family')} {cfg.get('font_size')}pt • Viền: {cfg.get('outline_width')}px • Đáy MarginV: {cfg.get('margin_v')}px"
    d.text((405, 122), meta_str, font=f_meta, fill=(148, 163, 184, 255))

    # Vẽ Phụ Đề Chính Xác Tại Vị Trí `margin_v`
    font_sz = int(cfg.get("font_size") or 48)
    f_sub = _load_pil_font_for_sub(cfg.get("font_family", "Arial"), font_sz, bold=cfg.get("bold", True))
    demo_line = str(template_obj.get("demo_line") or "PHẨM KHĂN LƯỚI KIM LOẠI RỬA")
    if cfg.get("uppercase", True):
        demo_line = demo_line.upper()

    hl_words = {w.upper() for w in (template_obj.get("demo_highlight_words") or ["LOẠI", "RỬA"])}
    pri_rgb = hex_to_rgb(cfg.get("primary_color", "#FFFFFF")) + (255,)
    sec_rgb = hex_to_rgb(cfg.get("secondary_color", "#FFE066")) + (255,)
    out_rgb = hex_to_rgb(cfg.get("outline_color", "#000000")) + (255,)
    sh_rgb = hex_to_rgb(cfg.get("shadow_color", "#000000")) + (int(round(int(cfg.get("shadow_opacity", 50)) * 2.55)),)
    stroke_w = max(1, int(round(float(cfg.get("outline_width") or 3.0))))
    shadow_d = int(round(float(cfg.get("shadow_depth") or 0.0)))
    border_style = int(cfg.get("border_style") or 1)
    margin_v = int(cfg.get("margin_v") or 225)

    lines = demo_line.split("\n")
    line_heights = []
    line_widths = []
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=f_sub, stroke_width=stroke_w)
        line_widths.append(bb[2] - bb[0])
        line_heights.append(max(font_sz + 8, bb[3] - bb[1]))

    total_h = sum(line_heights) + max(0, len(lines) - 1) * 12
    base_y = H - margin_v - total_h

    # Nếu `border_style == 3` (Hộp nền Pill/Box):
    if border_style == 3:
        box_rgb = hex_to_rgb(cfg.get("box_bg_color", "#000000"))
        box_alpha = int(round(int(cfg.get("box_bg_opacity", 78)) * 2.55))
        max_lw = max(line_widths) if line_widths else 600
        pad_x, pad_y = 28, 16
        bx1 = (W - max_lw) // 2 - pad_x
        by1 = base_y - pad_y
        bx2 = (W + max_lw) // 2 + pad_x
        by2 = base_y + total_h + pad_y
        d.rounded_rectangle([bx1, by1, bx2, by2], radius=16, fill=box_rgb + (box_alpha,))

    # Nếu hiệu ứng `glow_neon`, vẽ lớp phát sáng mờ phía dưới chữ
    if cfg.get("animation_style") == "glow_neon":
        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        cur_y = base_y
        for idx_l, ln in enumerate(lines):
            lw = line_widths[idx_l]
            lx = (W - lw) // 2
            gd.text((lx, cur_y), ln, font=f_sub, fill=sec_rgb, stroke_width=stroke_w + 6, stroke_fill=sec_rgb)
            cur_y += line_heights[idx_l] + 12
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(6))
        ov.alpha_composite(glow_layer)
        d = ImageDraw.Draw(ov)

    # Vẽ từng từ để thể hiện đúng 2 tông màu Karaoke (`primary_color` + `secondary_color`)
    cur_y = base_y
    space_bb = d.textbbox((0, 0), " ", font=f_sub)
    space_w = max(12, space_bb[2] - space_bb[0])

    for idx_l, ln in enumerate(lines):
        words = ln.split()
        word_widths = []
        for w in words:
            wb = d.textbbox((0, 0), w, font=f_sub)
            word_widths.append(wb[2] - wb[0])
        full_w = sum(word_widths) + max(0, len(words) - 1) * space_w
        cur_x = (W - full_w) // 2

        for idx_w, w in enumerate(words):
            is_hl = (w.upper().strip(".,!?") in hl_words) or (
                cfg.get("animation_style") == "dual_line_split" and idx_l == 1
            )
            fill_col = sec_rgb if is_hl else pri_rgb
            if shadow_d > 0 and border_style != 3:
                d.text(
                    (cur_x + shadow_d, cur_y + shadow_d),
                    w,
                    font=f_sub,
                    fill=sh_rgb,
                    stroke_width=stroke_w,
                    stroke_fill=sh_rgb,
                )
            d.text(
                (cur_x, cur_y),
                w,
                font=f_sub,
                fill=fill_col,
                stroke_width=(0 if border_style == 3 else stroke_w),
                stroke_fill=out_rgb,
            )
            cur_x += word_widths[idx_w] + space_w
        cur_y += line_heights[idx_l] + 12

    canvas.alpha_composite(ov)
    if not out_path:
        out_path = os.path.join(SUB_SAMPLES_DIR, f"{template_obj['id']}.jpg")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.convert("RGB").save(out_path, "JPEG", quality=93)
    return out_path


def ensure_all_subtitle_demo_images(force: bool = False) -> list:
    """Đảm bảo cả 16 Template Subtitle đều có ảnh Demo 1080x1920 sẵn sàng trên đĩa."""
    out = []
    for tpl in SUBTITLE_TEMPLATES:
        rel_p = f"Template/Subtitle_Templates/samples/{tpl['id']}.jpg"
        abs_p = os.path.join(SUB_SAMPLES_DIR, f"{tpl['id']}.jpg")
        if force or not os.path.isfile(abs_p) or os.path.getsize(abs_p) < 10000:
            try:
                render_subtitle_template_demo_image(tpl, out_path=abs_p)
            except Exception as e:
                print(f"WARN rendering subtitle demo {tpl['id']}:", e)
        tpl["sample_image"] = rel_p
        tpl["sample_image_abs"] = abs_p
        out.append(tpl)

    # Lưu manifest `Template/Subtitle_Templates/subtitle_templates.json`
    try:
        manifest_path = os.path.join(SUB_TEMPLATES_DIR, "subtitle_templates.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "total": len(out),
                    "categories": SUBTITLE_CATEGORIES,
                    "fonts": AVAILABLE_SUBTITLE_FONTS,
                    "animations": SUBTITLE_ANIMATION_STYLES,
                    "default_settings": DEFAULT_SUBTITLE_SETTINGS,
                    "templates": out,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception:
        pass
    return out


if __name__ == "__main__":
    rendered = ensure_all_subtitle_demo_images(force=True)
    print(f"Rendered {len(rendered)} Subtitle Template 1080x1920 demos into {SUB_SAMPLES_DIR}")
