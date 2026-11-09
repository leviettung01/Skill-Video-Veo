# -*- coding: utf-8 -*-
"""
DEEP FRAME-BY-FRAME & AUDIO BEAT RE-ANALYZER FOR ALL 252+ TEMPLATE VIDEOS (FVT_001 -> FVT_252)
==============================================================================================
Quét thực tế từng video gốc (.mp4) ở tốc độ 10 FPS (0.10s) + Âm thanh 8000Hz (lưới 0.01s) để:
  1. Đo chính xác BPM, khoảng cách nhịp beat (`beat_interval_sec`), danh sách `audio_beats` (0.01s)
     và các điểm cắt đổi trang phục thực tế (`visual_cuts` chuẩn 0.10s, khớp nhịp nhạc).
  2. Đo chuyển động giải phẫu học 8 vùng cơ thể (tay trái cao, tay phải cao, 2 tay ngang vai,
     dang rộng 2 cánh tay, đấm/chỉ tay về ống kính, kéo gấu áo/chạm eo, xoay lưng 360° / xoay nghiêng 45°,
     bước tiến catwalk / bước lùi nửa bước / nhún nhảy tại chỗ) cho TỪNG CỬA SỔ THỜI GIAN của Cảnh 1 & Cảnh 2.
  3. Đo chính xác Tư thế kết Cảnh 1 tại 7.50s–8.00s để khóa khớp 100% với Tư thế mở đầu Cảnh 2 tại 0.00s.
  4. Tạo bộ Prompt I2V (`prompt_chained_i2v`) và Prompt Motion Control (`prompt_template`) RIÊNG BIỆT,
     ĐỘC NHẤT (252/252 video không trùng lặp) và khớp thật với từng video gốc!
"""

import os
import re
import sys
import json
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.dirname(SCRIPT_DIR)
WS_DIR = os.path.dirname(PIPELINE_DIR)
for _p in (SCRIPT_DIR, WS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fashion_video_template_catalog as fvtc

CATALOG_JSON_PATH = fvtc.CATALOG_JSON_PATH


def _extract_10fps_and_audio(video_path: str, max_dur: float = 16.5):
    """
    Trích xuất đồng thời bằng FFmpeg pipe trong bộ nhớ RAM:
      - Khung hình 10 FPS (mỗi 0.10s), kích thước 60x106 RGB24
      - Âm thanh Mono 8000 Hz PCM 16-bit
    """
    cmd_v = [
        "ffmpeg", "-v", "error", "-t", f"{max_dur:.2f}",
        "-i", video_path,
        "-vf", "fps=10,scale=60:106",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]
    cmd_a = [
        "ffmpeg", "-v", "error", "-t", f"{max_dur:.2f}",
        "-i", video_path,
        "-vn", "-ac", "1", "-ar", "8000",
        "-f", "s16le", "-",
    ]
    pv = subprocess.run(cmd_v, capture_output=True, timeout=30)
    pa = subprocess.run(cmd_a, capture_output=True, timeout=20)

    fb = 60 * 106 * 3
    n_fr = len(pv.stdout) // fb
    frames = (
        np.frombuffer(pv.stdout[: n_fr * fb], dtype=np.uint8).reshape((n_fr, 106, 60, 3)).astype(np.float32)
        if n_fr > 0
        else np.zeros((0, 106, 60, 3), dtype=np.float32)
    )
    audio = np.frombuffer(pa.stdout, dtype=np.int16).astype(np.float32) if len(pa.stdout) >= 2 else np.zeros((0,), dtype=np.float32)
    return frames, audio


def _analyze_audio_100hz(audio: np.ndarray, dur: float) -> dict:
    """Phân tích tín hiệu âm thanh ở độ phân giải 100Hz (0.01s) để tìm BPM và các đỉnh nhịp beat."""
    if len(audio) < 800:
        return {"bpm": 140.0, "beat_interval_sec": 0.43, "audio_beats": [], "all_onsets": []}

    win = 80  # 8000Hz / 80 = 100Hz (mỗi mẫu 0.01s)
    n_bins = len(audio) // win
    trimmed = audio[: n_bins * win].reshape((n_bins, win))
    rms = np.sqrt(np.mean(trimmed ** 2, axis=1))
    flux = np.zeros_like(rms)
    flux[1:] = np.maximum(0.0, rms[1:] - rms[:-1])

    k_fast = np.ones(3, dtype=np.float32) / 3.0
    flux_s = np.convolve(flux, k_fast, mode="same")
    k_loc = np.ones(45, dtype=np.float32) / 45.0
    loc_mean = np.convolve(flux_s, k_loc, mode="same")
    med_f = float(np.median(flux_s)) if len(flux_s) else 1.0

    raw_peaks = []
    for i in range(8, len(flux_s) - 8):
        t_s = round(i * 0.01, 2)
        if t_s < 0.35 or t_s > (dur - 0.30):
            continue
        v = float(flux_s[i])
        if v >= float(np.max(flux_s[i - 6 : i + 7])) and v > max(med_f * 1.45, float(loc_mean[i]) * 1.22 + 12.0):
            raw_peaks.append((t_s, v))

    onsets = []
    for t_s, v in raw_peaks:
        if not onsets or (t_s - onsets[-1][0]) >= 0.22:
            onsets.append([t_s, v])
        elif v > onsets[-1][1]:
            onsets[-1] = [t_s, v]

    intervals = []
    for i in range(len(onsets) - 1):
        dt = onsets[i + 1][0] - onsets[i][0]
        if 0.34 <= dt <= 0.68:
            intervals.append(dt)
        elif 0.68 < dt <= 1.32:
            intervals.append(dt * 0.5)

    beat_int = round(float(np.median(intervals)), 2) if intervals else 0.43
    beat_int = max(0.36, min(0.58, beat_int))
    bpm = round(60.0 / beat_int, 1)

    strong_beats = []
    for t_s, v in onsets:
        if not strong_beats or (t_s - strong_beats[-1]) >= 0.38:
            strong_beats.append(round(t_s, 2))

    return {
        "bpm": bpm,
        "beat_interval_sec": beat_int,
        "audio_beats": strong_beats,
        "all_onsets": [round(x[0], 2) for x in onsets],
    }


def _detect_visual_cuts_10fps(frames: np.ndarray, dur: float, all_onsets: list) -> list:
    """
    Phát hiện chính xác các điểm cắt đổi đồ (`visual_cuts`) ở độ phân giải 0.10s (10 FPS),
    kết hợp sự thay đổi đột ngột màu sắc vùng trang phục (`garment_roi`) và độ lệch khung hình (`body_roi`),
    sau đó căn khớp (±0.06s) vào đỉnh nhịp nhạc 0.01s gần nhất.
    """
    n_fr = len(frames)
    if n_fr < 12:
        return [3.40, 6.85, 10.30, 12.80] if dur >= 11.5 else [3.40, 6.85]

    # Vùng thân trang phục (y: 26..80, x: 14..46) & vùng toàn thân (y: 12..94, x: 10..50)
    garment = frames[:, 26:80, 14:46, :]
    body = frames[:, 12:94, 10:50, :]

    # Độ lệch frame-to-frame (0.10s) + độ lệch màu trung bình trước/sau 0.20s (nhận diện đổi màu quần áo cực nhạy)
    f_diff = np.mean(np.abs(body[1:] - body[:-1]), axis=(1, 2, 3))
    c_jump = np.zeros_like(f_diff)
    for i in range(2, n_fr - 2):
        pre_rgb = np.mean(garment[max(0, i - 2) : i], axis=(0, 1, 2))
        post_rgb = np.mean(garment[i : min(n_fr, i + 2)], axis=(0, 1, 2))
        c_jump[i - 1] = float(np.linalg.norm(post_rgb - pre_rgb))

    score_curve = f_diff * 0.65 + c_jump * 0.55
    med_s = float(np.median(score_curve)) if len(score_curve) else 8.0
    thresh = max(11.5, med_s * 1.85)

    cands = []
    for i in range(6, len(score_curve) - 6):
        t_c = round((i + 1) * 0.10, 2)
        if t_c < 0.80 or t_c > (dur - 0.70):
            continue
        sv = float(score_curve[i])
        if sv >= float(np.max(score_curve[i - 2 : i + 3])) and sv >= thresh:
            cands.append((t_c, sv))

    # Ưu tiên lấy các đỉnh cao nhất cách nhau >= 1.35s
    cands_sorted = sorted(cands, key=lambda x: x[1], reverse=True)
    picked = []
    for t_c, sv in cands_sorted:
        if all(abs(t_c - p[0]) >= 1.35 for p in picked):
            # Snap nhẹ vào nhịp beat âm thanh gần nhất (trong vòng ±0.06s) để có độ chính xác 0.01s
            snapped = t_c
            if all_onsets:
                nb = min(all_onsets, key=lambda b: abs(b - t_c))
                if abs(nb - t_c) <= 0.06:
                    snapped = round(nb, 2)
            picked.append((snapped, sv))
        if len(picked) >= 8:
            break

    picked.sort(key=lambda x: x[0])
    return [p[0] for p in picked]


def _measure_subwindow_signature(frames: np.ndarray, t_start: float, t_end: float) -> dict:
    """
    Đo chi tiết đặc trưng chuyển động & tư thế trong khoảng `[t_start, t_end]` (giây tuyệt đối trên video)
    trên lưới 10 FPS (`60x106` RGB):
      - `dom_zone`: vùng cơ thể hoạt động mạnh nhất (`both_hands_high`, `left_hand_high`, `right_hand_high`,
        `wide_both_arms`, `wide_left_arm`, `wide_right_arm`, `center_lens_reach`, `hem_waist_pull`, `body_turn_spin`)
      - `peak_local_sec`: giây tương đối (tính từ đầu phân cảnh 8s) nơi động tác đạt đỉnh
      - `is_back_turn`: phát hiện xoay lưng 180°/360° (vùng mặt chuyển sang màu tóc sẫm + bề ngang vai co/giãn)
      - `turn_deg`: góc xoay người ước lượng (15°, 30°, 45°, 180°/360°)
      - `step_mode`: `step_forward`, `half_step_back`, `playful_bounce`, hoặc `smooth_hip_sway`
      - `span_px`: độ mở ngang của hai tay/thân người
      - `cx_shift`: biên độ dịch chuyển trọng tâm ngang
    """
    i0 = max(0, int(round(t_start * 10.0)))
    i1 = min(len(frames) - 1, int(round(t_end * 10.0)))
    if i1 <= i0 or len(frames) < 4:
        return {
            "dom_zone": "left_hand_high",
            "peak_local_sec": round(((t_start + t_end) * 0.5) % 8.0, 2),
            "is_back_turn": False,
            "turn_deg": 15,
            "step_mode": "smooth_hip_sway",
            "span_px": 28.0,
            "cx_shift": 3.5,
            "u_l": 4.0,
            "u_r": 4.0,
            "w_l": 4.0,
            "w_r": 4.0,
            "lens": 4.0,
            "hem": 4.0,
        }

    sub = frames[i0 : i1 + 1]
    diffs = np.abs(sub[1:] - sub[:-1]) if len(sub) >= 2 else np.zeros((1, 106, 60, 3), dtype=np.float32)
    gray_d = np.mean(diffs, axis=3)  # (N, 106, 60)

    # 6 vùng giải phẫu trên khung 60x106:
    # Lưu ý: bên trái ảnh (x: 4..28) là tay phải của người mẫu; bên phải ảnh (x: 32..56) là tay trái của người mẫu
    u_img_left = np.mean(gray_d[:, 14:44, 4:28], axis=(1, 2))    # model's right hand near shoulder/cheek
    u_img_right = np.mean(gray_d[:, 14:44, 32:56], axis=(1, 2))  # model's left hand near shoulder/cheek
    w_img_left = np.mean(gray_d[:, 32:70, 0:18], axis=(1, 2))    # model's right arm wide out
    w_img_right = np.mean(gray_d[:, 32:70, 42:60], axis=(1, 2))  # model's left arm wide out
    c_lens = np.mean(gray_d[:, 28:64, 18:42], axis=(1, 2))       # center chest / camera lens reach
    l_hem = np.mean(gray_d[:, 56:84, 14:46], axis=(1, 2))        # waist / bottom top hem / hip

    total_frame_motion = np.mean(gray_d[:, 14:90, 6:54], axis=(1, 2))
    peak_idx = int(np.argmax(total_frame_motion))
    peak_abs_sec = round((i0 + peak_idx + 1) * 0.10, 2)
    scene_base = 8.0 if t_start >= 7.95 else 0.0
    peak_local_sec = round(max(0.10, min(7.90, peak_abs_sec - scene_base)), 2)

    u_r_model = float(np.mean(u_img_left))
    u_l_model = float(np.mean(u_img_right))
    w_r_model = float(np.mean(w_img_left))
    w_l_model = float(np.mean(w_img_right))
    lens_v = float(np.max(c_lens))
    hem_v = float(np.max(l_hem))

    # Đo bề ngang hoạt động & dịch chuyển trọng tâm ngang/dọc
    spans = []
    cxs = []
    cys = []
    for gd in gray_d:
        ys, xs = np.where(gd[20:92, :] > 8.5)
        if len(xs) >= 8:
            spans.append(float(np.percentile(xs, 90) - np.percentile(xs, 10)))
            cxs.append(float(np.mean(xs)))
            cys.append(float(np.mean(ys)))
    span_px = float(np.max(spans)) if spans else 26.0
    cx_shift = (float(np.max(cxs)) - float(np.min(cxs))) if len(cxs) >= 2 else 2.5
    cy_shift = (float(np.max(cys)) - float(np.min(cys))) if len(cys) >= 2 else 2.0

    # Phát hiện xoay lưng 180°/360°: độ sáng vùng mặt (y: 10..26, x: 22..38) giảm sâu so với trung bình do tóc che mặt khi quay lưng
    face_luma = np.mean(sub[:, 10:26, 22:38, :], axis=(1, 2, 3))
    max_face = float(np.max(face_luma)) if len(face_luma) else 140.0
    min_face = float(np.min(face_luma)) if len(face_luma) else 140.0
    is_back_turn = (max_face - min_face) > 26.0 and cx_shift > 5.5

    if is_back_turn:
        turn_deg = 360
    elif cx_shift > 9.5:
        turn_deg = 45
    elif cx_shift > 5.8:
        turn_deg = 30
    else:
        turn_deg = 15

    # Phát hiện bước tiến / bước lùi / nhún nhảy
    if cy_shift > 7.5 and span_px > 32.0:
        step_mode = "step_forward"
    elif cy_shift > 6.2 and span_px <= 32.0:
        step_mode = "half_step_back"
    elif cy_shift > 4.2:
        step_mode = "playful_bounce"
    else:
        step_mode = "smooth_hip_sway"

    scores = {
        "both_hands_high": (u_l_model + u_r_model) * 0.72 if (u_l_model > 5.5 and u_r_model > 5.5) else 0.0,
        "left_hand_high": u_l_model * 1.22,
        "right_hand_high": u_r_model * 1.22,
        "wide_both_arms": (w_l_model + w_r_model) * 0.85 + (4.0 if span_px > 36.0 else 0.0),
        "wide_left_arm": w_l_model * 1.18,
        "wide_right_arm": w_r_model * 1.18,
        "center_lens_reach": lens_v * 0.92,
        "hem_waist_pull": hem_v * 0.90,
        "body_turn_spin": cx_shift * 1.35 + (12.0 if is_back_turn else 0.0),
    }
    dom_zone = max(scores.items(), key=lambda kv: kv[1])[0]

    return {
        "dom_zone": dom_zone,
        "peak_local_sec": peak_local_sec,
        "is_back_turn": bool(is_back_turn),
        "turn_deg": int(turn_deg),
        "step_mode": step_mode,
        "span_px": round(span_px, 1),
        "cx_shift": round(cx_shift, 1),
        "u_l": round(u_l_model, 2),
        "u_r": round(u_r_model, 2),
        "w_l": round(w_l_model, 2),
        "w_r": round(w_r_model, 2),
        "lens": round(lens_v, 2),
        "hem": round(hem_v, 2),
    }

def _render_window_action_en(win: dict, role: str, t_a: float, t_b: float, look_num: int = 1) -> str:
    """
    Chuyển số liệu đo 10 FPS thực tế của cửa sổ `[t_a, t_b]` thành câu mô tả hành động tiếng Anh
    chuẩn xác tới từng 0.1s (có kèm mốc giây đỉnh `peak_local_sec` và biên độ chuyển động thực tế của video đó).
    """
    dom = win.get("dom_zone") or "left_hand_high"
    pk = float(win.get("peak_local_sec") or round((t_a + t_b) * 0.5, 2))
    pk = max(round(t_a + 0.08, 2), min(round(t_b - 0.08, 2), pk))
    turn_deg = int(win.get("turn_deg") or 15)
    is_back = bool(win.get("is_back_turn"))
    step_m = win.get("step_mode") or "smooth_hip_sway"
    span_px = float(win.get("span_px") or 28.0)

    step_phrase_map = {
        "step_forward": f"takes a light rhythmic step forward toward the lens ({pk:.2f}s)",
        "half_step_back": f"takes a graceful half-step back to frame her full head-to-toe silhouette ({pk:.2f}s)",
        "playful_bounce": f"bounces lightly on soft knees to the beat ({pk:.2f}s)",
        "smooth_hip_sway": f"transfers her weight smoothly with a {turn_deg}-degree hip-and-shoulder sway ({pk:.2f}s)",
    }
    step_phrase = step_phrase_map.get(step_m, step_phrase_map["smooth_hip_sway"])

    if role == "open_s1":
        if dom == "both_hands_high":
            return (
                "Begin in the exact basic outfit from the reference room image.\n"
                f"She looks into the lens with a bright smile, raises both open palms near shoulder height in a cheerful greeting wave at {pk:.2f}s, "
                f"and {step_phrase} as her hands sweep softly toward her upper torso."
            )
        if dom == "right_hand_high":
            return (
                "Begin in the exact basic outfit from the reference room image.\n"
                f"She smiles warmly at the camera, lifts her right hand near her right shoulder and cheek in a playful wave at {pk:.2f}s, "
                f"and {step_phrase} while her left hand relaxes near her waist."
            )
        if dom in ("wide_both_arms", "wide_left_arm", "wide_right_arm"):
            return (
                "Begin in the exact basic outfit from the reference room image.\n"
                f"She faces the lens with a relaxed smile, {step_phrase}, "
                f"and opens both forearms outward at waist level (span accent at {pk:.2f}s) with loose, fluid wrists."
            )
        if dom == "center_lens_reach":
            return (
                "Begin in the exact basic outfit from the reference room image.\n"
                f"She looks directly into the camera with a confident smile, makes a playful forward finger-point gesture toward the lens at {pk:.2f}s, "
                f"and {step_phrase}."
            )
        if dom == "hem_waist_pull":
            return (
                "Begin in the exact basic outfit from the reference room image.\n"
                f"She stands poised in the center of the room, places her fingertips lightly at her waist/top hem at {pk:.2f}s, "
                f"and {step_phrase} with a warm lookbook smile."
            )
        return (
            "Begin in the exact basic outfit from the reference room image.\n"
            f"She looks into the lens with a soft smile, {step_phrase}, "
            f"raises her left forearm with palm facing upward at {pk:.2f}s, then softly sweeps that hand inward across her upper torso."
        )

    if role in ("build1", "build2", "build3", "build4"):
        if is_back:
            return (
                f"She executes a smooth, full 360-degree turn in place peaking at {pk:.2f}s to showcase both the front and rear fit of the outfit, "
                "keeping her feet cleanly planted and returning her gaze to the camera lens with a radiant smile."
            )
        if dom == "body_turn_spin" or turn_deg >= 30:
            return (
                f"She angles her torso {turn_deg} degrees at {pk:.2f}s to showcase the side profile and drape of the outfit while keeping her gaze on the lens, "
                f"then {step_phrase} as she returns frontally."
            )
        if dom == "both_hands_high":
            return (
                f"She brings both hands up symmetrically near shoulder-collarbone height at {pk:.2f}s in a lively musical accent, "
                f"then {step_phrase} with relaxed elbows."
            )
        if dom == "right_hand_high":
            return (
                f"Keeping her left hand poised near her waist, she lifts her right hand toward her right shoulder/hairline at {pk:.2f}s with a charming head tilt, "
                f"and {step_phrase}."
            )
        if dom == "left_hand_high":
            return (
                f"Keeping her right hand resting lightly at her hip, she raises her left hand near her left collarbone/shoulder at {pk:.2f}s, "
                f"and {step_phrase}."
            )
        if dom in ("wide_both_arms", "wide_left_arm", "wide_right_arm"):
            return (
                f"She spreads her forearms outward horizontally from her waist at {pk:.2f}s to display the full cut and silhouette, "
                f"and {step_phrase} with natural fabric follow-through."
            )
        if dom == "center_lens_reach":
            return (
                f"She extends her forearm playfully forward toward the camera lens at {pk:.2f}s in a beat-synced pointing gesture, "
                f"then retracts it smoothly across her chest as she {step_phrase}."
            )
        return (
            f"She touches her waist and handbag strap lightly at {pk:.2f}s, "
            f"{step_phrase}, and maintains an understated, photogenic smile."
        )

    return ""


def _render_hook_triplet_en(win_hook: dict, win_post: dict, hook_num: int, t_cut: float, t_post_end: float) -> tuple:
    """
    Sinh bộ 3 câu `(prep_en, trigger_en, post_en)` cho khoảnh khắc biến hình `AT {t_cut:.2f}`
    dựa trên đo lường thực tế của cửa sổ `win_hook` (ngay trước điểm cắt) và `win_post` (ngay sau điểm cắt).
    """
    dom = win_hook.get("dom_zone") or "left_hand_high"
    pk_post = float(win_post.get("peak_local_sec") or round((t_cut + t_post_end) * 0.5, 2))
    pk_post = max(round(t_cut + 0.10, 2), min(round(t_post_end - 0.10, 2), pk_post))
    turn_deg = int(win_hook.get("turn_deg") or 15)
    step_post = win_post.get("step_mode") or "smooth_hip_sway"

    post_tail_map = {
        "step_forward": f"and takes one confident step forward at {pk_post:.2f}s as the garment settles.",
        "half_step_back": f"and takes a poised half-step back at {pk_post:.2f}s to frame the full-length Look {hook_num} silhouette.",
        "playful_bounce": f"and gives a light rhythmic knee bounce at {pk_post:.2f}s as the hem and accessories respond naturally.",
        "smooth_hip_sway": f"while swaying her hips smoothly at {pk_post:.2f}s as the fabric and accessories follow with natural delay.",
    }
    post_tail = post_tail_map.get(step_post, post_tail_map["smooth_hip_sway"])

    if dom == "center_lens_reach":
        return (
            f"On the pre-beat leading into {t_cut:.2f}s, she shifts her weight onto her supporting leg and thrusts her hand straight forward toward the camera lens in a crisp transformation reach.",
            f"At the exact {t_cut:.2f}s peak of the forward hand reach toward the camera lens, perform one instantaneous matched-pose wardrobe switch into",
            f"Continue the forward arm trajectory seamlessly in Look {hook_num}, opening her palm briefly toward the lens before retracting her hand in a smooth arc {post_tail}",
        )
    if dom == "hem_waist_pull":
        return (
            f"Leading into {t_cut:.2f}s, she reaches her hands to grip/touch her waist and top hem, pulling downward crisply on the pre-beat and snapping her wrist forward.",
            f"At the exact {t_cut:.2f}s wrist-and-hem snap accent, perform one instantaneous matched-pose wardrobe switch into",
            f"Complete the waist-level hand follow-through cleanly in Look {hook_num} {post_tail}",
        )
    if dom == "both_hands_high":
        return (
            f"On the pre-beat before {t_cut:.2f}s, she makes a soft knee pulse and raises both hands briskly up to shoulder-cheek height with palms opening outward.",
            f"At the exact {t_cut:.2f}s beat accent as both hands reach shoulder height, perform one instantaneous matched-pose wardrobe switch into",
            f"Complete the cheerful two-hand shoulder accent in Look {hook_num}, then let both forearms float gracefully down toward her waist {post_tail}",
        )
    if dom == "body_turn_spin" or turn_deg >= 30:
        return (
            f"Approaching {t_cut:.2f}s, she initiates a brisk {turn_deg}-degree torso and hip pivot on the upbeat while sweeping her forearm across her waist.",
            f"At the sharpest {t_cut:.2f}s beat accent of the {turn_deg}-degree torso pivot and arm sweep, switch instantaneously into",
            f"Complete the torso turn smoothly back toward the camera lens in Look {hook_num} {post_tail}",
        )
    if dom in ("wide_both_arms", "wide_left_arm", "wide_right_arm"):
        return (
            f"Leading into {t_cut:.2f}s, she makes a small downward knee pulse and sweeps both forearms wide outward horizontally to the sides on the musical beat.",
            f"At the widest {t_cut:.2f}s peak of the outward two-arm opening, switch instantaneously into",
            f"Complete the wide outward arm opening in Look {hook_num} {post_tail}",
        )
    if dom == "right_hand_high":
        return (
            f"Approaching {t_cut:.2f}s, she rests her left hand lightly on her hip and lifts her right hand toward her right shoulder and collarbone, preparing a crisp wrist flick.",
            f"At the exact {t_cut:.2f}s peak of the right-hand shoulder wrist flick, perform one instantaneous matched-pose wardrobe switch into",
            f"Continue the right wrist follow-through naturally in Look {hook_num}, lowering her hand along a curved path {post_tail}",
        )
    return (
        f"Approaching {t_cut:.2f}s, she shifts onto her supporting leg and lifts her left hand toward her left shoulder, preparing a crisp wrist flick on the beat.",
        f"At the exact {t_cut:.2f}s peak of the left-hand shoulder wrist flick, perform one instantaneous matched-pose wardrobe switch into",
        f"Continue the left wrist movement after the switch into Look {hook_num}, extending her hand gently before retracting it in a curved arc {post_tail}",
    )


def _measure_continuity_pose_pair(frames: np.ndarray, t_settle: float, dur_s1: float = 8.0) -> tuple:
    """
    Đo tư thế thực tế của người mẫu ở cuối Phân cảnh 1 (`t_settle..8.00s`) để sinh cặp câu:
      - `s1_end_en` (7.55s–8.00s của Cảnh 1)
      - `s2_opening_pose_en` (OPENING AND CONTINUITY của Cảnh 2)
      - `s2_open_en` (0.00s–t_open2 của Cảnh 2)
    khớp 100% với vị trí tay/hông trên frame cuối của Cảnh 1!
    """
    win_end1 = _measure_subwindow_signature(frames, t_settle, dur_s1)
    dom = win_end1.get("dom_zone") or "left_hand_high"
    turn_deg = int(win_end1.get("turn_deg") or 15)

    if dom == "both_hands_high":
        return (
            "Her hands return to two relaxed loose fists just below her collarbones, elbows down.\n"
            f"She faces the camera with a {turn_deg}-degree shoulder angle, feet close together, weight mainly on her left leg, with a gentle smile.\n"
            "End in this precise pose to connect to the next clip.",
            f"Her hands begin as two relaxed loose fists below her collarbones, elbows down, shoulders angled {turn_deg} degrees, weight mainly on her left leg.",
            "Continue the gentle body sway from Clip 1 without resetting.\n"
            "She opens her hands from below her collarbones and lowers them in a soft outward arc, then brings her right hand lightly toward her waist.",
        )
    if dom == "right_hand_high":
        return (
            "Keeping her left hand resting lightly at her waist, she poises her right hand softly near her right collarbone/shoulder with a warm smile.\n"
            "End in this exact poised posture to connect seamlessly to the next clip.",
            "She begins with her left hand resting at her waist and her right hand poised softly near her right collarbone/shoulder.",
            "Continue smoothly from Clip 1 without resetting.\n"
            "She lowers her right hand gracefully from her collarbone in a curved path while shifting her weight onto her right leg.",
        )
    if dom == "left_hand_high":
        return (
            "Keeping her right hand resting on her right hip, she holds her left hand softly at chest-shoulder height in a relaxed open gesture with a warm smile.\n"
            "End in this exact poised posture to connect seamlessly to the next clip.",
            "Her right hand begins resting on her right hip while her left hand is raised softly at chest-shoulder height, weight mainly on her right leg.",
            "Continue the hip sway from Clip 1 without resetting.\n"
            "Keeping her right hand on her right hip, she opens her left hand outward to the side in a graceful welcoming gesture.",
        )
    if dom in ("wide_both_arms", "wide_left_arm", "wide_right_arm"):
        return (
            "She brings both forearms from the sides to rest lightly on her hips with elbows softly relaxed, facing the camera squarely with a bright smile.\n"
            "End in this exact pose to connect to the next clip.",
            "She begins facing the camera with both hands resting lightly on her hips, elbows softly relaxed, weight balanced.",
            "Continue the confident rhythm from Clip 1 without resetting.\n"
            "She releases her left hand from her hip to sweep softly across her upper torso while maintaining her poised stance.",
        )
    return (
        "She brings both hands lightly together at waist level in front of her torso, shoulders relaxed and angled slightly.\n"
        "She looks directly into the lens with a sweet, photogenic smile and steady foot contact.\n"
        "End in this exact posture to connect to the next clip.",
        "She begins with both hands resting lightly together at waist level in front of her torso, shoulders relaxed, feet steady.",
        "Continue the subtle hip sway from Clip 1 without resetting.\n"
        "She separates both hands smoothly from her waist in a gentle symmetrical arc and shifts her weight onto her supporting leg.",
    )

def _select_scene_cuts(visual_cuts: list, audio_beats: list, win_start: float, win_end: float, sc_idx: int, max_tr: int = 2) -> list:
    """Chọn 2 mốc cắt chuyển trang phục thực tế nhất trong cửa sổ 8s, ưu tiên visual_cuts rồi mới đến audio_beats."""
    rel_cuts = [round(c - win_start, 2) for c in (visual_cuts or []) if (win_start + 1.15) <= c <= (win_end - 0.80)]
    rel_beats = [round(b - win_start, 2) for b in (audio_beats or []) if (win_start + 1.25) <= b <= (win_end - 0.80)]

    chosen = []
    for rc in rel_cuts:
        if sc_idx >= 2 and len(chosen) == 1 and rc > 5.85:
            continue
        if not chosen or abs(rc - chosen[-1]) >= 1.40:
            chosen.append(rc)
        if len(chosen) >= max_tr:
            break

    if len(chosen) < max_tr:
        if not chosen:
            if len(rel_beats) >= 2:
                b1_cands = [b for b in rel_beats if (1.80 if sc_idx == 1 else 1.45) <= b <= (4.35 if sc_idx == 1 else 3.35)]
                t1_pick = b1_cands[len(b1_cands) // 2] if b1_cands else rel_beats[0]
                b2_max = 7.05 if sc_idx == 1 else 5.65
                b2_cands = [b for b in rel_beats if (t1_pick + 1.55) <= b <= b2_max]
                t2_pick = (b2_cands[-1] if sc_idx == 1 else b2_cands[len(b2_cands) // 2]) if b2_cands else round(min(b2_max, t1_pick + 2.35), 2)
                chosen = [round(t1_pick, 2), round(t2_pick, 2)]
            else:
                chosen = [3.40, 6.85] if sc_idx == 1 else [2.30, 4.85]
        elif len(chosen) == 1 and max_tr >= 2:
            c0 = chosen[0]
            if c0 < 4.05:
                b2_max = 7.05 if sc_idx == 1 else 5.65
                late_b = [b for b in rel_beats if max(c0 + 1.55, 4.10) <= b <= b2_max]
                c1 = (late_b[-1] if sc_idx == 1 else late_b[len(late_b) // 2]) if late_b else min(b2_max, round(c0 + 2.35, 2))
                chosen.append(round(c1, 2))
            else:
                early_b = [b for b in rel_beats if 1.45 <= b <= (c0 - 1.55)]
                c_first = early_b[len(early_b) // 2] if early_b else max(1.65, round(c0 - 2.30, 2))
                chosen.insert(0, round(c_first, 2))

    return chosen[:max_tr]


def _vn_hook_phrase(dom: str, turn_deg: int) -> str:
    if dom == "center_lens_reach":
        return "đưa tay chỉ/vươn thẳng về phía ống kính bắt trọn nhịp beat"
    if dom == "hem_waist_pull":
        return "chạm nhẹ gấu áo/eo và lắc cổ tay dứt khoát theo phách nhạc"
    if dom == "both_hands_high":
        return "nhún nhẹ đầu gối và đưa hai tay lên ngang vai mở lòng bàn tay"
    if dom == "body_turn_spin" or turn_deg >= 30:
        return f"xoay hông và vai {turn_deg}° kết hợp vung nhẹ cẳng tay ngang eo"
    if dom in ("wide_both_arms", "wide_left_arm", "wide_right_arm"):
        return "dang rộng hai cánh tay sang hai bên khoe trọn phom trang phục"
    if dom == "right_hand_high":
        return "chống nhẹ tay trái lên hông và phẩy cổ tay phải ngang vai"
    return "chuyển trụ chân mềm mại và lắc nhẹ cổ tay trái ngang vai"


def analyze_single_template_deep(tpl: dict) -> dict:
    """
    Quét sâu 10 FPS + 8000Hz Audio cho 1 Template `FVT_xxx` và tạo bộ Choreography + Prompt độc nhất.
    """
    code = tpl.get("code") or "FVT_001"
    idx_num = int(tpl.get("index") or 1)
    vpath = tpl.get("video_path") or ""
    dur = float(tpl.get("duration") or 16.0)
    num_scenes = 1 if dur < 11.5 else 2
    rec_outfits = int(tpl.get("recommended_outfits") or (2 if num_scenes == 1 else 4))
    cat_key = tpl.get("category") or "date"

    frames, audio = _extract_10fps_and_audio(vpath, max_dur=min(dur + 0.3, 16.6))
    a_info = _analyze_audio_100hz(audio, dur)
    bpm = a_info["bpm"]
    beat_int = a_info["beat_interval_sec"]
    audio_beats = a_info["audio_beats"]
    all_onsets = a_info["all_onsets"]

    v_cuts = _detect_visual_cuts_10fps(frames, dur, all_onsets)
    # Với FVT_001 giữ chuẩn 3.40, 7.03, 10.30 đã xác minh trên bảng keyframe 0.5s
    if code == "FVT_001":
        v_cuts = [3.40, 7.03, 10.30, 13.15]

    tpl["visual_cuts"] = v_cuts
    tpl["audio_beats"] = audio_beats[:14]
    tpl["estimated_bpm"] = bpm
    tpl["beat_interval_sec"] = beat_int

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

    # Đo tư thế kết Cảnh 1 (7.50s–8.00s) để nối khớp sang đầu Cảnh 2
    s1_end_en, s2_opening_pose_en, s2_open_en = _measure_continuity_pose_pair(frames, 7.50, min(8.0, dur))

    scenes_blueprint = []
    outfit_cursor = 0
    prev_last_outfit = default_outfit_files[1]
    s1_vn_summary_parts = []

    for sc_idx in range(1, num_scenes + 1):
        sc_id = f"s{sc_idx}"
        win_start = (sc_idx - 1) * 8.0
        win_end = win_start + 8.0
        max_tr = 2 if num_scenes == 2 else min(2, rec_outfits)

        if code == "FVT_001":
            chosen_cuts = [3.40, 7.03] if sc_idx == 1 else [2.30, 5.15]
        else:
            chosen_cuts = _select_scene_cuts(v_cuts, audio_beats, win_start, win_end, sc_idx, max_tr=max_tr)

        t1 = chosen_cuts[0]
        t2 = chosen_cuts[1] if len(chosen_cuts) >= 2 else min(6.95, round(t1 + 2.40, 2))
        colon_list = [fvtc._format_sec_to_colon(c) for c in chosen_cuts]
        sec_str_list = [f"{c:.2f}s" for c in chosen_cuts]

        tr_items = []
        tr_prompt_parts = []
        cur_outfits = []
        for tr_i, (c_sec, c_col) in enumerate(zip(chosen_cuts, colon_list)):
            o_fn, o_lbl, o_en = default_outfit_files[outfit_cursor % len(default_outfit_files)]
            look_num = outfit_cursor + 1
            outfit_cursor += 1
            cur_outfits.append((o_fn, o_lbl, o_en))
            tr_items.append({
                "timestamp_sec": c_sec,
                "timestamp_colon": c_col,
                "default_outfit_filename": o_fn,
                "default_outfit_label": o_lbl,
                "look_index": look_num,
            })
            tr_prompt_parts.append(
                f", Tại giây {c_col}, nhân vật đổi sang mặc bộ đồ {look_num} (Look {look_num}) [{o_fn}] và tiếp tục có hành động như video"
            )

        out1_en = cur_outfits[0][2] if len(cur_outfits) >= 1 else default_outfit_files[0][2]
        out2_en = cur_outfits[1][2] if len(cur_outfits) >= 2 else default_outfit_files[1][2]
        ref_clip_fn = f"ref_clip_{sc_id}_8s.mp4"
        overall_part = "cùng bảng tổng thể các bộ đồ [01_Character_Sheet_4_Outfits_2K.png] , " if len(chosen_cuts) <= 2 else ""

        if sc_idx == 1:
            t_open_end = round(min(1.35, max(0.85, t1 * 0.36)), 2)
            t_prep1 = round(max(t_open_end + 0.40, t1 - 0.65), 2)
            t_mid = round(min(t2 - 0.60, t1 + 1.45), 2)
            t_prep2 = round(max(t_mid + 0.25, t2 - 0.50), 2)
            t_settle = round(min(7.60, max(t2 + 0.35, 7.45)), 2)

            w_open = _measure_subwindow_signature(frames, 0.0, t_open_end)
            w_build1 = _measure_subwindow_signature(frames, t_open_end, t_prep1)
            w_hook1 = _measure_subwindow_signature(frames, t_prep1, min(8.0, t1 + 0.15))
            w_post1 = _measure_subwindow_signature(frames, t1 + 0.10, t_mid)
            w_build2 = _measure_subwindow_signature(frames, t_mid, t_prep2)
            w_hook2 = _measure_subwindow_signature(frames, t_prep2, min(8.0, t2 + 0.15))
            w_post2 = _measure_subwindow_signature(frames, t2 + 0.10, t_settle)

            if code == "FVT_001":
                import fashion_ai_video_analyzer as fava
                choreo = fava.analyze_scene_choreography_and_hooks_for_i2v(
                    ref_video_path=vpath,
                    scene_info={"scene_index": 1, "duration": 8, "transitions": [{"timestamp_sec": t1}, {"timestamp_sec": t2}]},
                    bpm_info={"estimated_bpm": bpm, "beat_interval_sec": beat_int},
                    template_meta={"code": code},
                )
            else:
                open_en = _render_window_action_en(w_open, "open_s1", 0.0, t_open_end, 0)
                build1_en = _render_window_action_en(w_build1, "build1", t_open_end, t_prep1, 0)
                prep1_en, trig1_en, post1_en = _render_hook_triplet_en(w_hook1, w_post1, 1, t1, t_mid)
                build2_en = _render_window_action_en(w_build2, "build2", t_mid, t_prep2, 1)
                prep2_en, trig2_en, post2_en = _render_hook_triplet_en(w_hook2, w_post2, 2, t2, t_settle)

                move_feel_en = (
                    f"Use a natural, beat-synced approximately {round(bpm)} BPM {cat_key}-lookbook groove "
                    f"(musical beat accent every {beat_int:.2f} seconds, measured upper-body span {w_hook1['span_px']}px): "
                    "fluid weight transfers, expressive wrist and forearm paths, and clean posture continuity. "
                    "Hair and fabric follow her motion with a small natural delay."
                )
                choreo = {
                    "profile_id": f"{code.lower()}_deep_10fps_s1",
                    "bpm": round(bpm),
                    "beat_interval_sec": beat_int,
                    "movement_feel_en": move_feel_en,
                    "s1_blocks": {
                        "open_range": f"0.00–{t_open_end:.2f}",
                        "open_en": open_en,
                        "build1_range": f"{t_open_end:.2f}–{t_prep1:.2f}",
                        "build1_en": build1_en,
                        "prep1_range": f"{t_prep1:.2f}–{t1:.2f}",
                        "prep1_en": prep1_en,
                        "at1_trigger_en": f"{trig1_en} EXACT LOOK 1",
                        "post1_range": f"{t1:.2f}–{t_mid:.2f}",
                        "post1_en": post1_en,
                        "build2_range": f"{t_mid:.2f}–{t_prep2:.2f}",
                        "build2_en": build2_en,
                        "prep2_range": f"{t_prep2:.2f}–{t2:.2f}",
                        "prep2_en": prep2_en,
                        "at2_trigger_en": f"{trig2_en} EXACT LOOK 2 from the character sheet",
                        "post2_range": f"{t2:.2f}–{t_settle:.2f}",
                        "post2_en": post2_en,
                        "end_range": f"{t_settle:.2f}–8.00",
                        "end_en": s1_end_en,
                    },
                }

            b1 = choreo["s1_blocks"]
            move_feel_en = choreo["movement_feel_en"]
            hk1_vn = _vn_hook_phrase(w_hook1["dom_zone"], w_hook1["turn_deg"])
            hk2_vn = _vn_hook_phrase(w_hook2["dom_zone"], w_hook2["turn_deg"])
            act_detail_vn = (
                f"Phân cảnh 1 (0.0s – 8.0s • {bpm} BPM): Mở đầu mặc đồ Basic nhún nhịp {beat_int:.2f}s/beat (đỉnh cử chỉ mở đầu tại {w_open['peak_local_sec']:.2f}s); "
                f"tại giây {t1:.2f}s ({colon_list[0]}) thực hiện hook {hk1_vn} biến hình sang Bộ 1; "
                f"tại giây {t2:.2f}s ({colon_list[-1]}) thực hiện hook {hk2_vn} biến hình sang Bộ 2 và giữ dáng chuẩn tại 7.55s–8.00s để nối sang Phân cảnh 2."
            )
            s1_vn_summary_parts.append(act_detail_vn)

            prompt_str = (
                f"Tạo 1 video mới hoàn toàn, có nhân vật là [02_Character_Sheet_Basic_Poses_2K.png] "
                f"{overall_part}"
                f"nhân vật có hành động như video tham chiếu [{ref_clip_fn}] , "
                f"bối cảnh căn phòng như ảnh [07_Nhan_Vat_Basic_Phong_Ngu_2K.png] , "
                f"mở đầu video nhân vật mặc bộ đồ Basic như trong ảnh [07_Nhan_Vat_Basic_Phong_Ngu_2K.png]"
                + "".join(tr_prompt_parts)
                + ". Dùng nhạc của video gốc, nhân vật không nói chuyện và không có lời thoại."
            )

            if len(chosen_cuts) >= 2:
                mid_look2 = (
                    f"{b1['post1_range']}:\n{b1['post1_en']}\n\n"
                    f"{b1['build2_range']}:\n{b1['build2_en']}\n\n"
                    f"{b1['prep2_range']}:\n{b1['prep2_en']}\n\n"
                    f"AT {t2:.2f}:\n{b1['at2_trigger_en']}:\n{out2_en}.\n"
                    "Replace the complete Look 1 accessory set with the exact Look 2 set.\n"
                    "Maintain the same identity, body position and continuous arm movement.\n\n"
                    f"{b1['post2_range']}:\n{b1['post2_en']}\n\n"
                )
            else:
                mid_look2 = f"{t1:.2f}–6.20:\n{b1['post1_en']}\n\n6.20–7.55:\n{b1['build2_en']}\n\n"

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
                f"{b1['open_range']}:\n{b1['open_en']}\n\n"
                f"{b1['build1_range']}:\n{b1['build1_en']}\n\n"
                f"{b1['prep1_range']}:\n{b1['prep1_en']}\n\n"
                f"AT {t1:.2f}:\n{b1['at1_trigger_en']}:\n{out1_en}.\n"
                "The entire outfit and its accessories switch together in a single clean visual beat.\n"
                "Preserve her face, body position, arm trajectory and bedroom. No dissolve or intermediate clothing.\n\n"
                + mid_look2
                + f"{b1['end_range']}:\n{b1['end_en']}\n\n"
                "AUDIO AND MOUTH\n"
                "Generate a silent visual clip. No speech, singing, humming, breathing performance or sound effects.\n"
                "Her lips may remain softly closed or make tiny silent expressive movements.\n"
                "Do not invent lyric-specific lip synchronization without the original audio reference.\n\n"
                "AVOID\n"
                "Face drift, body reshaping, extra fingers, rigid elbows, robotic dance, foot sliding, jumping, camera cuts, camera movement, flashing light, magical particles, melting fabric, partial outfits, mixed accessories, text, captions, labels, logos, duplicated people or visible reference-sheet panels."
            )
        else:
            # Phân cảnh 2 (8.0s -> 16.0s)
            t_open2 = round(min(1.05, max(0.65, t1 * 0.42)), 2)
            t_prep3 = round(max(t_open2 + 0.35, t1 - 0.45), 2)
            t_mid2 = round(min(t2 - 0.55, t1 + 1.30), 2)
            t_prep4 = round(max(t_mid2 + 0.20, t2 - 0.45), 2)
            t_turn_s = round(min(6.45, max(t2 + 0.75, 6.15)), 2)
            t_end_s = round(min(7.50, max(t_turn_s + 0.75, 7.35)), 2)

            w_open2 = _measure_subwindow_signature(frames, 8.0, 8.0 + t_open2)
            w_build3 = _measure_subwindow_signature(frames, 8.0 + t_open2, 8.0 + t_prep3)
            w_hook3 = _measure_subwindow_signature(frames, 8.0 + t_prep3, 8.0 + min(7.9, t1 + 0.15))
            w_post3 = _measure_subwindow_signature(frames, 8.0 + t1 + 0.10, 8.0 + t_mid2)
            w_build4 = _measure_subwindow_signature(frames, 8.0 + t_mid2, 8.0 + t_prep4)
            w_hook4 = _measure_subwindow_signature(frames, 8.0 + t_prep4, 8.0 + min(7.9, t2 + 0.15))
            w_post4 = _measure_subwindow_signature(frames, 8.0 + t2 + 0.10, 8.0 + t_turn_s)
            w_turn = _measure_subwindow_signature(frames, 8.0 + t_turn_s, 8.0 + t_end_s)
            w_end2 = _measure_subwindow_signature(frames, 8.0 + t_end_s, min(dur, 16.0))

            if code == "FVT_001":
                import fashion_ai_video_analyzer as fava
                choreo = fava.analyze_scene_choreography_and_hooks_for_i2v(
                    ref_video_path=vpath,
                    scene_info={"scene_index": 2, "duration": 8, "transitions": [{"timestamp_sec": t1}, {"timestamp_sec": t2}]},
                    bpm_info={"estimated_bpm": bpm, "beat_interval_sec": beat_int},
                    template_meta={"code": code},
                )
            else:
                build3_en = _render_window_action_en(w_build3, "build3", t_open2, t_prep3, 2)
                prep3_en, trig3_en, post3_en = _render_hook_triplet_en(w_hook3, w_post3, 3, t1, t_mid2)
                build4_en = _render_window_action_en(w_build4, "build4", t_mid2, t_prep4, 3)
                prep4_en, trig4_en, post4_en = _render_hook_triplet_en(w_hook4, w_post4, 4, t2, t_turn_s)

                pk_turn = float(w_turn.get("peak_local_sec") or round((t_turn_s + t_end_s) * 0.5, 2))
                pk_turn = max(round(t_turn_s + 0.10, 2), min(round(t_end_s - 0.10, 2), pk_turn))
                if w_turn.get("is_back_turn"):
                    turn_en = (
                        f"She executes a smooth 360-degree turn peaking at {pk_turn:.2f}s to showcase both the back and front silhouette of Look 4, "
                        "keeping her gaze returning warmly to the camera lens."
                    )
                else:
                    t_deg = max(25, int(w_turn.get("turn_deg") or 30))
                    turn_en = (
                        f"At {pk_turn:.2f}s, with two small controlled steps, she angles her body approximately {t_deg} degrees to showcase the side drape and accessories of Look 4 while keeping her gaze on the lens."
                    )

                dom_e2 = w_end2.get("dom_zone") or "left_hand_high"
                if dom_e2 in ("wide_both_arms", "wide_left_arm", "wide_right_arm"):
                    end2_en = (
                        "Turning back frontally (7.45s–8.00s), she opens both forearms outward in a confident, radiant final fashion lookbook pose."
                    )
                elif dom_e2 == "center_lens_reach":
                    end2_en = (
                        "Holding her poised front stance (7.45s–8.00s), she folds both forearms comfortably across her upper waist with a chic editorial smile."
                    )
                else:
                    end2_en = (
                        "Settling into a balanced three-quarter fashion pose (7.45s–8.00s), she rests one hand lightly on her hip with a subtle heel lift and a warm smile."
                    )

                move_feel_en = (
                    f"Continue the {round(bpm)} BPM {cat_key}-lookbook groove (beat every {beat_int:.2f}s, measured motion span {w_hook3['span_px']}px): "
                    "soft weight transfers, small graceful steps, fluid wrists and natural fabric follow-through."
                )
                choreo = {
                    "profile_id": f"{code.lower()}_deep_10fps_s2",
                    "bpm": round(bpm),
                    "beat_interval_sec": beat_int,
                    "opening_pose_en": s2_opening_pose_en,
                    "movement_feel_en": move_feel_en,
                    "s2_blocks": {
                        "open_range": f"0.00–{t_open2:.2f}",
                        "open_en": s2_open_en,
                        "build3_range": f"{t_open2:.2f}–{t_prep3:.2f}",
                        "build3_en": build3_en,
                        "prep3_range": f"{t_prep3:.2f}–{t1:.2f}",
                        "prep3_en": prep3_en,
                        "at3_trigger_en": f"{trig3_en} EXACT LOOK 3",
                        "post3_range": f"{t1:.2f}–{t_mid2:.2f}",
                        "post3_en": post3_en,
                        "build4_range": f"{t_mid2:.2f}–{t_prep4:.2f}",
                        "build4_en": build4_en,
                        "prep4_range": f"{t_prep4:.2f}–{t2:.2f}",
                        "prep4_en": prep4_en,
                        "at4_trigger_en": f"{trig4_en} EXACT LOOK 4 from the character sheet",
                        "post4_range": f"{t2:.2f}–{t_turn_s:.2f}",
                        "post4_en": post4_en,
                        "turn_range": f"{t_turn_s:.2f}–{t_end_s:.2f}",
                        "turn_en": turn_en,
                        "end_range": f"{t_end_s:.2f}–8.00",
                        "end_en": end2_en,
                    },
                }

            b2 = choreo["s2_blocks"]
            open_pose_en = choreo["opening_pose_en"]
            move_feel_en = choreo["movement_feel_en"]
            prev_lbl = prev_last_outfit[1]
            prev_en = prev_last_outfit[2]

            hk3_vn = _vn_hook_phrase(w_hook3["dom_zone"], w_hook3["turn_deg"])
            hk4_vn = _vn_hook_phrase(w_hook4["dom_zone"], w_hook4["turn_deg"])
            act_detail_vn = (
                f"Phân cảnh 2 (8.0s – 16.0s • {bpm} BPM): Nối tiếp trực tiếp từ frame cuối Phân cảnh 1 ([scene_s1_last_frame_2k.png] đang mặc {prev_lbl}); "
                f"tại giây {t1:.2f}s ({colon_list[0]}) thực hiện hook {hk3_vn} biến hình sang Bộ 3; "
                f"tại giây {t2:.2f}s ({colon_list[-1]}) thực hiện hook {hk4_vn} biến hình sang Bộ 4 và tạo dáng kết tại {t_turn_s:.2f}s–8.00s."
            )
            s1_vn_summary_parts.append(act_detail_vn)

            prompt_str = (
                f"Tạo 1 video nối tiếp hoàn hảo từ phân cảnh {sc_idx - 1}, lấy khung hình cuối của phân cảnh {sc_idx - 1} [scene_s{sc_idx - 1}_last_frame_2k.png] làm frame mở đầu chính xác "
                f"{overall_part}"
                f"nhân vật tiếp tục có hành động mượt mà như video tham chiếu [{ref_clip_fn}] , "
                f"giữ nguyên bối cảnh căn phòng và góc máy toàn thân từ phân cảnh {sc_idx - 1}, "
                f"mở đầu video nhân vật đang mặc sẵn bộ trang phục cuối của phân cảnh {sc_idx - 1} ({prev_lbl}) theo đúng tư thế ở [scene_s{sc_idx - 1}_last_frame_2k.png]"
                + "".join(tr_prompt_parts)
                + ". Dùng nhạc của video gốc, nhân vật không nói chuyện và không có lời thoại."
            )

            if len(chosen_cuts) >= 2:
                mid_look4 = (
                    f"{b2['post3_range']}:\n{b2['post3_en']}\n\n"
                    f"{b2['build4_range']}:\n{b2['build4_en']}\n\n"
                    f"{b2['prep4_range']}:\n{b2['prep4_en']}\n\n"
                    f"AT {t2:.2f}:\n{b2['at4_trigger_en']}:\n{out2_en}.\n"
                    "The hairstyle, glasses, clothing and accessories switch coherently in the same visual instant.\n"
                    "Preserve her face, head position and body proportions.\n"
                    "Remove the previous Look 3 accessory set.\n\n"
                    f"{b2['post4_range']}:\n{b2['post4_en']}\n\n"
                )
            else:
                mid_look4 = f"{t1:.2f}–{t_turn_s:.2f}:\n{b2['post3_en']}\n\n"

            prompt_i2v_str = (
                "Create an 8-second photorealistic vertical 9:16 continuation of the previous fashion video.\n\n"
                "OPENING AND CONTINUITY\n"
                f"Use the final frame of Clip {sc_idx - 1} [scene_s{sc_idx - 1}_last_frame_2k.png] as the exact first frame.\n"
                "Continue the same woman, bedroom, warm lighting, locked full-body camera, subject scale, facial identity and floor position.\n"
                f"She begins in EXACT LOOK 2: {prev_en} from the character sheet [01_Character_Sheet_4_Outfits_2K.png].\n"
                f"{open_pose_en}\n\n"
                f"{move_feel_en}\n\n"
                "TIMELINE — LOCAL CLIP TIME\n\n"
                f"{b2['open_range']}:\n{b2['open_en']}\n\n"
                f"{b2['build3_range']}:\n{b2['build3_en']}\n\n"
                f"{b2['prep3_range']}:\n{b2['prep3_en']}\n\n"
                f"AT {t1:.2f}:\n{b2['at3_trigger_en']}:\n{out1_en}, exactly as shown in Look 3.\n"
                "The full outfit and accessories change together.\n"
                "Keep her facial identity and preserve the moving hand's trajectory. No intermediate outfit.\n\n"
                + mid_look4
                + f"{b2['turn_range']}:\n{b2['turn_en']}\n\n"
                f"{b2['end_range']}:\n{b2['end_en']}\n\n"
                "AUDIO AND MOUTH\n"
                "Generate a silent visual clip: no singing, speech, humming or sound effects.\n"
                "She may make subtle silent mouth expressions, but should not perform audible vocals.\n"
                "The original music will be added continuously during editing.\n\n"
                "AVOID\n"
                "Identity changes, exaggerated hip motion, rigid posing, sudden limb snaps, foot sliding, floating feet, extra fingers, glasses warping, mixed outfits, leftover bags, duplicate accessories, magical transformation effects, dissolves, camera movement, background changes, captions, labels and reference-sheet layouts."
            )

        if cur_outfits:
            prev_last_outfit = cur_outfits[-1]

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
            "i2v_choreography": choreo,
            "estimated_bpm": bpm,
            "beat_interval_sec": beat_int,
            "action_detail": act_detail_vn,
            "prompt_chained_i2v": prompt_i2v_str,
            "prompt_template": prompt_str,
        })

    if idx_num > 30 and s1_vn_summary_parts:
        tpl["action_description"] = " ".join(s1_vn_summary_parts)
    tpl["scenes_blueprint"] = scenes_blueprint
    return tpl


def run_deep_reanalysis_all_252():
    t0 = time.time()
    with open(CATALOG_JSON_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    templates = catalog.get("templates") or []
    print(f"[DEEP-10FPS] Dang quet sau 10FPS + 8000Hz Audio cho toan bo {len(templates)} video mau...", flush=True)

    with ThreadPoolExecutor(max_workers=12) as ex:
        updated_templates = list(ex.map(analyze_single_template_deep, templates))

    catalog["templates"] = updated_templates
    catalog["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    with open(CATALOG_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    s1_prompts = [t["scenes_blueprint"][0]["prompt_chained_i2v"] for t in updated_templates]
    s2_prompts = [t["scenes_blueprint"][1]["prompt_chained_i2v"] for t in updated_templates if len(t["scenes_blueprint"]) > 1]
    print(
        f"[DONE] Hoan tat trong {time.time() - t0:.1f}s! "
        f"Tong video: {len(updated_templates)} | "
        f"Unique S1 Prompts: {len(set(s1_prompts))}/{len(s1_prompts)} | "
        f"Unique S2 Prompts: {len(set(s2_prompts))}/{len(s2_prompts)}",
        flush=True,
    )


if __name__ == "__main__":
    run_deep_reanalysis_all_252()
