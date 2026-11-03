# -*- coding: utf-8 -*-
import os
import sys
import json
import copy
import shutil

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS_DIR = r"c:\Users\ADMIN\Desktop\Python\Veo 3 Tool\AutoVeo3Pro_v6\Auto_Veo_3_Pro\Grok\Skill Video Veo"
PROJECTS_DIR = os.path.join(WS_DIR, "projects")

LEGACY_SCENES = {
    "1738260652434293979": [
        {
            "v_key": "v7",
            "base_v": "v2",
            "hook_title": "NV2 - Bản Cũ 1: Giá Sốc Tận Xưởng (Xưởng Lắp Ráp)",
            "style": "Xưởng Dây Chuyền Lắp Ráp (Bản Cũ)",
            "src_ref": "nv2-refimg.jpg",
            "dst_ref": "v7-refimg.jpg",
            "uuids": {
                "v7_s1": "958a3b41-5fbc-4a8e-bba2-b4996b7bb64e",
                "v7_s2": "dee94535-3f2b-447d-bffd-37d5aac6187e",
                "v7_s3": "7b94cb2c-c99b-4eb6-9a4a-0b40f26569f0",
            },
        },
        {
            "v_key": "v8",
            "base_v": "v4",
            "hook_title": "NV2 - Bản Cũ 2: Luxury Boutique (Showroom Cao Cấp)",
            "style": "Showroom Quà Tặng Luxury (Bản Cũ)",
            "src_ref": "nv2-luxury-refimg.jpg",
            "dst_ref": "v8-refimg.jpg",
            "uuids": {
                "v8_s1": "abd489c0-551b-4d9d-abe8-f74d5aa5035f",
                "v8_s2": "943a1888-2a27-4981-9051-6d1603d3d469",
                "v8_s3": "a72645e9-c771-4c8c-b30e-1d7d83494a2c",
            },
        },
    ],
    "1735811961345574265": [
        {
            "v_key": "v7",
            "base_v": "v2",
            "hook_title": "NV2 - Bản Cũ: Giá Sốc Tận Xưởng (Xưởng Lắp Ráp)",
            "style": "Xưởng Dây Chuyền Lắp Ráp (Bản Cũ)",
            "src_ref": "nv2-refimg.jpg",
            "dst_ref": "v7-refimg.jpg",
            "uuids": {
                "v7_s1": "259ca6a2-6941-4f74-b6b5-c6a07702d9c2",
                "v7_s2": "22595c79-8732-444a-8a14-fd5bbf4103bb",
                "v7_s3": "10c3f6c4-ec1e-4dc9-877f-85fd39510bc9",
            },
        }
    ],
    "1737365863541671120": [
        {
            "v_key": "v7",
            "base_v": "v2",
            "hook_title": "NV2 - Bản Cũ: Giá Sốc Tận Xưởng (Xưởng Lắp Ráp)",
            "style": "Xưởng Dây Chuyền Lắp Ráp (Bản Cũ)",
            "src_ref": "nv2-refimg.jpg",
            "dst_ref": "v7-refimg.jpg",
            "uuids": {
                "v7_s1": "14e9e0d3-0a2c-40d6-bc36-79005a406366",
                "v7_s2": "0d5b31c9-4899-4106-8618-e86eb9041c7f",
                "v7_s3": "83305eb2-f16b-4174-b115-7b104aa3ce3f",
            },
        }
    ],
    "1738175423853987061": [
        {
            "v_key": "v7",
            "base_v": "v2",
            "hook_title": "NV2 - Bản Cũ: Giá Sốc Tận Xưởng (Xưởng Ươm Giống)",
            "style": "Xưởng Ươm Giống & Đóng Gói (Bản Cũ)",
            "src_ref": "nv2-refimg.jpg",
            "dst_ref": "v7-refimg.jpg",
            "uuids": {
                "v7_s1": "c813d46a-3e41-45b3-acd8-c9b93e54de2f",
                "v7_s2": "eca81129-7a58-46c6-8bf3-b88b9a962167",
                "v7_s3": "bc614f0e-028f-4337-9186-279580449cfe",
            },
        }
    ],
    "1735424296473888680": [
        {
            "v_key": "v7",
            "base_v": "v2",
            "hook_title": "NV2 - Bản Cũ: Giá Sốc Tận Xưởng (Xưởng Chế Tác)",
            "style": "Xưởng Dây Chuyền Lắp Ráp (Bản Cũ)",
            "src_ref": "nv2-refimg.jpg",
            "dst_ref": "v7-refimg.jpg",
            "uuids": {
                "v7_s1": "e159120e-6444-49e5-82d6-ee58091c4b35",
                "v7_s2": "1edbee33-9937-4ce9-a824-49a22884a9ea",
                "v7_s3": "abc92b1a-4a87-46b1-b9b8-dc46195b5c1a",
            },
        }
    ],
    "1737909342761027082": [
        {
            "v_key": "v7",
            "base_v": "v2",
            "hook_title": "NV2 - Bản Cũ: Giá Sốc Tận Xưởng (Xưởng Chiết Rót)",
            "style": "Xưởng Chiết Rót & Đóng Gói (Bản Cũ)",
            "src_ref": "nv2-refimg.jpg",
            "dst_ref": "v7-refimg.jpg",
            "uuids": {
                "v7_s1": "f87b20b3-08d8-4b87-99ea-0f7e5d912452",
                "v7_s2": "9dfbd5e5-f38a-46b4-b425-9e30ec88b0c4",
                "v7_s3": "2d651fd7-8e12-44cc-906c-95c4ac4aa857",
            },
        }
    ],
}

ALL_PIDS = [
    "1735109997221349342",
    "1738260652434293979",
    "1735811961345574265",
    "1737365863541671120",
    "1738175423853987061",
    "1735424296473888680",
    "1737909342761027082",
]


def main():
    for pid in ALL_PIDS:
        pdir = os.path.join(PROJECTS_DIR, pid)
        prompts_path = os.path.join(pdir, "prompts.json")
        refs_path = os.path.join(pdir, "flow_refs_state.json")
        state_path = os.path.join(pdir, "flow_state.json")

        prompts_data = json.load(open(prompts_path, encoding="utf-8"))
        refs_state = json.load(open(refs_path, encoding="utf-8"))
        refs_state.setdefault("variants", {})
        state = {"uploaded_refs": {}, "scene_uuids": {}}
        if os.path.exists(state_path):
            try:
                state = json.load(open(state_path, encoding="utf-8"))
            except Exception:
                pass

        # 1. For any scene in v1..v6 that is NOT downloaded yet, clear its stale scene_uuid from state
        #    and polish its prompt wording so Veo never aborts it.
        for vk in ["v1", "v2", "v3", "v4", "v5", "v6"]:
            if vk not in prompts_data.get("videos", {}):
                continue
            vcfg = prompts_data["videos"][vk]
            for sc in vcfg.get("scenes", []):
                sc_id = sc["id"]
                mp4_abs = os.path.join(pdir, sc["file"])
                if not (os.path.exists(mp4_abs) and os.path.getsize(mp4_abs) > 50000):
                    state["scene_uuids"].pop(sc_id, None)
                    p_txt = sc["prompt"]
                    p_txt = p_txt.replace(
                        "Mỗi nick sẽ nhận được một mã trợ giá riêng biệt.",
                        "Mỗi tài khoản các bác sẽ thấy một mức giá khác nhau.",
                    )
                    p_txt = p_txt.replace("[0.0-3.4s]", "[0.0-3.5s]").replace("[3.6-6.0s]", "[3.5-6.0s]")
                    sc["prompt"] = p_txt
                    print(f"[CLEAN] Cleared stale UUID & polished prompt for {pid} | {sc_id}")

        # 2. Add legacy completed variants (v7, v8) where product image matched 100%
        for leg in LEGACY_SCENES.get(pid, []):
            vk = leg["v_key"]
            base_v = leg["base_v"]
            src_ref_abs = os.path.join(pdir, "flow_work", leg["src_ref"])
            if not os.path.exists(src_ref_abs):
                src_ref_abs = os.path.join(pdir, leg["src_ref"])
            dst_ref_abs = os.path.join(pdir, leg["dst_ref"])
            if os.path.exists(src_ref_abs):
                shutil.copy2(src_ref_abs, dst_ref_abs)

            base_vcfg = copy.deepcopy(prompts_data["videos"][base_v])
            base_vcfg["hook_title"] = leg["hook_title"]
            base_vcfg["style"] = leg["style"]
            base_vcfg["ref_image"] = leg["dst_ref"]
            for idx_s, sc in enumerate(base_vcfg["scenes"], start=1):
                new_sc_id = f"{vk}_s{idx_s}"
                sc["id"] = new_sc_id
                sc["file"] = f"{new_sc_id}.mp4"
                state["scene_uuids"][new_sc_id] = leg["uuids"][new_sc_id]

            prompts_data["videos"][vk] = base_vcfg

            # Get legacy ref_uuid from refs_state
            leg_ref_uuid = (
                refs_state.get("nv2_luxury", {}).get("ref_image_uuid")
                if "luxury" in leg["src_ref"]
                else refs_state.get("nv2", {}).get("ref_image_uuid")
            ) or "legacy-ref-uuid-00000000000000000000"

            refs_state["variants"][vk] = {
                "ref_image": leg["dst_ref"],
                "ref_image_uuid": leg_ref_uuid,
                "ref_image_path": dst_ref_abs,
                "style": leg["style"],
            }
            state["uploaded_refs"][leg["dst_ref"]] = leg_ref_uuid

            # Create spec_v7.json / spec_v8.json from spec_v2.json / spec_v4.json
            base_spec_path = os.path.join(pdir, f"spec_{base_v}.json")
            if os.path.exists(base_spec_path):
                spec_data = json.load(open(base_spec_path, encoding="utf-8"))
                for idx_s, s_entry in enumerate(spec_data.get("scenes", []), start=1):
                    s_entry["file"] = f"{vk}_s{idx_s}.mp4"
                spec_data["output"] = f"{pid}-{vk}-final-30s.mp4"
                with open(os.path.join(pdir, f"spec_{vk}.json"), "w", encoding="utf-8") as f:
                    json.dump(spec_data, f, ensure_ascii=False, indent=2)
            print(f"[LEGACY] Added {pid} | {vk} ({leg['hook_title']}) with pre-rendered UUIDs")

        with open(prompts_path, "w", encoding="utf-8") as f:
            json.dump(prompts_data, f, ensure_ascii=False, indent=2)
        with open(refs_path, "w", encoding="utf-8") as f:
            json.dump(refs_state, f, ensure_ascii=False, indent=2)
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
