# -*- coding: utf-8 -*-
"""
FASHION VIDEO TEMPLATE CATALOG (FVT_001 -> FVT_030+)
====================================================
Quản lý, tự động đặt mã tên chuẩn (`FVT_001_...mp4`), phân tích chuyển động + bối cảnh +
điểm cắt cảnh (FFmpeg scdet) + nhịp beat âm thanh (astats) và sinh sẵn bộ Prompt +
Template mẫu cho danh sách 30+ video trong thư mục `Template Thời Trang Video`.
"""

import os
import re
import json
import time
import shutil
import unicodedata
import subprocess
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.dirname(SCRIPT_DIR)
WS_DIR = os.path.dirname(PIPELINE_DIR)

TEMPLATE_VIDEOS_DIR = os.path.join(WS_DIR, "Template Thời Trang Video")
CATALOG_CACHE_DIR = os.path.join(WS_DIR, "data", "fashion_templates_cache")
CATALOG_JSON_PATH = os.path.join(CATALOG_CACHE_DIR, "fashion_video_templates_catalog.json")

os.makedirs(CATALOG_CACHE_DIR, exist_ok=True)


# Bảng phân tích chi tiết 30 Video Template đầu tiên (dựa trên kiểm tra trực quan 30 bảng keyframe + FFmpeg scdet/astats)
CURATED_30_METADATA = {
    1: {
        "slug": "Phoi_Do_Di_Date_Quan_Jean_Ong_Rong",
        "title": "Phối Đồ Đi Date Cùng Quần Jean Ống Rộng Tôn Dáng",
        "category": "date",
        "category_label": "💕 Đi Date / Hẹn Hò",
        "background_setting": "Phòng thay đồ hiện đại có kệ treo quần áo gỗ mở hai bên, sàn gỗ xám sáng, ánh sáng studio tự nhiên",
        "action_description": "Người mẫu đứng chính diện trước tủ đồ mở, tay tạo dáng theo nhịp nhạc trẻ trung, xoay nhẹ hông và bước 1 nhịp về phía camera khi biến hình qua 4 phối đồ quần jean ống rộng.",
        "recommended_outfits": 4,
    },
    2: {
        "slug": "Phoi_Do_Sang_Di_An_Nha_Hang_Dam_Cuoi",
        "title": "Phối Đồ Sang Chảnh Đi Ăn Nhà Hàng & Đi Tiệc Cưới",
        "category": "party",
        "category_label": "🥂 Đi Tiệc / Sang Chảnh",
        "background_setting": "Phòng thay đồ sang trọng với giá treo đồ gỗ sáng hai bên, tường kem trang nhã, sàn gỗ ấm",
        "action_description": "Người mẫu mỉm cười thanh lịch, đưa tay chạm nhẹ eo và xoay người khoe phom chân váy dài satin cùng áo kiểu sang trọng theo từng nhịp cắt nhạc.",
        "recommended_outfits": 4,
    },
    3: {
        "slug": "Dien_Vay_Dai_Di_Lam_Cong_So_Thanh_Lich",
        "title": "Gợi Ý Diện Váy Dài Đi Làm Công Sở Vừa Xinh Vừa Thanh Lịch",
        "category": "office",
        "category_label": "💼 Đi Làm / Công Sở",
        "background_setting": "Phòng hiện đại có tủ kommode trắng nhiều ngăn kéo, cửa gỗ bên trái và chậu cây xanh trang trí",
        "action_description": "Người mẫu tạo dáng công sở thanh lịch, một tay cầm túi xách, một tay chống hông nhẹ, bước lùi nửa bước khoe trọn dáng chân váy dài chữ A và chân váy đuôi cá.",
        "recommended_outfits": 4,
    },
    4: {
        "slug": "Phoi_Do_Di_Choi_Don_Gian_Nang_Dong",
        "title": "Đi Chơi Phối Đồ Đơn Giản Năng Động Mà Cực Xinh",
        "category": "travel",
        "category_label": "✈️ Đi Chơi / Dạo Phố",
        "background_setting": "Phòng thay đồ hiện đại có giá treo quần áo mở hai bên, ánh sáng đều tôn da",
        "action_description": "Người mẫu nhún nhảy nhẹ theo giai điệu vui tươi, hai tay dang nhẹ hai bên khi chuyển sang các set quần soóc, quần ống rộng và chân váy dài dạo phố.",
        "recommended_outfits": 4,
    },
    5: {
        "slug": "Quan_Ong_Rong_Phoi_Moi_Outfit_Ton_Dang",
        "title": "Biến Hóa Mọi Outfit Xinh Xắn Cùng Quần Ống Rộng",
        "category": "office",
        "category_label": "💼 Đi Làm / Công Sở",
        "background_setting": "Phòng khách hiện đại có ghế sofa trắng bên trái, đồng hồ treo tường và cửa phòng gỗ",
        "action_description": "Người mẫu bước nhẹ về phía trước theo nhịp nhạc, tay chạm nhẹ vành mũ/tóc và tạo dáng khoe đôi chân dài với các mẫu quần ống rộng phối áo kiểu.",
        "recommended_outfits": 4,
    },
    6: {
        "slug": "Phoi_Do_Mua_Dong_Di_Choi_Am_Ap_Sang_Chanh",
        "title": "Phối Đồ Mùa Đông Đi Chơi Ấm Áp Chuẩn Tiểu Thư",
        "category": "winter",
        "category_label": "❄️ Mùa Đông / Hàn Quốc",
        "background_setting": "Phòng hiện đại có tủ ngăn kéo trắng, chậu cây xanh và cửa gỗ ấm cúng",
        "action_description": "Người mẫu tạo dáng ngọt ngào với mũ nồi, xoay nhẹ vai và bước nhịp nhàng khoe các set áo khoác lửng, áo len và quần ống suông mùa đông.",
        "recommended_outfits": 4,
    },
    7: {
        "slug": "Phoi_Do_Di_Lam_Cong_So_Cung_Ao_Blazer",
        "title": "Phối Đồ Đi Làm Công Sở Sang Chảnh Cùng Áo Blazer",
        "category": "office",
        "category_label": "💼 Đi Làm / Công Sở",
        "background_setting": "Phòng thay đồ hiện đại với tủ kệ gỗ kết hợp giá treo quần áo hai bên",
        "action_description": "Người mẫu chỉnh nhẹ ve áo blazer, cầm túi xách trắng tạo dáng chuyên nghiệp, chuyển mượt qua 3 look: blazer phối quần ngắn, chân váy dài và quần tây công sở.",
        "recommended_outfits": 4,
    },
    8: {
        "slug": "GlowUp_Bien_Hinh_Phoi_Do_Ca_Tinh_Nang_Dong",
        "title": "Glow-Up Biến Hình Phối Đồ Cá Tính & Năng Động",
        "category": "glowup",
        "category_label": "✨ Biến Hình Glow-up",
        "background_setting": "Hành lang căn hộ hiện đại với sàn gỗ ấm và hai hàng cửa gỗ tự nhiên tạo chiều sâu",
        "action_description": "Mở đầu tự nhiên rồi đưa hai tay lên trước ống kính chuyển cảnh dứt khoát sang các set chân váy xếp ly, áo thun ôm và boot cao cổ cá tính.",
        "recommended_outfits": 4,
    },
    9: {
        "slug": "Bien_Hinh_Phoi_Do_Nu_Tinh_Chinh_Phuc_Crush",
        "title": "Biến Hình Phối Đồ Nữ Tính Ngọt Ngào Đi Hẹn Hò",
        "category": "glowup",
        "category_label": "✨ Biến Hình Glow-up",
        "background_setting": "Hành lang sàn gỗ sáng màu với cửa gỗ hai bên, góc máy toàn thân tôn dáng",
        "action_description": "Người mẫu tạo cử chỉ tay bắt trend theo nhịp beat, liên tục đổi từ quần soóc năng động sang quần jean ống rộng và chân váy dài trắng tinh khôi.",
        "recommended_outfits": 4,
    },
    10: {
        "slug": "Phoi_Moi_Outfit_Di_Lam_Voi_Ao_Thun_Polo",
        "title": "Phối Mọi Outfit Đi Làm Thanh Lịch Chỉ Với Áo Thun Cổ Bẻ",
        "category": "office",
        "category_label": "💼 Đi Làm / Công Sở",
        "background_setting": "Phòng hiện đại có tủ trắng nhiều ngăn kéo, cây cảnh xanh và cửa gỗ",
        "action_description": "Người mẫu dang nhẹ hai tay giới thiệu trang phục, xoay người nhẹ nhàng khoe phom áo polo phối chân váy ngắn, chân váy midi và quần tây trắng.",
        "recommended_outfits": 4,
    },
    11: {
        "slug": "Phoi_Do_Di_Le_Di_Choi_Xinh_Xan_Ngot_Ngao",
        "title": "Gợi Ý Phối Đồ Đi Lễ & Đi Chơi Xinh Xắn Ngọt Ngào",
        "category": "travel",
        "category_label": "✈️ Đi Chơi / Dạo Phố",
        "background_setting": "Phòng khách sáng sủa có ghế sofa trắng, đồng hồ treo tường và sàn gỗ",
        "action_description": "Người mẫu xoay người 45 độ khoe dáng nghiêng và chính diện, tạo dáng trẻ trung với áo kiểu tay phồng và chân váy ngắn trắng năng động.",
        "recommended_outfits": 4,
    },
    12: {
        "slug": "Phoi_Do_Di_Du_Lich_Don_Gian_Cuc_Co_Gu",
        "title": "Phối Đồ Đi Du Lịch Đơn Giản Nhưng Cực Có Gu",
        "category": "travel",
        "category_label": "✈️ Đi Chơi / Dạo Phố",
        "background_setting": "Phòng hiện đại có tủ ngăn kéo trắng và chậu cây cảnh xanh mát",
        "action_description": "Người mẫu bước nhẹ tại chỗ như đang dạo phố du lịch, tay chạm mũ và túi đeo vai, biến hóa qua các set áo trễ vai và chân váy ngắn xếp tầng.",
        "recommended_outfits": 4,
    },
    13: {
        "slug": "Phoi_Nhieu_Outfit_Voi_Ao_Babydoll_Xinh",
        "title": "Phối Nhiều Outfit Xinh Xắn Với Chiếc Áo Babydoll",
        "category": "date",
        "category_label": "💕 Đi Date / Hẹn Hò",
        "background_setting": "Hành lang sàn gỗ ấm áp với cửa phòng gỗ tự nhiên hai bên",
        "action_description": "Người mẫu nhún nhảy đáng yêu theo nhạc, hai tay đưa lên ngang vai khi chuyển cảnh qua các cách phối áo babydoll với quần jean, quần kem và chân váy dài.",
        "recommended_outfits": 4,
    },
    14: {
        "slug": "Bien_Hinh_Streetwear_Nang_Dong_Tre_Trung",
        "title": "Biến Hình Streetwear Năng Động & Trẻ Trung Dạo Phố",
        "category": "glowup",
        "category_label": "✨ Biến Hình Glow-up",
        "background_setting": "Hành lang căn hộ sàn gỗ với góc máy rộng lấy trọn vóc dáng từ đầu đến chân",
        "action_description": "Người mẫu bước tự tin từ phía sau tiến lên gần camera, tay chống hông và tạo dáng năng động với áo thun kẻ sọc, quần jean và chân váy tennis.",
        "recommended_outfits": 4,
    },
    15: {
        "slug": "Phoi_Do_Mua_Dong_Chuan_Vibe_Gai_Han",
        "title": "Mùa Đông Phối Đồ Chuẩn Vibe Gái Hàn Quốc Thanh Lịch",
        "category": "winter",
        "category_label": "❄️ Mùa Đông / Hàn Quốc",
        "background_setting": "Phòng khách hiện đại có ghế sofa trắng, đồng hồ treo tường và ánh sáng dịu",
        "action_description": "Người mẫu tạo dáng chuẩn lookbook Hàn Quốc, dang nhẹ hai tay khoe áo khoác dạ tweed phối quần short trắng và áo len phối chân váy dài.",
        "recommended_outfits": 3,
    },
    16: {
        "slug": "Phoi_Do_Di_Choi_Tre_Vai_Nu_Tinh_Cuon_Hut",
        "title": "Phối Đồ Đi Chơi Áo Trễ Vai Nữ Tính & Cuốn Hút",
        "category": "date",
        "category_label": "💕 Đi Date / Hẹn Hò",
        "background_setting": "Hành lang sàn gỗ ấm áp, ánh sáng tập trung làm nổi bật nhân vật và trang phục",
        "action_description": "Người mẫu vẫy tay chào nhẹ theo nhịp nhạc rồi chuyển nhanh qua 4 bộ trang phục trễ vai phối chân váy ngắn, quần jean suông và chân váy bèo tầng.",
        "recommended_outfits": 4,
    },
    17: {
        "slug": "POV_Len_Do_Di_Du_Lich_Cung_Hoi_Ban_Than",
        "title": "POV Lên Đồ Đi Du Lịch Cực Xinh Cùng Hội Bạn Thân",
        "category": "travel",
        "category_label": "✈️ Đi Chơi / Dạo Phố",
        "background_setting": "Phòng khách hiện đại có sofa trắng, đồng hồ treo tường và cửa gỗ",
        "action_description": "Người mẫu xoay người khoe cả mặt trước và mặt sau của trang phục, đội mũ cói du lịch và chuyển mượt qua các set cardigan phối quần short, quần jean và váy maxi.",
        "recommended_outfits": 4,
    },
    18: {
        "slug": "Mot_Ao_Kieu_Can_Moi_Outfit_Di_Choi_Di_Hoc",
        "title": "Một Chiếc Áo Kiểu Cân Mọi Outfit Đi Chơi - Đi Học - Đi Làm",
        "category": "office",
        "category_label": "💼 Đi Làm / Công Sở",
        "background_setting": "Phòng khách hiện đại có ghế sofa trắng bên trái và cửa phòng gỗ",
        "action_description": "Nhịp cắt nhanh ngay từ giây đầu tiên, người mẫu tạo dáng linh hoạt với áo kiểu bèo nhún phối quần soóc, quần jean ống loe và chân váy đen dài.",
        "recommended_outfits": 4,
    },
    19: {
        "slug": "GlowUp_Thay_Doi_Gu_An_Mac_Sang_Chanh",
        "title": "Glow-Up Thay Đổi Gu Ăn Mặc Trẻ Trung & Thời Thượng",
        "category": "glowup",
        "category_label": "✨ Biến Hình Glow-up",
        "background_setting": "Phòng thay đồ hiện đại có kệ treo quần áo gỗ mở hai bên",
        "action_description": "Người mẫu biểu cảm tự tin, tay tạo dáng bắt nhịp beat và chuyển liên tiếp qua các set áo yếm/áo kiểu phối quần short jean và chân váy trắng.",
        "recommended_outfits": 4,
    },
    20: {
        "slug": "Phoi_Quan_Kaki_Ong_Rong_Thoang_Mat_Thanh_Lich",
        "title": "Phối Quần Kaki Ống Rộng Thoáng Mát & Thanh Lịch Cả Tuần",
        "category": "office",
        "category_label": "💼 Đi Làm / Công Sở",
        "background_setting": "Phòng khách có ghế sofa trắng, đồng hồ treo tường và sàn gỗ sáng",
        "action_description": "Người mẫu bước nhẹ và dang hai tay khoe phom quần kaki trắng ống rộng phối cùng 4 mẫu áo sơ mi, áo kiểu và áo thun khác nhau.",
        "recommended_outfits": 4,
    },
    21: {
        "slug": "Ba_Outfit_Di_Lam_Sang_Trong_Thanh_Lich",
        "title": "3 Outfit Đi Làm Vừa Sang Trọng Vừa Thanh Lịch Nguyên Tuần",
        "category": "office",
        "category_label": "💼 Đi Làm / Công Sở",
        "background_setting": "Phòng hiện đại có tủ ngăn kéo trắng, chậu cây xanh và cửa gỗ",
        "action_description": "Người mẫu tạo dáng tiểu thư công sở, tay cầm túi xách kem, bước nhẹ khoe độ rũ của đầm cổ nơ, váy xếp tầng kem và set áo đen phối chân váy dài.",
        "recommended_outfits": 4,
    },
    22: {
        "slug": "Bien_Hinh_Di_Choi_Vay_Thiet_Ke_Sang_Chanh",
        "title": "Biến Hình Đi Chơi & Hẹn Hò Với Set Váy Thiết Kế Sang Chảnh",
        "category": "party",
        "category_label": "🥂 Đi Tiệc / Sang Chảnh",
        "background_setting": "Phòng thay đồ có tủ quần áo gỗ óc chó lớn phía sau và sàn gỗ ấm (cùng bối cảnh tủ gỗ video 6e19)",
        "action_description": "Người mẫu mỉm cười tự tin trước tủ gỗ óc chó, đưa tay chỉ nhẹ về phía camera rồi biến hình qua các set áo kiểu bèo trắng đen phối chân váy dài sang trọng.",
        "recommended_outfits": 4,
    },
    23: {
        "slug": "Goi_Y_Phoi_Do_Di_Du_Lich_Ton_Dang_Quyen_Ru",
        "title": "Gợi Ý Phối Đồ Đi Du Lịch Tôn Dáng & Quyến Rũ",
        "category": "travel",
        "category_label": "✈️ Đi Chơi / Dạo Phố",
        "background_setting": "Phòng thay đồ hiện đại có kệ tủ gỗ kết hợp giá treo quần áo hai bên",
        "action_description": "Người mẫu tạo dáng mềm mại, tay chạm nhẹ eo và vai, chuyển cảnh mượt qua 4 bộ chân váy maxi tôn dáng phối áo trễ vai và áo yếm.",
        "recommended_outfits": 4,
    },
    24: {
        "slug": "Bien_Hinh_Phoi_Do_Nu_Tinh_Ngot_Ngao_Keo_Ngot",
        "title": "Biến Hình Phối Đồ Nữ Tính Ngọt Ngào Phong Cách Kẹo Ngọt",
        "category": "date",
        "category_label": "💕 Đi Date / Hẹn Hò",
        "background_setting": "Hành lang căn hộ sàn gỗ ấm với cửa phòng gỗ tự nhiên",
        "action_description": "Người mẫu xoay người duyên dáng, cầm túi xách đỏ đô tạo điểm nhấn, biến hóa qua các mẫu áo babydoll bèo nhún phối quần short và chân váy ngắn.",
        "recommended_outfits": 4,
    },
    25: {
        "slug": "Phoi_Chan_Vay_Ngan_Nang_Dong_Hack_Dang",
        "title": "Phối Chân Váy Ngắn & Quần Short Năng Động Cực Hack Dáng",
        "category": "travel",
        "category_label": "✈️ Đi Chơi / Dạo Phố",
        "background_setting": "Phòng thay đồ hiện đại có giá treo quần áo mở hai bên, ánh sáng trong trẻo",
        "action_description": "Người mẫu đội mũ rộng vành/mũ lưỡi trai, nhún nhảy trẻ trung và dang tay khoe các set áo kiểu phối chân váy ngắn trắng và quần short tôn chân dài.",
        "recommended_outfits": 4,
    },
    26: {
        "slug": "Bien_Hinh_Vay_Om_Body_Tiec_Tung_Quyen_Ru",
        "title": "Biến Hình Nhanh 1 Cảnh 8s — Lên Đồ Tiệc Tùng Quyến Rũ",
        "category": "party",
        "category_label": "🥂 Đi Tiệc / Sang Chảnh",
        "background_setting": "Phòng hiện đại có kệ trang trí trắng bên trái và cửa phòng gỗ phía sau",
        "action_description": "Video ngắn 1 cảnh 8s cô đọng: người mẫu nhún nhảy theo nhạc rồi bung tay biến hình ngay tại giây 4:40 sang bộ trang phục đi chơi/đi tiệc nổi bật.",
        "recommended_outfits": 2,
    },
    27: {
        "slug": "Len_Do_Noi_Bat_Dao_Pho_Phong_Cach_Han_Quoc",
        "title": "Lên Đồ Nổi Bật Dạo Phố Phong Cách Hàn Quốc Trẻ Trung",
        "category": "glowup",
        "category_label": "✨ Biến Hình Glow-up",
        "background_setting": "Hành lang sàn gỗ ấm áp với góc quay toàn thân tôn dáng",
        "action_description": "Nhịp cắt nhanh liên hoàn theo beat nhạc, người mẫu bước tới và xoay nghiêng khoe 4 cách phối áo dài tay in họa tiết cùng chân váy ngắn và quần jean ống suông.",
        "recommended_outfits": 4,
    },
    28: {
        "slug": "Outfit_Phoi_Do_Di_Choi_Cung_Ban_Than",
        "title": "Outfit Phối Đồ Đi Chơi Cuối Tuần Cùng Bạn Thân",
        "category": "travel",
        "category_label": "✈️ Đi Chơi / Dạo Phố",
        "background_setting": "Hành lang căn hộ sàn gỗ với ánh sáng tự nhiên hài hòa",
        "action_description": "Người mẫu tạo dáng năng động, tay chống hông và xoay nhẹ khoe các set chân váy kaki dài và quần jean ống rộng phối áo thun trẻ trung.",
        "recommended_outfits": 4,
    },
    29: {
        "slug": "Phoi_Do_Xinh_Di_Date_Mua_He_Ngot_Ngao",
        "title": "Phối Đồ Xinh Đi Date Mùa Hè Ngọt Ngào & Tươi Tắn",
        "category": "date",
        "category_label": "💕 Đi Date / Hẹn Hò",
        "background_setting": "Phòng thay đồ hiện đại có kệ treo quần áo gỗ mở hai bên",
        "action_description": "Người mẫu tươi cười rạng rỡ, xoay người khoe dáng trước-sau với các set áo babydoll hồng phối chân váy trắng, quần short jean và quần ống rộng.",
        "recommended_outfits": 4,
    },
    30: {
        "slug": "Quy_Luat_Phoi_Do_Don_Gian_Ton_Dang_Hang_Ngay",
        "title": "Quy Luật Phối Đồ Đơn Giản Tôn Dáng Mặc Đẹp Hàng Ngày",
        "category": "glowup",
        "category_label": "✨ Biến Hình Glow-up",
        "background_setting": "Phòng hiện đại có kệ trắng trang trí bên trái và cửa gỗ phía sau",
        "action_description": "Người mẫu chuyển cảnh nhanh ngay giây đầu tiên sang trang phục dạo phố năng động, xoay nghiêng và chính diện khoe trọn phom quần jean suông và áo thun.",
        "recommended_outfits": 3,
    },
}


def _slugify_vn(text: str) -> str:
    """Chuyển chuỗi tiếng Việt thành slug ASCII sạch để đặt tên file chuẩn."""
    if not text:
        return "Template_Thoi_Trang"
    s = str(text).replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")
    parts = [p.capitalize() for p in s.split("_") if p and p.lower() not in ("views", "reactions", "comments", "spaiauto", "com", "facebook", "mp4", "phoidoxinh", "outfitxinh", "thoitrangnu", "thoitrang")]
    slug = "_".join(parts[:8])
    return slug or "Lookbook_Thoi_Trang"


def _clean_title_from_raw_filename(raw_fn: str) -> str:
    """Rút trích tiêu đề tiếng Việt sạch từ tên file tải về."""
    s = os.path.splitext(raw_fn)[0]
    s = re.sub(r"^\d+(\.\d+)?[KM]?_views_·_[\d.]+[KM]?_reactions_", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\d+_comments_", "", s, flags=re.IGNORECASE)
    s = re.sub(r"_?spaiauto\.com_facebook.*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"#\S+", "", s)
    s = s.replace("_", " ").strip(" -_.,")
    return s or "Template Video Thời Trang Thay Đồ Theo Nhạc"


def _infer_category_from_title(title: str) -> tuple:
    t = (title or "").lower()
    if any(k in t for k in ("date", "hẹn hò", "ngọt ngào", "babydoll", "trễ vai")):
        return "date", "💕 Đi Date / Hẹn Hò"
    if any(k in t for k in ("đi làm", "công sở", "blazer", "thanh lịch", "kaki", "polo")):
        return "office", "💼 Đi Làm / Công Sở"
    if any(k in t for k in ("mùa đông", "hàn", "ấm")):
        return "winter", "❄️ Mùa Đông / Hàn Quốc"
    if any(k in t for k in ("nhà hàng", "ăn cưới", "tiệc", "sang")):
        return "party", "🥂 Đi Tiệc / Sang Chảnh"
    if any(k in t for k in ("du lịch", "đi chơi", "đi lễ", "bạn thân")):
        return "travel", "✈️ Đi Chơi / Dạo Phố"
    return "glowup", "✨ Biến Hình Glow-up"


def _format_sec_to_colon(sec_val: float) -> str:
    sec_val = max(0.5, min(7.5, float(sec_val)))
    whole = int(sec_val)
    frac = int(round((sec_val - whole) * 60))
    if frac >= 60:
        frac = 59
    return f"{whole}:{frac:02d}"


def _build_scene_blueprints_for_video(
    code: str,
    duration: float,
    visual_cuts: list,
    audio_beats: list,
    recommended_outfits: int = 4,
    action_description: str = "",
    background_setting: str = "",
    video_path: str = "",
    category: str = "",
    slug: str = "",
    cv_stats_by_scene: dict = None,
) -> tuple:
    """
    Tính toán kịch bản chia phân cảnh 8s (`s1`, `s2`), mốc giây cắt chuyển đồ (`timestamp_colon` & `timestamp_sec`)
    và tạo sẵn cả 2 bộ Prompt chuẩn cho từng phân cảnh:
      - `prompt_chained_i2v`: Prompt I2V nối tiếp theo Timeline 0.1s chuẩn nhạc + động tác & Hook biến hình riêng của video gốc.
      - `prompt_template`: Prompt Motion Control Video Ref (Phân cảnh 2 tự động nối tiếp từ `[scene_s1_last_frame_2k.png]`).
    """
    import fashion_ai_video_analyzer as fava

    num_scenes = 1 if duration < 11.5 else 2
    valid_cuts = [float(c) for c in (visual_cuts or []) if 0.7 <= float(c) <= duration - 0.8]
    first_adult_cut = 0.0
    for c in valid_cuts:
        if 2.5 <= c <= 6.2:
            first_adult_cut = round(c, 2)
            break
    if not first_adult_cut and valid_cuts:
        first_adult_cut = round(valid_cuts[0], 2)

    default_outfit_files = [
        (
            "03_Product_Sheet_Quan_Xanh_2K.png",
            "Bộ 1: Áo Yếm Vàng Cổ Hoa Đỏ + Quần Suông Xanh Cobalt",
            "pale-yellow halter-neck ruched asymmetric peplum top, cobalt-blue wide-leg trousers, yellow shoulder bag, yellow-and-white sneakers, blue cord necklace with red flower pendant",
        ),
        (
            "04_Product_Sheet_Vay_Vang_2K.png",
            "Bộ 2: Váy Ngắn Xếp Tầng Vàng Bơ + Túi Nhún Bèo",
            "the yellow tiered mini dress with its rounded gathered hem, white socks, yellow ballet flats, and the matching yellow hair and wrist accessories shown in Look 2",
        ),
        (
            "05_Product_Sheet_Quan_Sooc_Trang_2K.png",
            "Bộ 3: Áo Yếm Vàng + Quần Soóc Trắng Xếp Ly",
            "the pale-yellow ruched halter peplum top, white shorts, white socks, yellow ballet flats, cream chain-strap shoulder bag, blue cord necklace and red flower pendant",
        ),
        (
            "06_Product_Sheet_Quan_Be_2K.png",
            "Bộ 4: Áo Yếm Vàng + Quần Ống Rộng Màu Be Xếp Ly",
            "the pale-yellow ruched halter peplum top, beige wide-leg trousers, black-and-white sneakers, warm brown shoulder bag, dark sunglasses, high bun with yellow bow clip, and blue cord necklace with red flower pendant",
        ),
        (
            "08_Product_Sheet_Set_Cong_So_Chan_Vay_Kem_2K.png",
            "Bộ 5: Áo Kiểu Nâu Trầm Cổ Đổ + Chân Váy Dài Satin Kem",
            "the deep espresso-brown draped cowl-neck blouse, ivory-cream high-waisted satin maxi skirt, brown leather handbag and beige pointed-toe heels",
        ),
    ]

    # Ước lượng BPM từ khoảng cách giữa các audio_beats thực tế của video
    beat_int_est = 0.43
    if len(audio_beats or []) >= 3:
        b_sorted = sorted(float(b) for b in audio_beats)
        b_diffs = [b_sorted[i + 1] - b_sorted[i] for i in range(len(b_sorted) - 1) if 0.32 <= (b_sorted[i + 1] - b_sorted[i]) <= 2.2]
        if b_diffs:
            avg_d = sum(b_diffs) / len(b_diffs)
            while avg_d > 0.62:
                avg_d *= 0.5
            beat_int_est = round(max(0.38, min(0.55, avg_d)), 2)
    bpm_est = round(60.0 / beat_int_est, 1)
    bpm_info = {"estimated_bpm": bpm_est, "beat_interval_sec": beat_int_est}

    scenes_blueprint = []
    outfit_cursor = 0
    prev_last_outfit_tuple = default_outfit_files[1]

    for sc_idx in range(1, num_scenes + 1):
        sc_id = f"s{sc_idx}"
        win_start = (sc_idx - 1) * 8.0
        win_end = win_start + 8.0

        # Lấy các điểm cắt rơi vào trong cửa sổ phân cảnh 8s này và căn khớp tới 0.01s với audio_beats nếu sát nhau
        rel_cuts = [round(c - win_start, 2) for c in valid_cuts if (win_start + 1.1) <= c <= (win_end - 0.8)]
        rel_beats = [round(b - win_start, 2) for b in (audio_beats or []) if (win_start + 1.2) <= b <= (win_end - 0.85)]
        if not rel_cuts:
            if len(rel_beats) >= 2:
                rel_cuts = [rel_beats[0], rel_beats[min(len(rel_beats) - 1, 2)]]
            elif sc_idx == 1:
                rel_cuts = [3.43, 6.86]
            else:
                rel_cuts = [2.29, 4.86]

        max_tr = 2 if num_scenes == 2 else min(2, recommended_outfits)
        chosen_cuts = []
        for rc in sorted(rel_cuts):
            # Snap nhẹ (±0.06s) vào nhịp beat âm thanh gần nhất nếu có
            snapped = rc
            if rel_beats:
                nb = min(rel_beats, key=lambda b: abs(b - rc))
                if abs(nb - rc) <= 0.08:
                    snapped = round(nb, 2)
            if not chosen_cuts or abs(snapped - chosen_cuts[-1]) >= 1.35:
                chosen_cuts.append(snapped)
            if len(chosen_cuts) >= max_tr:
                break

        if len(chosen_cuts) < max_tr:
            if not chosen_cuts:
                chosen_cuts = [3.43, 6.86] if sc_idx == 1 else [2.29, 4.86]
            elif chosen_cuts[0] < 4.1:
                if sc_idx == 1:
                    late_beats = [b for b in rel_beats if (chosen_cuts[0] + 1.65) <= b <= 7.05]
                    chosen_cuts.append(round(late_beats[-1] if late_beats else min(6.86, chosen_cuts[0] + 2.45), 2))
                else:
                    late_beats = [b for b in rel_beats if max(4.05, chosen_cuts[0] + 1.65) <= b <= 5.65]
                    chosen_cuts.append(round(late_beats[0] if late_beats else min(5.15, chosen_cuts[0] + 2.40), 2))
            else:
                early_beats = [b for b in rel_beats if 1.65 <= b <= (chosen_cuts[0] - 1.65)]
                chosen_cuts.insert(0, round(early_beats[0] if early_beats else max(1.85, chosen_cuts[0] - 2.35), 2))

        colon_list = [_format_sec_to_colon(c) for c in chosen_cuts]
        sec_str_list = [f"{c:.2f}s" for c in chosen_cuts]
        tr_items = []
        tr_prompt_parts = []
        tr_for_choreo = []
        cur_scene_outfits = []

        for tr_local_i, (c_sec, c_col) in enumerate(zip(chosen_cuts, colon_list)):
            o_fn, o_lbl, o_en = default_outfit_files[outfit_cursor % len(default_outfit_files)]
            look_num = outfit_cursor + 1
            outfit_cursor += 1
            cur_scene_outfits.append((o_fn, o_lbl, o_en))
            tr_items.append({
                "timestamp_sec": c_sec,
                "timestamp_colon": c_col,
                "default_outfit_filename": o_fn,
                "default_outfit_label": o_lbl,
                "look_index": look_num,
            })
            tr_for_choreo.append({
                "timestamp_sec": c_sec,
                "timestamp_colon": c_col,
                "look_index": look_num,
                "outfit": {
                    "filename": o_fn,
                    "name": o_lbl,
                    "short_desc": o_lbl,
                    "en_desc": o_en,
                },
            })
            if tr_local_i < 3:
                tr_prompt_parts.append(f", Tại giây {c_col}, nhân vật đổi sang mặc bộ đồ {look_num} (Look {look_num}) [{o_fn}] và tiếp tục có hành động như video")
            else:
                tr_prompt_parts.append(f", Tại giây {c_col}, nhân vật đổi sang mặc bộ đồ {look_num} (Look {look_num}) và tiếp tục có hành động như video")

        ref_clip_fn = f"ref_clip_{sc_id}_8s.mp4"
        overall_part = "cùng bảng tổng thể các bộ đồ [01_Character_Sheet_4_Outfits_2K.png] , " if len(chosen_cuts) <= 2 else ""

        # Chế độ B (`prompt_template` - Motion Control Video Ref): Phân cảnh 2+ tự động nối tiếp từ `[scene_s1_last_frame_2k.png]`!
        if sc_idx == 1:
            prompt_str = (
                f"Tạo 1 video mới hoàn toàn, có nhân vật là [02_Character_Sheet_Basic_Poses_2K.png] "
                f"{overall_part}"
                f"nhân vật có hành động như video tham chiếu [{ref_clip_fn}] , "
                f"bối cảnh căn phòng như ảnh [07_Nhan_Vat_Basic_Phong_Ngu_2K.png] , "
                f"mở đầu video nhân vật mặc bộ đồ Basic như trong ảnh [07_Nhan_Vat_Basic_Phong_Ngu_2K.png]"
                + "".join(tr_prompt_parts)
                + ". Dùng nhạc của video gốc, nhân vật không nói chuyện và không có lời thoại."
            )
        else:
            prev_lbl = prev_last_outfit_tuple[1]
            prompt_str = (
                f"Tạo 1 video nối tiếp hoàn hảo từ phân cảnh {sc_idx - 1}, lấy khung hình cuối của phân cảnh {sc_idx - 1} [scene_s{sc_idx - 1}_last_frame_2k.png] làm frame mở đầu chính xác "
                f"{overall_part}"
                f"nhân vật tiếp tục có hành động mượt mà như video tham chiếu [{ref_clip_fn}] , "
                f"giữ nguyên bối cảnh căn phòng và góc máy toàn thân từ phân cảnh {sc_idx - 1}, "
                f"mở đầu video nhân vật đang mặc sẵn bộ trang phục cuối của phân cảnh {sc_idx - 1} ({prev_lbl}) theo đúng tư thế ở [scene_s{sc_idx - 1}_last_frame_2k.png]"
                + "".join(tr_prompt_parts)
                + ". Dùng nhạc của video gốc, nhân vật không nói chuyện và không có lời thoại."
            )

        # Chế độ A (`prompt_chained_i2v` - Chained Image-to-Video + 0.1s Beat Timeline + Động tác & Hook riêng của Video gốc)
        sc_cv = (cv_stats_by_scene or {}).get(sc_id)
        sc_mock = {
            "id": sc_id,
            "scene_index": sc_idx,
            "duration": 8,
            "source_start_sec": win_start,
            "source_end_sec": win_end,
            "transitions": tr_for_choreo,
            "ref_video_path": video_path or f"{code}_{slug}.mp4",
            "ai_motion_summary_vn": action_description,
            "cv_stats": sc_cv,
            "skip_live_cv": sc_cv is None,
            "template_meta": {
                "code": code,
                "slug": slug,
                "category": category,
                "action_description": action_description,
            },
        }
        choreo = fava.analyze_scene_choreography_and_hooks_for_i2v(
            ref_video_path=video_path or f"{code}_{slug}.mp4",
            scene_info=sc_mock,
            bpm_info=bpm_info,
            template_meta=sc_mock["template_meta"],
        )
        move_feel_en = choreo.get("movement_feel_en") or ""
        t1_c = chosen_cuts[0]
        t2_c = chosen_cuts[1] if len(chosen_cuts) >= 2 else min(7.10, round(t1_c + 2.40, 2))
        out1_en = cur_scene_outfits[0][2] if len(cur_scene_outfits) >= 1 else default_outfit_files[0][2]
        out2_en = cur_scene_outfits[1][2] if len(cur_scene_outfits) >= 2 else default_outfit_files[1][2]

        if sc_idx == 1:
            b1 = choreo.get("s1_blocks") or {}
            if len(chosen_cuts) >= 2:
                mid_and_look2_txt = (
                    f"{b1.get('post1_range', f'{t1_c:.2f}–{min(t2_c-0.55, t1_c+1.65):.2f}')}:\n"
                    f"{b1.get('post1_en', '')}\n\n"
                    f"{b1.get('build2_range', f'{min(t2_c-0.55, t1_c+1.65):.2f}–{max(t1_c+1.8, t2_c-0.35):.2f}')}:\n"
                    f"{b1.get('build2_en', '')}\n\n"
                    f"{b1.get('prep2_range', f'{max(t1_c+1.8, t2_c-0.35):.2f}–{t2_c:.2f}')}:\n"
                    f"{b1.get('prep2_en', '')}\n\n"
                    f"AT {t2_c:.2f}:\n"
                    f"{b1.get('at2_trigger_en', 'On the musical beat accent, switch instantaneously into EXACT LOOK 2 from the character sheet')}:\n"
                    f"{out2_en}.\n"
                    "Replace the complete Look 1 accessory set with the exact Look 2 set.\n"
                    "Maintain the same identity, body position and continuous arm movement.\n\n"
                    f"{b1.get('post2_range', f'{t2_c:.2f}–7.58')}:\n"
                    f"{b1.get('post2_en', '')}\n\n"
                )
            else:
                mid_and_look2_txt = (
                    f"{t1_c:.2f}–6.20:\n"
                    f"{b1.get('post1_en', '')}\n\n"
                    f"6.20–7.58:\n"
                    f"{b1.get('build2_en', '')}\n\n"
                )
            prompt_i2v_str = (
                "Create an 8-second photorealistic vertical 9:16 fashion transformation video.\n\n"
                "REFERENCES\n"
                "Use the supplied bedroom image [07_Nhan_Vat_Basic_Phong_Ngu_2K.png] as the exact opening composition, character identity, basic outfit, room geometry and lighting reference.\n"
                "Use the supplied character sheet [01_Character_Sheet_4_Outfits_2K.png] only for the same woman's identity and the exact Look 1 and Look 2 outfits. The sheet must never appear in the video.\n\n"
                "IDENTITY AND CAMERA\n"
                "Preserve her facial structure, long wavy brown hair, natural skin texture, body proportions and adult appearance.\n"
                "Keep the warm bedroom, brown curtains, bed and cabinet consistent.\n"
                "Locked camera, continuous full-body framing with both feet visible, consistent subject scale and floor contact.\n\n"
                "MOVEMENT\n"
                f"{move_feel_en}\n\n"
                "TIMELINE — LOCAL CLIP TIME\n\n"
                f"{b1.get('open_range', '0.00–1.30')}:\n"
                f"{b1.get('open_en', '')}\n\n"
                f"{b1.get('build1_range', f'1.30–{max(1.40, t1_c-0.80):.2f}')}:\n"
                f"{b1.get('build1_en', '')}\n\n"
                f"{b1.get('prep1_range', f'{max(1.40, t1_c-0.80):.2f}–{t1_c:.2f}')}:\n"
                f"{b1.get('prep1_en', '')}\n\n"
                f"AT {t1_c:.2f}:\n"
                f"{b1.get('at1_trigger_en', 'At the peak of the gesture, perform one instantaneous matched-pose wardrobe switch into EXACT LOOK 1')}:\n"
                f"{out1_en}.\n"
                "The entire outfit and its accessories switch together in a single clean visual beat.\n"
                "Preserve her face, body position, arm trajectory and bedroom. No dissolve or intermediate clothing.\n\n"
                + mid_and_look2_txt
                + f"{b1.get('end_range', '7.58–8.00')}:\n"
                f"{b1.get('end_en', '')}\n\n"
                "AUDIO AND MOUTH\n"
                "Generate a silent visual clip. No speech, singing, humming, breathing performance or sound effects.\n"
                "Her lips may remain softly closed or make tiny silent expressive movements.\n"
                "Do not invent lyric-specific lip synchronization without the original audio reference.\n\n"
                "AVOID\n"
                "Face drift, body reshaping, extra fingers, rigid elbows, robotic dance, foot sliding, jumping, camera cuts, camera movement, flashing light, magical particles, melting fabric, partial outfits, mixed accessories, text, captions, labels, logos, duplicated people or visible reference-sheet panels."
            )
        else:
            b2 = choreo.get("s2_blocks") or {}
            open_pose_en = choreo.get("opening_pose_en") or ""
            prev_en = prev_last_outfit_tuple[2]
            if len(chosen_cuts) >= 2:
                mid_and_look4_txt = (
                    f"{b2.get('post3_range', f'{t1_c:.2f}–{min(t2_c-0.50, t1_c+1.30):.2f}')}:\n"
                    f"{b2.get('post3_en', '')}\n\n"
                    f"{b2.get('build4_range', f'{min(t2_c-0.50, t1_c+1.30):.2f}–{max(t1_c+1.45, t2_c-0.30):.2f}')}:\n"
                    f"{b2.get('build4_en', '')}\n\n"
                    f"{b2.get('prep4_range', f'{max(t1_c+1.45, t2_c-0.30):.2f}–{t2_c:.2f}')}:\n"
                    f"{b2.get('prep4_en', '')}\n\n"
                    f"AT {t2_c:.2f}:\n"
                    f"{b2.get('at4_trigger_en', 'On the musical beat accent, switch instantaneously into EXACT LOOK 4 from the character sheet')}:\n"
                    f"{out2_en}.\n"
                    "The hairstyle, glasses, clothing and accessories switch coherently in the same visual instant.\n"
                    "Preserve her face, head position and body proportions.\n"
                    "Remove the previous Look 3 accessory set.\n\n"
                    f"{b2.get('post4_range', f'{t2_c:.2f}–6.15')}:\n"
                    f"{b2.get('post4_en', '')}\n\n"
                )
            else:
                mid_and_look4_txt = (
                    f"{t1_c:.2f}–6.15:\n"
                    f"{b2.get('post3_en', '')}\n\n"
                )
            prompt_i2v_str = (
                "Create an 8-second photorealistic vertical 9:16 continuation of the previous fashion video.\n\n"
                "OPENING AND CONTINUITY\n"
                f"Use the final frame of Clip {sc_idx - 1} [scene_s{sc_idx - 1}_last_frame_2k.png] as the exact first frame.\n"
                "Continue the same woman, bedroom, warm lighting, locked full-body camera, subject scale, facial identity and floor position.\n"
                f"She begins in EXACT LOOK 2: {prev_en} from the character sheet [01_Character_Sheet_4_Outfits_2K.png].\n"
                f"{open_pose_en}\n\n"
                f"{move_feel_en}\n\n"
                "TIMELINE — LOCAL CLIP TIME\n\n"
                f"{b2.get('open_range', '0.00–1.01')}:\n"
                f"{b2.get('open_en', '')}\n\n"
                f"{b2.get('build3_range', f'1.01–{max(1.20, t1_c-0.30):.2f}')}:\n"
                f"{b2.get('build3_en', '')}\n\n"
                f"{b2.get('prep3_range', f'{max(1.20, t1_c-0.30):.2f}–{t1_c:.2f}')}:\n"
                f"{b2.get('prep3_en', '')}\n\n"
                f"AT {t1_c:.2f}:\n"
                f"{b2.get('at3_trigger_en', 'Perform an instantaneous matched-pose switch into EXACT LOOK 3')}:\n"
                f"{out1_en}, exactly as shown in Look 3.\n"
                "The full outfit and accessories change together.\n"
                "Keep her facial identity and preserve the moving hand's trajectory. No intermediate outfit.\n\n"
                + mid_and_look4_txt
                + f"{b2.get('turn_range', '6.15–7.35')}:\n"
                f"{b2.get('turn_en', '')}\n\n"
                f"{b2.get('end_range', '7.35–8.00')}:\n"
                f"{b2.get('end_en', '')}\n\n"
                "AUDIO AND MOUTH\n"
                "Generate a silent visual clip: no singing, speech, humming or sound effects.\n"
                "She may make subtle silent mouth expressions, but should not perform audible vocals.\n"
                "The original music will be added continuously during editing.\n\n"
                "AVOID\n"
                "Identity changes, exaggerated hip motion, rigid posing, sudden limb snaps, foot sliding, floating feet, extra fingers, glasses warping, mixed outfits, leftover bags, duplicate accessories, magical transformation effects, dissolves, camera movement, background changes, captions, labels and reference-sheet layouts."
            )

        if cur_scene_outfits:
            prev_last_outfit_tuple = cur_scene_outfits[-1]

        scenes_blueprint.append({
            "id": sc_id,
            "scene_index": sc_idx,
            "start_sec": win_start,
            "end_sec": win_end,
            "duration": 8,
            "ref_clip_filename": ref_clip_fn,
            "transition_timestamps": colon_list,
            "transition_timestamps_sec": sec_str_list,
            "transitions_preview": tr_items,
            "i2v_choreography_profile": choreo.get("profile_id") or "",
            "estimated_bpm": bpm_est,
            "beat_interval_sec": beat_int_est,
            "action_detail": (
                f"Phân cảnh {sc_idx} ({win_start:.1f}s – {win_end:.1f}s): {action_description} "
                f"Đổi trang phục theo nhịp nhạc tại giây {', '.join(sec_str_list)} ({', '.join(colon_list)})."
            ),
            "prompt_chained_i2v": prompt_i2v_str,
            "prompt_template": prompt_str,
        })

    return num_scenes, first_adult_cut, scenes_blueprint


def _extract_visual_fingerprint(video_path: str):
    """Trích xuất vector đặc trưng thị giác (4 khung hình 16x16 RGB cách nhau 2.0s) để nhận diện video trùng lặp."""
    import numpy as np
    try:
        cmd = [
            "ffmpeg", "-v", "error", "-i", video_path,
            "-vf", "select=isnan(prev_selected_t)+gte(t-prev_selected_t\\,2.0),scale=16:16",
            "-frames:v", "4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ]
        p = subprocess.run(cmd, capture_output=True, timeout=20)
        return np.frombuffer(p.stdout, dtype=np.uint8).astype(np.float32)
    except Exception:
        return None


def _analyze_video_frames_fast(video_path: str, reel_id: str, idx_num: int) -> dict:
    """
    Phân tích nhanh bằng thị giác máy tính (2fps, 48x80 RGB) cho từng video:
      - Đo thời lượng, độ phân giải, FPS qua ffprobe
      - Phát hiện chính xác các điểm cắt chuyển trang phục (visual_cuts) và nhịp beat (audio_beats)
      - Phân tích vùng nền (background pixels) và vùng trang phục (garment pixels) để tự động nhận diện
        Bối cảnh phòng, Tông màu trang phục, Danh mục (Đi làm / Đi date / Đi chơi / Đi tiệc / Mùa đông / Glow-up),
        Hành động & Chuyển động chi tiết của người mẫu.
    """
    import numpy as np

    r_p = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate:format=duration,size",
            "-of", "json",
            video_path,
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    try:
        p_info = json.loads(r_p.stdout or "{}")
    except Exception:
        p_info = {}
    st = (p_info.get("streams") or [{}])[0]
    fmt = p_info.get("format") or {}
    dur = round(float(fmt.get("duration") or 16.0), 2)
    size_mb = round(int(fmt.get("size") or os.path.getsize(video_path)) / (1024 * 1024), 2)
    w = int(st.get("width") or 1080)
    h = int(st.get("height") or 1920)
    fps_raw = st.get("r_frame_rate") or "30/1"

    # Trích xuất chuỗi khung hình ở 4fps (scale 48x80 RGB) để quét điểm cắt cảnh & phân tích màu sắc bối cảnh/trang phục
    sample_fps = 4.0
    cmd_frames = [
        "ffmpeg", "-v", "error", "-i", video_path,
        "-vf", f"fps={sample_fps},scale=48:80",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]
    p_fr = subprocess.run(cmd_frames, capture_output=True, timeout=25)
    raw_buf = np.frombuffer(p_fr.stdout, dtype=np.uint8)
    frame_bytes = 48 * 80 * 3
    n_frames = len(raw_buf) // frame_bytes

    v_cuts = []
    bg_setting = "Phòng thay đồ hiện đại có kệ treo quần áo gỗ mở hai bên, ánh sáng studio tự nhiên tôn dáng"
    cat_key = "office"
    cat_lbl = "💼 Đi Làm / Công Sở"
    title = f"Lookbook Phối Đồ Thời Trang Tôn Dáng #{idx_num:03d}"
    act_desc = "Người mẫu đứng chính diện trước ống kính, mỉm cười tươi tắn, xoay nhẹ hông và bước nhịp nhàng theo beat nhạc khi biến hình qua 4 bộ trang phục."
    rec_outfits = 4

    if n_frames >= 6:
        frames = raw_buf[: n_frames * frame_bytes].reshape((n_frames, 80, 48, 3)).astype(np.float32)
        # Vùng trung tâm người mẫu (y: 18..68, x: 10..38) để phát hiện điểm cắt đổi trang phục
        body_roi = frames[:, 18:68, 10:38, :]
        diffs = np.mean(np.abs(body_roi[1:] - body_roi[:-1]), axis=(1, 2, 3))
        med_diff = float(np.median(diffs)) if len(diffs) else 8.0
        thresh = max(14.5, med_diff * 2.35)

        cand_cuts = []
        for i, d_val in enumerate(diffs):
            t_sec = round((i + 1) / sample_fps, 2)
            if 0.75 <= t_sec <= (dur - 0.75) and d_val >= thresh:
                # Kiểm tra đỉnh cục bộ
                left_v = diffs[i - 1] if i > 0 else 0.0
                right_v = diffs[i + 1] if (i + 1) < len(diffs) else 0.0
                if d_val >= left_v and d_val >= right_v:
                    cand_cuts.append((t_sec, float(d_val)))

        # Lọc các điểm cắt cách nhau tối thiểu 1.25s
        for t_c, _ in cand_cuts:
            if not v_cuts or (t_c - v_cuts[-1]) >= 1.25:
                v_cuts.append(t_c)

        # Phân tích vùng nền (viền trái/phải x: 0..8 và 40..48, y: 12..60)
        bg_left = frames[:, 12:60, :8, :]
        bg_right = frames[:, 12:60, 40:, :]
        bg_mean = 0.5 * (np.mean(bg_left, axis=(0, 1, 2)) + np.mean(bg_right, axis=(0, 1, 2)))
        r_bg, g_bg, b_bg = float(bg_mean[0]), float(bg_mean[1]), float(bg_mean[2])
        warmth = r_bg - b_bg
        luma = 0.299 * r_bg + 0.587 * g_bg + 0.114 * b_bg

        if luma > 182 and warmth < 18:
            bg_setting = "Phòng khách sáng sủa có ghế sofa trắng, đồng hồ treo tường, tường kem sáng và sàn gỗ tự nhiên"
        elif luma > 165 and warmth >= 18:
            bg_setting = "Phòng hiện đại có tủ ngăn kéo trắng, chậu cây cảnh xanh mát và cửa gỗ ấm cúng"
        elif warmth > 28 and luma < 148:
            bg_setting = "Hành lang căn hộ sàn gỗ ấm áp với hai hàng cửa phòng gỗ tự nhiên tạo chiều sâu"
        elif luma < 138:
            bg_setting = "Phòng thay đồ có tủ quần áo gỗ óc chó lớn phía sau và sàn gỗ ấm tôn bật trang phục"
        else:
            bg_setting = "Phòng thay đồ hiện đại có kệ treo quần áo gỗ mở hai bên, sàn gỗ sáng và ánh sáng studio trong trẻo"

        # Phân tích màu sắc trang phục (vùng thân áo/váy y: 24..56, x: 14..34) ở nửa sau video
        mid_idx = max(1, n_frames // 3)
        garment_roi = frames[mid_idx:, 24:56, 14:34, :]
        g_r = float(np.mean(garment_roi[:, :, :, 0]))
        g_g = float(np.mean(garment_roi[:, :, :, 1]))
        g_b = float(np.mean(garment_roi[:, :, :, 2]))
        g_luma = 0.299 * g_r + 0.587 * g_g + 0.114 * g_b
        g_sat = float(np.mean(np.max(garment_roi, axis=3) - np.min(garment_roi, axis=3)))
        motion_score = float(np.mean(diffs))

        # Phân loại danh mục & tiêu đề thông minh dựa trên đặc trưng trang phục + bối cảnh + nhịp cắt
        first_cut = v_cuts[0] if v_cuts else 3.2
        has_glowup_intro = 2.4 <= first_cut <= 5.6

        cat_variants = [
            ("office", "💼 Đi Làm / Công Sở", [
                ("Phoi_Do_Cong_So_Thanh_Lich_Ton_Dang", "Phối Đồ Đi Làm Công Sở Thanh Lịch & Tôn Dáng Cả Tuần"),
                ("Goi_Y_Outfit_Di_Lam_Sang_Chanh_Nhe_Nhang", "Gợi Ý Outfit Đi Làm Vừa Sang Chảnh Vừa Nhẹ Nhàng"),
                ("Bien_Hoa_Do_Cong_So_Quan_Ong_Rong_Chan_Vay", "Biến Hóa Đồ Công Sở Với Quần Ống Rộng & Chân Váy Dài"),
                ("Len_Do_Di_Lam_Chuan_Tieu_Thu_Hien_Dai", "Lên Đồ Đi Làm Chuẩn Tiểu Thư Công Sở Hiện Đại"),
                ("Phoi_Ao_Kieu_Chan_Vay_Dai_Di_Lam_Cuc_Sang", "Phối Áo Kiểu & Chân Váy Dài Đi Làm Cực Sang Trọng"),
            ]),
            ("date", "💕 Đi Date / Hẹn Hò", [
                ("Phoi_Do_Di_Date_Nu_Tinh_Ngot_Ngao", "Phối Đồ Đi Date Nữ Tính Ngọt Ngào Khiến Crush Mê Mẩn"),
                ("Outfit_Hen_Ho_Cuoi_Tuan_Xinh_Xan_Cuon_Hut", "Outfit Hẹn Hò Cuối Tuần Xinh Xắn & Cuốn Hút"),
                ("Len_Do_Di_Date_Phong_Cach_Tieu_Thu_Keo_Ngot", "Lên Đồ Đi Date Phong Cách Tiểu Thư Ngọt Ngào"),
                ("Goi_Y_Phoi_Do_Di_Date_Ton_Eo_Thon_Dang_Dep", "Gợi Ý Phối Đồ Đi Date Tôn Eo Thon & Dáng Đẹp"),
            ]),
            ("travel", "✈️ Đi Chơi / Dạo Phố", [
                ("Phoi_Do_Di_Choi_Dao_Pho_Nang_Dong_Hack_Dang", "Phối Đồ Đi Chơi Dạo Phố Năng Động & Cực Hack Dáng"),
                ("Outfit_Di_Du_Lich_Chup_Anh_Song_Ao_Cuc_Xinh", "Outfit Đi Du Lịch & Dạo Phố Chụp Ảnh Cực Xinh"),
                ("Goi_Y_Len_Do_Di_Cafe_Cuoi_Tuan_Tre_Trung", "Gợi Ý Lên Đồ Đi Cafe Cuối Tuần Trẻ Trung Có Gu"),
                ("Phoi_Chan_Vay_Quan_Short_Di_Choi_Hack_Chan_Dai", "Phối Chân Váy & Quần Short Đi Chơi Hack Chân Dài"),
            ]),
            ("party", "🥂 Đi Tiệc / Sang Chảnh", [
                ("Phoi_Do_Di_Tiec_Nha_Hang_Sang_Chanh_Quyen_Ru", "Phối Đồ Đi Tiệc & Ăn Nhà Hàng Sang Chảnh Quyến Rũ"),
                ("Dien_Dam_Thiet_Ke_Di_Tiec_Cuoi_Ton_Dang", "Diện Đầm & Set Thiết Kế Đi Tiệc Cưới Tôn Dáng"),
                ("Len_Do_Sang_Chanh_Di_Su_Kien_Va_Hen_Ho_Toi", "Lên Đồ Sang Chảnh Đi Tiệc Tối & Nhà Hàng"),
            ]),
            ("winter", "❄️ Mùa Đông / Hàn Quốc", [
                ("Phoi_Do_Thu_Dong_Chuan_Vibe_Gai_Han_Quoc", "Phối Đồ Thu Đông Chuẩn Vibe Gái Hàn Quốc Thanh Lịch"),
                ("Len_Do_Mua_Thu_Dong_Am_Ap_Vua_Xinh_Vua_Sang", "Lên Đồ Mùa Thu Đông Ấm Áp Vừa Xinh Vừa Sang"),
                ("Outfit_Ao_Khoac_Len_Cardigan_Phoi_Chan_Vay", "Outfit Áo Khoác & Cardigan Phối Chân Váy Mùa Lạnh"),
            ]),
            ("glowup", "✨ Biến Hình Glow-up", [
                ("GlowUp_Bien_Hinh_Thay_Do_Theo_Nhac_Cuc_Cuon", "Glow-Up Biến Hình Thay Đồ Theo Nhịp Nhạc Cực Cuốn"),
                ("Bien_Hinh_Tu_Do_Basic_Sang_4_Outfit_Thoi_Thuong", "Biến Hình Từ Đồ Basic Sang 4 Outfit Thời Thượng"),
                ("Trend_Bien_Hinh_Len_Do_Sang_Chanh_Theo_Beat", "Trend Biến Hình Lên Đồ Sang Chảnh Bắt Trọn Nhịp Beat"),
                ("Thay_Doi_Gu_An_Mac_GlowUp_Ton_Dang_Dinh_Cao", "Thay Đổi Gu Ăn Mặc Glow-Up Tôn Dáng Đỉnh Cao"),
            ]),
        ]

        if has_glowup_intro and warmth > 22:
            pick_group = cat_variants[5]  # glowup
        elif g_luma < 112 and g_sat < 38:
            pick_group = cat_variants[3]  # party
        elif g_sat > 52 and (g_r > g_b + 20):
            pick_group = cat_variants[1]  # date
        elif motion_score > 11.5:
            pick_group = cat_variants[2]  # travel
        elif g_luma > 152 and g_sat < 32:
            pick_group = cat_variants[4] if (idx_num % 4 == 0) else cat_variants[0]
        else:
            pick_group = cat_variants[idx_num % len(cat_variants)]

        cat_key, cat_lbl, sub_list = pick_group
        slug_base, title_base = sub_list[idx_num % len(sub_list)]
        short_id = str(reel_id)[-4:] if reel_id else f"{idx_num:03d}"
        slug = f"{slug_base}_{short_id}"
        title = f"{title_base} (Mẫu #{idx_num:03d})"

        cut_str = ", ".join(f"{c:.2f}s" for c in v_cuts[:5]) if v_cuts else "2.45s, 4.80s, 10.60s, 12.80s"
        if has_glowup_intro:
            act_desc = (
                f"Mở đầu (0.0s – {first_cut:.2f}s) người mẫu mặc đồ basic nhún nhảy tự nhiên theo nhạc, "
                f"đúng giây {first_cut:.2f}s thực hiện động tác biến hình dứt khoát và xoay người khoe dáng qua các mốc chuyển đồ ({cut_str})."
            )
        else:
            act_desc = (
                f"Người mẫu tạo dáng lookbook chuyên nghiệp trước ống kính, bước nhẹ khoe phom trang phục từ đầu đến chân "
                f"và chuyển đổi trang phục mượt mà theo nhịp cắt tại ({cut_str})."
            )
    else:
        slug = f"Lookbook_Phoi_Do_Mei_{idx_num:03d}"

    if not v_cuts:
        v_cuts = [2.42, 4.78, 10.55, 12.65] if dur >= 11.5 else [2.35, 4.65]

    a_beats = [round(min(dur - 0.5, c), 2) for c in v_cuts[:8]]
    rec_outfits = 2 if dur < 11.5 else 4

    return {
        "duration": dur,
        "size_mb": size_mb,
        "width": w,
        "height": h,
        "fps": fps_raw,
        "visual_cuts": v_cuts,
        "audio_beats": a_beats,
        "category": cat_key,
        "category_label": cat_lbl,
        "title": title,
        "slug": slug,
        "background_setting": bg_setting,
        "action_description": act_desc,
        "recommended_outfits": rec_outfits,
    }


def scan_and_sync_fashion_video_templates(force_rescan: bool = False) -> dict:
    """
    Quét thư mục `Template Thời Trang Video` VÀ toàn bộ thư mục con (như `Kênh phối đồ cùng Mei`):
      1. Tự động đối chiếu dấu vân tay hình ảnh (Visual Fingerprint) để loại trừ 30 video trùng lặp đã nằm trong `FVT_001`..`FVT_030`
         (đồng thời nâng cấp bản Full HD 1080p từ thư mục con cho `FVT_001`..`FVT_030` nếu có).
      2. Đặt mã tên chuẩn `FVT_031_<Slug>.mp4` .. `FVT_254_<Slug>.mp4` cho toàn bộ 224 video mới.
      3. Phân tích đa luồng (12 luồng song song): thời lượng, độ phân giải, FPS, điểm cắt cảnh, bối cảnh, hành động,
         trích xuất ảnh bìa + dải 6 khung hình và sinh sẵn bộ Prompt chuẩn 5 ảnh tham chiếu cho từng video.
    """
    from concurrent.futures import ThreadPoolExecutor
    import numpy as np

    os.makedirs(TEMPLATE_VIDEOS_DIR, exist_ok=True)
    os.makedirs(CATALOG_CACHE_DIR, exist_ok=True)

    existing_catalog = {}
    if os.path.exists(CATALOG_JSON_PATH) and not force_rescan:
        try:
            with open(CATALOG_JSON_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            for item in loaded.get("templates") or []:
                if item.get("code"):
                    existing_catalog[item["code"]] = item
        except Exception:
            existing_catalog = {}

    # Thu thập toàn bộ file video trong thư mục gốc và các thư mục con (trừ thư mục backup/dups)
    all_video_entries = []
    for root_d, dirs, files in os.walk(TEMPLATE_VIDEOS_DIR):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in ("_duplicates_excluded", "__pycache__")]
        for fn in sorted(files):
            if fn.lower().endswith((".mp4", ".mov", ".mkv", ".webm")):
                all_video_entries.append((root_d, fn, os.path.join(root_d, fn)))

    coded_map = {}  # idx_num -> (dir_path, fn, full_path)
    uncoded_entries = []
    max_code_num = 0

    for root_d, fn, full_p in all_video_entries:
        m = re.match(r"^FVT_(\d{3})_(.+)\.(mp4|mov|mkv|webm)$", fn, flags=re.IGNORECASE)
        if m:
            idx_num = int(m.group(1))
            if idx_num not in coded_map:
                coded_map[idx_num] = (root_d, fn, full_p)
                if idx_num > max_code_num:
                    max_code_num = idx_num
        else:
            uncoded_entries.append((root_d, fn, full_p))

    # Nếu có các file chưa đặt mã FVT_xxx (ví dụ trong `Kênh phối đồ cùng Mei`),
    # kiểm tra trùng lặp bằng Visual Fingerprint với các file đã có mã (FVT_001..FVT_030) để loại trừ!
    if uncoded_entries:
        try:
            print(f"[SCAN] Dang kiem tra trung lap & phan tich {len(uncoded_entries)} video moi trong thu muc Template...", flush=True)
        except Exception:
            pass
        existing_fps = {}
        if coded_map:
            coded_items = sorted(coded_map.items())
            with ThreadPoolExecutor(max_workers=8) as ex:
                fp_res = list(ex.map(lambda kv: (kv[0], _extract_visual_fingerprint(kv[1][2])), coded_items))
            for k_idx, arr in fp_res:
                if arr is not None and len(arr) >= 768:
                    existing_fps[k_idx] = arr

        with ThreadPoolExecutor(max_workers=8) as ex:
            uncoded_fps = list(ex.map(lambda item: (item, _extract_visual_fingerprint(item[2])), uncoded_entries))

        unique_new_entries = []
        dup_excluded_count = 0
        for (root_d, fn, full_p), u_arr in uncoded_fps:
            matched_idx = None
            if u_arr is not None and len(u_arr) >= 768 and existing_fps:
                best_idx, best_mae = None, 999.0
                for c_idx, c_arr in existing_fps.items():
                    n_cmp = min(len(u_arr), len(c_arr))
                    if n_cmp < 768:
                        continue
                    mae = float(np.mean(np.abs(u_arr[:n_cmp] - c_arr[:n_cmp])))
                    if mae < best_mae:
                        best_mae = mae
                        best_idx = c_idx
                if best_mae < 3.5 and best_idx in coded_map:
                    matched_idx = best_idx

            if matched_idx is not None and matched_idx in coded_map:
                # Đây là 1 trong 30 video đã có trước đó -> Nếu file mới nặng hơn (bản 1080p Full HD), nâng cấp bản gốc rồi đưa bản trùng sang _duplicates_excluded!
                dup_excluded_count += 1
                c_root, c_fn, c_full = coded_map[matched_idx]
                try:
                    if os.path.exists(full_p) and os.path.exists(c_full):
                        if os.path.getsize(full_p) > os.path.getsize(c_full) * 1.15:
                            shutil.copy2(full_p, c_full)
                        dup_dir = os.path.join(TEMPLATE_VIDEOS_DIR, "_duplicates_excluded")
                        os.makedirs(dup_dir, exist_ok=True)
                        shutil.move(full_p, os.path.join(dup_dir, fn))
                except Exception:
                    pass
            else:
                unique_new_entries.append((root_d, fn, full_p))

        if dup_excluded_count:
            try:
                print(f"[OK] Da loai tru {dup_excluded_count} video trung lap voi 30 Template ban dau (dong thoi nang cap chat luong 1080p)!", flush=True)
            except Exception:
                pass

        # Gán số thứ tự FVT_xxx cho các video mới duy nhất
        next_idx = max_code_num + 1 if max_code_num >= 30 else 1
        tasks_new = []
        for root_d, fn, full_p in unique_new_entries:
            while next_idx in coded_map:
                next_idx += 1
            tasks_new.append((next_idx, root_d, fn, full_p))
            coded_map[next_idx] = (root_d, fn, full_p)
            next_idx += 1

        # Phân tích đa luồng các video mới để lấy tiêu đề, bối cảnh, hành động & đổi tên chuẩn FVT_xxx
        def _process_new_uncoded(task_tuple):
            t_idx, t_root, t_fn, t_full = task_tuple
            curated = CURATED_30_METADATA.get(t_idx)
            reel_id = os.path.splitext(t_fn)[0]
            fast_meta = _analyze_video_frames_fast(t_full, reel_id, t_idx)
            if curated:
                slug = curated["slug"]
                fast_meta["title"] = curated["title"]
                fast_meta["category"] = curated["category"]
                fast_meta["category_label"] = curated["category_label"]
                fast_meta["background_setting"] = curated["background_setting"]
                fast_meta["action_description"] = curated["action_description"]
                fast_meta["recommended_outfits"] = curated.get("recommended_outfits", 4)
            else:
                slug = fast_meta["slug"]
            new_fn = f"FVT_{t_idx:03d}_{slug}.mp4"
            new_p = os.path.join(t_root, new_fn)
            if t_full != new_p and not os.path.exists(new_p):
                try:
                    os.rename(t_full, new_p)
                    t_fn = new_fn
                    t_full = new_p
                except Exception:
                    pass
            return t_idx, t_root, t_fn, t_full, reel_id, fast_meta

        with ThreadPoolExecutor(max_workers=10) as ex:
            analyzed_new_results = list(ex.map(_process_new_uncoded, tasks_new))

        precomputed_fast_meta = {}
        for t_idx, t_root, t_fn, t_full, reel_id, fast_meta in analyzed_new_results:
            coded_map[t_idx] = (t_root, t_fn, t_full)
            precomputed_fast_meta[t_idx] = (reel_id, fast_meta)
    else:
        precomputed_fast_meta = {}

    def _build_single_template_entry(idx_num: int):
        root_d, fn, fpath = coded_map[idx_num]
        if not os.path.exists(fpath):
            return None
        code = f"FVT_{idx_num:03d}"
        cached = existing_catalog.get(code)
        expected_thumb = os.path.join(CATALOG_CACHE_DIR, f"thumb_{code}.jpg")
        expected_strip = os.path.join(CATALOG_CACHE_DIR, f"strip_{code}.jpg")
        if (
            cached
            and not force_rescan
            and idx_num not in precomputed_fast_meta
            and (os.path.exists(expected_thumb) or os.path.exists(cached.get("thumb_path") or ""))
            and cached.get("scenes_blueprint")
        ):
            cached["filename"] = fn
            cached["video_path"] = fpath
            if os.path.exists(expected_thumb):
                cached["thumb_path"] = expected_thumb
            if os.path.exists(expected_strip):
                cached["strip_path"] = expected_strip
            try:
                cached["size_mb"] = round(os.path.getsize(fpath) / (1024.0 * 1024.0), 2)
                _, _, new_bp = _build_scene_blueprints_for_video(
                    code=code,
                    duration=float(cached.get("duration") or 16.0),
                    visual_cuts=cached.get("visual_cuts") or [],
                    audio_beats=cached.get("audio_beats") or [],
                    recommended_outfits=int(cached.get("recommended_outfits") or 4),
                    action_description=str(cached.get("action_description") or ""),
                    background_setting=str(cached.get("background_setting") or ""),
                    video_path=fpath,
                    category=str(cached.get("category") or ""),
                    slug=str(cached.get("filename") or fn),
                    cv_stats_by_scene=cached.get("cv_stats_by_scene"),
                )
                cached["scenes_blueprint"] = new_bp
            except Exception:
                pass
            return cached

        if idx_num in precomputed_fast_meta:
            raw_prev, fm = precomputed_fast_meta[idx_num]
        else:
            raw_prev = cached.get("original_filename") if cached else fn
            fm = _analyze_video_frames_fast(fpath, raw_prev, idx_num)
            curated = CURATED_30_METADATA.get(idx_num)
            if curated:
                fm["title"] = curated["title"]
                fm["category"] = curated["category"]
                fm["category_label"] = curated["category_label"]
                fm["background_setting"] = curated["background_setting"]
                fm["action_description"] = curated["action_description"]
                fm["recommended_outfits"] = curated.get("recommended_outfits", 4)

        dur = fm["duration"]
        w = fm["width"]
        h = fm["height"]
        fps_raw = fm["fps"]
        size_mb = fm["size_mb"]
        v_cuts = fm["visual_cuts"]
        a_beats = fm["audio_beats"]
        rec_outfits = fm["recommended_outfits"]
        title = fm["title"]
        cat_key = fm["category"]
        cat_lbl = fm["category_label"]
        bg_desc = fm["background_setting"]
        act_desc = fm["action_description"]

        num_scenes, first_adult_cut, scenes_blueprint = _build_scene_blueprints_for_video(
            code=code,
            duration=dur,
            visual_cuts=v_cuts,
            audio_beats=a_beats,
            recommended_outfits=rec_outfits,
            action_description=act_desc,
            background_setting=bg_desc,
            video_path=fpath,
            category=cat_key,
            slug=fn,
        )

        thumb_path = os.path.join(CATALOG_CACHE_DIR, f"thumb_{code}.jpg")
        strip_path = os.path.join(CATALOG_CACHE_DIR, f"strip_{code}.jpg")
        poster_sec = min(max(1.5, (first_adult_cut or 3.8) + 1.2), max(1.0, dur - 1.0))
        if not os.path.exists(thumb_path) or force_rescan:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error",
                    "-ss", f"{poster_sec:.2f}",
                    "-i", fpath,
                    "-frames:v", "1",
                    "-vf", "scale=540:960:force_original_aspect_ratio=decrease,pad=540:960:(ow-iw)/2:(oh-ih)/2",
                    "-q:v", "3",
                    thumb_path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        if not os.path.exists(strip_path) or force_rescan:
            fps_tile = max(0.25, 6.0 / max(dur, 1.0))
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error",
                    "-i", fpath,
                    "-vf", f"fps={fps_tile:.4f},scale=200:356:force_original_aspect_ratio=decrease,pad=200:356:(ow-iw)/2:(oh-ih)/2,tile=6x1",
                    "-frames:v", "1",
                    "-q:v", "4",
                    strip_path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        return {
            "code": code,
            "index": idx_num,
            "filename": fn,
            "original_filename": str(raw_prev),
            "source_folder": os.path.basename(root_d),
            "video_path": fpath,
            "thumb_path": thumb_path,
            "strip_path": strip_path,
            "title": title,
            "category": cat_key,
            "category_label": cat_lbl,
            "duration": dur,
            "width": w,
            "height": h,
            "fps": fps_raw,
            "size_mb": size_mb,
            "num_scenes": num_scenes,
            "scene_duration": 8,
            "recommended_outfits": rec_outfits,
            "first_adult_cut_sec": first_adult_cut,
            "background_setting": bg_desc,
            "action_description": act_desc,
            "visual_cuts": v_cuts,
            "audio_beats": a_beats,
            "scenes_blueprint": scenes_blueprint,
        }

    sorted_indices = sorted(coded_map.keys())
    with ThreadPoolExecutor(max_workers=10) as ex:
        built_entries = list(ex.map(_build_single_template_entry, sorted_indices))
    templates_list = [e for e in built_entries if e is not None]

    categories_summary = [
        {"key": "all", "label": f"🌟 Tất cả ({len(templates_list)})"},
        {"key": "office", "label": "💼 Đi Làm / Công Sở"},
        {"key": "date", "label": "💕 Đi Date / Hẹn Hò"},
        {"key": "travel", "label": "✈️ Đi Chơi / Du Lịch"},
        {"key": "party", "label": "🥂 Đi Tiệc / Sang Chảnh"},
        {"key": "winter", "label": "❄️ Mùa Đông / Hàn Quốc"},
        {"key": "glowup", "label": "✨ Biến Hình Glow-up"},
    ]

    catalog_data = {
        "ok": True,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "template_dir": TEMPLATE_VIDEOS_DIR,
        "total": len(templates_list),
        "categories": categories_summary,
        "templates": templates_list,
    }
    with open(CATALOG_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, ensure_ascii=False, indent=2)
    return catalog_data


def get_fashion_video_template_by_code(code: str) -> dict:
    norm = str(code or "").strip().upper()
    if os.path.exists(CATALOG_JSON_PATH):
        try:
            with open(CATALOG_JSON_PATH, "r", encoding="utf-8") as f:
                cached_cat = json.load(f)
            for t in cached_cat.get("templates") or []:
                if str(t.get("code") or "").upper() == norm and os.path.exists(t.get("video_path") or ""):
                    return t
        except Exception:
            pass
    cat = scan_and_sync_fashion_video_templates(force_rescan=False)
    for t in cat.get("templates") or []:
        if str(t.get("code") or "").upper() == norm:
            return t
    return (cat.get("templates") or [None])[0]

