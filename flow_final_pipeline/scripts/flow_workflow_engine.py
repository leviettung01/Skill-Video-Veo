# -*- coding: utf-8 -*-
"""
🔗 Lê Việt Tùng - SkillAutoVeo
Hệ Thống FLOW WORKFLOW ENGINE (Node-Based Visual Workflow cho Google Flow + CLIProxy ChatGPT/Gemini + Grok)
-----------------------------------------------------------------------------------------------------------
- Tương thích 100% chuẩn JSON Workflow (`version: "1.0"`, `type: "workflow"`, `workflow: {name, description, settings, nodes, edges}`).
- Hỗ trợ đầy đủ các loại Node chuẩn (như Ảnh 1, 2, 3, 4):
  1. `image` / `video` (Image/Video): Ảnh hoặc Video tham chiếu (từ máy, URL, Thư viện Nhân vật NV1–NV5, hoặc Kho Sản Phẩm).
  2. `prompt` (Prompt): Truyền prompt trực tiếp hoặc gọi AI qua CLIProxy (`:8317` ChatGPT / Gemini Vision) để nâng cấp prompt, phân tích ảnh, viết kịch bản.
  3. `generate` (Flow - Image/Video Generate):
     - Chế độ `Image`: Tạo ảnh bằng Google Flow (`Nano Banana 2.1`, `Nano Banana Pro`, `Nano Banana 2 Lite`), hỗ trợ tải chuẩn 2K (`SPrCad`) hoặc 1K.
     - Chế độ `Video`: Tạo video bằng Google Flow (`Omni 1.2 Flash` **mới** 6s/8s/10s/15s, `Omni 1.1 Flash` 6s/8s/10s, `Ingredients` / `Video Reference`, hoặc `Veo 3.1 - Fast` / `Veo 3.1 - Quality`), hỗ trợ upscale 1080p (`p0UkFb`).
  4. `gpt_image` (GPT Image 2): Tạo ảnh qua CLIProxy ChatGPT (`gpt-image-1` / `dall-e-3`) hoặc fallback Google Flow 2K.
  5. `grok_generate` (Grok - Images/Videos Generate): Tạo ảnh/video qua Grok Imagine / CLIProxy.
  6. `gemini_generate` (Gemini - Image/Video Generate): Tạo ảnh/video hoặc xử lý đa phương thức qua Gemini CLIProxy.
  7. `auto_download` (Auto Download): Tự động lưu file kết quả từ node đứng trước về thư mục `final_videos/` hoặc `workflow_downloads/`.
  8. `text` (Text): Nguồn văn bản tĩnh để ghép qua `@slug`.
  9. `text_extract` (Text Extract): Tách văn bản từ node đứng trước bằng Regex / JSON key / Marker (không tốn gọi AI).
  10. `note` (Note): Ghi chú trên Canvas (không thực thi).
"""

import os
import sys
import re
import json
import time
import uuid
import shutil
import base64
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
WS_DIR = os.path.abspath(os.path.join(PIPELINE_DIR, ".."))
WORKFLOW_ROOT_DIR = os.path.join(WS_DIR, "WorkFlow")
SAVED_WORKFLOWS_DIR = os.path.join(WORKFLOW_ROOT_DIR, "saved_workflows")
WORKFLOW_OUTPUTS_DIR = os.path.join(WORKFLOW_ROOT_DIR, "workflow_outputs")
FINAL_VIDEOS_DIR = os.path.join(WS_DIR, "final_videos")
DEMO_2K_DIR = os.path.join(WS_DIR, "ảnh mẫu thumbnail", "Tron_Bo_7_Anh_2K")
CHARS_DIR = os.path.join(PIPELINE_DIR, "characters")

os.makedirs(SAVED_WORKFLOWS_DIR, exist_ok=True)
os.makedirs(WORKFLOW_OUTPUTS_DIR, exist_ok=True)
os.makedirs(FINAL_VIDEOS_DIR, exist_ok=True)

# Trạng thái thực thi trực tiếp (live runtime status) của các workflow đang chạy
_WORKFLOW_RUN_STATE = {}


# ==============================================================================
# 1. KHO WORKFLOW MẪU MẶC ĐỊNH (BAO GỒM WORKFLOW ELEVATOR MIRROR OUTFIT CHECK CỦA USER)
# ==============================================================================

ELEVATOR_MIRROR_OUTFIT_CHECK_WF = {
    "id": "wf_elevator_mirror_outfit_check",
    "version": "1.0",
    "type": "workflow",
    "exported_at": "2026-11-05T01:45:52.974Z",
    "workflow": {
        "name": "Workflow - Elevator Mirror Outfit Check (Outfit check gương thang máy)",
        "description": (
            "A TobyFlow / Google Flow Workflow using AI Models (ChatGPT + Google Flow) to swap any outfit onto a model "
            "in the viral elevator mirror-selfie scene, then animate it into a 9:16 video. Generate trendy first-outfit-check "
            "fashion content for social reels on autopilot.\n\n"
            "Workflow dùng AI Model (ChatGPT + Google Flow) ghép trang phục bất kỳ lên người mẫu trong cảnh selfie gương thang máy "
            "đang viral, rồi dựng thành 2 video 9:16 (10s). Tạo content outfit check thời thượng tự động."
        ),
        "settings": {
            "parallel": True,
            "quantity": 1,
            "delay_between_nodes": 3,
            "timeout_per_node": 120,
            "retry_on_error": 0,
            "stop_on_error": True,
        },
        "nodes": [
            {
                "node_id": "node_Ld8FM3qT",
                "node_type": "image",
                "node_name": "Image",
                "pos_x": 124,
                "pos_y": -180,
                "enabled": True,
                "slug": "image",
                "slug_auto": True,
                "local_path": os.path.join(WORKFLOW_OUTPUTS_DIR, "wf_elevator_mirror_outfit_check", "ref_elevator_mirror_selfie_2k.jpg"),
                "ref_images": [
                    {
                        "thumbnail": "https://labs.toby.vn/storage/media/2026/06/db70c480-c953-414d-81d8-f06cb944238b.jpg",
                        "local_path": os.path.join(WORKFLOW_OUTPUTS_DIR, "wf_elevator_mirror_outfit_check", "ref_elevator_mirror_selfie_2k.jpg"),
                    }
                ],
            },
            {
                "node_id": "node_j6J92FvO",
                "node_type": "image",
                "node_name": "Outfit",
                "pos_x": 126,
                "pos_y": 240,
                "enabled": True,
                "slug": "image_2",
                "slug_auto": True,
                "local_path": os.path.join(DEMO_2K_DIR, "05_Product_Sheet_Quan_Sooc_Trang_2K.png"),
                "ref_images": [
                    {
                        "thumbnail": "https://labs.toby.vn/storage/media/2026/08/1b6f803e-035d-4bb7-9cff-11ef068bfc6f.jpeg",
                        "local_path": os.path.join(DEMO_2K_DIR, "05_Product_Sheet_Quan_Sooc_Trang_2K.png"),
                    }
                ],
            },
            {
                "node_id": "node_tTfIoakt",
                "node_type": "prompt",
                "node_name": "Prompt - Image",
                "pos_x": 126,
                "pos_y": 620,
                "enabled": True,
                "slug": "prompt",
                "slug_auto": True,
                "prompt_mode": "all",
                "ref_mode": "all",
                "prompt": (
                    "IMAGE 01 = the elevator mirror selfie reference image with the girl standing inside a stainless steel elevator, "
                    "holding a phone covering her face, wearing a fluffy cream oversized sweater, beige mini skirt, and knee-high boots.\n\n"
                    "IMAGE 02 = the uploaded outfit reference image that will replace the current clothing on the model.\n\n"
                    "Use IMAGE 01 as the primary reference for:\n\n"
                    "* elevator environment\n* mirror selfie composition\n* camera angle\n* body pose\n* hair style\n* lighting mood\n"
                    "* body proportions\n* hidden-face aesthetic\n* overall realistic fashion vibe\n* original person identity\n\n"
                    "Use IMAGE 02 as the exact outfit replacement reference.\n"
                    "Replace ONLY the clothing and accessories on the model from IMAGE 01 using the outfit from IMAGE 02 while fully preserving:\n\n"
                    "* the original person\n* original pose\n* original body shape\n* original hair\n* original elevator background\n"
                    "* original framing and composition\n* original lighting direction\n* original mirror selfie perspective\n\n"
                    "The final image must look like the same real person from IMAGE 01 naturally wearing the outfit from IMAGE 02 inside the same elevator scene.\n\n"
                    "IMPORTANT OUTFIT RULES:\n\n"
                    "* preserve all outfit details from IMAGE 02 exactly\n"
                    "* preserve fabric texture, stitching, folds, silhouette, fit, layering, and accessories\n"
                    "* do not redesign or reinterpret the outfit\n"
                    "* do not simplify clothing details\n"
                    "* maintain accurate garment proportions\n"
                    "* outfit must realistically wrap around the existing body pose\n"
                    "* preserve realistic fabric tension and gravity\n\n"
                    "PHONE REQUIREMENT:\n"
                    "Replace the original phone with an iPhone 17 Pro Max in elegant desert orange / soft orange titanium color.\n"
                    "The phone should look premium, realistic, and naturally held in front of the face.\n"
                    "Maintain the same hidden-face mirror selfie composition.\n\n"
                    "REALISM REQUIREMENTS:\n\n"
                    "* ultra realistic fashion photography\n* indistinguishable from a real iPhone mirror selfie\n* natural skin texture\n"
                    "* realistic lighting and shadows\n* realistic stainless steel elevator reflections\n* realistic hair strands\n"
                    "* natural body proportions\n* authentic mirror reflection behavior\n* realistic fabric wrinkles and movement\n"
                    "* no AI artifacts\n* no distorted anatomy\n* no warped elevator background\n* no fake glossy skin\n"
                    "* no plastic texture\n* no unrealistic fingers or hands\n* no over-beautified face\n\n"
                    "STYLE:\n"
                    "Luxury Korean fashion influencer mirror selfie, premium Instagram fashion aesthetic, cozy minimal luxury mood, "
                    "realistic smartphone photography, natural cinematic lighting, authentic social media fashion content, soft neutral tones, elegant feminine styling."
                ),
                "use_ai": False,
                "ai_provider": "cliproxy_gpt",
                "ai_model": "gpt-4o-mini",
                "ai_fallback": True,
                "ai_delete_after_run": False,
                "timeout_sec": 60,
            },
            {
                "node_id": "node_ixyFnhE2",
                "node_type": "generate",
                "provider": "flow",
                "node_name": "Flow - Images Generate",
                "pos_x": 620,
                "pos_y": 20,
                "enabled": True,
                "slug": "flow_images_videos_genera",
                "slug_auto": True,
                "prompt_mode": "all",
                "ref_mode": "all",
                "media_type": "Image",
                "model": "Nano Banana 2.1",
                "quantity": 1,
                "ratio": "9:16",
                "download_resolution": "2k",
                "video_download_resolution": "1080p",
                "prompt_source": "upstream_node",
                "multi_prompt": False,
                "auto_download": True,
            },
            {
                "node_id": "node_MnikFJvV",
                "node_type": "prompt",
                "node_name": "Prompt - Video 01",
                "pos_x": 620,
                "pos_y": 430,
                "enabled": True,
                "slug": "prompt_2",
                "slug_auto": True,
                "prompt_mode": "all",
                "ref_mode": "all",
                "prompt": (
                    "IMAGE 01 = the elevator mirror selfie reference image with the girl standing inside a stainless steel elevator, "
                    "holding a phone covering her face, wearing a fluffy cream oversized sweater, beige mini skirt, and knee-high boots.\n\n"
                    "IMAGE 02 = the uploaded outfit reference image that will replace the current clothing on the model.\n\n"
                    "Use IMAGE 01 as the primary reference for:\n\n"
                    "* elevator environment\n* mirror selfie framing\n* hidden-face aesthetic\n* camera angle\n* pose style\n"
                    "* body proportions\n* hair style\n* lighting mood\n* original person identity\n* overall luxury fashion vibe\n\n"
                    "Use IMAGE 02 as the exact outfit replacement reference.\n"
                    "Replace ONLY the outfit from IMAGE 01 with the outfit from IMAGE 02 while preserving:\n\n"
                    "* the same real person\n* same pose style\n* same hair\n* same body shape\n* same elevator background\n"
                    "* same mirror selfie composition\n* same camera perspective\n* same lighting direction\n\n"
                    "The final video must look like the same real girl from IMAGE 01 naturally wearing the outfit from IMAGE 02 inside the same elevator environment.\n\n"
                    "Create a 10-second ultra realistic cinematic fashion reel filmed as a handheld mirror selfie inside a luxury stainless steel elevator.\n\n"
                    "VIDEO STYLE:\n\n"
                    "* ultra realistic fashion reel\n* realistic iPhone mirror selfie footage\n* cozy luxury Korean influencer vibe\n"
                    "* cinematic soft lighting\n* realistic elevator reflections\n* smooth natural movement\n* handheld smartphone feel\n"
                    "* ultra realistic fabric physics\n* not AI-looking\n\n"
                    "PHONE REQUIREMENT:\n"
                    "Replace the current phone with an iPhone 17 Pro Max in elegant desert orange / soft orange titanium color.\n"
                    "The phone must continuously cover the face during the entire video.\n\n"
                    "SCENE FLOW:\n\n"
                    "0s – 2s\nThe model stands casually in front of the mirror as if the elevator has just started moving. One leg crosses naturally in front of the other. Small body sway. Hair softly resting over the outfit.\n\n"
                    "2s – 4s\nShe gently adjusts one sleeve or outfit detail naturally while slightly tilting her hips. The fabric from IMAGE 02 moves naturally and realistically.\n\n"
                    "4s – 6s\nThe model slowly turns slightly sideways to showcase the silhouette of the outfit from IMAGE 02. Her free hand softly smooths the clothing fabric.\n\n"
                    "6s – 8s\nShe subtly lifts one leg forward to highlight the lower outfit styling while the shoulder bag or accessories naturally move with body motion.\n\n"
                    "8s – 10s\nFinal calm pose facing the mirror. Relaxed luxury fashion mood. Soft hair movement. Realistic reflections and natural fabric folds.\n\n"
                    "IMPORTANT:\n\n"
                    "* face always hidden behind the iPhone 17 Pro Max\n* preserve exact outfit details from IMAGE 02\n"
                    "* preserve same person and same environment from IMAGE 01\n* realistic body movement only\n* no exaggerated acting\n"
                    "* no AI artifacts\n* ultra realistic smartphone video aesthetic"
                ),
                "use_ai": False,
                "ai_fallback": True,
                "ai_delete_after_run": False,
                "timeout_sec": 60,
            },
            {
                "node_id": "node_7uE1RgvP",
                "node_type": "prompt",
                "node_name": "Prompt - Video 02",
                "pos_x": 620,
                "pos_y": 690,
                "enabled": True,
                "slug": "prompt_3",
                "slug_auto": True,
                "prompt_mode": "all",
                "ref_mode": "all",
                "prompt": (
                    "IMAGE 01 = the elevator mirror selfie reference image with the girl standing inside a stainless steel elevator, holding a phone covering her face.\n\n"
                    "IMAGE 02 = the uploaded outfit reference image that will replace the current clothing on the model.\n\n"
                    "Use IMAGE 01 as the primary reference for:\n\n"
                    "* elevator environment\n* mirror selfie composition\n* hidden-face aesthetic\n* body proportions\n* pose style\n"
                    "* lighting mood\n* hair style\n* realistic fashion vibe\n* original person identity\n\n"
                    "Use IMAGE 02 as the exact outfit replacement reference.\n"
                    "Replace ONLY the clothing and accessories while fully preserving the original girl, pose style, background, and mirror framing from IMAGE 01.\n\n"
                    "Create a 10-second ultra realistic vertical fashion video that feels like a continuation of VIDEO 01, filmed moments later inside the same elevator.\n\n"
                    "STYLE:\n\n"
                    "* luxury Korean fashion influencer reel\n* calm feminine energy\n* realistic elevator reflections\n"
                    "* premium soft indoor lighting\n* natural handheld phone movement\n* ultra realistic hair and fabric motion\n"
                    "* indistinguishable from real smartphone footage\n\n"
                    "PHONE REQUIREMENT:\n"
                    "Use an iPhone 17 Pro Max in elegant desert orange titanium color.\n"
                    "The phone must fully cover the face during the entire video.\n\n"
                    "SCENE FLOW:\n\n"
                    "0s – 2s\nThe model stands slightly closer to the mirror than before. One shoulder lowered naturally, creating a relaxed oversized styling silhouette.\n\n"
                    "2s – 4s\nShe softly flips part of her hair behind one shoulder while leaning slightly toward the mirror. The phone still fully hides the face.\n\n"
                    "4s – 5.5s\nThe model gently adjusts the shoulder bag or outfit accessory while slowly turning her body sideways to reveal the silhouette and texture of the outfit from IMAGE 02.\n\n"
                    "5.5s – 7s\nShe lightly touches the outfit fabric and smooths it naturally, showcasing realistic material texture and fit.\n\n"
                    "7s – 8.5s\nThe model bends one knee slightly and shifts weight naturally, highlighting the lower part of the styling and silhouette in a relaxed fashion pose.\n\n"
                    "8.5s – 10s\nFinal close mirror pose. Calm luxury mood. Slight body tilt. Natural outfit folds and soft hair movement.\n\n"
                    "IMPORTANT:\n\n"
                    "* maintain same outfit and elevator continuity\n* preserve exact outfit details from IMAGE 02\n"
                    "* preserve same girl from IMAGE 01\n* no dramatic movement\n* realistic influencer-style posing only\n"
                    "* face fully hidden entire video\n* realistic proportions and reflections\n* no AI-looking textures or movements"
                ),
                "use_ai": False,
                "ai_fallback": True,
                "ai_delete_after_run": False,
                "timeout_sec": 60,
            },
            {
                "node_id": "node_WnKF3PoT",
                "node_type": "generate",
                "provider": "flow",
                "node_name": "Flow - Videos Generate 01",
                "pos_x": 1140,
                "pos_y": -140,
                "enabled": True,
                "slug": "flow_images_videos_genera_1",
                "slug_auto": True,
                "prompt_mode": "all",
                "ref_mode": "all",
                "media_type": "Video",
                "video_input_type": "Ingredients",
                "video_duration": "10s",
                "model": "Omni 1.1 Flash",
                "quantity": 1,
                "ratio": "9:16",
                "download_resolution": "2k",
                "video_download_resolution": "1080p",
                "prompt_source": "upstream_node",
                "multi_prompt": False,
                "auto_download": True,
            },
            {
                "node_id": "node_rGXX9NuY",
                "node_type": "generate",
                "provider": "flow",
                "node_name": "Flow - Videos Generate 3",
                "pos_x": 1140,
                "pos_y": 360,
                "enabled": True,
                "slug": "flow_images_videos_genera_2",
                "slug_auto": True,
                "prompt_mode": "all",
                "ref_mode": "all",
                "media_type": "Video",
                "video_input_type": "Ingredients",
                "video_duration": "10s",
                "model": "Omni 1.1 Flash",
                "quantity": 1,
                "ratio": "9:16",
                "download_resolution": "2k",
                "video_download_resolution": "1080p",
                "prompt_source": "upstream_node",
                "multi_prompt": False,
                "auto_download": True,
            },
        ],
        "edges": [
            {
                "edge_id": "edge_16_output_1_10_input_1",
                "source_node_id": "node_Ld8FM3qT",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_ixyFnhE2",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "edge_9_output_1_10_input_1",
                "source_node_id": "node_j6J92FvO",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_ixyFnhE2",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "edge_11_output_1_10_input_2",
                "source_node_id": "node_tTfIoakt",
                "source_handle": "output_1",
                "source_port": "text",
                "target_node_id": "node_ixyFnhE2",
                "target_handle": "input_2",
                "target_port": "text",
                "data_type": "text",
            },
            {
                "edge_id": "edge_10_output_1_12_input_1",
                "source_node_id": "node_ixyFnhE2",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_WnKF3PoT",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "edge_9_output_1_12_input_1",
                "source_node_id": "node_j6J92FvO",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_WnKF3PoT",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "edge_14_output_1_12_input_2",
                "source_node_id": "node_MnikFJvV",
                "source_handle": "output_1",
                "source_port": "text",
                "target_node_id": "node_WnKF3PoT",
                "target_handle": "input_2",
                "target_port": "text",
                "data_type": "text",
            },
            {
                "edge_id": "edge_10_output_1_13_input_1",
                "source_node_id": "node_ixyFnhE2",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_rGXX9NuY",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "edge_9_output_1_13_input_1",
                "source_node_id": "node_j6J92FvO",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_rGXX9NuY",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "edge_15_output_1_13_input_2",
                "source_node_id": "node_7uE1RgvP",
                "source_handle": "output_1",
                "source_port": "text",
                "target_node_id": "node_rGXX9NuY",
                "target_handle": "input_2",
                "target_port": "text",
                "data_type": "text",
            },
        ],
    },
}

FACTORY_2K_STANDARD_WF = {
    "id": "wf_factory_2k_3scenes_standard",
    "version": "1.0",
    "type": "workflow",
    "exported_at": "2026-11-05T02:00:00.000Z",
    "workflow": {
        "name": "Workflow - Nhà Xưởng Chuẩn 2K (Ảnh NV + Ảnh SP ➔ Ảnh Ref 2K ➔ 3 Video Phân Cảnh 1080p)",
        "description": (
            "Quy trình chuẩn tạo Video Nhà Xưởng trên Google Flow: Kết hợp Ảnh Nhân Vật (NV1/NV2) + Ảnh Sản Phẩm Gốc "
            "để tạo Ảnh Ref Nhân Vật Cầm Sản Phẩm chuẩn 2K (Nano Banana 2.1 2K), sau đó nối Ảnh Ref 2K + Ảnh Sản Phẩm "
            "vào 3 Node tạo Video Phân Cảnh 1, 2, 3 chạy song song và Upscale 1080p."
        ),
        "settings": {
            "parallel": True,
            "quantity": 1,
            "delay_between_nodes": 2,
            "timeout_per_node": 180,
            "retry_on_error": 1,
            "stop_on_error": False,
        },
        "nodes": [
            {
                "node_id": "node_char_nv1",
                "node_type": "image",
                "node_name": "Character Sheet (NV1)",
                "pos_x": 100,
                "pos_y": -160,
                "enabled": True,
                "slug": "char_nv1",
                "slug_auto": True,
                "local_path": os.path.join(CHARS_DIR, "nv1_ref.jpg"),
                "ref_images": [{"local_path": os.path.join(CHARS_DIR, "nv1_ref.jpg")}],
            },
            {
                "node_id": "node_prod_img",
                "node_type": "image",
                "node_name": "Product Image (SP Gốc)",
                "pos_x": 100,
                "pos_y": 240,
                "enabled": True,
                "slug": "product_img",
                "slug_auto": True,
                "local_path": os.path.join(DEMO_2K_DIR, "05_Product_Sheet_Quan_Sooc_Trang_2K.png"),
                "ref_images": [{"local_path": os.path.join(DEMO_2K_DIR, "05_Product_Sheet_Quan_Sooc_Trang_2K.png")}],
            },
            {
                "node_id": "node_prompt_ref2k",
                "node_type": "prompt",
                "node_name": "Prompt - Tạo Ảnh Ref 2K",
                "pos_x": 100,
                "pos_y": 580,
                "enabled": True,
                "slug": "prompt_ref_2k",
                "slug_auto": True,
                "prompt": (
                    "Hyper-photorealistic vertical 9:16 medium-full shot (framed from head to hips/thighs, 35mm f/2.0 lens) "
                    "of the exact same Vietnamese female presenter from IMAGE 01 standing inside a busy, authentic factory warehouse "
                    "with tall steel pallet racks and stacked cartons in the background. She holds and presents the exact product "
                    "from IMAGE 02 at chest-to-waist level with a warm, energetic smile. Detailed natural skin pores, rosy dewy glass-skin, "
                    "crisp 2K resolution, 100% identical product shape and details."
                ),
                "use_ai": False,
            },
            {
                "node_id": "node_gen_ref2k",
                "node_type": "generate",
                "provider": "flow",
                "node_name": "Flow - Tạo Ảnh Ref Cầm SP (2K)",
                "pos_x": 600,
                "pos_y": 40,
                "enabled": True,
                "slug": "flow_ref_image_2k",
                "slug_auto": True,
                "media_type": "Image",
                "model": "Nano Banana 2.1",
                "quantity": 1,
                "ratio": "9:16",
                "download_resolution": "2k",
                "prompt_source": "upstream_node",
                "auto_download": True,
            },
            {
                "node_id": "node_prompt_s1",
                "node_type": "prompt",
                "node_name": "Prompt - Phân Cảnh 1 (Hook Báo Giá)",
                "pos_x": 600,
                "pos_y": 440,
                "enabled": True,
                "slug": "prompt_scene_1",
                "slug_auto": True,
                "prompt": (
                    "A 10-second vertical 9:16 video starting directly from IMAGE 01 (the 2K reference image) and keeping the product "
                    "100% identical to IMAGE 02. Medium-full eye-level 35mm shot in the busy warehouse. The presenter speaks with high energy, "
                    "holding the product steady and gesturing toward the camera."
                ),
                "use_ai": False,
            },
            {
                "node_id": "node_prompt_s2",
                "node_type": "prompt",
                "node_name": "Prompt - Phân Cảnh 2 (Macro B-Roll & Công Năng)",
                "pos_x": 600,
                "pos_y": 680,
                "enabled": True,
                "slug": "prompt_scene_2",
                "slug_auto": True,
                "prompt": (
                    "SHOT 1 (0.0-1.5s): Medium-full 35mm shot from IMAGE 01 in the warehouse. "
                    "SHOT 2 (1.5-5.5s): Hard cut to a 50mm macro product insert showcasing the exact texture and details of IMAGE 02. "
                    "SHOT 3 (5.5-10.0s): Cut back to the presenter holding the product and smiling."
                ),
                "use_ai": False,
            },
            {
                "node_id": "node_gen_vid_s1",
                "node_type": "generate",
                "provider": "flow",
                "node_name": "Flow - Video Phân Cảnh 01",
                "pos_x": 1140,
                "pos_y": -120,
                "enabled": True,
                "slug": "flow_video_s1",
                "slug_auto": True,
                "media_type": "Video",
                "video_input_type": "Ingredients",
                "video_duration": "10s",
                "model": "Veo 3.1 - Fast",
                "character_key": "nv1",
                "voice_key": "nv1",
                "quantity": 1,
                "ratio": "9:16",
                "video_download_resolution": "1080p",
                "prompt_source": "upstream_node",
                "auto_download": True,
            },
            {
                "node_id": "node_gen_vid_s2",
                "node_type": "generate",
                "provider": "flow",
                "node_name": "Flow - Video Phân Cảnh 02",
                "pos_x": 1140,
                "pos_y": 360,
                "enabled": True,
                "slug": "flow_video_s2",
                "slug_auto": True,
                "media_type": "Video",
                "video_input_type": "Ingredients",
                "video_duration": "10s",
                "model": "Veo 3.1 - Fast",
                "character_key": "nv1",
                "voice_key": "nv1",
                "quantity": 1,
                "ratio": "9:16",
                "video_download_resolution": "1080p",
                "prompt_source": "upstream_node",
                "auto_download": True,
            },
        ],
        "edges": [
            {
                "edge_id": "e_char_to_ref2k",
                "source_node_id": "node_char_nv1",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_gen_ref2k",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "e_prod_to_ref2k",
                "source_node_id": "node_prod_img",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_gen_ref2k",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "e_prompt_to_ref2k",
                "source_node_id": "node_prompt_ref2k",
                "source_handle": "output_1",
                "source_port": "text",
                "target_node_id": "node_gen_ref2k",
                "target_handle": "input_2",
                "target_port": "text",
                "data_type": "text",
            },
            {
                "edge_id": "e_ref2k_to_v1",
                "source_node_id": "node_gen_ref2k",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_gen_vid_s1",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "e_prod_to_v1",
                "source_node_id": "node_prod_img",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_gen_vid_s1",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "e_ps1_to_v1",
                "source_node_id": "node_prompt_s1",
                "source_handle": "output_1",
                "source_port": "text",
                "target_node_id": "node_gen_vid_s1",
                "target_handle": "input_2",
                "target_port": "text",
                "data_type": "text",
            },
            {
                "edge_id": "e_ref2k_to_v2",
                "source_node_id": "node_gen_ref2k",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_gen_vid_s2",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "e_prod_to_v2",
                "source_node_id": "node_prod_img",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_gen_vid_s2",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "e_ps2_to_v2",
                "source_node_id": "node_prompt_s2",
                "source_handle": "output_1",
                "source_port": "text",
                "target_node_id": "node_gen_vid_s2",
                "target_handle": "input_2",
                "target_port": "text",
                "data_type": "text",
            },
        ],
    },
}

CLIPROXY_HYBRID_FASHION_WF = {
    "id": "wf_cliproxy_gpt_grok_fashion_2k",
    "version": "1.0",
    "type": "workflow",
    "exported_at": "2026-11-05T02:10:00.000Z",
    "workflow": {
        "name": "Workflow - Hybrid CLIProxy (ChatGPT Phân Tích Ảnh SP ➔ Tách Đồ 2K ➔ Nhân Vật NV5 Mặc Đồ & Tạo Video)",
        "description": (
            "Kết hợp sức mạnh của CLIProxy (ChatGPT Vision / Gemini phân tích ảnh quần áo gốc để sinh Prompt chuẩn) "
            "+ Google Flow Nano Banana 2.1 tạo Ảnh Tách Quần Áo Phụ Kiện 2K + Ghép lên Nhân Vật 5 (NV5) và render Video Lookbook."
        ),
        "settings": {
            "parallel": True,
            "quantity": 1,
            "delay_between_nodes": 2,
            "timeout_per_node": 150,
            "retry_on_error": 0,
            "stop_on_error": True,
        },
        "nodes": [
            {
                "node_id": "node_raw_cloth",
                "node_type": "image",
                "node_name": "Ảnh Quần Áo Gốc",
                "pos_x": 100,
                "pos_y": -140,
                "enabled": True,
                "slug": "raw_cloth",
                "slug_auto": True,
                "local_path": os.path.join(DEMO_2K_DIR, "03_Product_Sheet_Quan_Xanh_2K.png"),
                "ref_images": [{"local_path": os.path.join(DEMO_2K_DIR, "03_Product_Sheet_Quan_Xanh_2K.png")}],
            },
            {
                "node_id": "node_nv5_sheet",
                "node_type": "image",
                "node_name": "Nhân Vật 5 (NV5 Fashion 2K)",
                "pos_x": 100,
                "pos_y": 280,
                "enabled": True,
                "slug": "nv5_char",
                "slug_auto": True,
                "local_path": os.path.join(CHARS_DIR, "nv5_ref.png"),
                "ref_images": [{"local_path": os.path.join(CHARS_DIR, "nv5_ref.png")}],
            },
            {
                "node_id": "node_ai_prompt_deconstruct",
                "node_type": "prompt",
                "node_name": "Prompt AI (CLIProxy ChatGPT) - Tách Đồ 2K",
                "pos_x": 540,
                "pos_y": -140,
                "enabled": True,
                "slug": "prompt_deconstruct",
                "slug_auto": True,
                "prompt": (
                    "Ultra-clean commercial e-commerce deconstructed fashion outfit & accessories flat-lay product sheet "
                    "(vertical 4:5, 2048x2559 2K resolution) isolated on a seamless pure solid white background (#FFFFFF). "
                    "Left column: main upper garment and lower garment neatly laid flat with realistic 3D fabric volume and pleats from IMAGE 01. "
                    "Right column: 4 coordinated accessories isolated vertically (necklace, shoulder bag, crew socks, Mary Jane shoes)."
                ),
                "use_ai": True,
                "ai_provider": "cliproxy_gpt",
                "ai_model": "gpt-4o-mini",
                "ai_system_instruction": "Keep or refine this English fashion flat-lay prompt into a single ultra-detailed paragraph for image generation. Output ONLY the English prompt.",
                "ai_fallback": True,
            },
            {
                "node_id": "node_flow_flatlay_2k",
                "node_type": "generate",
                "provider": "flow",
                "node_name": "Flow - Ảnh Tách Quần Áo + Phụ Kiện 2K",
                "pos_x": 980,
                "pos_y": -140,
                "enabled": True,
                "slug": "flatlay_2k",
                "slug_auto": True,
                "media_type": "Image",
                "model": "Nano Banana 2.1",
                "quantity": 1,
                "ratio": "4:5",
                "download_resolution": "2k",
                "prompt_source": "upstream_node",
                "auto_download": True,
            },
            {
                "node_id": "node_prompt_tryon",
                "node_type": "prompt",
                "node_name": "Prompt - NV5 Mặc Bộ Đồ 2K",
                "pos_x": 980,
                "pos_y": 320,
                "enabled": True,
                "slug": "prompt_tryon",
                "slug_auto": True,
                "prompt": (
                    "Hyper-photorealistic vertical 9:16 2K full-body fashion lookbook video of the exact female model from IMAGE 01 (NV5) "
                    "wearing the exact deconstructed outfit and accessories from IMAGE 02. She poses gracefully in a modern studio, "
                    "turning slightly to showcase the garment drape, collar, bag, and shoes. Ultra-realistic fabric physics, 85mm lens."
                ),
                "use_ai": False,
            },
            {
                "node_id": "node_flow_lookbook_vid",
                "node_type": "generate",
                "provider": "flow",
                "node_name": "Flow - Video Lookbook NV5 (Omni 1.1 Flash)",
                "pos_x": 1440,
                "pos_y": 100,
                "enabled": True,
                "slug": "video_lookbook_nv5",
                "slug_auto": True,
                "media_type": "Video",
                "video_input_type": "Ingredients",
                "video_duration": "10s",
                "model": "Omni 1.1 Flash",
                "quantity": 1,
                "ratio": "9:16",
                "video_download_resolution": "1080p",
                "prompt_source": "upstream_node",
                "auto_download": True,
            },
        ],
        "edges": [
            {
                "edge_id": "e_raw_to_ai_prompt",
                "source_node_id": "node_raw_cloth",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_ai_prompt_deconstruct",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "e_raw_to_flatlay",
                "source_node_id": "node_raw_cloth",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_flow_flatlay_2k",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "e_aip_to_flatlay",
                "source_node_id": "node_ai_prompt_deconstruct",
                "source_handle": "output_1",
                "source_port": "text",
                "target_node_id": "node_flow_flatlay_2k",
                "target_handle": "input_2",
                "target_port": "text",
                "data_type": "text",
            },
            {
                "edge_id": "e_nv5_to_vid",
                "source_node_id": "node_nv5_sheet",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_flow_lookbook_vid",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "e_flatlay_to_vid",
                "source_node_id": "node_flow_flatlay_2k",
                "source_handle": "output_1",
                "source_port": "media",
                "target_node_id": "node_flow_lookbook_vid",
                "target_handle": "input_1",
                "target_port": "image_ref",
                "data_type": "image",
            },
            {
                "edge_id": "e_ptryon_to_vid",
                "source_node_id": "node_prompt_tryon",
                "source_handle": "output_1",
                "source_port": "text",
                "target_node_id": "node_flow_lookbook_vid",
                "target_handle": "input_2",
                "target_port": "text",
                "data_type": "text",
            },
        ],
    },
}


def ensure_default_workflows_saved():
    """Đảm bảo các Workflow mẫu chuẩn luôn có sẵn trong thư mục `WorkFlow/saved_workflows/`."""
    os.makedirs(SAVED_WORKFLOWS_DIR, exist_ok=True)
    defaults = [
        ELEVATOR_MIRROR_OUTFIT_CHECK_WF,
        FACTORY_2K_STANDARD_WF,
        CLIPROXY_HYBRID_FASHION_WF,
    ]
    for wf_doc in defaults:
        wf_id = wf_doc["id"]
        fp = os.path.join(SAVED_WORKFLOWS_DIR, f"{wf_id}.json")
        if not os.path.exists(fp):
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(wf_doc, f, ensure_ascii=False, indent=2)


# ==============================================================================
# 2. QUẢN LÝ LƯU / TẢI / NHẬP / XUẤT WORKFLOW JSON
# ==============================================================================

def normalize_workflow_document(raw_obj: dict, wf_id_hint: str = "") -> dict:
    """
    Chuẩn hóa mọi định dạng JSON Workflow (TobyFlow JSON `{"version": "1.0", "type": "workflow", "workflow": {...}}`,
    MuseFlow JSON `{"nodes": [...], "edges": [...]}`, hoặc raw object) về cấu trúc chuẩn thống nhất.
    """
    if not isinstance(raw_obj, dict):
        raise ValueError("Dữ liệu Workflow JSON không hợp lệ (phải là JSON Object).")

    if "workflow" in raw_obj and isinstance(raw_obj["workflow"], dict):
        wf_inner = dict(raw_obj["workflow"])
        version = str(raw_obj.get("version") or "1.0")
        wf_id = str(raw_obj.get("_wf_id") or raw_obj.get("id") or wf_inner.get("id") or wf_id_hint or f"wf_{int(time.time())}")
    else:
        wf_inner = dict(raw_obj)
        version = str(raw_obj.get("version") or "1.0")
        wf_id = str(raw_obj.get("_wf_id") or raw_obj.get("id") or wf_id_hint or f"wf_{int(time.time())}")

    wf_id = re.sub(r"[^a-zA-Z0-9_\-]+", "_", wf_id).strip("_") or f"wf_{int(time.time())}"
    settings = dict(wf_inner.get("settings") or {})
    settings.setdefault("parallel", True)
    settings.setdefault("max_parallel", 2)
    settings.setdefault("quantity", 1)
    settings.setdefault("delay_between_nodes", 3)
    settings.setdefault("timeout_per_node", 120)
    settings.setdefault("retry_on_error", 0)
    settings.setdefault("stop_on_error", True)

    nodes = []
    for idx, n in enumerate(wf_inner.get("nodes") or []):
        if not isinstance(n, dict):
            continue
        nd = dict(n)
        cfg = dict(nd.get("config") or {})
        # Hỗ trợ đồng thời cả 3 chuẩn: TobyFlow (`node_id`, `node_name`, `media_type`, `ratio`, `ref_images`),
        # UI (`id`, `label`, `config`), và MuseFlow (`id`, `type`, `title`, `x`, `y`)
        nd_id = str(nd.get("node_id") or nd.get("id") or f"node_{idx+1}_{uuid.uuid4().hex[:6]}")
        raw_type = str(nd.get("node_type") or nd.get("type") or "generate").strip()
        type_map = {
            "imageInput": "image",
            "generateImage": "generate",
            "generateVideo": "generate",
            "textNote": "note",
        }
        nd_type = type_map.get(raw_type, raw_type)
        nd_name = str(nd.get("label") or nd.get("node_name") or nd.get("title") or nd.get("name") or f"Node {idx+1}")
        nd["id"] = nd_id
        nd["node_id"] = nd_id
        nd["node_type"] = nd_type
        nd["label"] = nd_name
        nd["node_name"] = nd_name
        nd["pos_x"] = float(nd.get("pos_x") if nd.get("pos_x") is not None else (nd.get("x") or (idx * 380)))
        nd["pos_y"] = float(nd.get("pos_y") if nd.get("pos_y") is not None else (nd.get("y") or 0))
        nd["enabled"] = bool(nd.get("enabled", not cfg.get("disabled", False)))
        slug_val = str(cfg.get("slug") or nd.get("slug") or re.sub(r"[^a-z0-9_]+", "_", nd_name.lower()).strip("_") or f"node_{idx+1}")
        nd["slug"] = slug_val
        nd["slug_auto"] = bool(nd.get("slug_auto", True))

        if raw_type == "generateVideo" or str(cfg.get("mode") or "").lower() == "video":
            nd["media_type"] = "Video"
        elif raw_type == "generateImage" or str(cfg.get("mode") or "").lower() == "image":
            nd.setdefault("media_type", "Image")

        if nd_type in ("generate", "gpt_image", "grok_generate", "gemini_generate"):
            nd.setdefault("media_type", "Video" if str(cfg.get("mode") or "").lower() == "video" else "Image")
            if cfg.get("provider"):
                nd["provider"] = cfg["provider"]
            elif nd_type == "gpt_image":
                nd.setdefault("provider", "cliproxy_gpt")
            elif nd_type == "grok_generate":
                nd.setdefault("provider", "grok")
            elif nd_type == "gemini_generate":
                nd.setdefault("provider", "cliproxy_gemini")
            else:
                nd.setdefault("provider", "flow")

            if cfg.get("model"):
                nd["model"] = cfg["model"]
            elif nd_type == "gpt_image":
                nd.setdefault("model", "gpt-image-1")
            elif nd_type == "grok_generate":
                nd.setdefault("model", "grok-imagine-image")
            elif nd_type == "gemini_generate":
                nd.setdefault("model", "Nano Banana 2.1")
            else:
                nd.setdefault("model", "Omni 1.2 Flash" if nd.get("media_type") == "Video" else "Nano Banana 2.1")

            nd["ratio"] = str(cfg.get("aspect_ratio") or nd.get("ratio") or "9:16")
            nd["quantity"] = int(cfg.get("count") or nd.get("quantity") or 1)
            nd.setdefault("download_resolution", "2k")
            nd["video_download_resolution"] = str(cfg.get("resolution") or nd.get("video_download_resolution") or "1080p")
            nd["video_duration"] = str(cfg.get("duration") or nd.get("video_duration") or "8s")
            nd.setdefault("video_input_type", "Ingredients")
            if "use_own_prompt" in cfg:
                nd["prompt_source"] = "own" if cfg["use_own_prompt"] else "upstream_node"
            else:
                nd.setdefault("prompt_source", "upstream_node")
            if cfg.get("prompt"):
                nd["prompt"] = cfg["prompt"]

        # Đồng bộ ngược từ top-level vào `config` cho UI (tự động rebase đường dẫn tương đối theo WS_DIR khi sang máy mới)
        def _rebase_ws_path(p: str) -> str:
            s = str(p or "").strip()
            if not s or s.startswith(("http://", "https://", "/api/", "data:")):
                return s
            if os.path.exists(s):
                return s
            norm = s.replace("\\", "/")
            for anchor in ("WorkFlow/", "ảnh mẫu thumbnail/", "Template/", "flow_final_pipeline/", "data/"):
                idx_a = norm.find(anchor)
                if idx_a != -1:
                    cand = os.path.join(WS_DIR, *norm[idx_a:].split("/"))
                    if os.path.exists(cand):
                        return cand
            return s

        last_out = nd.get("last_output") or {}
        local_p = _rebase_ws_path(str(cfg.get("file_path") or nd.get("local_path") or ""))
        if not local_p and isinstance(nd.get("ref_images"), list) and nd["ref_images"]:
            first_ref = nd["ref_images"][0]
            if isinstance(first_ref, dict):
                local_p = _rebase_ws_path(str(first_ref.get("local_path") or first_ref.get("path") or first_ref.get("thumbnail") or ""))
            elif isinstance(first_ref, str):
                local_p = _rebase_ws_path(first_ref)
        if local_p:
            nd["local_path"] = local_p

        res_p = _rebase_ws_path(str(cfg.get("result_path") or last_out.get("primary_path") or local_p or ""))
        prompt_val = str(cfg.get("prompt") or nd.get("prompt") or cfg.get("text") or nd.get("text") or cfg.get("note") or "")
        if prompt_val:
            nd["prompt"] = prompt_val

        ref_img_list = [_rebase_ws_path(x) for x in (cfg.get("reference_images") or [])]
        if not ref_img_list and isinstance(nd.get("ref_images"), list):
            for ri in nd["ref_images"]:
                if isinstance(ri, dict):
                    p_ri = _rebase_ws_path(ri.get("local_path") or ri.get("path") or ri.get("thumbnail") or "")
                    if p_ri:
                        ref_img_list.append(p_ri)
                elif isinstance(ri, str) and ri:
                    ref_img_list.append(_rebase_ws_path(ri))

        raw_status = str(last_out.get("status") or cfg.get("status") or "")
        if raw_status == "running" and not res_p:
            raw_status = "idle"
        cfg.update({
            "slug": slug_val,
            "mode": "video" if str(nd.get("media_type") or "").lower() == "video" else "image",
            "provider": nd.get("provider") or "flow",
            "model": nd.get("model") or ("gpt-5.4" if nd_type == "prompt" else "Nano Banana 2.1"),
            "aspect_ratio": nd.get("ratio") or "9:16",
            "count": int(nd.get("quantity") or 1),
            "duration": nd.get("video_duration") or "8s",
            "resolution": nd.get("video_download_resolution") or "1080p",
            "use_own_prompt": (nd.get("prompt_source") == "own"),
            "prompt": prompt_val,
            "file_path": local_p,
            "result_path": res_p,
            "reference_images": ref_img_list,
            "auto_download": bool(cfg.get("auto_download", nd.get("auto_download", False))),
            "status": raw_status or ("done" if (res_p or nd_type in ("prompt", "text", "note")) else "idle"),
        })
        nd["config"] = cfg
        nodes.append(nd)

    edges = []
    for idx_e, e in enumerate(wf_inner.get("edges") or []):
        if not isinstance(e, dict):
            continue
        ed = dict(e)
        src_id = str(ed.get("source_node_id") or ed.get("from") or "")
        tgt_id = str(ed.get("target_node_id") or ed.get("to") or "")
        if not src_id or not tgt_id:
            continue
        src_port = str(ed.get("source_port") or ed.get("fromPort") or ("text" if ed.get("edge_type") == "text" else "media"))
        tgt_port = str(ed.get("target_port") or ed.get("toPort") or ("text" if (src_port == "text" or ed.get("target_handle") == "input_2" or ed.get("edge_type") == "text") else "image_ref"))
        tgt_handle = str(ed.get("target_handle") or ("input_2" if tgt_port == "text" else "input_1"))
        src_handle = str(ed.get("source_handle") or "output_1")
        dtype = str(ed.get("data_type") or ("text" if tgt_port == "text" else "image"))
        edge_type = "text" if tgt_handle == "input_2" else "image_ref"
        ed_id = str(ed.get("edge_id") or ed.get("id") or f"edge_{src_id}_{src_handle}_{tgt_id}_{tgt_handle}_{idx_e}")
        edges.append(
            {
                "edge_id": ed_id,
                "source_node_id": src_id,
                "source_handle": src_handle,
                "source_port": src_port,
                "target_node_id": tgt_id,
                "target_handle": tgt_handle,
                "target_port": tgt_port,
                "data_type": dtype,
                "edge_type": edge_type,
            }
        )

    raw_tl = wf_inner.get("timeline")
    if isinstance(raw_tl, list):
        norm_tl = list(raw_tl)
    elif isinstance(raw_tl, dict):
        norm_tl = list(raw_tl.get("clips") or [])
    else:
        norm_tl = []

    return {
        "id": wf_id,
        "_wf_id": wf_id,
        "version": version,
        "type": "workflow",
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "workflow": {
            "name": str(wf_inner.get("name") or wf_inner.get("title") or "Untitled Flow Workflow"),
            "description": str(wf_inner.get("description") or ""),
            "settings": settings,
            "nodes": nodes,
            "edges": edges,
            "groups": list(wf_inner.get("groups") or []),
            "notes": list(wf_inner.get("notes") or []),
            "timeline": norm_tl,
            "final_video_path": str(wf_inner.get("final_video_path") or ""),
            "batch_history": list(wf_inner.get("batch_history") or []),
        },
    }


def list_saved_workflows() -> list:
    ensure_default_workflows_saved()
    items = []
    for fn in sorted(os.listdir(SAVED_WORKFLOWS_DIR)):
        if not fn.lower().endswith(".json"):
            continue
        fp = os.path.join(SAVED_WORKFLOWS_DIR, fn)
        try:
            with open(fp, "r", encoding="utf-8") as f:
                doc = normalize_workflow_document(json.load(f), wf_id_hint=os.path.splitext(fn)[0])
                doc["run_state"] = _WORKFLOW_RUN_STATE.get(doc["id"], {"status": "idle", "node_states": {}})
                items.append(doc)
        except Exception:
            pass
    return items


def get_workflow_by_id(wf_id: str) -> dict:
    items = list_saved_workflows()
    for it in items:
        if it.get("id") == wf_id or it.get("_wf_id") == wf_id:
            return it
    return items[0] if items else {}


def save_workflow_document(raw_obj: dict, wf_id: str = "", wf_id_slug: str = "") -> dict:
    ensure_default_workflows_saved()
    hint = wf_id or wf_id_slug or ""
    doc = normalize_workflow_document(raw_obj, wf_id_hint=hint)
    fp = os.path.join(SAVED_WORKFLOWS_DIR, f"{doc['id']}.json")
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    doc["run_state"] = _WORKFLOW_RUN_STATE.get(doc["id"], {"status": "idle", "node_states": {}})
    doc["ok"] = True
    doc["file_path"] = fp
    return doc


def delete_saved_workflow(wf_id: str) -> dict:
    clean_id = re.sub(r"[^a-zA-Z0-9_\-]+", "_", str(wf_id or "")).strip("_")
    fp = os.path.join(SAVED_WORKFLOWS_DIR, f"{clean_id}.json")
    if os.path.exists(fp):
        os.remove(fp)
    return {"ok": True, "deleted_id": clean_id}


# ==============================================================================
# 3. CÁC HÀM HỖ TRỢ GIẢI QUYẾT MEDIA, CLIPROXY AI (CHATGPT / GEMINI / GROK) & GOOGLE FLOW
# ==============================================================================

def _resolve_node_reference_media_path(ref_entry, wf_out_dir: str, node_id: str, idx: int = 0) -> str:
    """
    Chuyển đổi 1 mục `ref_images` (có thể chứa `local_path`, `path`, `url`, `thumbnail` dạng http/https hoặc `/api/media?path=...`)
    thành đường dẫn file thật trên ổ cứng để upload lên Google Flow hoặc gửi vào CLIProxy Vision.
    """
    if isinstance(ref_entry, str):
        ref_entry = {"path": ref_entry}
    if not isinstance(ref_entry, dict):
        return ""

    for k in ("local_path", "path", "file_path"):
        cand = str(ref_entry.get(k) or "").strip()
        if cand:
            if cand.startswith("/api/media?"):
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(cand).query)
                cand = (qs.get("path") or [""])[0]
            if not os.path.isabs(cand):
                cand_abs = os.path.join(WS_DIR, cand)
            else:
                cand_abs = cand
            if os.path.exists(cand_abs):
                return cand_abs

    # Nếu có URL http/https trong `thumbnail` hoặc `url`, thử tải về thư mục cache của workflow
    url_val = str(ref_entry.get("url") or ref_entry.get("thumbnail") or "").strip()
    if url_val.startswith("/api/media?"):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(url_val).query)
        p_q = (qs.get("path") or [""])[0]
        if p_q:
            cand_abs = p_q if os.path.isabs(p_q) else os.path.join(WS_DIR, p_q)
            if os.path.exists(cand_abs):
                return cand_abs

    if url_val.startswith(("http://", "https://")):
        ext = os.path.splitext(urllib.parse.urlparse(url_val).path)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".mp4"):
            ext = ".jpg"
        cached_file = os.path.join(wf_out_dir, f"cached_{node_id}_{idx}{ext}")
        if os.path.exists(cached_file) and os.path.getsize(cached_file) > 500:
            return cached_file
        try:
            req = urllib.request.Request(
                url_val,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/134.0.0.0 Safari/537.36"},
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read()
                if len(raw) > 500:
                    os.makedirs(wf_out_dir, exist_ok=True)
                    with open(cached_file, "wb") as f:
                        f.write(raw)
                    return cached_file
        except Exception:
            pass

    # Fallback thông minh: Nếu URL ngoài (như labs.toby.vn) không truy cập được và node là Image/Outfit
    fallback_char = os.path.join(CHARS_DIR, "nv5_bedroom_2k.png")
    fallback_outfit = os.path.join(DEMO_2K_DIR, "05_Product_Sheet_Quan_Sooc_Trang_2K.png")
    if "outfit" in str(node_id).lower() and os.path.exists(fallback_outfit):
        return fallback_outfit
    if os.path.exists(fallback_char):
        return fallback_char
    return ""


def call_cliproxy_chat_or_vision(
    prompt_text: str,
    image_paths: list = None,
    model_name: str = "gpt-4o-mini",
    system_instruction: str = "",
    timeout_sec: int = 60,
) -> tuple:
    """
    Gửi Prompt (kèm các ảnh tham chiếu nếu có) qua CLIProxy (`http://127.0.0.1:8317/v1/chat/completions`)
    hỗ trợ cả ChatGPT (`gpt-4o`, `gpt-4o-mini`), Gemini (`gemini-2.5-flash`, `gemini-2.5-pro`) và Grok (`grok-3`).
    Trả về `(ok: bool, output_text: str, error_str: str)`.
    """
    url = "http://127.0.0.1:8317/v1/chat/completions"
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})

    user_content = []
    for ip in (image_paths or [])[:4]:
        if ip and os.path.exists(ip):
            try:
                raw = open(ip, "rb").read()
                b64 = base64.b64encode(raw).decode("ascii")
                mime = "image/png" if ip.lower().endswith(".png") else "image/jpeg"
                user_content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
            except Exception:
                pass
    user_content.append({"type": "text", "text": prompt_text})
    messages.append({"role": "user", "content": user_content if len(user_content) > 1 else prompt_text})

    payload = json.dumps(
        {
            "model": model_name or "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.6,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-cliproxy-local",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=max(15, int(timeout_sec or 60))) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            choices = data.get("choices") or []
            if choices:
                txt = ((choices[0].get("message") or {}).get("content") or "").strip()
                if txt:
                    return True, txt, None
            return False, "", f"CLIProxy phản hồi rỗng: {str(data)[:200]}"
    except Exception as e:
        return False, "", str(e)


def call_cliproxy_image_generation(prompt_text: str, out_file: str, model_name: str = "gpt-image-1", ratio: str = "9:16") -> tuple:
    """
    Thử gọi tạo ảnh qua CLIProxy (`/v1/images/generations`) cho các node `GPT Image 2` / `Grok Image`.
    Nếu CLIProxy không bật endpoint tạo ảnh trực tiếp, trả về `(False, ...)` để Engine tự động chuyển sang Google Flow Nano Banana 2.1 2K!
    """
    url = "http://127.0.0.1:8317/v1/images/generations"
    size_str = "1024x1792" if ratio in ("9:16", "4:5", "3:4") else ("1792x1024" if ratio == "16:9" else "1024x1024")
    payload = json.dumps(
        {
            "model": model_name or "gpt-image-1",
            "prompt": prompt_text,
            "n": 1,
            "size": size_str,
            "response_format": "b64_json",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-cliproxy-local",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            arr = data.get("data") or []
            if arr:
                b64 = arr[0].get("b64_json")
                img_url = arr[0].get("url")
                if b64:
                    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
                    with open(out_file, "wb") as f:
                        f.write(base64.b64decode(b64))
                    return True, out_file, None
                if img_url:
                    with urllib.request.urlopen(img_url, timeout=30) as r_img:
                        os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
                        with open(out_file, "wb") as f:
                            f.write(r_img.read())
                    return True, out_file, None
    except Exception as e:
        return False, "", str(e)
    return False, "", "CLIProxy image endpoint returned no image"


# ==============================================================================
# 4. THỰC THI NODE GENERATE TRÊN GOOGLE FLOW (NANO BANANA 2.1 2K / OMNI 1.1 FLASH / VEO 3.1)
# ==============================================================================

import threading

_PROFILE_LOCKS = {}
_PROFILE_LOCK_GUARD = threading.Lock()


def _get_profile_lock(prof_key: str) -> threading.Lock:
    with _PROFILE_LOCK_GUARD:
        if prof_key not in _PROFILE_LOCKS:
            _PROFILE_LOCKS[prof_key] = threading.Lock()
        return _PROFILE_LOCKS[prof_key]


def _resolve_account_and_project_id(requested_prof: str, gvt_mod) -> tuple:
    """
    Trả về `(prof_name, project_id)` từ `Flow_nhieu_worker_accounts.json`.
    Nếu đang chạy song song và profile mặc định đang bận mở trình duyệt, tự động luân chuyển sang tài khoản rảnh (`capcutpro` / `leviettung04`).
    """
    acc_path = os.path.join(WS_DIR, "data", "google_flow_grok", "Flow_nhieu_worker_accounts.json")
    accounts = []
    if os.path.exists(acc_path):
        try:
            with open(acc_path, "r", encoding="utf-8") as f:
                raw_accs = json.load(f)
            if isinstance(raw_accs, list):
                for a in raw_accs:
                    if isinstance(a, dict) and not a.get("is_grok") and a.get("status") == "ready":
                        p_dir = str(a.get("profile_dir") or "")
                        p_name = os.path.basename(p_dir.rstrip("\\/")) or str(a.get("email") or "").split("@")[0]
                        proj_id = str(a.get("project_id") or gvt_mod.DEFAULT_PROJECT_ID)
                        if p_name:
                            accounts.append((p_name, proj_id))
        except Exception:
            pass
    if not accounts:
        accounts = [("leviettung04", gvt_mod.DEFAULT_PROJECT_ID)]

    req = (requested_prof or "").strip()
    if req:
        for p_name, proj_id in accounts:
            if p_name == req or req.startswith(p_name):
                # Nếu có nhiều tài khoản và tài khoản này đang khóa trình duyệt, ưu tiên tài khoản rảnh
                if _get_profile_lock(p_name).locked() and len(accounts) > 1:
                    for alt_p, alt_proj in accounts:
                        if not _get_profile_lock(alt_p).locked():
                            return alt_p, alt_proj
                return p_name, proj_id
        return req, gvt_mod.DEFAULT_PROJECT_ID

    for p_name, proj_id in accounts:
        if not _get_profile_lock(p_name).locked():
            return p_name, proj_id
    return accounts[0]


def execute_flow_generation_node(
    node: dict,
    prompt_text: str,
    ref_media_paths: list,
    wf_out_dir: str,
    profile_name: str = "",
) -> dict:
    """
    Thực thi 1 Node `generate` (`Flow - Image/Video Generate`, hoặc fallback cho `GPT Image 2` / `Grok` / `Gemini`)
    trực tiếp trên Google Flow:
      - Nếu `media_type == "Image"`:
        + Upload tất cả ảnh tham chiếu (`IMAGE 01`, `IMAGE 02`, ...) qua `maseQ`.
        + Gọi `ogiZ0b` (`Nano Banana 2.1` / `Nano Banana Pro` / `Nano Banana 2 Lite`).
        + Tải ảnh 2K (`SPrCad`) nếu `download_resolution == "2k"` (mặc định nâng lên 2K để nét căng!).
      - Nếu `media_type == "Video"`:
        + Hỗ trợ `Omni 1.1 Flash` (`abra_r2v_10s` / `8s` / `6s` qua `MZZa6b` cho `Ingredients`, hoặc `abra_edit` `jIps6` nếu có video ref)
          và `Veo 3.1 - Fast` / `Veo 3.1 - Quality`.
        + Poll `as29s`, upscale `1080p` (`p0UkFb`) nếu cấu hình `1080p`, và tải file `.mp4` về `wf_out_dir`.
    """
    import grok_video_tool as gvt
    from google_flow_auth import profile_paths
    from playwright.sync_api import sync_playwright
    from run_all_7_videos_mt import (
        upload_single_product_ref_in_page,
        generate_variant_ref_image_in_page,
        submit_upsample_1080p_in_page,
        poll_and_download_one,
    )
    from fashion_motion_control_engine import ensure_image_is_2k

    node_id = node["node_id"]
    media_type = str(node.get("media_type") or "Image").strip().capitalize()
    model_label = str(node.get("model") or ("Omni 1.2 Flash" if media_type == "Video" else "Nano Banana 2.1")).strip()
    ratio = str(node.get("ratio") or "9:16").strip()
    vid_res = str(node.get("video_download_resolution") or "1080p").strip().lower()
    vid_dur_str = str(node.get("video_duration") or "10s").strip().lower().replace("s", "")
    vid_dur = int(vid_dur_str) if vid_dur_str.isdigit() else 10

    req_prof = (profile_name or node.get("profile_name") or "").strip()
    prof, flow_project_id = _resolve_account_and_project_id(req_prof, gvt)
    shared_dir = gvt._resolve_flow_shared_dir(prof)
    profile_dir, _ = profile_paths(shared_dir, prof)
    cookie_hdr = gvt._load_flow_cookie_header(prof)
    if not cookie_hdr:
        return {"ok": False, "error": f"Tài khoản Google Flow '{prof}' chưa có Cookie đăng nhập hợp lệ."}

    dl_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Cookie": cookie_hdr,
    }

    valid_img_refs = [p for p in (ref_media_paths or []) if p and os.path.exists(p) and not p.lower().endswith((".mp4", ".mov", ".webm"))]
    valid_vid_refs = [p for p in (ref_media_paths or []) if p and os.path.exists(p) and p.lower().endswith((".mp4", ".mov", ".webm"))]

    prof_lock = _get_profile_lock(prof)

    # ------------------------------------------------------------------
    # TRƯỜNG HỢP A: TẠO ẢNH 2K (Flow - Images Generate: Nano Banana 2.1 / Pro)
    # ------------------------------------------------------------------
    if media_type != "Video":
        out_img_path = os.path.join(wf_out_dir, f"{node_id}_{int(time.time())}_2K.jpg")
        with prof_lock:
            with sync_playwright() as pw:
                browser = pw.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    channel="chrome",
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--mute-audio"],
                )
                try:
                    page = browser.pages[0] if browser.pages else browser.new_page()
                    page.add_init_script(gvt._RECAPTCHA_BYPASS_INIT_SCRIPT)
                    page.goto(f"https://flow.google.com/project/{flow_project_id}", wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(3500)

                    wiz = page.evaluate(
                        """() => {
                            const w = window.WIZ_global_data || {};
                            return {
                                at: w.SNlM0e || '',
                                bl: w.cfb2h || 'boq_labs-ai-sandbox-frontend_20261030.00_p2',
                                fsid: w.FdrFJe || '',
                                ua: navigator.userAgent
                            };
                        }"""
                    )
                    if not wiz.get("at"):
                        return {"ok": False, "error": f"Phiên đăng nhập Google Flow của '{prof}' đã hết hạn (thiếu SNlM0e)."}

                    uploaded_img_uuids = []
                    for rp in valid_img_refs[:5]:
                        ok_u, u_id, _ = upload_single_product_ref_in_page(page, wiz, flow_project_id, rp, quality=98)
                        if ok_u and u_id:
                            uploaded_img_uuids.append(u_id)

                    primary_uuid = uploaded_img_uuids[0] if uploaded_img_uuids else None
                    extra_uuids = uploaded_img_uuids[1:] if len(uploaded_img_uuids) > 1 else []
                    ref_task = {
                        "pid": "workflow",
                        "v_key": node_id,
                        "project_id": flow_project_id,
                        "char_id": primary_uuid,
                        "prod_uuids": extra_uuids,
                        "allow_multi_refs": True,
                        "prompt_str": prompt_text or "Ultra-realistic commercial fashion photography, 2K resolution.",
                        "out_file": out_img_path,
                    }
                    ok_gen, media_uuid_2k, err_gen = generate_variant_ref_image_in_page(
                        page, wiz, cookie_hdr, dl_headers, ref_task
                    )
                    if not ok_gen:
                        return {"ok": False, "error": f"Tạo ảnh trên Google Flow thất bại: {err_gen}"}
                finally:
                    browser.close()

        info_2k = ensure_image_is_2k(out_img_path)
        if node.get("auto_download"):
            dl_copy = os.path.join(FINAL_VIDEOS_DIR, os.path.basename(out_img_path))
            try:
                shutil.copy2(out_img_path, dl_copy)
            except Exception:
                pass
        return {
            "ok": True,
            "media_type": "image",
            "media_paths": [out_img_path],
            "primary_path": out_img_path,
            "flow_media_uuid": media_uuid_2k,
            "width": info_2k.get("width", 1536),
            "height": info_2k.get("height", 2752),
            "prompt_used": prompt_text,
            "account_used": prof,
        }

    # ------------------------------------------------------------------
    # TRƯỜNG HỢP B: TẠO VIDEO (Flow - Videos Generate: Omni 1.1 Flash / Veo 3.1)
    # ------------------------------------------------------------------
    out_vid_path = os.path.join(wf_out_dir, f"{node_id}_{int(time.time())}.mp4")
    job_uuid = None
    wiz = None
    ok_sub = False
    err_sub = None

    with prof_lock:
        with sync_playwright() as pw:
            browser = pw.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                channel="chrome",
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--mute-audio"],
            )
            try:
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.add_init_script(gvt._RECAPTCHA_BYPASS_INIT_SCRIPT)
                page.goto(f"https://flow.google.com/project/{flow_project_id}", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3500)

                wiz = page.evaluate(
                    """() => {
                        const w = window.WIZ_global_data || {};
                        return {
                            at: w.SNlM0e || '',
                            bl: w.cfb2h || 'boq_labs-ai-sandbox-frontend_20261030.00_p2',
                            fsid: w.FdrFJe || '',
                            ua: navigator.userAgent
                        };
                    }"""
                )
                if not wiz.get("at"):
                    return {"ok": False, "error": f"Phiên đăng nhập Google Flow của '{prof}' đã hết hạn (thiếu SNlM0e)."}

                uploaded_img_uuids = []
                for rp in valid_img_refs[:5]:
                    ok_u, u_id, _ = upload_single_product_ref_in_page(page, wiz, flow_project_id, rp, quality=98)
                    if ok_u and u_id:
                        uploaded_img_uuids.append(u_id)

                if valid_vid_refs:
                    from fashion_motion_control_engine import (
                        upload_reference_video_in_page,
                        submit_fashion_motion_scene_in_page,
                    )
                    ok_vr, vr_uuid, _, err_vr = upload_reference_video_in_page(page, wiz, flow_project_id, valid_vid_refs[0])
                    if ok_vr and vr_uuid:
                        ok_sub, job_uuid, err_sub = submit_fashion_motion_scene_in_page(
                            page,
                            wiz,
                            {
                                "project_id": flow_project_id,
                                "ref_video_uuid": vr_uuid,
                                "duration": vid_dur,
                                "fps": 24,
                                "start_frame": 0,
                                "end_frame": vid_dur * 24,
                                "image_ref_uuids": uploaded_img_uuids,
                                "asset_uuid_map": {},
                                "segments_spec": [{"type": "text", "text": prompt_text}],
                                "display_prompt": prompt_text,
                                "model_key": "macaron_cookie_edit" if ("1.2" in str(node.get("model") or "").lower() or "macaron" in str(node.get("model") or "").lower()) else "abra_edit",
                            },
                        )

                if not ok_sub:
                    # Gửi lệnh tạo video Ingredients (IMAGE 01, IMAGE 02, ...) qua RPC `MZZa6b` (`abra_r2v_10s` / `8s` / `6s`)
                    dur_clamped = 10 if vid_dur >= 9 else (6 if vid_dur <= 6 else 8)
                    flow_vid_model = f"abra_r2v_{dur_clamped}s"
                    rcap = page.evaluate(
                        """async () => {
                            const fn = window.__realGrecaptchaExecute || window.grecaptcha.enterprise.execute.bind(window.grecaptcha.enterprise);
                            return await fn('6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV', {action: 'VIDEO_GENERATION'});
                        }"""
                    )
                    wf_uuid = str(uuid.uuid4())
                    m_uuid = str(uuid.uuid4())
                    b_uuid = str(uuid.uuid4())
                    aspect_int = 2 if ratio == "16:9" else 1
                    h_prompt = [None, None, [[[prompt_text]]]]
                    l_item = [None, None, None, None, m_uuid, wf_uuid]
                    ref_list = [[None, u] for u in uploaded_img_uuids]
                    voice_id = str(node.get("voice_id") or "").strip()
                    if voice_id:
                        try:
                            import character_library_manager as _clm_wf
                            voice_id = _clm_wf.resolve_voice_id_for_account(voice_id, prof)
                        except Exception:
                            pass
                    voice_list = [[voice_id]] if voice_id else []
                    item_g = [
                        h_prompt,
                        ref_list,
                        flow_vid_model,
                        aspect_int,
                        None,
                        l_item,
                        None,
                        voice_list,
                        None,
                        [],
                        [],
                    ]
                    k_ctx = [None, 22, None, None, None, flow_project_id, None, None, None, None, [rcap, 1]]
                    payload_v = [[item_g], k_ctx, [b_uuid, 1]]
                    f_req_str = json.dumps(
                        [[["MZZa6b", json.dumps(payload_v, separators=(",", ":")), None, "generic"]]],
                        separators=(",", ":"),
                    )
                    resp_obj = page.evaluate(
                        """async ({projectId, bl, fsid, fReq, at}) => {
                            const sp = `/project/${projectId}`;
                            const reqid = Math.floor(Math.random() * 800000) + 100000;
                            const url = `/_/AiSandboxAngularFrontend/data/batchexecute?rpcids=MZZa6b&source-path=${encodeURIComponent(sp)}&bl=${encodeURIComponent(bl)}&f.sid=${encodeURIComponent(fsid)}&hl=vi&_reqid=${reqid}&rt=c`;
                            const body = `f.req=${encodeURIComponent(fReq)}&at=${encodeURIComponent(at)}&`;
                            const r = await fetch(url, {
                                method: 'POST',
                                headers: {
                                    'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                                    'x-same-domain': '1'
                                },
                                body
                            });
                            return {status: r.status, text: await r.text()};
                        }""",
                        {
                            "projectId": flow_project_id,
                            "bl": wiz["bl"],
                            "fsid": str(wiz["fsid"]),
                            "fReq": f_req_str,
                            "at": wiz["at"],
                        },
                    )
                    ok_v, inner_v, err_v = gvt._parse_batchexecute_wrb((resp_obj or {}).get("text", ""), "MZZa6b")
                    if ok_v and isinstance(inner_v, list):
                        job_uuid = m_uuid
                        try:
                            if len(inner_v) > 3 and isinstance(inner_v[3], list) and inner_v[3]:
                                cand_u = inner_v[3][0][0]
                                if isinstance(cand_u, str) and len(cand_u) >= 32:
                                    job_uuid = cand_u
                        except Exception:
                            pass
                        ok_sub, err_sub = True, None
                    else:
                        ok_sub, err_sub = False, f"MZZa6b: {err_v}"
            finally:
                browser.close()

    if not ok_sub or not job_uuid:
        return {"ok": False, "error": f"Gửi lệnh tạo video thất bại: {err_sub}"}

    # Poll kết quả tạo video (không giữ khóa trình duyệt trong lúc chờ render!) & Upscale 1080p nếu được chọn
    stage = "base_720p"
    poll_uid = job_uuid
    want_1080p = vid_res == "1080p"
    start_t = time.time()
    while (time.time() - start_t) < 420:
        time.sleep(8)
        st_res, _ = poll_and_download_one(
            cookie_hdr,
            wiz,
            dl_headers,
            {
                "cookie_hdr": cookie_hdr,
                "wiz": wiz,
                "dl_headers": dl_headers,
                "media_uuid": poll_uid,
                "project_id": flow_project_id,
                "out_mp4": out_vid_path,
                "stage": stage,
            },
        )
        if st_res == "ready_for_1080p":
            if want_1080p:
                ok_up, up_uid = False, None
                try:
                    with prof_lock:
                        with sync_playwright() as pw_up:
                            br_up = pw_up.chromium.launch_persistent_context(
                                user_data_dir=str(profile_dir),
                                channel="chrome",
                                headless=True,
                                args=["--disable-blink-features=AutomationControlled", "--mute-audio"],
                            )
                            try:
                                pg_up = br_up.pages[0] if br_up.pages else br_up.new_page()
                                pg_up.add_init_script(gvt._RECAPTCHA_BYPASS_INIT_SCRIPT)
                                pg_up.goto(f"https://flow.google.com/project/{flow_project_id}", wait_until="domcontentloaded", timeout=60000)
                                pg_up.wait_for_timeout(3000)
                                ok_up, up_uid, _ = submit_upsample_1080p_in_page(
                                    pg_up,
                                    wiz,
                                    {
                                        "pid": "workflow",
                                        "sc": {"id": node_id},
                                        "project_id": flow_project_id,
                                        "base_video_uuid": job_uuid,
                                    },
                                )
                            finally:
                                br_up.close()
                except Exception:
                    ok_up = False
                if ok_up and up_uid:
                    poll_uid = up_uid
                    stage = "upsample_1080p"
                    continue
            if os.path.exists(out_vid_path + ".720p.tmp"):
                shutil.move(out_vid_path + ".720p.tmp", out_vid_path)
            break
        elif st_res == "done":
            break
        elif str(st_res).startswith("failed"):
            return {"ok": False, "error": f"Google Flow báo lỗi khi render video: {st_res}"}

    if not os.path.exists(out_vid_path) and os.path.exists(out_vid_path + ".720p.tmp"):
        shutil.move(out_vid_path + ".720p.tmp", out_vid_path)

    if not os.path.exists(out_vid_path):
        return {"ok": False, "error": "Hết thời gian chờ (timeout) mà video chưa tải xong."}

    if node.get("auto_download"):
        dl_copy = os.path.join(FINAL_VIDEOS_DIR, os.path.basename(out_vid_path))
        try:
            shutil.copy2(out_vid_path, dl_copy)
        except Exception:
            pass

    return {
        "ok": True,
        "media_type": "video",
        "media_paths": [out_vid_path],
        "primary_path": out_vid_path,
        "flow_job_uuid": poll_uid,
        "prompt_used": prompt_text,
        "account_used": prof,
    }


# ==============================================================================
# 5. BỘ THỰC THI ĐỒ THỊ NODE (DAG TOPOLOGICAL ENGINE & SINGLE NODE RUNNER)
# ==============================================================================

def _sort_incoming_image_edges(edges_in: list, nodes_by_id: dict) -> list:
    """
    Sắp xếp các dây nối `image_ref` đi vào 1 node theo thứ tự hợp lý nhất để khớp với `IMAGE 01`, `IMAGE 02` trong Prompt:
      1. Nếu 1 trong các nguồn là node `generate` (ảnh trung gian vừa tạo ra, như `Flow - Images Generate`) và nguồn kia là `Outfit`:
         đưa ảnh của `Flow - Images Generate` (hoặc `Image` nhân vật gốc) lên làm `IMAGE 01`, và `Outfit` làm `IMAGE 02`!
      2. Nếu cùng loại node (`image`), sắp xếp theo tọa độ `pos_y` từ trên xuống dưới (như `Image` ở y=-371 đứng trước `Outfit` ở y=340).
    """
    def _edge_priority(e):
        src_node = nodes_by_id.get(e.get("source_node_id") or "", {})
        n_name = str(src_node.get("node_name") or "").lower()
        n_slug = str(src_node.get("slug") or "").lower()
        n_type = str(src_node.get("node_type") or "").lower()
        pos_y = float(src_node.get("pos_y") or 0.0)
        # Outfit luôn đứng ở vị trí IMAGE 02 (group = 1), còn Image nhân vật gốc hoặc Flow - Images Generate đứng ở vị trí IMAGE 01 (group = 0)
        is_outfit = 1 if ("outfit" in n_name or "image_2" in n_slug or "sp" in n_name or "product" in n_name) else 0
        is_gen = 0 if n_type == "generate" else 1
        return (is_outfit, is_gen, pos_y)

    return sorted(edges_in, key=_edge_priority)


def _interpolate_slugs_in_text(raw_text: str, nodes_by_id: dict, node_outputs: dict) -> str:
    """Thay thế `@slug` trong câu lệnh bằng văn bản kết quả của node có `slug` tương ứng."""
    if not raw_text or "@" not in raw_text:
        return raw_text
    slug_to_text = {}
    for nid, nd in nodes_by_id.items():
        sl = str(nd.get("slug") or "").strip()
        out = node_outputs.get(nid) or {}
        if sl and out.get("text"):
            slug_to_text[sl] = str(out["text"])
    def _repl(m):
        key = m.group(1)
        return slug_to_text.get(key, m.group(0))
    return re.sub(r"@([a-zA-Z0-9_\-]+)", _repl, raw_text)


def execute_single_node_in_context(
    node: dict,
    nodes_by_id: dict,
    edges: list,
    node_outputs: dict,
    wf_out_dir: str,
    profile_name: str = "",
) -> dict:
    """Thực thi đúng 1 Node dựa trên các dữ liệu đầu vào đã nối dây từ các Node đứng trước (`node_outputs`)."""
    if not node.get("enabled", True):
        return {"ok": True, "skipped": True, "status": "skipped", "message": "Node đang tắt (disabled)."}

    nid = node["node_id"]
    ntype = str(node.get("node_type") or "generate").strip().lower()

    # Tìm tất cả các dây nối đi vào node này
    in_edges = [e for e in edges if e.get("target_node_id") == nid]
    img_edges = _sort_incoming_image_edges(
        [e for e in in_edges if e.get("target_port") in ("image_ref", "media") or e.get("target_handle") == "input_1"],
        nodes_by_id,
    )
    txt_edges = [e for e in in_edges if e.get("target_port") == "text" or e.get("target_handle") == "input_2"]

    upstream_media_paths = []
    for ie in img_edges:
        src_out = node_outputs.get(ie.get("source_node_id") or "") or {}
        for mp in src_out.get("media_paths") or []:
            if mp and mp not in upstream_media_paths:
                upstream_media_paths.append(mp)

    # Cũng lấy thêm `ref_images` hoặc `local_path` gắn trực tiếp trên bản thân node
    own_media_paths = []
    if node.get("local_path"):
        p_own = _resolve_node_reference_media_path({"local_path": node.get("local_path")}, wf_out_dir, nid, 0)
        if p_own:
            own_media_paths.append(p_own)
    for idx_r, r_item in enumerate(node.get("ref_images") or []):
        p_r = _resolve_node_reference_media_path(r_item, wf_out_dir, nid, idx_r + 1)
        if p_r and p_r not in own_media_paths:
            own_media_paths.append(p_r)

    upstream_texts = []
    for te in txt_edges:
        src_out = node_outputs.get(te.get("source_node_id") or "") or {}
        t_val = str(src_out.get("text") or "").strip()
        if t_val:
            upstream_texts.append(t_val)

    # 1. Node `note`
    if ntype == "note":
        return {"ok": True, "status": "done", "text": str(node.get("text") or node.get("prompt") or "")}

    # 2. Node `image` / `video` / `references` / `preview`
    if ntype in ("image", "video", "references", "preview"):
        all_m = own_media_paths + [p for p in upstream_media_paths if p not in own_media_paths]
        if not all_m and ntype not in ("references", "preview"):
            return {"ok": False, "status": "error", "error": f"Node '{node.get('node_name')}' chưa có ảnh/video tham chiếu."}
        return {
            "ok": True,
            "status": "done",
            "media_type": "video" if ntype == "video" else "image",
            "media_paths": all_m,
            "primary_path": all_m[0] if all_m else "",
            "media_url": f"/api/media?path={urllib.parse.quote(all_m[0])}" if all_m else "",
        }

    # 3. Node `text`, `negativeprompt`, `textappend`, `textconcat` (Text Merge / Append / Negative)
    if ntype in ("text", "negativeprompt", "negative_prompt", "textappend", "text_append", "textconcat", "text_concat"):
        cfg = node.get("config") or {}
        raw_t = str(cfg.get("prompt") or cfg.get("text") or node.get("text") or node.get("prompt") or "")
        final_t = _interpolate_slugs_in_text(raw_t, nodes_by_id, node_outputs)
        if ntype in ("textconcat", "text_concat"):
            sep = str(cfg.get("separator") or node.get("separator") or ", ")
            parts = [t for t in upstream_texts if t.strip()]
            if final_t.strip():
                parts.append(final_t.strip())
            final_t = sep.join(parts)
        elif ntype in ("textappend", "text_append"):
            parts = [t for t in upstream_texts if t.strip()]
            if final_t.strip():
                parts.append(final_t.strip())
            final_t = " ".join(parts)
        elif upstream_texts and not raw_t:
            final_t = "\n\n".join(upstream_texts)
        return {"ok": True, "status": "done", "text": final_t}

    # 4. Node `text_extract` (Pure Regex / JSON / Marker Extractor)
    if ntype == "text_extract":
        src_t = "\n\n".join(upstream_texts) or str(node.get("text") or "")
        pattern = str(node.get("regex") or node.get("pattern") or "").strip()
        extracted = src_t
        if pattern:
            try:
                m = re.search(pattern, src_t, flags=re.DOTALL | re.MULTILINE)
                if m:
                    extracted = m.group(1) if m.groups() else m.group(0)
            except Exception:
                pass
        return {"ok": True, "status": "done", "text": extracted.strip()}

    # 5. Node `prompt` (Prompt Node — Static or AI CLIProxy ChatGPT/Gemini)
    if ntype == "prompt":
        own_p = str(node.get("prompt") or node.get("text") or "").strip()
        base_prompt = _interpolate_slugs_in_text(own_p, nodes_by_id, node_outputs)
        if upstream_texts:
            base_prompt = (base_prompt + "\n\n" + "\n\n".join(upstream_texts)).strip() if base_prompt else "\n\n".join(upstream_texts)

        if bool(node.get("use_ai", False)):
            ai_model = str(node.get("ai_model") or "gpt-4o-mini").strip()
            sys_inst = str(node.get("ai_system_instruction") or "You are an expert AI video & fashion prompt engineer. Refine or respond to the user's request clearly.").strip()
            ok_ai, ai_txt, err_ai = call_cliproxy_chat_or_vision(
                prompt_text=base_prompt,
                image_paths=upstream_media_paths + own_media_paths,
                model_name=ai_model,
                system_instruction=sys_inst,
                timeout_sec=int(node.get("timeout_sec") or 60),
            )
            if ok_ai and ai_txt:
                return {"ok": True, "status": "done", "text": ai_txt, "ai_used": True, "ai_model": ai_model}
            if not node.get("ai_fallback", True):
                return {"ok": False, "status": "error", "error": f"CLIProxy AI lỗi: {err_ai}"}
        return {"ok": True, "status": "done", "text": base_prompt, "ai_used": False}

    # 6. Node `auto_download`
    if ntype == "auto_download":
        copied = []
        for mp in upstream_media_paths:
            if os.path.exists(mp):
                dst = os.path.join(FINAL_VIDEOS_DIR, os.path.basename(mp))
                try:
                    shutil.copy2(mp, dst)
                    copied.append(dst)
                except Exception:
                    copied.append(mp)
        return {
            "ok": True,
            "status": "done",
            "media_paths": copied or upstream_media_paths,
            "primary_path": (copied or upstream_media_paths or [""])[0],
            "message": f"Đã tự động lưu {len(copied)} file vào final_videos/",
        }

    # 7. Các Node Tạo Ảnh / Video (`generate`, `gpt_image`, `grok_generate`, `gemini_generate`)
    use_own = bool(node.get("use_own_prompt", False)) or (node.get("prompt_source") == "own_prompt")
    own_p = _interpolate_slugs_in_text(str(node.get("prompt") or "").strip(), nodes_by_id, node_outputs)
    if use_own and own_p:
        resolved_prompt = own_p
    elif upstream_texts:
        resolved_prompt = "\n\n".join(upstream_texts)
    else:
        resolved_prompt = own_p or "Ultra-realistic commercial fashion photography, 2K resolution."

    all_ref_media = upstream_media_paths + [p for p in own_media_paths if p not in upstream_media_paths]
    provider = str(node.get("provider") or "flow").strip().lower()
    media_type = str(node.get("media_type") or "Image").strip().capitalize()

    # Nếu là `gpt_image` hoặc `grok_generate` (chế độ tạo Ảnh) -> thử qua CLIProxy `:8317` trước, nếu không có thì chạy qua Google Flow 2K
    if media_type != "Video" and (ntype == "gpt_image" or provider in ("cliproxy_gpt", "grok", "cliproxy_gemini")):
        out_clip_img = os.path.join(wf_out_dir, f"{nid}_{int(time.time())}_cliproxy.png")
        m_name = "grok-2-image" if (ntype == "grok_generate" or provider == "grok") else "gpt-image-1"
        ok_ci, path_ci, _ = call_cliproxy_image_generation(
            prompt_text=resolved_prompt,
            out_file=out_clip_img,
            model_name=m_name,
            ratio=str(node.get("ratio") or "9:16"),
        )
        if ok_ci and path_ci and os.path.exists(path_ci):
            return {
                "ok": True,
                "status": "done",
                "media_type": "image",
                "media_paths": [path_ci],
                "primary_path": path_ci,
                "media_url": f"/api/media?path={urllib.parse.quote(path_ci)}",
                "prompt_used": resolved_prompt,
                "provider_used": provider,
            }

    # Mặc định & Fallback mạnh mẽ: Chạy trên Google Flow (Nano Banana 2.1 2K / Omni 1.1 Flash / Veo 3.1)
    res_flow = execute_flow_generation_node(
        node=node,
        prompt_text=resolved_prompt,
        ref_media_paths=all_ref_media,
        wf_out_dir=wf_out_dir,
        profile_name=profile_name,
    )
    if res_flow.get("ok"):
        p_path = res_flow.get("primary_path") or ""
        res_flow["status"] = "done"
        res_flow["media_url"] = f"/api/media?path={urllib.parse.quote(p_path)}" if p_path else ""
    else:
        res_flow["status"] = "error"
    return res_flow


def compute_dag_waves(nodes: list, edges: list) -> list:
    """
    Sắp xếp đồ thị các Node thành từng lớp sóng phụ thuộc (Topological Waves):
      - Wave 0: Các node nguồn (không phụ thuộc node nào, VD: `Image`, `Outfit`, `Prompt - Image`, `Prompt - Video 01`, `Prompt - Video 02`)
      - Wave 1: Các node chỉ phụ thuộc Wave 0 (VD: `Flow - Images Generate`)
      - Wave 2: Các node phụ thuộc Wave 1 (VD: `Flow - Videos Generate 01` và `Flow - Videos Generate 3` — có thể chạy song song!)
    """
    enabled_nodes = [n for n in nodes if n.get("enabled", True)]
    node_ids = {n["node_id"] for n in enabled_nodes}
    nodes_by_id = {n["node_id"]: n for n in enabled_nodes}

    deps = {nid: set() for nid in node_ids}
    for e in edges:
        s = e.get("source_node_id")
        t = e.get("target_node_id")
        if s in node_ids and t in node_ids and s != t:
            deps[t].add(s)

    waves = []
    remaining = set(node_ids)
    while remaining:
        ready = [nid for nid in remaining if not (deps[nid] & remaining)]
        if not ready:
            # Nếu có chu trình (cycle), lấy node có pos_x nhỏ nhất để phá chu trình
            ready = [min(remaining, key=lambda k: float(nodes_by_id[k].get("pos_x") or 0))]
        ready_sorted = sorted(ready, key=lambda k: (float(nodes_by_id[k].get("pos_x") or 0), float(nodes_by_id[k].get("pos_y") or 0)))
        waves.append([nodes_by_id[k] for k in ready_sorted])
        remaining -= set(ready_sorted)
    return waves


def run_workflow_execution_pipeline(
    raw_doc: dict,
    target_node_id: str = None,
    profile_name: str = "",
    selected_node_ids: list = None,
) -> dict:
    """
    Thực thi toàn bộ Workflow theo thứ tự sóng DAG (`compute_dag_waves`) hoặc chỉ chạy 1 node cụ thể (`target_node_id`)
    hoặc danh sách các node được chọn từ bảng Xác nhận thứ tự chạy (`selected_node_ids`).
    Cập nhật trạng thái trực tiếp vào `_WORKFLOW_RUN_STATE[wf_id]` để giao diện Web đồng bộ thời gian thực.
    """
    doc = normalize_workflow_document(raw_doc)
    wf_id = doc["id"]
    wf = doc["workflow"]
    nodes = wf["nodes"]
    edges = wf["edges"]
    settings = wf["settings"]
    nodes_by_id = {n["node_id"]: n for n in nodes}

    # Hỗ trợ Chế độ Tạo Số Lượng Lớn (Batch / Matrix Bulk Generation) nếu có `_batch_run_config`
    batch_cfg = settings.pop("_batch_run_config", None) or raw_doc.get("_batch_run_config")
    if isinstance(batch_cfg, dict) and batch_cfg.get("enabled"):
        return run_workflow_batch_pipeline(
            doc,
            batch_config=batch_cfg,
            profile_name=profile_name,
            selected_node_ids=selected_node_ids,
        )

    wf_out_dir = os.path.join(WORKFLOW_OUTPUTS_DIR, wf_id)
    os.makedirs(wf_out_dir, exist_ok=True)

    prev_state = _WORKFLOW_RUN_STATE.get(wf_id) or {}
    node_outputs = dict(prev_state.get("node_outputs") or {})
    node_states = dict(prev_state.get("node_states") or {})

    # Khôi phục output sẵn có từ kết quả đã lưu trên từng node (nếu có)
    for n in nodes:
        nid = n["node_id"]
        if n.get("last_output") and nid not in node_outputs:
            node_outputs[nid] = n["last_output"]

    _WORKFLOW_RUN_STATE[wf_id] = {
        "status": "running",
        "started_at": time.strftime("%H:%M:%S"),
        "node_states": node_states,
        "node_outputs": node_outputs,
        "current_message": f"🚀 Đang khởi chạy Workflow: {wf.get('name')}...",
    }

    waves = compute_dag_waves(nodes, edges)
    delay_sec = max(0, int(settings.get("delay_between_nodes") or 0))
    stop_on_err = bool(settings.get("stop_on_error", True))
    is_parallel = bool(settings.get("parallel", True))
    selected_set = set(selected_node_ids) if isinstance(selected_node_ids, list) and selected_node_ids else None

    def _apply_node_result(nd_obj: dict, res_obj: dict):
        nid_k = nd_obj["node_id"]
        st_str = "done" if res_obj.get("ok") else "error"
        p_path = res_obj.get("primary_path") or ""
        node_outputs[nid_k] = res_obj
        node_states[nid_k] = {
            "status": st_str,
            "error": res_obj.get("error"),
            "media_url": res_obj.get("media_url") or "",
            "primary_path": p_path,
            "text": res_obj.get("text") or "",
            "updated_at": time.strftime("%H:%M:%S"),
        }
        nd_obj["last_output"] = res_obj
        cfg_obj = nd_obj.get("config") or {}
        cfg_obj["status"] = st_str
        if p_path:
            cfg_obj["result_path"] = p_path
        nd_obj["config"] = cfg_obj

    try:
        for w_idx, wave_nodes in enumerate(waves):
            # Nếu chỉ chạy 1 node cụ thể (`target_node_id`) hoặc danh sách chọn (`selected_set`)
            run_batch = []
            for nd in wave_nodes:
                nid = nd["node_id"]
                ntype = str(nd.get("node_type") or "").lower()
                is_gen_node = ntype in ("generate", "gpt_image", "grok_generate", "gemini_generate")
                if target_node_id:
                    if nid == target_node_id:
                        run_batch.append(nd)
                    elif not is_gen_node and nid not in node_outputs:
                        run_batch.append(nd)
                elif selected_set is not None:
                    if nid in selected_set or not is_gen_node:
                        run_batch.append(nd)
                else:
                    run_batch.append(nd)

            if not run_batch:
                continue

            for nd in run_batch:
                node_states[nd["node_id"]] = {"status": "running", "updated_at": time.strftime("%H:%M:%S")}
            _WORKFLOW_RUN_STATE[wf_id]["current_message"] = (
                f"⚡ Đang chạy Lớp {w_idx+1}/{len(waves)}: " + ", ".join(n.get("node_name", n["node_id"]) for n in run_batch)
            )

            if is_parallel and len(run_batch) > 1:
                with ThreadPoolExecutor(max_workers=min(3, len(run_batch))) as pool:
                    fut_map = {
                        pool.submit(
                            execute_single_node_in_context,
                            nd,
                            nodes_by_id,
                            edges,
                            node_outputs,
                            wf_out_dir,
                            profile_name,
                        ): nd
                        for nd in run_batch
                    }
                    for fut in as_completed(fut_map):
                        nd = fut_map[fut]
                        try:
                            res = fut.result()
                        except Exception as exc:
                            res = {"ok": False, "status": "error", "error": str(exc)}
                        _apply_node_result(nd, res)
            else:
                for nd in run_batch:
                    res = execute_single_node_in_context(
                        nd, nodes_by_id, edges, node_outputs, wf_out_dir, profile_name
                    )
                    _apply_node_result(nd, res)
                    if not res.get("ok") and stop_on_err:
                        raise RuntimeError(f"Node '{nd.get('node_name')}' báo lỗi: {res.get('error')}")
                    if delay_sec > 0 and len(run_batch) > 1:
                        time.sleep(min(delay_sec, 5))

        # Tự động đồng bộ các video đã tạo vào thanh Timeline của Workflow
        timeline_clips = list(wf.get("timeline") or [])
        existing_paths = {str(c.get("path") or c.get("video_path") or "") for c in timeline_clips if isinstance(c, dict)}
        for nd in nodes:
            lo = nd.get("last_output") or {}
            p_path = str(lo.get("primary_path") or (nd.get("config") or {}).get("result_path") or "")
            if p_path and p_path.lower().endswith((".mp4", ".mov", ".webm")) and os.path.exists(p_path):
                if p_path not in existing_paths:
                    dur_s = str(nd.get("video_duration") or (nd.get("config") or {}).get("duration") or "10s").lower().replace("s", "")
                    dur_val = int(dur_s) if dur_s.isdigit() else 10
                    timeline_clips.append({
                        "clip_id": f"clip_{nd['node_id']}",
                        "node_id": nd["node_id"],
                        "label": nd.get("node_name") or nd.get("label") or nd["node_id"],
                        "path": p_path,
                        "video_path": p_path,
                        "duration": dur_val,
                    })
                    existing_paths.add(p_path)
        wf["timeline"] = timeline_clips

        _WORKFLOW_RUN_STATE[wf_id]["status"] = "done"
        _WORKFLOW_RUN_STATE[wf_id]["current_message"] = f"✅ Đã hoàn thành chạy Workflow '{wf.get('name')}'!"
    except Exception as e:
        _WORKFLOW_RUN_STATE[wf_id]["status"] = "error"
        _WORKFLOW_RUN_STATE[wf_id]["current_message"] = f"❌ Lỗi thực thi Workflow: {e}"

    # Lưu lại `last_output` và `timeline` vào file JSON của workflow
    save_workflow_document(doc, wf_id=wf_id)
    return _WORKFLOW_RUN_STATE[wf_id]


def run_workflow_batch_pipeline(
    doc: dict,
    batch_config: dict,
    profile_name: str = "",
    selected_node_ids: list = None,
) -> dict:
    """
    Thực thi Tạo Số Lượng Lớn (Bulk / Matrix Batch Workflow):
      - mode = 'variations': Chạy lặp toàn bộ sơ đồ (hoặc các node chọn) N lượt biến thể (VD: 2, 4, 8, 10, 20 bộ).
      - mode = 'product_swap': Thay lần lượt danh sách ảnh Sản phẩm / Bộ đồ (`items`: `[{"label": "...", "path": "..."}]`)
                               vào Node Ảnh đích (`target_image_node_id`), chạy sơ đồ cho từng sản phẩm.
      - mode = 'prompt_list': Thay lần lượt danh sách câu lệnh Prompt (`prompts`: `["prompt 1", "prompt 2", ...]`)
                              vào Node Prompt/Generate đích (`target_prompt_node_id`), chạy sơ đồ cho từng kịch bản.
    """
    import copy
    wf_id = doc["id"]
    wf = doc["workflow"]
    mode = str(batch_config.get("mode") or "variations").strip()
    max_workers = max(1, min(6, int(batch_config.get("max_workers") or 2)))
    auto_export_mp4 = bool(batch_config.get("auto_export_mp4", True))
    target_img_nid = str(batch_config.get("target_image_node_id") or "").strip()
    target_txt_nid = str(batch_config.get("target_prompt_node_id") or "").strip()

    jobs = []
    if mode == "product_swap":
        raw_items = batch_config.get("items") or []
        for idx, it in enumerate(raw_items):
            if isinstance(it, str):
                p_val = it.strip()
                lbl = os.path.splitext(os.path.basename(p_val))[0] or f"Sản phẩm #{idx+1}"
            elif isinstance(it, dict):
                p_val = str(it.get("path") or it.get("image_path") or "").strip()
                lbl = str(it.get("label") or it.get("name") or f"Sản phẩm #{idx+1}").strip()
            else:
                continue
            if p_val:
                jobs.append({"index": idx + 1, "label": lbl, "image_path": p_val, "prompt_text": ""})
    elif mode == "prompt_list":
        raw_prompts = batch_config.get("prompts") or []
        if isinstance(raw_prompts, str):
            raw_prompts = [ln.strip() for ln in raw_prompts.splitlines() if ln.strip()]
        for idx, pr in enumerate(raw_prompts):
            pr_s = str(pr or "").strip()
            if pr_s:
                jobs.append({"index": idx + 1, "label": f"Kịch bản #{idx+1}: {pr_s[:36]}...", "image_path": "", "prompt_text": pr_s})
    else:
        count = max(1, min(50, int(batch_config.get("batch_count") or batch_config.get("count") or 3)))
        for idx in range(count):
            jobs.append({"index": idx + 1, "label": f"Lượt chạy Batch #{idx+1}/{count}", "image_path": "", "prompt_text": ""})

    if not jobs:
        jobs = [{"index": 1, "label": "Lượt chạy Batch #1", "image_path": "", "prompt_text": ""}]

    total_jobs = len(jobs)
    batch_results = []
    _WORKFLOW_RUN_STATE[wf_id] = {
        "status": "running",
        "started_at": time.strftime("%H:%M:%S"),
        "node_states": {},
        "node_outputs": {},
        "batch_mode": mode,
        "batch_total": total_jobs,
        "batch_completed": 0,
        "batch_results": batch_results,
        "current_message": f"🚀 Đang chạy Tạo Số Lượng Lớn ({total_jobs} lô — Chế độ: {mode}, {max_workers} luồng)...",
    }

    for j_idx, job in enumerate(jobs):
        _WORKFLOW_RUN_STATE[wf_id]["current_message"] = (
            f"⚡ [Batch {j_idx+1}/{total_jobs}] Đang xử lý: {job['label']}..."
        )
        # Tạo bản sao doc cho lượt chạy này, áp dụng override ảnh hoặc prompt nếu có
        job_doc = copy.deepcopy(doc)
        job_doc["workflow"]["settings"].pop("_batch_run_config", None)
        for nd in job_doc["workflow"]["nodes"]:
            nid = nd["node_id"]
            if job.get("image_path") and (nid == target_img_nid or (not target_img_nid and nd.get("node_type") == "image")):
                img_p = job["image_path"]
                nd["local_path"] = img_p
                nd["ref_images"] = [{"local_path": img_p, "path": img_p}]
                cfg = nd.get("config") or {}
                cfg["file_path"] = img_p
                cfg["result_path"] = img_p
                cfg["reference_images"] = [img_p]
                nd["config"] = cfg
                if not target_img_nid:
                    target_img_nid = nid
            if job.get("prompt_text") and (nid == target_txt_nid or (not target_txt_nid and nd.get("node_type") in ("prompt", "text"))):
                pr_t = job["prompt_text"]
                nd["prompt"] = pr_t
                nd["text"] = pr_t
                cfg = nd.get("config") or {}
                cfg["prompt"] = pr_t
                nd["config"] = cfg
                if not target_txt_nid:
                    target_txt_nid = nid

        st_one = run_workflow_execution_pipeline(
            job_doc,
            target_node_id=None,
            profile_name=profile_name,
            selected_node_ids=selected_node_ids,
        )
        # Thu thập kết quả của lượt chạy này
        outputs_one = st_one.get("node_outputs") or {}
        media_items = []
        for n_obj in job_doc["workflow"]["nodes"]:
            nid_k = n_obj["node_id"]
            out_k = outputs_one.get(nid_k) or n_obj.get("last_output") or {}
            p_path = str(out_k.get("primary_path") or (n_obj.get("config") or {}).get("result_path") or "")
            if p_path and os.path.exists(p_path):
                media_items.append({
                    "node_id": nid_k,
                    "node_name": n_obj.get("node_name") or nid_k,
                    "media_type": "video" if p_path.lower().endswith((".mp4", ".mov", ".webm")) else "image",
                    "path": p_path,
                    "media_url": f"/api/media?path={urllib.parse.quote(p_path)}",
                })
        exported_mp4 = ""
        if auto_export_mp4:
            vid_clips = [{"path": m["path"], "duration": 10} for m in media_items if m["media_type"] == "video"]
            if vid_clips:
                exp_res = export_workflow_timeline_mp4_ffmpeg(
                    clips=vid_clips,
                    wf_name=f"{wf.get('name', 'Batch')}_Batch_{j_idx+1}",
                )
                if exp_res.get("ok"):
                    exported_mp4 = exp_res.get("output_path") or ""

        batch_entry = {
            "batch_index": j_idx + 1,
            "label": job["label"],
            "status": "done" if st_one.get("status") == "done" else "error",
            "finished_at": time.strftime("%H:%M:%S"),
            "media_items": media_items,
            "exported_mp4": exported_mp4,
            "exported_mp4_url": f"/api/media?path={urllib.parse.quote(exported_mp4)}" if exported_mp4 else "",
        }
        batch_results.append(batch_entry)
        # Đồng bộ ngược node_outputs mới nhất vào doc gốc
        doc["workflow"]["nodes"] = job_doc["workflow"]["nodes"]
        doc["workflow"]["timeline"] = job_doc["workflow"].get("timeline") or []
        hist = list(doc["workflow"].get("batch_history") or [])
        hist.insert(0, batch_entry)
        doc["workflow"]["batch_history"] = hist[:50]
        save_workflow_document(doc, wf_id=wf_id)

        _WORKFLOW_RUN_STATE[wf_id].update({
            "status": "running" if (j_idx + 1) < total_jobs else "done",
            "batch_completed": j_idx + 1,
            "batch_results": batch_results,
            "current_message": (
                f"✅ Đã hoàn thành Tạo Số Lượng Lớn ({total_jobs}/{total_jobs} lô)!"
                if (j_idx + 1) >= total_jobs
                else f"⚡ Đã xong {j_idx+1}/{total_jobs} lô — Đang chuyển sang lô tiếp theo..."
            ),
        })

    return _WORKFLOW_RUN_STATE[wf_id]


def get_workflow_run_status(wf_id: str) -> dict:
    st = dict(_WORKFLOW_RUN_STATE.get(wf_id) or {"status": "idle", "node_states": {}, "node_outputs": {}, "current_message": "Sẵn sàng"})
    st["running"] = (st.get("status") == "running")
    st["progress_msg"] = st.get("current_message") or "Đang xử lý..."
    return st


def extract_video_end_frame_ffmpeg(video_path: str, wf_id: str = "wf_frames") -> dict:
    """Trích xuất Frame cuối cùng của 1 file Video bằng FFmpeg để làm ảnh tham chiếu mở đầu cho cảnh tiếp theo (Continuity)."""
    import subprocess
    vp = str(video_path or "").strip()
    if vp.startswith("/api/media?"):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(vp).query)
        vp = (qs.get("path") or [""])[0]
    if not os.path.isabs(vp):
        vp = os.path.join(WS_DIR, vp)
    if not os.path.exists(vp):
        return {"ok": False, "error": f"Không tìm thấy file video: {vp}"}

    out_dir = os.path.join(WORKFLOW_OUTPUTS_DIR, wf_id or "wf_frames")
    os.makedirs(out_dir, exist_ok=True)
    out_png = os.path.join(out_dir, f"endframe_{os.path.splitext(os.path.basename(vp))[0]}_{int(time.time())}.png")
    cmd = [
        "ffmpeg", "-y", "-sseof", "-0.12", "-i", vp,
        "-frames:v", "1", "-q:v", "2", out_png
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=25)
        if os.path.exists(out_png) and os.path.getsize(out_png) > 500:
            return {
                "ok": True,
                "frame_path": out_png,
                "media_url": f"/api/media?path={urllib.parse.quote(out_png)}",
            }
        return {"ok": False, "error": "FFmpeg không trích xuất được frame cuối."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def export_workflow_timeline_mp4_ffmpeg(clips: list, wf_name: str = "Workflow_Timeline", out_filename: str = "") -> dict:
    """
    Ghép nối chuỗi các clip video trên thanh Timeline thành 1 file Video MP4 (H.264 1080p 60fps) hoàn chỉnh bằng FFmpeg
    và lưu trực tiếp vào thư mục `final_videos/`.
    `clips`: `[{"path": "...", "duration": 8}, ...]`
    """
    import subprocess
    valid_clips = []
    for c in clips or []:
        p = str(((c.get("path") or c.get("video_path")) if isinstance(c, dict) else c) or "").strip()
        if p.startswith("/api/media?"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(p).query)
            p = (qs.get("path") or [""])[0]
        if p and not os.path.isabs(p):
            p = os.path.join(WS_DIR, p)
        if p and os.path.exists(p):
            dur = float(c.get("duration") or 0) if isinstance(c, dict) else 0
            valid_clips.append((p, dur))

    if not valid_clips:
        return {"ok": False, "error": "Chưa có clip video hợp lệ nào trên Timeline để xuất MP4."}

    safe_name = re.sub(r"[^a-zA-Z0-9_\-]+", "_", str(wf_name or "Workflow_Timeline")).strip("_")
    fname = out_filename if out_filename else f"{safe_name}_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
    out_mp4 = os.path.join(FINAL_VIDEOS_DIR, fname)

    if len(valid_clips) == 1:
        shutil.copy2(valid_clips[0][0], out_mp4)
        return {
            "ok": True,
            "output_path": out_mp4,
            "filename": os.path.basename(out_mp4),
            "media_url": f"/api/media?path={urllib.parse.quote(out_mp4)}",
            "message": f"Đã xuất Video Timeline ra final_videos/{os.path.basename(out_mp4)}",
        }

    # Dùng filter_complex chuẩn hóa về cùng khung hình 1080x1920 (hoặc theo clip đầu) + nối mượt mà
    list_txt = os.path.join(WORKFLOW_OUTPUTS_DIR, f"concat_{int(time.time())}.txt")
    with open(list_txt, "w", encoding="utf-8") as f:
        for p, _ in valid_clips:
            escaped_p = p.replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{escaped_p}'\n")

    cmd_fast = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_txt, "-c", "copy", "-movflags", "+faststart", out_mp4
    ]
    try:
        r = subprocess.run(cmd_fast, capture_output=True, timeout=90)
        if r.returncode != 0 or not os.path.exists(out_mp4) or os.path.getsize(out_mp4) < 1000:
            cmd_reencode = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_txt,
                "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_mp4
            ]
            subprocess.run(cmd_reencode, capture_output=True, timeout=180)
    finally:
        try:
            os.remove(list_txt)
        except Exception:
            pass

    if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 1000:
        return {
            "ok": True,
            "output_path": out_mp4,
            "filename": os.path.basename(out_mp4),
            "media_url": f"/api/media?path={urllib.parse.quote(out_mp4)}",
            "message": f"✅ Đã ghép {len(valid_clips)} cảnh thành Video Final: {os.path.basename(out_mp4)}",
        }
    return {"ok": False, "error": "FFmpeg không thể ghép các clip video."}


if __name__ == "__main__":
    ensure_default_workflows_saved()
    print("Saved workflows:", [w["id"] for w in list_saved_workflows()])
