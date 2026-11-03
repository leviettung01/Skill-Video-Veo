# -*- coding: utf-8 -*-
import os
import sys
import glob
import json
import shutil

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE = r"c:\Users\ADMIN\Desktop\Python\Veo 3 Tool\AutoVeo3Pro_v6\Auto_Veo_3_Pro\Grok\Skill Video Veo"
PROJECTS_DIR = os.path.join(WORKSPACE, "projects")
FINAL_VIDEOS_DIR = os.path.join(WORKSPACE, "final_videos")

os.makedirs(FINAL_VIDEOS_DIR, exist_ok=True)

ALL_PIDS = [
    "1735109997221349342",
    "1738260652434293979",
    "1735811961345574265",
    "1737365863541671120",
    "1738175423853987061",
    "1735424296473888680",
    "1737909342761027082",
]

moved_count = 0
for pid in ALL_PIDS:
    pdir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(pdir):
        continue

    prompts_path = os.path.join(pdir, "prompts.json")
    if not os.path.exists(prompts_path):
        continue
    prompts_data = json.load(open(prompts_path, encoding="utf-8"))
    videos = prompts_data.get("videos", {})

    state_path = os.path.join(pdir, "flow_state.json")
    state = {"uploaded_refs": {}, "scene_uuids": {}, "built_finals": []}
    if os.path.exists(state_path):
        try:
            state = json.load(open(state_path, encoding="utf-8"))
        except Exception:
            pass
    built_finals = set(state.get("built_finals") or [])

    for vkey in videos.keys():
        dst_name = f"{pid}-{vkey}-final-30s.mp4"
        dst_path = os.path.join(FINAL_VIDEOS_DIR, dst_name)
        src_path = os.path.join(pdir, dst_name)

        if os.path.exists(src_path) and os.path.getsize(src_path) > 50000:
            if not (os.path.exists(dst_path) and os.path.getsize(dst_path) == os.path.getsize(src_path)):
                shutil.copy2(src_path, dst_path)
            try:
                os.remove(src_path)
            except OSError:
                pass
            moved_count += 1
            built_finals.add(vkey)
            print(f"Synced {dst_name} -> final_videos/")
        elif os.path.exists(dst_path) and os.path.getsize(dst_path) > 50000:
            built_finals.add(vkey)

        # Update spec_<vkey>.json output path to point to final_videos/
        spec_path = os.path.join(pdir, f"spec_{vkey}.json")
        if os.path.exists(spec_path):
            try:
                sp = json.load(open(spec_path, encoding="utf-8"))
                sp["output"] = dst_path
                with open(spec_path, "w", encoding="utf-8") as f:
                    json.dump(sp, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    # Also clean up any old duplicate *-final-30s.mp4 left in pdir
    for leftover in glob.glob(os.path.join(pdir, "*-final-30s.mp4")):
        try:
            os.remove(leftover)
        except OSError:
            pass

    state["built_finals"] = sorted(list(built_finals))
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

total_in_final_dir = len(glob.glob(os.path.join(FINAL_VIDEOS_DIR, "*-final-30s.mp4")))
print(f"\nDONE! Synced {moved_count} files. Total Final Videos in {FINAL_VIDEOS_DIR}: {total_in_final_dir}")
