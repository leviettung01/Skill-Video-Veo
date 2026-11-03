# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS_DIR = r"c:\Users\ADMIN\Desktop\Python\Veo 3 Tool\AutoVeo3Pro_v6\Auto_Veo_3_Pro\Grok\Skill Video Veo"
mt_path = os.path.join(WS_DIR, "flow_final_pipeline", "scripts", "run_all_7_videos_mt.py")
txt = open(mt_path, encoding="utf-8").read()

old_block = """        final_mp4 = os.path.join(pdir, f"{pid}-{v_key}-final-30s.mp4")
        if os.path.exists(final_mp4) and os.path.getsize(final_mp4) > 50000:
            FFMPEG_SUBMITTED.add(key)
            return"""

new_block = """        final_mp4 = os.path.join(WS_DIR, "final_videos", f"{pid}-{v_key}-final-30s.mp4")
        if os.path.exists(final_mp4) and os.path.getsize(final_mp4) > 50000:
            FFMPEG_SUBMITTED.add(key)
            return"""

if old_block in txt:
    txt = txt.replace(old_block, new_block)

old_load = """        pdir = os.path.join(PROJECTS_DIR, pid)
        prompts_data = json.load(open(os.path.join(pdir, "prompts.json"), encoding="utf-8"))
        refs_state = json.load(open(os.path.join(pdir, "flow_refs_state.json"), encoding="utf-8"))"""

new_load = """        pdir = os.path.join(PROJECTS_DIR, pid)
        marker_clean = os.path.join(pdir, ".cleaned_new")
        if os.path.exists(marker_clean):
            try:
                os.remove(marker_clean)
            except OSError:
                pass
        prompts_data = json.load(open(os.path.join(pdir, "prompts.json"), encoding="utf-8"))
        refs_path = os.path.join(pdir, "flow_refs_state.json")
        refs_state = json.load(open(refs_path, encoding="utf-8")) if os.path.exists(refs_path) else {"uploaded_prod_refs": {}, "variants": {}}"""

if old_load in txt:
    txt = txt.replace(old_load, new_load)

with open(mt_path, "w", encoding="utf-8") as f:
    f.write(txt)
print("Updated run_all_7_videos_mt.py to use final_videos/ folder and support reset products!")
