# -*- coding: utf-8 -*-
"""
👗 Lê Việt Tùng - SkillAutoVeo
Hệ Thống Template #004: MOTION CONTROL VIDEO FASHION (Omni Flash Thay Đồ Theo Nhạc & Video Tham Chiếu)
------------------------------------------------------------------------------------------------------
Quy trình chuẩn:
  1. Nhận đầu vào:
     - 1 Ảnh Nhân Vật Gốc chuẩn 2K (Base Character Ref Image trong bối cảnh phòng ngủ/studio)
     - 1 Bảng Nhân Vật / Character Turnaround Sheet 2K (tùy chọn, giúp khóa tỷ lệ cơ thể & form đồ)
     - 1 Video Tham Chiếu Chuyển Động & Nhạc (Reference Motion Video - TikTok/Douyin/Reels thời trang)
     - Danh sách N Ảnh Bộ Đồ / Outfit Product Sheets chuẩn 2K (Outfit 1, Outfit 2, Outfit 3, ...)
  2. Phân tích Video Tham Chiếu (`analyze_and_split_reference_video`):
     - Tự động tính thời lượng gốc D (giây) và chia khít cho 8s hoặc 10s (hoặc 6s) vì chỉ có model
       Omni Flash (`abra_edit` / `abra_r2v_6s` / `8s` / `10s`) mới hỗ trợ tham chiếu video.
       + Ví dụ: Video 16.28s -> Chia thành 2 phân cảnh × 8s (16s).
       + Ví dụ: Video 20.0s  -> Chia thành 2 phân cảnh × 10s (20s).
       + Ví dụ: Video 24.0s  -> Chia thành 3 phân cảnh × 8s (24s).
       + Ví dụ: Video 30.0s  -> Chia thành 3 phân cảnh × 10s (30s).
     - Dùng FFmpeg cắt trực tiếp Video Tham Chiếu thành từng file video phân cảnh (`ref_clip_s1.mp4`, `ref_clip_s2.mp4`, ...)
       và tách file nhạc gốc chất lượng cao (`ref_master_audio.m4a`).
  3. Phân tích Nhịp Nhạc (Audio Beat Onset) + Điểm Chuyển Cảnh Hình Ảnh (`scdet`) trong từng phân cảnh:
     - Tự động phát hiện các mốc giây đổi đồ theo beat nhạc / chuyển động (VD: Phân cảnh 1 đổi đồ tại `4:04`,
       Phân cảnh 2 đổi đồ tại `3:04` và `6:12`) và gán từng bộ Outfit tương ứng.
  4. Đảm bảo Ảnh Ref Nhân Vật Chuẩn 2K (1536x2752) Cho Mọi Phân Cảnh:
     - Phân cảnh 1: Dùng Ảnh Nhân Vật 2K gốc (`07_Nhan_Vat_Basic_Phong_Ngu_2K.png`).
     - Phân cảnh 2+: Tự động tạo (hoặc dùng) Ảnh Ref Nhân Vật 2K đang mặc bộ Outfit cuối của Phân cảnh trước
       trong đúng bối cảnh phòng ngủ/studio đó (qua Google Flow Nano Banana 2.1 `ogiZ0b` -> tải 2K `SPrCad` -> upload `maseQ`),
       giúp chuyển nối giữa Phân cảnh 1 sang Phân cảnh 2 mượt 100% và giữ độ nét mặt 2K tuyệt đối!
  5. Tối ưu Prompt theo Timeline + Inline Media Mention Chips chuẩn Google Flow (`jIps6` / `abra_edit`):
     - Gắn trực tiếp chip tham chiếu `[Tên_Ảnh_Nhân_Vật]` và `[Tên_Ảnh_Bộ_Đồ]` vào đúng mốc giây trong câu lệnh
       kèm mô tả chi tiết Timeline chuyển động & giữ nhạc gốc.
"""

import os
import sys
import re
import json
import math
import time
import uuid
import wave
import struct
import shutil
import base64
import random
import subprocess
import threading
import concurrent.futures
from pathlib import Path
from PIL import Image, ImageFilter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
WS_DIR = os.path.abspath(os.path.join(PIPELINE_DIR, ".."))
for _p_dir in (SCRIPTS_DIR, WS_DIR):
    if _p_dir not in sys.path:
        sys.path.insert(0, _p_dir)
PROJECTS_DIR = os.path.join(WS_DIR, "projects")
FINAL_VIDEOS_DIR = os.path.join(WS_DIR, "final_videos")
FASHION_STUDIO_DIR = os.path.join(WS_DIR, "fashion_motion_projects")
DEMO_ASSETS_DIR = os.path.join(WS_DIR, "ảnh mẫu thumbnail", "Tron_Bo_7_Anh_2K")

os.makedirs(FASHION_STUDIO_DIR, exist_ok=True)
os.makedirs(FINAL_VIDEOS_DIR, exist_ok=True)


# ==============================================================================
# 1. CẤU HÌNH PRESET & MÔ TẢ TỰ ĐỘNG CHO TRỌN BỘ 7 ẢNH 2K MẪU
# ==============================================================================

DEFAULT_FASHION_DEMO_OUTFITS = [
    {
        "id": "outfit_1_quan_xanh",
        "filename": "03_Product_Sheet_Quan_Xanh_2K.png",
        "lookbook_model_filename": "10_NV5_Look1_Quan_Xanh_Tu_Go_2K.png",
        "name": "Bộ 1: Áo Yếm Vàng Cổ Hoa Đỏ + Quần Suông Xanh Coban",
        "short_desc": "áo yếm vàng vạt xòe peplum kèm vòng cổ hoa đỏ, quần dài ống suông rộng màu xanh coban đậm, túi xách vàng và giày sneaker vàng",
        "en_desc": "pastel yellow halter peplum top with red flower choker necklace, cobalt royal-blue wide-leg trousers, yellow handbag and yellow sneakers",
    },
    {
        "id": "outfit_2_vay_vang",
        "filename": "04_Product_Sheet_Vay_Vang_2K.png",
        "lookbook_model_filename": "11_NV5_Look2_Vay_Vang_Tu_Go_2K.png",
        "name": "Bộ 2: Váy Ngắn Xếp Tầng Vàng Bơ + Túi Nhún Bèo + Giày Búp Bê",
        "short_desc": "váy ngắn cổ yếm xếp tầng phồng màu vàng bơ, dây buộc tóc scrunchie vàng, túi kẹp nách quai nhún bèo vàng, tất trắng và giày búp bê vàng",
        "en_desc": "butter-yellow halter tiered bubble mini dress, yellow ruffled shoulder bag, yellow hair scrunchie, white ankle socks and yellow Mary Jane ballet flats",
    },
    {
        "id": "outfit_3_sooc_trang",
        "filename": "05_Product_Sheet_Quan_Sooc_Trang_2K.png",
        "lookbook_model_filename": "12_NV5_Look3_Sooc_Trang_Tu_Go_2K.png",
        "name": "Bộ 3 (Look 3): Áo Yếm Vàng + Quần Soóc Trắng Xếp Ly + Túi Kem",
        "short_desc": "áo yếm vàng vạt xòe, quần soóc trắng ống rộng xếp ly, vòng cổ hoa đỏ, túi đeo vai màu kem dây xích, tất trắng và giày búp bê vàng",
        "en_desc": "pastel yellow halter top, crisp white pleated wide-leg shorts, red flower choker, cream chain shoulder bag, white socks and yellow ballet flats",
    },
    {
        "id": "outfit_4_quan_be",
        "filename": "06_Product_Sheet_Quan_Be_2K.png",
        "lookbook_model_filename": "13_NV5_Look4_Quan_Be_Tu_Go_2K.png",
        "name": "Bộ 4 (Look 4): Áo Yếm Vàng + Quần Ống Rộng Màu Be Xếp Ly + Kính Hồng",
        "short_desc": "áo yếm vàng vạt xòe, quần tây ống rộng xếp ly màu be kem, mắt kính gọng hồng pastel, vòng tay vàng và giày búp bê vàng",
        "en_desc": "pastel yellow halter peplum top, cream-beige pleated wide-leg trousers, pink frame glasses, gold bangle bracelet and yellow ballet flats",
    },
    {
        "id": "outfit_5_chan_vay_cong_so",
        "filename": "08_Product_Sheet_Set_Cong_So_Chan_Vay_Kem_2K.png",
        "lookbook_model_filename": "14_NV5_Look5_Chan_Vay_Kem_Tu_Go_2K.png",
        "name": "Bộ 5: Áo Kiểu Nâu Trầm Cổ Đổ + Chân Váy Dài Satin Kem Công Sở",
        "short_desc": "áo kiểu cổ đổ màu nâu socola sang trọng, chân váy dài chữ A chất liệu satin màu kem thanh lịch, túi xách da nâu và giày cao gót mũi nhọn ánh bạc",
        "en_desc": "chic chocolate-brown draped cowl-neck short-sleeve blouse, ivory-cream high-waisted satin A-line maxi skirt, dark brown leather shoulder bag and silver pointed-toe slingback heels",
    },
]


def format_colon_timestamp(sec_val: float) -> str:
    """Chuyển đổi số giây (VD: 4.04, 3.04, 6.12) sang định dạng '4:04', '3:04', '6:12' chuẩn prompt Google Flow."""
    sec_val = max(0.0, float(sec_val))
    whole = int(sec_val)
    frac = int(round((sec_val - whole) * 100))
    if frac >= 100:
        whole += 1
        frac -= 100
    return f"{whole}:{frac:02d}"


def parse_colon_timestamp(ts_str) -> float:
    """Đọc mốc thời gian dạng '4:04' hoặc '4.04' hoặc số thực thành float giây (4.04)."""
    if isinstance(ts_str, (int, float)):
        return round(float(ts_str), 2)
    s = str(ts_str or "").strip().replace("s", "").replace("giây", "").strip()
    if not s:
        return 0.0
    if ":" in s:
        parts = s.split(":", 1)
        try:
            sec_part = int(parts[0].strip())
            hund_part = int(parts[1].strip()[:2].ljust(2, "0"))
            return round(sec_part + hund_part / 100.0, 2)
        except Exception:
            pass
    try:
        return round(float(s.replace(",", ".")), 2)
    except Exception:
        return 0.0


# ==============================================================================
# 2. ĐẢM BẢO ẢNH REF NHÂN VẬT & OUTFIT LUÔN ĐẠT CHUẨN 2K (1536x2752)
# ==============================================================================

def ensure_image_is_2k(img_path: str, out_path: str = None, target_portrait=(1536, 2752)) -> dict:
    """
    Kiểm tra độ phân giải ảnh Ref Nhân Vật / Outfit.
    Nếu ảnh nhỏ hơn chuẩn 2K (chiều dài < 2048px), tự động nâng cấp Lanczos + UnsharpMask lên chuẩn 2K (1536x2752)
    để khi đưa vào Omni Flash (`jIps6` / `abra_edit`) khuôn mặt và chi tiết vải nét căng.
    """
    if not img_path or not os.path.exists(img_path):
        return {"ok": False, "error": f"Không tìm thấy ảnh: {img_path}"}
    dest = out_path or img_path
    try:
        with Image.open(img_path) as im:
            orig_w, orig_h = im.size
            is_already_2k = max(orig_w, orig_h) >= 2048
            if is_already_2k and dest == img_path:
                return {
                    "ok": True,
                    "path": dest,
                    "width": orig_w,
                    "height": orig_h,
                    "was_upscaled": False,
                    "is_2k": True,
                }
            im_rgb = im.convert("RGB")
            if not is_already_2k:
                if orig_h >= orig_w:
                    new_w, new_h = target_portrait
                else:
                    new_w, new_h = (target_portrait[1], target_portrait[0])
                im_rgb = im_rgb.resize((new_w, new_h), Image.Resampling.LANCZOS)
                im_rgb = im_rgb.filter(ImageFilter.UnsharpMask(radius=1.05, percent=115, threshold=2))
            else:
                new_w, new_h = orig_w, orig_h
            os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
            ext = os.path.splitext(dest)[1].lower()
            if ext == ".png":
                im_rgb.save(dest, format="PNG", optimize=True)
            else:
                im_rgb.save(dest, format="JPEG", quality=98, subsampling=0)
            return {
                "ok": True,
                "path": dest,
                "width": new_w,
                "height": new_h,
                "orig_width": orig_w,
                "orig_height": orig_h,
                "was_upscaled": not is_already_2k,
                "is_2k": True,
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==============================================================================
# 3. PHÂN TÍCH THỜI LƯỢNG VIDEO THAM CHIẾU & CHIA KHÍT CHO 8S HOẶC 10S (OMNI FLASH)
# ==============================================================================

def probe_video_info(video_path: str) -> dict:
    """Lấy thông tin chi tiết của video tham chiếu (duration, width, height, fps, audio)."""
    if not video_path or not os.path.exists(video_path):
        return {"ok": False, "error": f"File video không tồn tại: {video_path}"}
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate",
        "-of",
        "json",
        video_path,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20, encoding="utf-8", errors="replace")
        data = json.loads(r.stdout or "{}")
        duration = float((data.get("format") or {}).get("duration") or 0.0)
        width, height, fps = 1080, 1920, 30.0
        has_audio = False
        for st in data.get("streams") or []:
            if st.get("codec_type") == "video":
                width = int(st.get("width") or width)
                height = int(st.get("height") or height)
                r_fps = str(st.get("r_frame_rate") or "30/1")
                if "/" in r_fps:
                    num, den = r_fps.split("/", 1)
                    if float(den) > 0:
                        fps = round(float(num) / float(den), 2)
                else:
                    fps = float(r_fps)
            elif st.get("codec_type") == "audio":
                has_audio = True
        return {
            "ok": True,
            "duration": round(duration, 3),
            "width": width,
            "height": height,
            "fps": fps,
            "has_audio": has_audio,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def choose_optimal_omni_flash_split(total_duration: float, preferred_chunk_sec: str = "auto") -> dict:
    """
    Quyết định chia video tham chiếu thành bao nhiêu phân cảnh (8s hoặc 10s, hỗ trợ thêm 6s).
    Ví dụ thực tế:
      - Video ~16s (như 16.28s) -> 2 phân cảnh × 8s = 16s
      - Video ~20s              -> 2 phân cảnh × 10s = 20s
      - Video ~24s              -> 3 phân cảnh × 8s = 24s
      - Video ~30s              -> 3 phân cảnh × 10s = 30s
      - Video ~12s              -> 2 phân cảnh × 6s = 12s
      - Video ~8s               -> 1 phân cảnh × 8s = 8s
      - Video ~10s              -> 1 phân cảnh × 10s = 10s
    """
    d = max(4.0, float(total_duration or 16.0))
    pref = str(preferred_chunk_sec or "auto").strip().lower().replace("s", "")
    if pref in ("6", "8", "10"):
        chunk = int(pref)
        num_scenes = max(1, int(round(d / chunk)))
        return {
            "scene_duration": chunk,
            "num_scenes": num_scenes,
            "effective_total_duration": num_scenes * chunk,
            "model_key_r2v": f"abra_r2v_{chunk}s",
            "model_key_edit": "abra_edit",
            "reason": f"Chia cố định theo cấu hình {num_scenes} phân cảnh × {chunk}s = {num_scenes * chunk}s",
        }

    # Ưu tiên chia hết cho 8s hoặc 10s (và 6s nếu video ~12s/18s)
    candidates = []
    for chunk in (8, 10, 6):
        n_floor = max(1, int(math.floor((d + 1.2) / chunk)))
        n_round = max(1, int(round(d / chunk)))
        for n in sorted(set([n_floor, n_round])):
            eff = n * chunk
            diff = abs(d - eff)
            # Ưu tiên 8s và 10s hơn 6s khi sai số tương đương
            priority_penalty = 0.0 if chunk in (8, 10) else 0.65
            # Phạt nhẹ nếu tổng thời lượng vượt quá thời lượng video gốc quá 1.2s (vì phần dư không có hình ref)
            overrun_penalty = max(0.0, eff - d - 0.5) * 1.8
            score = diff + priority_penalty + overrun_penalty
            candidates.append((score, diff, chunk, n, eff))

    candidates.sort(key=lambda x: (x[0], x[1]))
    _, _, best_chunk, best_n, best_eff = candidates[0]
    return {
        "scene_duration": best_chunk,
        "num_scenes": best_n,
        "effective_total_duration": best_eff,
        "model_key_r2v": f"abra_r2v_{best_chunk}s",
        "model_key_edit": "abra_edit",
        "reason": (
            f"Video gốc dài {d:.2f}s → Tối ưu chia thành {best_n} phân cảnh × {best_chunk}s "
            f"(Tổng {best_eff}s, chuẩn Omni Flash {best_chunk}s)"
        ),
    }


def detect_clip_beat_and_visual_cuts(clip_path: str, clip_duration: float, desired_cuts: int = 1) -> list:
    """
    Phân tích 1 phân cảnh video đã cắt (8s hoặc 10s) kết hợp:
      1. Điểm chuyển cảnh hình ảnh (`ffmpeg scdet`) — phát hiện chính xác khoảnh khắc video gốc nhảy frame / biến hình thay đồ.
      2. Đỉnh nhịp bass / beat nhạc (`audio energy flux onset`) — phát hiện nhịp rơi của nhạc nền.
    Trả về danh sách các mốc giây (float, làm tròn 2 chữ số thập phân, VD `[4.04]` hoặc `[3.04, 6.12]`).
    """
    dur = float(clip_duration or 8.0)
    if desired_cuts <= 0:
        return []

    # Bước 1: Quét scdet (visual scene change) trong khoảng [1.2s .. dur - 1.0s]
    visual_cuts = []
    try:
        cmd_sc = [
            "ffmpeg",
            "-hide_banner",
            "-i",
            clip_path,
            "-vf",
            "scdet=threshold=9",
            "-an",
            "-f",
            "null",
            "-",
        ]
        r_sc = subprocess.run(cmd_sc, capture_output=True, text=True, timeout=25, encoding="utf-8", errors="replace")
        stderr_txt = r_sc.stderr or ""
        for m in re.finditer(r"lavfi\.scd\.score:\s*([0-9.]+),\s*lavfi\.scd\.time:\s*([0-9.]+)", stderr_txt):
            sc_score = float(m.group(1))
            sc_time = round(float(m.group(2)), 2)
            if 1.3 <= sc_time <= (dur - 0.9):
                visual_cuts.append((sc_time, sc_score))
    except Exception:
        pass

    # Bước 2: Quét đỉnh năng lượng âm thanh (Audio Beat Onsets) bằng PCM 16kHz
    audio_peaks = []
    tmp_wav = clip_path + ".beat_tmp.wav"
    try:
        cmd_wav = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            clip_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            tmp_wav,
        ]
        subprocess.run(cmd_wav, capture_output=True, timeout=15)
        if os.path.exists(tmp_wav) and os.path.getsize(tmp_wav) > 1000:
            with wave.open(tmp_wav, "rb") as wf:
                sr = wf.getframerate()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)
            samples = struct.unpack(f"<{len(raw)//2}h", raw)
            hop = max(1, int(sr * 0.02))  # 20ms hop = 0.02s độ chính xác từng frame
            energies = []
            for idx in range(0, len(samples) - hop, hop):
                chunk_s = samples[idx : idx + hop]
                rms = math.sqrt(sum(float(x) * float(x) for x in chunk_s) / len(chunk_s))
                t_sec = round(idx / float(sr), 2)
                energies.append((t_sec, rms))
            # Tính onset flux (mức tăng năng lượng đột ngột khi beat đập)
            for i in range(3, len(energies) - 3):
                t_sec, e_curr = energies[i]
                if not (1.3 <= t_sec <= (dur - 0.9)):
                    continue
                e_prev = sum(energies[j][1] for j in range(i - 3, i)) / 3.0
                flux = max(0.0, e_curr - e_prev)
                if flux > 150:
                    audio_peaks.append((t_sec, flux))
    except Exception:
        pass
    finally:
        if os.path.exists(tmp_wav):
            try:
                os.remove(tmp_wav)
            except OSError:
                pass

    # Bước 3: Chia khung thời gian thành `desired_cuts` vùng hợp lý để chọn mốc chuẩn nhất trong mỗi vùng
    # Ví dụ:
    #   - Nếu desired_cuts == 1 trên clip 8s -> vùng lý tưởng quanh [3.2s .. 5.2s] (chuẩn ~4.04s)
    #   - Nếu desired_cuts == 2 trên clip 8s -> vùng 1 quanh [2.2s .. 4.2s] (~3.04s), vùng 2 quanh [5.0s .. 6.8s] (~6.12s)
    selected_timestamps = []
    for k in range(desired_cuts):
        ideal_t = round(dur * (k + 1) / (desired_cuts + 1), 2)
        if desired_cuts == 1 and abs(dur - 8.0) < 0.2:
            ideal_t = 4.04
        elif desired_cuts == 2 and abs(dur - 8.0) < 0.2:
            ideal_t = 3.04 if k == 0 else 6.12

        win_half = max(1.15, dur / (desired_cuts + 1) * 0.45)
        w_min = max(1.2, ideal_t - win_half)
        w_max = min(dur - 0.85, ideal_t + win_half)

        # Kiểm tra có visual cut rõ rệt trong vùng này không
        cand_vis = [c for c in visual_cuts if w_min <= c[0] <= w_max]
        if cand_vis:
            # Chọn visual cut gần ideal_t hoặc có điểm cao nhất
            cand_vis.sort(key=lambda x: (abs(x[0] - ideal_t) * 1.5 - (x[1] / 50.0)))
            best_t = cand_vis[0][0]
        else:
            cand_aud = [a for a in audio_peaks if w_min <= a[0] <= w_max]
            if cand_aud:
                cand_aud.sort(key=lambda x: (-x[1] / (1.0 + abs(x[0] - ideal_t) * 1.2)))
                best_t = cand_aud[0][0]
            else:
                best_t = ideal_t

        # Đảm bảo cách mốc trước ít nhất 1.6s
        if selected_timestamps and (best_t - selected_timestamps[-1]) < 1.6:
            best_t = round(min(dur - 0.8, selected_timestamps[-1] + 2.2), 2)
        selected_timestamps.append(round(best_t, 2))

    return selected_timestamps


def analyze_and_split_reference_video(
    ref_video_path: str,
    work_dir: str,
    outfits: list = None,
    preferred_chunk_sec: str = "auto",
    custom_scene_cuts: dict = None,
    generation_mode: str = "chained_i2v",
) -> dict:
    """
    1. Phân tích Video Tham Chiếu (`ref_video_path`).
    2. Chia thời lượng thành các phân cảnh chuẩn Omni Flash (`8s` hoặc `10s`, hoặc `6s`).
    3. Cắt trực tiếp Video Tham Chiếu thành từng file `ref_clip_s1.mp4`, `ref_clip_s2.mp4`, ...
       và tách nhạc gốc `ref_master_audio.m4a`.
    4. Phân bổ các bộ đồ (`outfits`) vào từng phân cảnh theo đúng nhịp beat 0.1s / chuyển cảnh của video gốc.
    """
    os.makedirs(work_dir, exist_ok=True)
    clips_dir = os.path.join(work_dir, "ref_clips")
    os.makedirs(clips_dir, exist_ok=True)

    import hashlib as _hl
    import fashion_ai_video_analyzer as fava

    outfits_list = list(outfits or DEFAULT_FASHION_DEMO_OUTFITS[:4])
    ref_cache_dir = ""
    cache_meta_path = ""
    try:
        st_ref = os.stat(ref_video_path)
        key_src = json.dumps(
            {
                "path": os.path.abspath(ref_video_path),
                "size": st_ref.st_size,
                "mtime": int(st_ref.st_mtime),
                "chunk_sec": str(preferred_chunk_sec),
                "mode": str(generation_mode or "chained_i2v"),
                "cuts": custom_scene_cuts or {},
            },
            sort_keys=True,
        )
        cache_hash = _hl.sha1(key_src.encode("utf-8")).hexdigest()[:16]
        ref_cache_dir = os.path.join(FASHION_STUDIO_DIR, "_ref_cache", cache_hash)
        cache_meta_path = os.path.join(ref_cache_dir, "meta.json")
    except Exception:
        ref_cache_dir = ""
        cache_meta_path = ""

    if cache_meta_path and os.path.isfile(cache_meta_path):
        try:
            cached = json.load(open(cache_meta_path, "r", encoding="utf-8"))
            c_probe = cached.get("video_probe") or {}
            c_plan = cached.get("split_plan") or {}
            c_gcuts = cached.get("global_cuts_info") or {}
            c_scenes = cached.get("scenes_files") or []
            c_aud_name = cached.get("master_audio_filename") or ""
            files_valid = bool(c_scenes) and all(
                os.path.isfile(os.path.join(ref_cache_dir, sf["clip"])) and os.path.getsize(os.path.join(ref_cache_dir, sf["clip"])) > 0
                for sf in c_scenes
            )
            if c_aud_name and not os.path.isfile(os.path.join(ref_cache_dir, c_aud_name)):
                files_valid = False
            if files_valid:
                master_audio_path = os.path.join(clips_dir, c_aud_name) if c_aud_name else ""
                if c_aud_name:
                    shutil.copy2(os.path.join(ref_cache_dir, c_aud_name), master_audio_path)
                c_chunk_sec = int(c_plan.get("scene_duration") or 8)
                c_num_scenes = int(c_plan.get("num_scenes") or len(c_scenes))
                c_total_dur = float(c_probe.get("duration") or (c_chunk_sec * c_num_scenes))
                scene_transitions_all = fava.map_outfits_to_scenes_smart(
                    num_scenes=c_num_scenes,
                    chunk_sec=c_chunk_sec,
                    total_dur=c_total_dur,
                    outfits_list=outfits_list,
                    global_cuts_info=c_gcuts,
                    clips_dir=clips_dir,
                    custom_scene_cuts=custom_scene_cuts,
                    detect_clip_fn=detect_clip_beat_and_visual_cuts,
                    generation_mode=generation_mode,
                )
                _g_tr_idx = 0
                for _sc_trs in scene_transitions_all:
                    for _tr_item in _sc_trs:
                        _g_tr_idx += 1
                        _tr_item["transition_index"] = _g_tr_idx
                scenes_data = []
                for idx, sf in enumerate(c_scenes):
                    sc_id = sf["id"]
                    clip_fn = sf["clip"]
                    clip_dst = os.path.join(clips_dir, clip_fn)
                    shutil.copy2(os.path.join(ref_cache_dir, clip_fn), clip_dst)
                    adult_dst = ""
                    if sf.get("adult") and os.path.isfile(os.path.join(ref_cache_dir, sf["adult"])):
                        adult_dst = os.path.join(clips_dir, sf["adult"])
                        shutil.copy2(os.path.join(ref_cache_dir, sf["adult"]), adult_dst)
                    thumb_dst = ""
                    if sf.get("thumb") and os.path.isfile(os.path.join(ref_cache_dir, sf["thumb"])):
                        thumb_dst = os.path.join(clips_dir, sf["thumb"])
                        shutil.copy2(os.path.join(ref_cache_dir, sf["thumb"]), thumb_dst)
                    kf_dst = ""
                    if sf.get("kf") and os.path.isfile(os.path.join(ref_cache_dir, sf["kf"])):
                        kf_dst = os.path.join(clips_dir, sf["kf"])
                        shutil.copy2(os.path.join(ref_cache_dir, sf["kf"]), kf_dst)
                    scenes_data.append({
                        "id": sc_id,
                        "scene_index": sf["scene_index"],
                        "start_sec": sf["start_sec"],
                        "end_sec": sf["end_sec"],
                        "duration": c_chunk_sec,
                        "fps": 30,
                        "start_frame": 1,
                        "end_frame": int(c_chunk_sec * 30) + 1,
                        "ref_clip_filename": clip_fn,
                        "ref_clip_path": clip_dst,
                        "adult_safe_clip_path": adult_dst,
                        "ref_clip_thumb": thumb_dst,
                        "keyframe_sheet_path": kf_dst,
                        "transitions": scene_transitions_all[idx] if idx < len(scene_transitions_all) else [],
                    })
                return {
                    "ok": True,
                    "video_probe": c_probe,
                    "split_plan": c_plan,
                    "global_cuts_info": c_gcuts,
                    "master_audio_path": master_audio_path if (master_audio_path and os.path.exists(master_audio_path)) else "",
                    "scenes": scenes_data,
                }
        except Exception:
            pass

    probe = probe_video_info(ref_video_path)
    if not probe.get("ok"):
        return probe

    total_dur = probe["duration"]
    split_plan = choose_optimal_omni_flash_split(total_dur, preferred_chunk_sec)
    chunk_sec = split_plan["scene_duration"]
    num_scenes = split_plan["num_scenes"]
    eff_total = split_plan["effective_total_duration"]

    # Tách nhạc gốc tổng (Master Audio) đúng độ dài `eff_total` giây để ghép vào Video Final
    master_audio_path = os.path.join(clips_dir, "ref_master_audio.m4a")
    if probe.get("has_audio"):
        cmd_aud = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            ref_video_path,
            "-t",
            str(eff_total),
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            master_audio_path,
        ]
        subprocess.run(cmd_aud, capture_output=True, timeout=30)

    total_outfits = len(outfits_list)

    global_cuts_info = fava.detect_global_video_cuts_and_beats(ref_video_path, total_dur)
    scene_transitions_all = fava.map_outfits_to_scenes_smart(
        num_scenes=num_scenes,
        chunk_sec=chunk_sec,
        total_dur=total_dur,
        outfits_list=outfits_list,
        global_cuts_info=global_cuts_info,
        clips_dir=clips_dir,
        custom_scene_cuts=custom_scene_cuts,
        detect_clip_fn=detect_clip_beat_and_visual_cuts,
        generation_mode=generation_mode,
    )
    _global_tr_counter = 0
    for _sc_trs in scene_transitions_all:
        for _tr_item in _sc_trs:
            _global_tr_counter += 1
            _tr_item["transition_index"] = _global_tr_counter

    scenes_data = []

    for idx in range(num_scenes):
        sc_num = idx + 1
        sc_id = f"s{sc_num}"
        start_sec = round(idx * chunk_sec, 2)
        end_sec = round((idx + 1) * chunk_sec, 2)
        clip_filename = f"ref_clip_{sc_id}_{chunk_sec}s.mp4"
        clip_path = os.path.join(clips_dir, clip_filename)

        # Cắt trực tiếp phân cảnh từ video tham chiếu bằng FFmpeg ở chuẩn 30 FPS (khớp 100% với _.KQ=30 của Google Flow cho video upload)
        # Đặt -i trước -ss kèm setpts=PTS-STARTPTS để không bị lệch keyframe hay đơ/thiếu 2s cuối khi Google Flow đọc 240 frames (8s * 30fps)
        avail_dur = max(0.5, float(total_dur) - float(start_sec))
        target_cut_dur = float(chunk_sec) + 0.15
        pad_dur = max(0.0, target_cut_dur - avail_dur)
        vf_cut = "fps=30,setpts=PTS-STARTPTS"
        if pad_dur > 0.01:
            vf_cut += f",tpad=stop_mode=clone:stop_duration={pad_dur:.3f}"
        cmd_cut = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            ref_video_path,
            "-ss",
            f"{start_sec:.3f}",
            "-t",
            f"{target_cut_dur:.3f}",
            "-vf",
            vf_cut,
            "-af",
            "asetpts=PTS-STARTPTS",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-r",
            "30",
            "-g",
            "30",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            clip_path,
        ]
        subprocess.run(cmd_cut, capture_output=True, timeout=60)

        # Trích ảnh thumbnail preview của clip phân cảnh
        thumb_clip_path = os.path.join(clips_dir, f"ref_clip_{sc_id}_thumb.jpg")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                "0.5",
                "-i",
                clip_path,
                "-frames:v",
                "1",
                "-q:v",
                "2",
                thumb_clip_path,
            ],
            capture_output=True,
            timeout=15,
        )

        # Tạo bảng Keyframe Contact Sheet (0.5s / khung hình) cho phân cảnh để AI Vision & Người dùng quan sát
        kf_sheet_path = os.path.join(clips_dir, f"keyframe_sheet_{sc_id}.jpg")
        fava.build_scene_keyframe_contact_sheet(clip_path, sc_num, start_sec, chunk_sec, kf_sheet_path)

        # Nếu là Phân cảnh 1 (s1) và video gốc có đoạn mở đầu mặc đồ ngủ/kính cận (2.0s - 5.5s),
        # tạo sẵn 1 bản `ref_clip_s1_adult_8s.mp4` CHỈ LẤY CÁC KHUNG HÌNH TRONG PHẠM VI CẢNH 1 (từ `adult_start` đến `8.0s`),
        # TUYỆT ĐỐI KHÔNG lấy lố sang Cảnh 2 (>8.0s) để tránh trùng lặp hành động với Cảnh 2!
        adult_clip_path = ""
        if sc_num == 1:
            v_cuts_all = [float(c.get("timestamp_sec") or 0) for c in (global_cuts_info.get("visual_cuts") or [])]
            adult_start = 0.0
            for vc in v_cuts_all:
                if 2.2 <= vc <= 5.8:
                    adult_start = round(vc, 2)
                    break
            scene1_end = min(float(total_dur), float(chunk_sec))
            if adult_start >= 1.8 and (scene1_end - adult_start) >= 2.2:
                adult_clip_path = os.path.join(clips_dir, f"ref_clip_{sc_id}_adult_{chunk_sec}s.mp4")
                tr_list_s1 = scene_transitions_all[0] if scene_transitions_all else []
                t1_cut = float(tr_list_s1[0]["timestamp_sec"]) if len(tr_list_s1) >= 1 else 2.25
                t2_cut = float(tr_list_s1[1]["timestamp_sec"]) if len(tr_list_s1) >= 2 else 4.47
                t1_cut = max(1.2, min(3.8, t1_cut))
                t2_cut = max(t1_cut + 1.5, min(6.5, t2_cut))
                dur_part1 = round(t1_cut, 3)
                dur_part2 = round(t2_cut - t1_cut, 3)
                dur_part3 = round(float(chunk_sec) + 0.12 - t2_cut, 3)
                # Lấy hoàn toàn trong vùng [adult_start .. scene1_end] của Cảnh 1:
                # - Phần mở đầu (0 .. t1_cut): lấy đoạn [scene1_end - dur_part1 .. scene1_end] (đứng nhún nhảy tự nhiên trong Cảnh 1)
                # - Phần Look 1 (t1_cut .. t2_cut): lấy từ [adult_start .. adult_start + dur_part2] (động tác đưa tay biến hình Look 1)
                # - Phần Look 2 (t2_cut .. 8.0s): lấy từ [adult_start .. scene1_end] (động tác biến hình Look 2 & tạo dáng cuối Cảnh 1)
                p1_start = max(adult_start, scene1_end - dur_part1)
                fc_adult = (
                    f"[0:v]trim=start={p1_start:.3f}:duration={dur_part1:.3f},setpts=PTS-STARTPTS,fps=30[v0];"
                    f"[0:v]trim=start={adult_start:.3f}:duration={dur_part2:.3f},setpts=PTS-STARTPTS,fps=30[v1];"
                    f"[0:v]trim=start={adult_start:.3f}:duration={dur_part3:.3f},setpts=PTS-STARTPTS,fps=30[v2];"
                    f"[v0][v1][v2]concat=n=3:v=1:a=0,fps=30,setpts=PTS-STARTPTS[vout];"
                    f"[0:a]atrim=start=0:duration={float(chunk_sec)+0.12:.3f},asetpts=PTS-STARTPTS[aout]"
                )
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-i", ref_video_path,
                        "-filter_complex", fc_adult,
                        "-map", "[vout]", "-map", "[aout]",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                        "-r", "30", "-g", "30", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
                        adult_clip_path,
                    ],
                    capture_output=True,
                    timeout=60,
                )

        transitions = scene_transitions_all[idx] if idx < len(scene_transitions_all) else []

        scenes_data.append(
            {
                "id": sc_id,
                "scene_index": sc_num,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration": chunk_sec,
                "fps": 30,
                "start_frame": 1,
                "end_frame": int(chunk_sec * 30) + 1,
                "ref_clip_filename": clip_filename,
                "ref_clip_path": clip_path,
                "adult_safe_clip_path": adult_clip_path if (adult_clip_path and os.path.exists(adult_clip_path)) else "",
                "ref_clip_thumb": thumb_clip_path if os.path.exists(thumb_clip_path) else "",
                "keyframe_sheet_path": kf_sheet_path if os.path.exists(kf_sheet_path) else "",
                "transitions": transitions,
            }
        )

    if cache_meta_path and ref_cache_dir and scenes_data and all(os.path.isfile(s["ref_clip_path"]) and os.path.getsize(s["ref_clip_path"]) > 0 for s in scenes_data):
        try:
            os.makedirs(ref_cache_dir, exist_ok=True)
            aud_fn = ""
            if os.path.isfile(master_audio_path) and os.path.getsize(master_audio_path) > 0:
                aud_fn = os.path.basename(master_audio_path)
                shutil.copy2(master_audio_path, os.path.join(ref_cache_dir, aud_fn))
            sf_list = []
            for s in scenes_data:
                cf = os.path.basename(s["ref_clip_path"])
                shutil.copy2(s["ref_clip_path"], os.path.join(ref_cache_dir, cf))
                af = ""
                if s.get("adult_safe_clip_path") and os.path.isfile(s["adult_safe_clip_path"]):
                    af = os.path.basename(s["adult_safe_clip_path"])
                    shutil.copy2(s["adult_safe_clip_path"], os.path.join(ref_cache_dir, af))
                tf = ""
                if s.get("ref_clip_thumb") and os.path.isfile(s["ref_clip_thumb"]):
                    tf = os.path.basename(s["ref_clip_thumb"])
                    shutil.copy2(s["ref_clip_thumb"], os.path.join(ref_cache_dir, tf))
                kf = ""
                if s.get("keyframe_sheet_path") and os.path.isfile(s["keyframe_sheet_path"]):
                    kf = os.path.basename(s["keyframe_sheet_path"])
                    shutil.copy2(s["keyframe_sheet_path"], os.path.join(ref_cache_dir, kf))
                sf_list.append({
                    "id": s["id"],
                    "scene_index": s["scene_index"],
                    "start_sec": s["start_sec"],
                    "end_sec": s["end_sec"],
                    "clip": cf,
                    "adult": af,
                    "thumb": tf,
                    "kf": kf,
                })
            with open(cache_meta_path, "w", encoding="utf-8") as mf:
                json.dump({
                    "video_probe": probe,
                    "split_plan": split_plan,
                    "global_cuts_info": global_cuts_info,
                    "master_audio_filename": aud_fn,
                    "scenes_files": sf_list,
                }, mf, ensure_ascii=False)
        except Exception:
            pass

    return {
        "ok": True,
        "video_probe": probe,
        "split_plan": split_plan,
        "global_cuts_info": global_cuts_info,
        "master_audio_path": master_audio_path if os.path.exists(master_audio_path) else "",
        "scenes": scenes_data,
    }


# ==============================================================================
# 4. XÂY DỰNG PROMPT THEO TIMELINE 0.1s + INLINE ASSET CHIPS CHUẨN GOOGLE FLOW
# ==============================================================================

def extract_scene_last_frame_2k(video_path: str, out_png_path: str) -> str:
    """
    Cắt chính xác frame cuối (cách cuối 2 frame để tránh frame tối/blur) của Video Phân Cảnh trước
    (VD: `fashion_scene_s1_1080p.mp4`) và chuẩn hóa lên 2K (1536×2752) làm Ảnh Ref Mở Đầu nối tiếp cho Phân Cảnh sau!
    """
    if not video_path or not os.path.exists(video_path):
        return ""
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        n_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        target_idx = max(0, n_f - 2)
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_idx)
        ok, frm = cap.read()
        cap.release()
        if not ok or frm is None:
            return ""
        os.makedirs(os.path.dirname(os.path.abspath(out_png_path)), exist_ok=True)
        cv2.imwrite(out_png_path, frm)
        ensure_image_is_2k(out_png_path)
        return out_png_path if os.path.exists(out_png_path) else ""
    except Exception:
        return ""


def normalize_fashion_generation_mode(mode_val: str, default: str = "chained_i2v") -> str:
    """Chuẩn hóa `generation_mode`: `'google_vids'` | `'chained_i2v'` | `'video_ref'`."""
    raw = str(mode_val or "").strip().lower()
    if "vids" in raw:
        return "google_vids"
    if "i2v" in raw or "chained" in raw:
        return "chained_i2v"
    if "video" in raw or "ref" in raw:
        return "video_ref"
    return default


def build_scene_timeline_prompt(
    scene_info: dict,
    start_char_ref: dict,
    char_sheet_ref: dict = None,
    prompt_style: str = "timeline_pro",
    prev_scene_last_outfit: dict = None,
    prev_scene_last_frame_ref: dict = None,
    bpm_info: dict = None,
) -> dict:
    """
    Tạo cấu trúc Prompt cho từng phân cảnh của Thời Trang AI (Hỗ trợ cả 2 chế độ):
      - Chế độ 1 (`prompt_style == "chained_i2v"`): Hoàn toàn từ Image-to-Video + Timeline 0.1s chuẩn nhạc (không dùng video làm ref).
        + Phân cảnh 1: Dùng ảnh phòng ngủ (`07_Nhan_Vat_Basic_Phong_Ngu_2K.png`) làm frame đầu + Character Sheet (`01_Character_Sheet_4_Outfits_2K.png`).
        + Phân cảnh 2+: Tự động dùng ảnh Frame cuối của Phân cảnh trước (`scene_s1_last_frame_2k.png`) làm frame đầu + Character Sheet để nối tiếp hành động & trang phục!
      - Chế độ 2 (`prompt_style in ("timeline_pro", "concise_flow")`): Motion Control Video Ref (`jIps6` có đính kèm video tham chiếu).
        + Phân cảnh 1: Mở đầu từ ảnh phòng ngủ Basic (`07_Nhan_Vat_Basic_Phong_Ngu_2K.png`).
        + Phân cảnh 2+: Mở đầu nối tiếp trực tiếp từ ảnh Frame cuối của Phân cảnh 1 (`scene_s1_last_frame_2k.png`) đang mặc bộ đồ cuối của Phân cảnh 1!
    """
    sc_num = int(scene_info.get("scene_index") or 1)
    sc_id = scene_info.get("id") or f"s{sc_num}"
    dur = int(scene_info.get("duration") or 8)
    transitions = scene_info.get("transitions") or []
    ref_clip_fn = scene_info.get("ref_clip_filename") or f"ref_clip_{sc_id}_{dur}s.mp4"
    ref_vid_key = f"ref_video_{sc_id}"

    start_title = start_char_ref.get("filename") or os.path.basename(start_char_ref.get("path") or "02_Character_Sheet_Basic_Poses_2K.png")
    start_key = start_char_ref.get("asset_key") or "base_char_2k"

    overall_title = "01_Character_Sheet_4_Outfits_2K.png"
    overall_key = "overall_sheet_2k"

    _default_nv5_files = (
        "02_Character_Sheet_Basic_Poses_2K.png",
        "07_Nhan_Vat_Basic_Phong_Ngu_2K.png",
        "09_NV5_Phong_Tu_Go_Mo_Dau_2K.png",
        overall_title,
    )
    is_custom_char = start_title not in _default_nv5_files

    bg_title = (char_sheet_ref or {}).get("filename") or (start_title if is_custom_char else "07_Nhan_Vat_Basic_Phong_Ngu_2K.png")
    bg_key = (char_sheet_ref or {}).get("asset_key") or ("base_char_2k" if is_custom_char else "char_sheet_2k")
    if bg_title == overall_title:
        bg_title = start_title if is_custom_char else "07_Nhan_Vat_Basic_Phong_Ngu_2K.png"
        bg_key = start_key if is_custom_char else "char_sheet_2k"
    elif is_custom_char and bg_title in _default_nv5_files:
        # Khi người dùng đã chọn/upload Nhân Vật mới nhưng bg_title vẫn trỏ về ảnh mặc định của NV5,
        # tự động dùng chính ảnh Nhân Vật mới làm ảnh mở đầu & giữ nhận diện khuôn mặt!
        bg_title = start_title
        bg_key = start_key

    prev_lf_obj = prev_scene_last_frame_ref or scene_info.get("prev_scene_last_frame_ref") or {}
    prev_outf_obj = prev_scene_last_outfit or scene_info.get("prev_scene_last_outfit") or {}
    prev_lf_title = prev_lf_obj.get("filename") or f"scene_s{max(1, sc_num-1)}_last_frame_2k.png"
    prev_lf_key = prev_lf_obj.get("asset_key") or f"scene_s{max(1, sc_num-1)}_last_frame_2k"

    bpm_val = round(float((bpm_info or {}).get("estimated_bpm") or 140.0))
    beat_int = round(float((bpm_info or {}).get("beat_interval_sec") or 0.43), 2)

    segments = []

    # ==========================================================================
    # CHẾ ĐỘ A0: GOOGLE VIDS WEB OMNI 1080p (`google_vids`)
    # Gắn tối đa 3 Chip Ảnh 2K gốc trực tiếp (@Hình ảnh1, @Hình ảnh2, @Hình ảnh3):
    #   - Cảnh 1: [Ảnh phòng ngủ Basic 2K] + [Ảnh phẳng Bộ đồ 1 2K] + [Ảnh phẳng Bộ đồ 2 2K]
    #   - Cảnh 2+: [Frame cuối Cảnh 1 2K] + [Ảnh phẳng Bộ đồ 3 2K] + [Ảnh phẳng Bộ đồ 4 2K]
    # ==========================================================================
    if prompt_style in ("google_vids", "chained_i2v"):
        import fashion_ai_video_analyzer as fava

        choreo = fava.analyze_scene_choreography_and_hooks_for_i2v(
            ref_video_path=scene_info.get("ref_video_path") or scene_info.get("ref_clip_path") or "",
            scene_info=scene_info,
            bpm_info=bpm_info,
            template_meta=scene_info.get("template_meta"),
        )
        scene_info["i2v_choreography_profile"] = choreo.get("profile_id") or "dynamic_cv"
        move_feel_en = choreo.get("movement_feel_en") or (
            f"Stylish rhythmic approximately {bpm_val} BPM TikTok fashion transition groove (beat every {beat_int:.2f} seconds): "
            "light, graceful movement with soft knees, relaxed shoulders, curved arm paths and natural fabric physics."
        )

        if sc_num == 1:
            t1 = round(float(transitions[0]["timestamp_sec"]) if len(transitions) >= 1 else 3.43, 2)
            t2 = round(float(transitions[1]["timestamp_sec"]) if len(transitions) >= 2 else 6.86, 2)
            out1 = transitions[0]["outfit"] if len(transitions) >= 1 else {}
            out2 = transitions[1]["outfit"] if len(transitions) >= 2 else {}
            out1_en = out1.get("en_desc") or out1.get("short_desc") or "exact Look 1 outfit and accessories"
            out2_en = out2.get("en_desc") or out2.get("short_desc") or "exact Look 2 outfit and accessories"
            out1_title = out1.get("filename") or os.path.basename(out1.get("path") or overall_title)
            out1_key = out1.get("id") or out1_title
            out2_title = out2.get("filename") or os.path.basename(out2.get("path") or overall_title)
            out2_key = out2.get("id") or out2_title
            use_individual_sheets = len(transitions) >= 1 and bool(out1.get("filename") or out1.get("path"))
            b1 = choreo.get("s1_blocks") or {}

            segments.append({"type": "text", "text": f"Create an {dur}-second photorealistic vertical 9:16 fashion transformation video.\n\nREFERENCES\nUse "})
            segments.append({"type": "media", "asset_key": bg_key, "title": bg_title})
            segments.append({"type": "text", "text": " as the exact opening frame composition, room environment, lighting, camera angle, woman's facial identity, hairstyle, and opening basic outfit.\n"})
            if use_individual_sheets:
                segments.append({"type": "text", "text": "Use "})
                segments.append({"type": "media", "asset_key": out1_key, "title": out1_title})
                segments.append({"type": "text", "text": f" strictly as the flatlay wardrobe reference for EXACT LOOK 1 ({out1_en}). Never show the flatlay collage sheet itself in the video.\n"})
                if len(transitions) >= 2 and (out2.get("filename") or out2.get("path")):
                    segments.append({"type": "text", "text": "Use "})
                    segments.append({"type": "media", "asset_key": out2_key, "title": out2_title})
                    segments.append({"type": "text", "text": f" strictly as the flatlay wardrobe reference for EXACT LOOK 2 ({out2_en}). Completely replace Look 1's accessories and never show the flatlay collage sheet itself in the video.\n\n"})
                else:
                    segments.append({"type": "text", "text": "\n"})
            elif not is_custom_char:
                segments.append({"type": "text", "text": "Use "})
                segments.append({"type": "media", "asset_key": overall_key, "title": overall_title})
                segments.append({"type": "text", "text": " strictly for the exact Look 1 and Look 2 outfits. Never show the reference sheet in the video.\n\n"})
            else:
                segments.append({"type": "text", "text": "\n"})

            segments.append({"type": "text", "text": "IDENTITY AND CAMERA\nPreserve the exact woman's face, natural skin texture, body proportions, and hairstyle from "})
            segments.append({"type": "media", "asset_key": bg_key, "title": bg_title})
            segments.append({"type": "text", "text": " throughout the entire clip.\nKeep the exact room background from "})
            segments.append({"type": "media", "asset_key": bg_key, "title": bg_title})
            segments.append({
                "type": "text",
                "text": (
                    " locked and unchanged.\n"
                    "Locked tripod camera, continuous full-body head-to-toe 9:16 framing with both feet clearly visible on the floor at all times.\n\n"
                    "MOVEMENT\n"
                    f"{move_feel_en}\n\n"
                    "TIMELINE (LOCAL CLIP TIME)\n"
                    f"{b1.get('open_range', '0.00-1.30')}: Start in the exact opening pose, room, and basic outfit from "
                ),
            })
            segments.append({"type": "media", "asset_key": bg_key, "title": bg_title})
            segments.append({
                "type": "text",
                "text": (
                    f". {b1.get('open_en', 'She smiles warmly at the camera and sways gently to the opening beat.')}\n"
                    f"{b1.get('build1_range', f'1.30-{max(1.40, t1-0.80):.2f}')}: {b1.get('build1_en', 'She opens both forearms outward at waist level and performs a playful rhythmic hand gesture.')}\n"
                    f"{b1.get('prep1_range', f'{max(1.40, t1-0.80):.2f}-{t1:.2f}')}: {b1.get('prep1_en', 'She prepares the crisp transformation gesture on the pre-beat.')}\n"
                    f"AT {t1:.2f}: {b1.get('at1_trigger_en', 'At the exact peak of the gesture, perform an instantaneous matched-pose cut-free wardrobe switch into EXACT LOOK 1')} from "
                ),
            })
            segments.append({"type": "media", "asset_key": out1_key if use_individual_sheets else overall_key, "title": out1_title if use_individual_sheets else overall_title})
            segments.append({
                "type": "text",
                "text": (
                    f": {out1_en}. Switch the entire outfit, shoes, and accessories cleanly in one single frame with zero dissolve while preserving her face, moving arm trajectory, and background.\n"
                ),
            })
            if len(transitions) >= 2:
                segments.append({
                    "type": "text",
                    "text": (
                        f"{b1.get('post1_range', f'{t1:.2f}-{min(t2-0.55, t1+1.65):.2f}')}: {b1.get('post1_en', 'Continue the arm movement seamlessly after the switch and sway her shoulders gracefully.')}\n"
                        f"{b1.get('build2_range', f'{min(t2-0.55, t1+1.65):.2f}-{max(t1+1.8, t2-0.35):.2f}')}: {b1.get('build2_en', 'She takes one small in-place step, softly tilts her head, and brings her hands gracefully toward her waist.')}\n"
                        f"{b1.get('prep2_range', f'{max(t1+1.8, t2-0.35):.2f}-{t2:.2f}')}: {b1.get('prep2_en', 'She executes the crisp wrist/hand accent on the musical beat.')}\n"
                        f"AT {t2:.2f}: {b1.get('at2_trigger_en', 'On the exact musical beat accent, perform an instantaneous matched-pose wardrobe switch into EXACT LOOK 2')} from "
                    ),
                })
                segments.append({"type": "media", "asset_key": out2_key if use_individual_sheets else overall_key, "title": out2_title if use_individual_sheets else overall_title})
                segments.append({
                    "type": "text",
                    "text": (
                        f": {out2_en}. Completely remove all Look 1 accessories/necklaces and replace with the exact Look 2 set while maintaining the same face, hairstyle, body position, and continuous arm motion.\n"
                        f"{b1.get('post2_range', f'{t2:.2f}-7.55')}: {b1.get('post2_en', 'Her arm settles smoothly at her waist as the garment hem settles naturally.')}\n"
                    ),
                })
            else:
                segments.append({
                    "type": "text",
                    "text": (
                        f"{t1:.2f}-7.55: {b1.get('post1_en', 'Continue the arm movement naturally after the switch and showcase the full silhouette of Look 1.')}\n"
                    ),
                })
            segments.append({
                "type": "text",
                "text": (
                    f"{b1.get('end_range', f'7.55-{dur:.2f}')}: {b1.get('end_en', 'Settle into a poised front-facing full-body pose smiling softly at the camera to connect seamlessly to the next clip.')}\n\n"
                    "AUDIO AND NEGATIVE CONSTRAINTS\n"
                    "Silent visual clip only: no speech, singing, voiceover, music, or lip-syncing. No camera zoom, no camera pan, no face drift, no leftover accessories from previous outfit, no morphing/melting clothes, no text/captions, and no split-screen or visible product sheet panels."
                ),
            })
        else:
            t3 = round(float(transitions[0]["timestamp_sec"]) if len(transitions) >= 1 else 2.29, 2)
            t4 = round(float(transitions[1]["timestamp_sec"]) if len(transitions) >= 2 else 4.86, 2)
            out3 = transitions[0]["outfit"] if len(transitions) >= 1 else {}
            out4 = transitions[1]["outfit"] if len(transitions) >= 2 else {}
            prev_en = prev_outf_obj.get("en_desc") or prev_outf_obj.get("short_desc") or "exact ending outfit from the previous clip"
            prev_outf_title = prev_outf_obj.get("filename") or os.path.basename(prev_outf_obj.get("path") or "")
            prev_outf_key = prev_outf_obj.get("id") or prev_outf_title
            out3_en = out3.get("en_desc") or out3.get("short_desc") or "exact Look 3 outfit and accessories"
            out4_en = out4.get("en_desc") or out4.get("short_desc") or "exact Look 4 outfit and accessories"
            out3_title = out3.get("filename") or os.path.basename(out3.get("path") or overall_title)
            out3_key = out3.get("id") or out3_title
            out4_title = out4.get("filename") or os.path.basename(out4.get("path") or overall_title)
            out4_key = out4.get("id") or out4_title
            use_individual_sheets = len(transitions) >= 1 and bool(out3.get("filename") or out3.get("path"))
            b2 = dict(choreo.get("s2_blocks") or {})
            if len(transitions) == 3:
                t5 = float(transitions[2]["timestamp_sec"])
                b2["turn_range"] = f"6.15-{t5:.2f}"
                b2["end_range"] = f"{t5:.2f}-{dur:.2f}"
                b2["end_en"] = "Settle into a balanced final pose wearing EXACT LOOK 5, retaining all its accessories."
            open_pose_en = choreo.get("opening_pose_en") or f"Her hands and feet begin in the exact ending pose of Clip {sc_num-1}."

            segments.append({"type": "text", "text": f"Create an {dur}-second photorealistic vertical 9:16 continuation of the previous fashion video.\n\nREFERENCES AND CONTINUITY\nUse "})
            segments.append({"type": "media", "asset_key": prev_lf_key, "title": prev_lf_title})
            segments.append({"type": "text", "text": f" as the exact first frame, continuing the exact same woman, facial identity, hairstyle, room background, warm lighting, locked full-body 9:16 camera, and starting outfit ({prev_en}).\n"})
            if len(transitions) == 0:
                if prev_outf_title:
                    segments.append({"type": "text", "text": "Use "})
                    segments.append({"type": "media", "asset_key": prev_outf_key, "title": prev_outf_title})
                    segments.append({"type": "text", "text": f" strictly as the flatlay wardrobe reference to preserve every detail of the current outfit ({prev_en}) throughout this clip. Never show the flatlay collage sheet in the video.\n\n"})
                else:
                    segments.append({"type": "text", "text": "\n"})
                segments.append({
                    "type": "text",
                    "text": (
                        f"{open_pose_en}\n{move_feel_en}\n\n"
                        "TIMELINE (LOCAL CLIP TIME)\n"
                        f"{b2.get('open_range', '0.00-1.50')}: Start seamlessly from "
                    ),
                })
                segments.append({"type": "media", "asset_key": prev_lf_key, "title": prev_lf_title})
                segments.append({
                    "type": "text",
                    "text": (
                        f". {b2.get('open_en', f'Continue the gentle body sway from Clip {sc_num-1} without resetting.')}\n"
                        f"1.50-4.50: {b2.get('build3_en', 'She places her right hand gently on her hip and gestures gracefully to the beat while showcasing the outfit.')}\n"
                        f"4.50-7.20: {b2.get('turn_en', 'She angles her body slightly to showcase the silhouette and fabric drape while keeping her gaze on the camera.')}\n"
                        f"7.20-{dur:.2f}: {b2.get('end_en', 'Settle into a balanced, confident final fashion lookbook pose.')}\n\n"
                        "AUDIO AND NEGATIVE CONSTRAINTS\n"
                        "Silent visual clip only: no speech, singing, voiceover, music, or lip-syncing. No camera movement, no face drift, no morphing clothes, no captions, and no visible reference-sheet panels."
                    ),
                })
            else:
                if use_individual_sheets:
                    segments.append({"type": "text", "text": "Use "})
                    segments.append({"type": "media", "asset_key": out3_key, "title": out3_title})
                    segments.append({"type": "text", "text": f" strictly as the flatlay wardrobe reference for EXACT LOOK 3 ({out3_en}). Never show the flatlay collage sheet in the video.\n"})
                    if len(transitions) >= 2 and (out4.get("filename") or out4.get("path")):
                        segments.append({"type": "text", "text": "Use "})
                        segments.append({"type": "media", "asset_key": out4_key, "title": out4_title})
                        segments.append({"type": "text", "text": f" strictly as the flatlay wardrobe reference for EXACT LOOK 4 ({out4_en}). Never show the flatlay collage sheet in the video.\n\n"})
                    else:
                        segments.append({"type": "text", "text": "\n"})
                elif not is_custom_char:
                    segments.append({"type": "text", "text": "Use "})
                    segments.append({"type": "media", "asset_key": overall_key, "title": overall_title})
                    segments.append({"type": "text", "text": " strictly for the exact Look 3 and Look 4 outfits. Never show the reference sheet in the video.\n\n"})
                else:
                    segments.append({"type": "text", "text": "\n"})

                segments.append({
                    "type": "text",
                    "text": (
                        f"{open_pose_en}\n{move_feel_en}\n\n"
                        "TIMELINE (LOCAL CLIP TIME)\n"
                        f"{b2.get('open_range', '0.00-1.01')}: Start seamlessly from "
                    ),
                })
                segments.append({"type": "media", "asset_key": prev_lf_key, "title": prev_lf_title})
                segments.append({
                    "type": "text",
                    "text": (
                        f". {b2.get('open_en', f'Continue the gentle body sway from Clip {sc_num-1} without resetting.')}\n"
                        f"{b2.get('build3_range', f'1.01-{max(1.20, t3-0.30):.2f}')}: {b2.get('build3_en', 'She places her right hand gently on her hip and gestures gracefully with her left forearm.')}\n"
                        f"{b2.get('prep3_range', f'{max(1.20, t3-0.30):.2f}-{t3:.2f}')}: {b2.get('prep3_en', 'She prepares the transition gesture on the pre-beat without pausing.')}\n"
                        f"AT {t3:.2f}: {b2.get('at3_trigger_en', 'Perform an instantaneous matched-pose wardrobe switch into EXACT LOOK 3')} from "
                    ),
                })
                segments.append({"type": "media", "asset_key": out3_key if use_individual_sheets else overall_key, "title": out3_title if use_individual_sheets else overall_title})
                segments.append({
                    "type": "text",
                    "text": (
                        f": {out3_en}. Switch the complete outfit, shoes, and accessories in a single clean frame while preserving her facial identity, moving arm trajectory, and locked room.\n"
                    ),
                })
                if len(transitions) >= 2:
                    segments.append({
                        "type": "text",
                        "text": (
                            f"{b2.get('post3_range', f'{t3:.2f}-{min(t4-0.50, t3+1.30):.2f}')}: {b2.get('post3_en', 'Complete the hand movement naturally in Look 3 and take one short graceful step in place.')}\n"
                            f"{b2.get('build4_range', f'{min(t4-0.50, t3+1.30):.2f}-{max(t3+1.45, t4-0.30):.2f}')}: {b2.get('build4_en', 'She subtly angles her torso and brings her hand up toward her shoulder to prepare the next switch.')}\n"
                            f"{b2.get('prep4_range', f'{max(t3+1.45, t4-0.30):.2f}-{t4:.2f}')}: {b2.get('prep4_en', 'She executes the pre-beat transition accent while keeping her face fully visible.')}\n"
                            f"AT {t4:.2f}: {b2.get('at4_trigger_en', 'On the musical beat accent, switch instantaneously into EXACT LOOK 4')} from "
                        ),
                    })
                    segments.append({"type": "media", "asset_key": out4_key if use_individual_sheets else overall_key, "title": out4_title if use_individual_sheets else overall_title})
                    segments.append({
                        "type": "text",
                        "text": (
                            f": {out4_en}. Remove the previous Look 3 accessories completely and switch coherently in the same visual instant.\n"
                            f"{b2.get('post4_range', f'{t4:.2f}-6.15')}: {b2.get('post4_en', 'Continue the hand movement smoothly after the switch and settle into a composed posture.')}\n"
                        ),
                    })
                else:
                    segments.append({
                        "type": "text",
                        "text": f"{t3:.2f}-6.15: {b2.get('post3_en', 'Complete the hand movement naturally in Look 3.')}\n",
                    })
                if len(transitions) == 3:
                    out5 = transitions[2]["outfit"]
                    segments.append({"type": "text", "text": f"AT {t5:.2f}: On the beat, make one matched-pose wardrobe switch into EXACT LOOK 5 from "})
                    segments.append({"type": "media", "asset_key": out5.get("id") or out5["filename"], "title": out5["filename"]})
                    segments.append({"type": "text", "text": f": {out5.get('en_desc') or out5.get('short_desc')}. Replace the complete outfit, shoes and accessories at once, preserving face, room and gesture.\n"})
                segments.append({
                    "type": "text",
                    "text": (
                        f"{b2.get('turn_range', '6.15-7.35')}: {b2.get('turn_en', 'She angles her body slightly to showcase the silhouette and accessories while keeping her gaze on the camera.')}\n"
                        f"{b2.get('end_range', f'7.35-{dur:.2f}')}: {b2.get('end_en', 'Settle into a balanced, confident final fashion lookbook pose.')}\n\n"
                        "AUDIO AND NEGATIVE CONSTRAINTS\n"
                        "Silent visual clip only: no speech, singing, voiceover, music, or lip-syncing. No camera movement, no face drift, no leftover accessories from previous outfits, no morphing clothes, no captions, and no visible reference-sheet panels."
                    ),
                })

    # ==========================================================================
    # CHẾ ĐỘ A: CHAINED IMAGE-TO-VIDEO + TIMELINE 0.1s CHUẨN NHẠC (`chained_i2v`)
    # Phân tích động tác & Hook biến hình trực tiếp từ Bảng Keyframe 0.5s + Video gốc!
    # ==========================================================================
    elif prompt_style == "chained_i2v":
        import fashion_ai_video_analyzer as fava

        choreo = fava.analyze_scene_choreography_and_hooks_for_i2v(
            ref_video_path=scene_info.get("ref_video_path") or scene_info.get("ref_clip_path") or "",
            scene_info=scene_info,
            bpm_info=bpm_info,
            template_meta=scene_info.get("template_meta"),
        )
        scene_info["i2v_choreography_profile"] = choreo.get("profile_id") or "dynamic_cv"
        move_feel_en = choreo.get("movement_feel_en") or (
            f"Use a relaxed approximately {bpm_val} BPM dance feel: gentle weight transfers approximately every {beat_int:.2f} seconds, with occasional smaller wrist accents between them.\n"
            "Her movement is light, graceful and physically connected: soft knees, relaxed shoulders, curved arm paths and loose wrists. Hair and fabric follow her motion with a small natural delay."
        )

        if sc_num == 1:
            t1 = round(float(transitions[0]["timestamp_sec"]) if len(transitions) >= 1 else 3.43, 2)
            t2 = round(float(transitions[1]["timestamp_sec"]) if len(transitions) >= 2 else 6.86, 2)
            out1 = transitions[0]["outfit"] if len(transitions) >= 1 else {}
            out2 = transitions[1]["outfit"] if len(transitions) >= 2 else {}
            out1_en = out1.get("en_desc") or out1.get("short_desc") or "exact Look 1 outfit and accessories from the character sheet"
            out2_en = out2.get("en_desc") or out2.get("short_desc") or "exact Look 2 outfit and accessories from the character sheet"
            b1 = choreo.get("s1_blocks") or {}

            segments.append({"type": "text", "text": f"Create an {dur}-second photorealistic vertical 9:16 fashion transformation video.\n\nREFERENCES\nUse the supplied bedroom image "})
            segments.append({"type": "media", "asset_key": bg_key, "title": bg_title})
            segments.append({"type": "text", "text": " as the exact opening composition, character identity, basic outfit, room geometry and lighting reference.\nUse the supplied character sheet "})
            segments.append({"type": "media", "asset_key": overall_key, "title": overall_title})
            segments.append({
                "type": "text",
                "text": (
                    " only for the same woman's identity and the exact Look 1 and Look 2 outfits. The sheet must never appear in the video.\n\n"
                    "IDENTITY AND CAMERA\n"
                    "Preserve her facial structure, long wavy brown hair, natural skin texture, body proportions and adult appearance.\n"
                    "Keep the warm bedroom, brown curtains, bed and cabinet consistent.\n"
                    "Locked camera, continuous full-body framing with both feet visible, consistent subject scale and floor contact.\n\n"
                    "MOVEMENT\n"
                    f"{move_feel_en}\n\n"
                    "TIMELINE — LOCAL CLIP TIME\n\n"
                    f"{b1.get('open_range', '0.00–1.30')}:\n"
                    f"{b1.get('open_en', 'Begin in the exact basic outfit and sway gently to the opening beat.')}\n\n"
                    f"{b1.get('build1_range', f'1.30–{max(1.40, t1-0.80):.2f}')}:\n"
                    f"{b1.get('build1_en', 'She opens both forearms outward at waist level and performs a playful rhythmic hand gesture.')}\n\n"
                    f"{b1.get('prep1_range', f'{max(1.40, t1-0.80):.2f}–{t1:.2f}')}:\n"
                    f"{b1.get('prep1_en', 'She shifts her weight onto her supporting leg and prepares the transformation gesture on the pre-beat.')}\n\n"
                    f"AT {t1:.2f}:\n"
                    f"{b1.get('at1_trigger_en', 'At the peak of the gesture, perform one instantaneous matched-pose wardrobe switch into EXACT LOOK 1')}:\n"
                    f"{out1_en}.\n"
                    "The entire outfit and its accessories switch together in a single clean visual beat.\n"
                    "Preserve her face, body position, arm trajectory and bedroom. No dissolve or intermediate clothing.\n\n"
                ),
            })
            if len(transitions) >= 2:
                segments.append({
                    "type": "text",
                    "text": (
                        f"{b1.get('post1_range', f'{t1:.2f}–{min(t2-0.55, t1+1.65):.2f}')}:\n"
                        f"{b1.get('post1_en', 'Continue the same hand movement after the switch and sway her shoulders gracefully.')}\n\n"
                        f"{b1.get('build2_range', f'{min(t2-0.55, t1+1.65):.2f}–{max(t1+1.8, t2-0.35):.2f}')}:\n"
                        f"{b1.get('build2_en', 'She takes one small in-place step, softly tilts her head and brings both relaxed hands toward her upper chest.')}\n\n"
                        f"{b1.get('prep2_range', f'{max(t1+1.8, t2-0.35):.2f}–{t2:.2f}')}:\n"
                        f"{b1.get('prep2_en', 'She makes a small downward knee pulse and prepares the second switch on the musical beat.')}\n\n"
                        f"AT {t2:.2f}:\n"
                        f"{b1.get('at2_trigger_en', 'On the musical beat accent, switch instantaneously into EXACT LOOK 2 from the character sheet')}:\n"
                        f"{out2_en}.\n"
                        "Replace the complete Look 1 accessory set with the exact Look 2 set.\n"
                        "Maintain the same identity, body position and continuous arm movement.\n\n"
                        f"{b1.get('post2_range', f'{t2:.2f}–7.58')}:\n"
                        f"{b1.get('post2_en', 'She completes the arm follow-through and settles her weight smoothly onto her supporting leg.')}\n\n"
                    ),
                })
            else:
                segments.append({
                    "type": "text",
                    "text": (
                        f"{t1:.2f}–{min(dur-0.45, max(t1+1.60, 6.20)):.2f}:\n"
                        f"{b1.get('post1_en', 'Continue the same hand movement after the switch and sway her shoulders gracefully.')}\n\n"
                        f"{min(dur-0.45, max(t1+1.60, 6.20)):.2f}–7.58:\n"
                        f"{b1.get('build2_en', 'She takes one small in-place step, softly tilts her head and showcases the full silhouette of Look 1.')}\n\n"
                    ),
                })
            segments.append({
                "type": "text",
                "text": (
                    f"{b1.get('end_range', f'7.58–{dur:.2f}')}:\n"
                    f"{b1.get('end_en', 'She settles into a balanced front-facing pose with a gentle smile. End in this precise pose to connect to the next clip.')}\n\n"
                    "AUDIO AND MOUTH\n"
                    "Generate a silent visual clip. No speech, singing, humming, breathing performance or sound effects.\n"
                    "Her lips may remain softly closed or make tiny silent expressive movements.\n"
                    "Do not invent lyric-specific lip synchronization without the original audio reference.\n\n"
                    "AVOID\n"
                    "Face drift, body reshaping, extra fingers, rigid elbows, robotic dance, foot sliding, jumping, camera cuts, camera movement, flashing light, magical particles, melting fabric, partial outfits, mixed accessories, text, captions, labels, logos, duplicated people or visible reference-sheet panels."
                ),
            })
        else:
            # Phân cảnh 2+: Mở đầu từ Frame cuối của Phân cảnh trước (`scene_s1_last_frame_2k.png`) + Character Sheet!
            t3 = round(float(transitions[0]["timestamp_sec"]) if len(transitions) >= 1 else 2.29, 2)
            t4 = round(float(transitions[1]["timestamp_sec"]) if len(transitions) >= 2 else 4.86, 2)
            out3 = transitions[0]["outfit"] if len(transitions) >= 1 else {}
            out4 = transitions[1]["outfit"] if len(transitions) >= 2 else {}
            prev_en = prev_outf_obj.get("en_desc") or prev_outf_obj.get("short_desc") or "yellow tiered mini dress, white socks, yellow ballet flats and the precise matching accessories"
            out3_en = out3.get("en_desc") or out3.get("short_desc") or "exact Look 3 outfit and accessories from the character sheet"
            out4_en = out4.get("en_desc") or out4.get("short_desc") or "exact Look 4 outfit and accessories from the character sheet"
            b2 = choreo.get("s2_blocks") or {}
            open_pose_en = choreo.get("opening_pose_en") or "Her hands begin in the exact ending pose of Clip 1, feet close together, weight balanced."

            segments.append({"type": "text", "text": f"Create an {dur}-second photorealistic vertical 9:16 continuation of the previous fashion video.\n\nOPENING AND CONTINUITY\nUse the final frame of Clip {sc_num-1} "})
            segments.append({"type": "media", "asset_key": prev_lf_key, "title": prev_lf_title})
            segments.append({"type": "text", "text": f" as the exact first frame.\nContinue the same woman, bedroom, warm lighting, locked full-body camera, subject scale, facial identity and floor position.\nShe begins in EXACT LOOK 2: {prev_en} from the character sheet "})
            segments.append({"type": "media", "asset_key": overall_key, "title": overall_title})
            segments.append({
                "type": "text",
                "text": (
                    f".\n{open_pose_en}\n\n"
                    f"{move_feel_en}\n\n"
                    "TIMELINE — LOCAL CLIP TIME\n\n"
                    f"{b2.get('open_range', '0.00–1.01')}:\n"
                    f"{b2.get('open_en', f'Continue the gentle body sway from Clip {sc_num-1} without resetting.')}\n\n"
                    f"{b2.get('build3_range', f'1.01–{max(1.20, t3-0.30):.2f}')}:\n"
                    f"{b2.get('build3_en', 'She places her right hand gently on her right hip and gestures gracefully with her left forearm.')}\n\n"
                    f"{b2.get('prep3_range', f'{max(1.20, t3-0.30):.2f}–{t3:.2f}')}:\n"
                    f"{b2.get('prep3_en', 'She prepares the transition gesture on the pre-beat without pausing.')}\n\n"
                    f"AT {t3:.2f}:\n"
                    f"{b2.get('at3_trigger_en', 'Perform an instantaneous matched-pose switch into EXACT LOOK 3')}:\n"
                    f"{out3_en}, exactly as shown in Look 3.\n"
                    "The full outfit and accessories change together.\n"
                    "Keep her facial identity and preserve the moving hand's trajectory. No intermediate outfit.\n\n"
                ),
            })
            if len(transitions) >= 2:
                segments.append({
                    "type": "text",
                    "text": (
                        f"{b2.get('post3_range', f'{t3:.2f}–{min(t4-0.50, t3+1.30):.2f}')}:\n"
                        f"{b2.get('post3_en', 'Complete the hand movement naturally in Look 3 and take one short graceful step in place.')}\n\n"
                        f"{b2.get('build4_range', f'{min(t4-0.50, t3+1.30):.2f}–{max(t3+1.45, t4-0.30):.2f}')}:\n"
                        f"{b2.get('build4_en', 'She subtly angles her torso and brings her hand up toward her shoulder to prepare the next switch.')}\n\n"
                        f"{b2.get('prep4_range', f'{max(t3+1.45, t4-0.30):.2f}–{t4:.2f}')}:\n"
                        f"{b2.get('prep4_en', 'She executes the pre-beat transition accent while keeping her face fully visible.')}\n\n"
                        f"AT {t4:.2f}:\n"
                        f"{b2.get('at4_trigger_en', 'On the musical beat accent, switch instantaneously into EXACT LOOK 4 from the character sheet')}:\n"
                        f"{out4_en}.\n"
                        "The hairstyle, glasses, clothing and accessories switch coherently in the same visual instant.\n"
                        "Preserve her face, head position and body proportions.\n"
                        "Remove the previous Look 3 accessory set.\n\n"
                        f"{b2.get('post4_range', f'{t4:.2f}–6.15')}:\n"
                        f"{b2.get('post4_en', 'Continue the hand movement smoothly after the switch and settle into a composed posture.')}\n\n"
                    ),
                })
            else:
                segments.append({
                    "type": "text",
                    "text": (
                        f"{t3:.2f}–6.15:\n"
                        f"{b2.get('post3_en', 'Complete the hand movement naturally in Look 3 and take one short graceful step in place.')}\n\n"
                    ),
                })
            segments.append({
                "type": "text",
                "text": (
                    f"{b2.get('turn_range', '6.15–7.35')}:\n"
                    f"{b2.get('turn_en', 'She angles her body slightly to showcase the silhouette and accessories while keeping her gaze on the camera.')}\n\n"
                    f"{b2.get('end_range', f'7.35–{dur:.2f}')}:\n"
                    f"{b2.get('end_en', 'Settle into a balanced, confident final fashion lookbook pose.')}\n\n"
                    "AUDIO AND MOUTH\n"
                    "Generate a silent visual clip: no singing, speech, humming or sound effects.\n"
                    "She may make subtle silent mouth expressions, but should not perform audible vocals.\n"
                    "The original music will be added continuously during editing.\n\n"
                    "AVOID\n"
                    "Identity changes, exaggerated hip motion, rigid posing, sudden limb snaps, foot sliding, floating feet, extra fingers, glasses warping, mixed outfits, leftover bags, duplicate accessories, magical transformation effects, dissolves, camera movement, background changes, captions, labels and reference-sheet layouts."
                ),
            })

    # ==========================================================================
    # CHẾ ĐỘ B: MOTION CONTROL VIDEO REF (`timeline_pro` / `concise_flow`)
    # Phân cảnh 2+ BẮT BUỘC dùng ảnh Frame cuối của Phân cảnh 1 (`scene_s1_last_frame_2k.png`) làm ảnh mở đầu nối tiếp!
    # ==========================================================================
    else:
        include_overall_sheet = (not is_custom_char) and (not scene_info.get("disable_overall_sheet")) and len(transitions) <= 2
        if sc_num == 1:
            segments.append({"type": "text", "text": "Tạo 1 video mới hoàn toàn, có nhân vật là "})
            segments.append({"type": "media", "asset_key": start_key, "title": start_title})
            if include_overall_sheet:
                segments.append({"type": "text", "text": " cùng bảng tổng thể các bộ đồ "})
                segments.append({"type": "media", "asset_key": overall_key, "title": overall_title})
            segments.append({"type": "text", "text": " , nhân vật có hành động như video tham chiếu "})
            segments.append({"type": "media", "asset_key": ref_vid_key, "title": ref_clip_fn})
            segments.append({"type": "text", "text": " , bối cảnh căn phòng giữ cố định như ảnh "})
            segments.append({"type": "media", "asset_key": bg_key, "title": bg_title})
            segments.append({"type": "text", "text": " , mở đầu video nhân vật mặc bộ đồ Basic như trong ảnh "})
            segments.append({"type": "media", "asset_key": bg_key, "title": bg_title})
        else:
            # Phân cảnh 2+: Nối tiếp từ Frame cuối của Phân cảnh trước (`scene_s1_last_frame_2k.png`) và mặc bộ đồ cuối của Phân cảnh trước!
            prev_outf_name = prev_outf_obj.get("name") or prev_outf_obj.get("filename") or "bộ đồ cuối của Phân cảnh 1"
            segments.append({"type": "text", "text": f"Tạo 1 video mới hoàn toàn nối tiếp Phân cảnh {sc_num-1}, có nhân vật là "})
            segments.append({"type": "media", "asset_key": start_key, "title": start_title})
            if include_overall_sheet:
                segments.append({"type": "text", "text": " cùng bảng tổng thể các bộ đồ "})
                segments.append({"type": "media", "asset_key": overall_key, "title": overall_title})
            segments.append({"type": "text", "text": " , nhân vật có hành động nối tiếp như video tham chiếu "})
            segments.append({"type": "media", "asset_key": ref_vid_key, "title": ref_clip_fn})
            segments.append({"type": "text", "text": f" , bắt đầu video từ đúng khung hình cuối của Phân cảnh {sc_num-1} là ảnh "})
            segments.append({"type": "media", "asset_key": prev_lf_key, "title": prev_lf_title})
            segments.append({"type": "text", "text": f" (giữ nguyên bối cảnh căn phòng, tư thế và đang mặc {prev_outf_name} từ cuối Phân cảnh {sc_num-1})"})

        for tr_idx, tr in enumerate(transitions):
            ts_col = tr["timestamp_colon"]
            outf = tr["outfit"]
            o_title = outf.get("filename") or os.path.basename(outf.get("path") or "outfit_2K.png")
            o_key = outf.get("id") or o_title
            if tr_idx < 3:
                segments.append({"type": "text", "text": f", Tại giây {ts_col}, nhân vật đổi sang mặc bộ đồ "})
                segments.append({"type": "media", "asset_key": o_key, "title": o_title})
                segments.append({"type": "text", "text": " và tiếp tục có hành động như video"})
            else:
                segments.append({"type": "text", "text": f", Tại giây {ts_col}, nhân vật đổi sang mặc bộ đồ tiếp theo và tiếp tục có hành động như video"})

        segments.append({"type": "text", "text": ". Giữ nguyên bối cảnh căn phòng xuyên suốt, không hiển thị bất kỳ chữ viết hay nhãn chữ nào trên màn hình. Dùng nhạc của video gốc, nhân vật không nói chuyện và không có lời thoại."})

    # Ghép thành chuỗi hiển thị dễ đọc trên UI (với chip `[filename]`)
    display_parts = []
    for seg in segments:
        if seg["type"] == "text":
            display_parts.append(seg["text"])
        else:
            display_parts.append(f"[{seg['title']}]")
    display_prompt = "".join(display_parts)

    return {
        "display_prompt": display_prompt,
        "segments_spec": segments,
    }


def resolve_fashion_prompt_image_refs(segments_spec, asset_uuid_map, limit=5):
    """Every image mention must be an attached, resolved asset; never flatten to text."""
    refs = []
    for segment in segments_spec:
        if segment.get("type") != "media":
            continue
        key = segment.get("asset_key") or ""
        title = segment.get("title") or key
        if key.startswith("ref_video_") or title.lower().endswith(".mp4"):
            continue
        uid = asset_uuid_map.get(key) or asset_uuid_map.get(title)
        if not uid:
            raise ValueError(f"Missing uploaded image for inline chip: {title}")
        if uid not in refs:
            refs.append(uid)
    if len(refs) > limit:
        raise ValueError(f"Scene needs {len(refs)} image refs; supported limit is {limit}")
    return refs


def encode_flow_structured_prompt_Nj(segments_spec: list, asset_uuid_map: dict, fallback_text: str = "", allowed_image_uuids: list = None) -> list:
    """
    Chuyển đổi `segments_spec` thành cấu trúc Protobuf JSON `h_prompt = [None, None, [encoded_segments]]`
    chuẩn hàm `_.YP` + `Y9a` trong `flow_rpc_module.js`:
      - Đoạn văn bản (text): `[text_str]`
      - Chip tham chiếu ảnh inline (media mention): `[None, [[media_uuid, title_str]]]`
    """
    if not segments_spec:
        return [None, None, [[[fallback_text]]]]

    allowed_set = set(allowed_image_uuids) if allowed_image_uuids else None
    encoded_segments = []
    for seg in segments_spec:
        if seg.get("type") == "media":
            a_key = seg.get("asset_key") or ""
            title = seg.get("title") or a_key
            # Video tham chiếu được gửi riêng tại field 1 F4a(c.hL) của jIps6 (không đặt UUID video trong Nj để tránh lỗi schema [5])
            if str(a_key).startswith("ref_video_") or str(title).lower().endswith(".mp4"):
                continue
            m_uuid = (asset_uuid_map or {}).get(a_key) or (asset_uuid_map or {}).get(title)
            if m_uuid and (allowed_set is None or m_uuid in allowed_set):
                encoded_segments.append([None, [[m_uuid, title]]])
                continue
            # Nếu chưa có media_uuid hoặc không nằm trong 5 ảnh của cảnh thì nối tên file dạng text vào đoạn trước
            fallback_chip_txt = f" {title} "
            if encoded_segments and len(encoded_segments[-1]) == 1 and isinstance(encoded_segments[-1][0], str):
                encoded_segments[-1][0] += fallback_chip_txt
            else:
                encoded_segments.append([fallback_chip_txt])
        else:
            txt = str(seg.get("text") or "")
            if not txt:
                continue
            if encoded_segments and len(encoded_segments[-1]) == 1 and isinstance(encoded_segments[-1][0], str):
                encoded_segments[-1][0] += txt
            else:
                encoded_segments.append([txt])

    if not encoded_segments:
        encoded_segments = [[fallback_text or "Character follows the reference video motion."]]
    return [None, None, [encoded_segments]]


def build_continuity_2k_ref_prompt(outfit_info: dict) -> str:
    """
    Prompt tạo Ảnh Ref Nhân Vật 2K mặc sẵn bộ Outfit cuối của Phân cảnh trước trong đúng bối cảnh phòng ngủ/studio của Ảnh 1
    (Giống hệt 3 ảnh Ref 2K nhân vật mặc bộ đồ 1/2/3 đứng trong phòng ngủ ở hàng giữa trên giao diện Google Flow của người dùng!).
    """
    en_desc = outfit_info.get("en_desc") or outfit_info.get("short_desc") or "the exact outfit from the second reference image"
    return (
        "Ultra-realistic 2K 9:16 full-body vertical portrait starting from the exact room background, lighting, camera angle, "
        "and the exact young East Asian woman's face, hairstyle, and body proportions in Reference Image 1. "
        f"Change ONLY her clothing so she is now wearing {en_desc} exactly matching Reference Image 2 (keep exact garment cut, fabric pleats, color, and accessories). "
        "She stands naturally in the center of the exact same bedroom with brown curtains behind her and plush toys on the left cabinet, "
        "facing the camera with a gentle charming smile, photorealistic skin pores, 85mm f/2.0 lens, crisp 2K detail, zero text or watermarks."
    )


# ==============================================================================
# 4B. BỘ 4 PROMPT CHUẨN TẠO ẢNH THỜI TRANG 2K (TÁCH QUẦN ÁO & PHỤ KIỆN / MẶC FULL ĐỒ / TURNAROUND NV5)
# ==============================================================================

STANDARD_FASHION_PROMPTS = {
    "deconstructed_outfit_flatlay_2k": {
        "id": "deconstructed_outfit_flatlay_2k",
        "title": "Prompt #1 • Biến Ảnh Quần Áo Gốc → Ảnh Product Sheet Tách Riêng Quần Áo & Phụ Kiện Nền Trắng 2K (Chuẩn Ảnh 2)",
        "badge": "TÁCH ĐỒ & PHỤ KIỆN 2K",
        "sample_image": "/api/fashion_motion/demo_asset/05_Product_Sheet_Quan_Sooc_Trang_2K.png",
        "aspect_ratio": "4:5 (2048×2559 2K)",
        "guide_vn": (
            "Đính kèm 1 hoặc nhiều ảnh sản phẩm quần áo gốc (ảnh chụp mẫu mặc hoặc ảnh shop từ Kho Sản Phẩm). "
            "Prompt này sẽ bóc tách bộ quần áo gốc ra nền trắng tinh (#FFFFFF) ở cột trái và tự động phối kèm 4 phụ kiện tách rời (vòng cổ, túi xách, tất/scrunchie, giày) ở cột phải chuẩn 2K."
        ),
        "prompt_template": (
            "Ultra-clean commercial e-commerce deconstructed fashion outfit & accessories flat-lay product sheet (vertical 4:5, 2048x2559 2K resolution) "
            "isolated on a seamless pure solid white background (#FFFFFF) with soft natural contact shadows and zero text, labels, or watermarks. "
            "Extract and isolate the exact clothing items from the provided product reference image ({outfit_desc}) and pair them with coordinated styling accessories ({accessories_desc}) in a neat 2-column knolling layout:\n"
            "- LEFT COLUMN (55% width, Main Garments): Top-Left shows the main upper garment (top / blouse / shirt / jacket, or full dress) neatly laid flat with realistic 3D fabric volume, natural pleats, exact neckline, stitching, and hem drape; Bottom-Left shows the matching lower garment (high-waisted tailored shorts / wide-leg trousers / pleated skirt) positioned cleanly below the top garment with crisp waistband, buttons, and fabric weave.\n"
            "- RIGHT COLUMN (45% width, 4 Isolated Coordinated Accessories stacked vertically from top to bottom with generous white spacing): "
            "(1) Top-Right: delicate necklace / choker pendant or fashion eyewear; "
            "(2) Upper-Middle Right: structured shoulder bag / handbag with chain or strap neatly arranged; "
            "(3) Lower-Middle Right: pair of ribbed crew socks or fabric hair scrunchie / bracelet; "
            "(4) Bottom-Right: pair of matching footwear (Mary Jane bow ballet flats / minimalist sneakers / heels) angled naturally.\n"
            "Shot on Hasselblad H6D-100c 80mm macro lens, crisp high-key studio product lighting, 100% faithful garment cut, fabric texture, and colors from the reference image, 2K ultra-sharp photorealistic quality."
        ),
        "default_vars": {
            "outfit_desc": "pastel yellow halter twist-front peplum top and crisp white high-waisted pleated tailored shorts from the product reference image",
            "accessories_desc": "blue cord choker necklace with red flower pendant, cream leather flap shoulder bag with gold chain, white ribbed crew socks, and pastel yellow Mary Jane bow ballet flats",
        },
    },
    "wardrobe_4looks_character_sheet_2k": {
        "id": "wardrobe_4looks_character_sheet_2k",
        "title": "Prompt #2 • Tạo Ảnh Character Sheet Nhân Vật Mặc Full Các Bộ Đồ Look 1–Look 4 + Phụ Kiện 2K (Chuẩn Ảnh 3)",
        "badge": "MẶC FULL 4 BỘ ĐỒ 2K",
        "sample_image": "/api/fashion_motion/demo_asset/01_Character_Sheet_4_Outfits_2K.png",
        "aspect_ratio": "4:5 (2048×2559 2K)",
        "guide_vn": (
            "Đính kèm [Ảnh Character Sheet Nhân Vật (NV5) + Các Ảnh Product Sheet Bộ Đồ 1, 2, 3, 4]. "
            "Prompt này tạo ra bảng tổng hợp Nhân Vật Mặc Full Đồ (3 góc xoay trên + 4 Look toàn thân dưới + 6 ô Macro phụ kiện + Bảng 10 màu) để AI hiểu chính xác món đồ nào mặc ở đâu trên người mẫu."
        ),
        "prompt_template": (
            "Hyper-photorealistic vertical 4:5 (2048x2559 2K resolution) multi-look fashion wardrobe & turnaround character sheet on a clean warm-ivory studio background. "
            "Keep the female model's exact facial identity, chestnut-brown wavy hairstyle, Douyin glass-skin texture, and slender hourglass body proportions 100% identical to the attached Character Reference Image ({character_desc}), "
            "and dress her accurately in the exact outfits and accessories from the attached Product Sheet Reference Images ({looks_desc}) so it is 100% clear how each garment and accessory fits on her body:\n"
            "- TOP SECTION (Turnaround & Portrait of Look 1): Left 68% shows 3 full-body standing turnaround views side-by-side labeled in clean pill tags underneath ('Front', '3/4', 'Side') of the exact model wearing Look 1; Right 32% shows 1 large framed 'Close-up' beauty portrait (head, shoulders, and upper chest) showing her exact face, dewy skin pores, collar/neckline, and choker necklace in razor-sharp 2K detail.\n"
            "- BOTTOM SECTION (below a thin horizontal divider line): Left 68% shows 4 full-body front-facing lookbook panels side-by-side in rounded vertical frames labeled underneath ('Look 1', 'Look 2', 'Look 3', 'Look 4'), each showcasing the exact same model wearing one complete coordinated outfit variation from the product sheets from head to toe; "
            "Right 32% Top shows a 2x3 grid of 6 framed square macro accessory callout boxes isolating each key accessory (necklace, hair scrunchie, eyeglasses, shoulder bag 1, shoulder bag 2, ballet flats); "
            "Right 32% Bottom shows a 2x5 palette of 10 rounded square color swatches matching the exact garment fabrics.\n"
            "Shot on Sony A7R V 50mm f/1.4 GM, commercial lookbook studio lighting, 100% consistent facial identity and exact garment fidelity across all panels, 2K photorealistic."
        ),
        "default_vars": {
            "character_desc": "22-year-old Vietnamese female fashion lookbook model (NV5) with oval V-line face, rosy dewy glass-skin, and long wavy chestnut-brown hair",
            "looks_desc": "Look 1: yellow halter peplum top + royal blue wide-leg trousers + yellow bag; Look 2: butter-yellow tiered mini dress + white crew socks + yellow Mary Jane flats; Look 3: yellow halter top + white pleated shorts + cream chain bag; Look 4: yellow halter top + beige wide-leg trousers + pink glasses",
        },
    },
    "fashion_model_turnaround_5poses_2k": {
        "id": "fashion_model_turnaround_5poses_2k",
        "title": "Prompt #3 • Tạo Ảnh Character Sheet Người Mẫu Thời Trang 4 Góc Xoay + 5 Poses (Chuẩn Ảnh 4 - Nhân Vật 5 NV5)",
        "badge": "NV5 TURNAROUND & 5 POSES",
        "sample_image": "/api/fashion_motion/demo_asset/02_Character_Sheet_Basic_Poses_2K.png",
        "aspect_ratio": "4:5 (2048×2559 2K)",
        "guide_vn": (
            "Dùng để tạo Nhân Vật Mẫu Thời Trang Mới (như Nhân Vật 5 - NV5): Phần trên gồm 4 góc xoay (Front, 3/4, Side, Back) mặc áo thun trắng & quần short be ôm dáng + 1 ảnh Close-up cận mặt; Phần dưới gồm 5 dáng Pose mẫu chuẩn Lookbook."
        ),
        "prompt_template": (
            "Hyper-photorealistic vertical 4:5 (2048x2559 2K resolution) fashion model character turnaround & pose reference sheet on a clean warm-ivory studio background with minimalist editorial serif typography.\n"
            "- TOP SECTION titled 'CHARACTER SHEET — MODEL / CHARACTER TURNAROUND & POSES': Left 70% shows 4 full-body standing turnaround views side-by-side labeled in italic serif underneath ('Front', '3/4', 'Side', 'Back') of the exact same young East Asian/Vietnamese female fashion model ({character_desc}) wearing a form-fitting basic white crew-neck short-sleeve baby tee, high-waisted light-beige tailored shorts, and neutral nude ballet flats to clearly define her body proportions, waistline, and leg length; Right 30% shows 1 large framed 'Close-up' beauty portrait showing her exact oval V-line face, visible natural skin pores, rosy dewy Douyin glass-skin, soft coral-pink blush, expressive dark-brown almond eyes, glossy rose lips, and voluminous chestnut-brown wavy hair.\n"
            "- BOTTOM SECTION titled 'POSE REFERENCES' (below a thin horizontal divider line): 5 full-body fashion lookbook poses side-by-side labeled underneath ('Pose 1': relaxed standing front pose, 'Pose 2': one hand on hip with legs crossed at ankle, 'Pose 3': natural mid-stride runway walk, 'Pose 4': seated gracefully on a white studio cube with legs crossed, 'Pose 5': standing with both hands raised touching hair).\n"
            "Shot on Sony A7R V 85mm f/1.4 GM lens, soft diffused studio lighting, 100% identical facial identity, hairstyle, and body proportions across all 10 figures, 2K photorealistic quality, zero AI plastic look."
        ),
        "default_vars": {
            "character_desc": "ultra-photorealistic 22-year-old Vietnamese/East Asian female fashion lookbook model (NV5), oval V-line face, porcelain-fair rosy dewy Douyin glass-skin, long voluminous chestnut-brown wavy hair parted on the side, slender hourglass fashion model physique (168cm tall, long toned legs, slender waist)",
        },
    },
    "base_char_bedroom_2k": {
        "id": "base_char_bedroom_2k",
        "title": "Prompt #4 • Tạo Ảnh Ref Nhân Vật 2K Đứng Trong Phòng Ngủ / Studio Mở Đầu Video (Chuẩn Ảnh 7)",
        "badge": "ẢNH MỞ ĐẦU VIDEO 2K",
        "sample_image": "/api/fashion_motion/demo_asset/07_Nhan_Vat_Basic_Phong_Ngu_2K.png",
        "aspect_ratio": "9:16 (1536×2752 2K)",
        "guide_vn": (
            "Đính kèm Ảnh Character Sheet Nhân Vật (NV5) để tạo ra Ảnh Ref Nhân Vật 2K đứng trong phòng ngủ/studio ấm cúng làm khung hình mở đầu (Giây 0:00) trước khi biến hình thay đồ theo nhạc."
        ),
        "prompt_template": (
            "Hyper-photorealistic vertical 9:16 (1536x2752 2K resolution) full-body shot of the exact same young Vietnamese female fashion model from the provided character reference sheet ({character_desc}), "
            "standing naturally in the center of a cozy modern lived-in bedroom/dressing room ({room_desc}). "
            "She wears a casual fitted basic white baby tee and light-beige shorts before changing clothes, looking directly at the camera with a bright charming smile and relaxed feminine posture. "
            "Shot on Sony A7R V 35mm f/1.8 lens, soft natural indoor lighting, detailed visible skin pores, crisp 2K photorealistic quality, zero text or watermarks."
        ),
        "default_vars": {
            "character_desc": "22-year-old Vietnamese female fashion model (NV5) with oval V-line face, rosy dewy glass-skin, and long wavy chestnut-brown hair",
            "room_desc": "warm neutral walls, dark brown pleated floor-to-ceiling curtains in the background, a cozy bed with brown duvet on the right, and a white display shelf with cute plush toys on the left",
        },
    },
}


def get_standard_fashion_prompts(custom_vars: dict = None) -> dict:
    """Trả về bộ 4 Prompt Chuẩn Thời Trang 2K đã điền sẵn biến mặc định hoặc biến tùy chỉnh."""
    out = {}
    vars_in = custom_vars or {}
    for k, item in STANDARD_FASHION_PROMPTS.items():
        merged_vars = dict(item.get("default_vars") or {})
        for vk, vv in vars_in.items():
            if vv:
                merged_vars[vk] = vv
        tmpl = item["prompt_template"]
        try:
            rendered = tmpl.format(**merged_vars)
        except Exception:
            rendered = tmpl
        out[k] = {
            **item,
            "rendered_prompt": rendered,
        }
    return out


def generate_fashion_2k_asset_on_flow(
    asset_type: str,
    prompt_str: str,
    ref_image_paths: list = None,
    output_filename: str = None,
    project_id_slug: str = "fashion_motion_demo_7anh_2k",
    profile_name: str = "",
) -> dict:
    """
    Tạo trực tiếp trên Google Flow (Nano Banana 2.1 `ogiZ0b` -> tải bản 2K `SPrCad`) 1 trong 4 loại ảnh 2K chuẩn Thời Trang:
      - `deconstructed_outfit_flatlay_2k`: Biến ảnh quần áo gốc thành ảnh Product Sheet tách riêng quần áo & phụ kiện nền trắng 2K.
      - `wardrobe_4looks_character_sheet_2k`: Tạo ảnh Character Sheet nhân vật mặc full 4 bộ đồ + phụ kiện 2K.
      - `fashion_model_turnaround_5poses_2k`: Tạo ảnh Character Sheet người mẫu thời trang 4 góc + 5 Poses 2K.
      - `base_char_bedroom_2k`: Tạo ảnh Ref nhân vật 2K đứng trong phòng ngủ/studio mở đầu video.
    """
    import grok_video_tool as gvt
    from google_flow_auth import profile_paths
    from playwright.sync_api import sync_playwright
    from run_all_7_videos_mt import (
        upload_single_product_ref_in_page,
        generate_variant_ref_image_in_page,
    )

    proj_dir = os.path.join(FASHION_STUDIO_DIR, project_id_slug or "fashion_motion_demo_7anh_2k")
    assets_dir = os.path.join(proj_dir, "assets_2k")
    os.makedirs(assets_dir, exist_ok=True)
    manifest_path = os.path.join(proj_dir, "fashion_project.json")

    valid_refs = [p for p in (ref_image_paths or []) if p and os.path.exists(p)]
    if not output_filename:
        ts_tag = int(time.time())
        output_filename = f"{asset_type}_{ts_tag}_2K.jpg"
    out_file = os.path.join(assets_dir, output_filename)

    def _update_manifest_switch_msg(msg_text: str):
        if not os.path.exists(manifest_path):
            return
        try:
            with open(manifest_path, "r", encoding="utf-8") as _mf:
                _mdata = json.load(_mf)
            _mdata["status_message"] = msg_text
            _mdata["updated_at"] = time.strftime("%H:%M:%S")
            with open(manifest_path, "w", encoding="utf-8") as _mf:
                json.dump(_mdata, _mf, ensure_ascii=False, indent=2)
        except Exception:
            pass

    candidate_profiles = _get_ordered_flow_account_candidates(profile_name)
    last_err = "Không có tài khoản Google Flow khả dụng."

    for acc_idx, prof in enumerate(candidate_profiles):
        cookie_hdr = gvt._load_flow_cookie_header(prof)
        pw_cookies = _build_playwright_cookies_from_header(cookie_hdr, prof)
        if not cookie_hdr and not pw_cookies:
            last_err = f"Tài khoản Flow '{prof}' chưa có Cookie hợp lệ."
            _mark_flow_profile_unhealthy(prof, last_err)
            if acc_idx + 1 < len(candidate_profiles):
                next_prof = candidate_profiles[acc_idx + 1]
                _update_manifest_switch_msg(f"🔄 Tài khoản '{prof}' chưa có Cookie -> Tự động đổi sang tài khoản '{next_prof}'...")
            continue

        try:
            flow_project_id = _resolve_account_flow_project_id(prof)
        except Exception as _proj_exc:
            last_err = str(_proj_exc)
            _mark_flow_profile_unhealthy(prof, last_err)
            continue

        dl_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": "https://flow.google.com/",
            "Cookie": cookie_hdr or "",
        }

        with sync_playwright() as pw:
            browser = _launch_flow_browser(pw)
            context = None
            _bypass_js = getattr(gvt, "_FLOW_HIJACK_BYPASS_JS", None) or getattr(gvt, "_RECAPTCHA_BYPASS_INIT_SCRIPT", None)

            context = browser.new_context(viewport={"width": 1280, "height": 800})
            if _bypass_js:
                context.add_init_script(_bypass_js)
            if pw_cookies:
                try:
                    context.add_cookies(pw_cookies)
                except Exception:
                    pass

            try:
                page = context.new_page()
                if _bypass_js:
                    page.add_init_script(_bypass_js)
                page.goto(f"https://flow.google.com/project/{flow_project_id}", wait_until="domcontentloaded", timeout=60000)
                if _bypass_js:
                    try:
                        page.evaluate(_bypass_js)
                    except Exception:
                        pass
                try:
                    page.wait_for_function(
                        "() => window.WIZ_global_data && window.WIZ_global_data.SNlM0e && window.grecaptcha && window.grecaptcha.enterprise",
                        timeout=35000,
                    )
                except Exception:
                    page.wait_for_timeout(4000)
                page.wait_for_timeout(1200)

                wiz = page.evaluate(
                    """() => {
                        const w = window.WIZ_global_data || {};
                        return {
                            at: w.SNlM0e || '',
                            bl: w.cfb2h || 'boq_labs-ai-sandbox-frontend_20261104.10_p0',
                            fsid: w.FdrFJe || '',
                            ua: navigator.userAgent
                        };
                    }"""
                )
                if not wiz.get("at"):
                    last_err = f"Phiên đăng nhập Google Flow của '{prof}' đã hết hạn (thiếu SNlM0e)."
                    _mark_flow_profile_unhealthy(prof, last_err)
                    if acc_idx + 1 < len(candidate_profiles):
                        next_prof = candidate_profiles[acc_idx + 1]
                        _update_manifest_switch_msg(
                            f"🔄 Tài khoản '{prof}' hết hạn phiên đăng nhập -> Tự động đổi sang tài khoản '{next_prof}' để tạo ảnh 2K..."
                        )
                    continue

                try:
                    live_c = context.cookies(["https://flow.google.com", "https://google.com", "https://accounts.google.com"])
                    c_map = {c["name"]: c["value"] for c in live_c if "GRECAPTCHA" not in c.get("name", "").upper()}
                    if c_map:
                        cookie_hdr = "; ".join(f"{k}={v}" for k, v in c_map.items())
                        dl_headers = {
                            "Cookie": cookie_hdr,
                            "Referer": "https://flow.google.com/",
                            "User-Agent": wiz["ua"],
                        }
                except Exception:
                    pass

                uploaded_uuids = []
                upload_err_detail = ""
                for rp in valid_refs[:5]:
                    ok_u, u_id, err_u = upload_single_product_ref_in_page(page, wiz, flow_project_id, rp, quality=98)
                    if ok_u and u_id:
                        uploaded_uuids.append(u_id)
                    else:
                        upload_err_detail = str(err_u or "upload_failed")

                if valid_refs and len(uploaded_uuids) < len(valid_refs[:5]):
                    last_err = f"Upload ảnh tham chiếu lên Google Flow ({prof}) thất bại: {upload_err_detail}"
                    _mark_flow_profile_unhealthy(prof, last_err)
                    if acc_idx + 1 < len(candidate_profiles):
                        next_prof = candidate_profiles[acc_idx + 1]
                        _update_manifest_switch_msg(
                            f"🔄 Tài khoản '{prof}' lỗi upload ảnh tham chiếu -> Tự động đổi sang tài khoản '{next_prof}'..."
                        )
                    continue

                ref_task = {
                    "pid": project_id_slug,
                    "v_key": asset_type,
                    "project_id": flow_project_id,
                    "char_id": "",
                    "prod_uuids": uploaded_uuids,
                    "allow_multi_refs": len(uploaded_uuids) > 1,
                    "prompt_str": prompt_str,
                    "out_file": out_file,
                }
                ok_gen, media_uuid_2k, err_gen = generate_variant_ref_image_in_page(
                    page, wiz, cookie_hdr, dl_headers, ref_task
                )
                if not ok_gen:
                    last_err = f"Tạo ảnh 2K trên Google Flow ({prof}) thất bại: {err_gen}"
                    _mark_flow_profile_unhealthy(prof, last_err)
                    if acc_idx + 1 < len(candidate_profiles):
                        next_prof = candidate_profiles[acc_idx + 1]
                        _update_manifest_switch_msg(
                            f"🔄 Tài khoản '{prof}' lỗi tạo ảnh 2K ({str(err_gen)[:45]}) -> Tự động đổi sang tài khoản '{next_prof}'..."
                        )
                    continue

                _mark_flow_profile_healthy(prof)
                info_2k = ensure_image_is_2k(out_file)
                return {
                    "ok": True,
                    "asset_type": asset_type,
                    "filename": os.path.basename(out_file),
                    "path": out_file,
                    "media_uuid_2k": media_uuid_2k,
                    "width": info_2k.get("width", 1536),
                    "height": info_2k.get("height", 2752),
                    "is_2k": True,
                    "profile_used": prof,
                }
            finally:
                try:
                    context.close()
                except Exception:
                    pass
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass

    return {"ok": False, "error": last_err, "tried_accounts": candidate_profiles}


# ==============================================================================
# 5. GOOGLE FLOW SCOTTY VIDEO UPLOAD & OMNI FLASH `jIps6` (`abra_edit`) RUNNER
# ==============================================================================

def upload_reference_video_in_page(page, wiz: dict, project_id: str, video_path: str) -> tuple:
    """
    Upload 1 phân cảnh Video Tham Chiếu (`ref_clip_s1.mp4`, `ref_clip_s2.mp4`) lên Google Flow
    bằng giao thức Scotty Resumable Upload (`/upload/v1/flow/upload/video/${projectId}`)
    trực tiếp bên trong phiên trình duyệt Chrome của tài khoản Flow.
    Trả về: `(ok: bool, video_media_uuid: str, meta_dict: dict, err_str: str)`
    """
    if not os.path.exists(video_path):
        return False, None, None, f"Không tìm thấy file video: {video_path}"

    raw_bytes = open(video_path, "rb").read()
    b64_video = base64.b64encode(raw_bytes).decode("ascii")
    file_name = os.path.basename(video_path)

    resp = page.evaluate(
        """async ({projectId, atToken, fileName, b64Video, byteLength}) => {
            try {
                const startUrl = `/upload/v1/flow/upload/video/${projectId}`;
                const startHeaders = {
                    'X-Goog-Upload-Protocol': 'resumable',
                    'X-Goog-Upload-Command': 'start',
                    'X-Goog-Upload-Header-Content-Length': String(byteLength),
                    'X-Goog-Upload-Header-Content-Type': 'video/mp4',
                    'Slug': encodeURIComponent(fileName)
                };
                if (atToken) {
                    startHeaders['X-Framework-Xsrf-Token'] = atToken;
                }
                const rStart = await fetch(startUrl, {
                    method: 'POST',
                    headers: startHeaders,
                    credentials: 'include',
                    body: ''
                });
                const uploadUrl = rStart.headers.get('x-goog-upload-url') || rStart.headers.get('X-Goog-Upload-URL');
                if (!uploadUrl) {
                    const errTxt = await rStart.text();
                    return {ok: false, status: rStart.status, error: `Missing X-Goog-Upload-URL (HTTP ${rStart.status}): ${errTxt.slice(0, 240)}`};
                }
                const binStr = atob(b64Video);
                const bytes = new Uint8Array(binStr.length);
                for (let i = 0; i < binStr.length; i++) {
                    bytes[i] = binStr.charCodeAt(i);
                }
                const blob = new Blob([bytes], {type: 'video/mp4'});
                const rUp = await fetch(uploadUrl, {
                    method: 'POST',
                    headers: {
                        'X-Goog-Upload-Command': 'upload, finalize',
                        'X-Goog-Upload-Offset': '0',
                        'Content-Type': 'video/mp4'
                    },
                    credentials: 'include',
                    body: blob
                });
                const bodyText = await rUp.text();
                return {ok: rUp.status >= 200 && rUp.status < 300, status: rUp.status, text: bodyText};
            } catch (err) {
                return {ok: false, status: 0, error: String(err)};
            }
        }""",
        {
            "projectId": project_id,
            "atToken": wiz.get("at") or "",
            "fileName": file_name,
            "b64Video": b64_video,
            "byteLength": len(raw_bytes),
        },
    )

    if not resp or not resp.get("ok"):
        return False, None, None, (resp or {}).get("error") or f"HTTP {(resp or {}).get('status')}: {(resp or {}).get('text', '')[:200]}"

    try:
        data = json.loads(resp.get("text") or "{}")
    except Exception as e:
        return False, None, None, f"Invalid JSON from Scotty video upload: {e}"

    media_obj = data.get("media") if isinstance(data.get("media"), dict) else {}
    wf_obj = data.get("workflow") if isinstance(data.get("workflow"), dict) else {}
    raw_id = data.get("mediaId") or data.get("media_id") or media_obj.get("name") or ""
    media_uuid = str(raw_id).split("/")[-1].strip()
    if not media_uuid:
        return False, None, None, f"Không tìm thấy mediaId trong phản hồi upload video: {str(data)[:240]}"

    wf_id = str(wf_obj.get("name") or media_obj.get("workflowId") or media_obj.get("workflow_id") or media_uuid).split("/")[-1].strip()
    return True, media_uuid, {"media_uuid": media_uuid, "workflow_id": wf_id, "file_name": file_name}, None


def upload_multiple_reference_videos_parallel_in_page(page, wiz: dict, project_id: str, video_items: list) -> dict:
    """
    Upload ĐA LUỒNG SONG SONG (`Promise.all`) toàn bộ các clip Video Tham Chiếu (`ref_clip_s1_8s.mp4`, `ref_clip_s2_8s.mp4`, ...)
    cùng lúc bên trong phiên trình duyệt Chrome, rút ngắn thời gian upload tất cả clip xuống chỉ ~2.5–3.5 giây!
    `video_items`: `[{"key": "ref_video_s1", "path": "..."}, ...]`
    Trả về: `{"ref_video_s1": {"ok": True, "uuid": "...", "error": None}, ...}`
    """
    payload_items = []
    results = {}
    for it in video_items or []:
        k = it["key"]
        vp = it.get("path") or ""
        if not vp or not os.path.exists(vp):
            results[k] = {"ok": False, "uuid": None, "error": f"Không tìm thấy file video: {vp}"}
            continue
        raw_b = open(vp, "rb").read()
        payload_items.append({
            "key": k,
            "fileName": os.path.basename(vp),
            "b64Video": base64.b64encode(raw_b).decode("ascii"),
            "byteLength": len(raw_b),
        })

    if not payload_items:
        return results

    resp_list = page.evaluate(
        """async ({projectId, atToken, items}) => {
            const uploadOne = async (item) => {
                try {
                    const startUrl = `/upload/v1/flow/upload/video/${projectId}`;
                    const startHeaders = {
                        'X-Goog-Upload-Protocol': 'resumable',
                        'X-Goog-Upload-Command': 'start',
                        'X-Goog-Upload-Header-Content-Length': String(item.byteLength),
                        'X-Goog-Upload-Header-Content-Type': 'video/mp4',
                        'Slug': encodeURIComponent(item.fileName)
                    };
                    if (atToken) {
                        startHeaders['X-Framework-Xsrf-Token'] = atToken;
                    }
                    const rStart = await fetch(startUrl, {
                        method: 'POST',
                        headers: startHeaders,
                        credentials: 'include',
                        body: ''
                    });
                    const uploadUrl = rStart.headers.get('x-goog-upload-url') || rStart.headers.get('X-Goog-Upload-URL');
                    if (!uploadUrl) {
                        const errTxt = await rStart.text();
                        return {key: item.key, ok: false, status: rStart.status, error: `Missing X-Goog-Upload-URL (HTTP ${rStart.status}): ${errTxt.slice(0, 200)}`};
                    }
                    const binStr = atob(item.b64Video);
                    const bytes = new Uint8Array(binStr.length);
                    for (let i = 0; i < binStr.length; i++) {
                        bytes[i] = binStr.charCodeAt(i);
                    }
                    const blob = new Blob([bytes], {type: 'video/mp4'});
                    const rUp = await fetch(uploadUrl, {
                        method: 'POST',
                        headers: {
                            'X-Goog-Upload-Command': 'upload, finalize',
                            'X-Goog-Upload-Offset': '0',
                            'Content-Type': 'video/mp4'
                        },
                        credentials: 'include',
                        body: blob
                    });
                    const bodyText = await rUp.text();
                    return {key: item.key, ok: rUp.status >= 200 && rUp.status < 300, status: rUp.status, text: bodyText};
                } catch (err) {
                    return {key: item.key, ok: false, status: 0, error: String(err)};
                }
            };
            return await Promise.all(items.map(uploadOne));
        }""",
        {
            "projectId": project_id,
            "atToken": wiz.get("at") or "",
            "items": payload_items,
        },
    )

    for r_item in resp_list or []:
        k = r_item.get("key")
        if not r_item.get("ok"):
            results[k] = {
                "ok": False,
                "uuid": None,
                "error": r_item.get("error") or f"HTTP {r_item.get('status')}: {(r_item.get('text') or '')[:180]}",
            }
            continue
        try:
            data = json.loads(r_item.get("text") or "{}")
            media_obj = data.get("media") if isinstance(data.get("media"), dict) else {}
            raw_id = data.get("mediaId") or data.get("media_id") or media_obj.get("name") or ""
            m_uuid = str(raw_id).split("/")[-1].strip()
            if m_uuid:
                results[k] = {"ok": True, "uuid": m_uuid, "error": None}
            else:
                results[k] = {"ok": False, "uuid": None, "error": f"Missing mediaId: {str(data)[:180]}"}
        except Exception as e:
            results[k] = {"ok": False, "uuid": None, "error": str(e)}
    return results



def submit_fashion_motion_scene_in_page(page, wiz: dict, task: dict) -> tuple:
    """
    Gửi lệnh tạo Video Thời Trang Có Video Tham Chiếu (`EDIT_VIDEO` / `jIps6` / model `macaron_cookie_edit`)
    với đầy đủ:
      - `F4a(c.hL)`: `[None, ref_video_uuid, start_frame, end_frame]` (Video tham chiếu chuyển động)
      - `h_prompt`: Cấu trúc Prompt INTERLEAVED text+image `[[text],[null,[[uuid,fn]]],[text],...]`
      - `VQ(c.mw)`: Danh sách ảnh 2K tham chiếu `[[None,uuid1],[None,uuid2],...]`
      - `x_batch`: `[batch_uuid, 2]` (count=2 theo request thực)
      - Model key xác nhận từ browser DevTools: `macaron_cookie_edit`
    """
    import grok_video_tool as gvt

    project_id = task["project_id"]
    ref_video_uuid = task["ref_video_uuid"]
    duration_sec = int(task.get("duration") or 8)
    # Google Flow frontend (_.KQ in flow_rpc_module.js) luôn tính dg/Gg của video upload (source === _.Zx) theo chuẩn 30 FPS:
    # start_frame = 1, end_frame = 241 -> (241 - 1) = 240 frames @ 30fps = trọn vẹn đủ 8.00 giây (không bị hụt 2s cuối!)
    f4a_fps = 30
    target_end_frame = max(31, round(duration_sec * f4a_fps) + 1)
    start_frame = 1
    end_frame = target_end_frame

    # Danh sách UUID ảnh tham chiếu (Character 2K + Outfits 2K + Character Sheet 2K)
    image_ref_uuids = [u for u in (task.get("image_ref_uuids") or []) if u]
    asset_uuid_map = task.get("asset_uuid_map") or {}
    segments_spec = task.get("segments_spec") or []
    display_prompt = task.get("display_prompt") or ""

    # Mô phỏng tương tác chuột tự nhiên trên trang trước khi lấy reCAPTCHA Enterprise token cho VIDEO_GENERATION
    try:
        page.mouse.move(random.randint(240, 520), random.randint(260, 480), steps=6)
        page.wait_for_timeout(180)
        page.mouse.move(random.randint(540, 860), random.randint(320, 620), steps=6)
        page.wait_for_timeout(220)
    except Exception:
        pass

    rcap = page.evaluate(
        """async () => {
            const fn = window.__realGrecaptchaExecute || window.grecaptcha.enterprise.execute.bind(window.grecaptcha.enterprise);
            try { await fn('6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV', {action: 'PAGE_VIEW'}); } catch (e) {}
            await new Promise(r => setTimeout(r, 250));
            return await fn('6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV', {action: 'VIDEO_GENERATION'});
        }"""
    )

    wf_uuid = str(uuid.uuid4()).upper()
    m_uuid = str(uuid.uuid4()).upper()
    b_uuid = str(uuid.uuid4()).upper()

    # 1. F4a(c.hL): [None, video_media_id, dg(start_frame), Gg(end_frame)]
    f4a_video_ref = [None, ref_video_uuid, start_frame, end_frame]

    # 2. Y9a(new Z9a, c.Nj): [None, None, [encoded_segments]]
    h_prompt = encode_flow_structured_prompt_Nj(segments_spec, asset_uuid_map, fallback_text=display_prompt, allowed_image_uuids=image_ref_uuids)

    # 3. Model key cho VIDEO_REFERENCES có đính kèm video:
    #    - Omni 1.1 Flash: "abra_edit" (mặc định theo yêu cầu)
    #    - Omni 1.2 Flash: "macaron_cookie_edit"
    model_key = task.get("model_key") or "abra_edit"
    aspect_int = 1  # 9:16 dọc

    # 4. dS metadata (field 5): [None, None, None, None, m_uuid, wf_uuid]
    d_meta = [None, None, None, None, m_uuid, wf_uuid]

    # 5. VQ(c.mw) (field 9): [[None, img_uuid_1], [None, img_uuid_2], ...]
    vq_images = [[None, u] for u in image_ref_uuids]

    # 6. $9a message (9 fields chuẩn Protobuf-JS của jIps6):
    #    field 1 (idx 0): F4a(c.hL)
    #    field 2 (idx 1): h_prompt
    #    field 3 (idx 2): model_key ("abra_edit" hoặc "macaron_cookie_edit")
    #    field 4 (idx 3): aspectRatio (1 = 9:16)
    #    field 5 (idx 4): d_meta
    #    field 6 (idx 5): c.fi (None)
    #    field 7 (idx 6): None
    #    field 8 (idx 7): None
    #    field 9 (idx 8): VQ(c.mw)
    item_edit = [
        f4a_video_ref,
        h_prompt,
        model_key,
        aspect_int,
        d_meta,
        None,
        None,
        None,
        vq_images,
    ]

    k_ctx = [None, 22, None, None, None, project_id, None, None, None, None, [rcap, 1]]
    x_batch = [b_uuid, 1]
    payload_jips6 = [[item_edit], k_ctx, x_batch]

    f_req_str = json.dumps(
        [[["jIps6", json.dumps(payload_jips6, separators=(",", ":")), None, "generic"]]],
        separators=(",", ":"),
    )
    reqid = random.randint(100000, 999999)
    resp_obj = page.evaluate(
        """async ({projectId, bl, fsid, reqid, fReq, at}) => {
            const sp = `/project/${projectId}`;
            const url = `/_/AiSandboxAngularFrontend/data/batchexecute?rpcids=jIps6&source-path=${encodeURIComponent(sp)}&bl=${encodeURIComponent(bl)}&f.sid=${encodeURIComponent(fsid)}&hl=vi&_reqid=${reqid}&rt=c`;
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
            "projectId": project_id,
            "bl": wiz["bl"],
            "fsid": str(wiz["fsid"]),
            "reqid": reqid,
            "fReq": f_req_str,
            "at": wiz["at"],
        },
    )
    if not resp_obj or resp_obj.get("status") != 200:
        return False, None, f"jIps6 HTTP {(resp_obj or {}).get('status')}: {(resp_obj or {}).get('text', '')[:220]}"

    ok_sub, inner_sub, err_sub = gvt._parse_batchexecute_wrb(resp_obj.get("text", ""), "jIps6")
    if not ok_sub or not isinstance(inner_sub, list):
        return False, None, f"jIps6 error: {err_sub}"

    try:
        job_uuid = inner_sub[3][0][0]
    except Exception:
        job_uuid = m_uuid
    return True, job_uuid, None


def submit_fashion_chained_i2v_scene_in_page(page, wiz: dict, task: dict) -> tuple:
    """
    Gửi lệnh tạo Video Thời Trang Chained Image-to-Video + Timeline 0.1s Chuẩn Nhạc (`MZZa6b` / `macaron_cookie_r2v_8s` hoặc `abra_r2v_8s`)
    hoàn toàn từ Ảnh 2K (KHÔNG dùng video làm ref):
      - Phân cảnh 1: `[07_Nhan_Vat_Basic_Phong_Ngu_2K.png, 01_Character_Sheet_4_Outfits_2K.png]`
      - Phân cảnh 2+: `[scene_s1_last_frame_2k.png, 01_Character_Sheet_4_Outfits_2K.png]` (bắt đầu từ đúng Frame cuối của Phân cảnh 1!)
    """
    import grok_video_tool as gvt

    project_id = task["project_id"]
    image_ref_uuids = [u for u in (task.get("image_ref_uuids") or []) if u]
    asset_uuid_map = task.get("asset_uuid_map") or {}
    segments_spec = task.get("segments_spec") or []
    display_prompt = task.get("display_prompt") or ""
    dur = int(task.get("duration") or 8)
    raw_mk = str(task.get("model_key") or "macaron_cookie_r2v_8s")
    if "edit" in raw_mk:
        model_key = f"macaron_cookie_r2v_{dur}s" if "macaron" in raw_mk else f"abra_r2v_{dur}s"
    elif "_r2v_" in raw_mk or "_i2v_" in raw_mk:
        model_key = raw_mk
    else:
        model_key = f"macaron_cookie_r2v_{dur}s"

    try:
        page.mouse.move(random.randint(240, 520), random.randint(260, 480), steps=5)
        page.wait_for_timeout(150)
    except Exception:
        pass

    rcap = page.evaluate(
        """async () => {
            const fn = window.__realGrecaptchaExecute || window.grecaptcha.enterprise.execute.bind(window.grecaptcha.enterprise);
            try { await fn('6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV', {action: 'PAGE_VIEW'}); } catch (e) {}
            await new Promise(r => setTimeout(r, 200));
            return await fn('6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV', {action: 'VIDEO_GENERATION'});
        }"""
    )
    wf_uuid = str(uuid.uuid4()).upper()
    m_uuid = str(uuid.uuid4()).upper()
    b_uuid = str(uuid.uuid4()).upper()

    h_prompt = encode_flow_structured_prompt_Nj(
        segments_spec,
        asset_uuid_map,
        fallback_text=display_prompt,
        allowed_image_uuids=image_ref_uuids,
    )
    l_item = [None, None, None, None, m_uuid, wf_uuid]
    x_batch = [b_uuid, 1]
    aspect_int = 1  # 9:16 dọc
    ref_list = [[None, u] for u in image_ref_uuids]

    item_g = [
        h_prompt,
        ref_list,
        model_key,
        aspect_int,
        None,
        l_item,
        None,
        [],
        None,
        [],
        [],
    ]
    k_ctx = [None, 22, None, None, None, project_id, None, None, None, None, [rcap, 1]]
    payload_v = [[item_g], k_ctx, x_batch]
    f_req_str = json.dumps(
        [[["MZZa6b", json.dumps(payload_v, separators=(",", ":")), None, "generic"]]],
        separators=(",", ":"),
    )
    reqid = random.randint(100000, 999999)
    resp_obj = page.evaluate(
        """async ({projectId, bl, fsid, reqid, fReq, at}) => {
            const sp = `/project/${projectId}`;
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
            "projectId": project_id,
            "bl": wiz["bl"],
            "fsid": str(wiz["fsid"]),
            "reqid": reqid,
            "fReq": f_req_str,
            "at": wiz["at"],
        },
    )
    if not resp_obj or resp_obj.get("status") != 200:
        return False, None, f"MZZa6b HTTP {(resp_obj or {}).get('status')}: {(resp_obj or {}).get('text', '')[:200]}"
    ok_v, inner_v, err_v = gvt._parse_batchexecute_wrb(resp_obj.get("text", ""), "MZZa6b")
    if not ok_v or not isinstance(inner_v, list):
        return False, None, f"MZZa6b error: {err_v}"
    ret_uuid = m_uuid
    try:
        if len(inner_v) > 3 and isinstance(inner_v[3], list) and inner_v[3]:
            cand_u = inner_v[3][0][0]
            if isinstance(cand_u, str) and len(cand_u) >= 32:
                ret_uuid = cand_u
    except Exception:
        pass
    return True, ret_uuid, None


# ==============================================================================
# 6. KHỞI TẠO PROJECT MẪU TỪ BỘ 7 ẢNH 2K + VIDEO THAM CHIẾU 16S CỦA NGƯỜNG DÙNG
# ==============================================================================

def create_or_update_fashion_motion_project(
    project_id_slug: str = "fashion_motion_demo_7anh_2k",
    title: str = "Lookbook Thời Trang Thay Đồ Theo Nhạc (Trọn Bộ 7 Ảnh 2K)",
    base_char_path: str = None,
    char_sheet_path: str = None,
    ref_video_path: str = None,
    outfit_items: list = None,
    preferred_chunk_sec: str = "auto",
    prompt_style: str = "chained_i2v",
    generation_mode: str = "chained_i2v",
    custom_scene_cuts: dict = None,
    ai_provider: str = "auto",
    ai_model: str = "gemini-2.5-flash",
    auto_render_preview_final: bool = True,
) -> dict:
    """
    Tạo hoặc cập nhật 1 dự án Video Thời Trang AI hoàn chỉnh (Hỗ trợ cả 2 chế độ `chained_i2v` và `video_ref`):
      - `generation_mode == "chained_i2v"`: Hoàn toàn từ Image-to-Video + Timeline 0.1s Chuẩn Nhạc (cắt frame cuối Cảnh 1 nối tiếp Cảnh 2).
      - `generation_mode == "video_ref"`: Motion Control dùng Video Tham Chiếu + Nối tiếp Frame cuối Cảnh 1 cho Cảnh 2.
    """
    import fashion_ai_video_analyzer as fava

    gen_mode = normalize_fashion_generation_mode(generation_mode or prompt_style or "chained_i2v")
    if gen_mode == "google_vids":
        prompt_style = "google_vids"
    elif gen_mode == "chained_i2v" and prompt_style not in ("chained_i2v", "timeline_pro", "concise_flow"):
        prompt_style = "chained_i2v"

    proj_dir = os.path.join(FASHION_STUDIO_DIR, project_id_slug)
    assets_dir = os.path.join(proj_dir, "assets_2k")
    os.makedirs(assets_dir, exist_ok=True)

    def _resolve_fashion_input_path(raw_p: str) -> str:
        p = str(raw_p or "").strip().strip('"').strip("'")
        if not p:
            return ""
        if os.path.exists(p):
            return os.path.abspath(p)
        for base_d in (WS_DIR, PIPELINE_DIR, DEMO_ASSETS_DIR, assets_dir):
            cand = os.path.join(base_d, p.lstrip("/\\"))
            if os.path.exists(cand):
                return os.path.abspath(cand)
            cand_bn = os.path.join(base_d, os.path.basename(p))
            if os.path.exists(cand_bn):
                return os.path.abspath(cand_bn)
        return ""

    base_char_path = _resolve_fashion_input_path(base_char_path)
    char_sheet_path = _resolve_fashion_input_path(char_sheet_path)
    ref_video_path = _resolve_fashion_input_path(ref_video_path) or ref_video_path

    # Mặc định lấy từ folder `ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K`:
    # - Ảnh Ref Nhân Vật Thời Trang gốc: `02_Character_Sheet_Basic_Poses_2K.png`
    # - Ảnh Bối Cảnh Phòng Tham Chiếu: `07_Nhan_Vat_Basic_Phong_Ngu_2K.png`
    if not base_char_path or not os.path.exists(base_char_path):
        base_char_path = os.path.join(DEMO_ASSETS_DIR, "02_Character_Sheet_Basic_Poses_2K.png")

    _default_nv5_filenames = {
        "02_Character_Sheet_Basic_Poses_2K.png",
        "07_Nhan_Vat_Basic_Phong_Ngu_2K.png",
        "09_NV5_Phong_Tu_Go_Mo_Dau_2K.png",
        "01_Character_Sheet_4_Outfits_2K.png",
    }
    is_custom_base_char = os.path.basename(base_char_path) not in _default_nv5_filenames

    if is_custom_base_char:
        # Nếu người dùng đã đổi sang Nhân Vật của họ mà ô Bối Cảnh Mở Đầu vẫn để trống hoặc còn dính ảnh mẫu NV5,
        # tự động dùng chính ảnh Nhân Vật của người dùng làm ảnh mở đầu!
        if not char_sheet_path or not os.path.exists(char_sheet_path) or os.path.basename(char_sheet_path) in _default_nv5_filenames:
            char_sheet_path = base_char_path
    else:
        if not char_sheet_path or not os.path.exists(char_sheet_path):
            cand_cs = os.path.join(DEMO_ASSETS_DIR, "07_Nhan_Vat_Basic_Phong_Ngu_2K.png")
            if os.path.exists(cand_cs):
                char_sheet_path = cand_cs

    # Copy & đảm bảo chuẩn 2K cho ảnh nhân vật gốc
    char_filename = os.path.basename(base_char_path)
    local_char_2k = os.path.join(assets_dir, char_filename)
    if os.path.abspath(base_char_path) != os.path.abspath(local_char_2k):
        shutil.copy2(base_char_path, local_char_2k)
    char_2k_info = ensure_image_is_2k(local_char_2k)

    local_cs_2k = ""
    cs_filename = ""
    if char_sheet_path and os.path.exists(char_sheet_path):
        cs_filename = os.path.basename(char_sheet_path)
        local_cs_2k = os.path.join(assets_dir, cs_filename)
        if os.path.abspath(char_sheet_path) != os.path.abspath(local_cs_2k):
            shutil.copy2(char_sheet_path, local_cs_2k)
        ensure_image_is_2k(local_cs_2k)

    # Luôn chuẩn bị Bảng Tham Chiếu Tổng Thể Các Bộ Đồ (`01_Character_Sheet_4_Outfits_2K.png`) trong assets_2k
    overall_sheet_src = os.path.join(DEMO_ASSETS_DIR, "01_Character_Sheet_4_Outfits_2K.png")
    local_overall_2k = os.path.join(assets_dir, "01_Character_Sheet_4_Outfits_2K.png")
    if os.path.exists(overall_sheet_src) and not os.path.exists(local_overall_2k):
        shutil.copy2(overall_sheet_src, local_overall_2k)
        ensure_image_is_2k(local_overall_2k)

    # Chuẩn bị danh sách Outfit 2K (Tôn trọng 1..N bộ đồ của người dùng; chỉ fallback sang 5 bộ mẫu nếu rỗng hoàn toàn)
    if not outfit_items:
        outfit_items = []
        for d_out in DEFAULT_FASHION_DEMO_OUTFITS[:5]:
            src_p = os.path.join(DEMO_ASSETS_DIR, d_out["filename"])
            if os.path.exists(src_p):
                item_copy = dict(d_out)
                item_copy["path"] = src_p
                outfit_items.append(item_copy)

    default_outfit_filenames = {d["filename"] for d in DEFAULT_FASHION_DEMO_OUTFITS}
    normalized_outfits = []
    seen_outfit_fns = set()
    _generic_store_fns = {"prod_1.jpg", "prod_2.jpg", "prod_3.jpg", "prod_1.png", "prod_2.png", "image.png", "image.jpg", "media.png", "media.jpg", "clipboard.png"}
    for idx_o, item in enumerate(outfit_items):
        src_p = _resolve_fashion_input_path(item.get("path") or item.get("filename") or "")
        if not src_p or not os.path.exists(src_p):
            continue
        fn = os.path.basename(src_p)
        if fn in seen_outfit_fns or fn.lower() in _generic_store_fns:
            import hashlib as _hl
            try:
                with open(src_p, "rb") as _sf:
                    _h6 = _hl.sha1(_sf.read()).hexdigest()[:6]
            except Exception:
                _h6 = f"s{idx_o+1}"
            _st, _ex = os.path.splitext(fn)
            fn = f"{_st}_{_h6}{_ex}"
        seen_outfit_fns.add(fn)
        dst_p = os.path.join(assets_dir, fn)
        if os.path.abspath(src_p) != os.path.abspath(dst_p):
            shutil.copy2(src_p, dst_p)
        info_2k = ensure_image_is_2k(dst_p)
        out_entry = {
            "id": item.get("id") or f"outfit_{idx_o+1}",
            "filename": fn,
            "path": dst_p,
            "name": item.get("name") or f"Bộ Đồ #{idx_o+1} ({fn})",
            "short_desc": item.get("short_desc") or f"trang phục thời trang theo đúng ảnh tham chiếu {fn}",
            "en_desc": item.get("en_desc") or f"exact fashion outfit matching reference image {fn}",
            "width": info_2k.get("width", 1536),
            "height": info_2k.get("height", 2752),
            "is_2k": True,
        }
        if item.get("raw_product_path") and os.path.exists(item["raw_product_path"]):
            out_entry["raw_product_path"] = item["raw_product_path"]
        if item.get("needs_deconstruct_sheet"):
            out_entry["needs_deconstruct_sheet"] = True
        lb_path = item.get("lookbook_model_path") or ""
        if not lb_path or not os.path.exists(lb_path):
            lb_fn = item.get("lookbook_model_filename") or ""
            if not lb_fn:
                for d_o in DEFAULT_FASHION_DEMO_OUTFITS:
                    if d_o["filename"] == fn or d_o["id"] == out_entry["id"]:
                        lb_fn = d_o.get("lookbook_model_filename") or ""
                        break
            if lb_fn:
                cand_lb = os.path.join(DEMO_ASSETS_DIR, lb_fn)
                if os.path.exists(cand_lb):
                    lb_path = cand_lb
        if lb_path and os.path.exists(lb_path):
            out_entry["lookbook_model_path"] = lb_path
        normalized_outfits.append(out_entry)

    has_custom_outfits = any(o.get("filename") not in default_outfit_filenames for o in normalized_outfits)
    disable_overall_sheet = bool(is_custom_base_char or has_custom_outfits)

    # Copy video tham chiếu vào project
    local_ref_video = os.path.join(proj_dir, "reference_motion_source.mp4")
    if (not ref_video_path or not os.path.exists(ref_video_path)) and not os.path.exists(local_ref_video):
        # Fallback về video tham chiếu mặc định hoặc FVT_001 để khi người dùng chỉ đổi Nhân vật / Sản phẩm trên dự án mới vẫn chạy ngay
        for _cand_v in (
            os.path.join(FASHION_STUDIO_DIR, "fashion_tpl_fvt_001", "reference_motion_source.mp4"),
            os.path.join(FASHION_STUDIO_DIR, "fashion_lookbook_chan_vay_6e19", "reference_motion_source.mp4"),
        ):
            if _cand_v and os.path.exists(_cand_v):
                ref_video_path = _cand_v
                break

    orig_ref_filename = os.path.basename(ref_video_path) if (ref_video_path and os.path.exists(ref_video_path)) else "reference_motion_source.mp4"
    if ref_video_path and os.path.exists(ref_video_path):
        if os.path.abspath(ref_video_path) != os.path.abspath(local_ref_video):
            shutil.copy2(ref_video_path, local_ref_video)

    if not os.path.exists(local_ref_video):
        return {"ok": False, "error": "Chưa có file Video Tham Chiếu (reference_motion_source.mp4)"}

    # Phân tích & cắt Video Tham Chiếu thành từng phân cảnh 8s hoặc 10s (kèm quét nhịp 0.01s/0.1s)
    split_res = analyze_and_split_reference_video(
        ref_video_path=local_ref_video,
        work_dir=proj_dir,
        outfits=normalized_outfits,
        preferred_chunk_sec=preferred_chunk_sec,
        custom_scene_cuts=custom_scene_cuts,
        generation_mode="chained_i2v" if gen_mode in ("chained_i2v", "google_vids") else "video_ref",
    )
    if not split_res.get("ok"):
        return split_res

    char_sheet_ref_obj = (
        {"asset_key": "char_sheet_2k", "filename": cs_filename, "path": local_cs_2k}
        if local_cs_2k and os.path.exists(local_cs_2k)
        else None
    )

    # Xây dựng kịch bản từng phân cảnh kèm AI Phân Tích Chuyển Động + Ảnh Ref Mở Đầu 2K + Prompt Timeline
    scenes = split_res["scenes"]
    total_dur_probe = split_res["video_probe"]["duration"]
    bpm_info_obj = split_res.get("global_cuts_info") or {}
    last_outfit_of_prev_scene = None

    for sc in scenes:
        sc_idx = sc["scene_index"]
        sc["output_video_file"] = f"fashion_scene_{sc['id']}_1080p.mp4"
        sc_out_mp4 = os.path.join(proj_dir, sc["output_video_file"])

        prev_lf_ref = None
        if sc_idx >= 2:
            prev_sc_mp4 = os.path.join(proj_dir, f"fashion_scene_s{sc_idx-1}_1080p.mp4")
            lf_fn = f"scene_s{sc_idx-1}_last_frame_2k.png"
            lf_key = f"scene_s{sc_idx-1}_last_frame_2k"
            lf_path = os.path.join(assets_dir, lf_fn)
            if os.path.exists(prev_sc_mp4) and os.path.getsize(prev_sc_mp4) > 50000:
                extract_scene_last_frame_2k(prev_sc_mp4, lf_path)
            elif not os.path.exists(lf_path) and local_cs_2k and os.path.exists(local_cs_2k):
                shutil.copy2(local_cs_2k, lf_path)
            prev_lf_ref = {
                "asset_key": lf_key,
                "filename": lf_fn,
                "path": lf_path,
                "is_chained_last_frame": True,
                "description": f"Frame cuối cắt từ Phân cảnh {sc_idx-1} ({lf_fn}) để nối tiếp hành động & trang phục sang Phân cảnh {sc_idx}",
            }
            sc["prev_scene_last_frame_ref"] = prev_lf_ref
            sc["prev_scene_last_outfit"] = last_outfit_of_prev_scene

        start_char_ref = {
            "asset_key": "base_char_2k",
            "filename": char_filename,
            "path": local_char_2k,
            "is_continuity_generated": False,
            "description": (
                "Ảnh Ref Nhân Vật Thời Trang 2K (02_Character_Sheet_Basic_Poses_2K.png)"
                if sc_idx == 1
                else f"Nối tiếp từ Frame cuối Cảnh {sc_idx-1} (scene_s{sc_idx-1}_last_frame_2k.png) + Character Sheet ({char_filename})"
            ),
        }

        # Phân tích chuyển động phân cảnh qua CLIProxy Vision AI hoặc AI Agent Deep Vision
        ai_res = None
        if ai_provider in ("cliproxy", "auto"):
            ai_res = fava.call_cliproxy_vision_for_scene_analysis(
                keyframe_sheet_path=sc.get("keyframe_sheet_path") or "",
                scene_index=sc_idx,
                duration=sc["duration"],
                transitions=sc.get("transitions") or [],
                ai_model=ai_model or "gemini-2.5-flash",
            )
        if not ai_res or not ai_res.get("ok"):
            ai_res = fava.build_builtin_deep_scene_analysis(
                ref_video_path=ref_video_path or local_ref_video,
                scene_info=sc,
                total_duration=total_dur_probe,
            )

        sc["ai_motion_summary_vn"] = ai_res.get("motion_summary_vn") or ""
        sc["ai_model_used"] = ai_res.get("ai_model_used") or "AI Agent Vision + FFmpeg 0.1s Beat Scanner"
        sc["opening_action_vn"] = ai_res.get("opening_action_vn") or ""
        sc["transition_actions_vn"] = ai_res.get("transition_actions_vn") or []
        sc["ref_video_path"] = orig_ref_filename or local_ref_video
        sc["template_meta"] = {"code": project_id_slug, "slug": orig_ref_filename}
        sc["disable_overall_sheet"] = disable_overall_sheet

        sc["start_char_ref"] = start_char_ref
        p_vids = build_scene_timeline_prompt(
            sc, start_char_ref, char_sheet_ref_obj,
            prompt_style="google_vids",
            prev_scene_last_outfit=last_outfit_of_prev_scene,
            prev_scene_last_frame_ref=prev_lf_ref,
            bpm_info=bpm_info_obj,
        )
        p_i2v = build_scene_timeline_prompt(
            sc, start_char_ref, char_sheet_ref_obj,
            prompt_style="chained_i2v",
            prev_scene_last_outfit=last_outfit_of_prev_scene,
            prev_scene_last_frame_ref=prev_lf_ref,
            bpm_info=bpm_info_obj,
        )
        p_pro = build_scene_timeline_prompt(
            sc, start_char_ref, char_sheet_ref_obj,
            prompt_style="timeline_pro",
            prev_scene_last_outfit=last_outfit_of_prev_scene,
            prev_scene_last_frame_ref=prev_lf_ref,
            bpm_info=bpm_info_obj,
        )
        p_concise = build_scene_timeline_prompt(
            sc, start_char_ref, char_sheet_ref_obj,
            prompt_style="concise_flow",
            prev_scene_last_outfit=last_outfit_of_prev_scene,
            prev_scene_last_frame_ref=prev_lf_ref,
            bpm_info=bpm_info_obj,
        )

        sc["prompt_google_vids"] = p_vids["display_prompt"]
        sc["segments_google_vids"] = p_vids["segments_spec"]
        sc["prompt_chained_i2v"] = p_i2v["display_prompt"]
        sc["segments_chained_i2v"] = p_i2v["segments_spec"]
        sc["prompt_timeline_pro"] = p_pro["display_prompt"]
        sc["segments_timeline_pro"] = p_pro["segments_spec"]
        sc["prompt_concise_flow"] = p_concise["display_prompt"]
        sc["segments_concise_flow"] = p_concise["segments_spec"]

        if gen_mode == "google_vids":
            eff_style = "google_vids"
            active_p = p_vids
        elif gen_mode == "chained_i2v":
            eff_style = "chained_i2v"
            active_p = p_i2v
        else:
            eff_style = prompt_style if prompt_style in ("timeline_pro", "concise_flow") else "timeline_pro"
            active_p = p_concise if eff_style == "concise_flow" else p_pro
        sc["active_prompt_style"] = eff_style
        sc["generation_mode"] = gen_mode
        sc["prompt"] = active_p["display_prompt"]
        sc["segments_spec"] = active_p["segments_spec"]
        sc["output_video_path"] = sc_out_mp4 if os.path.exists(sc_out_mp4) else ""
        sc["status"] = "done" if os.path.exists(sc_out_mp4) else "ready"

        if sc.get("transitions"):
            last_outfit_of_prev_scene = sc["transitions"][-1]["outfit"]

    kf_list_str = ", ".join(sc.get("keyframe_sheet_path") or "" for sc in scenes if sc.get("keyframe_sheet_path"))
    ai_agent_cmd = (
        f"Phân tích video thời trang '{orig_ref_filename}' (Project: {project_id_slug}, bảng keyframe: {kf_list_str}) "
        f"và tối ưu kịch bản {len(scenes)} phân cảnh thay {len(normalized_outfits)} bộ đồ theo nhạc"
    )

    manifest_path = os.path.join(proj_dir, "fashion_project.json")
    prev_manifest = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as _pf:
                prev_manifest = json.load(_pf) or {}
        except Exception:
            prev_manifest = {}

    def _is_cacheable_img_filename(k_str: str) -> bool:
        kl = str(k_str or "").strip().lower()
        if not kl.endswith((".png", ".jpg", ".jpeg", ".webp")):
            return False
        if kl.startswith(("prepared_", "scene_s", "ref_video_", "outfit_prod_")):
            return False
        return True

    prev_img_uuids = {
        k: v for k, v in (prev_manifest.get("asset_uuid_map") or {}).items()
        if v and _is_cacheable_img_filename(k)
    }

    final_vid_path = os.path.join(FINAL_VIDEOS_DIR, f"{project_id_slug}_final.mp4")
    project_manifest = {
        "ok": True,
        "project_id": project_id_slug,
        "title": title,
        "template_code": "#004",
        "template_name": "Motion Control & Chained I2V Video Fashion (Thay Đồ Theo Nhạc 0.1s)",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "project_dir": proj_dir,
        "ai_provider": ai_provider,
        "ai_model": ai_model,
        "ai_agent_command": ai_agent_cmd,
        "generation_mode": gen_mode,
        "disable_overall_sheet": disable_overall_sheet,
        "global_cuts_info": split_res.get("global_cuts_info") or {},
        "base_char_2k": {
            "filename": char_filename,
            "path": local_char_2k,
            "width": char_2k_info.get("width", 1536),
            "height": char_2k_info.get("height", 2752),
            "is_2k": True,
        },
        "char_sheet_2k": char_sheet_ref_obj,
        "reference_video": {
            "filename": orig_ref_filename,
            "path": local_ref_video,
            "duration": split_res["video_probe"]["duration"],
            "width": split_res["video_probe"]["width"],
            "height": split_res["video_probe"]["height"],
            "fps": split_res["video_probe"]["fps"],
            "has_audio": split_res["video_probe"]["has_audio"],
        },
        "master_audio_path": split_res.get("master_audio_path") or "",
        "split_plan": split_res["split_plan"],
        "outfits": normalized_outfits,
        "prompt_style": "chained_i2v" if gen_mode == "chained_i2v" else prompt_style,
        "scenes": scenes,
        "final_video_path": final_vid_path,
        "final_video_ready": os.path.exists(final_vid_path),
    }
    if prev_manifest.get("flow_project_id"):
        project_manifest["flow_project_id"] = prev_manifest["flow_project_id"]
    if prev_manifest.get("asset_uuid_project_id"):
        project_manifest["asset_uuid_project_id"] = prev_manifest["asset_uuid_project_id"]
    if prev_img_uuids:
        project_manifest["asset_uuid_map"] = prev_img_uuids

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(project_manifest, f, ensure_ascii=False, indent=2)

    if auto_render_preview_final:
        try:
            fava.render_fashion_postprod_final_video(project_id_slug, proj_dir, project_manifest, FINAL_VIDEOS_DIR)
        except Exception:
            pass

    return project_manifest


def list_fashion_motion_projects() -> list:
    """Liệt kê tất cả các dự án Motion Control Video Fashion hiện có."""
    items = []
    if not os.path.exists(FASHION_STUDIO_DIR):
        return items
    for name in sorted(os.listdir(FASHION_STUDIO_DIR)):
        m_path = os.path.join(FASHION_STUDIO_DIR, name, "fashion_project.json")
        if os.path.exists(m_path):
            try:
                with open(m_path, "r", encoding="utf-8") as f:
                    items.append(json.load(f))
            except Exception:
                pass
    return items


# ==============================================================================
# 7. CHẠY FULL PIPELINE MOTION CONTROL VIDEO FASHION TRÊN GOOGLE FLOW (2K + OMNI FLASH)
# ==============================================================================

_UNHEALTHY_FLOW_PROFILES = {}  # {prof_lower: (timestamp, reason)}
_FLOW_ACCOUNT_RR_COUNTER = 0


def _launch_flow_browser(pw):
    """Khởi chạy trình duyệt Chrome sạch cho Google Flow (headless mặc định, trừ khi FLOW_SHOW_BROWSER=1)."""
    headless_mode = os.environ.get("FLOW_SHOW_BROWSER", "").strip() != "1"
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--window-size=1280,800",
        "--mute-audio",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    try:
        return pw.chromium.launch(channel="chrome", headless=headless_mode, args=launch_args)
    except Exception:
        return pw.chromium.launch(headless=headless_mode, args=launch_args)


def _mark_flow_profile_unhealthy(prof: str, reason: str = "") -> None:
    key = str(prof or "").strip().lower()
    if not key:
        return
    _UNHEALTHY_FLOW_PROFILES[key] = (time.time(), str(reason or "error"))
    print(
        f"⚠️ [Auto-Switch Account] Tài khoản '{prof}' báo lỗi ({str(reason)[:95]}) -> Tự động chuyển sang tài khoản khác!",
        flush=True,
    )


def _mark_flow_profile_healthy(prof: str) -> None:
    key = str(prof or "").strip().lower()
    if key:
        _UNHEALTHY_FLOW_PROFILES.pop(key, None)


def _is_flow_profile_unhealthy(prof: str, cooldown_sec: float = 300.0) -> bool:
    key = str(prof or "").strip().lower()
    if not key or key not in _UNHEALTHY_FLOW_PROFILES:
        return False
    ts, _ = _UNHEALTHY_FLOW_PROFILES[key]
    if (time.time() - ts) > cooldown_sec:
        _UNHEALTHY_FLOW_PROFILES.pop(key, None)
        return False
    return True


def _get_ordered_flow_account_candidates(preferred_profile: str = "", rotate_round_robin: bool = False) -> list:
    """
    Trả về danh sách toàn bộ tài khoản Google Flow / Vids khả dụng theo thứ tự ưu tiên:
      1. Các tài khoản khỏe mạnh (chưa bị lỗi phiên `SNlM0e` / Cookie trong 5 phút gần nhất).
      2. Nếu người dùng chọn `preferred_profile` và tài khoản đó chưa bị đánh dấu lỗi, xếp đầu tiên;
         nếu tài khoản đó lỗi, tự động xoay sang `flow_acc_2`, `leviettung04`, `capcutpro`, `Profile 13`, `Profile 15`, ...
      3. Khi `rotate_round_robin=True` (đa luồng đa tài khoản), xoay vòng giữa các tài khoản khỏe mạnh có đủ Cookie.
    """
    global _FLOW_ACCOUNT_RR_COUNTER
    pref_clean = str(preferred_profile or "").strip()
    accounts_meta = []
    seen_lower = set()

    try:
        from cooking_storyboard_engine import list_cooking_flow_accounts, load_cooking_cookies
        for acc in list_cooking_flow_accounts():
            p_name = str(acc.get("profile_name") or "").strip()
            if not p_name or p_name.lower() in seen_lower:
                continue
            if not acc.get("active", True):
                continue
            ck_list = load_cooking_cookies(p_name)
            has_ck = bool(acc.get("has_cookies") or ck_list)
            if not has_ck:
                continue
            seen_lower.add(p_name.lower())
            tag_str = str(acc.get("tag") or "").lower()
            tier_rank = 0 if ("ultra" in tag_str or "pro" in tag_str) else 1
            rich_rank = 0 if len(ck_list) >= 15 else 1
            accounts_meta.append({
                "profile_name": p_name,
                "rich_rank": rich_rank,
                "tier_rank": tier_rank,
                "cookie_count": len(ck_list),
            })
    except Exception:
        pass

    if pref_clean and pref_clean.lower() not in seen_lower:
        accounts_meta.insert(0, {
            "profile_name": pref_clean,
            "rich_rank": 0,
            "tier_rank": 0,
            "cookie_count": 50,
        })
        seen_lower.add(pref_clean.lower())

    if not accounts_meta:
        return [pref_clean] if pref_clean else []

    healthy = [m for m in accounts_meta if not _is_flow_profile_unhealthy(m["profile_name"])]
    unhealthy = [m for m in accounts_meta if _is_flow_profile_unhealthy(m["profile_name"])]

    healthy.sort(key=lambda m: (m["rich_rank"], m["tier_rank"], -m["cookie_count"]))

    if rotate_round_robin and len(healthy) > 1:
        rich_healthy = [m for m in healthy if m["rich_rank"] == 0] or healthy
        shift = _FLOW_ACCOUNT_RR_COUNTER % len(rich_healthy)
        _FLOW_ACCOUNT_RR_COUNTER += 1
        rotated_rich = rich_healthy[shift:] + rich_healthy[:shift]
        rest_healthy = [m for m in healthy if m not in rich_healthy]
        healthy = rotated_rich + rest_healthy

    if pref_clean:
        pref_match = next((m for m in healthy if m["profile_name"].lower() == pref_clean.lower()), None)
        if pref_match:
            healthy = [pref_match] + [m for m in healthy if m["profile_name"].lower() != pref_clean.lower()]

    ordered = [m["profile_name"] for m in healthy] + [m["profile_name"] for m in unhealthy]
    return ordered or ([pref_clean] if pref_clean else [])


def _resolve_account_flow_project_id(prof: str) -> str:
    """Lấy đúng Google Flow Project ID của tài khoản đang chọn từ Flow_nhieu_worker_accounts.json."""
    from cooking_storyboard_engine import list_cooking_flow_accounts, DEFAULT_FLOW_PROJECT_UUID
    for account in list_cooking_flow_accounts():
        if str(account.get("profile_name", "")).lower() == prof.lower():
            project_id = str(account.get("project_id") or "").strip()
            if project_id:
                return project_id
    acc_file = os.path.join(WS_DIR, "data", "google_flow_grok", "Flow_nhieu_worker_accounts.json")
    if os.path.exists(acc_file):
        try:
            with open(acc_file, "r", encoding="utf-8") as f:
                accs = json.load(f)
            for a in accs:
                em = str(a.get("email") or "").lower()
                if prof.lower() in em and a.get("project_id"):
                    return str(a["project_id"]).strip()
        except Exception:
            pass
    return DEFAULT_FLOW_PROJECT_UUID


def _build_playwright_cookies_from_header(cookie_hdr: str, prof: str) -> list:
    """Tạo danh sách cookie chuẩn Playwright từ file cookies JSON đầy đủ (giữ nguyên __Host-1PLSID/3PLSID/GAPS) + chuỗi Cookie header."""
    pw_cookies = []
    seen = set()
    try:
        from cooking_storyboard_engine import load_cooking_cookies
        raw_list = load_cooking_cookies(prof)
        for c in raw_list or []:
            if not isinstance(c, dict):
                continue
            name = str(c.get("name") or "").strip()
            val = c.get("value")
            if not name or val is None or "GRECAPTCHA" in name.upper():
                continue
            dom = str(c.get("domain") or ".google.com").strip()
            pw_cookies.append(c)
            seen.add((name, dom))
    except Exception:
        pass

    cookies_json = os.path.join(WS_DIR, "data", "google_flow_grok", "cookies", f"{prof}.json")
    if not pw_cookies and os.path.exists(cookies_json):
        try:
            with open(cookies_json, "r", encoding="utf-8") as f:
                cdata = json.load(f)
            for c in cdata.get("cookies") or []:
                name = str(c.get("name") or "").strip()
                val = c.get("value")
                dom = str(c.get("domain") or ".google.com").strip()
                if not name or val is None or "GRECAPTCHA" in name.upper():
                    continue
                if "google.com" in dom or "youtube.com" in dom:
                    is_sec = bool(c.get("secure", True)) or name.startswith(("__Secure-", "__Host-"))
                    pw_cookies.append(
                        {
                            "name": name,
                            "value": str(val),
                            "domain": dom,
                            "path": c.get("path") or "/",
                            "secure": is_sec,
                            "httpOnly": bool(c.get("httpOnly", False)),
                        }
                    )
                    seen.add((name, dom))
        except Exception:
            pass

    for part in (cookie_hdr or "").split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip()
        if not k or k.startswith("__Host-") or "GRECAPTCHA" in k.upper():
            continue
        dom = "flow.google.com" if k in ("OSID", "__Secure-OSID") else (".flow.google.com" if k.startswith("_ga") else ".google.com")
        if (k, dom) not in seen:
            pw_cookies.append(
                {
                    "name": k,
                    "value": v,
                    "domain": dom,
                    "path": "/",
                    "secure": k.startswith("__Secure") or k in ("SSID", "APISID", "SAPISID", "NID", "AEC", "OSID"),
                    "httpOnly": not k.startswith("_ga"),
                }
            )
            seen.add((k, dom))
    return pw_cookies


def _poll_flow_scene_video_cffi(
    http_sess,
    cookie_hdr: str,
    wiz: dict,
    dl_headers: dict,
    flow_project_id: str,
    media_uuid: str,
    out_mp4: str,
    stage: str = "base_720p",
    page=None,
) -> tuple:
    """
    Poll trạng thái render video trên Google Flow qua RPC `as29s` (ưu tiên gọi qua `page.evaluate` để không bao giờ bị HTTP 401 khi xoay cookie).
    Khi bản 720p hoàn tất: lưu ngay vào `out_mp4` (để luôn có video AI thật từ Google Flow) và trả về `"ready_for_1080p"`.
    Khi bản 1080p (`_upsampled`) hoàn tất: ghi đè bản 1080p sắc nét vào `out_mp4` và trả về `"done"`.
    """
    import grok_video_tool as gvt
    from run_all_7_videos_mt import call_flow_rpc_cffi

    ok_p, inner_p, err_p = False, None, None
    if page is not None:
        try:
            f_req_as = json.dumps(
                [[["as29s", json.dumps([media_uuid, None, [2]], separators=(",", ":")), None, "generic"]]],
                separators=(",", ":"),
            )
            reqid_as = random.randint(100000, 999999)
            resp_as = page.evaluate(
                """async ({projectId, bl, fsid, reqid, fReq, at}) => {
                    const sp = `/project/${projectId}`;
                    const url = `/_/AiSandboxAngularFrontend/data/batchexecute?rpcids=as29s&source-path=${encodeURIComponent(sp)}&bl=${encodeURIComponent(bl)}&f.sid=${encodeURIComponent(fsid)}&hl=vi&_reqid=${reqid}&rt=c`;
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
                    "reqid": reqid_as,
                    "fReq": f_req_as,
                    "at": wiz["at"],
                },
            )
            if resp_as and resp_as.get("status") == 200:
                ok_p, inner_p, err_p = gvt._parse_batchexecute_wrb(resp_as.get("text", ""), "as29s")
        except Exception as _pe:
            err_p = str(_pe)

    if not ok_p and err_p is None:
        ok_p, inner_p, err_p = call_flow_rpc_cffi(http_sess, cookie_hdr, wiz, flow_project_id, "as29s", [media_uuid, None, [2]])
    if not ok_p or not isinstance(inner_p, list):
        err_s = str(err_p or "")
        if "[5]" in err_s or "NOT_FOUND" in err_s.upper():
            return "failed:not_found_5", None
        if "[3]" in err_s or "INVALID_ARGUMENT" in err_s.upper() or "[7]" in err_s or "PERMISSION_DENIED" in err_s.upper():
            return f"failed:rpc_{err_s[:36]}", None
        return f"rpc_err:{err_s[:40]}", None

    v_urls = gvt._find_signed_flow_urls(inner_p, "https://flow-content.google/video/")
    if not v_urls:
        v_urls = gvt._find_signed_flow_urls(inner_p, "https://storage.googleapis.com/")

    if v_urls:
        v_url = v_urls[0]
        if page is not None:
            try:
                live_c = page.context.cookies(["https://flow.google.com", "https://google.com"])
                if live_c:
                    cookie_hdr = "; ".join(f"{c['name']}={c['value']}" for c in live_c if "GRECAPTCHA" not in c.get("name", "").upper())
                    dl_headers["Cookie"] = cookie_hdr
            except Exception:
                pass
        r_dl = http_sess.get(v_url, headers=dl_headers, timeout=120, allow_redirects=True)
        if r_dl.status_code != 200 or len(r_dl.content) <= 10000 or b"ftyp" not in r_dl.content[:16]:
            r_dl = http_sess.get(
                v_url,
                headers={"Referer": "https://flow.google.com/", "User-Agent": wiz["ua"], "Cookie": cookie_hdr},
                timeout=120,
                allow_redirects=True,
            )
        if r_dl.status_code == 200 and len(r_dl.content) > 10000 and b"ftyp" in r_dl.content[:16]:
            with open(out_mp4, "wb") as f:
                f.write(r_dl.content)
            if stage == "base_720p":
                return "ready_for_1080p", len(r_dl.content)
            return "done", len(r_dl.content)
        return f"dl_err:{r_dl.status_code}", None

    status_code = None
    try:
        status_code = inner_p[5][8][0]
    except Exception:
        pass
    if status_code is None:
        try:
            status_code = inner_p[0][0][5][8][0]
        except Exception:
            pass
    if status_code is None:
        try:
            status_code = inner_p[0][0][3]
        except Exception:
            pass
    if status_code is None:
        try:
            status_code = inner_p[5][7][0]
        except Exception:
            pass
    raw_s = json.dumps(inner_p, ensure_ascii=False)
    raw_upper = raw_s.upper()
    if (
        status_code in (4, 5, 6, 7, 8, "FAILED", "CANCELED", "ERROR", "REJECTED")
        or "PUBLIC_ERROR" in raw_upper
        or "GENERATION_FAILED" in raw_upper
        or "POLICY_VIOLATION" in raw_upper
        or "SAFETY_ERROR" in raw_upper
    ):
        print(f"   [POLL-ERR {media_uuid[:8]}] {raw_s[:260]}", flush=True)
        return f"failed:{status_code or 'error'}", None
    return f"rendering:{status_code}", None


def _build_fashion_local_asset_path_map(proj_dir: str, manifest: dict) -> dict:
    """Ánh xạ mọi `asset_key` và `filename` của dự án Thời Trang sang đường dẫn file ảnh 2K trên ổ đĩa."""
    assets_dir = os.path.join(proj_dir, "assets_2k")
    path_map = {}

    def _reg(key_or_fn: str, fpath: str):
        if key_or_fn and fpath and os.path.isfile(fpath):
            path_map[str(key_or_fn)] = os.path.abspath(fpath)

    base_obj = manifest.get("base_char_2k") or {}
    base_fn = base_obj.get("filename") or "02_Character_Sheet_Basic_Poses_2K.png"
    base_p = base_obj.get("path") or os.path.join(assets_dir, base_fn)
    if not os.path.isfile(base_p):
        base_p = os.path.join(DEMO_ASSETS_DIR, base_fn)
    _reg("base_char_2k", base_p)
    _reg(base_fn, base_p)

    cs_obj = manifest.get("char_sheet_2k") or {}
    cs_fn = cs_obj.get("filename") or "07_Nhan_Vat_Basic_Phong_Ngu_2K.png"
    cs_p = cs_obj.get("path") or os.path.join(assets_dir, cs_fn)
    if not os.path.isfile(cs_p):
        cs_p = os.path.join(DEMO_ASSETS_DIR, cs_fn)
    _reg("char_sheet_2k", cs_p)
    _reg(cs_fn, cs_p)

    ov_fn = "01_Character_Sheet_4_Outfits_2K.png"
    ov_p = os.path.join(assets_dir, ov_fn)
    if not os.path.isfile(ov_p):
        ov_p = os.path.join(DEMO_ASSETS_DIR, ov_fn)
    _reg("overall_sheet_2k", ov_p)
    _reg(ov_fn, ov_p)

    for outf in manifest.get("outfits") or []:
        if not isinstance(outf, dict):
            continue
        fn = outf.get("filename") or os.path.basename(outf.get("path") or "")
        op = outf.get("path") or os.path.join(assets_dir, fn)
        if not os.path.isfile(op) and fn:
            op = os.path.join(assets_dir, fn)
        if not os.path.isfile(op) and fn:
            op = os.path.join(DEMO_ASSETS_DIR, fn)
        _reg(outf.get("id") or "", op)
        _reg(fn, op)

    for sc in manifest.get("scenes") or []:
        for tr in sc.get("transitions") or []:
            outf = tr.get("outfit") or {}
            fn = outf.get("filename") or os.path.basename(outf.get("path") or "")
            op = outf.get("path") or (os.path.join(assets_dir, fn) if fn else "")
            if op and not os.path.isfile(op) and fn:
                op = os.path.join(DEMO_ASSETS_DIR, fn)
            _reg(outf.get("id") or "", op)
            _reg(fn, op)
        lf_ref = sc.get("prev_scene_last_frame_ref") or {}
        lf_fn = lf_ref.get("filename") or ""
        lf_p = lf_ref.get("path") or (os.path.join(assets_dir, lf_fn) if lf_fn else "")
        _reg(lf_ref.get("asset_key") or "", lf_p)
        _reg(lf_fn, lf_p)

    return path_map


def _run_fashion_motion_project_on_google_vids(
    project_id_slug: str,
    proj_dir: str,
    manifest: dict,
    manifest_path: str,
    profile_name: str = "",
    target_scene_id: str = "",
) -> dict:
    """
    Thực thi dự án Video Thời Trang trực tiếp qua **Google Vids Web (`docs.google.com/videos`)**:
      - 100% HTTP thuần (`GoogleVidsClient`), KHÔNG mở trình duyệt Chrome/Playwright, KHÔNG cần reCAPTCHA!
      - Tải trực tiếp tối đa 3 ảnh 2K gốc mỗi phân cảnh qua Scotty temporaryblob & gắn UUID Chip `Amv` chuẩn xác.
      - Xuất thẳng MP4 Native 1080×1920 24FPS (không cần bước chờ Upsample 720p -> 1080p).
      - Cảnh 1 xong tự động trích xuất `scene_s1_last_frame_2k.png` làm Frame đầu nối tiếp Cảnh 2, sau đó ghép nhạc gốc Final!
    """
    import fashion_ai_video_analyzer as fava
    import google_vids_client as gvc

    cfg = {}
    try:
        import engine_settings_manager as _esm
        cfg = _esm.load_engine_settings()
    except Exception:
        cfg = {}

    vids_model = str(cfg.get("google_vids_model") or "omni").strip().lower()
    multi_acc = bool(cfg.get("multi_account_enabled", True))
    candidate_profiles = _get_ordered_flow_account_candidates(
        profile_name or manifest.get("preferred_profile_name") or ""
    )
    prof = candidate_profiles[0] if candidate_profiles else (profile_name or "").strip()
    if not prof:
        return {"ok": False, "error": "Chưa có tài khoản Google Vids / Google Flow nào được đăng nhập. Vui lòng đăng nhập ở tab Tài Khoản!"}
    fallback_profs = [p for p in candidate_profiles if p != prof] if multi_acc else []

    manifest["generation_mode"] = "google_vids"
    manifest["prompt_style"] = "google_vids"
    all_scenes = sorted(manifest.get("scenes") or [], key=lambda x: int(x.get("scene_index") or 1))
    scenes_to_run = [s for s in all_scenes if not target_scene_id or s.get("id") == target_scene_id]
    if not scenes_to_run:
        return {"ok": False, "error": f"Không tìm thấy phân cảnh '{target_scene_id}' trong dự án '{project_id_slug}'."}

    _last_sync_ts = [0.0]

    def _save_live(st_code: str = None, st_msg: str = None):
        if st_code:
            manifest["status"] = st_code
        if st_msg:
            manifest["status_message"] = st_msg
        manifest["updated_at"] = time.strftime("%H:%M:%S")
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, ensure_ascii=False, indent=2)
        now_t = time.monotonic()
        if st_code in ("completed_final", "failed_scenes", "failed_auth", "failed_upload") or (now_t - _last_sync_ts[0] >= 2.5):
            _last_sync_ts[0] = now_t
            try:
                import sync_web_ui_state as _sws
                threading.Thread(target=lambda: _sws.sync_web_ui(force=True), daemon=True).start()
            except Exception:
                pass

    start_char_ref = {
        "asset_key": "base_char_2k",
        "filename": (manifest.get("base_char_2k") or {}).get("filename") or "02_Character_Sheet_Basic_Poses_2K.png",
        "path": (manifest.get("base_char_2k") or {}).get("path") or "",
        "is_continuity_generated": False,
    }
    char_sheet_ref_obj = manifest.get("char_sheet_2k")
    bpm_info = (manifest.get("split_plan") or {}).get("bpm_info") or manifest.get("global_cuts_info") or {}
    assets_dir = os.path.join(proj_dir, "assets_2k")
    os.makedirs(assets_dir, exist_ok=True)

    asset_path_map = _build_fashion_local_asset_path_map(proj_dir, manifest)
    client = gvc.get_google_vids_client()
    max_attempts = 3

    _save_live(
        "running_flow",
        f"🌐 Đang kết nối Google Vids Web ({prof} • Model {vids_model.upper()} 1080p • Không cần reCAPTCHA)...",
    )

    for idx_s, sc in enumerate(all_scenes):
        sc_id = sc.get("id") or f"s{idx_s + 1}"
        sc_num = int(sc.get("scene_index") or (idx_s + 1))
        out_mp4 = os.path.join(proj_dir, sc.get("output_video_file") or f"fashion_scene_{sc_id}_1080p.mp4")

        # Nếu chỉ chạy 1 cảnh cụ thể (VD s2), vẫn đảm bảo cắt last frame từ s1 nếu s1 đã có sẵn trên ổ đĩa
        if target_scene_id and sc_id != target_scene_id:
            if os.path.isfile(out_mp4) and os.path.getsize(out_mp4) > 50000:
                lf_key = f"scene_{sc_id}_last_frame_2k"
                lf_path = os.path.join(assets_dir, f"{lf_key}.png")
                if not os.path.isfile(lf_path):
                    extract_scene_last_frame_2k(out_mp4, lf_path)
                if os.path.isfile(lf_path):
                    asset_path_map[lf_key] = os.path.abspath(lf_path)
                    asset_path_map[f"{lf_key}.png"] = os.path.abspath(lf_path)
            continue

        # Với Cảnh 2+, cập nhật `prev_scene_last_frame_ref` mới nhất từ Cảnh trước vừa render xong
        if sc_num >= 2 and idx_s >= 1:
            prev_sc = all_scenes[idx_s - 1]
            prev_id = prev_sc.get("id") or f"s{sc_num - 1}"
            prev_mp4 = prev_sc.get("output_video_path") or os.path.join(
                proj_dir, prev_sc.get("output_video_file") or f"fashion_scene_{prev_id}_1080p.mp4"
            )
            lf_key = f"scene_{prev_id}_last_frame_2k"
            lf_fn = f"{lf_key}.png"
            lf_path = os.path.join(assets_dir, lf_fn)
            if os.path.isfile(prev_mp4) and os.path.getsize(prev_mp4) > 50000:
                extract_scene_last_frame_2k(prev_mp4, lf_path)
            if os.path.isfile(lf_path):
                asset_path_map[lf_key] = os.path.abspath(lf_path)
                asset_path_map[lf_fn] = os.path.abspath(lf_path)
                sc["prev_scene_last_frame_ref"] = {"asset_key": lf_key, "filename": lf_fn, "path": lf_path}
            if not sc.get("prev_scene_last_outfit") and prev_sc.get("transitions"):
                sc["prev_scene_last_outfit"] = prev_sc["transitions"][-1].get("outfit")

        # Đảm bảo phân cảnh có `segments_google_vids` chuẩn 3 chip ảnh 2K
        if not sc.get("user_edited_prompt"):
            p_vids = build_scene_timeline_prompt(
                sc,
                start_char_ref,
                char_sheet_ref_obj,
                prompt_style="google_vids",
                prev_scene_last_outfit=sc.get("prev_scene_last_outfit"),
                prev_scene_last_frame_ref=sc.get("prev_scene_last_frame_ref"),
                bpm_info=bpm_info,
            )
            sc["prompt_google_vids"] = p_vids["display_prompt"]
            sc["segments_google_vids"] = p_vids["segments_spec"]
            sc["prompt"] = p_vids["display_prompt"]
            sc["segments_spec"] = p_vids["segments_spec"]
            sc["active_prompt_style"] = "google_vids"
            sc["generation_mode"] = "google_vids"

        dur_sec = int(round(float(sc.get("duration") or sc.get("duration_sec") or 8)))
        sc["attempt"] = 1
        sc["max_attempts"] = max_attempts
        sc["status"] = "rendering:vids_1080p"
        sc["status_detail"] = (
            f"🌐 Đang tải ảnh 2K & tạo Video Phân Cảnh {sc_num} (1080p • {dur_sec}s) trên Google Vids Web ({prof})..."
        )
        _save_live("running_flow", sc["status_detail"])

        # Nếu người dùng tự sửa text prompt thủ công, trích danh sách 3 ảnh từ segments_google_vids để gắn tag tự động
        custom_img_specs = None
        use_segments = sc.get("segments_google_vids") or sc.get("segments_spec")
        if sc.get("user_edited_prompt") and sc.get("prompt"):
            custom_img_specs = []
            for seg in (use_segments or []):
                if seg.get("type") == "media":
                    ak = str(seg.get("asset_key") or "")
                    tt = str(seg.get("title") or "")
                    fp = asset_path_map.get(ak) or asset_path_map.get(tt)
                    if fp and os.path.isfile(fp):
                        custom_img_specs.append({"path": fp, "tags": [f"[{tt}]", tt, ak]})
            use_segments = None

        res_gen = client.generate_video(
            out_mp4=out_mp4,
            prompt=str(sc.get("prompt") or ""),
            image_paths=custom_img_specs,
            segments_spec=use_segments,
            asset_path_map=asset_path_map if use_segments else None,
            profile_name=prof,
            fallback_profiles=fallback_profs,
            model=vids_model,
            aspect_ratio="9:16",
            resolution="1080p",
            duration_sec=dur_sec,
            ingredient_role="fashion",
            max_retries=max_attempts - 1,
        )

        if res_gen.get("ok") and os.path.isfile(out_mp4) and os.path.getsize(out_mp4) > 50000:
            mb_size = round(res_gen["bytes"] / 1048576, 2)
            used_prof = res_gen.get("profile") or prof
            if used_prof != prof:
                _mark_flow_profile_unhealthy(prof, f"Google Vids tự động chuyển sang '{used_prof}'")
                prof = used_prof
                fallback_profs = [p for p in candidate_profiles if p != prof] if multi_acc else []
            _mark_flow_profile_healthy(used_prof)
            q_rem = (res_gen.get("quota") or {}).get("remaining")
            q_str = f" • Quota còn: {q_rem}" if q_rem is not None else ""
            sc["output_video_path"] = out_mp4
            sc["is_ai_generated"] = True
            sc["provider"] = "google_vids"
            sc["last_error"] = ""
            sc["status"] = "done"
            sc["status_detail"] = (
                f"✅ Đã hoàn tất Video Phân Cảnh {sc_num} Native 1080p qua Google Vids "
                f"({used_prof} • {mb_size} MB trong {res_gen['elapsed_sec']}s{q_str})!"
            )
            lf_out = os.path.join(assets_dir, f"scene_{sc_id}_last_frame_2k.png")
            extract_scene_last_frame_2k(out_mp4, lf_out)
            if os.path.isfile(lf_out):
                asset_path_map[f"scene_{sc_id}_last_frame_2k"] = os.path.abspath(lf_out)
                asset_path_map[f"scene_{sc_id}_last_frame_2k.png"] = os.path.abspath(lf_out)
            _save_live("running_flow", sc["status_detail"])
        else:
            err_msg = res_gen.get("error") or "Lỗi tạo video trên Google Vids"
            sc["status"] = f"failed:vids"
            sc["last_error"] = err_msg
            sc["status_detail"] = f"❌ Phân cảnh {sc_num} lỗi trên Google Vids: {err_msg}"
            _save_live("running_flow", sc["status_detail"])
            # Nếu Cảnh 1 lỗi thì dừng sớm vì Cảnh 2 cần Frame cuối Cảnh 1
            if sc_num == 1 and not target_scene_id:
                break

    done_scenes = [
        s for s in (manifest.get("scenes") or [])
        if s.get("status") == "done" or (s.get("output_video_path") and os.path.exists(s.get("output_video_path", "")))
    ]
    failed_scenes = [s for s in scenes_to_run if str(s.get("status") or "").startswith("failed")]

    try:
        if len(done_scenes) == len(manifest.get("scenes") or []):
            post_res = fava.render_fashion_postprod_final_video(
                project_id_slug, proj_dir, manifest, FINAL_VIDEOS_DIR
            )
            if post_res.get("ok"):
                manifest["final_video_path"] = post_res["final_video_path"]
                manifest["final_video_ready"] = True
    except Exception as exc:
        print(f"[GoogleVids PostProd Warn] {exc}", flush=True)

    all_ok = len(failed_scenes) == 0
    manifest["ok"] = all_ok
    if all_ok:
        manifest.pop("error", None)
        manifest["status"] = "completed_flow"
        manifest["status_message"] = (
            f"🎉 Đã hoàn tất Video Final Thời Trang 1080p qua Google Vids Web ({len(done_scenes)} phân cảnh • Không reCAPTCHA)!"
        )
        manifest["message"] = manifest["status_message"]
    else:
        f_ids = ", ".join(str(s.get("id", "")).upper() for s in failed_scenes)
        manifest["status"] = "failed_scenes"
        manifest["status_message"] = f"⚠️ Phân cảnh {f_ids} chưa hoàn tất trên Google Vids: {failed_scenes[0].get('last_error', '')[:160]}"
        manifest["error"] = manifest["status_message"]

    _save_live()
    try:
        import sync_web_ui_state as _sws
        _sws.sync_web_ui(force=True)
    except Exception:
        pass
    manifest["project"] = dict(manifest)
    return manifest


def run_fashion_motion_project_on_flow(
    project_id_slug: str,
    profile_name: str = "",
    target_scene_id: str = "",
    generation_mode: str = "",
) -> dict:
    """
    Thực thi tự động dự án Fashion Video với 3 chế độ tuỳ chọn:
      - `google_vids`: Google Vids Web (`docs.google.com/videos`) Omni 1080p Native — Không cần Chrome/Playwright, không reCAPTCHA, gắn 3 Chip Ảnh 2K gốc.
      - `chained_i2v`: Google Flow Img2Video (`MZZa6b`) + Timeline 0.1s chuẩn nhạc (không dùng Video Ref).
      - `video_ref`:   Google Flow Motion Control Video Ref (`jIps6` / `abra_edit`) + Nối Frame cuối Cảnh 1.
    """
    proj_dir = os.path.join(FASHION_STUDIO_DIR, project_id_slug)
    manifest_path = os.path.join(proj_dir, "fashion_project.json")
    if not os.path.exists(manifest_path):
        return {"ok": False, "error": f"Không tìm thấy project: {project_id_slug}"}

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    if manifest.get('input_flow') == 'simple' and not manifest.get('input_assets_prepared'):
        prepared = prepare_simple_fashion_inputs(project_id_slug, manifest, profile_name)
        if not prepared.get('ok'):
            manifest['status'] = 'failed_input_preparation'
            manifest['status_message'] = prepared.get('error','Không chuẩn bị được ảnh đầu vào.')
            for scene in manifest.get('scenes',[]):
                scene.update(status='failed:input_preparation',status_detail=manifest['status_message'])
            with open(manifest_path,'w',encoding='utf-8') as f:
                json.dump(manifest,f,ensure_ascii=False,indent=2)
            return prepared
        manifest = prepared['project']

    gen_mode_norm = normalize_fashion_generation_mode(
        generation_mode or manifest.get("generation_mode") or "chained_i2v"
    )
    manifest["generation_mode"] = gen_mode_norm

    if gen_mode_norm == "google_vids":
        return _run_fashion_motion_project_on_google_vids(
            project_id_slug=project_id_slug,
            proj_dir=proj_dir,
            manifest=manifest,
            manifest_path=manifest_path,
            profile_name=profile_name,
            target_scene_id=target_scene_id,
        )

    import fashion_ai_video_analyzer as fava
    import grok_video_tool as gvt
    from playwright.sync_api import sync_playwright
    from curl_cffi import requests as cffi_requests
    from run_all_7_videos_mt import (
        upload_single_product_ref_in_page,
        generate_variant_ref_image_in_page,
        submit_upsample_1080p_in_page,
    )

    _last_flow_sync_ts = [0.0]

    def _save_manifest_live(proj_status: str = None, status_msg: str = None):
        if proj_status:
            manifest["status"] = proj_status
        if status_msg:
            manifest["status_message"] = status_msg
        manifest["updated_at"] = time.strftime("%H:%M:%S")
        try:
            with open(manifest_path, "w", encoding="utf-8") as _mf:
                json.dump(manifest, _mf, ensure_ascii=False, indent=2)
        except Exception:
            pass
        now_t = time.monotonic()
        if proj_status in ("completed_final", "failed_scenes", "failed_auth", "failed_upload") or (now_t - _last_flow_sync_ts[0] >= 2.5):
            _last_flow_sync_ts[0] = now_t
            try:
                import sync_web_ui_state as _sws
                threading.Thread(target=lambda: _sws.sync_web_ui(force=True), daemon=True).start()
            except Exception:
                pass

    def _refresh_wiz_tokens_in_page(pw_page, fallback_wiz: dict) -> dict:
        try:
            new_w = pw_page.evaluate(
                """() => {
                    const w = window.WIZ_global_data || {};
                    return {
                        at: w.SNlM0e || '',
                        bl: w.cfb2h || 'boq_labs-ai-sandbox-frontend_20261104.10_p0',
                        fsid: w.FdrFJe || '',
                        ua: navigator.userAgent
                    };
                }"""
            )
            if new_w and new_w.get("at"):
                return new_w
        except Exception:
            pass
        return fallback_wiz

    target_sc_norm = str(target_scene_id or "").strip().lower()
    all_target_scenes = [
        sc
        for sc in (manifest.get("scenes") or [])
        if (not target_sc_norm) or str(sc.get("id") or "").lower() == target_sc_norm
    ]
    if not all_target_scenes:
        return {"ok": False, "error": f"Không tìm thấy phân cảnh '{target_scene_id}' trong project {project_id_slug}"}

    MAX_SCENE_ATTEMPTS = max(1, int(manifest.get("max_scene_attempts", 4)))
    if target_sc_norm:
        for _sc_t in all_target_scenes:
            _sc_t["status"] = "preparing"
            _sc_t["job_uuid_720p"] = None
            _sc_t["job_uuid_1080p"] = None

    candidate_profiles = _get_ordered_flow_account_candidates(
        profile_name or manifest.get("preferred_profile_name") or ""
    )
    last_account_error = ""

    for acc_idx, prof in enumerate(candidate_profiles):
        scenes_to_run = [
            sc
            for sc in all_target_scenes
            if (target_sc_norm and acc_idx == 0)
            or (
                sc.get("status") != "done"
                and not (
                    sc.get("output_video_path")
                    and os.path.exists(sc.get("output_video_path", ""))
                    and os.path.getsize(sc.get("output_video_path", "")) > 50000
                )
            )
        ]
        if not scenes_to_run:
            break

        cookie_hdr = gvt._load_flow_cookie_header(prof)
        if not cookie_hdr:
            last_account_error = f"Tài khoản Flow '{prof}' chưa có Cookie hợp lệ."
            _mark_flow_profile_unhealthy(prof, last_account_error)
            if acc_idx + 1 < len(candidate_profiles):
                next_prof = candidate_profiles[acc_idx + 1]
                _save_manifest_live(
                    "running_flow",
                    f"⚠️ {last_account_error} -> Đang tự động đổi sang tài khoản '{next_prof}' ({acc_idx + 2}/{len(candidate_profiles)})...",
                )
                continue
            return {"ok": False, "error": last_account_error}

        account_project_id = _resolve_account_flow_project_id(prof)
        flow_project_id = account_project_id or manifest.get("flow_project_id")

        # ── GLOBAL ASSET UUID CACHE (Chỉ lưu theo đúng tên file ảnh gốc .png/.jpg, tuyệt đối không lưu key chung như base_char_2k hay outfit_*) ──
        def _is_valid_global_img_key(k_str: str) -> bool:
            kl = str(k_str or "").strip().lower()
            if not kl.endswith((".png", ".jpg", ".jpeg", ".webp")):
                return False
            if kl.startswith(("prepared_", "scene_s", "ref_video_", "outfit_prod_")):
                return False
            return True

        global_cache_path = os.path.join(FASHION_STUDIO_DIR, "_global_flow_asset_cache.json")
        global_proj_cache = {}
        try:
            if os.path.exists(global_cache_path):
                with open(global_cache_path, "r", encoding="utf-8") as _gcf:
                    _all_gc = json.load(_gcf)
                    if isinstance(_all_gc, dict):
                        raw_gc = dict(_all_gc.get(flow_project_id) or {})
                        global_proj_cache = {
                            k: v for k, v in raw_gc.items()
                            if v and _is_valid_global_img_key(k)
                        }
        except Exception:
            global_proj_cache = {}

        if not global_proj_cache:
            for _seed_slug in ("fashion_tpl_fvt_001", "fashion_lookbook_chan_vay_6e19"):
                _seed_p = os.path.join(FASHION_STUDIO_DIR, _seed_slug, "fashion_project.json")
                if os.path.exists(_seed_p):
                    try:
                        _sd = json.load(open(_seed_p, "r", encoding="utf-8"))
                        if _sd.get("flow_project_id") == flow_project_id and isinstance(_sd.get("asset_uuid_map"), dict):
                            for _k, _v in _sd["asset_uuid_map"].items():
                                if _v and _is_valid_global_img_key(_k):
                                    global_proj_cache[_k] = _v
                    except Exception:
                        pass

        def _save_global_asset_cache():
            try:
                _all_gc = {}
                if os.path.exists(global_cache_path):
                    try:
                        _all_gc = json.load(open(global_cache_path, "r", encoding="utf-8"))
                    except Exception:
                        _all_gc = {}
                _all_gc[flow_project_id] = {
                    k: v for k, v in asset_uuid_map.items()
                    if v and _is_valid_global_img_key(k)
                }
                with open(global_cache_path, "w", encoding="utf-8") as _gcf:
                    json.dump(_all_gc, _gcf, ensure_ascii=False, indent=2)
            except Exception:
                pass

        if manifest.get("asset_uuid_project_id") != flow_project_id or manifest.get("flow_project_id") != flow_project_id:
            print(
                f"🔄 [Google Flow] Đồng bộ asset_uuid_map sang đúng Project {flow_project_id} của tài khoản '{prof}'...",
                flush=True,
            )
            asset_uuid_map = dict(global_proj_cache)
            for _sc in manifest.get("scenes") or []:
                _sc["ref_video_uuid"] = None
        else:
            asset_uuid_map = dict(global_proj_cache)
            for _mk, _mv in (manifest.get("asset_uuid_map") or {}).items():
                if _mv and (_is_valid_global_img_key(_mk) or str(_mk).startswith(("scene_s", "ref_video_"))):
                    asset_uuid_map[_mk] = _mv

        manifest["flow_project_id"] = flow_project_id
        manifest["asset_uuid_project_id"] = flow_project_id
        manifest["active_profile_name"] = prof

        http_sess = cffi_requests.Session(impersonate="chrome131")
        dl_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": "https://flow.google.com/",
            "Cookie": cookie_hdr,
        }

        for _sc_init in scenes_to_run:
            _sc_init["status"] = "preparing"
            _sc_init["attempt"] = 1
            _sc_init["_retries"] = 0
            _sc_init["max_attempts"] = MAX_SCENE_ATTEMPTS
            _sc_init["job_uuid_720p"] = None
            _sc_init["job_uuid_1080p"] = None
            _sc_init["status_detail"] = (
                f"🚀 Đang kết nối Google Flow ({prof}) & chuẩn bị nguyên liệu 2K cho Phân Cảnh {_sc_init.get('scene_index', _sc_init['id'])}..."
            )
        _save_manifest_live(
            "running_flow",
            f"🚀 Đang khởi chạy tạo video trên Google Flow bằng tài khoản '{prof}' ({len(scenes_to_run)} phân cảnh)...",
        )

        with sync_playwright() as pw:
            browser = _launch_flow_browser(pw)
            context = None
            _bypass_js = getattr(gvt, "_FLOW_HIJACK_BYPASS_JS", None) or getattr(gvt, "_RECAPTCHA_BYPASS_INIT_SCRIPT", None)

            context = browser.new_context(viewport={"width": 1280, "height": 800})
            if _bypass_js:
                context.add_init_script(_bypass_js)

            pw_cookies = _build_playwright_cookies_from_header(cookie_hdr, prof)
            if pw_cookies:
                context.add_cookies(pw_cookies)

            try:
                page = context.new_page()
                if _bypass_js:
                    page.add_init_script(_bypass_js)
                page.goto(f"https://flow.google.com/project/{flow_project_id}", wait_until="domcontentloaded", timeout=60000)
                if _bypass_js:
                    try:
                        page.evaluate(_bypass_js)
                    except Exception:
                        pass
                try:
                    page.wait_for_function(
                        "() => window.WIZ_global_data && window.WIZ_global_data.SNlM0e && window.grecaptcha && window.grecaptcha.enterprise && typeof window.grecaptcha.enterprise.execute === 'function'",
                        timeout=40000,
                    )
                except Exception:
                    page.wait_for_timeout(5000)
                page.wait_for_timeout(1500)

                wiz = _refresh_wiz_tokens_in_page(page, {})
                if not wiz.get("at"):
                    err_msg = f"Phiên đăng nhập Google Flow của '{prof}' đã hết hạn (thiếu SNlM0e tại {page.url})."
                    raise RuntimeError(err_msg)

                try:
                    live_c = context.cookies(["https://flow.google.com", "https://google.com", "https://accounts.google.com"])
                    c_map = {c["name"]: c["value"] for c in live_c if "GRECAPTCHA" not in c.get("name", "").upper()}
                    if c_map:
                        cookie_hdr = "; ".join(f"{k}={v}" for k, v in c_map.items())
                        dl_headers = {
                            "Cookie": cookie_hdr,
                            "Referer": "https://flow.google.com/",
                            "User-Agent": wiz["ua"],
                        }
                except Exception:
                    pass

                print(f"✅ [Google Flow] Đã kết nối Project {flow_project_id} (bl={wiz['bl']})", flush=True)

                def _upload_img_with_401_recovery(img_p: str, q_val: int = 98):
                    nonlocal wiz
                    ok_x, uid_x, err_x = upload_single_product_ref_in_page(page, wiz, flow_project_id, img_p, quality=q_val)
                    if not ok_x:
                        if "401" in str(err_x):
                            try:
                                page.reload(wait_until="domcontentloaded", timeout=45000)
                                page.wait_for_timeout(2500)
                            except Exception:
                                time.sleep(2.5)
                        else:
                            time.sleep(2.0)
                        wiz = _refresh_wiz_tokens_in_page(page, wiz)
                        ok_x, uid_x, err_x = upload_single_product_ref_in_page(page, wiz, flow_project_id, img_p, quality=q_val)
                    return ok_x, uid_x, err_x

                did_any_upload_in_session = False

                # 1. Upload Ảnh Nhân Vật Gốc 2K (Tra cứu theo đúng filename để khi đổi nhân vật sẽ upload ảnh mới ngay!)
                base_char = manifest["base_char_2k"]
                bc_fn = base_char.get("filename") or ""
                cached_bc_uid = asset_uuid_map.get(bc_fn) if bc_fn else asset_uuid_map.get("base_char_2k")
                if not cached_bc_uid:
                    _save_manifest_live("running_flow", f"📸 Đang upload Ảnh Nhân Vật 2K ({bc_fn})...")
                    ok_u, u_id, err_u = _upload_img_with_401_recovery(base_char["path"], 98)
                    if not ok_u:
                        err_msg = f"Upload Ảnh Nhân Vật 2K thất bại ({prof}): {err_u}"
                        raise RuntimeError(err_msg)
                    did_any_upload_in_session = True
                    asset_uuid_map["base_char_2k"] = u_id
                    asset_uuid_map[bc_fn] = u_id
                    manifest["asset_uuid_map"] = asset_uuid_map
                    _save_manifest_live()
                    _save_global_asset_cache()
                    print(f"📸 Uploaded Base Char 2K ({bc_fn}) -> {u_id}", flush=True)
                else:
                    asset_uuid_map["base_char_2k"] = cached_bc_uid
                    if bc_fn:
                        asset_uuid_map[bc_fn] = cached_bc_uid

                # 2. Upload (hoặc Tách nền Flat-Lay 2K nếu ảnh sản phẩm thô chưa tách) toàn bộ Ảnh Bộ Đồ 2K (Product Sheets)
                for outf in manifest.get("outfits") or []:
                    o_key = outf["id"]
                    o_fn = outf.get("filename") or ""
                    cached_o_uid = asset_uuid_map.get(o_fn) if o_fn else asset_uuid_map.get(o_key)
                    if not cached_o_uid or outf.get("needs_deconstruct_sheet"):
                        _save_manifest_live("running_flow", f"👗 Đang upload Ảnh Sản Phẩm 2K ({o_fn})...")
                        if outf.get("needs_deconstruct_sheet") and outf.get("raw_product_path") and os.path.exists(outf["raw_product_path"]):
                            ok_raw, raw_u_id, _ = _upload_img_with_401_recovery(outf["raw_product_path"], 96)
                            if ok_raw and raw_u_id:
                                did_any_upload_in_session = True
                                flatlay_prompt = STANDARD_FASHION_PROMPTS["deconstructed_outfit_flatlay_2k"]["prompt_en"]
                                if outf.get("en_desc"):
                                    flatlay_prompt += f" Product details: {outf['en_desc']}."
                                ok_fl, fl_uuid_2k, _ = generate_variant_ref_image_in_page(
                                    page,
                                    wiz,
                                    cookie_hdr,
                                    dl_headers,
                                    {
                                        "pid": project_id_slug,
                                        "v_key": f"flatlay_{o_key}",
                                        "project_id": flow_project_id,
                                        "char_id": "",
                                        "prod_uuids": [raw_u_id],
                                        "allow_multi_refs": False,
                                        "prompt_str": flatlay_prompt,
                                        "out_file": outf["path"],
                                    },
                                )
                                if ok_fl and fl_uuid_2k:
                                    cached_o_uid = fl_uuid_2k
                                    asset_uuid_map[o_key] = fl_uuid_2k
                                    asset_uuid_map[o_fn] = fl_uuid_2k
                                    outf["needs_deconstruct_sheet"] = False
                                    manifest["asset_uuid_map"] = asset_uuid_map
                                    _save_manifest_live()
                                    _save_global_asset_cache()
                                    print(f"✨ Tách nền Product Sheet 2K ({o_fn}) -> {fl_uuid_2k}", flush=True)
                        if not cached_o_uid:
                            ok_o, o_id, err_o = _upload_img_with_401_recovery(outf["path"], 98)
                            if not ok_o:
                                err_msg = f"Upload Ảnh Outfit '{o_fn}' thất bại ({prof}): {err_o}"
                                raise RuntimeError(err_msg)
                            did_any_upload_in_session = True
                            asset_uuid_map[o_key] = o_id
                            asset_uuid_map[o_fn] = o_id
                            manifest["asset_uuid_map"] = asset_uuid_map
                            _save_manifest_live()
                            _save_global_asset_cache()
                            print(f"👗 Uploaded Outfit Product Sheet 2K ({o_fn}) -> {o_id}", flush=True)
                    else:
                        asset_uuid_map[o_key] = cached_o_uid
                        if o_fn:
                            asset_uuid_map[o_fn] = cached_o_uid

                # 3A. Upload Ảnh Bối Cảnh Căn Phòng & Bộ Đồ Basic Mở Đầu 2K (`07_Nhan_Vat_Basic_Phong_Ngu_2K.png` hoặc Ảnh Nhân Vật Mới)
                cs_obj = manifest.get("char_sheet_2k")
                if cs_obj:
                    cs_fn = cs_obj.get("filename") or ""
                    cached_cs_uid = asset_uuid_map.get(cs_fn) if cs_fn else asset_uuid_map.get("char_sheet_2k")
                    if not cached_cs_uid:
                        if cs_obj.get("path") and os.path.exists(cs_obj["path"]) and not cs_obj.get("needs_auto_generate"):
                            ok_cs, cs_id, _ = _upload_img_with_401_recovery(cs_obj["path"], 96)
                            if ok_cs and cs_id:
                                did_any_upload_in_session = True
                                asset_uuid_map["char_sheet_2k"] = cs_id
                                asset_uuid_map[cs_fn] = cs_id
                                manifest["asset_uuid_map"] = asset_uuid_map
                                _save_manifest_live()
                                _save_global_asset_cache()
                                print(f"📸 Uploaded Room Background & Basic Ref 2K ({cs_fn}) -> {cs_id}", flush=True)
                    else:
                        asset_uuid_map["char_sheet_2k"] = cached_cs_uid
                        if cs_fn:
                            asset_uuid_map[cs_fn] = cached_cs_uid

                # 3B. Upload Bảng Tham Chiếu Tổng Thể Các Bộ Đồ 2K (`01_Character_Sheet_4_Outfits_2K.png`)
                overall_sheet_fn = "01_Character_Sheet_4_Outfits_2K.png"
                overall_sheet_p = os.path.join(proj_dir, "assets_2k", overall_sheet_fn)
                if not manifest.get("disable_overall_sheet") and not os.path.exists(overall_sheet_p):
                    cand_ov = os.path.join(DEMO_ASSETS_DIR, overall_sheet_fn)
                    if os.path.exists(cand_ov):
                        shutil.copy2(cand_ov, overall_sheet_p)
                if manifest.get("disable_overall_sheet"):
                    asset_uuid_map.pop(overall_sheet_fn, None)
                    asset_uuid_map.pop("overall_sheet_2k", None)
                cached_ov_uid = asset_uuid_map.get(overall_sheet_fn) or asset_uuid_map.get("overall_sheet_2k")
                if not cached_ov_uid:
                    if not manifest.get("disable_overall_sheet") and os.path.exists(overall_sheet_p):
                        ok_ov, ov_id, _ = _upload_img_with_401_recovery(overall_sheet_p, 96)
                        if ok_ov and ov_id:
                            did_any_upload_in_session = True
                            asset_uuid_map["overall_sheet_2k"] = ov_id
                            asset_uuid_map[overall_sheet_fn] = ov_id
                            manifest["asset_uuid_map"] = asset_uuid_map
                            _save_manifest_live()
                            _save_global_asset_cache()
                            print(f"📸 Uploaded Overall 4-Outfits Sheet 2K ({overall_sheet_fn}) -> {ov_id}", flush=True)
                else:
                    asset_uuid_map["overall_sheet_2k"] = cached_ov_uid
                    asset_uuid_map[overall_sheet_fn] = cached_ov_uid

                _save_global_asset_cache()

                # 4A. NẾU CHẾ ĐỘ LÀ `video_ref`: UPLOAD ĐA LUỒNG SONG SONG (`Promise.all`) TẤT CẢ CLIP VIDEO THAM CHIẾU 30 FPS (`ref_clip_s1_8s.mp4`, `ref_clip_s2_8s.mp4`)
                # (Nếu chế độ là `chained_i2v`, KHÔNG upload Video Tham Chiếu vì tạo hoàn toàn từ Img2Video + Timeline 0.1s!)
                if gen_mode_norm == "video_ref":
                    vids_to_upload = []
                    for sc in scenes_to_run:
                        sc_id = sc["id"]
                        vid_key = f"ref_video_{sc_id}"
                        if not asset_uuid_map.get(vid_key):
                            sc["status"] = "uploading_video"
                            sc["status_detail"] = f"🎬 Đang upload song song Video Tham Chiếu {sc['ref_clip_filename']} (30 FPS)..."
                            vids_to_upload.append({"key": vid_key, "sc": sc, "path": sc["ref_clip_path"]})

                    if vids_to_upload:
                        _save_manifest_live(
                            "running_flow",
                            f"⚡ Đang upload song song {len(vids_to_upload)} clip Video Tham Chiếu 30FPS ({', '.join(v['sc']['ref_clip_filename'] for v in vids_to_upload)})...",
                        )
                        par_res = upload_multiple_reference_videos_parallel_in_page(
                            page, wiz, flow_project_id, [{"key": v["key"], "path": v["path"]} for v in vids_to_upload]
                        )
                        for v_it in vids_to_upload:
                            vk = v_it["key"]
                            sc_v = v_it["sc"]
                            r_v = par_res.get(vk) or {}
                            if r_v.get("ok") and r_v.get("uuid"):
                                did_any_upload_in_session = True
                                asset_uuid_map[vk] = r_v["uuid"]
                                print(f"🎬 [Parallel Upload] {sc_v['ref_clip_filename']} -> {r_v['uuid']}", flush=True)
                            else:
                                wiz = _refresh_wiz_tokens_in_page(page, wiz)
                                ok_v, v_uuid, _, err_v = upload_reference_video_in_page(page, wiz, flow_project_id, v_it["path"])
                                if not ok_v:
                                    err_msg = f"Upload Video Tham Chiếu '{sc_v['ref_clip_filename']}' thất bại ({prof}): {err_v}"
                                    sc_v["status"] = "failed:upload_video"
                                    sc_v["status_detail"] = f"❌ {err_msg}"
                                    raise RuntimeError(err_msg)
                                did_any_upload_in_session = True
                                asset_uuid_map[vk] = v_uuid
                                print(f"🎬 Uploaded Reference Video 30fps ({sc_v['ref_clip_filename']}) -> {v_uuid}", flush=True)

                # Nếu toàn bộ Ảnh 2K và Video Ref đều đã lấy từ Cache (0 lượt upload trong phiên mở trang này),
                # thực hiện 1 lượt warmup maseQ nhanh (~1s) để kích hoạt phiên reCAPTCHA Enterprise, tránh lỗi PUBLIC_ERROR_UNUSUAL_ACTIVITY ngay từ Try 1!
                if not did_any_upload_in_session and base_char.get("path") and os.path.exists(base_char["path"]):
                    try:
                        ok_w0, w0_uid, _ = upload_single_product_ref_in_page(page, wiz, flow_project_id, base_char["path"], quality=95)
                        if ok_w0 and w0_uid:
                            asset_uuid_map["base_char_2k"] = w0_uid
                            if bc_fn:
                                asset_uuid_map[bc_fn] = w0_uid
                            _save_global_asset_cache()
                    except Exception:
                        pass

                def _extract_and_upload_prev_scene_last_frame(prev_sc_id: str, prev_video_path: str) -> str:
                    """Cắt Frame cuối của phân cảnh trước (`prev_sc_id`) chuẩn 2K (`1536x2752`) và upload lên Google Flow qua `maseQ`."""
                    lf_key = f"scene_{prev_sc_id}_last_frame_2k"
                    lf_fn = f"{lf_key}.png"
                    lf_path = os.path.join(proj_dir, "assets_2k", lf_fn)
                    if prev_video_path and os.path.exists(prev_video_path) and os.path.getsize(prev_video_path) > 50000:
                        extract_scene_last_frame_2k(prev_video_path, lf_path)
                    if os.path.exists(lf_path):
                        # Upload encoded JPEG with matching filename and MIME, preserving
                        # the exact extracted frame rather than substituting the room.
                        lf_jpg = os.path.splitext(lf_path)[0] + ".jpg"
                        with Image.open(lf_path) as frame_image:
                            frame_image.convert("RGB").save(lf_jpg, "JPEG", quality=95)
                        ok_lf, lf_uid, err_lf = _upload_img_with_401_recovery(lf_jpg, 95)
                        if ok_lf and lf_uid:
                            asset_uuid_map[lf_key] = lf_uid
                            asset_uuid_map[lf_fn] = lf_uid
                            manifest["asset_uuid_map"] = asset_uuid_map
                            _save_manifest_live()
                            print(f"🎞️ [Last-Frame Continuity] Cắt & Upload Frame cuối {lf_fn} -> {lf_uid}", flush=True)
                            return lf_uid
                        print(f"⚠️ [Last-Frame Upload Warn] {lf_fn}: {err_lf}", flush=True)
                    if asset_uuid_map.get(lf_key):
                        return asset_uuid_map[lf_key]
                    raise RuntimeError(f"Cannot upload continuity frame {lf_fn}; scene submission stopped")

                def _prepare_and_submit_scene(sc: dict, is_retry: bool = False, retry_idx: int = 0) -> bool:
                    """Chuẩn bị danh sách ảnh tham chiếu + prompt (theo `gen_mode_norm`) và gửi đúng 1 job duy nhất cho phân cảnh `sc`."""
                    nonlocal wiz
                    sc_id = sc["id"]
                    sc_num = int(sc.get("scene_index") or 1)
                    sc_idx_label = sc.get("scene_index", sc_id)
                    clip_path = sc.get("ref_clip_path") or ""
                    vid_key = f"ref_video_{sc_id}"
                    if gen_mode_norm == "video_ref" and asset_uuid_map.get(vid_key):
                        sc["ref_video_uuid"] = asset_uuid_map[vid_key]
                        asset_uuid_map[sc["ref_clip_filename"]] = sc["ref_video_uuid"]

                    # Nếu đây là Phân cảnh 2+ (sc_num >= 2), đảm bảo Frame cuối của Phân cảnh trước đã được cắt & upload
                    prev_sc_id = f"s{sc_num - 1}"
                    lf_key = f"scene_{prev_sc_id}_last_frame_2k"
                    lf_fn = f"{lf_key}.png"
                    lf_path = os.path.join(proj_dir, "assets_2k", lf_fn)
                    if sc_num >= 2:
                        if not asset_uuid_map.get(lf_key):
                            prev_mp4 = os.path.join(proj_dir, f"fashion_scene_{prev_sc_id}_1080p.mp4")
                            _extract_and_upload_prev_scene_last_frame(prev_sc_id, prev_mp4)
                        sc["prev_scene_last_frame_ref"] = {
                            "asset_key": lf_key,
                            "filename": lf_fn,
                            "path": lf_path,
                        }

                    # Xây dựng lại prompt theo đúng chế độ (`chained_i2v` hoặc `timeline_pro`)
                    sc["start_char_ref"] = {
                        "asset_key": "base_char_2k",
                        "filename": manifest["base_char_2k"]["filename"],
                        "path": manifest["base_char_2k"]["path"],
                        "is_continuity_generated": False,
                    }
                    char_sheet_ref_obj = manifest.get("char_sheet_2k")
                    target_p_style = "chained_i2v" if gen_mode_norm == "chained_i2v" else "timeline_pro"
                    rebuilt_p = build_scene_timeline_prompt(
                        sc,
                        sc["start_char_ref"],
                        char_sheet_ref_obj,
                        prompt_style=target_p_style,
                        bpm_info=(manifest.get("split_plan") or {}).get("bpm_info"),
                    )
                    sc["generation_mode"] = gen_mode_norm
                    sc["active_prompt_style"] = target_p_style
                    if gen_mode_norm == "chained_i2v":
                        sc["prompt_chained_i2v"] = rebuilt_p["display_prompt"]
                        sc["segments_chained_i2v"] = rebuilt_p["segments_spec"]
                    else:
                        sc["prompt_timeline_pro"] = rebuilt_p["display_prompt"]
                        sc["segments_timeline_pro"] = rebuilt_p["segments_spec"]
                        sc["prompt_concise_flow"] = rebuilt_p["display_prompt"]
                        sc["segments_concise_flow"] = rebuilt_p["segments_spec"]
                    if not sc.get("user_edited_prompt"):
                        sc["prompt"] = rebuilt_p["display_prompt"]
                        sc["segments_spec"] = rebuilt_p["segments_spec"]

                    # Tập hợp danh sách ảnh tham chiếu chuẩn xác cho từng chế độ:
                    sc_transitions = sc.get("transitions") or []
                    sc_img_uuids = []
                    if gen_mode_norm == "chained_i2v":
                        # Chế độ Chained I2V (`MZZa6b` / `macaron_cookie_r2v_8s`):
                        # - Cảnh 1: [Ảnh phòng ngủ Basic 07 + Character Sheet 01]
                        # - Cảnh 2+: [Ảnh Frame cuối Cảnh 1 (`scene_s1_last_frame_2k.png`) + Character Sheet 01]
                        open_uid = (
                            (asset_uuid_map.get(lf_key) or asset_uuid_map.get("char_sheet_2k"))
                            if sc_num >= 2
                            else asset_uuid_map.get("char_sheet_2k")
                        )
                        if open_uid:
                            sc_img_uuids.append(open_uid)
                        sc_img_uuids = resolve_fashion_prompt_image_refs(
                            sc.get("segments_spec") or rebuilt_p["segments_spec"], asset_uuid_map
                        )
                        use_model_key = "abra_r2v_8s" if (is_retry and retry_idx >= 2) else "macaron_cookie_r2v_8s"
                    else:
                        # Chế độ Motion Control Video Ref (`jIps6` / `abra_edit`):
                        # - Cảnh 1: Mở đầu từ `char_sheet_2k` (`07_Nhan_Vat_Basic_Phong_Ngu_2K.png`)
                        # - Cảnh 2+: Mở đầu nối tiếp từ `scene_s1_last_frame_2k` (`scene_s1_last_frame_2k.png`)!
                        open_bg_uid = (
                            (asset_uuid_map.get(lf_key) or asset_uuid_map.get("char_sheet_2k"))
                            if sc_num >= 2
                            else asset_uuid_map.get("char_sheet_2k")
                        )
                        if asset_uuid_map.get("base_char_2k"):
                            sc_img_uuids.append(asset_uuid_map["base_char_2k"])
                        if len(sc_transitions) <= 2 and asset_uuid_map.get("overall_sheet_2k") and asset_uuid_map["overall_sheet_2k"] not in sc_img_uuids:
                            sc_img_uuids.append(asset_uuid_map["overall_sheet_2k"])
                        if open_bg_uid and open_bg_uid not in sc_img_uuids:
                            sc_img_uuids.append(open_bg_uid)
                        for tr in sc_transitions[:3]:
                            o_u = asset_uuid_map.get(tr["outfit"].get("filename") or "") or asset_uuid_map.get(tr["outfit"]["id"])
                            if o_u and o_u not in sc_img_uuids and len(sc_img_uuids) < 5:
                                sc_img_uuids.append(o_u)
                        if len(sc_img_uuids) < 5 and asset_uuid_map.get("overall_sheet_2k") and asset_uuid_map["overall_sheet_2k"] not in sc_img_uuids:
                            sc_img_uuids.append(asset_uuid_map["overall_sheet_2k"])
                        sc_img_uuids = sc_img_uuids[:5]
                        use_model_key = sc.get("model_key") or (manifest.get("split_plan") or {}).get("model_key_edit") or "abra_edit"
                        if is_retry and retry_idx >= 3:
                            use_model_key = "macaron_cookie_edit"

                    sc["_sc_img_uuids"] = sc_img_uuids
                    # Persist the actual prompt/chip bindings immediately before submission.
                    if gen_mode_norm == "chained_i2v":
                        audit_segments = sc.get("segments_spec") or rebuilt_p["segments_spec"]
                        sc["submitted_prompt_audit"] = {
                            "display_prompt": sc.get("prompt") or rebuilt_p["display_prompt"],
                            "segments_spec": audit_segments,
                            "image_ref_uuids": sc_img_uuids,
                            "encoded_prompt": encode_flow_structured_prompt_Nj(
                                audit_segments, asset_uuid_map, allowed_image_uuids=sc_img_uuids
                            ),
                        }

                    ok_sub, job_uuid, err_sub = False, None, ""
                    for sub_try in range(1, 4):
                        sc["status"] = "submitting" if sub_try == 1 else f"retrying_submit_{sub_try}"
                        sc["status_detail"] = (
                            f"🚀 Đang gửi lệnh tạo video Phân Cảnh {sc_idx_label} lên Google Flow ({use_model_key})..."
                            if sub_try == 1
                            else f"🔁 Lỗi gửi lệnh ({err_sub[:45]}) -> Đang tự động Retry gửi lại ngay (Lần {sub_try}/3)..."
                        )
                        _save_manifest_live("running_flow", sc["status_detail"])
                        if sub_try > 1:
                            time.sleep(2.0)
                            if "UNUSUAL_ACTIVITY" in str(err_sub).upper():
                                try:
                                    page.reload(wait_until="domcontentloaded", timeout=35000)
                                    page.wait_for_timeout(2000)
                                    page.mouse.move(400, 360, steps=10)
                                    page.mouse.wheel(0, 120)
                                    page.wait_for_timeout(500)
                                    wiz = _refresh_wiz_tokens_in_page(page, wiz)
                                    if base_char.get("path") and os.path.exists(base_char["path"]):
                                        ok_w, w_uid, _ = upload_single_product_ref_in_page(page, wiz, flow_project_id, base_char["path"])
                                        if ok_w and w_uid:
                                            asset_uuid_map["base_char_2k"] = w_uid
                                            if bc_fn:
                                                asset_uuid_map[bc_fn] = w_uid
                                except Exception:
                                    pass
                            wiz = _refresh_wiz_tokens_in_page(page, wiz)
                            if gen_mode_norm == "video_ref" and any(k in str(err_sub).upper() for k in ("INVALID", "NOT_FOUND", "[3]", "[5]")):
                                re_clip = (sc.get("adult_safe_clip_path") if sub_try >= 2 and sc.get("adult_safe_clip_path") and os.path.exists(sc.get("adult_safe_clip_path")) else clip_path)
                                ok_rv, rv_uid, _, _ = upload_reference_video_in_page(page, wiz, flow_project_id, re_clip)
                                if ok_rv and rv_uid:
                                    sc["ref_video_uuid"] = rv_uid
                                    asset_uuid_map[vid_key] = rv_uid
                                    asset_uuid_map[sc["ref_clip_filename"]] = rv_uid

                        if gen_mode_norm == "chained_i2v":
                            ok_sub, job_uuid, err_sub = submit_fashion_chained_i2v_scene_in_page(
                                page,
                                wiz,
                                {
                                    "project_id": flow_project_id,
                                    "image_ref_uuids": sc_img_uuids,
                                    "asset_uuid_map": asset_uuid_map,
                                    "segments_spec": sc.get("segments_spec") or rebuilt_p["segments_spec"],
                                    "display_prompt": sc.get("prompt") or rebuilt_p["display_prompt"],
                                    "model_key": use_model_key,
                                },
                            )
                        else:
                            ok_sub, job_uuid, err_sub = submit_fashion_motion_scene_in_page(
                                page,
                                wiz,
                                {
                                    "project_id": flow_project_id,
                                    "ref_video_uuid": sc.get("ref_video_uuid"),
                                    "duration": sc["duration"],
                                    "fps": 30,
                                    "start_frame": 1,
                                    "end_frame": round(int(sc.get("duration") or 8) * 30) + 1,
                                    "image_ref_uuids": sc_img_uuids,
                                    "asset_uuid_map": asset_uuid_map,
                                    "segments_spec": sc.get("segments_spec") or rebuilt_p["segments_spec"],
                                    "display_prompt": sc.get("prompt") or rebuilt_p["display_prompt"],
                                    "model_key": use_model_key,
                                },
                            )
                        if ok_sub and job_uuid:
                            break
                        print(f"⚠️ [Submit {sc_id} Try {sub_try}/3 Failed] {err_sub}", flush=True)

                    if not ok_sub or not job_uuid:
                        sc["status"] = f"failed:submit_{str(err_sub)[:40]}"
                        sc["last_error"] = str(err_sub)
                        sc["status_detail"] = f"❌ Gửi lệnh tạo video Phân Cảnh {sc_id} thất bại sau 3 lần thử: {err_sub}"
                        _save_manifest_live("running_flow", sc["status_detail"])
                        return False

                    sc["job_uuid_720p"] = job_uuid
                    sc["job_uuid_1080p"] = None
                    if not is_retry:
                        sc["_retries"] = 0
                        sc["attempt"] = 1
                    sc["max_attempts"] = MAX_SCENE_ATTEMPTS
                    sc["_job_start_ts"] = time.time()
                    sc["_rpc_errs"] = 0
                    sc["last_error"] = ""
                    sc["status"] = "submitted_720p"
                    sc["status_detail"] = f"⏳ Đang tạo video Cảnh {sc_idx_label} trên Google Flow ({use_model_key} • Lần thử {sc.get('attempt', 1)}/{MAX_SCENE_ATTEMPTS})..."
                    print(f"🚀 [Google Flow {gen_mode_norm}/{use_model_key}] Đã gửi Phân Cảnh {sc_id} -> media_uuid={job_uuid}", flush=True)
                    return True

                # 4B. KHỞI CHẠY PHÂN CẢNH 1 TRƯỚC, PHÂN CẢNH 2+ CHỜ CẮT FRAME CUỐI CỦA PHÂN CẢNH 1 ĐỂ NỐI TIẾP LIỀN MẠCH!
                # (Nếu user chỉ bấm Render riêng Phân cảnh 2 khi Phân cảnh 1 đã xong từ trước, Phân cảnh 2 sẽ tự cắt Frame cuối Cảnh 1 và gửi ngay!)
                waiting_chained_scenes = []
                running_s1_in_batch = any(int(s.get("scene_index") or 1) == 1 for s in scenes_to_run)

                for sc in scenes_to_run:
                    sc_num = int(sc.get("scene_index") or 1)
                    if sc_num >= 2 and running_s1_in_batch:
                        sc["job_uuid_720p"] = None
                        sc["job_uuid_1080p"] = None
                        sc["status"] = "waiting_prev_scene_frame"
                        sc["status_detail"] = f"⏳ Đang chờ Phân Cảnh {sc_num - 1} hoàn tất để cắt Frame cuối 2K (`scene_s{sc_num - 1}_last_frame_2k.png`) nối tiếp sang Phân Cảnh {sc_num}..."
                        waiting_chained_scenes.append(sc)
                    else:
                        _prepare_and_submit_scene(sc, is_retry=False, retry_idx=0)

                manifest["asset_uuid_map"] = asset_uuid_map
                _save_manifest_live(
                    "running_flow",
                    f"⚡ Đang chạy chế độ {'Chained Img2Video 0.1s' if gen_mode_norm == 'chained_i2v' else 'Motion Control Video Ref'} trên Google Flow...",
                )

                # 6. POLL ĐA LUỒNG SONG SONG (`ThreadPoolExecutor`) & TỰ ĐỘNG CẮT FRAME CUỐI CẢNH 1 ĐỂ GỬI CẢNH 2 NGAY LẬP TỨC!
                pending = [sc for sc in scenes_to_run if sc.get("job_uuid_720p")]
                start_wait = time.time()
                while (pending or waiting_chained_scenes) and (time.time() - start_wait) < 900:
                    if not pending:
                        break
                    time.sleep(3.0)
                    still_pending = []

                    def _poll_worker(sc_item):
                        _sid = sc_item["id"]
                        _out_p = os.path.join(proj_dir, sc_item["output_video_file"])
                        _stg = "upsample_1080p" if sc_item.get("job_uuid_1080p") else "base_720p"
                        _p_uid = sc_item.get("job_uuid_1080p") or sc_item.get("job_uuid_720p")
                        _t_sess = cffi_requests.Session(impersonate="chrome131")
                        _st, _blen = _poll_flow_scene_video_cffi(
                            _t_sess, cookie_hdr, wiz, dl_headers, flow_project_id, _p_uid, _out_p, stage=_stg, page=None
                        )
                        return _sid, _stg, _p_uid, _out_p, _st, _blen

                    poll_map = {}
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(pending))) as _pool:
                        futs = {_pool.submit(_poll_worker, sc): sc for sc in pending}
                        for fut in concurrent.futures.as_completed(futs):
                            sc_ref = futs[fut]
                            try:
                                poll_map[sc_ref["id"]] = fut.result()
                            except Exception as _pe:
                                poll_map[sc_ref["id"]] = (
                                    sc_ref["id"],
                                    "upsample_1080p" if sc_ref.get("job_uuid_1080p") else "base_720p",
                                    sc_ref.get("job_uuid_1080p") or sc_ref.get("job_uuid_720p"),
                                    os.path.join(proj_dir, sc_ref["output_video_file"]),
                                    f"rpc_err:{_pe}",
                                    None,
                                )

                    for sc in pending:
                        sc_id = sc["id"]
                        sc_num = int(sc.get("scene_index") or 1)
                        sc_idx_label = sc.get("scene_index", sc_id)
                        _, stage, poll_uid, out_mp4, st_res, byte_len = poll_map[sc_id]
                        elapsed_s = int(time.time() - (sc.get("_job_start_ts") or start_wait))
                        sc["elapsed_sec"] = elapsed_s
                        cur_attempt = int(sc.get("attempt") or (int(sc.get("_retries") or 0) + 1))

                        if str(st_res).startswith("rpc_err:") or str(st_res).startswith("dl_err:"):
                            st_res, byte_len = _poll_flow_scene_video_cffi(
                                http_sess, cookie_hdr, wiz, dl_headers, flow_project_id, poll_uid, out_mp4, stage=stage, page=page
                            )

                        print(
                            f"⏳ [Poll {sc_id} | {gen_mode_norm} | {stage} | Try {cur_attempt}/{MAX_SCENE_ATTEMPTS} | {elapsed_s}s | {poll_uid[:8]}] -> {st_res} ({byte_len or 0} bytes)",
                            flush=True,
                        )

                        if str(st_res).startswith("rpc_err:") or str(st_res).startswith("dl_err:"):
                            sc["_rpc_errs"] = int(sc.get("_rpc_errs") or 0) + 1
                            if sc["_rpc_errs"] >= 3:
                                st_res = f"failed:{st_res}"
                        else:
                            sc["_rpc_errs"] = 0

                        if stage == "base_720p" and str(st_res).startswith("rendering:") and elapsed_s > 185:
                            print(f"⚠️ [Timeout Watchdog {sc_id}] Treo >185s ở trạng thái {st_res} -> Kích hoạt Retry ngay!", flush=True)
                            st_res = "failed:timeout_185s"
                        elif stage == "upsample_1080p" and str(st_res).startswith("rendering:") and elapsed_s > 60 and os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 50000:
                            print(f"⚡ [Fast-Path 1080p {sc_id}] Upsample Flow >60s -> Dùng ngay file AI đã tải để hậu kỳ!", flush=True)
                            st_res = "done"
                            byte_len = os.path.getsize(out_mp4)

                        if st_res == "ready_for_1080p":
                            sc["output_video_path"] = out_mp4
                            sc["is_ai_generated"] = True
                            sc["flow_job_id"] = sc["job_uuid_720p"]
                            sc["last_error"] = ""
                            sc["status_detail"] = f"✨ Đã tải xong bản 720p ({round((byte_len or 0)/1048576, 2)} MB) -> Đang nâng cấp lên 1080p & cắt Frame cuối nối Cảnh tiếp theo..."

                            # ⚡ NGAY KHI CẢNH TRƯỚC (`s1`) TẢI XONG VIDEO: CẮT FRAME CUỐI 2K, UPLOAD LÊN FLOW VÀ GỬI CẢNH TIẾP THEO (`s2`) CHẠY SONG SONG!
                            next_wait_list = [w for w in waiting_chained_scenes if int(w.get("scene_index") or 2) == sc_num + 1]
                            if next_wait_list:
                                _extract_and_upload_prev_scene_last_frame(sc_id, out_mp4)
                                for w_sc in next_wait_list:
                                    waiting_chained_scenes.remove(w_sc)
                                    if _prepare_and_submit_scene(w_sc, is_retry=False, retry_idx=0):
                                        still_pending.append(w_sc)

                            ok_up, up_uid, _ = submit_upsample_1080p_in_page(
                                page,
                                wiz,
                                {
                                    "pid": project_id_slug,
                                    "sc": {"id": sc_id},
                                    "project_id": flow_project_id,
                                    "base_video_uuid": sc["job_uuid_720p"],
                                },
                            )
                            if ok_up and up_uid:
                                sc["job_uuid_1080p"] = up_uid
                                sc["_job_start_ts"] = time.time()
                                sc["status"] = "upsampling_1080p"
                                still_pending.append(sc)
                            else:
                                sc["status"] = "done"
                                sc["status_detail"] = f"✅ Đã tạo xong Video Phân Cảnh {sc_idx_label} (Lần thử {cur_attempt}/{MAX_SCENE_ATTEMPTS})!"
                        elif st_res == "done":
                            sc["output_video_path"] = out_mp4
                            sc["is_ai_generated"] = True
                            sc["flow_job_id"] = sc.get("job_uuid_1080p") or sc.get("job_uuid_720p")
                            sc["last_error"] = ""
                            sc["status"] = "done"
                            sc["status_detail"] = f"✅ Đã hoàn tất Video Phân Cảnh {sc_idx_label} 1080p ({round((byte_len or 0)/1048576, 2)} MB)!"
                            # Cập nhật lại ảnh Frame cuối trên ổ đĩa từ bản 1080p sắc nét
                            if sc_num == 1 and os.path.exists(out_mp4):
                                extract_scene_last_frame_2k(out_mp4, os.path.join(proj_dir, "assets_2k", f"scene_{sc_id}_last_frame_2k.png"))
                            next_wait_list = [w for w in waiting_chained_scenes if int(w.get("scene_index") or 2) == sc_num + 1]
                            if next_wait_list:
                                _extract_and_upload_prev_scene_last_frame(sc_id, out_mp4)
                                for w_sc in next_wait_list:
                                    waiting_chained_scenes.remove(w_sc)
                                    if _prepare_and_submit_scene(w_sc, is_retry=False, retry_idx=0):
                                        still_pending.append(w_sc)
                        elif str(st_res).startswith("failed"):
                            if stage == "upsample_1080p" and os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 50000:
                                sc["output_video_path"] = out_mp4
                                sc["is_ai_generated"] = True
                                sc["flow_job_id"] = sc.get("job_uuid_720p")
                                sc["last_error"] = ""
                                sc["status"] = "done"
                                sc["status_detail"] = f"✅ Đã tạo xong Video Phân Cảnh {sc_idx_label} (Bản chuẩn AI)!"
                            elif stage == "base_720p" and int(sc.get("_retries") or 0) < (MAX_SCENE_ATTEMPTS - 1):
                                sc["_retries"] = int(sc.get("_retries") or 0) + 1
                                retry_idx = sc["_retries"]
                                sc["attempt"] = retry_idx + 1
                                sc["last_error"] = st_res
                                sc["status"] = f"retrying_{retry_idx}"
                                sc["status_detail"] = (
                                    f"🔁 Phát hiện lỗi tạo video ({st_res}) ở Cảnh {sc_idx_label} -> "
                                    f"Đang tự động Retry ngay lập tức (Lần thử {sc['attempt']}/{MAX_SCENE_ATTEMPTS})..."
                                )
                                _save_manifest_live("running_flow", sc["status_detail"])
                                print(f"⚡ [Auto-Retry Immediate {sc_id}] {sc['status_detail']}", flush=True)

                                wiz = _refresh_wiz_tokens_in_page(page, wiz)
                                if gen_mode_norm == "video_ref" and retry_idx in (1, 2):
                                    adult_clip = sc.get("adult_safe_clip_path") or ""
                                    re_clip_p = adult_clip if (adult_clip and os.path.exists(adult_clip)) else sc.get("ref_clip_path")
                                    if re_clip_p and os.path.exists(re_clip_p):
                                        ok_rv2, rv2_uid, _, _ = upload_reference_video_in_page(page, wiz, flow_project_id, re_clip_p)
                                        if ok_rv2 and rv2_uid:
                                            sc["ref_video_uuid"] = rv2_uid
                                            asset_uuid_map[f"ref_video_{sc_id}"] = rv2_uid
                                            asset_uuid_map[sc["ref_clip_filename"]] = rv2_uid

                                time.sleep(2)
                                if _prepare_and_submit_scene(sc, is_retry=True, retry_idx=retry_idx):
                                    still_pending.append(sc)
                            else:
                                sc["status"] = st_res
                                sc["last_error"] = st_res
                                sc["status_detail"] = f"❌ Tạo video Cảnh {sc_idx_label} không thành công sau {MAX_SCENE_ATTEMPTS} lần thử ({st_res}). Bấm Retry để chạy lại!"
                        else:
                            sc["status"] = st_res
                            sc["status_detail"] = (
                                f"⏳ Đang tạo video Cảnh {sc_idx_label} trên Google Flow "
                                f"(Lần thử {cur_attempt}/{MAX_SCENE_ATTEMPTS} • {elapsed_s}s)..."
                            )
                            still_pending.append(sc)
                    pending = still_pending
                    if pending:
                        summary_parts = [
                            f"Cảnh {s.get('scene_index', s['id'])}: Lần {s.get('attempt', 1)}/{MAX_SCENE_ATTEMPTS} ({s.get('elapsed_sec', 0)}s)"
                            for s in pending
                        ]
                        if waiting_chained_scenes:
                            summary_parts.append(f"Cảnh 2: Chờ nối Frame cuối Cảnh 1")
                        _save_manifest_live("running_flow", "⏳ Đang theo dõi & tạo video: " + " | ".join(summary_parts))
                    else:
                        _save_manifest_live("running_flow", "✅ Đã hoàn tất vòng theo dõi các phân cảnh!")

                for _sc_clean in manifest.get("scenes") or []:
                    _sc_clean.pop("_sc_img_uuids", None)
                    _sc_clean.pop("_job_start_ts", None)
                    _sc_clean.pop("_rpc_errs", None)
                _save_manifest_live()
            except Exception as _acc_exc:
                last_account_error = str(_acc_exc)
                _mark_flow_profile_unhealthy(prof, last_account_error)
                for _sc_f in scenes_to_run:
                    if _sc_f.get("status") != "done":
                        _sc_f["status"] = "failed:account_error"
                        _sc_f["last_error"] = last_account_error
                        _sc_f["status_detail"] = f"⚠️ {last_account_error}"
                if acc_idx + 1 < len(candidate_profiles):
                    next_prof = candidate_profiles[acc_idx + 1]
                    _save_manifest_live(
                        "running_flow",
                        f"🔄 Tài khoản '{prof}' lỗi ({last_account_error[:70]}) -> Chủ động chuyển sang tài khoản '{next_prof}' ({acc_idx + 2}/{len(candidate_profiles)})...",
                    )
                else:
                    _save_manifest_live("failed_auth", last_account_error)
            finally:
                try:
                    context.close()
                except Exception:
                    pass
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass

        remaining_unfinished = [
            sc
            for sc in all_target_scenes
            if sc.get("status") != "done"
            and not (
                sc.get("output_video_path")
                and os.path.exists(sc.get("output_video_path", ""))
                and os.path.getsize(sc.get("output_video_path", "")) > 50000
            )
        ]
        if not remaining_unfinished:
            _mark_flow_profile_healthy(prof)
            break

        if not last_account_error:
            last_account_error = (
                remaining_unfinished[0].get("last_error")
                or remaining_unfinished[0].get("status_detail")
                or f"Tài khoản '{prof}' chưa hoàn tất phân cảnh"
            )
        _mark_flow_profile_unhealthy(prof, last_account_error)
        if acc_idx + 1 < len(candidate_profiles):
            next_prof = candidate_profiles[acc_idx + 1]
            _save_manifest_live(
                "running_flow",
                f"🔄 Tài khoản '{prof}' chưa hoàn tất ({str(last_account_error)[:65]}) -> Chủ động chuyển sang tài khoản '{next_prof}' ({acc_idx + 2}/{len(candidate_profiles)}) để chạy tiếp...",
            )
            continue

    # 7. Render hậu kỳ ghép các phân cảnh AI hoàn chỉnh + Nhạc gốc ở chuẩn 24 FPS CFR mượt mà thành Video Final
    done_scenes = [s for s in (manifest.get("scenes") or []) if s.get("status") == "done" or (s.get("output_video_path") and os.path.exists(s.get("output_video_path", "")))]
    failed_scenes = [
        s
        for s in all_target_scenes
        if s.get("status") != "done"
        and not (
            s.get("output_video_path")
            and os.path.exists(s.get("output_video_path", ""))
            and os.path.getsize(s.get("output_video_path", "")) > 50000
        )
    ]
    try:
        if len(done_scenes) == len(manifest.get("scenes") or []):
            post_res = fava.render_fashion_postprod_final_video(
                project_id_slug, proj_dir, manifest, FINAL_VIDEOS_DIR
            )
            if post_res.get("ok"):
                manifest["final_video_path"] = post_res["final_video_path"]
                manifest["final_video_ready"] = True
    except Exception as e:
        print(f"[PostProd Warn] {e}", flush=True)

    all_target_ok = len(failed_scenes) == 0
    manifest["ok"] = all_target_ok
    if all_target_ok:
        manifest.pop("error", None)
        manifest["status"] = "completed_flow"
        manifest["status_message"] = f"🎉 Đã hoàn tất Video Final Thời Trang 1080p ({len(done_scenes)} phân cảnh • Chế độ {gen_mode_norm})!"
        manifest["message"] = manifest["status_message"]
    else:
        failed_ids = ", ".join(str(s.get("id", "")).upper() for s in failed_scenes)
        manifest["status"] = "failed_scenes"
        manifest["status_message"] = f"⚠️ Phân cảnh {failed_ids} lỗi sau {MAX_SCENE_ATTEMPTS} lần thử tự động."
        manifest["error"] = manifest["status_message"]

    _save_manifest_live()
    try:
        import sync_web_ui_state as _sws
        _sws.sync_web_ui(force=True)
    except Exception:
        pass
    manifest["project"] = dict(manifest)
    return manifest


def run_single_fashion_motion_scene_on_flow(
    project_id_slug: str,
    scene_id: str,
    profile_name: str = "",
    generation_mode: str = "",
) -> dict:
    """Render trực tiếp 1 phân cảnh cụ thể trên Google Flow (theo `generation_mode`: `chained_i2v` hoặc `video_ref`) và cập nhật Video Final."""
    return run_fashion_motion_project_on_flow(
        project_id_slug=project_id_slug,
        profile_name=profile_name,
        target_scene_id=scene_id,
        generation_mode=generation_mode,
    )


def retry_failed_fashion_scenes_on_flow(project_id_slug: str, profile_name: str = "") -> dict:
    """
    Kiểm tra tất cả các phân cảnh bị lỗi (`failed*`) hoặc chưa có video trong dự án `project_id_slug`
    và tự động chạy Retry ngay lập tức trên Google Flow.
    """
    proj_dir = os.path.join(FASHION_STUDIO_DIR, project_id_slug)
    manifest_path = os.path.join(proj_dir, "fashion_project.json")
    if not os.path.exists(manifest_path):
        return {"ok": False, "error": f"Không tìm thấy project: {project_id_slug}"}
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    failed_ids = [
        sc["id"]
        for sc in (manifest.get("scenes") or [])
        if str(sc.get("status") or "").startswith("failed")
        or not (sc.get("output_video_path") and os.path.exists(sc.get("output_video_path", "")))
    ]
    if not failed_ids:
        return {"ok": True, "message": "Tất cả phân cảnh đã hoàn tất, không có phân cảnh lỗi cần Retry.", "project": manifest}
    for sc in manifest.get("scenes") or []:
        if sc["id"] in failed_ids:
            sc["job_uuid_720p"] = None
            sc["job_uuid_1080p"] = None
            sc["_retries"] = 0
            sc["status"] = "retrying_auto"
    prev_err_msg = str(manifest.get("status_message") or "")
    for _cand_p in _get_ordered_flow_account_candidates(""):
        if f"'{_cand_p}'" in prev_err_msg and ("hết hạn" in prev_err_msg or "SNlM0e" in prev_err_msg or "lỗi" in prev_err_msg.lower()):
            _mark_flow_profile_unhealthy(_cand_p, prev_err_msg)
    if not profile_name:
        manifest["preferred_profile_name"] = ""
    manifest["status"] = "running_flow"
    manifest["status_message"] = "🔄 Đang tự động đổi sang tài khoản Google Flow khả dụng để chạy lại các phân cảnh lỗi..."
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    if len(failed_ids) == 1:
        return run_fashion_motion_project_on_flow(project_id_slug, profile_name=profile_name, target_scene_id=failed_ids[0])
    return run_fashion_motion_project_on_flow(project_id_slug, profile_name=profile_name)


# ==============================================================================
# 8. QUẢN LÝ THƯ VIỆN NHÂN VẬT, TÁCH NỀN TRẮNG SẢN PHẨM 2K (CHATGPT / BANANA) & ÁP DỤNG 30+ TEMPLATE VIDEO
# ==============================================================================

CUSTOM_FASHION_LIBRARY_JSON = os.path.join(WS_DIR, "data", "fashion_templates_cache", "custom_fashion_library.json")


def _load_custom_fashion_library() -> dict:
    os.makedirs(os.path.dirname(CUSTOM_FASHION_LIBRARY_JSON), exist_ok=True)
    if os.path.exists(CUSTOM_FASHION_LIBRARY_JSON):
        try:
            with open(CUSTOM_FASHION_LIBRARY_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"characters": [], "outfits": []}


def _save_custom_fashion_library(data: dict) -> None:
    os.makedirs(os.path.dirname(CUSTOM_FASHION_LIBRARY_JSON), exist_ok=True)
    with open(CUSTOM_FASHION_LIBRARY_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_fashion_characters_and_outfits_library() -> dict:
    """
    Trả về danh sách Nhân Vật và Sản Phẩm Quần Áo (Outfits) trong Thư Viện Thời Trang:
      - Mặc định Nhân Vật: Bộ nhân vật mới của người dùng (`02_Character_Sheet_Basic_Poses_2K.png` + bối cảnh `07_Nhan_Vat_Basic_Phong_Ngu_2K.png`)
        cùng các nhân vật trong `Kho Nhân Vật` và nhân vật người dùng thêm mới.
      - Mặc định Sản Phẩm (Quần Áo): 5 bộ đồ nền trắng chuẩn 2K của người dùng (`03`..`08`) + các bộ đồ người dùng thêm mới/tách nền trắng.
    """
    custom_lib = _load_custom_fashion_library()

    default_pose_p = os.path.join(DEMO_ASSETS_DIR, "02_Character_Sheet_Basic_Poses_2K.png")
    default_bg_p = os.path.join(DEMO_ASSETS_DIR, "07_Nhan_Vat_Basic_Phong_Ngu_2K.png")
    default_wardrobe_p = os.path.join(DEMO_ASSETS_DIR, "01_Character_Sheet_4_Outfits_2K.png")

    characters = [
        {
            "id": "char_default_nv5_2k",
            "key": "char_default_nv5_2k",
            "name": "⭐ Nhân Vật Mặc Định (NV5 — 02_Character_Sheet_Basic_Poses_2K.png + Phòng Ngủ 07)",
            "char_filename": "02_Character_Sheet_Basic_Poses_2K.png",
            "char_path": default_pose_p,
            "pose_sheet_path": default_pose_p,
            "bg_filename": "07_Nhan_Vat_Basic_Phong_Ngu_2K.png",
            "bg_path": default_bg_p,
            "bg_ref_path": default_bg_p,
            "wardrobe_sheet_path": default_wardrobe_p if os.path.exists(default_wardrobe_p) else "",
            "is_default": True,
            "badge": "MẶC ĐỊNH 2K",
        },
        {
            "id": "char_nv5_tu_go_2k",
            "key": "char_nv5_tu_go_2k",
            "name": "Nhân Vật NV5 — Bối Cảnh Phòng Thay Đồ Tủ Gỗ (09_NV5_Phong_Tu_Go_Mo_Dau_2K.png)",
            "char_filename": "02_Character_Sheet_Basic_Poses_2K.png",
            "char_path": default_pose_p,
            "pose_sheet_path": default_pose_p,
            "bg_filename": "09_NV5_Phong_Tu_Go_Mo_Dau_2K.png",
            "bg_path": os.path.join(DEMO_ASSETS_DIR, "09_NV5_Phong_Tu_Go_Mo_Dau_2K.png"),
            "bg_ref_path": os.path.join(DEMO_ASSETS_DIR, "09_NV5_Phong_Tu_Go_Mo_Dau_2K.png"),
            "is_default": False,
            "badge": "PHÒNG TỦ GỖ 2K",
        },
    ]

    for c_item in custom_lib.get("characters") or []:
        c_p = c_item.get("char_path") or c_item.get("pose_sheet_path")
        if c_p and os.path.exists(c_p):
            c_copy = dict(c_item)
            c_copy["char_path"] = c_p
            c_copy["pose_sheet_path"] = c_p
            bg_p = c_copy.get("bg_path") or c_copy.get("bg_ref_path") or c_p
            # Nếu nhân vật tuỳ chỉnh trước đây bị gán nhầm bg_path = 07_Nhan_Vat_Basic_Phong_Ngu_2K.png của NV5,
            # tự động dùng chính ảnh nhân vật tuỳ chỉnh làm ảnh mở đầu & nhận diện khuôn mặt!
            if os.path.basename(bg_p) == "07_Nhan_Vat_Basic_Phong_Ngu_2K.png" and os.path.basename(c_p) != "02_Character_Sheet_Basic_Poses_2K.png":
                bg_p = c_p
            c_copy["bg_path"] = bg_p
            c_copy["bg_ref_path"] = bg_p
            c_copy["bg_filename"] = os.path.basename(bg_p)
            characters.append(c_copy)

    # Tích hợp toàn bộ nhân vật từ Kho Nhân Vật chung (`voices_and_characters.json`: NV1, NV2, ...)
    try:
        import character_library_manager as _clm
        clm_state = _clm.get_character_library_state()
        seen_paths_clm = {os.path.abspath(c["char_path"]) for c in characters if c.get("char_path") and os.path.exists(c["char_path"])}
        for ch_item in (clm_state.get("characters") or []):
            ch_abs = ch_item.get("ref_image_abs") or ""
            if not ch_abs and ch_item.get("ref_image"):
                ch_abs = os.path.join(WS_DIR, str(ch_item["ref_image"]).lstrip("/\\"))
            if ch_abs and os.path.exists(ch_abs) and os.path.abspath(ch_abs) not in seen_paths_clm:
                ch_key = ch_item.get("key") or os.path.splitext(os.path.basename(ch_abs))[0]
                ch_fn = os.path.basename(ch_abs)
                seen_paths_clm.add(os.path.abspath(ch_abs))
                characters.append({
                    "id": f"char_store_{ch_key}",
                    "key": f"char_store_{ch_key}",
                    "name": f"👤 Kho Nhân Vật: {ch_item.get('name') or ch_key.upper()} ({ch_fn})",
                    "char_filename": ch_fn,
                    "char_path": os.path.abspath(ch_abs),
                    "pose_sheet_path": os.path.abspath(ch_abs),
                    "bg_filename": ch_fn,
                    "bg_path": os.path.abspath(ch_abs),
                    "bg_ref_path": os.path.abspath(ch_abs),
                    "is_default": False,
                    "badge": f"KHO NV ({ch_key.upper()})",
                })
    except Exception:
        pass

    # Quét thêm từ thư mục `character_library` nếu có
    char_lib_dir = os.path.join(WS_DIR, "character_library")
    if os.path.exists(char_lib_dir):
        seen_paths = {os.path.abspath(c["char_path"]) for c in characters if c.get("char_path") and os.path.exists(c["char_path"])}
        for fn in sorted(os.listdir(char_lib_dir)):
            if fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                fp = os.path.join(char_lib_dir, fn)
                if os.path.abspath(fp) not in seen_paths:
                    characters.append({
                        "id": f"char_lib_{os.path.splitext(fn)[0]}",
                        "key": f"char_lib_{os.path.splitext(fn)[0]}",
                        "name": f"Thư Viện NV: {os.path.splitext(fn)[0]}",
                        "char_filename": fn,
                        "char_path": fp,
                        "pose_sheet_path": fp,
                        "bg_filename": fn,
                        "bg_path": fp,
                        "bg_ref_path": fp,
                        "is_default": False,
                        "badge": "KHO NHÂN VẬT",
                    })

    outfits = []
    for d_out in DEFAULT_FASHION_DEMO_OUTFITS:
        op = os.path.join(DEMO_ASSETS_DIR, d_out["filename"])
        if os.path.exists(op):
            item_c = dict(d_out)
            item_c["path"] = op
            item_c["is_default"] = True
            item_c["is_white_bg_sheet"] = True
            lb_fn = d_out.get("lookbook_model_filename") or ""
            if lb_fn and os.path.exists(os.path.join(DEMO_ASSETS_DIR, lb_fn)):
                item_c["lookbook_model_path"] = os.path.join(DEMO_ASSETS_DIR, lb_fn)
            outfits.append(item_c)

    seen_outfit_files = {o["filename"] for o in outfits}
    for o_item in custom_lib.get("outfits") or []:
        if o_item.get("path") and os.path.exists(o_item["path"]) and o_item.get("filename") not in seen_outfit_files:
            outfits.append(o_item)
            seen_outfit_files.add(o_item["filename"])

    return {
        "ok": True,
        "characters": characters,
        "outfits": outfits,
    }


def add_custom_fashion_character(char_image_path: str, char_name: str = "", bg_image_path: str = "") -> dict:
    """Thêm 1 nhân vật mới vào Thư Viện Nhân Vật Thời Trang (tự động nâng cấp lên chuẩn 2K)."""
    if not char_image_path or not os.path.exists(char_image_path):
        return {"ok": False, "error": f"Không tìm thấy file ảnh nhân vật: {char_image_path}"}

    os.makedirs(DEMO_ASSETS_DIR, exist_ok=True)
    fn = os.path.basename(char_image_path)
    clean_fn = re.sub(r"[^a-zA-Z0-9_.-]+", "_", fn)
    if not clean_fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        clean_fn += ".png"
    dst_char = os.path.join(DEMO_ASSETS_DIR, clean_fn)
    if os.path.abspath(char_image_path) != os.path.abspath(dst_char):
        shutil.copy2(char_image_path, dst_char)
    ensure_image_is_2k(dst_char)

    if bg_image_path and os.path.exists(bg_image_path):
        bg_fn = re.sub(r"[^a-zA-Z0-9_.-]+", "_", os.path.basename(bg_image_path))
        dst_bg = os.path.join(DEMO_ASSETS_DIR, bg_fn)
        if os.path.abspath(bg_image_path) != os.path.abspath(dst_bg):
            shutil.copy2(bg_image_path, dst_bg)
        ensure_image_is_2k(dst_bg)
    else:
        # Mặc định dùng chính ảnh nhân vật 2K của người dùng làm ảnh mở đầu & giữ nhận diện khuôn mặt (KHÔNG lấy ảnh phòng ngủ NV5!)
        dst_bg = dst_char
        bg_fn = clean_fn

    lib = _load_custom_fashion_library()
    c_id = f"char_custom_{int(time.time())}"
    new_char = {
        "id": c_id,
        "key": c_id,
        "name": (char_name or "").strip() or f"Nhân Vật Mới ({clean_fn})",
        "char_filename": clean_fn,
        "char_path": dst_char,
        "pose_sheet_path": dst_char,
        "bg_filename": bg_fn,
        "bg_path": dst_bg,
        "bg_ref_path": dst_bg,
        "is_default": False,
        "badge": "NHÂN VẬT MỚI 2K",
    }
    existing_chars = [c for c in (lib.get("characters") or []) if c.get("char_filename") != clean_fn]
    existing_chars.insert(0, new_char)
    lib["characters"] = existing_chars
    _save_custom_fashion_library(lib)
    return {"ok": True, "character": new_char, "library": list_fashion_characters_and_outfits_library()}


def upload_custom_fashion_asset_base64(
    filename: str,
    data_base64: str,
    kind: str = "outfit",
    name: str = "",
    short_desc: str = "",
    en_desc: str = "",
    project_id_slug: str = "",
    auto_white_bg_local: bool = False,
) -> dict:
    """
    Nhận file ảnh/video người dùng chọn trực tiếp từ trình duyệt (HTML5 File Input),
    lưu xuống ổ đĩa, chuẩn hóa 2K và đăng ký vào Thư Viện Thời Trang / Dự Án hiện tại.
    """
    if not data_base64:
        return {"ok": False, "error": "Dữ liệu file tải lên trống (thiếu data_base64)."}
    b64_str = str(data_base64).strip()
    if "," in b64_str and b64_str.lower().startswith("data:"):
        b64_str = b64_str.split(",", 1)[1]
    try:
        raw_bytes = base64.b64decode(b64_str)
    except Exception as e:
        return {"ok": False, "error": f"Giải mã base64 thất bại: {e}"}

    if len(raw_bytes) < 64:
        return {"ok": False, "error": "File tải lên quá nhỏ hoặc không hợp lệ."}

    kind_norm = str(kind or "outfit").strip().lower()
    orig_bn = os.path.basename(str(filename or f"upload_{int(time.time())}.png"))
    stem, ext = os.path.splitext(orig_bn)
    clean_stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", stem).strip("_")[:42] or f"Custom_{int(time.time())}"
    if clean_stem.lower() in ("prod_1", "prod_2", "prod_3", "image", "media", "clipboard", "upload", "screenshot"):
        import hashlib as _hl_u
        clean_stem = f"{clean_stem}_{_hl_u.sha1(raw_bytes).hexdigest()[:6]}"
    ext_low = ext.lower()

    def _invalidate_global_asset_cache_filename(fn_to_clear: str):
        if not fn_to_clear:
            return
        gc_p = os.path.join(FASHION_STUDIO_DIR, "_global_flow_asset_cache.json")
        if not os.path.exists(gc_p):
            return
        try:
            with open(gc_p, "r", encoding="utf-8") as _gf:
                gc_data = json.load(_gf)
            if isinstance(gc_data, dict):
                changed = False
                for _proj_u, _u_map in gc_data.items():
                    if isinstance(_u_map, dict) and fn_to_clear in _u_map:
                        _u_map.pop(fn_to_clear, None)
                        changed = True
                if changed:
                    with open(gc_p, "w", encoding="utf-8") as _gf:
                        json.dump(gc_data, _gf, ensure_ascii=False, indent=2)
        except Exception:
            pass

    if kind_norm == "video":
        if ext_low not in (".mp4", ".mov", ".webm", ".mkv"):
            ext_low = ".mp4"
        up_dir = os.path.join(FASHION_STUDIO_DIR, "_custom_uploads")
        os.makedirs(up_dir, exist_ok=True)
        clean_fn = f"{clean_stem}{ext_low}"
        dst_p = os.path.join(up_dir, clean_fn)
        with open(dst_p, "wb") as f:
            f.write(raw_bytes)
        return {"ok": True, "kind": "video", "path": dst_p, "filename": clean_fn}

    if ext_low not in (".png", ".jpg", ".jpeg", ".webp"):
        ext_low = ".png"
    os.makedirs(DEMO_ASSETS_DIR, exist_ok=True)

    if kind_norm == "character":
        clean_fn = f"Char_{clean_stem}_2K.png" if not clean_stem.endswith("_2K") else f"Char_{clean_stem}.png"
        dst_p = os.path.join(DEMO_ASSETS_DIR, clean_fn)
        with open(dst_p, "wb") as f:
            f.write(raw_bytes)
        _invalidate_global_asset_cache_filename(clean_fn)
        res_c = add_custom_fashion_character(dst_p, char_name=name or stem)
        if not res_c.get("ok"):
            return res_c
        ch_obj = res_c["character"]
        _invalidate_global_asset_cache_filename(ch_obj.get("char_filename") or "")
        return {
            "ok": True,
            "kind": "character",
            "path": ch_obj["char_path"],
            "filename": ch_obj["char_filename"],
            "character": ch_obj,
            "library": res_c.get("library"),
        }

    if kind_norm == "bg":
        clean_fn = f"BG_{clean_stem}_2K.png" if not clean_stem.endswith("_2K") else f"BG_{clean_stem}.png"
        dst_p = os.path.join(DEMO_ASSETS_DIR, clean_fn)
        with open(dst_p, "wb") as f:
            f.write(raw_bytes)
        _invalidate_global_asset_cache_filename(clean_fn)
        info_2k = ensure_image_is_2k(dst_p)
        return {
            "ok": True,
            "kind": "bg",
            "path": dst_p,
            "filename": clean_fn,
            "width": info_2k.get("width", 1536),
            "height": info_2k.get("height", 2752),
        }

    # Mặc định: kind == "outfit" (Sản phẩm quần áo của người dùng)
    clean_fn = f"Outfit_{clean_stem}_2K.png" if not clean_stem.endswith("_2K") else f"Outfit_{clean_stem}.png"
    dst_p = os.path.join(DEMO_ASSETS_DIR, clean_fn)
    raw_tmp_p = os.path.join(DEMO_ASSETS_DIR, f"_raw_{clean_fn}")
    with open(raw_tmp_p, "wb") as f:
        f.write(raw_bytes)
    _invalidate_global_asset_cache_filename(clean_fn)

    if auto_white_bg_local:
        try:
            _create_clean_white_bg_product_sheet_local_2k(raw_tmp_p, dst_p, outfit_name=name or stem)
        except Exception:
            shutil.copy2(raw_tmp_p, dst_p)
    else:
        shutil.copy2(raw_tmp_p, dst_p)

    info_2k = ensure_image_is_2k(dst_p)
    outfit_id = f"outfit_custom_{clean_stem.lower()}"
    final_name = (name or "").strip() or f"SP Thời Trang: {stem}"
    new_outfit_entry = {
        "id": outfit_id,
        "filename": clean_fn,
        "path": dst_p,
        "raw_product_path": raw_tmp_p if os.path.exists(raw_tmp_p) else dst_p,
        "name": final_name,
        "short_desc": (short_desc or "").strip() or f"trang phục thời trang theo đúng ảnh sản phẩm {clean_fn}",
        "en_desc": (en_desc or "").strip() or f"exact fashion outfit matching product reference image {clean_fn}",
        "width": info_2k.get("width", 1536),
        "height": info_2k.get("height", 2752),
        "is_2k": True,
        "is_default": False,
        "is_white_bg_sheet": bool(auto_white_bg_local),
    }

    lib = _load_custom_fashion_library()
    existing_outfits = [o for o in (lib.get("outfits") or []) if o.get("filename") != clean_fn]
    existing_outfits.insert(0, new_outfit_entry)
    lib["outfits"] = existing_outfits
    _save_custom_fashion_library(lib)

    if project_id_slug:
        proj_assets = os.path.join(FASHION_STUDIO_DIR, project_id_slug, "assets_2k")
        os.makedirs(proj_assets, exist_ok=True)
        proj_dst = os.path.join(proj_assets, clean_fn)
        if os.path.abspath(dst_p) != os.path.abspath(proj_dst):
            shutil.copy2(dst_p, proj_dst)

    return {
        "ok": True,
        "kind": "outfit",
        "path": dst_p,
        "filename": clean_fn,
        "outfit": new_outfit_entry,
        "library": list_fashion_characters_and_outfits_library(),
    }


def _create_clean_white_bg_product_sheet_local_2k(source_image_path: str, out_file: str, outfit_name: str = "") -> dict:
    """
    Tạo bảng Product Sheet Nền Trắng Tinh (#FFFFFF) chuẩn 2K (2048x2559, tỷ lệ 4:5 giống 03_Product_Sheet_Quan_Xanh_2K.png):
      - Tự động tách nền / làm trắng nền quanh sản phẩm quần áo gốc.
      - Bố cục phẳng phiu trên nền trắng tinh (#FFFFFF) không chữ, sắc nét chuẩn 2K.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    canvas_w, canvas_h = 2048, 2559
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))

    with Image.open(source_image_path) as im:
        im_rgba = im.convert("RGBA")
        w, h = im_rgba.size
        px = im_rgba.load()
        # Lấy màu nền ở 4 góc ảnh để làm sạch nền xám/kem thành trắng tinh (#FFFFFF)
        corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
        bg_r = sum(c[0] for c in corners) / 4.0
        bg_g = sum(c[1] for c in corners) / 4.0
        bg_b = sum(c[2] for c in corners) / 4.0

        # Nếu ảnh có nền sáng hoặc đồng màu ở viền, tự động tẩy trắng nền mịn màng
        cleaned = Image.new("RGBA", (w, h), (255, 255, 255, 255))
        c_px = cleaned.load()
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a < 25:
                    c_px[x, y] = (255, 255, 255, 255)
                    continue
                dist = math.sqrt((r - bg_r) ** 2 + (g - bg_g) ** 2 + (b - bg_b) ** 2)
                if dist < 22 and (r > 205 and g > 205 and b > 205):
                    c_px[x, y] = (255, 255, 255, 255)
                else:
                    c_px[x, y] = (r, g, b, 255)

        prod_rgb = cleaned.convert("RGB")
        # Căn giữa sản phẩm chiếm 86% khung 2048x2559 nền trắng tinh
        max_w = int(canvas_w * 0.86)
        max_h = int(canvas_h * 0.88)
        scale = min(max_w / float(w), max_h / float(h))
        nw = max(64, int(round(w * scale)))
        nh = max(64, int(round(h * scale)))
        prod_resized = prod_rgb.resize((nw, nh), Image.Resampling.LANCZOS)
        prod_resized = prod_resized.filter(ImageFilter.UnsharpMask(radius=1.1, percent=120, threshold=2))
        ox = (canvas_w - nw) // 2
        oy = (canvas_h - nh) // 2
        canvas.paste(prod_resized, (ox, oy))

    ext = os.path.splitext(out_file)[1].lower()
    if ext == ".png":
        canvas.save(out_file, format="PNG", optimize=True)
    else:
        canvas.save(out_file, format="JPEG", quality=98, subsampling=0)
    return {"ok": True, "path": out_file, "width": canvas_w, "height": canvas_h}


def deconstruct_user_product_to_white_bg_sheet_2k(
    source_image_path: str,
    outfit_name: str = "",
    model_provider: str = "nano_banana",
    project_id_slug: str = "fashion_lookbook_chan_vay_6e19",
    profile_name: str = "",
) -> dict:
    """
    Chuyển đổi 1 ảnh quần áo bất kỳ của người dùng (ảnh chụp mẫu mặc, ảnh shop, hoặc ảnh sản phẩm)
    thành Ảnh Tham Chiếu Quần Áo Tiêu Chuẩn Nền Trắng 2K (`03_Product_Sheet_..._2K.png` — nền trắng tinh #FFFFFF, chỉ có quần áo & phụ kiện):
      - Hỗ trợ chọn model:
        1. `nano_banana`: Dùng trực tiếp Nano Banana 2.1 2K trên Google Flow (`ogiZ0b` -> `SPrCad`).
        2. `chatgpt`: Dùng model ChatGPT Vision (`gpt-4o` / `gpt-5` qua CLIProxy `:8317`) phân tích chi tiết form dáng/chất liệu/màu sắc
           của bộ quần áo rồi gọi Image Generation / Nano Banana 2K tách thành bảng Product Sheet nền trắng tinh 2K.
      - Luôn đảm bảo xuất ra file `.png` chuẩn 2K (`2048x2559`), lưu vào cả Project hiện tại lẫn Thư Viện Sản Phẩm Thời Trang.
    """
    if not source_image_path or not os.path.exists(source_image_path):
        return {"ok": False, "error": f"Không tìm thấy ảnh sản phẩm gốc: {source_image_path}"}

    os.makedirs(DEMO_ASSETS_DIR, exist_ok=True)
    base_stem = os.path.splitext(os.path.basename(source_image_path))[0]
    clean_stem = re.sub(r"[^a-zA-Z0-9]+", "_", base_stem).strip("_")[:32] or f"Outfit_{int(time.time())}"
    if clean_stem.endswith("_2K"):
        out_filename = f"Product_Sheet_{clean_stem}.png"
    else:
        out_filename = f"Product_Sheet_{clean_stem}_2K.png"

    out_demo_path = os.path.join(DEMO_ASSETS_DIR, out_filename)
    proj_dir = os.path.join(FASHION_STUDIO_DIR, project_id_slug or "fashion_lookbook_chan_vay_6e19")
    proj_assets_dir = os.path.join(proj_dir, "assets_2k")
    os.makedirs(proj_assets_dir, exist_ok=True)
    out_proj_path = os.path.join(proj_assets_dir, out_filename)

    provider_norm = str(model_provider or "nano_banana").strip().lower()
    analyzed_en_desc = ""
    analyzed_vn_desc = ""

    # Bước 1: Nếu chọn ChatGPT (hoặc auto), gọi CLIProxy Vision (:8317) để trích xuất mô tả chuẩn xác từng món đồ trong ảnh
    if "chatgpt" in provider_norm or "gpt" in provider_norm or "auto" in provider_norm:
        try:
            import urllib.request
            import engine_settings_manager as _esm_fmc
            _cp_cfg = _esm_fmc.get_cliproxy_config()
            raw_b = open(source_image_path, "rb").read()
            b64_img = base64.b64encode(raw_b).decode("ascii")
            mime = "image/png" if source_image_path.lower().endswith(".png") else "image/jpeg"
            for _m_vis in _esm_fmc.resolve_cliproxy_chat_models(("gpt-5.6-luna", "gpt-6-luna", "gemini-3.5-flash-lite", "gpt-4o"))[:3]:
                try:
                    payload_chat = {
                        "model": _m_vis,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": (
                                            "Analyze this clothing/fashion image and return ONLY a JSON object with 3 keys: "
                                            "\"name_vn\" (short Vietnamese outfit title), "
                                            "\"desc_vn\" (detailed Vietnamese description of top, bottom/skirt/dress, color, fabric, and matching accessories), "
                                            "\"desc_en\" (detailed English description of the exact garments, cut, pleats, fabric texture, colors, and 4 matching accessories for an e-commerce flat-lay product sheet on pure white background)."
                                        ),
                                    },
                                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_img}"}},
                                ],
                            }
                        ],
                        "temperature": 0.2,
                    }
                    req = urllib.request.Request(
                        f"{_cp_cfg['url']}/v1/chat/completions",
                        data=json.dumps(payload_chat).encode("utf-8"),
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {_cp_cfg['api_key']}"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=25) as resp:
                        r_data = json.loads(resp.read().decode("utf-8", errors="replace"))
                        txt_c = (((r_data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
                        m_j = re.search(r"\{.*\}", txt_c, flags=re.DOTALL)
                        if m_j:
                            parsed_j = json.loads(m_j.group(0))
                            if not outfit_name and parsed_j.get("name_vn"):
                                outfit_name = parsed_j["name_vn"]
                            analyzed_vn_desc = parsed_j.get("desc_vn") or ""
                            analyzed_en_desc = parsed_j.get("desc_en") or ""
                            break
                except Exception:
                    continue
        except Exception as _chat_err:
            print(f"[ChatGPT Vision Info] {_chat_err}", flush=True)

    # Bước 2: Tạo Prompt tách nền trắng chỉ lấy sản phẩm (giống hệt 03_Product_Sheet_Quan_Xanh_2K.png)
    custom_vars = {}
    if analyzed_en_desc:
        custom_vars["outfit_desc"] = analyzed_en_desc
    prompts_map = get_standard_fashion_prompts(custom_vars)
    flatlay_prompt = prompts_map["deconstructed_outfit_flatlay_2k"]["rendered_prompt"]

    # Bước 3: Chạy Nano Banana 2K trên Google Flow để tạo bảng Product Sheet nền trắng tinh 2K
    gen_res = generate_fashion_2k_asset_on_flow(
        asset_type="deconstructed_outfit_flatlay_2k",
        prompt_str=flatlay_prompt,
        ref_image_paths=[source_image_path],
        output_filename=out_filename,
        project_id_slug=project_id_slug or "fashion_lookbook_chan_vay_6e19",
        profile_name=profile_name,
    )

    used_method = "Nano Banana 2.1 2K (Google Flow)" if "banana" in provider_norm else "ChatGPT Vision + Nano Banana 2K"
    if gen_res.get("ok") and gen_res.get("path") and os.path.exists(gen_res["path"]):
        if os.path.abspath(gen_res["path"]) != os.path.abspath(out_demo_path):
            shutil.copy2(gen_res["path"], out_demo_path)
        if os.path.abspath(gen_res["path"]) != os.path.abspath(out_proj_path):
            shutil.copy2(gen_res["path"], out_proj_path)
    else:
        # Fallback xử lý tách nền trắng Studio 2K ngay trên máy để tính năng luôn hoạt động 100%
        _create_clean_white_bg_product_sheet_local_2k(source_image_path, out_demo_path, outfit_name=outfit_name)
        shutil.copy2(out_demo_path, out_proj_path)
        used_method = f"Studio White-BG 2K Extractor ({gen_res.get('error', 'Local 2K')[:60]})"

    info_2k = ensure_image_is_2k(out_demo_path)
    outfit_id = f"outfit_custom_{clean_stem.lower()}"
    final_name = (outfit_name or "").strip() or f"Bộ Đồ Tách Nền Trắng 2K ({clean_stem})"
    new_outfit_entry = {
        "id": outfit_id,
        "filename": out_filename,
        "path": out_demo_path,
        "raw_product_path": source_image_path,
        "name": final_name,
        "short_desc": analyzed_vn_desc or f"trang phục thời trang tách nền trắng chuẩn 2K ({out_filename})",
        "en_desc": analyzed_en_desc or f"isolated fashion outfit on pure white background matching {out_filename}",
        "width": info_2k.get("width", 2048),
        "height": info_2k.get("height", 2559),
        "is_2k": True,
        "is_white_bg_sheet": True,
        "needs_deconstruct_sheet": False,
        "model_used": used_method,
    }

    # Lưu vào thư viện chung
    lib = _load_custom_fashion_library()
    existing_outfits = [o for o in (lib.get("outfits") or []) if o.get("filename") != out_filename]
    existing_outfits.insert(0, new_outfit_entry)
    lib["outfits"] = existing_outfits
    _save_custom_fashion_library(lib)

    # Nếu project hiện tại tồn tại, thêm luôn vào project
    manifest_path = os.path.join(proj_dir, "fashion_project.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            proj_outfits = [o for o in (manifest.get("outfits") or []) if o.get("filename") != out_filename]
            proj_entry = dict(new_outfit_entry)
            proj_entry["path"] = out_proj_path
            proj_outfits.append(proj_entry)
            manifest["outfits"] = proj_outfits
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return {
        "ok": True,
        "outfit": new_outfit_entry,
        "model_used": used_method,
        "library": list_fashion_characters_and_outfits_library(),
    }


def scan_and_sync_fashion_video_templates(force_rescan: bool = False) -> dict:
    """Quét và đồng bộ danh mục 30+ Video Template Thời Trang (`FVT_001`..`FVT_030`+)."""
    import fashion_video_template_catalog as fvtc
    return fvtc.scan_and_sync_fashion_video_templates(force_rescan=force_rescan)


def switch_fashion_project_generation_mode(project_id_slug: str, generation_mode: str = "chained_i2v") -> dict:
    """
    Chuyển đổi tức thì chế độ tạo video của dự án (`chained_i2v` <-> `video_ref`) và đồng bộ lại Prompt + Chips của tất cả phân cảnh.
    """
    proj_dir = os.path.join(FASHION_STUDIO_DIR, project_id_slug)
    manifest_path = os.path.join(proj_dir, "fashion_project.json")
    if not os.path.exists(manifest_path):
        return {"ok": False, "error": f"Không tìm thấy project: {project_id_slug}"}
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    gen_mode_norm = normalize_fashion_generation_mode(generation_mode or "chained_i2v")
    target_p_style = (
        "google_vids"
        if gen_mode_norm == "google_vids"
        else ("chained_i2v" if gen_mode_norm == "chained_i2v" else "timeline_pro")
    )
    manifest["generation_mode"] = gen_mode_norm
    manifest["prompt_style"] = target_p_style

    start_char_ref = {
        "asset_key": "base_char_2k",
        "filename": (manifest.get("base_char_2k") or {}).get("filename") or "02_Character_Sheet_Basic_Poses_2K.png",
        "path": (manifest.get("base_char_2k") or {}).get("path") or "",
        "is_continuity_generated": False,
    }
    char_sheet_ref_obj = manifest.get("char_sheet_2k")
    bpm_info = (manifest.get("split_plan") or {}).get("bpm_info")
    all_scenes = manifest.get("scenes") or []

    # Tự động quét lại nhịp beat 0.01s/0.1s & mốc biến hình đầu tiên từ Basic -> Outfit 1 chuẩn theo nhạc khi chuyển chế độ
    ref_vid_path = os.path.join(proj_dir, "reference_motion_source.mp4")
    if not os.path.exists(ref_vid_path):
        ref_vid_path = manifest.get("ref_video_path") or ""
    if os.path.exists(ref_vid_path) and all_scenes:
        try:
            import fashion_ai_video_analyzer as fava
            tot_d = float(((manifest.get("split_plan") or {}).get("total_duration")) or manifest.get("total_duration_sec") or (len(all_scenes) * 8.0))
            g_cuts = fava.detect_global_video_cuts_and_beats(ref_vid_path, tot_d)
            bpm_info = g_cuts
            manifest.setdefault("split_plan", {})["bpm_info"] = g_cuts
            outfits_list = manifest.get("outfits") or []
            if outfits_list:
                smart_tr_map = fava.map_outfits_to_scenes_smart(
                    num_scenes=len(all_scenes),
                    chunk_sec=int(round(float(all_scenes[0].get("duration_sec") or 8.0))),
                    total_dur=tot_d,
                    outfits_list=outfits_list,
                    global_cuts_info=g_cuts,
                    clips_dir=os.path.join(proj_dir, "ref_clips"),
                    custom_scene_cuts=None,
                    generation_mode="chained_i2v" if gen_mode_norm in ("chained_i2v", "google_vids") else "video_ref",
                )
                for idx_c, sc_c in enumerate(all_scenes):
                    if idx_c < len(smart_tr_map) and smart_tr_map[idx_c]:
                        sc_c["transitions"] = smart_tr_map[idx_c]
        except Exception as _re_err:
            print(f"[SwitchMode Beat Align Info] {_re_err}", flush=True)

    for idx_s, sc in enumerate(all_scenes):
        sc_num = int(sc.get("scene_index") or (idx_s + 1))
        if sc_num >= 2:
            prev_sc = all_scenes[idx_s - 1]
            prev_sc_id = prev_sc.get("id") or f"s{sc_num - 1}"
            lf_key = f"scene_{prev_sc_id}_last_frame_2k"
            lf_fn = f"{lf_key}.png"
            lf_path = os.path.join(proj_dir, "assets_2k", lf_fn)
            prev_vid_p = prev_sc.get("output_video_path") or os.path.join(proj_dir, prev_sc.get("output_video_file") or f"fashion_scene_{prev_sc_id}_1080p.mp4")
            if os.path.exists(prev_vid_p) and not os.path.exists(lf_path):
                extract_scene_last_frame_2k(prev_vid_p, lf_path)
            sc["prev_scene_last_frame_ref"] = {
                "asset_key": lf_key,
                "filename": lf_fn,
                "path": lf_path,
            }
            if not sc.get("prev_scene_last_outfit") and prev_sc.get("transitions"):
                sc["prev_scene_last_outfit"] = prev_sc["transitions"][-1].get("outfit")

        sc["ref_video_path"] = (manifest.get("reference_video") or {}).get("filename") or ref_vid_path or project_id_slug
        sc["template_meta"] = {
            "code": manifest.get("source_template_code") or project_id_slug,
            "slug": (manifest.get("reference_video") or {}).get("filename") or "",
            "action_description": manifest.get("source_template_action") or sc.get("ai_motion_summary_vn") or "",
        }

        p_vids = build_scene_timeline_prompt(sc, start_char_ref, char_sheet_ref_obj, prompt_style="google_vids", bpm_info=bpm_info)
        p_i2v = build_scene_timeline_prompt(sc, start_char_ref, char_sheet_ref_obj, prompt_style="chained_i2v", bpm_info=bpm_info)
        p_vref = build_scene_timeline_prompt(sc, start_char_ref, char_sheet_ref_obj, prompt_style="timeline_pro", bpm_info=bpm_info)
        sc["prompt_google_vids"] = p_vids["display_prompt"]
        sc["segments_google_vids"] = p_vids["segments_spec"]
        sc["prompt_chained_i2v"] = p_i2v["display_prompt"]
        sc["segments_chained_i2v"] = p_i2v["segments_spec"]
        sc["prompt_timeline_pro"] = p_vref["display_prompt"]
        sc["segments_timeline_pro"] = p_vref["segments_spec"]
        sc["prompt_concise_flow"] = p_vref["display_prompt"]
        sc["segments_concise_flow"] = p_vref["segments_spec"]
        sc["generation_mode"] = gen_mode_norm
        sc["active_prompt_style"] = target_p_style
        sc["user_edited_prompt"] = False
        if gen_mode_norm == "google_vids":
            sc["prompt"] = p_vids["display_prompt"]
            sc["segments_spec"] = p_vids["segments_spec"]
        elif gen_mode_norm == "chained_i2v":
            sc["prompt"] = p_i2v["display_prompt"]
            sc["segments_spec"] = p_i2v["segments_spec"]
        else:
            sc["prompt"] = p_vref["display_prompt"]
            sc["segments_spec"] = p_vref["segments_spec"]

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return {"ok": True, "generation_mode": gen_mode_norm, "project": manifest}


def apply_fashion_video_template_to_project(
    template_code: str,
    base_char_path: str = None,
    char_sheet_path: str = None,
    outfit_items: list = None,
    project_id_slug: str = None,
    use_adult_safe_s1: bool = False,
    generation_mode: str = "chained_i2v",
) -> dict:
    """
    Áp dụng 1 Template Video Thời Trang (`FVT_001` .. `FVT_030`+) vào dự án:
      1. Lấy thông tin đã phân tích sẵn của Template (`video_path`, `title`, `action_description`, `background_setting`, `scenes_blueprint`).
      2. Kết hợp với Nhân Vật đang chọn (mặc định là `02_Character_Sheet_Basic_Poses_2K.png` + `07_Nhan_Vat_Basic_Phong_Ngu_2K.png`)
         và danh sách Sản Phẩm / Bộ Đồ 2K đang chọn (mặc định là 5 bộ đồ nền trắng chuẩn 2K của người dùng).
      3. Hỗ trợ tuỳ chọn `generation_mode`: `"chained_i2v"` (Hoàn toàn từ Img2Video + Timeline 0.1s chuẩn nhạc) hoặc `"video_ref"` (Motion Control Video Ref),
         đều tự động dùng Frame cuối của Phân cảnh 1 (`scene_s1_last_frame_2k.png`) để nối tiếp Phân cảnh 2!
    """
    import fashion_video_template_catalog as fvtc

    tpl = fvtc.get_fashion_video_template_by_code(template_code)
    if not tpl or not tpl.get("video_path") or not os.path.exists(tpl["video_path"]):
        return {"ok": False, "error": f"Không tìm thấy Template Video với mã: {template_code}"}

    code_norm = tpl["code"]
    if not project_id_slug:
        project_id_slug = f"fashion_tpl_{code_norm.lower()}"

    gen_mode_norm = normalize_fashion_generation_mode(generation_mode or "chained_i2v")

    # Nếu ở chế độ `video_ref`, lấy mốc cắt của template; nếu ở chế độ `chained_i2v` / `google_vids`, để bộ dò 0.01s/0.1s Beat & Visual Cut phân tích chuẩn xác theo nhạc!
    custom_cuts = {}
    if gen_mode_norm == "video_ref":
        for sc_bp in tpl.get("scenes_blueprint") or []:
            sc_id = sc_bp.get("id")
            if sc_id and sc_bp.get("transition_timestamps"):
                custom_cuts[sc_id] = sc_bp["transition_timestamps"]

    manifest = create_or_update_fashion_motion_project(
        project_id_slug=project_id_slug,
        title=f"[{code_norm}] {tpl['title']}",
        base_char_path=base_char_path,
        char_sheet_path=char_sheet_path,
        ref_video_path=tpl["video_path"],
        outfit_items=outfit_items,
        preferred_chunk_sec="8",
        prompt_style="google_vids" if gen_mode_norm == "google_vids" else ("chained_i2v" if gen_mode_norm == "chained_i2v" else "timeline_pro"),
        generation_mode=gen_mode_norm,
        custom_scene_cuts=custom_cuts if custom_cuts else None,
        ai_provider="template_preanalyzed",
        auto_render_preview_final=False,
    )
    if not manifest.get("ok"):
        return manifest

    manifest["source_template_code"] = code_norm
    manifest["source_template_title"] = tpl["title"]
    manifest["source_template_category"] = tpl.get("category_label") or ""
    manifest["source_template_background"] = tpl.get("background_setting") or ""
    manifest["source_template_action"] = tpl.get("action_description") or ""

    # Ghi đè tóm tắt AI cho từng phân cảnh bằng đúng nội dung Hành Động + Bối Cảnh đã phân tích của Template và cập nhật lại Prompt I2V / Video Ref khớp 100% Template
    bp_map = {b["id"]: b for b in (tpl.get("scenes_blueprint") or []) if b.get("id")}
    start_char_ref = {
        "asset_key": "base_char_2k",
        "filename": (manifest.get("base_char_2k") or {}).get("filename") or "02_Character_Sheet_Basic_Poses_2K.png",
        "path": (manifest.get("base_char_2k") or {}).get("path") or "",
        "is_continuity_generated": False,
    }
    char_sheet_ref_obj = manifest.get("char_sheet_2k")
    bpm_info = (manifest.get("split_plan") or {}).get("bpm_info")
    for sc in manifest.get("scenes") or []:
        sc_id = sc.get("id")
        bp = bp_map.get(sc_id) or {}
        # Bind selected outfits to template beats; changing assets must not re-detect its timing.
        template_times = bp.get('transition_timestamps_sec') or []
        if len(template_times) >= len(sc.get('transitions') or []):
            for tr, raw_time in zip(sc.get('transitions') or [], template_times):
                seconds = float(str(raw_time).rstrip('sS'))
                tr['timestamp_sec'] = seconds
                tr['timestamp_colon'] = format_colon_timestamp(seconds)
                tr['global_timestamp_sec'] = round(float(sc.get('start_sec') or 0) + seconds, 2)
        if use_adult_safe_s1 and sc_id == "s1" and sc.get("adult_safe_clip_path") and os.path.exists(sc["adult_safe_clip_path"]):
            sc["ref_clip_path"] = sc["adult_safe_clip_path"]
            sc["ref_clip_filename"] = os.path.basename(sc["adult_safe_clip_path"])
        sc["ai_motion_summary_vn"] = (
            f"[{code_norm} • {tpl.get('category_label', '')}] "
            f"Bối cảnh: {tpl.get('background_setting', '')}. "
            f"Hành động: {bp.get('action_detail') or tpl.get('action_description', '')}"
        )
        sc["ref_video_path"] = tpl.get("video_path") or (manifest.get("reference_video") or {}).get("filename") or code_norm
        if bp.get("i2v_choreography"):
            sc["i2v_choreography_precomputed"] = bp["i2v_choreography"]
        sc["template_meta"] = {
            "code": code_norm,
            "slug": tpl.get("slug") or tpl.get("filename") or "",
            "category": tpl.get("category") or "",
            "action_description": tpl.get("action_description") or sc["ai_motion_summary_vn"],
        }
        p_vids = build_scene_timeline_prompt(sc, start_char_ref, char_sheet_ref_obj, prompt_style="google_vids", bpm_info=bpm_info)
        p_i2v = build_scene_timeline_prompt(sc, start_char_ref, char_sheet_ref_obj, prompt_style="chained_i2v", bpm_info=bpm_info)
        p_vref = build_scene_timeline_prompt(sc, start_char_ref, char_sheet_ref_obj, prompt_style="timeline_pro", bpm_info=bpm_info)
        sc["prompt_google_vids"] = p_vids["display_prompt"]
        sc["segments_google_vids"] = p_vids["segments_spec"]
        sc["prompt_chained_i2v"] = p_i2v["display_prompt"]
        sc["segments_chained_i2v"] = p_i2v["segments_spec"]
        sc["prompt_timeline_pro"] = p_vref["display_prompt"]
        sc["segments_timeline_pro"] = p_vref["segments_spec"]
        sc["prompt_concise_flow"] = p_vref["display_prompt"]
        sc["segments_concise_flow"] = p_vref["segments_spec"]
        if gen_mode_norm == "google_vids":
            sc["prompt"] = p_vids["display_prompt"]
            sc["segments_spec"] = p_vids["segments_spec"]
        elif gen_mode_norm == "chained_i2v":
            sc["prompt"] = p_i2v["display_prompt"]
            sc["segments_spec"] = p_i2v["segments_spec"]
        else:
            sc["prompt"] = p_vref["display_prompt"]
            sc["segments_spec"] = p_vref["segments_spec"]

    proj_dir = manifest["project_dir"]
    manifest_path = os.path.join(proj_dir, "fashion_project.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return manifest


if __name__ == "__main__":
    default_vid = os.environ.get("FASHION_DEMO_VIDEO", "").strip() or (sys.argv[1] if len(sys.argv) > 1 else "")
    if default_vid and os.path.exists(default_vid) and os.path.exists(DEMO_ASSETS_DIR):
        res = create_or_update_fashion_motion_project(
            project_id_slug="fashion_motion_demo_7anh_2k",
            title="Lookbook Thời Trang Thay Đồ Theo Nhạc (Trọn Bộ 7 Ảnh 2K — 2 Phân Cảnh × 8s)",
            ref_video_path=default_vid,
            preferred_chunk_sec="auto",
            prompt_style="concise_flow",
        )
        print(json.dumps(res, ensure_ascii=False, indent=2))


def prepare_simple_fashion_inputs(project_id, manifest, profile_name=''):
    """Create a single opening shot and faithful garment-only refs; keep cached successes."""
    import hashlib
    folder = os.path.join(FASHION_STUDIO_DIR, project_id)
    cache_path = os.path.join(folder, 'input_preparation.json')
    cache_lock = threading.Lock()
    try:
        with open(cache_path,encoding='utf-8') as f: cache=json.load(f)
    except (OSError,ValueError): cache={}
    def generate(role, source, prompt, assigned_profile=None):
        if not source or not os.path.isfile(source):
            raise ValueError('Không tìm thấy ảnh '+role)
        with open(source,'rb') as source_file:
            digest=hashlib.sha256(source_file.read()).hexdigest()
        key=role+'_'+digest
        with cache_lock:
            saved=cache.get(key,{})
            if saved.get('path') and os.path.isfile(saved['path']): return saved['path']
            manifest['status_message']='Đang chuẩn bị ảnh '+role+' từ ảnh bạn đã thêm...'
            with open(os.path.join(folder,'fashion_project.json'),'w',encoding='utf-8') as f:
                json.dump(manifest,f,ensure_ascii=False,indent=2)
        use_prof = assigned_profile if assigned_profile is not None else profile_name
        result=generate_fashion_2k_asset_on_flow(
            asset_type='base_char_bedroom_2k' if role=='opening' else 'deconstructed_outfit_flatlay_2k',
            prompt_str=prompt,ref_image_paths=[source],
            output_filename='prepared_'+role+'_'+digest[:12]+'.png',
            project_id_slug=project_id,profile_name=use_prof)
        if not result.get('ok') or not os.path.isfile(result.get('path','')):
            raise ValueError(result.get('error') or 'Không tạo được ảnh '+role)
        with cache_lock:
            cache[key]={'path':result['path'],'source':source,'source_hash':digest,'prompt':prompt}
            with open(cache_path,'w',encoding='utf-8') as f:json.dump(cache,f,ensure_ascii=False,indent=2)
        return result['path']
    try:
        source=manifest['base_char_2k']['path']
        opening=generate('opening',source,
            'Create ONE photorealistic vertical 9:16 full-body opening frame for a fashion video. '
            'The supplied image defines the same adult character face, hair, skin tone and body identity only. '
            'If it is a multi-view character sheet, reconstruct exactly ONE person, never show panels or text. '
            'Neutral simple basic outfit, full head and both feet visible, relaxed standing pose, natural hands. '
            'Use a tidy fashion room with soft daylight, fixed eye-level tripod camera. Setting: '
            +str(manifest.get('source_template_background') or 'a clean bright dressing room')+
            '. No product held in hands, no logos, labels, text, extra people or collage.')
        raw_outfits = list(manifest.get('outfits') or [])
        if not raw_outfits: raise ValueError('Chưa chọn sản phẩm.')
        outfit_prompt = (
            'Create one clean garment-only fashion reference on a seamless white background. '
            'Extract ONLY the exact visible clothing from the supplied product photo. Preserve its actual '
            'color, material, print, buttons, cut and hem. Remove the original wearer, face, hands, hair, '
            'room and text. No invented accessories, jewelry, bags, shoes, outfit colors or extra garments. '
            'If a feature is not visible, do not invent a distinctive design. One coherent flatlay, '
            'soft contact shadows, crisp realistic fabric, no labels or watermark.'
        )
        outfits=[]
        if len(raw_outfits) == 1:
            item = raw_outfits[0]
            raw = item.get('path') or ''
            ref = generate('outfit1', raw, outfit_prompt)
            outfits.append(dict(item, path=ref, filename=os.path.basename(ref)))
        else:
            cand_accs = _get_ordered_flow_account_candidates(profile_name, rotate_round_robin=True)
            def _prep_one_outfit(idx_and_item):
                idx, it = idx_and_item
                raw_p = it.get('path') or ''
                acc_p = cand_accs[(idx - 1) % len(cand_accs)] if cand_accs else profile_name
                ref_p = generate('outfit'+str(idx), raw_p, outfit_prompt, assigned_profile=acc_p)
                return idx, dict(it, path=ref_p, filename=os.path.basename(ref_p))
            max_w = min(len(raw_outfits), max(1, len(cand_accs)), 3)
            indexed_results = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as _opool:
                futs = {_opool.submit(_prep_one_outfit, (i, it)): i for i, it in enumerate(raw_outfits, 1)}
                for fut in concurrent.futures.as_completed(futs):
                    r_idx, r_item = fut.result()
                    indexed_results[r_idx] = r_item
            for i in range(1, len(raw_outfits) + 1):
                outfits.append(indexed_results[i])
        result=apply_fashion_video_template_to_project(
            template_code=manifest['source_template_code'],base_char_path=opening,char_sheet_path=opening,
            outfit_items=outfits,project_id_slug=project_id,
            generation_mode=manifest.get('generation_mode') or 'chained_i2v')
        if not result.get('ok'): return result
        result.update(input_flow='simple',input_assets_prepared=True,
            original_character_path=source,original_outfit_paths=[o.get('path') for o in manifest.get('outfits',[])],
            max_scene_attempts=manifest.get('max_scene_attempts',1),status='running_flow')
        with open(os.path.join(folder,'fashion_project.json'),'w',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
        return {'ok':True,'project':result}
    except Exception as error:
        return {'ok':False,'error':str(error)}
