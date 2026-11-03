#!/usr/bin/env python3
"""
EditVideo.py -- Module xu ly Video & Audio cho GrokVideoTool
"""
import os, random, shutil, subprocess, uuid, datetime
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

try:
    _CNOW = subprocess.CREATE_NO_WINDOW
except AttributeError:
    _CNOW = 0

from PyQt6.QtCore import QThread, pyqtSignal

if TYPE_CHECKING:
    pass

def get_video_duration(path: str) -> float:
    try:
        if not shutil.which("ffprobe"):
            return 10.0
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=10
        )
        val = r.stdout.strip()
        return float(val) if val else 10.0
    except Exception:
        return 10.0

def get_audio_duration(path: str) -> float:
    try:
        if not shutil.which("ffprobe"):
            return 0.0
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=10
        )
        val = r.stdout.strip()
        return float(val) if val else 0.0
    except Exception:
        return 0.0

def has_audio_stream(file_path: str) -> bool:
    try:
        if not shutil.which("ffprobe"):
            return False
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
             "-of", "csv=p=0", file_path],
            capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=5
        )
        return "audio" in res.stdout.lower()
    except Exception:
        return False

def pick_music_from_playlist(playlist: List[str], random_mode: bool = True) -> Optional[str]:
    if not playlist:
        return None
    valid = [p for p in playlist if p and Path(p).exists()]
    if not valid:
        return None
    return random.choice(valid) if random_mode else valid[0]

def adjust_video_speed(input_path: str, output_path: str, speed_factor: float, log_fn=None) -> bool:
    def _log(msg):
        if log_fn: log_fn(msg)
    speed_factor = max(0.25, min(4.0, speed_factor))
    setpts_val = 1.0 / speed_factor
    def build_atempo_chain(sf):
        filters = []
        remaining = sf
        while remaining > 2.0:
            filters.append("atempo=2.0"); remaining /= 2.0
        while remaining < 0.5:
            filters.append("atempo=0.5"); remaining /= 0.5
        filters.append(f"atempo={remaining:.4f}")
        return ",".join(filters)
    atempo_chain = build_atempo_chain(speed_factor)
    _log(f"  Dieu chinh toc do video: {speed_factor:.3f}x")
    audio_ok = has_audio_stream(input_path)
    if audio_ok:
        cmd = ["ffmpeg", "-y", "-i", input_path,
               "-vf", f"setpts={setpts_val:.6f}*PTS",
               "-af", atempo_chain,
               "-c:v", "libx264", "-preset", "fast", "-crf", "23",
               "-c:a", "aac", "-b:a", "192k", output_path]
    else:
        cmd = ["ffmpeg", "-y", "-i", input_path,
               "-vf", f"setpts={setpts_val:.6f}*PTS",
               "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
               output_path]
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=300)
    if r.returncode == 0 and Path(output_path).exists():
        _log(f"  OK: {Path(output_path).name}"); return True
    _log(f"  Loi dieu chinh toc do: {r.stderr[:200]}")
    try: shutil.copy2(input_path, output_path)
    except: pass
    return False

def cleanup_source_clips(sp, log_fn=None):
    def _log(msg):
        if log_fn: log_fn(msg)
    deleted = 0
    for scene in (sp.scenes or []):
        opts = getattr(scene, "video_options", [])
        if not opts and scene.video_path:
            opts = [scene.video_path]
        for path in opts:
            try:
                p = Path(path)
                if p.exists() and p.is_file() and "FINAL_" not in p.name:
                    p.unlink(); deleted += 1
                    _log(f"  Xoa clip goc: {p.name}")
            except Exception as e:
                _log(f"  Loi xoa {path}: {e}")
    _log(f"  Da xoa {deleted} clip goc")


# Device profiles mimicking real smartphone cameras
DEVICE_PROFILES = [
    {
        "make": "Apple",
        "model": "iPhone 13 Pro",
        "software": "17.4.1",
        "video_handler": "Core Media Video",
        "audio_handler": "Core Media Audio",
        "brand": "mp42"
    },
    {
        "make": "Apple",
        "model": "iPhone 14 Pro Max",
        "software": "17.5.1",
        "video_handler": "Core Media Video",
        "audio_handler": "Core Media Audio",
        "brand": "mp42"
    },
    {
        "make": "Apple",
        "model": "iPhone 15",
        "software": "17.6",
        "video_handler": "Core Media Video",
        "audio_handler": "Core Media Audio",
        "brand": "mp42"
    },
    {
        "make": "samsung",
        "model": "SM-S908B",
        "software": "Android 13",
        "video_handler": "VideoHandle",
        "audio_handler": "SoundHandle",
        "brand": "mp42"
    },
    {
        "make": "samsung",
        "model": "SM-S918B",
        "software": "Android 14",
        "video_handler": "VideoHandle",
        "audio_handler": "SoundHandle",
        "brand": "mp42"
    },
    {
        "make": "Xiaomi",
        "model": "2201122C",
        "software": "Android 12",
        "video_handler": "VideoHandle",
        "audio_handler": "SoundHandle",
        "brand": "mp42"
    },
    {
        "make": "Xiaomi",
        "model": "23127PN0CC",
        "software": "Android 14",
        "video_handler": "VideoHandle",
        "audio_handler": "SoundHandle",
        "brand": "mp42"
    }
]

# Random GPS locations in major Vietnam cities
VIETNAM_LOCATIONS = [
    "+10.7769+106.7009/", # HCMC District 1
    "+10.7626+106.6822/", # HCMC District 5
    "+21.0285+105.8542/", # Hanoi Hoan Kiem
    "+21.0064+105.8427/", # Hanoi Hai Ba Trung
    "+16.0544+108.2022/", # Da Nang
    "+12.2388+109.1967/", # Nha Trang
    "+10.0384+105.7876/", # Can Tho
    "+20.8449+106.6881/", # Hai Phong
]

def post_process_natural_metadata(video_path: str, log_fn=None) -> bool:
    def _log(msg):
        if log_fn: log_fn(msg)
    
    if not Path(video_path).exists():
        _log(f"  [Error] Natural metadata: File {video_path} khong ton tai.")
        return False
        
    _log(f"  Tu nhien hoa metadata cho video final...")
    
    try:
        # Choose a random profile and location
        profile = random.choice(DEVICE_PROFILES)
        location = random.choice(VIETNAM_LOCATIONS)
        
        # Choose creation time slightly in the past
        now = datetime.datetime.utcnow()
        offset_minutes = random.randint(5, 60)
        creation_time = (now - datetime.timedelta(minutes=offset_minutes)).strftime("%Y-%m-%dT%H:%M:%S.000000Z")
        
        temp_out = str(Path(video_path).parent / f"_temp_natural_{uuid.uuid4().hex[:6]}.mp4")
        
        has_audio = has_audio_stream(video_path)
        
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-map", "0:v:0"
        ]
        if has_audio:
            cmd.extend(["-map", "0:a:0"])
            
        cmd.extend([
            "-c:v", "copy"
        ])
        
        if has_audio:
            cmd.extend([
                "-c:a", "copy"
            ])
            
        cmd.extend([
            "-fflags", "+bitexact",
            "-metadata", f"make={profile['make']}",
            "-metadata", f"model={profile['model']}",
            "-metadata", f"software={profile['software']}",
            "-metadata", f"creation_time={creation_time}",
            "-metadata", f"location={location}",
            "-metadata:s:v:0", f"handler_name={profile['video_handler']}",
            "-metadata:s:v:0", "encoder=",
        ])
        
        if has_audio:
            cmd.extend([
                "-metadata:s:a:0", f"handler_name={profile['audio_handler']}",
                "-metadata:s:a:0", "encoder=",
            ])
            
        cmd.extend([
            "-brand", profile["brand"],
            temp_out
        ])
        
        _log(f"  Gia lap thiet bi: {profile['make']} {profile['model']} | GPS: {location.strip('/')}")
        
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=300)
        if r.returncode == 0 and Path(temp_out).exists():
            Path(video_path).unlink()
            shutil.move(temp_out, video_path)
            _log("  OK: Hoan thanh tu nhien hoa metadata video final!")
            return True
        else:
            _log(f"  [Warning] FFmpeg naturalize loi: {r.stderr[:200]}")
            if Path(temp_out).exists():
                try: Path(temp_out).unlink()
                except: pass
            return False
            
    except Exception as e:
        _log(f"  [Warning] Loi ngoai le khi tu nhien hoa metadata: {e}")
        return False


class FFmpegConcatWorker(QThread):
    log_signal   = pyqtSignal(str)
    concat_ready = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, project, concat_settings: dict = None):
        super().__init__()
        self.project = project
        self.concat_settings = concat_settings or {}

    def _log(self, msg: str):
        self.log_signal.emit(msg)

    def run(self):
        try:
            self._run_internal()
        except Exception as e:
            self._log(f"Loi noi video: {e}")
            self.error_signal.emit(str(e))

    def _run_internal(self):
        p = self.project
        settings = self.concat_settings
        if settings.get("scenes"):
            scene_info = settings["scenes"]
        else:
            scene_info = []
            for scene in sorted(p.scenes, key=lambda s: s.scene_number):
                if scene.video_path and Path(scene.video_path).exists():
                    scene_info.append({"video_path": scene.video_path, "trim_start": 0, "scene_number": scene.scene_number})
        if not scene_info:
            raise RuntimeError("Khong co video nao de noi.")
        if not shutil.which("ffmpeg"):
            self._log("FFmpeg chua cai."); self.concat_ready.emit(scene_info[0]["video_path"]); return

        transition_type = ""; transition_dur = 0.0; xfade_transition_name = "fade"
        trans = settings.get("transition", "")
        if trans and "Không" not in trans and "Random" not in trans:
            parts = trans.strip().split()
            if parts:
                dur_str = parts[-1].replace("s", "")
                try:
                    transition_dur = float(dur_str)
                except ValueError:
                    transition_dur = 0.0
                
                type_str = " ".join(parts[:-1]).lower()
                if "fade to black" in type_str:
                    transition_type = "fade_black"
                else:
                    transition_type = "crossfade"
                    if "dissolve" in type_str:
                        xfade_transition_name = "dissolve"
                    elif "wipe left" in type_str:
                        xfade_transition_name = "wipeleft"
                    elif "wipe right" in type_str:
                        xfade_transition_name = "wiperight"
                    elif "slide left" in type_str:
                        xfade_transition_name = "slideleft"
                    elif "slide right" in type_str:
                        xfade_transition_name = "slideright"
                    else:
                        xfade_transition_name = "fade"

        clones_by_scene: dict = {}
        for item in scene_info:
            clones_by_scene.setdefault(item["scene_number"], []).append(item)
        reverse_scenes = settings.get("reverse_scenes", False)
        if reverse_scenes:
            scene_numbers = sorted(clones_by_scene.keys(), reverse=True)
        else:
            scene_numbers = sorted(clones_by_scene.keys())
        num_outputs = settings.get("num_outputs", 1)
        no_duplicate = settings.get("no_duplicate", False)
        delete_source = settings.get("delete_source", False)
        voice_speed_adjust = settings.get("voice_speed_adjust", False)

        bg_music_playlist = settings.get("bg_music_playlist") or []
        if not bg_music_playlist and settings.get("bg_music_path"):
            bg_music_playlist = [settings["bg_music_path"]]
        bg_music_random = settings.get("bg_music_random", True)

        available_clones = {s: list(c) for s, c in clones_by_scene.items()}
        first_final_path = ""; actual_outputs = 0
        self._log(f"Bat dau noi video: {num_outputs} output")

        for out_idx in range(1, num_outputs + 1):
            chosen_items = []
            for s_num in scene_numbers:
                pool = available_clones[s_num]
                if no_duplicate:
                    if not pool:
                        if out_idx == 1: raise RuntimeError(f"Phan canh #{s_num} het clone.")
                        self._log(f"Hoan thanh {actual_outputs} video!"); self.concat_ready.emit(first_final_path); return
                    choice = random.choice(pool); pool.remove(choice); chosen_items.append(choice)
                else:
                    chosen_items.append(random.choice(clones_by_scene[s_num]))

            trimmed_paths = []
            for si in chosen_items:
                vp = si["video_path"]
                trim_start = si.get("trim_start", 0)
                trim_end = si.get("trim_end", 0)
                total_duration = get_video_duration(vp)
                if total_duration <= 0:
                    total_duration = si.get("duration", 10.0)
                
                # We always re-encode to make the join 100% smooth and handle both start/end trims
                trimmed = str(p.output_dir / f"_trimmed_out{out_idx}_sc{si['scene_number']}.mp4")
                self._log(f"  Xu ly phan canh {si['scene_number']}: cat dau {trim_start}s, cat cuoi {trim_end}s...")
                
                active_duration = max(0.1, total_duration - trim_start - trim_end)
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", f"{trim_start:.2f}",
                    "-t", f"{active_duration:.2f}",
                    "-i", vp,
                    "-c:v", "libx264",
                    "-preset", "superfast",
                    "-crf", "22",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    trimmed
                ]
                r = subprocess.run(cmd, capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=60)
                if r.returncode == 0 and Path(trimmed).exists():
                    trimmed_paths.append(trimmed)
                else:
                    self._log(f"  [Warning] Re-encode failed for scene {si['scene_number']}, using original: {r.stderr[:200] if r.stderr else 'Unknown'}")
                    trimmed_paths.append(vp)

            voiceover_raw = settings.get("voiceover_path")
            if voiceover_raw in ("random", "random_all"):
                valid_voices = []
                if hasattr(self.project, "voice_paths") and self.project.voice_paths:
                    valid_voices = [v for v in self.project.voice_paths if v and Path(v).exists()]
                
                if not valid_voices and voiceover_raw == "random_all":
                    downloads_dir = Path(__file__).parent.absolute() / "TiktokShop" / "crawled_products"
                    if downloads_dir.exists():
                        seen = set()
                        # 1. Quét voices từ thư mục root voices/
                        root_voices = downloads_dir / "voices"
                        if root_voices.exists() and root_voices.is_dir():
                            for pid_dir in root_voices.iterdir():
                                if pid_dir.is_dir():
                                    for f in pid_dir.glob("*.mp3"):
                                        fp = str(f)
                                        if fp not in seen:
                                            seen.add(fp)
                                            valid_voices.append(fp)
                        # 2. Quét voices từ các thư mục con trong crawled_products
                        for entry in downloads_dir.iterdir():
                            if entry.is_dir() and entry.name != "voices":
                                if "_" in entry.name:
                                    v_dir = entry / "voices"
                                    if v_dir.exists() and v_dir.is_dir():
                                        for f in v_dir.glob("*.mp3"):
                                            fp = str(f)
                                            if fp not in seen:
                                                seen.add(fp)
                                                valid_voices.append(fp)
                                else:
                                    for sub in entry.iterdir():
                                        if sub.is_dir() and "_" in sub.name:
                                            v_dir = sub / "voices"
                                            if v_dir.exists() and v_dir.is_dir():
                                                for f in v_dir.glob("*.mp3"):
                                                    fp = str(f)
                                                    if fp not in seen:
                                                        seen.add(fp)
                                                        valid_voices.append(fp)
                
                voiceover_raw = random.choice(valid_voices) if valid_voices else None
                if voiceover_raw: 
                    self._log(f"Random voice: {Path(voiceover_raw).name}")
            elif voiceover_raw == "silent":
                voiceover_raw = None

            speed_adjusted_paths = list(trimmed_paths)
            if voice_speed_adjust and voiceover_raw and Path(voiceover_raw).exists():
                voice_dur = get_audio_duration(voiceover_raw)
                if voice_dur > 0:
                    total_vid_dur = sum(max(0.1, get_video_duration(vp)) for vp in trimmed_paths)

                    target_vid_dur = voice_dur
                    if transition_type == "crossfade" and transition_dur > 0 and len(trimmed_paths) > 1:
                        target_vid_dur += (len(trimmed_paths) - 1) * transition_dur
                    sf = max(0.25, min(4.0, total_vid_dur / target_vid_dur))
                    self._log(f"  Voice: {voice_dur:.1f}s | Target Vid Dur: {target_vid_dur:.1f}s | Video: {total_vid_dur:.1f}s -> x{sf:.3f}")
                    if abs(sf - 1.0) > 0.02:
                        adjusted = []
                        for vp, si in zip(trimmed_paths, chosen_items):
                            adj = str(p.output_dir / f"_speed_out{out_idx}_sc{si['scene_number']}.mp4")
                            ok = adjust_video_speed(vp, adj, sf, self._log)
                            adjusted.append(adj if ok and Path(adj).exists() else vp)
                        speed_adjusted_paths = adjusted

            if num_outputs == 1:
                final_path = str(p.output_dir / f"FINAL_{p.id}.mp4")
            else:
                final_path = str(p.output_dir / f"FINAL_{p.id}_{out_idx}.mp4")
            if out_idx == 1: first_final_path = final_path

            if len(speed_adjusted_paths) == 1:
                shutil.copy2(speed_adjusted_paths[0], final_path)
                self._log(f"  Output {out_idx}: copy don canh -> {Path(final_path).name}")
            else:
                if transition_type == "crossfade" and transition_dur > 0:
                    self._log(f"  Output {out_idx}: crossfade {transition_dur}s ({xfade_transition_name})...")
                    self._concat_with_xfade(speed_adjusted_paths, final_path, transition_dur, xfade_transition_name)
                elif transition_type == "fade_black" and transition_dur > 0:
                    self._log(f"  Output {out_idx}: fade-to-black {transition_dur}s...")
                    self._concat_with_fade_black(speed_adjusted_paths, final_path, transition_dur)
                else:
                    self._log(f"  Output {out_idx}: cat thang {len(speed_adjusted_paths)} clips (re-encode de tranh dung hinh)...")
                    list_path = p.output_dir / f"concat_list_out{out_idx}.txt"
                    with open(list_path, "w", encoding="utf-8") as f:
                        for vp in speed_adjusted_paths: f.write(f"file '{vp}'\n")
                    r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
                                         "-c:v", "libx264", "-preset", "superfast", "-crf", "22",
                                         "-c:a", "aac", "-b:a", "128k", "-vsync", "cfr", final_path],
                                       capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=300)
                    if r.returncode != 0:
                        raise RuntimeError(f"Concat error: {r.stderr[:500] if r.stderr else 'Unknown error'}")
                    try: list_path.unlink()
                    except: pass

            for vp in trimmed_paths:
                if f"_trimmed_out{out_idx}_" in str(vp) and Path(vp).exists():
                    try: Path(vp).unlink()
                    except: pass
            for vp in speed_adjusted_paths:
                if f"_speed_out{out_idx}_" in str(vp) and Path(vp).exists():
                    try: Path(vp).unlink()
                    except: pass

            self._log(f"  OK Output {out_idx}: {Path(final_path).name}")
            chosen_bg = pick_music_from_playlist(bg_music_playlist, bg_music_random)
            bg_vol = settings.get("bg_music_vol", 0.3); voice_vol = settings.get("voiceover_vol", 1.0); orig_vol = settings.get("orig_video_vol", 1.0)
            if chosen_bg or voiceover_raw or orig_vol != 1.0:
                target_dur = None
                if voice_speed_adjust and voiceover_raw and Path(voiceover_raw).exists():
                    target_dur = get_audio_duration(voiceover_raw)
                self._mix_audio_post_process(final_path, chosen_bg, voiceover_raw, bg_vol, voice_vol, orig_vol, target_duration=target_dur)
            
            # Tu nhien hoa metadata video sau khi mix
            post_process_natural_metadata(final_path, self._log)
            
            actual_outputs += 1

        if delete_source and first_final_path and Path(first_final_path).exists():
            self._log("  Xoa clip goc sau render...")
            cleanup_source_clips(self.project, self._log)
        self._log(f"Hoan thanh {actual_outputs} video final!")
        self.concat_ready.emit(first_final_path)

    def _mix_audio_post_process(self, video_path, bg_music_path, voiceover_path, bg_vol, voice_vol, orig_vol, target_duration=None):
        self._log(f"  Mix audio: {Path(video_path).name}...")
        vid_has_audio = has_audio_stream(video_path)
        inputs = ["-i", video_path]; filters = []; mix_inputs = []; input_idx = 1
        if vid_has_audio and orig_vol > 0:
            filters.append(f"[0:a]volume={orig_vol}[a_orig]"); mix_inputs.append("[a_orig]")
        if bg_music_path and Path(bg_music_path).exists() and bg_vol > 0:
            inputs.extend(["-stream_loop", "-1", "-i", bg_music_path])
            filters.append(f"[{input_idx}:a]volume={bg_vol}[a_bg]"); mix_inputs.append("[a_bg]"); input_idx += 1
            self._log(f"  Nhac nen: {Path(bg_music_path).name} (loop)")
        if voiceover_path and Path(voiceover_path).exists() and voice_vol > 0:
            inputs.extend(["-i", voiceover_path])
            filters.append(f"[{input_idx}:a]volume={voice_vol}[a_voice]"); mix_inputs.append("[a_voice]"); input_idx += 1
            self._log(f"  Long tieng: {Path(voiceover_path).name}")
        if not mix_inputs: return
        if len(mix_inputs) == 1:
            filter_complex = filters[0]; map_audio = mix_inputs[0]
        else:
            filter_complex = "; ".join(filters) + f"; {''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0[aout]"
            map_audio = "[aout]"
        temp_mixed = str(Path(video_path).parent / f"_temp_mixed_{uuid.uuid4().hex[:6]}.mp4")
        duration_args = ["-shortest"]
        if target_duration is not None and target_duration > 0:
            duration_args = ["-t", f"{target_duration:.3f}"]
        cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_complex, "-map", "0:v", "-map", map_audio,
                                           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k"] + duration_args + [temp_mixed]
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=300)
        if r.returncode == 0 and Path(temp_mixed).exists():
            try: Path(video_path).unlink(); shutil.move(temp_mixed, video_path); self._log("  OK mix audio!")
            except Exception as e: self._log(f"  Loi luu file mixed: {e}")
        else:
            self._log(f"  Loi FFmpeg audio: {r.stderr[:300]}")
            if Path(temp_mixed).exists():
                try: Path(temp_mixed).unlink()
                except: pass

    def _concat_with_xfade(self, paths, final_path, xfade_dur, transition_name="fade"):
        if len(paths) == 2:
            dur1 = get_video_duration(paths[0]); offset = max(0, dur1 - xfade_dur)
            cmd = ["ffmpeg", "-y", "-i", paths[0], "-i", paths[1],
                   "-filter_complex",
                   f"[0:v][1:v]xfade=transition={transition_name}:duration={xfade_dur}:offset={offset}[v];[0:a][1:a]acrossfade=d={xfade_dur}[a]",
                   "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                   "-c:a", "aac", "-b:a", "192k", final_path]
            r = subprocess.run(cmd, capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=300)
            if r.returncode != 0:
                cmd[-7] = f"[0:v][1:v]xfade=transition={transition_name}:duration={xfade_dur}:offset={offset}[v];[0:a][1:a]concat=n=2:v=0:a=1[a]"
                r2 = subprocess.run(cmd, capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=300)
                if r2.returncode != 0: raise RuntimeError(f"xfade error: {r2.stderr[:300]}")
        else:
            temp = paths[0]
            for i in range(1, len(paths)):
                out = str(Path(final_path).parent / f"_xfade_temp_{i}.mp4") if i < len(paths)-1 else final_path
                dur_prev = get_video_duration(temp); offset = max(0, dur_prev - xfade_dur)
                cmd = ["ffmpeg", "-y", "-i", temp, "-i", paths[i],
                       "-filter_complex",
                       f"[0:v][1:v]xfade=transition={transition_name}:duration={xfade_dur}:offset={offset}[v];[0:a][1:a]acrossfade=d={xfade_dur}[a]",
                       "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                       "-c:a", "aac", "-b:a", "192k", out]
                r = subprocess.run(cmd, capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=300)
                if r.returncode != 0:
                    cmd_fb = list(cmd)
                    cmd_fb[-7] = f"[0:v][1:v]xfade=transition={transition_name}:duration={xfade_dur}:offset={offset}[v];[0:a][1:a]concat=n=2:v=0:a=1[a]"
                    r2 = subprocess.run(cmd_fb, capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=300)
                    if r2.returncode != 0: raise RuntimeError(f"xfade chain error {i}: {r2.stderr[:200]}")
                if "_xfade_temp_" in str(temp) and Path(temp).exists():
                    try: Path(temp).unlink()
                    except: pass
                temp = out

    def _concat_with_fade_black(self, paths, final_path, fade_dur):
        faded_paths = []
        for i, vp in enumerate(paths):
            dur = get_video_duration(vp); faded = str(Path(final_path).parent / f"_faded_{i+1}.mp4")
            fade_start = max(0, dur - fade_dur)
            cmd = ["ffmpeg", "-y", "-i", vp, "-vf", f"fade=t=out:st={fade_start}:d={fade_dur}",
                   "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "copy", faded]
            r = subprocess.run(cmd, capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=120)
            faded_paths.append(faded if r.returncode == 0 else vp)
        list_path = Path(final_path).parent / "concat_faded.txt"
        with open(list_path, "w", encoding="utf-8") as f:
            for fp in faded_paths: f.write(f"file '{fp}'\n")
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", final_path]
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=120)
        if r.returncode != 0:
            cmd2 = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", "-b:a", "128k", final_path]
            r = subprocess.run(cmd2, capture_output=True, encoding="utf-8", creationflags=_CNOW, timeout=300)
            if r.returncode != 0: raise RuntimeError(f"Fade concat error: {r.stderr[:300]}")
        try: list_path.unlink()
        except: pass
        for fp in faded_paths:
            if "_faded_" in str(fp) and Path(fp).exists():
                try: Path(fp).unlink()
                except: pass
