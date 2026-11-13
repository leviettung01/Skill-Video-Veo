# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import uuid
import base64
import random
import shutil
import urllib.parse
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GROK_DIR = r"C:\Users\ADMIN\Desktop\Python\Veo 3 Tool\AutoVeo3Pro_v6\Auto_Veo_3_Pro\Grok"
WS_DIR = r"c:\Users\ADMIN\Desktop\Python\Veo 3 Tool\AutoVeo3Pro_v6\Auto_Veo_3_Pro\Grok\Skill Video Veo"
PROJECTS_DIR = os.path.join(WS_DIR, "projects")
SCRATCH_DIR = r"C:\Users\ADMIN\.gemini\antigravity\brain\d671407a-7a92-4e69-88ae-fef70956018d\scratch"

sys.path.insert(0, GROK_DIR)
sys.path.insert(0, SCRATCH_DIR)
import grok_video_tool as gvt
from google_flow_auth import profile_paths
from playwright.sync_api import sync_playwright
from curl_cffi import requests as cffi_requests
from sync_web_ui_state import sync_web_ui

ALL_PIDS = [
    "1735109997221349342",
    "1738260652434293979",
    "1735811961345574265",
    "1737365863541671120",
    "1738175423853987061",
    "1735424296473888680",
    "1737909342761027082",
]

PROF_NAME = "leviettung04"
shared_dir = gvt._resolve_flow_shared_dir(PROF_NAME)
profile_dir, _ = profile_paths(shared_dir, PROF_NAME)


def call_flow_rpc_cffi(http_session, cookie_hdr, wiz, project_id, rpcid, payload_obj):
    url = (
        f"https://flow.google.com/_/AiSandboxAngularFrontend/data/batchexecute"
        f"?rpcids={rpcid}&source-path=%2Fproject%2F{project_id}"
        f"&bl={urllib.parse.quote(wiz['bl'])}&f.sid={urllib.parse.quote(str(wiz['fsid']))}"
        f"&hl=vi&_reqid={random.randint(100000, 999999)}&rt=c"
    )
    f_req = json.dumps(
        [[[rpcid, json.dumps(payload_obj, separators=(",", ":")), None, "generic"]]],
        separators=(",", ":"),
    )
    body = f"f.req={urllib.parse.quote(f_req)}&at={urllib.parse.quote(wiz['at'])}&"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "https://flow.google.com",
        "Referer": f"https://flow.google.com/project/{project_id}",
        "User-Agent": wiz["ua"],
        "X-Same-Domain": "1",
        "Cookie": cookie_hdr,
    }
    r = http_session.post(url, headers=headers, data=body, timeout=120)
    if r.status_code != 200:
        return False, None, f"HTTP {r.status_code}: {r.text[:300]}"
    return gvt._parse_batchexecute_wrb(r.text, rpcid)


def get_rcap_token(page, action):
    return page.evaluate(
        """async (action) => {
            const fn = window.__realGrecaptchaExecute || window.grecaptcha.enterprise.execute.bind(window.grecaptcha.enterprise);
            return await fn('6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV', {action});
        }""",
        action,
    )


def find_img_url(obj):
    if isinstance(obj, str) and (
        obj.startswith("https://lh3.googleusercontent.com/")
        or obj.startswith("https://flow-content.google/image/")
    ):
        return obj
    if isinstance(obj, list):
        for x in obj:
            r = find_img_url(x)
            if r:
                return r
    return None


def upload_product_ref_image(page, http_session, cookie_hdr, wiz, flow_project_id, img_path, quality=95):
    with Image.open(img_path) as im:
        im_rgb = im.convert("RGB")
        width, height = im_rgb.size
        tmp_jpg = img_path + ".upload_tmp.jpg"
        im_rgb.save(tmp_jpg, format="JPEG", quality=int(quality or 95))
    try:
        raw_bytes = open(tmp_jpg, "rb").read()
    finally:
        if os.path.exists(tmp_jpg):
            try:
                os.remove(tmp_jpg)
            except OSError:
                pass
    b64_str = base64.b64encode(raw_bytes).decode("ascii")
    rcap = get_rcap_token(page, "UPLOAD_IMAGE")
    wf_seed = str(uuid.uuid4())
    media_seed = str(uuid.uuid4())
    U = [None, 22, None, None, None, flow_project_id, None, None, None, None, [rcap, 1]]
    payload_maseq = [
        U,                          # 0 (field 1): request context
        b64_str,                    # 1 (field 2): image bytes (base64)
        "image/jpeg",               # 2 (field 3): mimeType
        True,                       # 3 (field 4): Dg = True
        None,                       # 4 (field 5)
        None,                       # 5 (field 6)
        None,                       # 6 (field 7): crop
        False,                      # 7 (field 8): isHidden
        os.path.basename(img_path), # 8 (field 9): fileName
        None,                       # 9 (field 10): F5
        wf_seed,                    # 10 (field 11): nG (UUID seed string)
        media_seed,                 # 11 (field 12): ZE (UUID seed string)
        None,                       # 12 (field 13)
        [1],                        # 13 (field 14): _.nO() -> [1]
    ]
    ok, inner, err = call_flow_rpc_cffi(http_session, cookie_hdr, wiz, flow_project_id, "maseQ", payload_maseq)
    if not ok or not isinstance(inner, list):
        raise RuntimeError(f"maseQ upload failed for {img_path}: {err} | {inner}")
    media_uuid = inner[0][0]
    if not isinstance(media_uuid, str) or len(media_uuid) < 32:
        raise RuntimeError(f"Unexpected maseQ response for {img_path}: {inner}")
    return media_uuid


def generate_one_ref_image(page, http_session, cookie_hdr, wiz, flow_project_id, char_id, prod_ref_uuids, prompt_str, out_file):
    rcap = get_rcap_token(page, "IMAGE_GENERATION")
    wf_uuid = str(uuid.uuid4())
    m_uuid = str(uuid.uuid4())
    b_uuid = str(uuid.uuid4())
    seed = random.randint(100000, 999999)

    S = [None, 22, None, None, None, flow_project_id, None, None, None, None, [rcap, 1]]
    aa = [[u, None, None, None, 1] for u in prod_ref_uuids]
    f_prompt = [[[prompt_str]]]
    yb = [
        None,           # 0 (field 1)
        None,           # 1 (field 2)
        aa,             # 2 (field 3): referenceImageMediaIds
        seed,           # 3 (field 4): seed
        2,              # 4 (field 5): aspectRatio 2 = 9:16 portrait
        "BELUGA",       # 5 (field 6): Nano Banana 2.1
        None,           # 6 (field 7)
        S,              # 7 (field 8): request context
        f_prompt,       # 8 (field 9): structuredPrompt [[[prompt]]]
        None,           # 9 (field 10): fi (None)
        [[char_id]],    # 10 (field 11): referenceEntityIds (Saved Character!)
        [],             # 11 (field 12): referenceLikenessIds
        wf_uuid,        # 12 (field 13): workflowId
        m_uuid,         # 13 (field 14): mediaId
    ]
    payload_ogi = [None, [yb], True, S, [b_uuid]]
    ok, inner, err = call_flow_rpc_cffi(http_session, cookie_hdr, wiz, flow_project_id, "ogiZ0b", payload_ogi)
    if not ok:
        print(f"  ogiZ0b returned {err}, trying Z9cAtf...", flush=True)
        time.sleep(2.5)
        rcap = get_rcap_token(page, "IMAGE_GENERATION")
        S = [None, 22, None, None, None, flow_project_id, None, None, None, None, [rcap, 1]]
        yb[7] = S
        payload_z9 = [[yb], None, S, [b_uuid]]
        ok, inner, err = call_flow_rpc_cffi(http_session, cookie_hdr, wiz, flow_project_id, "Z9cAtf", payload_z9)

    if not ok or not isinstance(inner, list):
        raise RuntimeError(f"Image generation failed: {err} | {inner}")

    gen_uuid = m_uuid
    try:
        cand = inner[0][0][0]
        if isinstance(cand, str) and len(cand) >= 32:
            gen_uuid = cand
    except Exception:
        pass
    img_url = find_img_url(inner)
    if not img_url:
        for _ in range(25):
            time.sleep(3)
            ok_p, inner_p, _ = call_flow_rpc_cffi(http_session, cookie_hdr, wiz, flow_project_id, "as29s", [gen_uuid, None, [2]])
            if ok_p:
                img_url = find_img_url(inner_p)
                if img_url:
                    break
    if not img_url:
        raise RuntimeError(f"No image URL returned for {gen_uuid}")

    # Step 2: Upsample & download 2K (1536x2752) via SPrCad (0 credits)
    saved_2k = False
    nbytes_2k = 0
    for _try_2k in range(1, 5):
        try:
            rcap_2k = get_rcap_token(page, "IMAGE_GENERATION")
            S_2k = [None, 22, None, None, None, flow_project_id, None, None, None, None, [rcap_2k, 1]]
            ok_s, inner_s, _ = call_flow_rpc_cffi(http_session, cookie_hdr, wiz, flow_project_id, "SPrCad", [gen_uuid, 1, S_2k])
            if ok_s and isinstance(inner_s, list) and len(inner_s) >= 2 and isinstance(inner_s[1], str):
                raw_2k = base64.b64decode(inner_s[1])
                if len(raw_2k) > 50000:
                    with open(out_file, "wb") as f:
                        f.write(raw_2k)
                    saved_2k = True
                    nbytes_2k = len(raw_2k)
                    break
        except Exception:
            pass
        time.sleep(3.0)

    if not saved_2k:
        r_img = http_session.get(
            img_url,
            headers={"Cookie": cookie_hdr, "Referer": "https://flow.google.com/", "User-Agent": wiz["ua"]},
            timeout=60,
            allow_redirects=True,
        )
        if r_img.status_code != 200 or len(r_img.content) < 5000:
            raise RuntimeError(f"Failed to download image: HTTP {r_img.status_code}")
        with open(out_file, "wb") as f:
            f.write(r_img.content)
        try:
            from PIL import ImageFilter
            with Image.open(out_file) as im_fb:
                im_2k = im_fb.convert("RGB").resize((1536, 2752), Image.Resampling.LANCZOS)
                im_2k = im_2k.filter(ImageFilter.UnsharpMask(radius=1.1, percent=115, threshold=2))
                im_2k.save(out_file, format="JPEG", quality=98, subsampling=0)
            nbytes_2k = os.path.getsize(out_file)
        except Exception:
            nbytes_2k = len(r_img.content)

    # Re-upload the downloaded 2K image back to Google Flow via maseQ so video scenes use the 2K asset!
    try:
        uuid_2k = upload_product_ref_image(page, http_session, cookie_hdr, wiz, flow_project_id, out_file, quality=98)
        if uuid_2k:
            gen_uuid = uuid_2k
    except Exception as e_u2k:
        print(f"  [WARN] 2K re-upload warning: {e_u2k}", flush=True)

    return gen_uuid, img_url, nbytes_2k


def main():
    only_pids = sys.argv[1:] if len(sys.argv) > 1 else ALL_PIDS
    force_regen = "--force" in only_pids
    if force_regen:
        only_pids = [p for p in only_pids if p != "--force"]
        if not only_pids:
            only_pids = ALL_PIDS

    with sync_playwright() as pw:
        print("Launching Chrome context for Google Flow...", flush=True)
        _headless_mode = os.environ.get("FLOW_SHOW_BROWSER", "").strip() != "1"
        _p_args = ["--disable-blink-features=AutomationControlled", "--window-size=1280,800", "--mute-audio"]
        context = pw.chromium.launch_persistent_context(
            str(profile_dir),
            channel="chrome",
            headless=_headless_mode,
            args=_p_args,
        )
        context.add_init_script(gvt._FLOW_HIJACK_BYPASS_JS)
        page = context.pages[0] if context.pages else context.new_page()
        first_proj = ""
        try:
            import engine_settings_manager as _esm_g
            first_proj = _esm_g.get_default_flow_project_id(PROF_NAME)
        except Exception:
            first_proj = ""
        first_proj = first_proj or getattr(gvt, "DEFAULT_PROJECT_ID", "") or ""
        target_flow_u = f"https://flow.google.com/project/{first_proj}" if first_proj else "https://flow.google.com/"
        page.goto(target_flow_u, wait_until="domcontentloaded", timeout=45000)
        page.evaluate(gvt._FLOW_HIJACK_BYPASS_JS)
        page.wait_for_function(
            "() => window.WIZ_global_data && window.WIZ_global_data.SNlM0e && window.grecaptcha && window.grecaptcha.enterprise && typeof window.grecaptcha.enterprise.execute === 'function'",
            timeout=35000,
        )
        page.wait_for_timeout(1500)
        wiz = page.evaluate(
            """() => {
                const w = window.WIZ_global_data || {};
                return {
                    at: w.SNlM0e || '',
                    bl: w.cfb2h || 'boq_labs-ai-sandbox-frontend_20261030.00_p2',
                    fsid: w.FdrFJe || '',
                    ua: navigator.userAgent,
                };
            }"""
        )
        live_cookies = context.cookies(["https://flow.google.com", "https://google.com", "https://accounts.google.com"])
        cookie_hdr = "; ".join(f"{c['name']}={c['value']}" for c in live_cookies)
        http_session = cffi_requests.Session(impersonate="chrome131")
        print(f"Connected to Google Flow! Live cookies={len(live_cookies)}", flush=True)

        for pid in only_pids:
            pdir = os.path.join(PROJECTS_DIR, pid)
            prompts_data = json.load(open(os.path.join(pdir, "prompts.json"), encoding="utf-8"))
            state_file = os.path.join(pdir, "flow_refs_state.json")
            refs_state = {}
            if os.path.exists(state_file):
                try:
                    refs_state = json.load(open(state_file, encoding="utf-8"))
                except Exception:
                    refs_state = {}

            # Pre-seed known uploaded product refs for 1738260652434293979 if not in state
            if pid == "1738260652434293979":
                refs_state.setdefault("uploaded_prod_refs", {})
                refs_state["uploaded_prod_refs"].setdefault("nv1", ["7b712134-3d52-4b85-8a6c-35ba2aa22bfb"])
                refs_state["uploaded_prod_refs"].setdefault("nv2", ["945b3e4d-86ce-427a-958a-cae8b5679271"])

            refs_state.setdefault("uploaded_prod_refs", {})
            primary_ref_rel = prompts_data["primary_product_refs"][0]
            primary_ref_abs = os.path.join(pdir, "product_images", primary_ref_rel)

            for vkey, char_key in [("v1", "nv1"), ("v2", "nv2")]:
                vcfg = prompts_data["videos"][vkey]
                flow_proj_id = vcfg["project_id"]
                char_id = vcfg["character_id"]
                voice_id = vcfg["voice_id"]
                out_img_abs = os.path.join(pdir, vcfg["ref_image"])

                # For 1738260652434293979, we want to regenerate v1/v2 if they were belt-only
                already_updated_giftbox = refs_state.get(char_key, {}).get("is_factory_giftbox_v2", False) if pid == "1738260652434293979" else True
                if (
                    not force_regen
                    and already_updated_giftbox
                    and char_key in refs_state
                    and refs_state[char_key].get("ref_image_uuid")
                    and os.path.exists(out_img_abs)
                    and os.path.getsize(out_img_abs) > 10000
                ):
                    print(f"[{pid} | {char_key}] Reference image already exists ({os.path.getsize(out_img_abs)//1024} KB), skipping.", flush=True)
                    continue

                # 1. Ensure product reference image is uploaded to this character's Flow project
                prod_uuids = refs_state["uploaded_prod_refs"].get(char_key, [])
                if not prod_uuids:
                    print(f"[{pid} | {char_key}] Uploading product ref {primary_ref_rel} to Flow project {flow_proj_id}...", flush=True)
                    u_id = upload_product_ref_image(page, http_session, cookie_hdr, wiz, flow_proj_id, primary_ref_abs)
                    prod_uuids = [u_id]
                    refs_state["uploaded_prod_refs"][char_key] = prod_uuids
                    with open(state_file, "w", encoding="utf-8") as f:
                        json.dump(refs_state, f, ensure_ascii=False, indent=2)
                    print(f"[{pid} | {char_key}] Uploaded product ref -> media_uuid={u_id}", flush=True)
                    time.sleep(15.0)

                # 2. Generate 9:16 Factory + Product + Character reference image via BELUGA (Nano Banana 2.1)
                print(f"[{pid} | {char_key}] Generating 9:16 Factory reference image (Nano Banana 2.1)...", flush=True)
                gen_uuid, img_url, img_bytes = generate_one_ref_image(
                    page,
                    http_session,
                    cookie_hdr,
                    wiz,
                    flow_proj_id,
                    char_id,
                    prod_uuids,
                    vcfg["ref_image_prompt"],
                    out_img_abs,
                )
                refs_dir = os.path.join(pdir, "refs")
                os.makedirs(refs_dir, exist_ok=True)
                shutil.copy2(out_img_abs, os.path.join(refs_dir, os.path.basename(out_img_abs)))

                refs_state[char_key] = {
                    "project_id": flow_proj_id,
                    "character_id": char_id,
                    "voice_id": voice_id,
                    "prod_ref_uuids": prod_uuids,
                    "ref_image_uuid": gen_uuid,
                    "ref_image_path": out_img_abs,
                    "ref_image_url": img_url,
                    "is_factory_giftbox_v2": True,
                }
                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(refs_state, f, ensure_ascii=False, indent=2)

                # If 1738260652434293979 v1/v2 ref image was updated to gift box, remove old belt-only v1_s1..s3 / v2_s1..s3 so they re-render with the gift box
                if pid == "1738260652434293979" and not already_updated_giftbox:
                    for s_idx in range(1, 4):
                        old_mp4 = os.path.join(pdir, f"{vkey}_s{s_idx}.mp4")
                        if os.path.exists(old_mp4):
                            os.remove(old_mp4)
                    old_final = os.path.join(pdir, f"{pid}-{vkey}-final-30s.mp4")
                    if os.path.exists(old_final):
                        os.remove(old_final)

                print(f"[{pid} | {char_key}] Saved {out_img_abs} ({img_bytes//1024} KB) | media_uuid={gen_uuid}", flush=True)
                sync_web_ui()
                time.sleep(15.0)

        context.close()
    print("\nAll 7 products' NV1 and NV2 9:16 Factory reference images generated!", flush=True)


if __name__ == "__main__":
    main()
