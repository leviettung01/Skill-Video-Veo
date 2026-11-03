# -*- coding: utf-8 -*-
import os
import re
import json

WS_DIR = r"c:\Users\ADMIN\Desktop\Python\Veo 3 Tool\AutoVeo3Pro_v6\Auto_Veo_3_Pro\Grok\Skill Video Veo"
PROJECTS_DIR = os.path.join(WS_DIR, "projects")

ALL_PIDS = [
    "1735109997221349342",
    "1738260652434293979",
    "1735811961345574265",
    "1737365863541671120",
    "1738175423853987061",
    "1735424296473888680",
    "1737909342761027082",
]

ACTION_BY_SCENE_IDX = {
    1: (
        "ACTION: The woman looks directly at the camera with a confident, energetic expression, "
        "naturally speaking while holding the exact product from the reference image steady at waist level, "
        "tilting it slightly toward the camera to showcase it, then keeping the presenting pose at the end."
    ),
    2: (
        "ACTION: The woman looks directly at the camera with a warm, enthusiastic expression, "
        "naturally speaking while holding the exact product from the reference image steady at waist level "
        "and gesturing lightly toward the bottom-left shopping cart, then keeping the presenting pose at the end."
    ),
    3: (
        "ACTION: The woman looks directly at the camera with a bright, friendly smile, "
        "naturally speaking while holding the exact product from the reference image steady at waist level "
        "to showcase it clearly, then keeping the presenting pose at the end."
    ),
}


def build_concise_video_prompt(scene_idx, timed_lines):
    action_line = ACTION_BY_SCENE_IDX.get(scene_idx, ACTION_BY_SCENE_IDX[1])
    lines_joined = "\n".join(timed_lines)
    return (
        "A 10-second vertical 9:16 video starting directly from the provided reference image, "
        "one continuous medium shot, front-facing camera. Keep the character, the exact product in her hands, "
        "the items on the table, and the background 100% unchanged from the reference image — "
        "do not alter, redesign, or replace the product's shape, color, pattern, or logo.\n\n"
        f"{action_line}\n\n"
        "VOICE — read the dialogue in 3 timed segments exactly as marked. Keep a steady, even pace so each segment "
        "fills its time window. Finish the last word exactly at 10.0 seconds. Read each word exactly once — "
        "no repetition, no looping, no added words, then stay silent:\n"
        f"{lines_joined}\n\n"
        "No background music, no watermark.\n"
        "Negative: changed product, altered product design, repeating voice, looping dialogue, second voice pass, rushed reading, changed face"
    )


def extract_timed_lines(old_prompt):
    matches = re.findall(r'^\[[0-9.]+-[0-9.]+s\]\s*".*"$', old_prompt, flags=re.MULTILINE)
    if len(matches) == 3:
        return matches
    # Fallback line scan
    out = []
    for ln in old_prompt.splitlines():
        ln_s = ln.strip()
        if ln_s.startswith("[") and "s]" in ln_s:
            out.append(ln_s)
    return out


def main():
    updated_scenes = 0
    for pid in ALL_PIDS:
        pdir = os.path.join(PROJECTS_DIR, pid)
        prompts_path = os.path.join(pdir, "prompts.json")
        if not os.path.exists(prompts_path):
            continue
        data = json.load(open(prompts_path, encoding="utf-8"))
        for v_key, v_info in data.get("videos", {}).items():
            for idx_s, sc in enumerate(v_info.get("scenes", []), start=1):
                timed = extract_timed_lines(sc.get("prompt", ""))
                if len(timed) == 3:
                    sc["prompt"] = build_concise_video_prompt(idx_s, timed)
                    updated_scenes += 1
                else:
                    print(f"[WARN] Could not extract 3 timed lines for {pid} | {sc.get('id')}: {timed}")
        with open(prompts_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Updated {updated_scenes} scene video prompts across {len(ALL_PIDS)} products to the new concise format!")


if __name__ == "__main__":
    main()

