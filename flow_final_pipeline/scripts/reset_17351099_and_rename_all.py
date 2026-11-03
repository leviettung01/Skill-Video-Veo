# -*- coding: utf-8 -*-
import os
import sys
import glob
import json
import shutil

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS_DIR = r"c:\Users\ADMIN\Desktop\Python\Veo 3 Tool\AutoVeo3Pro_v6\Auto_Veo_3_Pro\Grok\Skill Video Veo"
PROJECTS_DIR = os.path.join(WS_DIR, "projects")
FINAL_VIDEOS_DIR = os.path.join(WS_DIR, "final_videos")
SCRIPTS_DIR = os.path.join(WS_DIR, "flow_final_pipeline", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from sync_web_ui_state import ALL_PIDS, VKEY_TO_CHAR_V, get_final_video_filename, sync_web_ui

TARGET_RESET_PID = "1735109997221349342"


def main():
    os.makedirs(FINAL_VIDEOS_DIR, exist_ok=True)
    renamed_count = 0

    for pid in ALL_PIDS:
        pdir = os.path.join(PROJECTS_DIR, pid)
        if not os.path.isdir(pdir):
            continue

        # 1. Update all spec_v*.json files to output "{pid}_{nv1/nv2}_v{1/2/3}.mp4"
        for vkey, char_v in VKEY_TO_CHAR_V.items():
            spec_path = os.path.join(pdir, f"spec_{vkey}.json")
            if os.path.exists(spec_path):
                sp = json.load(open(spec_path, encoding="utf-8"))
                sp["output"] = f"{pid}_{char_v}.mp4"
                with open(spec_path, "w", encoding="utf-8") as f:
                    json.dump(sp, f, ensure_ascii=False, indent=2)

            # 2. Rename existing final videos in final_videos/ (for non-reset products)
            old_final = os.path.join(FINAL_VIDEOS_DIR, f"{pid}-{vkey}-final-30s.mp4")
            new_final = os.path.join(FINAL_VIDEOS_DIR, f"{pid}_{char_v}.mp4")
            if pid != TARGET_RESET_PID and os.path.exists(old_final):
                if os.path.exists(new_final):
                    os.remove(old_final)
                else:
                    shutil.move(old_final, new_final)
                renamed_count += 1
                print(f"[RENAME] {os.path.basename(old_final)} -> {os.path.basename(new_final)}")

    # 3. Delete ALL videos of TARGET_RESET_PID (1735109997221349342) to re-render from scratch!
    t_pdir = os.path.join(PROJECTS_DIR, TARGET_RESET_PID)
    removed_vids = []
    for pat in (
        os.path.join(FINAL_VIDEOS_DIR, f"{TARGET_RESET_PID}*"),
        os.path.join(t_pdir, "v*_s*.mp4*"),
        os.path.join(t_pdir, "nv*_s*.mp4*"),
        os.path.join(t_pdir, "_norm_*.mp4"),
        os.path.join(t_pdir, "_tmp_*.ass"),
        os.path.join(t_pdir, "*-final-30s.mp4"),
        os.path.join(t_pdir, f"{TARGET_RESET_PID}_*.mp4"),
    ):
        for fp in glob.glob(pat):
            if os.path.isfile(fp):
                try:
                    os.remove(fp)
                    removed_vids.append(os.path.basename(fp))
                except OSError:
                    pass

    # Clear scene_uuids and built_finals in flow_state.json for TARGET_RESET_PID
    state_path = os.path.join(t_pdir, "flow_state.json")
    state = {"uploaded_refs": {}, "scene_uuids": {}, "built_finals": []}
    if os.path.exists(state_path):
        try:
            old_st = json.load(open(state_path, encoding="utf-8"))
            state["uploaded_refs"] = old_st.get("uploaded_refs", {})
        except Exception:
            pass
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    sync_web_ui(force=True)
    print(f"\n[DONE] Renamed {renamed_count} final videos to {{id}}_{{nv1/nv2}}_v{{1/2/3}}.mp4")
    print(f"[RESET {TARGET_RESET_PID}] Deleted {len(removed_vids)} video files: {removed_vids}")


if __name__ == "__main__":
    main()

