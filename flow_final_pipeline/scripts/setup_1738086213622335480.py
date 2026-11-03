# -*- coding: utf-8 -*-
import os
import sys
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS_DIR = r"c:\Users\ADMIN\Desktop\Python\Veo 3 Tool\AutoVeo3Pro_v6\Auto_Veo_3_Pro\Grok\Skill Video Veo"
PID = "1738086213622335480"
PDIR = os.path.join(WS_DIR, "projects", PID)
os.makedirs(PDIR, exist_ok=True)

PNAME = "Cân Tiểu Ly Điện Tử Nhà Bếp INOX 304 5KG 10KG Độ Chính Xác Cao Chất Liệu Hợp Kim Thép Bền Bỉ - HGHOME"
PRIMARY_REFS = ["prod_3.jpg"]
SLIDE_OVERLAYS = ["prod_3.jpg", "prod_7.jpg", "prod_12.jpg", "prod_11.jpg", "prod_14.jpg"]

NV1_CHAR_ID = "208606a7-a345-48b2-af32-9fd3c37d0c9a"
NV1_PROJ_ID = "932bc2a1-07ea-4199-b147-80ab0018d41c"
NV1_VOICE_ID = "27f51973-e290-4a38-bd7a-9d6fbe81b2f6"
NV1_VOICE_NAME = "Nhân Vật 1 Affi Giọng Bắc"

NV2_CHAR_ID = "562be2fe-3c7c-4fc9-b3f2-c9b87743ec30"
NV2_PROJ_ID = "bf4979d1-548a-44bd-a265-3927bba76dc1"
NV2_VOICE_ID = "75a3d14a-ed10-4bdc-862c-44adb02a5562"
NV2_VOICE_NAME = "Nhân Vật 2 Affi Giọng Bắc Năng Lượng"

ACTION_BY_SCENE_IDX = {
    1: "The woman looks directly at the camera with a confident, energetic expression, naturally speaking while holding the exact product from the reference image steady at waist level, tilting it slightly toward the camera to showcase it, then keeping the presenting pose at the end.",
    2: "The woman looks directly at the camera with a warm, enthusiastic expression, naturally speaking while holding the exact product from the reference image steady at waist level and gesturing lightly toward the bottom-left shopping cart, then keeping the presenting pose at the end.",
    3: "The woman looks directly at the camera with a bright, friendly smile, naturally speaking while holding the exact product from the reference image steady at waist level to showcase it clearly, then keeping the presenting pose at the end.",
}


def make_video_prompt(scene_idx: int, timed_lines: list) -> str:
    action_str = ACTION_BY_SCENE_IDX[scene_idx]
    voice_block = "\n".join(timed_lines)
    return (
        "A 10-second vertical 9:16 video starting directly from the provided reference image, "
        "one continuous medium shot, front-facing camera. Keep the character, the exact product in her hands, "
        "the items on the table, and the background 100% unchanged from the reference image — "
        "do not alter, redesign, or replace the product's shape, color, pattern, or logo.\n\n"
        f"ACTION: {action_str}\n\n"
        "VOICE — read the dialogue in 3 timed segments exactly as marked. Keep a steady, even pace so each segment "
        "fills its time window. Finish the last word exactly at 10.0 seconds. Read each word exactly once — "
        "no repetition, no looping, no added words, then stay silent:\n"
        f"{voice_block}\n\n"
        "No background music, no watermark.\n"
        "Negative: changed product, altered product design, repeating voice, looping dialogue, second voice pass, rushed reading, changed face"
    )


VARIANTS = {
    "v1": {
        "char_v": "nv1_v1",
        "character": "nv1",
        "hook_title": "NV1 - Kịch bản 1: Trợ Giá Sàn",
        "style": "Xưởng Dây Chuyền Lắp Ráp Cân Điện Tử",
        "character_id": NV1_CHAR_ID,
        "project_id": NV1_PROJ_ID,
        "voice_id": NV1_VOICE_ID,
        "voice_name": NV1_VOICE_NAME,
        "ref_image": "v1-refimg.jpg",
        "ref_image_prompt": (
            "Photorealistic vertical 9:16 medium-wide standing photo (framed from head to hips, camera at 2 meters distance, NOT a close-up): "
            "the exact same woman from the character reference (shoulder-length layered black hair, black-framed glasses, identical face), "
            "wearing a polite professional dark navy blazer over a crisp light blue collared shirt and black trousers, standing behind a display worktable "
            "in a reputable modern digital scale assembly and calibration factory floor with assembly lines, neatly stacked boxes, and factory technicians in blue uniforms softly blurred in the background. "
            "She looks directly at the camera with a warm, friendly, confident smile while holding and presenting the exact compact digital kitchen scale from the product reference image in her hands at waist level facing the camera "
            "(true-to-life compact 18x14cm hand-held scale relative to her hands and body, NOT oversized), with neat retail packaging boxes on the worktable beside her. "
            "Keep the product 100% identical as shown in the product reference image (keep all original product details, prints, logos, and true size intact, do not redesign or alter the product in any way), and keep her face identical."
        ),
        "scenes_spec": [
            {
                "id": "v1_s1",
                "file": "v1_s1.mp4",
                "timed": [
                    '[0.0-3.7s] "Cái này là cho các bác này. Sàn người ta cho chứ không phải bán nữa rồi."',
                    '[3.7-7.8s] "Siêu phẩm cân tiểu ly điện tử nhà bếp mặt inox ba lẻ tư đang trợ giá cực rẻ,"',
                    '[7.8-10.0s] "các bác bấm giỏ hàng xem giá giúp em nhé."',
                ],
                "phrases": [
                    ["CÁI NÀY LÀ CHO CÁC BÁC NÀY", 7],
                    ["SÀN NGƯỜI TA CHO CHỨ", 5],
                    ["KHÔNG PHẢI BÁN NỮA RỒI", 5],
                    ["SIÊU PHẨM CÂN TIỂU LY", 5],
                    ["ĐIỆN TỬ NHÀ BẾP MẶT INOX", 6],
                    ["BA LẺ TƯ ĐANG TRỢ GIÁ RẺ", 7],
                    ["CÁC BÁC BẤM GIỎ HÀNG", 5],
                    ["XEM GIÁ GIÚP EM NHÉ", 5],
                ],
            },
            {
                "id": "v1_s2",
                "file": "v1_s2.mp4",
                "timed": [
                    '[0.0-3.6s] "Giá không phải 200, không phải 150, 70K cũng không luôn."',
                    '[3.6-6.0s] "Mỗi tài khoản các bác sẽ thấy một giá khác nhau."',
                    '[6.0-10.0s] "Bấm giỏ hàng góc trái nha, nếu thấy giá dưới 70K thì săn liền giúp em ạ."',
                ],
                "phrases": [
                    ["GIÁ KHÔNG PHẢI 200", 4],
                    ["KHÔNG PHẢI 150", 3],
                    ["70K CŨNG KHÔNG LUÔN", 4],
                    ["MỖI TÀI KHOẢN CÁC BÁC", 5],
                    ["SẼ THẤY MỘT GIÁ KHÁC NHAU", 6],
                    ["BẤM GIỎ HÀNG GÓC TRÁI NHA", 6],
                    ["NẾU THẤY GIÁ DƯỚI 70K", 5],
                    ["THÌ SĂN LIỀN GIÚP EM Ạ", 6],
                ],
            },
            {
                "id": "v1_s3",
                "file": "v1_s3.mp4",
                "timed": [
                    '[0.0-3.5s] "Đây là ưu đãi chớp nhoáng hôm nay thôi, hết là về giá gốc đó."',
                    '[3.5-7.2s] "Cân tối đa mười ký chính xác từng gam, có tính năng trừ bì và tặng kèm pin,"',
                    '[7.2-10.0s] "làm bánh nấu ăn cực chuẩn, chốt ngay các bác ơi."',
                ],
                "phrases": [
                    ["ĐÂY LÀ ƯU ĐÃI CHỚP NHOÁNG", 6],
                    ["HẾT LÀ VỀ GIÁ GỐC ĐÓ", 6],
                    ["CÂN TỐI ĐA MƯỜI KÝ", 5],
                    ["CHÍNH XÁC TỪNG GAM", 4],
                    ["CÓ TÍNH NĂNG TRỪ BÌ", 5],
                    ["VÀ TẶNG KÈM PIN LUÔN", 5],
                    ["LÀM BÁNH NẤU ĂN CỰC CHUẨN", 6],
                    ["CHỐT NGAY CÁC BÁC ƠI", 5],
                ],
            },
        ],
    },
    "v2": {
        "char_v": "nv2_v1",
        "character": "nv2",
        "hook_title": "NV2 - Kịch bản 1: Giá Sốc Tận Xưởng",
        "style": "Phòng Kiểm Định Chất Lượng QC",
        "character_id": NV2_CHAR_ID,
        "project_id": NV2_PROJ_ID,
        "voice_id": NV2_VOICE_ID,
        "voice_name": NV2_VOICE_NAME,
        "ref_image": "v2-refimg.jpg",
        "ref_image_prompt": (
            "Photorealistic vertical 9:16 medium-wide standing photo (framed from head to hips, camera at 2 meters distance, NOT a close-up): "
            "the exact same woman from the character reference (long wavy dark-brown hair in a high ponytail with colourful pastel hair clips, identical face, no glasses), "
            "wearing a polite professional cream-white tailored blazer over a dark navy blouse and black trousers, standing behind a clean white inspection counter "
            "in a bright, modern glass-walled Quality Control (QC) testing and inspection laboratory with precision inspection lamps, sample testing shelves, quality pass certificates, and QC specialists in white lab coats softly blurred in the background. "
            "She looks directly at the camera with a warm, friendly, confident smile while holding and presenting the exact compact digital kitchen scale from the product reference image in her hands at waist level facing the camera "
            "(true-to-life compact 18x14cm hand-held scale relative to her hands and body, NOT oversized), with neat retail packaging boxes on the worktable beside her. "
            "Keep the product 100% identical as shown in the product reference image (keep all original product details, prints, logos, and true size intact, do not redesign or alter the product in any way), and keep her face identical."
        ),
        "scenes_spec": [
            {
                "id": "v2_s1",
                "file": "v2_s1.mp4",
                "timed": [
                    '[0.0-4.0s] "69K cho siêu phẩm cân tiểu ly điện tử inox ba lẻ tư này các bác ơi."',
                    '[4.0-7.8s] "Ở đâu bán giá này em cũng bái phục, tận xưởng không thể rẻ vậy."',
                    '[7.8-10.0s] "Hôm nay kênh em được trợ giá rất rẻ luôn."',
                ],
                "phrases": [
                    ["69K CHO SIÊU PHẨM CÂN", 5],
                    ["TIỂU LY ĐIỆN TỬ INOX NÀY", 6],
                    ["Ở ĐÂU BÁN GIÁ NÀY", 5],
                    ["EM CŨNG BÁI PHỤC LUÔN", 5],
                    ["TẬN XƯỞNG KHÔNG THỂ RẺ VẬY", 6],
                    ["HÔM NAY KÊNH EM ĐƯỢC", 5],
                    ["TRỢ GIÁ RẤT RẺ LUÔN", 5],
                ],
            },
            {
                "id": "v2_s2",
                "file": "v2_s2.mp4",
                "timed": [
                    '[0.0-3.7s] "Giá không phải 200, không phải 150, 70K cũng không luôn."',
                    '[3.7-5.7s] "Mà mỗi tài khoản một giá khác nhau nha."',
                    '[5.7-10.0s] "Các bác bấm giỏ hàng góc trái, thấy dưới 70K thì săn liền giúp em ạ."',
                ],
                "phrases": [
                    ["GIÁ KHÔNG PHẢI 200", 4],
                    ["KHÔNG PHẢI 150", 3],
                    ["70K CŨNG KHÔNG LUÔN", 4],
                    ["MÀ MỖI TÀI KHOẢN", 4],
                    ["MỘT GIÁ KHÁC NHAU NHA", 5],
                    ["BẤM GIỎ HÀNG GÓC TRÁI", 5],
                    ["THẤY DƯỚI 70K THÌ SĂN LIỀN", 6],
                    ["GIÚP EM NGAY NHA CÁC BÁC", 6],
                ],
            },
            {
                "id": "v2_s3",
                "file": "v2_s3.mp4",
                "timed": [
                    '[0.0-3.8s] "Mặt cân hợp kim thép inox bền đẹp, cân mười ký chuẩn từng gam có trừ bì."',
                    '[3.8-6.8s] "Có sẵn pin đi kèm tiện lợi, các bác chốt ngay giúp em."',
                    '[6.8-10.0s] "Ưu đãi chớp nhoáng hôm nay, hết là về giá gốc đó ạ."',
                ],
                "phrases": [
                    ["MẶT CÂN INOX BỀN ĐẸP", 5],
                    ["CÂN MƯỜI KÝ CHUẨN TỪNG GAM", 6],
                    ["CÓ TÍNH NĂNG TRỪ BÌ", 5],
                    ["CÓ SẴN PIN ĐI KÈM TIỆN LỢI", 6],
                    ["CÁC BÁC CHỐT NGAY GIÚP EM", 6],
                    ["ƯU ĐÃI CHỚP NHOÁNG HÔM NAY", 6],
                    ["HẾT LÀ VỀ GIÁ GỐC ĐÓ Ạ", 7],
                ],
            },
        ],
    },
    "v3": {
        "char_v": "nv1_v2",
        "character": "nv1",
        "hook_title": "NV1 - Kịch bản 2: Báo Động Giá Xưởng",
        "style": "Tổng Kho Pallet Xuất Xưởng Gia Dụng",
        "character_id": NV1_CHAR_ID,
        "project_id": NV1_PROJ_ID,
        "voice_id": NV1_VOICE_ID,
        "voice_name": NV1_VOICE_NAME,
        "ref_image": "v3-refimg.jpg",
        "ref_image_prompt": (
            "Photorealistic vertical 9:16 medium-wide standing photo (framed from head to hips, camera at 2 meters distance, NOT a close-up): "
            "the exact same woman from the character reference (shoulder-length layered black hair, black-framed glasses, identical face), "
            "wearing a polite charcoal-grey tailored waistcoat vest over a crisp white collared office shirt and dark trousers, standing behind a packing table "
            "in a spacious high-bay factory dispatch and logistics warehouse with towering orange-and-blue steel pallet racks stacked high with brown export shipping cartons, yellow warehouse aisle markings, and logistics staff softly blurred in the background. "
            "She looks directly at the camera with a warm, friendly, confident smile while holding and presenting the exact compact digital kitchen scale from the product reference image in her hands at waist level facing the camera "
            "(true-to-life compact 18x14cm hand-held scale relative to her hands and body, NOT oversized), with neat retail packaging boxes on the worktable beside her. "
            "Keep the product 100% identical as shown in the product reference image (keep all original product details, prints, logos, and true size intact, do not redesign or alter the product in any way), and keep her face identical."
        ),
        "scenes_spec": [
            {
                "id": "v3_s1",
                "file": "v3_s1.mp4",
                "timed": [
                    '[0.0-3.5s] "Các bác khoan hãy lướt qua video này kẻo tiếc hùi hụi luôn nha."',
                    '[3.5-7.4s] "Tại tổng kho hôm nay mẫu cân tiểu ly điện tử inox đang xả trợ giá cực sâu,"',
                    '[7.4-10.0s] "bấm ngay vào giỏ hàng kiểm tra giá giúp em nhé."',
                ],
                "phrases": [
                    ["KHOAN HÃY LƯỚT QUA VIDEO", 5],
                    ["KẺO TIẾC HÙI HỤI LUÔN NHA", 6],
                    ["TẠI TỔNG KHO HÔM NAY", 5],
                    ["MẪU CÂN TIỂU LY ĐIỆN TỬ", 6],
                    ["ĐANG XẢ TRỢ GIÁ CỰC SÂU", 6],
                    ["BẤM NGAY VÀO GIỎ HÀNG", 5],
                    ["KIỂM TRA GIÁ GIÚP EM NHÉ", 6],
                ],
            },
            {
                "id": "v3_s2",
                "file": "v3_s2.mp4",
                "timed": [
                    '[0.0-3.6s] "Giá không phải 200, không phải 150, 70K cũng không luôn."',
                    '[3.6-6.2s] "Tùy từng tài khoản mà sàn áp mức giảm khác nhau."',
                    '[6.2-10.0s] "Các bác mở giỏ hàng góc trái, thấy dưới 70K là chốt đơn liền tay nha."',
                ],
                "phrases": [
                    ["GIÁ KHÔNG PHẢI 200", 4],
                    ["KHÔNG PHẢI 150", 3],
                    ["70K CŨNG KHÔNG LUÔN", 4],
                    ["TÙY TỪNG TÀI KHOẢN", 4],
                    ["SÀN ÁP MỨC GIẢM KHÁC NHAU", 6],
                    ["MỞ GIỎ HÀNG GÓC TRÁI", 5],
                    ["THẤY DƯỚI 70K LÀ CHỐT", 5],
                    ["ĐƠN LIỀN TAY NHA CÁC BÁC", 6],
                ],
            },
            {
                "id": "v3_s3",
                "file": "v3_s3.mp4",
                "timed": [
                    '[0.0-3.6s] "Cân chính xác đến một gam, có phím trừ bì cân đồ nhỏ cực chuẩn xác."',
                    '[3.6-7.0s] "Hàng xuất trực tiếp từ nhà máy kèm sẵn pin, kiểm tra kỹ từng chiếc,"',
                    '[7.0-10.0s] "số lượng ưu đãi có hạn nên các bác đặt sớm nhé."',
                ],
                "phrases": [
                    ["CÂN CHÍNH XÁC ĐẾN MỘT GAM", 6],
                    ["CÓ PHÍM TRỪ BÌ CỰC CHUẨN", 6],
                    ["HÀNG XUẤT TỪ NHÀ MÁY", 5],
                    ["KÈM SẴN PIN TIỆN LỢI", 5],
                    ["KIỂM TRA KỸ TỪNG CHIẾC", 5],
                    ["SỐ LƯỢNG ƯU ĐÃI CÓ HẠN", 6],
                    ["CÁC BÁC ĐẶT SỚM NHÉ", 5],
                ],
            },
        ],
    },
    "v4": {
        "char_v": "nv2_v2",
        "character": "nv2",
        "hook_title": "NV2 - Kịch bản 2: Không Qua Trung Gian",
        "style": "Showroom Trưng Bày Thiết Bị Nhà Bếp",
        "character_id": NV2_CHAR_ID,
        "project_id": NV2_PROJ_ID,
        "voice_id": NV2_VOICE_ID,
        "voice_name": NV2_VOICE_NAME,
        "ref_image": "v4-refimg.jpg",
        "ref_image_prompt": (
            "Photorealistic vertical 9:16 medium-wide standing photo (framed from head to hips, camera at 2 meters distance, NOT a close-up): "
            "the exact same woman from the character reference (long wavy dark-brown hair in a high ponytail with colourful pastel hair clips, identical face, no glasses), "
            "wearing a polite elegant black tailored blazer over a silk ivory blouse and dark trousers, standing behind a wooden display counter "
            "in a warm-lit official brand showroom and sample display gallery with illuminated wooden shelves displaying kitchen appliances, framed ISO quality awards, and warm spotlighting softly blurred in the background. "
            "She looks directly at the camera with a warm, friendly, confident smile while holding and presenting the exact compact digital kitchen scale from the product reference image in her hands at waist level facing the camera "
            "(true-to-life compact 18x14cm hand-held scale relative to her hands and body, NOT oversized), with neat retail packaging boxes on the counter beside her. "
            "Keep the product 100% identical as shown in the product reference image (keep all original product details, prints, logos, and true size intact, do not redesign or alter the product in any way), and keep her face identical."
        ),
        "scenes_spec": [
            {
                "id": "v4_s1",
                "file": "v4_s1.mp4",
                "timed": [
                    '[0.0-3.5s] "Đừng mua ở ngoài làm gì cho đắt đỏ tốn kém các bác ơi."',
                    '[3.5-7.4s] "Lấy trực tiếp tại xưởng mẫu cân tiểu ly điện tử nhà bếp hôm nay rẻ bất ngờ,"',
                    '[7.4-10.0s] "các bác mở giỏ hàng góc trái xem thử ngay nhé."',
                ],
                "phrases": [
                    ["ĐỪNG MUA Ở NGOÀI LÀM GÌ", 6],
                    ["CHO ĐẮT ĐỎ TỐN KÉM", 5],
                    ["LẤY TRỰC TIẾP TẠI XƯỞNG", 5],
                    ["MẪU CÂN TIỂU LY ĐIỆN TỬ", 6],
                    ["HÔM NAY RẺ BẤT NGỜ LUÔN", 6],
                    ["MỞ GIỎ HÀNG GÓC TRÁI", 5],
                    ["XEM THỬ NGAY NHÉ CÁC BÁC", 6],
                ],
            },
            {
                "id": "v4_s2",
                "file": "v4_s2.mp4",
                "timed": [
                    '[0.0-3.6s] "Giá không phải 200, không phải 150, 70K cũng không luôn."',
                    '[3.6-6.2s] "Mỗi tài khoản các bác sẽ nhận một mã trợ giá riêng."',
                    '[6.2-10.0s] "Bấm giỏ hàng bên dưới nha, thấy giá dưới 70K thì săn liền giúp em ạ."',
                ],
                "phrases": [
                    ["GIÁ KHÔNG PHẢI 200", 4],
                    ["KHÔNG PHẢI 150", 3],
                    ["70K CŨNG KHÔNG LUÔN", 4],
                    ["MỖI TÀI KHOẢN CÁC BÁC", 5],
                    ["NHẬN MỘT MÃ TRỢ GIÁ RIÊNG", 6],
                    ["BẤM GIỎ HÀNG BÊN DƯỚI NHA", 6],
                    ["THẤY GIÁ DƯỚI 70K", 4],
                    ["THÌ SĂN LIỀN GIÚP EM Ạ", 6],
                ],
            },
            {
                "id": "v4_s3",
                "file": "v4_s3.mp4",
                "timed": [
                    '[0.0-3.7s] "Mặt inox ba lẻ tư sáng bóng dễ vệ sinh, màn hình điện tử hiển thị sắc nét."',
                    '[3.7-7.1s] "Cân làm bánh pha chế hay cân thực phẩm đều chuẩn từng gam,"',
                    '[7.1-10.0s] "hết suất trợ giá là quay về giá cũ ngay đó ạ."',
                ],
                "phrases": [
                    ["MẶT INOX BA LẺ TƯ SÁNG BÓNG", 7],
                    ["MÀN HÌNH HIỂN THỊ SẮC NÉT", 6],
                    ["CÂN LÀM BÁNH PHA CHẾ", 5],
                    ["HAY CÂN THỰC PHẨM ĐỀU CHUẨN", 6],
                    ["CHÍNH XÁC ĐẾN TỪNG GAM", 5],
                    ["HẾT SUẤT TRỢ GIÁ HÔM NAY", 6],
                    ["LÀ VỀ GIÁ CŨ NGAY ĐÓ Ạ", 7],
                ],
            },
        ],
    },
    "v5": {
        "char_v": "nv1_v3",
        "character": "nv1",
        "hook_title": "NV1 - Kịch bản 3: Xả Kho Lô Mới",
        "style": "Phòng Thử Nghiệm & Hiệu Chuẩn Độ Chính Xác",
        "character_id": NV1_CHAR_ID,
        "project_id": NV1_PROJ_ID,
        "voice_id": NV1_VOICE_ID,
        "voice_name": NV1_VOICE_NAME,
        "ref_image": "v5-refimg.jpg",
        "ref_image_prompt": (
            "Photorealistic vertical 9:16 medium-wide standing photo (framed from head to hips, camera at 2 meters distance, NOT a close-up): "
            "the exact same woman from the character reference (shoulder-length layered black hair, black-framed glasses, identical face), "
            "wearing a polite warm mocha-brown tailored blazer over a slate-blue collared shirt and black trousers, standing behind a stainless-steel calibration workbench "
            "in a bright precision metrology and scale calibration workshop with stainless-steel test weights, measurement instruments, storage shelves, and engineers softly blurred in the background. "
            "She looks directly at the camera with a warm, friendly, confident smile while holding and presenting the exact compact digital kitchen scale from the product reference image in her hands at waist level facing the camera "
            "(true-to-life compact 18x14cm hand-held scale relative to her hands and body, NOT oversized), with neat retail packaging boxes on the workbench beside her. "
            "Keep the product 100% identical as shown in the product reference image (keep all original product details, prints, logos, and true size intact, do not redesign or alter the product in any way), and keep her face identical."
        ),
        "scenes_spec": [
            {
                "id": "v5_s1",
                "file": "v5_s1.mp4",
                "timed": [
                    '[0.0-3.5s] "Tin vui cho các bác đang tìm cân điện tử nhà bếp chuẩn xưởng giá bình dân."',
                    '[3.5-7.4s] "Lô mới xuất xưởng cân tiểu ly inox ba lẻ tư đang được sàn tài trợ giá,"',
                    '[7.4-10.0s] "các bác ấn ngay vào giỏ hàng xem ưu đãi nhé."',
                ],
                "phrases": [
                    ["TIN VUI CHO CÁC BÁC", 5],
                    ["TÌM CÂN ĐIỆN TỬ NHÀ BẾP", 6],
                    ["CHUẨN XƯỞNG GIÁ BÌNH DÂN", 5],
                    ["LÔ MỚI CÂN TIỂU LY INOX", 6],
                    ["ĐANG ĐƯỢC SÀN TÀI TRỢ GIÁ", 6],
                    ["ẤN NGAY VÀO GIỎ HÀNG", 5],
                    ["XEM ƯU ĐÃI NHÉ CÁC BÁC", 6],
                ],
            },
            {
                "id": "v5_s2",
                "file": "v5_s2.mp4",
                "timed": [
                    '[0.0-3.6s] "Giá không phải 200, không phải 150, 70K cũng không luôn."',
                    '[3.6-6.2s] "Giá hiển thị sẽ tùy thuộc vào ưu đãi từng tài khoản."',
                    '[6.2-10.0s] "Các bác kiểm tra giỏ hàng ngay, thấy dưới 70K là phải rinh liền tay ạ."',
                ],
                "phrases": [
                    ["GIÁ KHÔNG PHẢI 200", 4],
                    ["KHÔNG PHẢI 150", 3],
                    ["70K CŨNG KHÔNG LUÔN", 4],
                    ["GIÁ HIỂN THỊ TÙY THUỘC", 5],
                    ["ƯU ĐÃI TỪNG TÀI KHOẢN", 5],
                    ["KIỂM TRA GIỎ HÀNG NGAY", 5],
                    ["THẤY DƯỚI 70K LÀ PHẢI", 5],
                    ["RINH LIỀN TAY NHA CÁC BÁC", 6],
                ],
            },
            {
                "id": "v5_s3",
                "file": "v5_s3.mp4",
                "timed": [
                    '[0.0-3.6s] "Cân tối đa mười ký chia vạch một gam, có nút trừ bì và đổi đơn vị."',
                    '[3.6-7.0s] "Trang bị sẵn pin đi kèm dùng linh hoạt mọi nơi không lo nguồn điện,"',
                    '[7.0-10.0s] "chương trình chỉ mở trong hôm nay thôi ạ."',
                ],
                "phrases": [
                    ["CÂN TỐI ĐA MƯỜI KÝ", 5],
                    ["CHIA VẠCH CHUẨN MỘT GAM", 5],
                    ["CÓ NÚT TRỪ BÌ TIỆN LỢI", 6],
                    ["TRANG BỊ SẴN PIN ĐI KÈM", 6],
                    ["DÙNG LINH HOẠT MỌI NƠI", 5],
                    ["CHƯƠNG TRÌNH CHỈ MỞ", 4],
                    ["TRONG HÔM NAY THÔI Ạ", 5],
                ],
            },
        ],
    },
    "v6": {
        "char_v": "nv2_v3",
        "character": "nv2",
        "hook_title": "NV2 - Kịch bản 3: Săn Deal Tận Gốc",
        "style": "Khu Băng Chuyền Đóng Gói Xuất Kho",
        "character_id": NV2_CHAR_ID,
        "project_id": NV2_PROJ_ID,
        "voice_id": NV2_VOICE_ID,
        "voice_name": NV2_VOICE_NAME,
        "ref_image": "v6-refimg.jpg",
        "ref_image_prompt": (
            "Photorealistic vertical 9:16 medium-wide standing photo (framed from head to hips, camera at 2 meters distance, NOT a close-up): "
            "the exact same woman from the character reference (long wavy dark-brown hair in a high ponytail with colourful pastel hair clips, identical face, no glasses), "
            "wearing a polite smart-casual dove-grey blazer over a soft pastel pink collared shirt and black trousers, standing behind a stainless-steel packing station "
            "in a modern automated factory packaging and parcel fulfillment center with roller conveyor belts, barcode scanners, neatly taped shipping boxes, and fulfillment workers in navy polo uniforms softly blurred in the background. "
            "She looks directly at the camera with a warm, friendly, confident smile while holding and presenting the exact compact digital kitchen scale from the product reference image in her hands at waist level facing the camera "
            "(true-to-life compact 18x14cm hand-held scale relative to her hands and body, NOT oversized), with neat retail packaging boxes on the station beside her. "
            "Keep the product 100% identical as shown in the product reference image (keep all original product details, prints, logos, and true size intact, do not redesign or alter the product in any way), and keep her face identical."
        ),
        "scenes_spec": [
            {
                "id": "v6_s1",
                "file": "v6_s1.mp4",
                "timed": [
                    '[0.0-3.5s] "Thật sự mức giá hôm nay làm em đứng tại xưởng cũng bất ngờ."',
                    '[3.5-7.4s] "Nguyên một chiếc cân tiểu ly điện tử inox mười ký mà giá chỉ bằng bữa sáng,"',
                    '[7.4-10.0s] "các bác bấm giỏ hàng bên dưới xem ngay nha."',
                ],
                "phrases": [
                    ["MỨC GIÁ HÔM NAY LÀM EM", 6],
                    ["ĐỨNG TẠI XƯỞNG CŨNG BẤT NGỜ", 6],
                    ["NGUYÊN CHIẾC CÂN TIỂU LY", 5],
                    ["ĐIỆN TỬ INOX MƯỜI KÝ", 5],
                    ["MÀ GIÁ CHỈ BẰNG BỮA SÁNG", 6],
                    ["BẤM GIỎ HÀNG BÊN DƯỚI", 5],
                    ["XEM NGAY NHA CÁC BÁC", 5],
                ],
            },
            {
                "id": "v6_s2",
                "file": "v6_s2.mp4",
                "timed": [
                    '[0.0-3.6s] "Giá không phải 200, không phải 150, 70K cũng không luôn."',
                    '[3.6-6.2s] "Do sàn phát ngẫu nhiên voucher cho từng người xem video."',
                    '[6.2-10.0s] "Mở ngay giỏ hàng góc trái nha, ai thấy dưới 70K là cực kỳ may mắn đó."',
                ],
                "phrases": [
                    ["GIÁ KHÔNG PHẢI 200", 4],
                    ["KHÔNG PHẢI 150", 3],
                    ["70K CŨNG KHÔNG LUÔN", 4],
                    ["DO SÀN PHÁT NGẪU NHIÊN", 5],
                    ["VOUCHER CHO TỪNG NGƯỜI XEM", 5],
                    ["MỞ NGAY GIỎ HÀNG GÓC TRÁI", 6],
                    ["AI THẤY DƯỚI 70K LÀ", 5],
                    ["CỰC KỲ MAY MẮN ĐÓ Ạ", 6],
                ],
            },
            {
                "id": "v6_s3",
                "file": "v6_s3.mp4",
                "timed": [
                    '[0.0-3.6s] "Chất liệu hợp kim thép inox ba lẻ tư bền bỉ, cân chính xác từng gam."',
                    '[3.6-7.0s] "Đầy đủ tính năng trừ bì và tặng sẵn pin trong hộp,"',
                    '[7.0-10.0s] "ưu đãi số lượng ít nên các bác bấm mua liền nhé."',
                ],
                "phrases": [
                    ["CHẤT LIỆU HỢP KIM THÉP", 5],
                    ["INOX BA LẺ TƯ BỀN BỈ", 6],
                    ["CÂN CHÍNH XÁC TỪNG GAM", 5],
                    ["ĐẦY ĐỦ TÍNH NĂNG TRỪ BÌ", 6],
                    ["VÀ TẶNG SẴN PIN TRONG HỘP", 6],
                    ["ƯU ĐÃI SỐ LƯỢNG ÍT LẮM", 6],
                    ["CÁC BÁC BẤM MUA LIỀN NHÉ", 6],
                ],
            },
        ],
    },
}


def main():
    videos_json = {}
    for vk, vdata in VARIANTS.items():
        scenes_list = []
        spec_scenes = []
        for idx_s, sc in enumerate(vdata["scenes_spec"], start=1):
            # Validate phrase lengths <= 28 chars
            for txt, sw in sc["phrases"]:
                assert len(txt) <= 28, f"Phrase too long ({len(txt)}): {txt}"
            total_w = sum(sw for _, sw in sc["phrases"])
            v_prompt = make_video_prompt(idx_s, sc["timed"])
            scenes_list.append({
                "id": sc["id"],
                "file": sc["file"],
                "words": total_w,
                "prompt": v_prompt,
            })
            spec_scenes.append({
                "file": sc["file"],
                "words": total_w,
                "phrases": sc["phrases"],
            })

        videos_json[vk] = {
            "character": vdata["character"],
            "hook_title": vdata["hook_title"],
            "style": vdata["style"],
            "character_id": vdata["character_id"],
            "project_id": vdata["project_id"],
            "voice_id": vdata["voice_id"],
            "voice_name": vdata["voice_name"],
            "ref_image": vdata["ref_image"],
            "ref_image_prompt": vdata["ref_image_prompt"],
            "primary_product_refs": PRIMARY_REFS,
            "slide_overlay_files": SLIDE_OVERLAYS,
            "scenes": scenes_list,
        }

        spec_obj = {
            "scenes": spec_scenes,
            "overlays": [os.path.join("product_images", f) for f in SLIDE_OVERLAYS],
            "output": f"{PID}_{vdata['char_v']}.mp4",
        }
        with open(os.path.join(PDIR, f"spec_{vk}.json"), "w", encoding="utf-8") as f:
            json.dump(spec_obj, f, ensure_ascii=False, indent=2)

    prompts_obj = {
        "product_id": PID,
        "product_name": PNAME,
        "primary_product_refs": PRIMARY_REFS,
        "slide_overlay_files": SLIDE_OVERLAYS,
        "ref_img_prompt_nv1": VARIANTS["v1"]["ref_image_prompt"],
        "ref_img_prompt_nv2": VARIANTS["v2"]["ref_image_prompt"],
        "videos": videos_json,
    }
    with open(os.path.join(PDIR, "prompts.json"), "w", encoding="utf-8") as f:
        json.dump(prompts_obj, f, ensure_ascii=False, indent=2)

    print(f"[OK] Created prompts.json and spec_v1..v6.json for {PID} ({PNAME})")


if __name__ == "__main__":
    main()

