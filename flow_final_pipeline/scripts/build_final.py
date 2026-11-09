#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build final 1080p 60fps video: concat scenes + Kho Template Subtitle (Karaoke / Custom ASS) + top-left slide overlays.
Usage: python3 build_final.py spec.json
"""
import json, subprocess, sys, os, shutil, re

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    import engine_settings_manager as _esm
except Exception:
    _esm = None

try:
    from subtitle_template_engine import (
        DEFAULT_SUBTITLE_SETTINGS,
        build_ass_from_subtitle_settings,
    )
except Exception:
    DEFAULT_SUBTITLE_SETTINGS = {}
    build_ass_from_subtitle_settings = None

TARGET_FPS = 60


def ts(s):
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"


def probe_clip_duration(clip_path: str, default_dur: float = 10.0) -> float:
    if not os.path.exists(clip_path):
        return default_dur
    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                clip_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        val = float((r.stdout or "").strip())
        if 2.0 <= val <= 30.0:
            return val
    except Exception:
        pass
    return default_dur


def build_ass(spec, ass_path, scene_durations, subtitle_settings=None):
    if build_ass_from_subtitle_settings is not None:
        return build_ass_from_subtitle_settings(
            spec=spec,
            ass_path=ass_path,
            scene_durations=scene_durations,
            subtitle_settings=subtitle_settings,
        )

    # Fallback mặc định chuẩn hiện tại (Font DejaVu Sans cỡ 48, Trắng + Vàng Gold #FFE066, Viền đen 3px, MarginV 225)
    L = []
    L.append(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "ScaledBorderAndShadow: yes\n"
    )
    L.append(
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
        "SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
        "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
    )
    L.append(
        "Style: Sub,DejaVu Sans,48,&H00FFFFFF,&H0066E0FF,&H00000000,"
        "&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,30,30,225,1\n"
    )
    L.append(
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
    )
    off = 0.0
    for i, sc in enumerate(spec["scenes"]):
        sc_dur = scene_durations[i] if i < len(scene_durations) else 10.0
        phrases = sc.get("phrases") or []
        total = sum(max(1, sw) for _, sw in phrases) or max(1, sc.get("words", 10))
        t = off
        for _, (text, sw) in enumerate(phrases):
            text_str = str(text or "").strip().upper()
            if not text_str:
                continue
            dur = (max(1, sw) / float(total)) * sc_dur
            toks = text_str.split()
            kcs = max(1, int(round(dur * 100 / max(1, len(toks)))))
            ktxt = "".join(f"{{\\k{kcs}}}{w} " for w in toks).rstrip()
            L.append(
                f"Dialogue: 0,{ts(t)},{ts(t+dur)},Sub,,0,0,0,,"
                f"{{\\fad(150,150)}}{ktxt}\n"
            )
            t += dur
        off += sc_dur
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("".join(L))
    return ass_path


def main():
    spec_path = sys.argv[1]
    base = os.path.dirname(os.path.abspath(spec_path))
    spec = json.load(open(spec_path, encoding="utf-8"))
    n_scenes = len(spec["scenes"])
    assert n_scenes >= 2, "need at least 2 scenes"
    ov = [im for im in (spec.get("overlays") or []) if os.path.exists(os.path.join(base, im))]
    if not ov:
        p_img_dir = os.path.join(base, "product_images")
        if os.path.isdir(p_img_dir):
            for fn in sorted(os.listdir(p_img_dir)):
                if fn.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    ov.append(os.path.join("product_images", fn))
        if not ov and os.path.exists(os.path.join(base, "v1-refimg.jpg")):
            ov.append("v1-refimg.jpg")
    ov = ov[:5]
    assert len(ov) >= 1, "need at least 1 overlay image"

    scene_durations = [
        probe_clip_duration(os.path.join(base, sc["file"]), default_dur=float(spec.get("scene_duration_sec", 10.0)))
        for sc in spec["scenes"]
    ]
    total_dur = sum(scene_durations)

    # Hardware-aware FFmpeg configuration & Subtitle Template settings from engine_settings_manager
    threads_cnt = 4
    use_nvenc = False
    cpu_preset = "medium"
    auto_gen_thumb = True
    auto_inject_01s = True
    sub_settings = dict(DEFAULT_SUBTITLE_SETTINGS or {})
    if _esm is not None:
        try:
            cfg = _esm.load_engine_settings()
            hw = cfg.get("hardware") or {}
            threads_cnt = int(cfg.get("ffmpeg_threads_per_job") or 4)
            enc_pref = cfg.get("video_encoder", "auto")
            use_nvenc = (enc_pref == "h264_nvenc") or (enc_pref == "auto" and hw.get("has_nvenc"))
            cpu_preset = cfg.get("ffmpeg_preset") or "fast"
            if cpu_preset not in ("ultrafast", "superfast", "veryfast", "faster", "fast", "medium"):
                cpu_preset = "fast"
            auto_gen_thumb = bool(cfg.get("auto_generate_thumbnail", True))
            auto_inject_01s = bool(cfg.get("auto_inject_thumbnail_01s", True))
            if isinstance(cfg.get("subtitle_settings"), dict):
                sub_settings.update(cfg["subtitle_settings"])
        except Exception:
            pass
    if isinstance(spec.get("subtitle_settings"), dict):
        sub_settings.update(spec["subtitle_settings"])

    out_rel = os.path.basename(spec["output"])
    tmp_out_rel = "_tmp_build_" + out_rel
    tmp_out = os.path.join(base, tmp_out_rel)
    out = os.path.join(base, out_rel)
    ass_rel = "_tmp_" + out_rel.replace(".mp4", ".ass")
    ass = os.path.join(base, ass_rel)
    old_same_ass = os.path.join(base, out_rel.replace(".mp4", ".ass"))
    if os.path.exists(old_same_ass):
        try:
            os.remove(old_same_ass)
        except OSError:
            pass
    build_ass(spec, ass, scene_durations, subtitle_settings=sub_settings)

    ov_window = min(20.0, max(total_dur - scene_durations[0], total_dur * 0.66))
    ov_start = max(0.0, total_dur - ov_window)
    n_ov = len(ov)
    step = ov_window / float(n_ov)
    marks = []
    for idx_ov in range(n_ov):
        t_a = round(ov_start + idx_ov * step, 2)
        t_b = round(total_dur if idx_ov == n_ov - 1 else (ov_start + (idx_ov + 1) * step), 2)
        marks.append((t_a, t_b))

    norm_v = []
    norm_a = []
    for idx in range(n_scenes):
        norm_v.append(
            f"[{idx}:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={TARGET_FPS},format=yuv420p[vn{idx}];"
        )
        norm_a.append(
            f"[{idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[an{idx}];"
        )

    v_inputs = "".join(f"[vn{i}]" for i in range(n_scenes))
    a_inputs = "".join(f"[an{i}]" for i in range(n_scenes))

    fc = (
        "".join(norm_v)
        + "".join(norm_a)
        + f"{v_inputs}concat=n={n_scenes}:v=1:a=0[vcat];"
        + f"{a_inputs}concat=n={n_scenes}:v=0:a=1[acat];"
    )
    for j in range(n_ov):
        fc += (
            f"[{n_scenes + j}:v]scale=390:390:force_original_aspect_ratio=decrease,"
            f"pad=390:390:(ow-iw)/2:(oh-ih)/2:color=black@0.0,format=rgba[ov{j+1}];"
        )

    prev = "vcat"
    # 1. Chèn các ảnh Slide Sản Phẩm góc trên bên trái (20s cuối)
    for j, (a, b) in enumerate(marks, start=1):
        nxt = f"vov{j}"
        fc += f"[{prev}][ov{j}]overlay=30:30:eof_action=repeat:enable='between(t,{a},{b})'[{nxt}];"
        prev = nxt

    # 2. Render Phụ đề chuyên nghiệp từ Kho Template Subtitle (`[vout]`)
    fc += f"[{prev}]ass='{ass_rel}'[vout]"

    cmd = ["ffmpeg", "-y", "-v", "error"]
    for sc in spec["scenes"]:
        cmd += ["-i", sc["file"]]
    for im in ov:
        cmd += ["-i", im]
    cmd += [
        "-filter_complex", fc,
        "-map", "[vout]", "-map", "[acat]",
        "-r", str(TARGET_FPS),
        "-threads", str(threads_cnt),
    ]
    if use_nvenc:
        cmd += ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "20"]
    else:
        cmd += ["-c:v", "libx264", "-preset", cpu_preset, "-crf", "19"]
    cmd += [
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", tmp_out_rel,
    ]
    subprocess.run(cmd, cwd=base, check=True)

    dst_central = out
    try:
        ws_root = os.path.dirname(os.path.dirname(base))
        final_videos_dir = os.path.join(ws_root, "final_videos")
        if os.path.basename(os.path.dirname(base)).lower() == "projects" or os.path.exists(final_videos_dir):
            os.makedirs(final_videos_dir, exist_ok=True)
            dst_central = os.path.join(final_videos_dir, out_rel)
            shutil.copy2(tmp_out, dst_central)
            try:
                os.remove(tmp_out)
            except OSError:
                pass
        else:
            os.replace(tmp_out, out)
    except Exception as e:
        print("WARN copying to final_videos:", e)

    # Auto-generate AI Thumbnail & inject 0.1s intro frame into Final Video
    if _esm is not None and auto_gen_thumb:
        try:
            pid_dir = os.path.basename(base)
            spec_bname = os.path.basename(spec_path)
            m_vk = re.match(r"^spec_(.+)\.json$", spec_bname, re.I)
            vkey_str = m_vk.group(1) if m_vk else "v1"
            res_th = _esm.generate_thumbnail_for_variant(
                pid=pid_dir,
                vkey=vkey_str,
                inject_01s=auto_inject_01s,
                prefer_existing_ref=True,
            )
            if res_th.get("ok"):
                print(f"THUMB_OK: {res_th.get('thumbnail_path')} (injected_01s={res_th.get('injected_01s')})")
        except Exception as th_err:
            print("WARN generating/injecting thumbnail:", th_err)

    r = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height,codec_name,r_frame_rate",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1",
            dst_central,
        ],
        capture_output=True, text=True, check=True,
    )
    print(r.stdout)
    print("OK:", dst_central)


if __name__ == "__main__":
    main()
