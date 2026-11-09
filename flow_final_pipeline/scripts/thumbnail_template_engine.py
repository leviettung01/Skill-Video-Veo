# -*- coding: utf-8 -*-
"""
🎨 KHO TEMPLATE THUMBNAIL ĐA NGÀNH HÀNG & COMPOSITOR ẢNH SẢN PHẨM THỰC TẾ
Phân tích từ 29 mẫu Thumbnail Affiliate chuyển đổi cao trong thư mục `ảnh mẫu thumbnail/`:
- Gia dụng & Nhà bếp (`gia_dung_3grid_pro`, `gia_dung_infographic_tech`)
- Tiện ích & Phụ kiện nhỏ (`phu_kien_macro_3cards`)
- Giày dép / Clog / Sandal (`giay_dep_kawaii_sticker`, `giay_dep_luxury_zoom`, `giay_dep_flatlay_colors`)
- Quần áo & Thời trang Nữ (`thoi_trang_lookbook_3zoom`, `thoi_trang_pastel_cta`)
- Thời trang Nam/Nữ Unisex & Xả kho (`streetwear_unisex_flashsale`)
- Phong cách GenZ & Cute (`genz_mirror_polaroid`)
- Túi xách & Phụ kiện Hàn Quốc (`tui_xach_korean_scrapbook`)
- Mỹ phẩm & Chăm sóc cá nhân (`my_pham_beauty_glow`)

Đặc điểm cốt lõi:
1. Luôn nhúng 2-3 Ảnh Sản Phẩm Thực Tế (`prod_1.jpg .. prod_6.jpg`) vào các khung Inset chuyên nghiệp
   (3-Card Grid, Vòng Tròn Zoom Viền Vàng, Khung Polaroid Dán Băng Dính, Thẻ Trước/Sau Infographic, Sticker Viền Trắng).
2. Hỗ trợ 3 chế độ chọn Template:
   - `fixed`: Cố định 1 Style cho toàn bộ video
   - `auto_category`: Tự động nhận diện ngành hàng & xoay vòng các style phù hợp cho v1, v2, v3
   - `custom_category`: Người dùng tự gán riêng từng ngành hàng dùng cố định 1 Template yêu thích
"""
import os
import re
import glob
import json
import math
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
WS_DIR = os.path.abspath(os.path.join(PIPELINE_DIR, ".."))
THUMB_TPL_DIR = os.path.join(WS_DIR, "Template", "Thumbnail_Templates")
SAMPLES_DIR = os.path.join(THUMB_TPL_DIR, "samples")
os.makedirs(SAMPLES_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. DANH MỤC 8 NGÀNH HÀNG THUMBNAIL & TỪ KHOÁ NHẬN DIỆN TỰ ĐỘNG
# ═══════════════════════════════════════════════════════════════════════════════

THUMBNAIL_CATEGORIES = [
    {
        "id": "gia_dung",
        "name": "🏠 Gia Dụng, Nhà Bếp & Đời Sống",
        "short_name": "Gia Dụng & Bếp",
        "default_template": "gia_dung_3grid_pro",
        "rotation_templates": ["gia_dung_3grid_pro", "gia_dung_cookware_4set_bar", "gia_dung_multicooker_3tabs", "gia_dung_infographic_tech", "gia_dung_shield_5pills"],
        "keywords": [
            "khăn lưới", "rửa chén", "rửa bát", "xoong", "nồi", "chảo", "bếp", "gia dụng",
            "nhà bếp", "lau bếp", "vệ sinh", "cọ nồi", "dao", "thớt", "kệ", "hộp đựng",
            "bình giữ nhiệt", "máy xay", "nồi chiên", "ấm đun", "chổi", "cây lau", "thùng rác",
            "móc treo", "nhà tắm", "nhà cửa", "cân tiểu ly", "lồng bàn", "đĩa", "bát", "ly", "cốc",
        ],
    },
    {
        "id": "giay_dep",
        "name": "👟 Giày Dép, Clog, Sandal & Cao Gót",
        "short_name": "Giày Dép & Clog",
        "default_template": "giay_dep_kawaii_sticker",
        "rotation_templates": ["giay_dep_kawaii_sticker", "giay_dep_slides_4pills_3scenes", "giay_dep_leya_check_inset", "giay_dep_luxury_zoom", "giay_dep_flatlay_colors"],
        "keywords": [
            "giày", "dép", "sandal", "sục", "clog", "cao gót", "sneaker", "boot", "tất", "vớ",
            "đế êm", "chống trượt", "giày da", "giày lười", "dép lê", "dép quai", "giày thể thao",
        ],
    },
    {
        "id": "quan_ao_nu",
        "name": "👗 Quần Áo & Thời Trang Nữ",
        "short_name": "Thời Trang Nữ",
        "default_template": "thoi_trang_lookbook_3zoom",
        "rotation_templates": ["thoi_trang_lookbook_3zoom", "thoi_trang_model_flatlay_swatch", "thoi_trang_mannequin_cottagecore", "thoi_trang_pastel_cta"],
        "keywords": [
            "váy", "đầm", "chân váy", "áo kiểu", "áo trễ vai", "set bộ nữ", "cardigan",
            "áo sơ mi nữ", "áo khoác nữ", "pijama", "đồ ngủ", "đồ bộ mặc nhà", "áo hai dây",
            "croptop", "babydoll", "thời trang nữ", "áo len", "blazer",
        ],
    },
    {
        "id": "nam_nu_unisex",
        "name": "👔 Thời Trang Nam, Giày Tây & Unisex",
        "short_name": "Nam/Nữ & Đồ Nam VIP",
        "default_template": "giay_tay_nam_classy_gold",
        "rotation_templates": ["giay_tay_nam_classy_gold", "streetwear_unisex_flashsale", "thoi_trang_lookbook_3zoom"],
        "keywords": [
            "quần ống rộng", "baggy", "unisex", "áo thun", "áo phông", "hoodie", "sweater",
            "quần jean", "quần kaki", "quần đùi", "quần short", "áo polo", "sơ mi nam",
            "đồ tập", "jogger", "thể thao", "nam nữ", "streetwear", "áo khoác dù", "thắt lưng nam", "giày tây",
        ],
    },
    {
        "id": "genz_cute",
        "name": "✨ Phong Cách GenZ, Cute & Kawaii",
        "short_name": "GenZ & Cute",
        "default_template": "genz_mirror_polaroid",
        "rotation_templates": ["genz_mirror_polaroid", "genz_influencer_3zoom_vertical", "giay_dep_kawaii_sticker"],
        "keywords": [
            "genz", "cute", "dễ thương", "kawaii", "gấu bông", "kẹp tóc", "băng đô",
            "sticker", "charm", "đáng yêu", "pastel", "hàn quốc", "ulzzang", "nơ",
        ],
    },
    {
        "id": "tui_xach",
        "name": "👜 Túi Xách, Balo & Ví Thời Trang",
        "short_name": "Túi Xách & Ví",
        "default_template": "tui_xach_korean_scrapbook",
        "rotation_templates": ["tui_xach_korean_scrapbook", "tui_xach_mega_8grid_2tier", "giay_dep_luxury_zoom"],
        "keywords": [
            "túi xách", "túi đeo chéo", "túi tote", "balo", "ví da", "bóp", "túi kẹp nách",
            "túi vải", "túi canvas",
        ],
    },
    {
        "id": "my_pham",
        "name": "💄 Mỹ Phẩm, Skincare & Chăm Sóc Cá Nhân",
        "short_name": "Mỹ Phẩm & Làm Đẹp",
        "default_template": "my_pham_beauty_glow",
        "rotation_templates": ["my_pham_beauty_glow", "thoi_trang_pastel_cta", "genz_mirror_polaroid"],
        "keywords": [
            "kem dưỡng", "serum", "sữa rửa mặt", "son", "chống nắng", "dầu gội", "sữa tắm",
            "nước hoa", "dưỡng thể", "lotion", "mặt nạ", "tẩy trang", "skincare", "mỹ phẩm",
            "trắng da", "mụn", "collagen", "xịt thơm",
        ],
    },
    {
        "id": "phu_kien",
        "name": "🔍 Phụ Kiện Nhỏ, Kẹp Tóc POV & Trang Sức",
        "short_name": "Phụ Kiện & POV",
        "default_template": "phu_kien_macro_3cards",
        "rotation_templates": ["phu_kien_macro_3cards", "phu_kien_pov_mui_ten_pastel", "gia_dung_3grid_pro"],
        "keywords": [
            "bông tai", "khuyên tai", "dây chuyền", "vòng tay", "nhẫn", "mắt kính", "đồng hồ",
            "tai nghe", "cáp sạc", "ốp lưng", "phụ kiện", "dụng cụ", "móc khoá", "buộc tóc", "scrunchie",
        ],
    },
    {
        "id": "dien_tu_y_te",
        "name": "🩺 Thiết Bị Y Tế, Điện Tử & Đèn Decor",
        "short_name": "Y Tế, Điện Tử & Decor",
        "default_template": "thiet_bi_y_te_5metrics",
        "rotation_templates": ["thiet_bi_y_te_5metrics", "gia_dung_multicooker_3tabs", "gia_dung_infographic_tech"],
        "keywords": [
            "spo2", "máy đo", "nhiệt kế", "huyết áp", "y tế", "sức khỏe", "điện tử", "cân điện tử",
            "cân tiểu ly", "đèn", "đèn ngủ", "đèn sàn", "decor", "cây thông", "trang trí", "máy massage",
        ],
    },
]

DEFAULT_CATEGORY_THUMBNAIL_MAP = {
    c["id"]: c["default_template"] for c in THUMBNAIL_CATEGORIES
}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. KHO 12 TEMPLATE THUMBNAIL CHUYÊN NGHIỆP (PHÂN TÍCH TỪ 29 ẢNH MẪU)
# ═══════════════════════════════════════════════════════════════════════════════

THUMBNAIL_TEMPLATES = [
    {
        "id": "gia_dung_3grid_pro",
        "aliases": ["tiktok_shop_pro", "tiktok_viral_sale", "gia_dung_3grid_pro"],
        "name": "🏠 Gia Dụng & Bếp: Nhân Vật + 3 Ảnh Chi Tiết SP & Trợ Giá Xưởng",
        "short_name": "Gia Dụng • 3 Ảnh Chi Tiết SP",
        "category": "gia_dung",
        "category_label": "🏠 Gia Dụng & Nhà Bếp",
        "style_badge": "+3 Ảnh SP Thật • Lưới Bo Góc",
        "layout_type": "grid_3_bottom",
        "sample_image": "Template/Thumbnail_Templates/samples/gia_dung_3grid_pro.jpg",
        "recommended_for": "Khăn lưới kim loại rửa chén, Xoong nồi, Dụng cụ bếp, Đồ vệ sinh nhà cửa, Gia dụng tiện ích",
        "description": "Nhân vật cầm sản phẩm ở 2/3 trên kết hợp 3 khung ảnh sản phẩm thực tế (prod_1, prod_2, prod_3) bo góc viền trắng-vàng sắc nét bên dưới kèm nhãn công dụng & thanh 4 cam kết.",
        "palette": {
            "dock_bg_top": (6, 78, 59, 242),
            "dock_bg_bot": (4, 47, 36, 252),
            "accent": (251, 191, 36),
            "accent_rgb": (251, 191, 36),
            "card_border": (255, 255, 255),
            "pill_bg": (16, 185, 129),
            "pill_text": (255, 255, 255),
            "cta_bg": (220, 38, 38),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a high-converting 9:16 vertical TikTok Shop household & kitchenware commercial poster thumbnail (2K 1536x2752), ultra-sharp studio advertisement photography. "
            "Use Reference Image 1 (character holding product) and Reference Image 2-3 (original product closeups) as strict visual anchors: "
            "Position the character ({character_desc}) in the UPPER-MIDDLE zone (top 68% of the frame), smiling warmly and holding the exact product ({product_name}) clearly toward the camera. "
            "Place a bold 3D Vietnamese commercial headline at the very top for \"{hook_text}\" and a vibrant factory-direct price badge ({price}) beside the character. "
            "Preserve 100% authentic product texture, weave, shape, and color. Product USP: {product_info}. "
            "Keep the bottom 30% of the frame clean worktable space for the 3-photo product detail showcase grid."
        ),
    },
    {
        "id": "gia_dung_infographic_tech",
        "aliases": ["factory_qc_trust", "gia_dung_infographic_tech"],
        "name": "⚡ Gia Dụng & Thiết Bị: Infographic Trước/Sau + Cụm Ảnh SP Thực Tế",
        "short_name": "Gia Dụng • Infographic Trước/Sau",
        "category": "gia_dung",
        "category_label": "🏠 Gia Dụng & Thiết Bị",
        "style_badge": "+1 Ảnh Lớn Trước/Sau + 2 Ảnh Phụ",
        "layout_type": "infographic_tech_3cards",
        "sample_image": "Template/Thumbnail_Templates/samples/gia_dung_infographic_tech.jpg",
        "recommended_for": "Khăn lưới cọ xoong nồi, Nồi điện đa năng, Bình đun, Cân điện tử, Dụng cụ cơ khí & Nhà xưởng",
        "description": "Bố cục Infographic chuẩn Mall: Nhân vật kiểm định tại xưởng + 1 khung lớn đối chiếu Trước/Sau hoặc Ứng dụng bên trái + 2 khung ảnh chi tiết sản phẩm bên phải + Thanh thông số.",
        "palette": {
            "dock_bg_top": (15, 23, 42, 245),
            "dock_bg_bot": (9, 14, 28, 254),
            "accent": (245, 158, 11),
            "accent_rgb": (245, 158, 11),
            "card_border": (254, 243, 199),
            "pill_bg": (30, 58, 138),
            "pill_text": (254, 240, 138),
            "cta_bg": (239, 68, 68),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a photorealistic 2K 9:16 vertical factory-direct QC & kitchen appliance infographic thumbnail poster (1536x2752). "
            "Combine Reference Image 1 (character holding product) and Reference Image 2 (original product photo): "
            "Feature the supervisor character ({character_desc}) in the upper 68% of the frame in a bright modern workshop/kitchen ({style}), presenting the exact product ({product_name}) close to the lens. "
            "Include bold 3D commercial Vietnamese title \"{hook_text}\" at the top and a high-contrast price callout ({price}). "
            "Product specifications & USP: {product_info}. Leave the lower 30% clean for the multi-angle product infographic dock."
        ),
    },
    {
        "id": "phu_kien_macro_3cards",
        "aliases": ["phu_kien_macro_3cards"],
        "name": "🔍 Tiện Ích & Phụ Kiện: Cận Cảnh SP + 3 Thẻ Vuông & 5 Huy Hiệu Tròn",
        "short_name": "Tiện Ích • 3 Thẻ + 5 Icon Tròn",
        "category": "phu_kien",
        "category_label": "🔍 Tiện Ích & Phụ Kiện Nhỏ",
        "style_badge": "+3 Thẻ Ảnh Vuông + 5 Icon Đáy",
        "layout_type": "macro_3cards_5icons",
        "sample_image": "Template/Thumbnail_Templates/samples/phu_kien_macro_3cards.jpg",
        "recommended_for": "Khăn lưới đa năng, Đồ gia dụng nhỏ, Trang sức, Bông tai, Phụ kiện điện thoại, Đồ dùng thông minh",
        "description": "Lấy cảm hứng từ mẫu 792917470: Nền kem-xanh sang trọng, 3 khung vuông bo góc trưng bày 3 góc cận cảnh sản phẩm thực tế kèm nhãn xanh + 5 huy hiệu icon tròn cam kết dưới đáy.",
        "palette": {
            "dock_bg_top": (254, 252, 232, 248),
            "dock_bg_bot": (240, 253, 244, 254),
            "accent": (21, 128, 61),
            "accent_rgb": (21, 128, 61),
            "card_border": (22, 101, 52),
            "pill_bg": (21, 128, 61),
            "pill_text": (255, 255, 255),
            "cta_bg": (220, 38, 38),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render an ultra-detailed 2K 9:16 vertical product-focused commercial poster thumbnail (1536x2752). "
            "Using Reference Image 1 (character holding product) and Reference Image 2 (macro product closeup), showcase the presenter ({character_desc}) in the upper 68% holding the exact product ({product_name}) with crisp studio rim lighting. "
            "Highlight Vietnamese hook \"{hook_text}\" and price ({price}) with clean emerald-and-gold typography. "
            "Product highlights: {product_info}."
        ),
    },
    {
        "id": "giay_dep_kawaii_sticker",
        "aliases": ["giay_dep_kawaii_sticker"],
        "name": "👟 Giày Dép & Clog: Kawaii Pastel Sticker Trắng & Chú Thích Điểm Nhấn",
        "short_name": "Giày Dép • Kawaii Pastel Sticker",
        "category": "giay_dep",
        "category_label": "👟 Giày Dép & Clog",
        "style_badge": "+3 Sticker SP Viền Trắng • Pastel",
        "layout_type": "kawaii_sticker_callouts",
        "sample_image": "Template/Thumbnail_Templates/samples/giay_dep_kawaii_sticker.jpg",
        "recommended_for": "Dép sục Clog, Sandal nữ, Dép bánh mì, Giày búp bê, Phụ kiện Cute, Đồ trẻ em",
        "description": "Lấy cảm hứng từ mẫu BloomStep/SoftStep (705693507): Tông hồng-kem Pastel ngọt ngào, 3 ảnh sản phẩm cắt viền Sticker trắng dày nổi khối kèm nhãn ưu điểm dễ thương & thanh 4 icon đế êm.",
        "palette": {
            "dock_bg_top": (253, 242, 248, 246),
            "dock_bg_bot": (252, 231, 243, 254),
            "accent": (219, 39, 119),
            "accent_rgb": (219, 39, 119),
            "card_border": (255, 255, 255),
            "pill_bg": (236, 72, 153),
            "pill_text": (255, 255, 255),
            "cta_bg": (190, 24, 93),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a cute pastel Kawaii 9:16 vertical TikTok Shop commercial thumbnail poster (2K 1536x2752). "
            "Using Reference Image 1 (character with product) and Reference Image 2 (product closeup), feature the presenter ({character_desc}) in the upper 68% cheerfully showcasing the exact product ({product_name}) with soft pastel studio lighting and 3D bubble headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "giay_dep_luxury_zoom",
        "aliases": ["giay_dep_luxury_zoom"],
        "name": "👠 Giày Cao Gót & Giày Da: Chân Dung Sang Trọng + 3 Vòng Tròn Zoom SP",
        "short_name": "Giày Da/Cao Gót • 3 Vòng Zoom Vàng",
        "category": "giay_dep",
        "category_label": "👠 Giày Cao Gót & Giày Da",
        "style_badge": "+3 Vòng Tròn Zoom Viền Vàng Kim",
        "layout_type": "circle_zoom_left",
        "sample_image": "Template/Thumbnail_Templates/samples/giay_dep_luxury_zoom.jpg",
        "recommended_for": "Giày cao gót, Giày tây nam, Giày da công sở, Boot nữ, Túi da cao cấp, Đồng hồ",
        "description": "Lấy cảm hứng từ mẫu 3-Inches High Heels (791143612): Tông Nâu Espresso & Vàng Champagne sang trọng, 3 Vòng Tròn Zoom viền vàng kim phóng to chất liệu/kiểu dáng thực tế của sản phẩm.",
        "palette": {
            "dock_bg_top": (69, 26, 3, 244),
            "dock_bg_bot": (41, 16, 2, 254),
            "accent": (245, 158, 11),
            "accent_rgb": (245, 158, 11),
            "card_border": (253, 230, 138),
            "pill_bg": (146, 64, 14),
            "pill_text": (254, 243, 199),
            "cta_bg": (217, 119, 6),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a luxury champagne-and-espresso 9:16 vertical commercial thumbnail poster (2K 1536x2752). "
            "Using Reference Image 1 (character holding product) and Reference Image 2 (product closeup), feature the elegant presenter ({character_desc}) in the upper 68% showcasing the exact product ({product_name}) under warm golden studio lighting with headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "giay_dep_flatlay_colors",
        "aliases": ["giay_dep_flatlay_colors"],
        "name": "🩴 Dép Lê & Sản Phẩm Nhiều Phân Loại: So Sánh Phối Màu + Tem Giá Đứt Nét",
        "short_name": "Đa Phân Loại • So Sánh + Tem Giá",
        "category": "giay_dep",
        "category_label": "🩴 Dép & SP Nhiều Phân Loại",
        "style_badge": "+2 Khung So Sánh Lớn + 1 Vòng Tròn",
        "layout_type": "split_flash_deal",
        "sample_image": "Template/Thumbnail_Templates/samples/giay_dep_flatlay_colors.jpg",
        "recommended_for": "Dép lê nhiều màu, Combo khăn nhiều cỡ, Tất vớ theo lố, Quần áo nhiều màu, Đồ gia dụng theo bộ",
        "description": "Lấy cảm hứng từ mẫu Rubber Flip Flop (784426838): Trưng bày 2 khung ảnh lớn đối xứng so sánh các phân loại/ứng dụng của sản phẩm + 1 vòng tròn cận cảnh ở giữa + Khung giá giảm nét đứt.",
        "palette": {
            "dock_bg_top": (131, 24, 67, 244),
            "dock_bg_bot": (80, 7, 36, 254),
            "accent": (251, 191, 36),
            "accent_rgb": (251, 191, 36),
            "card_border": (252, 231, 243),
            "pill_bg": (190, 24, 93),
            "pill_text": (255, 255, 255),
            "cta_bg": (245, 158, 11),
            "cta_text": (15, 23, 42),
        },
        "master_prompt": (
            "Render a vibrant multi-variant commercial 9:16 vertical thumbnail poster (2K 1536x2752). "
            "Using Reference Image 1 (character holding product) and Reference Image 2 (product variations), position the presenter ({character_desc}) in the upper 68% presenting the exact product ({product_name}) with bold commercial headline \"{hook_text}\" and dashed discount price tag ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "thoi_trang_lookbook_3zoom",
        "aliases": ["luxury_fashion_lookbook", "fashion_editorial_lookbook", "thoi_trang_lookbook_3zoom"],
        "name": "👗 Thời Trang Nữ Lookbook: 3 Vòng Tròn Zoom Chất Vải + Ảnh Rời SP",
        "short_name": "Thời Trang Nữ • 3 Vòng Zoom Chất Vải",
        "category": "quan_ao_nu",
        "category_label": "👗 Quần Áo & Thời Trang Nữ",
        "style_badge": "+3 Vòng Tròn Zoom Đường May/Chất Vải",
        "layout_type": "circle_zoom_left",
        "sample_image": "Template/Thumbnail_Templates/samples/thoi_trang_lookbook_3zoom.jpg",
        "recommended_for": "Set bộ nữ, Váy đầm thiết kế, Áo kiểu Hàn Quốc, Áo sơ mi, Blazer nữ, Đồ mặc nhà cao cấp",
        "description": "Lấy cảm hứng từ mẫu Ely Aesthetic Co-ord Set (705693510): Tông Kem-Mocha Hàn Quốc, 3 vòng tròn phóng to chất liệu vải/đường kim mũi chỉ lấy trực tiếp từ ảnh sản phẩm thực tế.",
        "palette": {
            "dock_bg_top": (68, 64, 60, 242),
            "dock_bg_bot": (28, 25, 23, 252),
            "accent": (251, 113, 133),
            "accent_rgb": (251, 113, 133),
            "card_border": (245, 245, 244),
            "pill_bg": (120, 53, 15),
            "pill_text": (255, 255, 255),
            "cta_bg": (225, 29, 72),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a Korean lookbook fashion editorial 9:16 vertical commercial thumbnail poster (2K 1536x2752). "
            "Using Reference Image 1 (character with product) and Reference Image 2 (product closeup), feature the model ({character_desc}) in the upper 68% posing gracefully with the exact product ({product_name}) in a bright aesthetic studio ({style}) with headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "genz_mirror_polaroid",
        "aliases": ["genz_mirror_polaroid"],
        "name": "✨ GenZ & Cute: 2 Khung Ảnh Polaroid Dán Băng Dính + Thẻ Note Checklist",
        "short_name": "GenZ & Cute • Polaroid + Checklist",
        "category": "genz_cute",
        "category_label": "✨ Phong Cách GenZ & Cute",
        "style_badge": "+2 Ảnh Polaroid Nghiêng + Bảng Note",
        "layout_type": "polaroid_collage",
        "sample_image": "Template/Thumbnail_Templates/samples/genz_mirror_polaroid.jpg",
        "recommended_for": "Đồ ngủ Pijama, Đồ bộ GenZ, Quần Jogger, Phụ kiện dễ thương, Kẹp tóc, Đồ dùng học tập & Decor",
        "description": "Lấy cảm hứng từ mẫu Sweet Dream (706091452) & Jogger Set (707210154): 2 khung ảnh Polaroid nghiêng dán băng dính trưng bày ảnh thật của sản phẩm kèm tờ giấy Note 3 dấu tích ưu điểm.",
        "palette": {
            "dock_bg_top": (253, 244, 255, 246),
            "dock_bg_bot": (250, 232, 255, 254),
            "accent": (157, 23, 77),
            "accent_rgb": (157, 23, 77),
            "card_border": (255, 255, 255),
            "pill_bg": (219, 39, 119),
            "pill_text": (255, 255, 255),
            "cta_bg": (190, 24, 93),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a trendy Gen-Z aesthetic 9:16 vertical TikTok Shop thumbnail poster (2K 1536x2752). "
            "Using Reference Image 1 (character holding product) and Reference Image 2 (product closeup), feature the young presenter ({character_desc}) in the upper 68% with vibrant natural lighting, playful Gen-Z typography for \"{hook_text}\" and price badge ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "streetwear_unisex_flashsale",
        "aliases": ["streetwear_unisex_flashsale"],
        "name": "🔥 Nam/Nữ Unisex & Xả Kho: 2 Khung Ảnh SP Lớn Đối Xứng + Deal Đỏ Rực",
        "short_name": "Unisex & Xả Kho • 2 Ảnh Lớn Deal Đỏ",
        "category": "nam_nu_unisex",
        "category_label": "👫 Nam/Nữ Unisex & Deal Sốc",
        "style_badge": "+2 Ảnh SP Cực Lớn + Tem Flash Sale",
        "layout_type": "split_flash_deal",
        "sample_image": "Template/Thumbnail_Templates/samples/streetwear_unisex_flashsale.jpg",
        "recommended_for": "Quần ống rộng Nam/Nữ, Áo thun Unisex, Đồ thể thao, Xả kho Gia dụng tận xưởng, Combo Mua 1 Tặng 1",
        "description": "Lấy cảm hứng từ mẫu Buy 1 Get 1 (786069942) & Racing Baggy Pants (784197617): Tương phản Đỏ-Vàng-Đen cực mạnh, ghép 2 khung ảnh sản phẩm lớn đối xứng + Vòng tròn phụ ở giữa + Thanh lượt bán khủng.",
        "palette": {
            "dock_bg_top": (17, 24, 39, 246),
            "dock_bg_bot": (127, 29, 29, 254),
            "accent": (250, 204, 21),
            "accent_rgb": (250, 204, 21),
            "card_border": (255, 255, 255),
            "pill_bg": (220, 38, 38),
            "pill_text": (255, 255, 255),
            "cta_bg": (250, 204, 21),
            "cta_text": (17, 24, 39),
        },
        "master_prompt": (
            "Render a high-impact Flash Sale 9:16 vertical TikTok Shop commercial poster thumbnail (2K 1536x2752). "
            "Using Reference Image 1 (character holding product) and Reference Image 2 (product closeup), feature the energetic presenter ({character_desc}) in the upper 68% holding the exact product ({product_name}), with bold red-and-yellow brush-stroke headline \"{hook_text}\" and explosive factory deal badge ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "thoi_trang_pastel_cta",
        "aliases": ["thoi_trang_pastel_cta"],
        "name": "👚 Thời Trang Dạo Phố: 3 Khung Ảnh SP Bo Tròn + Băng Rôn Giỏ Hàng Hồng",
        "short_name": "Thời Trang • 3 Khung Tròn + CTA Hồng",
        "category": "quan_ao_nu",
        "category_label": "👚 Váy Đầm & Dạo Phố",
        "style_badge": "+3 Ảnh SP Bo Góc + Băng Rôn CTA",
        "layout_type": "grid_3_bottom",
        "sample_image": "Template/Thumbnail_Templates/samples/thoi_trang_pastel_cta.jpg",
        "recommended_for": "Chân váy, Quần suông nữ, Áo kiểu công sở, Đồ dạo phố, Phụ kiện thời trang nữ",
        "description": "Lấy cảm hứng từ mẫu Ang Gandang Palda (790791873) & Must-Have Pants (790826330): Tông Hồng Berry & Trắng sáng, 3 khung ảnh chi tiết sản phẩm kèm dải băng CTA 'THÊM VÀO GIỎ HÀNG NGAY!' nổi bật.",
        "palette": {
            "dock_bg_top": (131, 24, 67, 242),
            "dock_bg_bot": (80, 7, 36, 252),
            "accent": (251, 207, 232),
            "accent_rgb": (251, 207, 232),
            "card_border": (255, 255, 255),
            "pill_bg": (219, 39, 119),
            "pill_text": (255, 255, 255),
            "cta_bg": (244, 63, 94),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a bright feminine street-style 9:16 vertical commercial thumbnail poster (2K 1536x2752). "
            "Using Reference Image 1 (character with product) and Reference Image 2 (product closeup), feature the stylish presenter ({character_desc}) in the upper 68% showcasing the exact product ({product_name}) with vibrant pink-and-white commercial typography \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "tui_xach_korean_scrapbook",
        "aliases": ["tui_xach_korean_scrapbook"],
        "name": "👜 Túi Xách & Phụ Kiện: Scrapbook Giấy Xé Hàn Quốc + Ảnh Polaroid SP",
        "short_name": "Túi Xách • Scrapbook Giấy Xé Hàn Quốc",
        "category": "tui_xach",
        "category_label": "👜 Túi Xách & Phụ Kiện",
        "style_badge": "+Scrapbook Giấy Kraft + Polaroid SP",
        "layout_type": "polaroid_collage",
        "sample_image": "Template/Thumbnail_Templates/samples/tui_xach_korean_scrapbook.jpg",
        "recommended_for": "Túi xách nữ, Túi đeo chéo, Túi Tote vải, Balo đi học, Ví cầm tay, Sandal Hàn Quốc",
        "description": "Lấy cảm hứng từ bộ mẫu Korean Style Bag (772510888, 772604380): Nền giấy Kraft/Kem xé viền nghệ thuật, ghép 2 khung ảnh Polaroid sản phẩm thực tế có dán băng dính + Giấy note kẻ ngang ghi ưu điểm.",
        "palette": {
            "dock_bg_top": (245, 245, 244, 248),
            "dock_bg_bot": (231, 229, 228, 254),
            "accent": (120, 53, 15),
            "accent_rgb": (120, 53, 15),
            "card_border": (255, 255, 255),
            "pill_bg": (146, 64, 14),
            "pill_text": (255, 255, 255),
            "cta_bg": (180, 83, 9),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a warm Korean vintage scrapbook aesthetic 9:16 vertical commercial poster thumbnail (2K 1536x2752). "
            "Using Reference Image 1 (character holding product) and Reference Image 2 (product closeup), feature the presenter ({character_desc}) in the upper 68% in warm cream-and-espresso tones presenting the exact product ({product_name}) with headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "my_pham_beauty_glow",
        "aliases": ["food_asmr_vivid", "foodie_closeup_appetizing", "my_pham_beauty_glow"],
        "name": "💄 Mỹ Phẩm & Chăm Sóc Cá Nhân: Beauty Glow + 3 Vòng Zoom Kết Cấu SP",
        "short_name": "Mỹ Phẩm • Beauty Glow + 3 Vòng Zoom",
        "category": "my_pham",
        "category_label": "💄 Mỹ Phẩm & Làm Đẹp",
        "style_badge": "+3 Vòng Tròn Zoom SP • Rose Gold",
        "layout_type": "circle_zoom_left",
        "sample_image": "Template/Thumbnail_Templates/samples/my_pham_beauty_glow.jpg",
        "recommended_for": "Kem dưỡng thể, Serum, Sữa rửa mặt, Son môi, Nước hoa, Dầu gội, Thực phẩm chức năng & Đồ ăn",
        "description": "Lấy cảm hứng từ mẫu Labn' Care Body Lotion (790540836): Tôn làn da căng bóng của nhân vật cầm sản phẩm + 3 vòng tròn viền Rose Gold phóng to cận cảnh bao bì/kết cấu sản phẩm thực tế + Huy hiệu Chính Hãng.",
        "palette": {
            "dock_bg_top": (136, 19, 55, 242),
            "dock_bg_bot": (76, 5, 25, 252),
            "accent": (253, 164, 175),
            "accent_rgb": (253, 164, 175),
            "card_border": (255, 228, 230),
            "pill_bg": (225, 29, 72),
            "pill_text": (255, 255, 255),
            "cta_bg": (244, 63, 94),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a radiant beauty & skincare commercial 9:16 vertical thumbnail poster (2K 1536x2752). "
            "Using Reference Image 1 (character holding product) and Reference Image 2 (product closeup), feature the glowing presenter ({character_desc}) in the upper 68% holding the exact product ({product_name}) near the camera with luminous beauty lighting, rose-gold headline \"{hook_text}\" and price badge ({price}). "
            "Product highlights: {product_info}."
        ),
    },
    # ═══════════════════════════════════════════════════════════════════════════
    # 12 STYLE MỚI (PHÂN TÍCH TỪ 59 MẪU TRONG 5 BẢNG LƯỚI TIKTOK AFFILIATE)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "gia_dung_cookware_4set_bar",
        "aliases": ["gia_dung_cookware_4set_bar", "cookware_5piece_set"],
        "name": "🍳 Gia Dụng & Bộ Nồi/Bếp: 4 Pill Ưu Điểm Trái + 4 Khung Phân Tích Từng Món Đáy",
        "short_name": "Bộ Gia Dụng • 4 Pill + 4 Ô Từng Món",
        "category": "gia_dung",
        "category_label": "🏠 Gia Dụng & Nhà Bếp",
        "style_badge": "+4 Pill Trái + 4 Ô Chi Tiết Bộ SP",
        "layout_type": "cookware_set_4breakdown",
        "sample_image": "Template/Thumbnail_Templates/samples/gia_dung_cookware_4set_bar.jpg",
        "reference_image": "Template/Thumbnail_Templates/samples/cropped_refs/sheet1_pastel_appliances_r1c2.jpg",
        "recommended_for": "Bộ nồi chảo Inox, Bộ dao thớt nhà bếp, Khay kệ 3 tầng, Nồi hâm thức ăn, Combo khăn lưới đa năng",
        "description": "Phân tích từ mẫu '5-Piece Stainless Steel Cookware Set' (Ảnh 1 H1C2) & '3-Tier Serve In Style' (Ảnh 2 H4C1): Cột 4 Pill ưu điểm bên trái + Thanh 4 ô Oval phân tích từng món/kích cỡ của bộ sản phẩm dưới đáy.",
        "palette": {
            "dock_bg_top": (254, 242, 242, 246),
            "dock_bg_bot": (252, 231, 243, 254),
            "accent": (190, 24, 93),
            "accent_rgb": (190, 24, 93),
            "card_border": (255, 255, 255),
            "pill_bg": (219, 39, 119),
            "pill_text": (255, 255, 255),
            "cta_bg": (157, 23, 77),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a bright pastel kitchenware set commercial 9:16 vertical thumbnail poster (2K 1536x2752). "
            "Showcase the complete cookware/kitchen product set ({product_name}) on a warm wooden/marble kitchen counter in the upper 68% with 3D commercial headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "gia_dung_multicooker_3tabs",
        "aliases": ["gia_dung_multicooker_3tabs", "stackable_multicooker"],
        "name": "🍲 Thiết Bị Bếp Đa Năng: 4 Thông Số Trái + 3 Khung Ảnh Kết Quả Có Tab Màu (Hấp/Nấu/Ủ)",
        "short_name": "Thiết Bị Bếp • 3 Tab Màu Hấp/Nấu/Ủ",
        "category": "gia_dung",
        "category_label": "🏠 Gia Dụng & Thiết Bị",
        "style_badge": "+4 Pill Thông Số + 3 Khung Tab Màu",
        "layout_type": "multicooker_3food_tabs",
        "sample_image": "Template/Thumbnail_Templates/samples/gia_dung_multicooker_3tabs.jpg",
        "reference_image": "Template/Thumbnail_Templates/samples/cropped_refs/sheet1_pastel_appliances_r3c2.jpg",
        "recommended_for": "Nồi điện đa năng, Nồi lẩu hấp 2 tầng, Ấm siêu tốc giữ nhiệt, Nồi chiên không dầu, Máy xay đa năng",
        "description": "Phân tích từ mẫu 'Tough Mama Stackable Multicooker' (Ảnh 1 H3C2): Cột 4 thông số kỹ thuật bên trái + 3 khung ảnh món ăn/ứng dụng thực tế dưới đáy có 3 Tab màu phân biệt 3 công năng (Xanh Blue / Xanh Lá / Tím).",
        "palette": {
            "dock_bg_top": (240, 253, 244, 246),
            "dock_bg_bot": (220, 252, 231, 254),
            "accent": (22, 163, 74),
            "accent_rgb": (22, 163, 74),
            "card_border": (255, 255, 255),
            "pill_bg": (219, 39, 119),
            "pill_text": (255, 255, 255),
            "cta_bg": (21, 128, 61),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a vibrant multi-function kitchen appliance 9:16 vertical commercial thumbnail poster (2K 1536x2752). "
            "Feature the appliance ({product_name}) in the upper 68% with appetizing food results and bold headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "gia_dung_shield_5pills",
        "aliases": ["gia_dung_shield_5pills", "food_cover_multilayer"],
        "name": "🛡️ Gia Dụng Bảo Quản: 5 Pill Tính Năng + Vòng Tròn Thao Tác Tay & 2 Ảnh Chi Tiết",
        "short_name": "Bảo Quản & Lồng Bàn • 5 Pill + Vòng Tròn",
        "category": "gia_dung",
        "category_label": "🏠 Gia Dụng & Nhà Bếp",
        "style_badge": "+5 Pill Trái + 1 Vòng Tròn + 2 Thẻ SP",
        "layout_type": "fresh_shield_5layers",
        "sample_image": "Template/Thumbnail_Templates/samples/gia_dung_shield_5pills.jpg",
        "reference_image": "Template/Thumbnail_Templates/samples/cropped_refs/sheet1_pastel_appliances_r4c2.jpg",
        "recommended_for": "Lồng bàn đậy thức ăn nhiều tầng, Hộp bảo quản thực phẩm, Kệ úp chén chống bụi, Túi hút chân không, Khăn lau bếp",
        "description": "Phân tích từ mẫu 'Keep Food Fresh & Protected Multi-Layer Food Cover' (Ảnh 1 H4C2): 5 Pill tính năng bảo vệ bên trái + 1 Vòng tròn thao tác tay bên dưới + 2 Khung ảnh chi tiết từng tầng.",
        "palette": {
            "dock_bg_top": (255, 241, 242, 246),
            "dock_bg_bot": (254, 226, 226, 254),
            "accent": (225, 29, 72),
            "accent_rgb": (225, 29, 72),
            "card_border": (255, 255, 255),
            "pill_bg": (225, 29, 72),
            "pill_text": (255, 255, 255),
            "cta_bg": (190, 18, 60),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a clean hygienic kitchen storage & protection 9:16 vertical commercial thumbnail poster (2K 1536x2752). "
            "Feature the transparent multi-layer food cover / household organizer ({product_name}) in the upper 68% with headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "giay_dep_slides_4pills_3scenes",
        "aliases": ["giay_dep_slides_4pills_3scenes", "cute_comfy_slides"],
        "name": "🩴 Dép Nữ & Sneaker Êm Chân: 4 Pill Ưu Điểm Trái + Huy Hiệu 100% + 3 Ô Đế/Chất Liệu",
        "short_name": "Dép & Sneaker • 4 Pill + 3 Ô Chất Liệu",
        "category": "giay_dep",
        "category_label": "👟 Giày Dép & Sandal",
        "style_badge": "+4 Pill Trái + Huy Hiệu + 3 Ô Cận Đế",
        "layout_type": "left_pills_3scene_bar",
        "sample_image": "Template/Thumbnail_Templates/samples/giay_dep_slides_4pills_3scenes.jpg",
        "reference_image": "Template/Thumbnail_Templates/samples/cropped_refs/sheet1_pastel_appliances_r1c1.jpg",
        "recommended_for": "Dép quai ngang nữ, Dép bánh mì, Giày chạy bộ nữ hồng, Giày búp bê đế mềm, Dép đi trong nhà",
        "description": "Phân tích từ bộ mẫu 'Cute, Comfy & Stylish Slides' (Ảnh 1 H1C1, H3C1, H3C3): Cột dọc 4 Pill icon hồng/xanh bên trái + Đôi dép đặt trên bục gỗ bên phải + Huy hiệu 100% kèm 3 ô cận cảnh quai/đế chống trượt dưới đáy.",
        "palette": {
            "dock_bg_top": (254, 243, 199, 246),
            "dock_bg_bot": (253, 230, 138, 254),
            "accent": (219, 39, 119),
            "accent_rgb": (219, 39, 119),
            "card_border": (255, 255, 255),
            "pill_bg": (219, 39, 119),
            "pill_text": (255, 255, 255),
            "cta_bg": (180, 83, 9),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a warm pastel footwear commercial 9:16 vertical thumbnail poster (2K 1536x2752). "
            "Showcase the stylish comfortable slides/shoes ({product_name}) on a natural wooden pedestal in the upper-right 68% with 3D headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "giay_dep_leya_check_inset",
        "aliases": ["giay_dep_leya_check_inset", "leya_cute_comfy"],
        "name": "👡 Sandal & Giày Bệt Hàn Quốc: Vòng Tròn Mang Thực Tế Lên Chân + 2 Khung Cận Cảnh",
        "short_name": "Sandal Hàn Quốc • Vòng Tròn Lên Chân",
        "category": "giay_dep",
        "category_label": "👟 Giày Dép & Sandal",
        "style_badge": "+1 Vòng Tròn Lên Chân + 2 Thẻ Cận Cảnh",
        "layout_type": "fresh_shield_5layers",
        "sample_image": "Template/Thumbnail_Templates/samples/giay_dep_leya_check_inset.jpg",
        "reference_image": "Template/Thumbnail_Templates/samples/cropped_refs/sheet1_pastel_appliances_r4c3.jpg",
        "recommended_for": "Sandal quai chéo, Giày búp bê đính nơ, Giày Mary Jane, Dép cói đi biển, Guốc nữ",
        "description": "Phân tích từ mẫu 'Leya Cute & Comfy' (Ảnh 1 H4C3) & 'VDEN Cute Comfy Everyday' (Ảnh 2 H2C3): Kết hợp 5 ưu điểm êm nhẹ bên trái với 1 vòng tròn chụp thực tế khi mang lên chân và 2 khung cận cảnh quai/đế.",
        "palette": {
            "dock_bg_top": (253, 242, 248, 246),
            "dock_bg_bot": (251, 207, 232, 254),
            "accent": (190, 24, 93),
            "accent_rgb": (190, 24, 93),
            "card_border": (255, 255, 255),
            "pill_bg": (236, 72, 153),
            "pill_text": (255, 255, 255),
            "cta_bg": (157, 23, 77),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render an elegant feminine sandal & flat shoe 9:16 vertical commercial thumbnail poster (2K 1536x2752). "
            "Feature the sandals/flats ({product_name}) in warm cream-and-pink studio light in the upper 68% with headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "thoi_trang_model_flatlay_swatch",
        "aliases": ["thoi_trang_model_flatlay_swatch", "vneck_knit_sweater"],
        "name": "🧶 Thời Trang Hàn Quốc: Mẫu Mặc + Ảnh Trải Sàn SP Rời + Vòng Zoom Vải & 5 Chấm Màu",
        "short_name": "Thời Trang • Mẫu Mặc + Trải Sàn + 5 Màu",
        "category": "quan_ao_nu",
        "category_label": "👗 Quần Áo & Thời Trang Nữ",
        "style_badge": "+Ảnh SP Rời + Zoom Sợi Vải + 5 Chấm Màu",
        "layout_type": "model_flatlay_swatch_dots",
        "sample_image": "Template/Thumbnail_Templates/samples/thoi_trang_model_flatlay_swatch.jpg",
        "reference_image": "Template/Thumbnail_Templates/samples/cropped_refs/sheet2_xmas_fashion_home_r2c2.jpg",
        "recommended_for": "Áo len cổ tim, Cardigan Hàn Quốc, Set Blazer nữ, Áo thun nhiều màu, Chân váy xếp ly",
        "description": "Phân tích từ mẫu 'JNN V-Neck Knit Sweater' (Ảnh 2 H2C2): Kết hợp người mẫu mặc thực tế ở trên với 1 khung ảnh sản phẩm trải sàn phẳng phiu, 1 vòng tròn phóng to chất vải len/dệt và 5 chấm tròn bảng màu phân loại.",
        "palette": {
            "dock_bg_top": (254, 249, 239, 246),
            "dock_bg_bot": (245, 235, 224, 254),
            "accent": (153, 27, 27),
            "accent_rgb": (153, 27, 27),
            "card_border": (255, 255, 255),
            "pill_bg": (153, 27, 27),
            "pill_text": (255, 255, 255),
            "cta_bg": (127, 29, 29),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a cozy Korean fashion lookbook 9:16 vertical commercial thumbnail poster (2K 1536x2752). "
            "Feature the female model ({character_desc}) wearing the exact garment ({product_name}) in the upper 68% with warm studio lighting and headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "thoi_trang_mannequin_cottagecore",
        "aliases": ["thoi_trang_mannequin_cottagecore", "petal_dreams_dress"],
        "name": "🎀 Váy Đầm Thiết Kế & Manocanh: 4 Mũi Tên Chỉ Chi Tiết Ren/Nơ + 3 Ảnh Cận Cảnh Vải",
        "short_name": "Váy Thiết Kế • Manocanh + 4 Mũi Tên",
        "category": "quan_ao_nu",
        "category_label": "👗 Váy Đầm & Thiết Kế",
        "style_badge": "+4 Mũi Tên Chỉ Nơ/Ren + 3 Ảnh Cận Vải",
        "layout_type": "pov_hands_pointer_arrows",
        "sample_image": "Template/Thumbnail_Templates/samples/thoi_trang_mannequin_cottagecore.jpg",
        "reference_image": "Template/Thumbnail_Templates/samples/cropped_refs/sheet3_pov_coquette_hands_r4c1.jpg",
        "recommended_for": "Váy công chúa, Đầm dự tiệc, Áo hai dây Gingham, Đồng phục học sinh, Váy bầu thiết kế, Đồ trẻ em",
        "description": "Phân tích từ bộ mẫu 'Petal Dreams Dress / Blossom Boutique / Gingham Joy Cami' (Ảnh 3 H4C1..C3): Trưng bày váy đầm trên Manocanh cổ điển kèm 4 mũi tên nét đứt chỉ thẳng vào cổ áo, nơ ngực, chất ren và đường may.",
        "palette": {
            "dock_bg_top": (253, 248, 245, 246),
            "dock_bg_bot": (245, 232, 227, 254),
            "accent": (180, 83, 9),
            "accent_rgb": (180, 83, 9),
            "card_border": (255, 255, 255),
            "pill_bg": (190, 24, 93),
            "pill_text": (255, 255, 255),
            "cta_bg": (157, 23, 77),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a dreamy Cottagecore & Coquette boutique dress 9:16 vertical commercial thumbnail poster (2K 1536x2752). "
            "Showcase the dress/garment ({product_name}) on a vintage cream mannequin bust in warm sunlight in the upper 68% with headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "giay_tay_nam_classy_gold",
        "aliases": ["giay_tay_nam_classy_gold", "mens_dress_shoes_gold"],
        "name": "👞 Đồ Nam Lịch Lãm (Giày Tây / Thắt Lưng / Boot): Đen-Vàng Kim + 2 Khung Lớn Fullbox",
        "short_name": "Đồ Nam VIP • Đen Vàng Kim + Fullbox",
        "category": "nam_nu_unisex",
        "category_label": "👔 Thời Trang & Phụ Kiện Nam",
        "style_badge": "+4 Pill Đen Vàng + 2 Khung VIP Fullbox",
        "layout_type": "mens_luxury_dark_gold",
        "sample_image": "Template/Thumbnail_Templates/samples/giay_tay_nam_classy_gold.jpg",
        "reference_image": "Template/Thumbnail_Templates/samples/cropped_refs/sheet1_pastel_appliances_r4c1.jpg",
        "recommended_for": "Giày tây nam, Giày da Oxford, Boot da Combat, Thắt lưng nam khóa tự động, Ví da nam, Đồng hồ nam",
        "description": "Phân tích từ mẫu 'Classy Every Step Men's Dress Shoes' (Ảnh 1 H4C1) & 'Classic Combat Boots' (Ảnh 2 H3C2): Tông Đen-Vàng Kim nam tính quyền lực, cột 4 Pill thông số da thật bên trái + 2 khung lớn Fullbox & Cận cảnh đế dưới đáy.",
        "palette": {
            "dock_bg_top": (17, 24, 39, 248),
            "dock_bg_bot": (9, 13, 22, 254),
            "accent": (250, 204, 21),
            "accent_rgb": (250, 204, 21),
            "card_border": (253, 224, 71),
            "pill_bg": (161, 98, 7),
            "pill_text": (255, 255, 255),
            "cta_bg": (202, 138, 4),
            "cta_text": (15, 23, 42),
        },
        "master_prompt": (
            "Render a classy masculine luxury black-and-gold 9:16 vertical commercial thumbnail poster (2K 1536x2752). "
            "Showcase the men's leather shoes/belt/accessory ({product_name}) with its premium box on a dark walnut pedestal in the upper 68% with bold gold headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "genz_influencer_3zoom_vertical",
        "aliases": ["genz_influencer_3zoom_vertical", "kids_jogger_3zoom"],
        "name": "🎵 GenZ Creator Mặc Thử: Cột Dọc 3 Vòng Tròn Zoom Bên Trái + 2 Ảnh Đáy & Giỏ Hàng Vàng",
        "short_name": "GenZ OOTD • 3 Vòng Zoom Dọc Trái",
        "category": "genz_cute",
        "category_label": "✨ Phong Cách GenZ & Creator",
        "style_badge": "+3 Vòng Zoom Dọc Trái + 2 Khung Đáy",
        "layout_type": "influencer_3circle_left_music",
        "sample_image": "Template/Thumbnail_Templates/samples/genz_influencer_3zoom_vertical.jpg",
        "reference_image": "Template/Thumbnail_Templates/samples/cropped_refs/sheet4_creator_ootd_zoom_r2c1.jpg",
        "recommended_for": "Quần Jogger ống rộng, Đồ bộ mặc nhà Pijama, Set đồ đi chơi GenZ, Bình giữ nhiệt Cute, Túi Tote bông",
        "description": "Phân tích từ bộ mẫu 'Kids Jogger Pants / Pajama Set / Trendy Co-ord Set' (Ảnh 4 H2C1, H2C2, H3C1): Creator mặc thử toàn thân bên phải + Cột dọc 3 vòng tròn phóng to dây rút/nơ/gấu quần bên trái + 2 khung ảnh đáy.",
        "palette": {
            "dock_bg_top": (30, 27, 75, 244),
            "dock_bg_bot": (15, 23, 42, 254),
            "accent": (244, 114, 182),
            "accent_rgb": (244, 114, 182),
            "card_border": (255, 255, 255),
            "pill_bg": (219, 39, 119),
            "pill_text": (255, 255, 255),
            "cta_bg": (250, 204, 21),
            "cta_text": (15, 23, 42),
        },
        "master_prompt": (
            "Render a viral TikTok Gen-Z creator OOTD 9:16 vertical commercial thumbnail poster (2K 1536x2752). "
            "Position the cheerful young creator ({character_desc}) on the right side of the frame showcasing the exact product ({product_name}) in a bright aesthetic room with headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "tui_xach_mega_8grid_2tier",
        "aliases": ["tui_xach_mega_8grid_2tier", "everyday_essential_bag_grid"],
        "name": "👜 Túi Xách & Balo Đa Ngăn: Lưới 6 Ô Chi Tiết Mọi Ngăn Khóa Xếp 2 Tầng Dưới Đáy",
        "short_name": "Túi Xách • Lưới 6 Ô Chi Tiết 2 Tầng",
        "category": "tui_xach",
        "category_label": "👜 Túi Xách & Balo",
        "style_badge": "+4 Pill Trái + Lưới 6 Ô Chi Tiết 2 Tầng",
        "layout_type": "mega_6grid_bag_showcase",
        "sample_image": "Template/Thumbnail_Templates/samples/tui_xach_mega_8grid_2tier.jpg",
        "reference_image": "Template/Thumbnail_Templates/samples/cropped_refs/sheet5_itsjessa_bags_shoes_r3c2.jpg",
        "recommended_for": "Túi đeo chéo phao, Túi Tote da công sở, Balo đi học nhiều ngăn, Túi kẹp nách, Bộ dụng cụ nhiều chi tiết",
        "description": "Phân tích từ mẫu 'The Everyday Essential Bag' (Ảnh 5 H3C2) & 'The Cutest Mini Bag' (Ảnh 5 H2C3): Túi xách lớn ở trên kèm cột 4 Pill ưu điểm + Lưới 6 ô ảnh chi tiết xếp 2 tầng soi rõ từng ngăn khóa, lòng túi, dây đeo.",
        "palette": {
            "dock_bg_top": (63, 98, 18, 246),
            "dock_bg_bot": (26, 46, 5, 254),
            "accent": (254, 240, 138),
            "accent_rgb": (254, 240, 138),
            "card_border": (255, 255, 255),
            "pill_bg": (77, 124, 15),
            "pill_text": (255, 255, 255),
            "cta_bg": (202, 138, 4),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a trendy fashion bag & backpack showcase 9:16 vertical commercial thumbnail poster (2K 1536x2752). "
            "Feature the hero bag/product ({product_name}) on a warm wooden studio table in the upper 65% with bold headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "phu_kien_pov_mui_ten_pastel",
        "aliases": ["phu_kien_pov_mui_ten_pastel", "smile_cherry_pouch_pov"],
        "name": "🤲 Phụ Kiện Cầm Tay POV: Đôi Tay Cầm SP Giữa Khung + 4 Mũi Tên Chỉ Điểm Nhấn Đắt Giá",
        "short_name": "Phụ Kiện POV • Đôi Tay + 4 Mũi Tên",
        "category": "phu_kien",
        "category_label": "🔍 Phụ Kiện & Đồ Cute POV",
        "style_badge": "+4 Mũi Tên Chỉ Điểm Nhấn + 3 Ảnh Đáy",
        "layout_type": "pov_hands_pointer_arrows",
        "sample_image": "Template/Thumbnail_Templates/samples/phu_kien_pov_mui_ten_pastel.jpg",
        "reference_image": "Template/Thumbnail_Templates/samples/cropped_refs/sheet3_pov_coquette_hands_r3c2.jpg",
        "recommended_for": "Túi đựng mỹ phẩm, Dây buộc tóc Scrunchie, Kẹp tóc hoa, Ví mini, Hộp bút học tập, Nước hoa mini",
        "description": "Phân tích từ bộ mẫu 'Smile Cherry Makeup Pouch / Pastel Paradise / Sugar & Bow Co.' (Ảnh 3 H1..H3): Góc chụp POV đôi tay nâng niu sản phẩm trên nền lụa kem kèm 4 mũi tên nét đứt chỉ vào khóa kéo, chất liệu, nơ đính.",
        "palette": {
            "dock_bg_top": (255, 245, 245, 246),
            "dock_bg_bot": (254, 226, 226, 254),
            "accent": (185, 28, 28),
            "accent_rgb": (185, 28, 28),
            "card_border": (255, 255, 255),
            "pill_bg": (220, 38, 38),
            "pill_text": (255, 255, 255),
            "cta_bg": (153, 27, 27),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a Coquette Pastel POV hands-holding product 9:16 vertical commercial thumbnail poster (2K 1536x2752). "
            "Show graceful female hands holding the exact product ({product_name}) in the center-upper frame over soft cream satin fabric with headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
    {
        "id": "thiet_bi_y_te_5metrics",
        "aliases": ["thiet_bi_y_te_5metrics", "decor_size_lineup_comparison", "medical_spo2_5metrics"],
        "name": "🩺 Thiết Bị Y Tế, Cân Điện Tử & Đèn Decor: 5 Huy Hiệu Thông Số Kỹ Thuật + 3 Khung Đo Thực Tế",
        "short_name": "Y Tế & Điện Tử • 5 Chỉ Số + 3 Ảnh Đo",
        "category": "dien_tu_y_te",
        "category_label": "🩺 Thiết Bị Y Tế, Điện Tử & Decor",
        "style_badge": "+5 Huy Hiệu Chỉ Số Kỹ Thuật + 3 Khung SP",
        "layout_type": "medical_tech_5metrics",
        "sample_image": "Template/Thumbnail_Templates/samples/thiet_bi_y_te_5metrics.jpg",
        "reference_image": "Template/Thumbnail_Templates/samples/cropped_refs/sheet1_pastel_appliances_r2c1.jpg",
        "recommended_for": "Máy đo SpO2, Máy đo huyết áp, Cân tiểu ly điện tử Inox, Ấm đun hiển thị nhiệt độ, Đèn sàn Wave Lamp",
        "description": "Phân tích từ mẫu 'Check Your Health In Seconds SPO2 Medical' (Ảnh 1 H2C1) & 'Dreepor Digital Kettle 98°C' (Ảnh 1 H2C2): Cột dọc 5 huy hiệu tròn mã hóa thông số kỹ thuật bên trái + Màn hình LED/OLED sắc nét + 3 khung chi tiết.",
        "palette": {
            "dock_bg_top": (239, 246, 255, 246),
            "dock_bg_bot": (219, 234, 254, 254),
            "accent": (29, 78, 216),
            "accent_rgb": (29, 78, 216),
            "card_border": (255, 255, 255),
            "pill_bg": (190, 24, 93),
            "pill_text": (255, 255, 255),
            "cta_bg": (30, 64, 175),
            "cta_text": (255, 255, 255),
        },
        "master_prompt": (
            "Render a clinical & smart-tech infographic 9:16 vertical commercial thumbnail poster (2K 1536x2752). "
            "Showcase the digital device/scale/lamp ({product_name}) with a crisp glowing screen in the upper-right 68% and bold headline \"{hook_text}\" ({price}). "
            "Product details: {product_info}."
        ),
    },
]

# Bổ sung đường dẫn tuyệt đối (`sample_image_abs`, `reference_image_abs`) và mảng `recommended_products` cho cả 24 Templates
_DEFAULT_REF_MAP = {
    "gia_dung_3grid_pro": "Template/Thumbnail_Templates/samples/cropped_refs/sheet2_xmas_fashion_home_r1c3.jpg",
    "gia_dung_infographic_tech": "Template/Thumbnail_Templates/samples/cropped_refs/sheet1_pastel_appliances_r2c2.jpg",
    "phu_kien_macro_3cards": "ảnh mẫu thumbnail/792917470_1091161583776436_3796032225107330466_n.jpg",
    "giay_dep_kawaii_sticker": "ảnh mẫu thumbnail/705693507_2437213620075949_7774279751475897985_n.jpg",
    "giay_dep_luxury_zoom": "ảnh mẫu thumbnail/791143612_122195457512856813_2866929608561976047_n.jpg",
    "giay_dep_flatlay_colors": "ảnh mẫu thumbnail/784426838_1851177525913688_5829303496852567401_n.jpg",
    "thoi_trang_lookbook_3zoom": "ảnh mẫu thumbnail/705693510_2437213950075916_2420653896667694433_n.jpg",
    "genz_mirror_polaroid": "ảnh mẫu thumbnail/706091452_2437213876742590_8675074229038497605_n.jpg",
    "streetwear_unisex_flashsale": "ảnh mẫu thumbnail/786069942_1851177709247003_2167877908667997277_n.jpg",
    "thoi_trang_pastel_cta": "ảnh mẫu thumbnail/790791873_122195457446856813_3303216790783442356_n.jpg",
    "tui_xach_korean_scrapbook": "ảnh mẫu thumbnail/772510888_122250363626100760_3887054691644325587_n.jpg",
    "my_pham_beauty_glow": "ảnh mẫu thumbnail/790540836_122195457434856813_3166816566274811932_n.jpg",
}

for _tpl in THUMBNAIL_TEMPLATES:
    _rel_s = _tpl.get("sample_image") or f"Template/Thumbnail_Templates/samples/{_tpl['id']}.jpg"
    _tpl["sample_image"] = _rel_s
    _tpl["sample_image_abs"] = os.path.normpath(os.path.join(WS_DIR, _rel_s))
    _rel_r = _tpl.get("reference_image") or _DEFAULT_REF_MAP.get(_tpl["id"], _rel_s)
    _tpl["reference_image"] = _rel_r
    _tpl["reference_image_abs"] = os.path.normpath(os.path.join(WS_DIR, _rel_r))
    if not _tpl.get("recommended_products"):
        _rec_str = str(_tpl.get("recommended_for") or "")
        _tpl["recommended_products"] = [x.strip() for x in _rec_str.split(",") if x.strip()]



def export_templates_catalog_json():
    """Lưu danh mục 12 Template Thumbnail & 8 Ngành hàng ra `Template/Thumbnail_Templates/templates.json`."""
    try:
        os.makedirs(THUMB_TPL_DIR, exist_ok=True)
        out_path = os.path.join(THUMB_TPL_DIR, "templates.json")
        payload = {
            "version": "2.0",
            "categories": THUMBNAIL_CATEGORIES,
            "default_category_map": DEFAULT_CATEGORY_THUMBNAIL_MAP,
            "templates": [
                {k: v for k, v in tpl.items() if k != "palette"}
                for tpl in THUMBNAIL_TEMPLATES
            ],
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


export_templates_catalog_json()


def get_template_by_id(template_id: str) -> dict:
    tid = (template_id or "").strip().lower()
    if tid:
        for tpl in THUMBNAIL_TEMPLATES:
            if tpl["id"].lower() == tid or tid in [a.lower() for a in (tpl.get("aliases") or [])]:
                return tpl
    return THUMBNAIL_TEMPLATES[0]


def detect_product_thumbnail_category(product_name: str, product_info: str = "", category_hint: str = "") -> str:
    """Tự động phân tích Tên sản phẩm + Mô tả + Ngành hàng để nhận diện chính xác mã ngành hàng Thumbnail."""
    combined = f"{category_hint or ''} {product_name or ''} {product_info or ''}".lower()
    best_cat = "gia_dung"
    best_score = 0
    for cat in THUMBNAIL_CATEGORIES:
        score = 0
        for kw in cat.get("keywords", []):
            if kw in combined:
                # Ưu tiên từ khoá nằm ngay trong tên sản phẩm
                if kw in (product_name or "").lower():
                    score += 4
                else:
                    score += 1
        if score > best_score:
            best_score = score
            best_cat = cat["id"]
    return best_cat


def _variant_rotation_index(vkey: str) -> int:
    vk = (vkey or "v1").strip().lower()
    if vk in ("v1", "v2", "nv1_v1", "nv2_v1", "nv3_v1"):
        return 0
    if vk in ("v3", "v4", "nv1_v2", "nv2_v2", "nv3_v2"):
        return 1
    if vk in ("v5", "v6", "nv1_v3", "nv2_v3", "nv3_v3"):
        return 2
    m = re.search(r"(\d+)$", vk)
    if m:
        return (int(m.group(1)) - 1) % 3
    return 0


def resolve_thumbnail_template(
    vkey: str = "v1",
    preset_id: str = "",
    settings: dict = None,
    product_name: str = "",
    product_info: str = "",
    category_hint: str = "",
) -> dict:
    """
    Xác định chính xác Template Thumbnail sẽ áp dụng cho biến thể `vkey`:
      1. Nếu truyền trực tiếp `preset_id` cụ thể (khác 'auto' / 'auto_category') -> dùng ngay `preset_id`.
      2. Nếu `thumbnail_selection_mode == 'fixed'` -> dùng cố định `settings['thumbnail_preset_id']` cho mọi video.
      3. Nếu `thumbnail_selection_mode == 'custom_category'` -> tra bảng `category_thumbnail_map[detected_cat]`.
      4. Nếu `thumbnail_selection_mode == 'auto_category'` (Mặc định thông minh):
         - Tự động nhận diện ngành hàng của sản phẩm (`detected_cat`).
         - Nếu bật `rotate_templates_per_variant`: tự động xoay vòng 3 Template cùng ngành hàng cho v1, v2, v3
           (tất cả đều có khung ghép Ảnh Sản Phẩm Thực Tế!).
    """
    cfg = settings or {}
    req_id = (preset_id or "").strip()
    if req_id and req_id.lower() not in ("auto", "auto_category", "category"):
        return get_template_by_id(req_id)

    mode = str(cfg.get("thumbnail_selection_mode") or "auto_category").strip().lower()
    detected_cat = detect_product_thumbnail_category(product_name, product_info, category_hint)
    cat_map = dict(DEFAULT_CATEGORY_THUMBNAIL_MAP)
    if isinstance(cfg.get("category_thumbnail_map"), dict):
        cat_map.update(cfg["category_thumbnail_map"])

    if mode == "fixed":
        fixed_id = str(cfg.get("thumbnail_preset_id") or "gia_dung_3grid_pro").strip()
        return get_template_by_id(fixed_id)

    if mode == "custom_category":
        mapped_id = cat_map.get(detected_cat) or DEFAULT_CATEGORY_THUMBNAIL_MAP.get(detected_cat, "gia_dung_3grid_pro")
        return get_template_by_id(mapped_id)

    # Mode 'auto_category': kết hợp bảng map ngành hàng + xoay vòng đa dạng giữa các biến thể v1, v2, v3
    cat_obj = next((c for c in THUMBNAIL_CATEGORIES if c["id"] == detected_cat), THUMBNAIL_CATEGORIES[0])
    primary_tpl_id = cat_map.get(detected_cat) or cat_obj["default_template"]
    rot_list = [primary_tpl_id] + [t for t in cat_obj.get("rotation_templates", []) if t != primary_tpl_id]
    if bool(cfg.get("rotate_templates_per_variant", True)) and len(rot_list) > 1:
        r_idx = _variant_rotation_index(vkey) % len(rot_list)
        return get_template_by_id(rot_list[r_idx])
    return get_template_by_id(primary_tpl_id)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. BỘ XỬ LÝ ẢNH SẢN PHẨM THỰC TẾ & COMPOSITOR ĐA BỐ CỤC (PIL)
# ═══════════════════════════════════════════════════════════════════════════════

def _load_vn_font(size: int, bold: bool = True):
    candidates = (
        [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\tahomabd.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
        ]
        if bold
        else [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\tahoma.ttf",
        ]
    )
    for fp in candidates:
        if os.path.isfile(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip())
    if not s:
        return ""
    bbox = draw.textbbox((0, 0), s, font=font)
    if (bbox[2] - bbox[0]) <= max_w:
        return s
    while len(s) > 4:
        s = s[:-1].rstrip()
        cand = s + "…"
        b = draw.textbbox((0, 0), cand, font=font)
        if (b[2] - b[0]) <= max_w:
            return cand
    return s


def _extract_prod_num(bname: str) -> int:
    m = re.search(r"prod_(\d+)\.", (bname or "").lower())
    if not m:
        return 0
    val = int(m.group(1))
    # prod_7..12 là bản lặp của prod_1..6
    return ((val - 1) % 6) + 1 if val >= 1 else 0


def _smart_crop_product_photo(img_path: str, target_w: int, target_h: int) -> Image.Image:
    """
    Đọc ảnh sản phẩm thực tế (`prod_1.jpg..prod_6.jpg`) và crop thông minh vào đúng vùng vật thể sản phẩm:
    - Loại bỏ vùng tiêu đề chữ thừa ở mép trên ảnh gốc của sàn TMĐT để vật thể sản phẩm
      bên trong khung Inset hiển thị TO, RÕ NÉT, TRỰC QUAN nhất!
    """
    bname = os.path.basename(img_path).lower()
    pnum = _extract_prod_num(bname)
    with Image.open(img_path) as raw_im:
        im = raw_im.convert("RGB")
        sw, sh = im.size
        if abs(sw - sh) <= int(max(sw, sh) * 0.15) and sh >= 500:
            # Tinh chỉnh vùng crop tối ưu theo bố cục ảnh sản phẩm TMĐT
            if pnum == 1:
                # Lấy trọn bàn tay uốn khăn lưới quanh bát sứ và chồng khăn
                crop_box = (int(sw * 0.16), int(sh * 0.18), int(sw * 0.98), int(sh * 0.98))
            elif pnum == 2:
                # Lấy trọn 4 ô ứng dụng (Lau nồi, Lau bếp, Lau bồn rửa, Rửa bát đĩa)
                crop_box = (int(sw * 0.03), int(sh * 0.15), int(sw * 0.97), int(sh * 0.86))
            elif pnum == 3:
                # Lấy trọn 2 chồng khăn 10 chiếc / 50 chiếc và khăn lưới trải phía trước
                crop_box = (int(sw * 0.03), int(sh * 0.22), int(sw * 0.97), int(sh * 0.90))
            elif pnum == 4:
                # Lấy trọn khung đối chiếu TRƯỚC / SAU chảo inox sạch bóng
                crop_box = (int(sw * 0.02), int(sh * 0.20), int(sw * 0.98), int(sh * 0.90))
            elif pnum == 5:
                # Lấy trọn cảnh cọ chảo chống dính & đĩa sứ
                crop_box = (int(sw * 0.32), int(sh * 0.16), int(sw * 0.98), int(sh * 0.87))
            elif pnum == 6:
                # Lấy trọn cảnh giũ sạch khăn lưới dưới vòi nước chảy
                crop_box = (int(sw * 0.04), int(sh * 0.22), int(sw * 0.98), int(sh * 0.98))
            else:
                crop_box = (int(sw * 0.04), int(sh * 0.16), int(sw * 0.96), int(sh * 0.95))
            im = im.crop(crop_box)
            sw, sh = im.size

        scale = max(target_w / float(max(1, sw)), target_h / float(max(1, sh)))
        nw, nh = max(target_w, int(round(sw * scale))), max(target_h, int(round(sh * scale)))
        im_resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - target_w) // 2
        top = (nh - target_h) // 2
        cropped = im_resized.crop((left, top, left + target_w, top + target_h))
        cropped = ImageEnhance.Sharpness(cropped).enhance(1.18)
        cropped = ImageEnhance.Contrast(cropped).enhance(1.06)
        cropped = ImageEnhance.Color(cropped).enhance(1.06)
        return cropped


def _get_photo_specific_badge_and_label(img_path: str, idx: int, default_badges: list, default_labels: list, is_mesh_cloth: bool) -> tuple:
    bname = os.path.basename(img_path or "").lower()
    pnum = _extract_prod_num(bname)
    if is_mesh_cloth:
        if pnum == 1:
            return ("♦ CẬN CẢNH SỢI LƯỚI", "Mềm dẻo luồn mọi góc kẹt")
        if pnum == 2:
            return ("♦ ĐA NĂNG 4 TRONG 1", "Lau nồi, bếp, bồn rửa, bát")
        if pnum == 3:
            return ("♦ COMBO SỈ TẬN XƯỞNG", "Đủ gói 10 khăn & 50 khăn")
        if pnum == 4:
            return ("♦ TRƯỚC & SAU KHI CỌ", "Đánh bay vết cháy cứng đầu")
        if pnum == 5:
            return ("♦ AN TOÀN CHỐNG DÍNH", "Cọ sạch không làm trầy nồi")
        if pnum == 6:
            return ("♦ DỄ DÀNG GIŨ SẠCH", "Rửa trôi dầu mỡ dưới vòi nước")
    b_txt = default_badges[idx % len(default_badges)] if default_badges else f"♦ CHI TIẾT 0{idx + 1}"
    l_txt = default_labels[idx % len(default_labels)] if default_labels else "Ảnh thật sản phẩm 100%"
    return (b_txt, l_txt)


def _select_3_product_photos_for_variant(pdir: str, prod_img_paths: list, vkey: str) -> list:
    """
    Chọn ra 3 ảnh sản phẩm thực tế đa dạng nhất trong `projects/<pid>/product_images/prod_1.jpg..prod_6.jpg`
    cho từng biến thể (`v1`, `v2`, `v3`) để mỗi video có góc chụp cận cảnh sản phẩm phong phú.
    """
    all_prods = []
    if pdir and os.path.isdir(os.path.join(pdir, "product_images")):
        raw_files = glob.glob(os.path.join(pdir, "product_images", "prod_*.jpg"))
        # Sắp xếp theo số thứ tự prod_1 .. prod_6 và loại trùng
        numbered = []
        for fp in raw_files:
            if os.path.isfile(fp) and os.path.getsize(fp) > 3000:
                m = re.search(r"prod_(\d+)\.jpg$", os.path.basename(fp).lower())
                num_k = int(m.group(1)) if m else 999
                numbered.append((num_k, fp))
        numbered.sort(key=lambda x: x[0])
        seen_mod = set()
        for num_k, fp in numbered:
            mod_k = ((num_k - 1) % 6) + 1 if num_k < 900 else num_k
            if mod_k not in seen_mod:
                seen_mod.add(mod_k)
                all_prods.append(fp)

    for p in (prod_img_paths or []):
        if p and os.path.isfile(p) and p not in all_prods:
            all_prods.append(p)

    if not all_prods:
        return []
    if len(all_prods) == 1:
        return [all_prods[0], all_prods[0], all_prods[0]]
    if len(all_prods) == 2:
        return [all_prods[0], all_prods[1], all_prods[0]]

    r_idx = _variant_rotation_index(vkey)
    n = len(all_prods)
    if n >= 6:
        orders = [
            [0, 3, 5],  # prod_1 (uốn bát sứ), prod_4 (trước/sau chảo inox), prod_6 (giũ sạch dưới vòi nước)
            [3, 1, 4],  # prod_4 (trước/sau chảo inox lớn bên trái), prod_2 (4 ứng dụng), prod_5 (chảo chống dính)
            [5, 2, 4],  # prod_6 (giũ sạch nước), prod_3 (combo 10/50 chiếc), prod_5 (cọ chảo chống dính)
        ]
        chosen_idx = orders[r_idx % len(orders)]
        return [all_prods[i % n] for i in chosen_idx]

    return [all_prods[(r_idx + k) % n] for k in range(3)]


def _extract_short_usp_labels(product_name: str, product_info: str, price_str: str = "") -> dict:
    """Trích xuất bộ nhãn ngắn gọn Tiếng Việt có dấu chuẩn xác (dùng ký tự ♦ ► √ chuẩn font Windows WGL4)."""
    combined = f"{product_name or ''} {product_info or ''}".lower()
    price_clean = "Giá Xưởng"
    if price_str:
        num = re.sub(r"[^\d]", "", str(price_str))
        if num:
            val = int(num)
            price_clean = f"{val:,}đ".replace(",", ".")

    pname_low = (product_name or "").lower()
    if "khăn lưới" in pname_low or "rửa chén" in pname_low or "cọ xoong" in pname_low:
        return {
            "is_mesh_cloth": True,
            "header": "► ẢNH THẬT SẢN PHẨM • KHĂN LƯỚI KIM LOẠI ĐA NĂNG ◄",
            "card_badges": ["♦ CẬN CẢNH LƯỚI", "♦ ĐÁNH BAY DẦU MỠ", "♦ COMBO TIẾT KIỆM"],
            "card_labels": ["Mềm dẻo luồn góc kẹt", "Cọ sạch không trầy nồi", "Combo 10 - 50 khăn"],
            "footer_usps": ["√ Không trầy chống dính", "√ Dễ giũ sạch dầu mỡ", "√ Bền gấp 10 lần"],
            "five_icons": [
                ("01", "Lưới Kim Loại", "Đan kép bền bỉ"),
                ("02", "Không Trầy", "An toàn nồi chảo"),
                ("03", "Sạch Dầu Mỡ", "Đánh bay vết cháy"),
                ("04", "Rửa Trôi Nhanh", "Không bám mùi"),
                ("HOT", f"Chỉ {price_clean}", "Trợ giá tận xưởng"),
            ],
            "short_title_cta": "KHĂN LƯỚI KIM LOẠI RỬA CHÉN ĐA NĂNG 20X20CM",
            "price_cta": f"► CHỈ {price_clean} • SĂN NGAY",
        }

    short_p = re.sub(r"\s+", " ", (product_name or "Sản phẩm chính hãng").strip())
    if len(short_p) > 34:
        short_p = short_p[:32].rstrip() + "…"

    if any(k in pname_low for k in ("dép", "giày", "sandal", "clog", "sục", "boot")):
        return {
            "is_mesh_cloth": False,
            "header": f"► ẢNH THẬT CHI TIẾT • {short_p.upper()} ◄",
            "card_badges": ["♦ CẬN CẢNH QUAI/MŨI", "♦ ĐẾ ÊM CHỐNG TRƯỢT", "♦ LÊN FORM TÔN DÁNG"],
            "card_labels": ["Đường khâu sắc sảo", "Cao su nguyên khối êm", "Đủ size Nam/Nữ chuẩn"],
            "footer_usps": ["√ Đế êm đi cả ngày", "√ Chống trượt an toàn", "√ Đổi size miễn phí"],
            "five_icons": [
                ("01", "Đế Êm Siêu Nhẹ", "Đi cả ngày không mỏi"),
                ("02", "Chống Trơn Trượt", "Rãnh ma sát an toàn"),
                ("03", "Chất Liệu Bền Đẹp", "Chống thấm dễ vệ sinh"),
                ("04", "Form Chuẩn Tôn Dáng", "Dễ phối đồ mọi dịp"),
                ("HOT", f"Chỉ {price_clean}", "Trợ giá hôm nay"),
            ],
            "short_title_cta": short_p.upper(),
            "price_cta": f"► CHỈ {price_clean} • SĂN NGAY",
        }

    if any(k in pname_low for k in ("nồi", "ấm", "lồng bàn", "bếp", "chảo", "hấp")):
        return {
            "is_mesh_cloth": False,
            "header": f"► TRỌN BỘ TIỆN ÍCH NHÀ BẾP • {short_p.upper()} ◄",
            "card_badges": ["♦ CHẤT LIỆU AN TOÀN", "♦ CÔNG NĂNG ĐA DẠNG", "♦ TRỌN BỘ TIẾT KIỆM"],
            "card_labels": ["Inox 304 / Nhựa nguyên sinh", "Giữ nhiệt & truyền nhiệt", "Dễ tháo lắp vệ sinh"],
            "footer_usps": ["√ An toàn thực phẩm", "√ Bền bỉ gấp 5 lần", "√ Bảo hành chính hãng"],
            "five_icons": [
                ("01", "Vật Liệu Cao Cấp", "An toàn cho sức khỏe"),
                ("02", "Thiết Kế Thông Minh", "Tiết kiệm không gian"),
                ("03", "Đa Năng Tiện Dụng", "Nấu/Hấp/Bảo quản"),
                ("04", "Dễ Dàng Vệ Sinh", "Không bám bẩn dầu mỡ"),
                ("HOT", f"Chỉ {price_clean}", "Ưu đãi tận xưởng"),
            ],
            "short_title_cta": short_p.upper(),
            "price_cta": f"► CHỈ {price_clean} • MUA NGAY",
        }

    if any(k in pname_low for k in ("áo", "váy", "đầm", "quần", "jogger", "len", "set")):
        return {
            "is_mesh_cloth": False,
            "header": f"► CẬN CẢNH CHẤT VẢI & FORM DÁNG • {short_p.upper()} ◄",
            "card_badges": ["♦ FORM LÊN DÁNG", "♦ CẬN CẢNH CHẤT VẢI", "♦ ĐƯỜNG KIM MŨI CHỈ"],
            "card_labels": ["Tôn dáng che khuyết điểm", "Vải mềm mịn thoáng mát", "May kỹ chuẩn xuất khẩu"],
            "footer_usps": ["√ Không xù không bai", "√ Đủ màu đủ size", "√ Kiểm hàng trước nhận"],
            "five_icons": [
                ("01", "Chất Vải Mềm Mịn", "Mặc cực kỳ thoải mái"),
                ("02", "Form Chuẩn Tôn Dáng", "Hack dáng trẻ trung"),
                ("03", "Đường May Tinh Tế", "Tỉ mỉ từng chi tiết"),
                ("04", "Dễ Phối Nhiều Đồ", "Đi học, đi làm, dạo phố"),
                ("HOT", f"Chỉ {price_clean}", "Săn deal giảm sâu"),
            ],
            "short_title_cta": short_p.upper(),
            "price_cta": f"► CHỈ {price_clean} • SĂN NGAY",
        }

    if any(k in pname_low for k in ("túi", "balo", "ví", "bóp")):
        return {
            "is_mesh_cloth": False,
            "header": f"► CHI TIẾT NGĂN CHỨA & CHẤT LIỆU • {short_p.upper()} ◄",
            "card_badges": ["♦ FORM TÚI CỨNG CÁP", "♦ NGĂN CHỨA RỘNG RÃI", "♦ KHÓA KÉO & DÂY ĐEO"],
            "card_labels": ["Da/Vải chống thấm tốt", "Đựng vừa điện thoại, mỹ phẩm", "Khóa kim loại mượt mà"],
            "footer_usps": ["√ Ngăn chứa khoa học", "√ Khóa kéo bền mượt", "√ Chuẩn hình 100%"],
            "five_icons": [
                ("01", "Ngăn Chứa Rộng Rãi", "Đựng gọn đồ cá nhân"),
                ("02", "Khóa Kéo Mượt Mà", "Kim loại chống gỉ sét"),
                ("03", "Chất Liệu Bền Đẹp", "Chống thấm dễ lau chùi"),
                ("04", "Siêu Nhẹ Thời Trang", "Phù hợp đi học, đi làm"),
                ("HOT", f"Chỉ {price_clean}", "Giá tốt hôm nay"),
            ],
            "short_title_cta": short_p.upper(),
            "price_cta": f"► CHỈ {price_clean} • MUA NGAY",
        }

    if any(k in pname_low for k in ("máy đo", "oxy", "y tế", "cân", "điện tử", "đèn")):
        return {
            "is_mesh_cloth": False,
            "header": f"► THÔNG SỐ KỸ THUẬT & MÀN HÌNH • {short_p.upper()} ◄",
            "card_badges": ["♦ MÀN HÌNH SẮC NÉT", "♦ CẢM BIẾN CHÍNH XÁC", "♦ THIẾT KẾ NHỎ GỌN"],
            "card_labels": ["Hiển thị chữ số rõ ràng", "Đo nhanh chỉ sau 3 giây", "Tiết kiệm pin bền bỉ"],
            "footer_usps": ["√ Cảm biến chuẩn xác", "√ Một nút bấm dễ dùng", "√ Bảo hành 1 đổi 1"],
            "five_icons": [
                ("SpO2", "Đo Nồng Độ Oxy", "Chính xác chuẩn y khoa"),
                ("PR", "Đo Nhịp Tim Mạch", "Theo dõi tức thì 3 giây"),
                ("OLED", "Màn Hình Đổi Chiều", "Chữ số to rõ dễ đọc"),
                ("PIN", "Tiết Kiệm Năng Lượng", "Tự động tắt thông minh"),
                ("100%", "Bảo Hành Uy Tín", f"Ưu đãi chỉ {price_clean}"),
            ],
            "short_title_cta": short_p.upper(),
            "price_cta": f"► CHỈ {price_clean} • ĐẶT NGAY",
        }

    return {
        "is_mesh_cloth": False,
        "header": f"► ẢNH CHI TIẾT SẢN PHẨM • {short_p.upper()} ◄",
        "card_badges": ["♦ GÓC CẬN CẢNH", "♦ CHẤT LIỆU THẬT", "♦ ĐỦ PHÂN LOẠI"],
        "card_labels": ["Hình ảnh thực tế 100%", "Chất lượng kiểm định", "Đóng gói chuẩn xưởng"],
        "footer_usps": ["√ Chuẩn hình 100%", "√ Đổi trả miễn phí", "√ Giao nhanh toàn quốc"],
        "five_icons": [
            ("01", "Chuẩn Xưởng", "Kiểm định kỹ"),
            ("02", "Chất Liệu Xịn", "Bền đẹp lâu dài"),
            ("03", "Ảnh Thật 100%", "Y hình quảng cáo"),
            ("04", "Ship Toàn Quốc", "Nhận hàng kiểm tra"),
            ("HOT", f"Chỉ {price_clean}", "Ưu đãi hôm nay"),
        ],
        "short_title_cta": short_p.upper(),
        "price_cta": f"► CHỈ {price_clean} • MUA NGAY",
    }


def _make_rounded_photo_card(
    photo_im: Image.Image,
    card_w: int,
    card_h: int,
    radius: int,
    border_color: tuple,
    border_width: int,
    top_badge_text: str,
    bottom_label_text: str,
    pill_bg: tuple,
    pill_text: tuple,
    accent_color: tuple,
) -> Image.Image:
    """Tạo 1 thẻ ảnh sản phẩm bo góc có viền nổi, đổ bóng, tem góc trên và thanh nhãn Tiếng Việt phía dưới."""
    pad = 10
    total_w, total_h = card_w + pad * 2, card_h + pad * 2
    card_canvas = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

    # Đổ bóng mềm
    shadow = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rounded_rectangle(
        [pad + 2, pad + 5, pad + card_w + 2, pad + card_h + 5],
        radius=radius,
        fill=(0, 0, 0, 145),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    card_canvas.alpha_composite(shadow)

    # Mask bo góc cho ảnh sản phẩm
    mask = Image.new("L", (card_w, card_h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=radius, fill=255)

    resized_photo = photo_im.resize((card_w, card_h), Image.Resampling.LANCZOS).convert("RGBA")

    # Vẽ thanh nhãn dưới đáy thẻ ảnh
    ov = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    o_draw = ImageDraw.Draw(ov)
    bar_h = 56
    for y in range(card_h - bar_h - 18, card_h):
        ratio = max(0.0, min(1.0, (y - (card_h - bar_h - 18)) / float(bar_h + 18)))
        alpha = int(235 * (ratio ** 1.15))
        o_draw.line([(0, y), (card_w, y)], fill=(pill_bg[0], pill_bg[1], pill_bg[2], alpha))

    f_lbl = _load_vn_font(23, bold=True)
    f_bdg = _load_vn_font(18, bold=True)

    if bottom_label_text:
        lbl_str = _fit_text(o_draw, bottom_label_text, f_lbl, card_w - 20)
        bb = o_draw.textbbox((0, 0), lbl_str, font=f_lbl)
        tw = bb[2] - bb[0]
        tx = max(10, (card_w - tw) // 2)
        ty = card_h - bar_h + 14
        o_draw.text((tx + 1, ty + 2), lbl_str, font=f_lbl, fill=(0, 0, 0, 210))
        o_draw.text((tx, ty), lbl_str, font=f_lbl, fill=pill_text + (255,) if len(pill_text) == 3 else pill_text)

    if top_badge_text:
        bdg_str = _fit_text(o_draw, top_badge_text, f_bdg, card_w - 24)
        bb2 = o_draw.textbbox((0, 0), bdg_str, font=f_bdg)
        bw = (bb2[2] - bb2[0]) + 22
        bh = 32
        o_draw.rounded_rectangle(
            [10, 10, 10 + bw, 10 + bh],
            radius=12,
            fill=(15, 23, 42, 215),
            outline=accent_color + (255,) if len(accent_color) == 3 else accent_color,
            width=2,
        )
        o_draw.text((21, 15), bdg_str, font=f_bdg, fill=(255, 255, 255, 255))

    merged_inner = Image.alpha_composite(resized_photo, ov)
    card_inner = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    card_inner.paste(merged_inner, (0, 0), mask)

    # Viền ngoài sắc nét
    b_draw = ImageDraw.Draw(card_inner)
    b_draw.rounded_rectangle(
        [1, 1, card_w - 2, card_h - 2],
        radius=radius,
        outline=border_color + (255,) if len(border_color) == 3 else border_color,
        width=border_width,
    )
    if border_width >= 4:
        b_draw.rounded_rectangle(
            [border_width + 1, border_width + 1, card_w - border_width - 2, card_h - border_width - 2],
            radius=max(6, radius - border_width),
            outline=accent_color + (220,) if len(accent_color) == 3 else accent_color,
            width=2,
        )

    card_canvas.alpha_composite(card_inner, (pad, pad))
    return card_canvas


def _make_circular_zoom_inset(
    photo_im: Image.Image,
    diameter: int,
    ring_color: tuple,
    outer_color: tuple,
    badge_text: str,
    caption_text: str,
    pill_bg: tuple,
) -> Image.Image:
    """Tạo khung Vòng Tròn Zoom Chi Tiết Sản Phẩm (viền vàng kim / trắng kép + nhãn công dụng dưới vòng tròn)."""
    pad = 12
    total_w = diameter + pad * 2
    total_h = diameter + 58 + pad * 2
    canvas = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

    # Bóng đổ tròn
    sh = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.ellipse([pad + 2, pad + 5, pad + diameter + 2, pad + diameter + 5], fill=(0, 0, 0, 155))
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    canvas.alpha_composite(sh)

    # Mask hình tròn cho ảnh SP
    mask = Image.new("L", (diameter, diameter), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([0, 0, diameter - 1, diameter - 1], fill=255)

    p_resized = photo_im.resize((diameter, diameter), Image.Resampling.LANCZOS).convert("RGBA")
    circle_im = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    circle_im.paste(p_resized, (0, 0), mask)

    cd = ImageDraw.Draw(circle_im)
    cd.ellipse([1, 1, diameter - 2, diameter - 2], outline=outer_color + (255,), width=7)
    cd.ellipse([8, 8, diameter - 9, diameter - 9], outline=ring_color + (255,), width=3)

    canvas.alpha_composite(circle_im, (pad, pad))

    # Nhãn trên đỉnh vòng tròn
    draw = ImageDraw.Draw(canvas)
    f_bdg = _load_vn_font(17, bold=True)
    f_cap = _load_vn_font(22, bold=True)

    if badge_text:
        b_str = _fit_text(draw, badge_text, f_bdg, diameter - 24)
        bb = draw.textbbox((0, 0), b_str, font=f_bdg)
        bw = (bb[2] - bb[0]) + 22
        bx = pad + (diameter - bw) // 2
        by = pad - 4
        draw.rounded_rectangle([bx, by, bx + bw, by + 30], radius=14, fill=(15, 23, 42, 235), outline=ring_color + (255,), width=2)
        draw.text((bx + 11, by + 5), b_str, font=f_bdg, fill=(255, 255, 255, 255))

    # Thanh pill chú thích dưới vòng tròn
    if caption_text:
        c_str = _fit_text(draw, caption_text, f_cap, total_w - 12)
        py1 = pad + diameter - 14
        py2 = py1 + 48
        draw.rounded_rectangle(
            [6, py1, total_w - 6, py2],
            radius=20,
            fill=pill_bg + (245,),
            outline=outer_color + (255,),
            width=3,
        )
        bb2 = draw.textbbox((0, 0), c_str, font=f_cap)
        tw = bb2[2] - bb2[0]
        tx = max(12, (total_w - tw) // 2)
        draw.text((tx + 1, py1 + 11), c_str, font=f_cap, fill=(0, 0, 0, 190))
        draw.text((tx, py1 + 10), c_str, font=f_cap, fill=(255, 255, 255, 255))

    return canvas


def _make_polaroid_frame(
    photo_im: Image.Image,
    photo_w: int,
    photo_h: int,
    caption_text: str,
    tilt_deg: float,
    accent_color: tuple,
) -> Image.Image:
    """Tạo khung ảnh Polaroid có viền trắng dày, ghi chú bên dưới và miếng băng dính dán ở đỉnh."""
    border_side = 16
    border_top = 20
    border_bot = 66
    pw = photo_w + border_side * 2
    ph = photo_h + border_top + border_bot

    base = Image.new("RGBA", (pw + 24, ph + 32), (0, 0, 0, 0))
    sh = Image.new("RGBA", (pw + 24, ph + 32), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle([14, 18, 14 + pw, 18 + ph], radius=10, fill=(0, 0, 0, 130))
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    base.alpha_composite(sh)

    pol = Image.new("RGBA", (pw, ph), (255, 255, 255, 255))
    p_draw = ImageDraw.Draw(pol)
    p_draw.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=8, fill=(255, 255, 255, 255), outline=(214, 211, 209, 255), width=2)

    p_resized = photo_im.resize((photo_w, photo_h), Image.Resampling.LANCZOS).convert("RGBA")
    pol.paste(p_resized, (border_side, border_top))
    p_draw.rectangle([border_side, border_top, border_side + photo_w - 1, border_top + photo_h - 1], outline=(229, 231, 235, 255), width=2)

    f_cap = _load_vn_font(22, bold=True)
    if caption_text:
        c_str = _fit_text(p_draw, caption_text, f_cap, pw - 20)
        bb = p_draw.textbbox((0, 0), c_str, font=f_cap)
        tw = bb[2] - bb[0]
        tx = max(10, (pw - tw) // 2)
        ty = border_top + photo_h + 16
        p_draw.text((tx, ty), c_str, font=f_cap, fill=accent_color + (255,))

    base.alpha_composite(pol, (12, 14))

    # Miếng băng dính Washi Tape ở giữa đỉnh Polaroid
    tape_w, tape_h = 110, 26
    tape = Image.new("RGBA", (tape_w, tape_h), (253, 224, 71, 185))
    td = ImageDraw.Draw(tape)
    td.rectangle([0, 0, tape_w - 1, tape_h - 1], outline=(250, 204, 21, 230), width=1)
    base.alpha_composite(tape, (12 + (pw - tape_w) // 2, 3))

    if abs(tilt_deg) > 0.2:
        base = base.rotate(tilt_deg, resample=Image.Resampling.BICUBIC, expand=True)
    return base


def composite_template_product_insets(
    img_path: str,
    pdir: str,
    prod_img_paths: list,
    template_obj: dict,
    meta: dict,
) -> bool:
    """
    Ghép cụm Ảnh Sản Phẩm Thực Tế (`prod_1.jpg .. prod_6.jpg`) + Infographic USP + Giá Bán
    lên ảnh Thumbnail `img_path` (1080x1920) theo đúng `layout_type` của `template_obj`.
    Luôn lưu bản backup 2K gốc tại `{base}_raw2k.jpg` để khi đổi Template có thể render lại tức thì!
    """
    if not os.path.isfile(img_path):
        return False

    # 1. Bảo toàn file AI 2K gốc (`_raw2k.jpg`) để tránh vẽ đè nhiều lần khi đổi Template
    base_no_ext, ext = os.path.splitext(img_path)
    raw_backup_path = f"{base_no_ext}_raw2k{ext}"
    if not os.path.isfile(raw_backup_path) or os.path.getsize(raw_backup_path) < 10000:
        shutil.copy2(img_path, raw_backup_path)

    src_path = raw_backup_path if os.path.isfile(raw_backup_path) else img_path
    vkey = str(meta.get("vkey") or "v1")
    product_name = str(meta.get("product_name") or "")
    product_info = str(meta.get("product_info") or "")
    price_str = str(meta.get("price") or "")

    chosen_prods = _select_3_product_photos_for_variant(pdir, prod_img_paths, vkey)
    if not chosen_prods:
        return False

    with Image.open(src_path) as im:
        im_rgb = im.convert("RGB")
        target_w, target_h = 1080, 1920
        sw, sh = im_rgb.size
        scale = max(target_w / float(max(1, sw)), target_h / float(max(1, sh)))
        nw, nh = int(round(sw * scale)), int(round(sh * scale))
        im_resized = im_rgb.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - target_w) // 2
        top = (nh - target_h) // 2
        cropped_bg = im_resized.crop((left, top, left + target_w, top + target_h))
        # Dịch nhẹ vùng trên (y=0..1420) lên vùng (y=0..1320) để toàn bộ Nhân vật + Tay cầm SP + Giá nằm gọn phía trên Dock SP!
        upper_zone = cropped_bg.crop((0, 0, 1080, 1410)).resize((1080, 1325), Image.Resampling.LANCZOS)
        canvas = cropped_bg.convert("RGBA")
        canvas.paste(upper_zone.convert("RGBA"), (0, 0))

    palette = template_obj.get("palette") or THUMBNAIL_TEMPLATES[0]["palette"]
    layout_type = str(template_obj.get("layout_type") or "grid_3_bottom")
    labels = _extract_short_usp_labels(product_name, product_info, price_str)
    is_mesh = bool(labels.get("is_mesh_cloth", False))
    photo_meta = [
        _get_photo_specific_badge_and_label(chosen_prods[i], i, labels["card_badges"], labels["card_labels"], is_mesh)
        for i in range(3)
    ]

    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 2. Vẽ nền Dock trưng bày Sản Phẩm ở vùng dưới (`y=1310..1920`) với hiệu ứng chuyển sắc mượt mà
    dock_top_y = 1315
    grad_start_y = 1260
    bg_top = palette["dock_bg_top"]
    bg_bot = palette["dock_bg_bot"]
    acc = palette["accent_rgb"]

    for y in range(grad_start_y, 1920):
        if y < dock_top_y:
            ratio = (y - grad_start_y) / float(max(1, dock_top_y - grad_start_y))
            alpha = int(bg_top[3] * (ratio ** 1.6))
            r, g, b = bg_top[0], bg_top[1], bg_top[2]
        else:
            t = (y - dock_top_y) / float(max(1, 1920 - dock_top_y))
            r = int(bg_top[0] * (1 - t) + bg_bot[0] * t)
            g = int(bg_top[1] * (1 - t) + bg_bot[1] * t)
            b = int(bg_top[2] * (1 - t) + bg_bot[2] * t)
            alpha = int(bg_top[3] * (1 - t) + bg_bot[3] * t)
        draw.line([(0, y), (1080, y)], fill=(r, g, b, alpha))

    # Đường viền phát sáng ngăn cách tinh tế tại đỉnh Dock
    draw.line([(28, dock_top_y), (1052, dock_top_y)], fill=acc + (220,), width=4)

    # Thanh Header Pill giới thiệu cụm Ảnh Sản Phẩm Thực Tế (`y=1290..1336`)
    f_hdr = _load_vn_font(22, bold=True)
    hdr_text = _fit_text(draw, labels["header"], f_hdr, 960)
    hb = draw.textbbox((0, 0), hdr_text, font=f_hdr)
    hw = (hb[2] - hb[0]) + 48
    hx = (1080 - hw) // 2
    hy = 1290
    draw.rounded_rectangle(
        [hx, hy, hx + hw, hy + 46],
        radius=23,
        fill=palette["pill_bg"] + (250,),
        outline=(255, 255, 255, 255),
        width=3,
    )
    draw.text((hx + 24, hy + 10), hdr_text, font=f_hdr, fill=(255, 255, 255, 255))

    canvas = Image.alpha_composite(canvas, overlay)

    # 3. Render từng bố cục khung Ảnh Sản Phẩm Thực Tế theo `layout_type`
    if layout_type == "infographic_tech_3cards":
        # Bố cục 2: 1 Ảnh Lớn Trước/Sau bên trái (576x390) + 2 Ảnh Phụ xếp chồng bên phải (410x186)
        im_a = _smart_crop_product_photo(chosen_prods[0], 576, 390)
        card_a = _make_rounded_photo_card(
            im_a, 576, 390, 24,
            palette["card_border"], 5,
            photo_meta[0][0],
            photo_meta[0][1],
            palette["pill_bg"], palette["pill_text"], acc,
        )
        canvas.alpha_composite(card_a, (26, 1342))

        im_b = _smart_crop_product_photo(chosen_prods[1], 410, 186)
        card_b = _make_rounded_photo_card(
            im_b, 410, 186, 20,
            palette["card_border"], 4,
            photo_meta[1][0],
            photo_meta[1][1],
            palette["pill_bg"], palette["pill_text"], acc,
        )
        canvas.alpha_composite(card_b, (624, 1342))

        im_c = _smart_crop_product_photo(chosen_prods[2], 410, 186)
        card_c = _make_rounded_photo_card(
            im_c, 410, 186, 20,
            palette["card_border"], 4,
            photo_meta[2][0],
            photo_meta[2][1],
            palette["pill_bg"], palette["pill_text"], acc,
        )
        canvas.alpha_composite(card_c, (624, 1546))

    elif layout_type == "macro_3cards_5icons":
        # Bố cục 3 (Mẫu 792917470): 3 Thẻ vuông bo góc (316x316) + 5 Huy hiệu tròn cam kết dưới đáy
        xs = [32, 382, 732]
        for idx in range(3):
            im_p = _smart_crop_product_photo(chosen_prods[idx], 316, 320)
            card_p = _make_rounded_photo_card(
                im_p, 316, 320, 24,
                palette["card_border"], 5,
                photo_meta[idx][0],
                photo_meta[idx][1],
                palette["pill_bg"], palette["pill_text"], acc,
            )
            canvas.alpha_composite(card_p, (xs[idx] - 10, 1340))

        # Vẽ 5 huy hiệu tròn ở đáy (`y=1695..1905`)
        bot_ov = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(bot_ov)
        f_ic_t = _load_vn_font(20, bold=True)
        f_ic_s = _load_vn_font(16, bold=False)
        five_items = labels["five_icons"][:5]
        col_w = 1020 // 5
        for i, (num_str, t_main, t_sub) in enumerate(five_items):
            cx = 30 + col_w * i + col_w // 2
            cy = 1752
            r_c = 42
            b_draw.ellipse(
                [cx - r_c, cy - r_c, cx + r_c, cy + r_c],
                fill=palette["pill_bg"] + (255,),
                outline=(255, 255, 255, 255),
                width=4,
            )
            nb = b_draw.textbbox((0, 0), num_str, font=f_ic_t)
            b_draw.text((cx - (nb[2] - nb[0]) // 2, cy - 13), num_str, font=f_ic_t, fill=(254, 240, 138, 255))

            m_str = _fit_text(b_draw, t_main, f_ic_t, col_w - 8)
            mb = b_draw.textbbox((0, 0), m_str, font=f_ic_t)
            b_draw.text((cx - (mb[2] - mb[0]) // 2, 1804), m_str, font=f_ic_t, fill=(20, 83, 45, 255))

            s_str = _fit_text(b_draw, t_sub, f_ic_s, col_w - 6)
            sb = b_draw.textbbox((0, 0), s_str, font=f_ic_s)
            b_draw.text((cx - (sb[2] - sb[0]) // 2, 1832), s_str, font=f_ic_s, fill=(55, 65, 81, 255))

        canvas = Image.alpha_composite(canvas, bot_ov)

    elif layout_type == "circle_zoom_left":
        # Bố cục 5/7/12: 3 Vòng Tròn Zoom Chi Tiết Viền Vàng Kim / Rose Gold (308px mỗi vòng)
        xs = [30, 374, 718]
        for idx in range(3):
            im_p = _smart_crop_product_photo(chosen_prods[idx], 308, 308)
            circ = _make_circular_zoom_inset(
                im_p, 308,
                ring_color=acc,
                outer_color=palette["card_border"],
                badge_text=photo_meta[idx][0],
                caption_text=photo_meta[idx][1],
                pill_bg=palette["pill_bg"],
            )
            canvas.alpha_composite(circ, (xs[idx], 1342))

    elif layout_type == "polaroid_collage":
        # Bố cục 8/11: 2 Khung Ảnh Polaroid Dán Băng Dính + 1 Bảng Giấy Note Kẻ Ngang Ghi Ưu Điểm
        im_1 = _smart_crop_product_photo(chosen_prods[0], 286, 286)
        pol_1 = _make_polaroid_frame(im_1, 286, 286, photo_meta[0][1], -3.5, acc)
        canvas.alpha_composite(pol_1, (22, 1344))

        im_2 = _smart_crop_product_photo(chosen_prods[1], 286, 286)
        pol_2 = _make_polaroid_frame(im_2, 286, 286, photo_meta[1][1], 3.0, acc)
        canvas.alpha_composite(pol_2, (366, 1346))

        # Tờ giấy Note kèm ảnh nhỏ thứ 3 bên phải (`x=716..1048, y=1352..1742`)
        note_ov = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        n_draw = ImageDraw.Draw(note_ov)
        nx1, ny1, nx2, ny2 = 716, 1352, 1048, 1742
        n_draw.rounded_rectangle([nx1 + 4, ny1 + 6, nx2 + 4, ny2 + 6], radius=20, fill=(0, 0, 0, 110))
        n_draw.rounded_rectangle([nx1, ny1, nx2, ny2], radius=20, fill=(255, 255, 255, 250), outline=acc + (255,), width=4)
        # Đường kẻ ngang sổ tay
        for ly in range(ny1 + 65, ny2 - 20, 44):
            n_draw.line([(nx1 + 18, ly), (nx2 - 18, ly)], fill=(229, 231, 235, 255), width=2)

        f_nt = _load_vn_font(21, bold=True)
        f_nb = _load_vn_font(19, bold=True)
        n_draw.rounded_rectangle([nx1 + 16, ny1 + 14, nx2 - 16, ny1 + 54], radius=12, fill=palette["pill_bg"] + (255,))
        n_draw.text((nx1 + 28, ny1 + 21), "► ĐIỂM NỔI BẬT ◄", font=f_nt, fill=(255, 255, 255, 255))

        for k_i, u_txt in enumerate(labels["footer_usps"][:3]):
            u_clean = _fit_text(n_draw, u_txt, f_nb, (nx2 - nx1) - 32)
            n_draw.text((nx1 + 18, ny1 + 72 + k_i * 46), u_clean, font=f_nb, fill=(31, 41, 55, 255))

        canvas = Image.alpha_composite(canvas, note_ov)
        # Ghép thêm ảnh SP thứ 3 ở góc dưới bảng Note
        im_3 = _smart_crop_product_photo(chosen_prods[2], 292, 142)
        card_3 = _make_rounded_photo_card(
            im_3, 292, 142, 16,
            palette["pill_bg"], 3,
            "", photo_meta[2][1],
            palette["pill_bg"], palette["pill_text"], acc,
        )
        canvas.alpha_composite(card_3, (nx1 + 10, ny1 + 218))

    elif layout_type == "split_flash_deal":
        # Bố cục 6/9: 2 Khung Ảnh Sản Phẩm Cực Lớn Đối Xứng (482x385) + 1 Vòng Tròn Phụ Ở Giữa
        im_left = _smart_crop_product_photo(chosen_prods[0], 482, 385)
        card_left = _make_rounded_photo_card(
            im_left, 482, 385, 24,
            palette["card_border"], 5,
            photo_meta[0][0],
            photo_meta[0][1],
            palette["pill_bg"], palette["pill_text"], acc,
        )
        canvas.alpha_composite(card_left, (22, 1342))

        im_right = _smart_crop_product_photo(chosen_prods[1], 482, 385)
        card_right = _make_rounded_photo_card(
            im_right, 482, 385, 24,
            palette["card_border"], 5,
            photo_meta[1][0],
            photo_meta[1][1],
            palette["pill_bg"], palette["pill_text"], acc,
        )
        canvas.alpha_composite(card_right, (556, 1342))

        # Vòng tròn cận cảnh ảnh thứ 3 ở tâm điểm giao nhau
        im_mid = _smart_crop_product_photo(chosen_prods[2], 156, 156)
        circ_mid = _make_circular_zoom_inset(
            im_mid, 156,
            ring_color=acc,
            outer_color=(255, 255, 255),
            badge_text="COMBO",
            caption_text="",
            pill_bg=palette["pill_bg"],
        )
        canvas.alpha_composite(circ_mid, (450, 1445))

    elif layout_type == "kawaii_sticker_callouts":
        # Bố cục 4: 3 Sticker Sản Phẩm Viền Trắng Dày Nổi Khối + Nghiêng Nhẹ Kawaii
        xs = [30, 380, 730]
        tilts = [-2.5, 0.0, 2.5]
        for idx in range(3):
            im_p = _smart_crop_product_photo(chosen_prods[idx], 316, 375)
            card_p = _make_rounded_photo_card(
                im_p, 316, 375, 32,
                (255, 255, 255), 8,
                photo_meta[idx][0],
                photo_meta[idx][1],
                palette["pill_bg"], palette["pill_text"], acc,
            )
            if abs(tilts[idx]) > 0.1:
                card_p = card_p.rotate(tilts[idx], resample=Image.Resampling.BICUBIC, expand=False)
            canvas.alpha_composite(card_p, (xs[idx] - 10, 1342))

    elif layout_type in (
        "left_pills_3scene_bar",
        "cookware_set_4breakdown",
        "multicooker_3food_tabs",
        "medical_tech_5metrics",
        "mens_luxury_dark_gold",
        "fresh_shield_5layers",
        "size_lineup_comparison",
        "model_flatlay_swatch_dots",
        "pov_hands_pointer_arrows",
        "influencer_3circle_left_music",
        "mega_6grid_bag_showcase",
    ):
        from thumbnail_template_layouts_ext import render_extended_layout
        canvas = render_extended_layout(
            layout_type=layout_type,
            canvas=canvas,
            chosen_prods=chosen_prods,
            photo_meta=photo_meta,
            labels=labels,
            palette=palette,
            smart_crop_fn=_smart_crop_product_photo,
            make_card_fn=_make_rounded_photo_card,
            make_circle_fn=_make_circular_zoom_inset,
            load_font_fn=_load_vn_font,
            fit_text_fn=_fit_text,
        )

    else:
        # Mặc định `grid_3_bottom`: 3 Khung Ảnh Sản Phẩm Thực Tế Bo Góc (318x385) chuẩn Mall
        xs = [30, 381, 732]
        for idx in range(3):
            im_p = _smart_crop_product_photo(chosen_prods[idx], 318, 385)
            card_p = _make_rounded_photo_card(
                im_p, 318, 385, 24,
                palette["card_border"], 5,
                photo_meta[idx][0],
                photo_meta[idx][1],
                palette["pill_bg"], palette["pill_text"], acc,
            )
            canvas.alpha_composite(card_p, (xs[idx] - 10, 1342))

    # Nếu `meta.get("draw_top_headline")` bật (dùng cho ảnh nền AI chưa có chữ trên đỉnh hoặc tạo Demo Thumbnail)
    if meta.get("draw_top_headline"):
        from thumbnail_template_layouts_ext import draw_top_commercial_headline_banner
        style_var = "dark_gold" if layout_type in ("mens_luxury_dark_gold", "split_flash_deal", "infographic_tech_3cards") else "pastel_3d"
        canvas = draw_top_commercial_headline_banner(
            canvas=canvas,
            title_main=str(meta.get("top_title") or labels.get("short_title_cta") or product_name),
            subtitle_pill=str(meta.get("top_subtitle") or template_obj.get("style_badge") or "CHÍNH HÃNG 100% • GIÁ TẬN XƯỞNG"),
            price_badge=str(meta.get("top_price_badge") or f"CHỈ {price_str or '18.000đ'}"),
            palette=palette,
            load_font_fn=_load_vn_font,
            fit_text_fn=_fit_text,
            style_variant=style_var,
        )

    # 4. Thanh Footer Cam Kết & Nút Giá Bán / CTA ở đáy (`y=1758..1900`) cho mọi bố cục (trừ macro_3cards_5icons đã có 5 icon)
    if layout_type != "macro_3cards_5icons":
        foot_ov = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        f_draw = ImageDraw.Draw(foot_ov)
        f_usp = _load_vn_font(21, bold=True)
        f_cta = _load_vn_font(24, bold=True)

        # Hàng 3 pill ưu điểm (`y=1755..1808`)
        usps = labels["footer_usps"][:3]
        pw_u = 326
        for i, u_str in enumerate(usps):
            ux = 32 + i * (pw_u + 18)
            uy = 1754
            f_draw.rounded_rectangle(
                [ux, uy, ux + pw_u, uy + 48],
                radius=16,
                fill=(15, 23, 42, 215),
                outline=acc + (220,),
                width=2,
            )
            u_fit = _fit_text(f_draw, u_str, f_usp, pw_u - 20)
            ub = f_draw.textbbox((0, 0), u_fit, font=f_usp)
            utx = ux + max(10, (pw_u - (ub[2] - ub[0])) // 2)
            f_draw.text((utx, uy + 11), u_fit, font=f_usp, fill=(255, 255, 255, 255))

        # Thanh Băng Rôn CTA & Giá Xưởng dưới cùng (`y=1816..1898`)
        cta_bg = palette["cta_bg"]
        cta_txt_col = palette["cta_text"]
        f_draw.rounded_rectangle(
            [32, 1816, 1048, 1898],
            radius=24,
            fill=cta_bg + (255,),
            outline=(255, 255, 255, 255),
            width=4,
        )
        short_prod_clean = labels.get("short_title_cta") or _fit_text(f_draw, product_name, f_cta, 560)
        cta_full = f"♦ {short_prod_clean.upper()}  |  {labels['price_cta']}"
        cta_full = _fit_text(f_draw, cta_full, f_cta, 980)
        cb = f_draw.textbbox((0, 0), cta_full, font=f_cta)
        ctx = max(48, (1080 - (cb[2] - cb[0])) // 2)
        f_draw.text((ctx + 2, 1843), cta_full, font=f_cta, fill=(0, 0, 0, 160))
        f_draw.text((ctx, 1841), cta_full, font=f_cta, fill=cta_txt_col + (255,))

        canvas = Image.alpha_composite(canvas, foot_ov)

    out_rgb = canvas.convert("RGB")
    out_rgb.save(img_path, format="JPEG", quality=96)
    return True
