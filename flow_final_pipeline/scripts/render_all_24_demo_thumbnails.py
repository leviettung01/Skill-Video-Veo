# -*- coding: utf-8 -*-
"""
🚀 Tạo toàn bộ 24 Ảnh Demo Thumbnail AI 9:16 (1080x1920) cho Kho 24 Template Thumbnail
Lưu tại `Template/Thumbnail_Templates/samples/<template_id>.jpg`
"""
import os
import sys
import glob
import shutil
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from thumbnail_template_engine import (
    WS_DIR,
    SAMPLES_DIR,
    THUMBNAIL_TEMPLATES,
    composite_template_product_insets,
    export_templates_catalog_json,
)

AI_BASES_DIR = os.path.join(SAMPLES_DIR, "ai_bases")
SUB_CROPS_DIR = os.path.join(SAMPLES_DIR, "ai_subcrops")
os.makedirs(SUB_CROPS_DIR, exist_ok=True)


def _create_3_detail_subcrops(base_img_path: str, prefix: str) -> list:
    """Tạo 6 ảnh cận cảnh chi tiết sản phẩm khác biệt rõ rệt từ ảnh AI Studio gốc (trái, macro tâm, phải, trên, dưới, chi tiết)."""
    out_paths = []
    with Image.open(base_img_path) as im:
        im_rgb = im.convert("RGB")
        w, h = im_rgb.size
        boxes = [
            (int(w * 0.08), int(h * 0.25), int(w * 0.56), int(h * 0.68)),  # 1: Góc trái sản phẩm
            (int(w * 0.30), int(h * 0.34), int(w * 0.70), int(h * 0.64)),  # 2: Macro cận cảnh bề mặt / chất liệu ở tâm
            (int(w * 0.44), int(h * 0.28), int(w * 0.94), int(h * 0.72)),  # 3: Góc phải sản phẩm / phụ kiện
            (int(w * 0.18), int(h * 0.16), int(w * 0.82), int(h * 0.54)),  # 4: Chi tiết phần trên
            (int(w * 0.16), int(h * 0.42), int(w * 0.84), int(h * 0.78)),  # 5: Chi tiết phần đế / gấu / ngăn dưới
            (int(w * 0.06), int(h * 0.18), int(w * 0.94), int(h * 0.76)),  # 6: Toàn cảnh bộ sản phẩm
        ]
        for idx, box in enumerate(boxes, 1):
            p = os.path.join(SUB_CROPS_DIR, f"{prefix}_sub_{idx}.jpg")
            im_rgb.crop(box).resize((640, 640), Image.Resampling.LANCZOS).save(p, quality=95)
            out_paths.append(p)
    return out_paths


# Cấu hình Demo thực tế cho từng Template trong 24 Templates
DEMO_CONFIGS = {
    "gia_dung_3grid_pro": {
        "base": "thumbnails/1736467481808438427_nv1_v1_thumb_raw2k.jpg",
        "pdir": "projects/1736467481808438427",
        "vkey": "v1",
        "product_name": "Khăn Lưới Kim Loại Rửa Chén Đa Năng 20x20cm",
        "price": "18.000đ",
        "draw_top_headline": False,
    },
    "gia_dung_infographic_tech": {
        "base": "thumbnails/1736467481808438427_nv1_v2_thumb_raw2k.jpg",
        "pdir": "projects/1736467481808438427",
        "vkey": "v3",
        "product_name": "Khăn Lưới Kim Loại Rửa Chén Đa Năng 20x20cm",
        "price": "18.000đ",
        "draw_top_headline": False,
    },
    "phu_kien_macro_3cards": {
        "base": "thumbnails/1736467481808438427_nv1_v3_thumb_raw2k.jpg",
        "pdir": "projects/1736467481808438427",
        "vkey": "v5",
        "product_name": "Khăn Lưới Kim Loại Rửa Chén Đa Năng 20x20cm",
        "price": "18.000đ",
        "draw_top_headline": False,
    },
    "giay_dep_kawaii_sticker": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_slides_pastel.jpg",
        "product_name": "Dép Sục Clog & Sandal Đế Êm Pastel Hàn Quốc",
        "top_title": "DÉP PASTEL SIÊU ÊM",
        "top_subtitle": "SIÊU NHẸ • CHỐNG TRƯỢT • TÔN DÁNG",
        "top_price_badge": "CHỈ 69K",
        "price": "69.000đ",
        "draw_top_headline": True,
    },
    "giay_dep_luxury_zoom": {
        "base": "thumbnails/1736467481808438427_nv2_v1_thumb_raw2k.jpg",
        "pdir": "projects/1736467481808438427",
        "vkey": "v2",
        "product_name": "Khăn Lưới Kim Loại Rửa Chén Đa Năng Cao Cấp",
        "price": "18.000đ",
        "draw_top_headline": False,
    },
    "giay_dep_flatlay_colors": {
        "base": "thumbnails/1736467481808438427_nv2_v2_thumb_raw2k.jpg",
        "pdir": "projects/1736467481808438427",
        "vkey": "v4",
        "product_name": "Combo Khăn Lưới Kim Loại Đa Năng 10 - 50 Chiếc",
        "price": "18.000đ",
        "draw_top_headline": False,
    },
    "thoi_trang_lookbook_3zoom": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_fashion_sweater_model.jpg",
        "product_name": "Set Áo Len Cổ Tim & Chân Váy Xếp Ly Hàn Quốc",
        "top_title": "LOOKBOOK THU ĐÔNG",
        "top_subtitle": "CHẤT LEN MỀM MỊN • CHUẨN FORM HÀN QUỐC",
        "top_price_badge": "CHỈ 139K",
        "price": "139.000đ",
        "draw_top_headline": True,
    },
    "genz_mirror_polaroid": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_genz_jogger_ootd.jpg",
        "product_name": "Quần Jogger Ống Rộng Đính Nơ Phong Cách GenZ",
        "top_title": "JOGGER NƠ GENZ CỰC XINH",
        "top_subtitle": "HACK DÁNG CỰC ĐỈNH • VẢI MỀM THOÁNG MÁT",
        "top_price_badge": "DEAL 89K",
        "price": "89.000đ",
        "draw_top_headline": True,
    },
    "streetwear_unisex_flashsale": {
        "base": "thumbnails/1736467481808438427_nv3_v1_thumb_raw2k.jpg",
        "pdir": "projects/1736467481808438427",
        "vkey": "nv3_v1",
        "product_name": "Khăn Lưới Kim Loại Rửa Chén Đa Năng Xả Kho",
        "price": "18.000đ",
        "draw_top_headline": False,
    },
    "thoi_trang_pastel_cta": {
        "base": "thumbnails/1736467481808438427_nv2_v3_thumb_raw2k.jpg",
        "pdir": "projects/1736467481808438427",
        "vkey": "v6",
        "product_name": "Khăn Lưới Kim Loại Đa Năng Chuẩn Bếp Xinh",
        "price": "18.000đ",
        "draw_top_headline": False,
    },
    "tui_xach_korean_scrapbook": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_tote_bag_collection.jpg",
        "product_name": "Bộ Sưu Tập Túi Tote Da & Túi Đeo Chéo Hàn Quốc",
        "top_title": "TÚI TOTE HÀN QUỐC",
        "top_subtitle": "DA MỀM CAO CẤP • ĐỰNG VỪA LAPTOP & A4",
        "top_price_badge": "CHỈ 119K",
        "price": "119.000đ",
        "draw_top_headline": True,
    },
    "my_pham_beauty_glow": {
        "base": "projects/1737909342761027082/nv1-refimg.jpg",
        "pdir": "projects/1737909342761027082",
        "vkey": "v1",
        "product_name": "Set 5 Chai Tinh Dầu Nước Hoa Dubai Luxury",
        "top_title": "NƯỚC HOA DUBAI LUXURY",
        "top_subtitle": "LƯU HƯƠNG 24H • SANG TRỌNG QUYẾN RŨ",
        "top_price_badge": "CHỈ 99K",
        "price": "99.000đ",
        "draw_top_headline": True,
    },
    # 12 STYLE MỚI
    "gia_dung_cookware_4set_bar": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_cookware_kettle.jpg",
        "product_name": "Bộ Nồi Inox 304 & Ấm Đun Siêu Tốc Giữ Nhiệt Cao Cấp",
        "top_title": "BỘ NỒI & ẤM INOX 304",
        "top_subtitle": "TRUYỀN NHIỆT NHANH • AN TOÀN SỨC KHỎE",
        "top_price_badge": "COMBO 249K",
        "price": "249.000đ",
        "draw_top_headline": True,
    },
    "gia_dung_multicooker_3tabs": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_multicooker_steamer.jpg",
        "product_name": "Nồi Điện Đa Năng 2 Tầng Hấp Nấu Lẩu Chống Dính",
        "top_title": "NỒI ĐIỆN ĐA NĂNG 2 TẦNG",
        "top_subtitle": "HẤP • NẤU • LẨU 3 TRONG 1 TIẾT KIỆM ĐIỆN",
        "top_price_badge": "CHỈ 189K",
        "price": "189.000đ",
        "draw_top_headline": True,
    },
    "gia_dung_shield_5pills": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_food_cover_multilayer.jpg",
        "product_name": "Lồng Bàn Đậy Thức Ăn Giữ Nhiệt Nhiều Tầng Thông Minh",
        "top_title": "LỒNG BÀN GIỮ NHIỆT 3 TẦNG",
        "top_subtitle": "CHỐNG BỤI & CÔN TRÙNG • GIỮ NÓNG ĐỒ ĂN",
        "top_price_badge": "CHỈ 79K",
        "price": "79.000đ",
        "draw_top_headline": True,
    },
    "giay_dep_slides_4pills_3scenes": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_slides_pastel.jpg",
        "product_name": "Dép Quai Ngang Đan Cói Đế Cao Su Êm Chân Nữ",
        "top_title": "CUTE, ÊM CHÂN & TÔN DÁNG!",
        "top_subtitle": "ĐẾ ÊM SIÊU NHẸ • DỄ PHỐI ĐỒ MỌI DỊP",
        "top_price_badge": "CHỈ 65K",
        "price": "65.000đ",
        "draw_top_headline": True,
    },
    "giay_dep_leya_check_inset": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_slides_pastel.jpg",
        "product_name": "Sandal Nữ Quai Mảnh Đính Khóa Vàng Hàn Quốc",
        "top_title": "SANDAL HÀN QUỐC ÊM NHẸ",
        "top_subtitle": "THANH LỊCH • CHỐNG TRƯỢT • ĐI HỌC ĐI LÀM",
        "top_price_badge": "CHỈ 75K",
        "price": "75.000đ",
        "draw_top_headline": True,
    },
    "thoi_trang_model_flatlay_swatch": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_fashion_sweater_model.jpg",
        "product_name": "Áo Len Cổ Tim Dáng Rộng Hàn Quốc Đủ 5 Màu",
        "top_title": "ÁO LEN CỔ TIM HÀN QUỐC",
        "top_subtitle": "MỀM MỊN ẤM ÁP • TÔN DÁNG • ĐỦ 5 MÀU HOT",
        "top_price_badge": "CHỈ 125K",
        "price": "125.000đ",
        "draw_top_headline": True,
    },
    "thoi_trang_mannequin_cottagecore": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_cottagecore_dress_mannequin.jpg",
        "product_name": "Váy Thiết Kế Công Chúa Phối Ren Hoa & Nơ Ngực",
        "top_title": "VÁY CÔNG CHÚA PHỐI REN",
        "top_subtitle": "THIẾT KẾ NÀNG THƠ • CHẤT VOAN TƠ MỀM MẠI",
        "top_price_badge": "CHỈ 169K",
        "price": "169.000đ",
        "draw_top_headline": True,
    },
    "giay_tay_nam_classy_gold": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_mens_dress_shoes.jpg",
        "product_name": "Giày Tây Nam Da Bóng Oxford & Boot Da Cao Cấp",
        "top_title": "GIÀY DA NAM LỊCH LÃM VIP",
        "top_subtitle": "DA BÓNG CAO CẤP • ĐẾ ÊM CHỐNG MÒN • FULLBOX",
        "top_price_badge": "DEAL 199K",
        "price": "199.000đ",
        "draw_top_headline": True,
    },
    "genz_influencer_3zoom_vertical": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_genz_jogger_ootd.jpg",
        "product_name": "Quần Ống Rộng Phối Nơ & Dây Rút Cá Tính GenZ",
        "top_title": "QUẦN JOGGER NƠ TRENDY",
        "top_subtitle": "CUTE • COMFY • TRENDY • DỄ MẶC MỌI NGÀY",
        "top_price_badge": "SĂN 85K",
        "price": "85.000đ",
        "draw_top_headline": True,
    },
    "tui_xach_mega_8grid_2tier": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_tote_bag_collection.jpg",
        "product_name": "Túi Đeo Chéo Trần Bông & Túi Tote Da Nhiều Ngăn",
        "top_title": "TÚI ĐA NGĂN SIÊU RỘNG",
        "top_subtitle": "SIÊU NHẸ • CHỐNG THẤM • 6 NGĂN TIỆN DỤNG",
        "top_price_badge": "CHỈ 109K",
        "price": "109.000đ",
        "draw_top_headline": True,
    },
    "phu_kien_pov_mui_ten_pastel": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_korean_bag_pouch.jpg",
        "product_name": "Túi Đựng Mỹ Phẩm & Phụ Kiện Đính Nơ Pastel Cute",
        "top_title": "TÚI MỸ PHẨM NƠ PASTEL",
        "top_subtitle": "BÔNG MỀM ĐÁNG YÊU • KHÓA KÉO ĐÔI MƯỢT MÀ",
        "top_price_badge": "CHỈ 45K",
        "price": "45.000đ",
        "draw_top_headline": True,
    },
    "thiet_bi_y_te_5metrics": {
        "base": "Template/Thumbnail_Templates/samples/ai_bases/ai_base_medical_tech_device.jpg",
        "product_name": "Máy Đo Nồng Độ Oxy & Nhịp Tim Điện Tử Màn Hình OLED",
        "top_title": "KIỂM TRA SỨC KHỎE 3 GIÂY!",
        "top_subtitle": "ĐO CHÍNH XÁC 99% • MÀN HÌNH OLED 4 CHIỀU",
        "top_price_badge": "CHỈ 115K",
        "price": "115.000đ",
        "draw_top_headline": True,
    },
}


def build_all_24_demo_thumbnails():
    rendered_count = 0
    for tpl in THUMBNAIL_TEMPLATES:
        tid = tpl["id"]
        cfg = DEMO_CONFIGS.get(tid) or DEMO_CONFIGS["gia_dung_3grid_pro"]
        base_rel = cfg["base"].replace("thumbnails/1736467481808438427_", "projects/1736467481808438427/thumbnails/1736467481808438427_")
        base_abs = os.path.join(WS_DIR, base_rel)
        if not os.path.isfile(base_abs):
            base_abs = os.path.join(WS_DIR, "projects/1736467481808438427/thumbnails/1736467481808438427_nv1_v1_thumb_raw2k.jpg")

        out_path = os.path.join(SAMPLES_DIR, f"{tid}.jpg")
        raw_backup = os.path.join(SAMPLES_DIR, f"{tid}_raw2k.jpg")
        shutil.copy2(base_abs, out_path)
        shutil.copy2(base_abs, raw_backup)

        pdir = os.path.join(WS_DIR, cfg["pdir"]) if cfg.get("pdir") else ""
        prod_imgs = []
        if pdir and os.path.isdir(os.path.join(pdir, "product_images")):
            prod_imgs = sorted(glob.glob(os.path.join(pdir, "product_images", "prod_*.jpg")))[:6]
        if not prod_imgs:
            prod_imgs = _create_3_detail_subcrops(base_abs, tid)

        meta = {
            "vkey": cfg.get("vkey", "v1"),
            "product_name": cfg.get("product_name", tpl["name"]),
            "product_info": tpl.get("recommended_for", ""),
            "price": cfg.get("price", "18.000đ"),
            "draw_top_headline": bool(cfg.get("draw_top_headline", False)),
            "top_title": cfg.get("top_title", ""),
            "top_subtitle": cfg.get("top_subtitle", ""),
            "top_price_badge": cfg.get("top_price_badge", ""),
        }
        ok = composite_template_product_insets(out_path, pdir, prod_imgs, tpl, meta)
        # Xoá file _raw2k.jpg tạm trong samples/ để thư mục gọn gàng
        if os.path.isfile(raw_backup):
            try:
                os.remove(raw_backup)
            except Exception:
                pass
        if ok:
            rendered_count += 1
            print(f"[OK] Rendered 1080x1920 Demo Thumbnail ({rendered_count}/24): {tid} -> {out_path}")

    export_templates_catalog_json()
    print(f"=== COMPLETED {rendered_count}/24 AI DEMO THUMBNAILS ===")


if __name__ == "__main__":
    build_all_24_demo_thumbnails()
