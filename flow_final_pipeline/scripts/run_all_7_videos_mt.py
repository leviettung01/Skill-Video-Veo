# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import uuid
import base64
import random
import shutil
import threading
import urllib.parse
import subprocess
import concurrent.futures
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
WS_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, "..", ".."))
GROK_DIR = WS_DIR
PROJECTS_DIR = os.path.join(WS_DIR, "projects")
BUILD_FINAL_SCRIPT = os.path.join(SCRIPTS_DIR, "build_final.py")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
if WS_DIR not in sys.path:
    sys.path.insert(0, WS_DIR)
import grok_video_tool as gvt
from google_flow_auth import profile_paths
from playwright.sync_api import sync_playwright
from curl_cffi import requests as cffi_requests
from sync_web_ui_state import sync_web_ui, get_final_video_filename

try:
    import engine_settings_manager as _esm
except Exception:
    _esm = None

ALL_PIDS = [
    "1738086213622335480",
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
profile_dir, cookies_file = profile_paths(shared_dir, PROF_NAME)

STATE_LOCK = threading.Lock()
UI_SYNC_LOCK = threading.Lock()
FFMPEG_SUBMITTED = set()


def safe_sync_ui():
    with UI_SYNC_LOCK:
        try:
            sync_web_ui()
        except Exception as e:
            print(f"[UI-SYNC WARN] {e}", flush=True)


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
    r = http_session.post(url, headers=headers, data=body, timeout=90)
    if r.status_code != 200:
        return False, None, f"HTTP {r.status_code}: {r.text[:250]}"
    return gvt._parse_batchexecute_wrb(r.text, rpcid)


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


def upload_single_product_ref_in_page(page, wiz, project_id, img_path, quality=95):
    """Upload ONLY 1 single-variant product or 2K reference image via maseQ directly inside the clean Chrome context."""
    with Image.open(img_path) as im:
        im_rgb = im.convert("RGB")
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
    rcap = page.evaluate(
        """async () => {
            const fn = window.__realGrecaptchaExecute || window.grecaptcha.enterprise.execute.bind(window.grecaptcha.enterprise);
            return await fn('6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV', {action: 'UPLOAD_IMAGE'});
        }"""
    )
    wf_seed = str(uuid.uuid4())
    media_seed = str(uuid.uuid4())
    U = [None, 22, None, None, None, project_id, None, None, None, None, [rcap, 1]]
    payload_maseq = [
        U,
        b64_str,
        "image/jpeg",
        True,
        None,
        None,
        None,
        False,
        os.path.basename(img_path),
        None,
        wf_seed,
        media_seed,
        None,
        [1],
    ]
    f_req_str = json.dumps(
        [[["maseQ", json.dumps(payload_maseq, separators=(",", ":")), None, "generic"]]],
        separators=(",", ":"),
    )
    reqid = random.randint(100000, 999999)
    resp_obj = page.evaluate(
        """async ({projectId, bl, fsid, reqid, fReq, at}) => {
            const sp = `/project/${projectId}`;
            const url = `/_/AiSandboxAngularFrontend/data/batchexecute?rpcids=maseQ&source-path=${encodeURIComponent(sp)}&bl=${encodeURIComponent(bl)}&f.sid=${encodeURIComponent(fsid)}&hl=vi&_reqid=${reqid}&rt=c`;
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
        return False, None, f"maseQ HTTP {(resp_obj or {}).get('status')}"
    ok_u, inner_u, err_u = gvt._parse_batchexecute_wrb(resp_obj.get("text", ""), "maseQ")
    if not ok_u or not isinstance(inner_u, list):
        return False, None, f"maseQ {err_u}"
    media_uuid = inner_u[0][0]
    if not isinstance(media_uuid, str) or len(media_uuid) < 32:
        return False, None, f"Unexpected maseQ {inner_u}"
    return True, media_uuid, None


def upsample_image_2k_in_page(page, wiz, project_id, img_uuid, out_file):
    """Upsample & download a Flow image at 2K resolution (1536x2752) via SPrCad (ts=1, 0 credits)."""
    rcap = page.evaluate(
        """async () => {
            const fn = window.__realGrecaptchaExecute || window.grecaptcha.enterprise.execute.bind(window.grecaptcha.enterprise);
            return await fn('6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV', {action: 'IMAGE_GENERATION'});
        }"""
    )
    S = [None, 22, None, None, None, project_id, None, None, None, None, [rcap, 1]]
    payload_spr = [img_uuid, 1, S]
    f_req_str = json.dumps(
        [[["SPrCad", json.dumps(payload_spr, separators=(",", ":")), None, "generic"]]],
        separators=(",", ":"),
    )
    reqid = random.randint(100000, 999999)
    resp_obj = page.evaluate(
        """async ({projectId, bl, fsid, reqid, fReq, at}) => {
            const sp = `/project/${projectId}`;
            const url = `/_/AiSandboxAngularFrontend/data/batchexecute?rpcids=SPrCad&source-path=${encodeURIComponent(sp)}&bl=${encodeURIComponent(bl)}&f.sid=${encodeURIComponent(fsid)}&hl=vi&_reqid=${reqid}&rt=c`;
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
        return False, 0, f"SPrCad HTTP {(resp_obj or {}).get('status')}"
    ok_s, inner_s, err_s = gvt._parse_batchexecute_wrb(resp_obj.get("text", ""), "SPrCad")
    if not ok_s or not isinstance(inner_s, list) or len(inner_s) < 2 or not isinstance(inner_s[1], str):
        return False, 0, f"SPrCad {err_s}"
    raw_2k = base64.b64decode(inner_s[1])
    if len(raw_2k) < 50000:
        return False, 0, f"SPrCad too small ({len(raw_2k)} B)"
    with open(out_file, "wb") as f:
        f.write(raw_2k)
    refs_dir = os.path.join(os.path.dirname(out_file), "refs")
    os.makedirs(refs_dir, exist_ok=True)
    shutil.copy2(out_file, os.path.join(refs_dir, os.path.basename(out_file)))
    return True, len(raw_2k), None


def generate_variant_ref_image_in_page(page, wiz, cookie_hdr, dl_headers, task):
    """Generate a unique 9:16 reference image or AI Thumbnail (ogiZ0b / BELUGA) and download it at 2K (1536x2752) via SPrCad."""
    pid = task["pid"]
    v_key = task["v_key"]
    project_id = task["project_id"]
    char_id = task["char_id"]
    max_refs = 4 if task.get("allow_multi_refs") else 1
    prod_uuids = [u for u in (task.get("prod_uuids") or []) if u][:max_refs]
    prompt_str = task["prompt_str"]
    out_file = task["out_file"]

    rcap = page.evaluate(
        """async () => {
            const fn = window.__realGrecaptchaExecute || window.grecaptcha.enterprise.execute.bind(window.grecaptcha.enterprise);
            return await fn('6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV', {action: 'IMAGE_GENERATION'});
        }"""
    )
    wf_uuid = str(uuid.uuid4())
    m_uuid = str(uuid.uuid4())
    b_uuid = str(uuid.uuid4())
    seed = random.randint(100000, 999999)

    S = [None, 22, None, None, None, project_id, None, None, None, None, [rcap, 1]]
    aa = [[u, None, None, None, 1] for u in prod_uuids]
    f_prompt = [[[prompt_str]]]
    yb = [
        None,
        None,
        aa,
        seed,
        2,          # 9:16 portrait
        "BELUGA",   # Nano Banana 2.1
        None,
        S,
        f_prompt,
        None,
        [[char_id]] if char_id else [],
        [],
        wf_uuid,
        m_uuid,
    ]
    payload_ogi = [None, [yb], True, S, [b_uuid]]
    f_req_str = json.dumps(
        [[["ogiZ0b", json.dumps(payload_ogi, separators=(",", ":")), None, "generic"]]],
        separators=(",", ":"),
    )
    reqid = random.randint(100000, 999999)
    resp_obj = page.evaluate(
        """async ({projectId, bl, fsid, reqid, fReq, at}) => {
            const sp = `/project/${projectId}`;
            const url = `/_/AiSandboxAngularFrontend/data/batchexecute?rpcids=ogiZ0b&source-path=${encodeURIComponent(sp)}&bl=${encodeURIComponent(bl)}&f.sid=${encodeURIComponent(fsid)}&hl=vi&_reqid=${reqid}&rt=c`;
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
        return False, None, f"HTTP {(resp_obj or {}).get('status')}"
    ok_i, inner_i, err_i = gvt._parse_batchexecute_wrb(resp_obj.get("text", ""), "ogiZ0b")
    if not ok_i or not isinstance(inner_i, list):
        return False, None, f"{err_i}"

    gen_uuid = m_uuid
    try:
        cand = inner_i[0][0][0]
        if isinstance(cand, str) and len(cand) >= 32:
            gen_uuid = cand
    except Exception:
        pass

    img_url = find_img_url(inner_i)
    with cffi_requests.Session(impersonate="chrome131") as s:
        if not img_url:
            for _ in range(15):
                time.sleep(2.5)
                ok_p, inner_p, _ = call_flow_rpc_cffi(s, cookie_hdr, wiz, project_id, "as29s", [gen_uuid, None, [2]])
                if ok_p:
                    img_url = find_img_url(inner_p)
                    if img_url:
                        break
        if not img_url:
            return False, None, f"No image URL for {gen_uuid}"

        # Step 2 (Standard Pipeline): Upsample & download at 2K (1536x2752) via SPrCad (0 credits) with up to 4 retries
        ok_2k, nbytes_2k, err_2k = False, 0, "not_run"
        for attempt_2k in range(1, 5):
            ok_2k, nbytes_2k, err_2k = upsample_image_2k_in_page(page, wiz, project_id, gen_uuid, out_file)
            if ok_2k and nbytes_2k > 50000:
                break
            if attempt_2k < 4:
                time.sleep(3.0)

        if not (ok_2k and nbytes_2k > 50000):
            print(f"   [2K-FALLBACK {pid} | {v_key}] SPrCad returned {err_2k} after 4 tries, downloading & upscaling to 2K (1536x2752)...", flush=True)
            r_img = s.get(img_url, headers=dl_headers, timeout=60, allow_redirects=True)
            if r_img.status_code != 200 or len(r_img.content) < 5000:
                return False, None, f"Download HTTP {r_img.status_code}"
            with open(out_file, "wb") as f:
                f.write(r_img.content)
            try:
                from PIL import ImageFilter
                with Image.open(out_file) as im_fb:
                    im_2k = im_fb.convert("RGB").resize((1536, 2752), Image.Resampling.LANCZOS)
                    im_2k = im_2k.filter(ImageFilter.UnsharpMask(radius=1.1, percent=115, threshold=2))
                    im_2k.save(out_file, format="JPEG", quality=98, subsampling=0)
                nbytes_2k = os.path.getsize(out_file)
            except Exception as e_up_fb:
                print(f"   [WARN {pid} | {v_key}] Local 2K resize fallback warning: {e_up_fb}", flush=True)
                nbytes_2k = len(r_img.content)

    refs_dir = os.path.join(os.path.dirname(out_file), "refs")
    os.makedirs(refs_dir, exist_ok=True)
    shutil.copy2(out_file, os.path.join(refs_dir, os.path.basename(out_file)))

    # Step 2b (Standard Pipeline): Upload the downloaded 2K (1536x2752) Ref Image back to Google Flow via maseQ
    # so all 3 video scenes use the true 2K uploaded Reference Image + Product Image + Voice!
    if not task.get("skip_reupload_2k"):
        uploaded_2k_ok = False
        for u2k_try in range(1, 4):
            try:
                ok_u2k, uuid_2k, err_u2k = upload_single_product_ref_in_page(page, wiz, project_id, out_file, quality=98)
                if ok_u2k and uuid_2k:
                    gen_uuid = uuid_2k
                    uploaded_2k_ok = True
                    break
            except Exception as e_u2k:
                err_u2k = str(e_u2k)
            if u2k_try < 3:
                time.sleep(2.0)
        if not uploaded_2k_ok:
            print(f"   [WARN {pid} | {v_key}] 2K re-upload fallback to gen_uuid", flush=True)

    print(f"🖼️ [{pid} | {v_key.upper()}] Generated, downloaded 2K (1536x2752) & re-uploaded 2K Ref Image {os.path.basename(out_file)} ({nbytes_2k//1024} KB) -> uuid_2k={gen_uuid}", flush=True)
    return True, gen_uuid, None


def submit_scene_in_page(page, wiz, task):
    """Mint reCAPTCHA Enterprise token AND execute MZZa6b fetch with ALL 3 ingredients: [2K ref_uuid, prod_uuid] + [voice_id]."""
    pid = task["pid"]
    sc = task["sc"]
    sc_id = sc["id"]
    project_id = task["project_id"]
    ref_uuid = task["ref_uuid"]
    prod_uuid = task.get("prod_uuid")
    voice_id = task["voice_id"]
    worker_prof = task.get("worker_profile") or ""
    if voice_id and worker_prof:
        try:
            import character_library_manager as _clm_mt
            voice_id = _clm_mt.resolve_voice_id_for_account(voice_id, worker_prof)
        except Exception:
            pass

    if not prod_uuid or prod_uuid == ref_uuid:
        return False, None, "Missing prod_uuid (Standard workflow requires [2K Ref Image + Product Image + Voice])"

    rcap = page.evaluate(
        """async () => {
            const fn = window.__realGrecaptchaExecute || window.grecaptcha.enterprise.execute.bind(window.grecaptcha.enterprise);
            return await fn('6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV', {action: 'VIDEO_GENERATION'});
        }"""
    )
    wf_uuid = str(uuid.uuid4())
    m_uuid = str(uuid.uuid4())
    b_uuid = str(uuid.uuid4())
    h_prompt = [None, None, [[[sc["prompt"]]]]]
    l_item = [None, None, None, None, m_uuid, wf_uuid]
    x_batch = [b_uuid, 1]
    dur_sec = int(sc.get("duration_sec") or task.get("scene_duration_sec") or 10)
    model_key = sc.get("model_key") or ("abra_r2v_6s" if dur_sec <= 6 else ("abra_r2v_8s" if dur_sec <= 8 else "abra_r2v_10s"))
    aspect_int = 1  # 9:16 portrait
    # Standard 5-Step Google Flow Pipeline:
    # All 3 scenes (s1, s2, s3) ALWAYS pass the exact same 3 Reference Ingredients:
    #   1) [None, ref_uuid]  -> 2K Reference Image of Character holding Product (1536x2752)
    #   2) [None, prod_uuid] -> Product Reference Image (prod_1.jpg)
    #   3) [[voice_id]]      -> Character Voice
    ref_list = [[None, ref_uuid], [None, prod_uuid]]
    voice_list = [[voice_id]] if voice_id else []
    item_g = [
        h_prompt,
        ref_list,
        model_key,
        aspect_int,
        None,
        l_item,
        None,
        voice_list,
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
        return False, None, f"HTTP {(resp_obj or {}).get('status')}"
    ok_v, inner_v, err_v = gvt._parse_batchexecute_wrb(resp_obj.get("text", ""), "MZZa6b")
    if not ok_v or not isinstance(inner_v, list):
        return False, None, f"{err_v}"

    ret_uuid = m_uuid
    try:
        if len(inner_v) > 3 and isinstance(inner_v[3], list) and inner_v[3]:
            cand_u = inner_v[3][0][0]
            if isinstance(cand_u, str) and len(cand_u) >= 32:
                ret_uuid = cand_u
    except Exception:
        pass
    credits_left = inner_v[1] if len(inner_v) > 1 and isinstance(inner_v[1], int) else None
    prod_tag = f"+prod={prod_uuid[:8]}" if prod_uuid else ""
    print(f"🚀 [{pid} | {sc_id}] Submitted MZZa6b (ref={ref_uuid[:8]}{prod_tag}) -> media_uuid={ret_uuid} (Credits: {credits_left})", flush=True)
    return True, ret_uuid, None


def submit_upsample_1080p_in_page(page, wiz, task):
    """Submit 1080p video upsample via p0UkFb (veo_3_1_upsampler_1080p, resolution=2, 0 credits)."""
    pid = task["pid"]
    sc_id = task["sc"]["id"]
    project_id = task["project_id"]
    base_video_uuid = task["base_video_uuid"]

    rcap = page.evaluate(
        """async () => {
            const fn = window.__realGrecaptchaExecute || window.grecaptcha.enterprise.execute.bind(window.grecaptcha.enterprise);
            return await fn('6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV', {action: 'VIDEO_GENERATION'});
        }"""
    )
    wf_uuid = str(uuid.uuid4())
    m_uuid = str(uuid.uuid4())
    b_uuid = str(uuid.uuid4())
    l_item = [None, None, None, None, m_uuid, wf_uuid]
    item_x = [None] * 32
    item_x[0] = [None, base_video_uuid]          # field 1: baseVideoId
    item_x[2] = 1                                # field 3: aspectRatio (1 = 9:16 portrait)
    item_x[4] = l_item                           # field 5: metadata / destination
    item_x[6] = 2                                # field 7: resolution (2 = 1080p)
    item_x[31] = "veo_3_1_upsampler_1080p"       # field 32: videoModelKey (0 credits)

    k_ctx = [None, 22, None, None, None, project_id, None, None, None, None, [rcap, 1]]
    payload_upv = [[item_x], k_ctx, [b_uuid, 1]]
    f_req_str = json.dumps(
        [[["p0UkFb", json.dumps(payload_upv, separators=(",", ":")), None, "generic"]]],
        separators=(",", ":"),
    )
    reqid = random.randint(100000, 999999)
    resp_obj = page.evaluate(
        """async ({projectId, bl, fsid, reqid, fReq, at}) => {
            const sp = `/project/${projectId}`;
            const url = `/_/AiSandboxAngularFrontend/data/batchexecute?rpcids=p0UkFb&source-path=${encodeURIComponent(sp)}&bl=${encodeURIComponent(bl)}&f.sid=${encodeURIComponent(fsid)}&hl=vi&_reqid=${reqid}&rt=c`;
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
        return False, None, f"p0UkFb HTTP {(resp_obj or {}).get('status')}"
    ok_v, inner_v, err_v = gvt._parse_batchexecute_wrb(resp_obj.get("text", ""), "p0UkFb")
    if not ok_v or not isinstance(inner_v, list):
        return False, None, f"p0UkFb {err_v}"

    upsampled_uuid = f"{base_video_uuid}_upsampled"
    try:
        if len(inner_v) > 3 and isinstance(inner_v[3], list) and inner_v[3]:
            cand_u = inner_v[3][0][0]
            if isinstance(cand_u, str) and len(cand_u) >= 32:
                upsampled_uuid = cand_u
    except Exception:
        pass
    print(f"✨ [{pid} | {sc_id}] Submitted 1080p Upsample p0UkFb -> {upsampled_uuid} (0 credits)", flush=True)
    return True, upsampled_uuid, None


def poll_and_download_one(default_cookie_hdr, default_wiz, default_dl_headers, task):
    cookie_hdr = task.get("cookie_hdr") or default_cookie_hdr
    wiz = task.get("wiz") or default_wiz
    dl_headers = task.get("dl_headers") or default_dl_headers
    uid = task["media_uuid"]
    project_id = task["project_id"]
    out_mp4 = task["out_mp4"]
    stage = task.get("stage", "upsample_1080p" if str(uid).endswith("_upsampled") else "base_720p")

    with cffi_requests.Session(impersonate="chrome131") as s:
        ok_p, inner_p, err_p = call_flow_rpc_cffi(s, cookie_hdr, wiz, project_id, "as29s", [uid, None, [2]])
        if not ok_p or not isinstance(inner_p, list):
            return f"rpc_err:{str(err_p)[:25]}", None

        v_urls = gvt._find_signed_flow_urls(inner_p, "https://flow-content.google/video/")
        if not v_urls:
            v_urls = gvt._find_signed_flow_urls(inner_p, "https://storage.googleapis.com/")
        if v_urls:
            v_url = v_urls[0]
            r_dl = s.get(v_url, headers=dl_headers, timeout=120, allow_redirects=True)
            if r_dl.status_code != 200 or len(r_dl.content) <= 10000:
                r_dl = s.get(
                    v_url,
                    headers={"Referer": "https://flow.google.com/", "User-Agent": wiz["ua"]},
                    timeout=120,
                    allow_redirects=True,
                )
            if r_dl.status_code == 200 and len(r_dl.content) > 10000:
                if stage == "base_720p":
                    # Save 720p backup in case 1080p upsample fails, then transition to 1080p upsample
                    with open(out_mp4 + ".720p.tmp", "wb") as f:
                        f.write(r_dl.content)
                    return "ready_for_1080p", len(r_dl.content)
                else:
                    with open(out_mp4, "wb") as f:
                        f.write(r_dl.content)
                    if os.path.exists(out_mp4 + ".720p.tmp"):
                        try:
                            os.remove(out_mp4 + ".720p.tmp")
                        except OSError:
                            pass
                    return "done", len(r_dl.content)
            return f"dl_err:{r_dl.status_code}", None

    status_code = None
    try:
        status_code = inner_p[0][0][3]
    except Exception:
        pass
    if status_code is None:
        try:
            status_code = inner_p[5][7][0]
        except Exception:
            pass
    if status_code in (3, 4, 5, 7):
        return f"failed_{status_code}", None
    raw_s = json.dumps(inner_p, ensure_ascii=False)
    if "PUBLIC_ERROR" in raw_s or "ERROR" in raw_s.upper() or inner_p == [None] or inner_p == []:
        print(f"   [POLL-ERR {uid[:8]}] {raw_s[:220]}", flush=True)
        return "failed_err", None
    return f"running_{status_code}", None


def run_ffmpeg_build(pid, pdir, v_key):
    spec_path = os.path.join(pdir, f"spec_{v_key}.json")
    print(f"🎞️ [FFMPEG-THREAD | {pid} | {v_key.upper()}] Building Final 30s 1080p video...", flush=True)
    res = subprocess.run(
        [sys.executable, BUILD_FINAL_SCRIPT, spec_path],
        cwd=pdir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if res.returncode != 0:
        print(f"❌ [FFMPEG-THREAD | {pid} | {v_key.upper()}] Failed: {res.stderr[:300]}", flush=True)
        return False
    print(f"✅ [FFMPEG-THREAD | {pid} | {v_key.upper()}] {res.stdout.strip()}", flush=True)
    safe_sync_ui()
    return True


def check_and_queue_ffmpeg(ffmpeg_pool, ffmpeg_futures, pid, pdir, v_key, scenes):
    key = f"{pid}_{v_key}"
    with STATE_LOCK:
        if key in FFMPEG_SUBMITTED:
            return
        final_mp4 = os.path.join(WS_DIR, "final_videos", get_final_video_filename(pid, v_key))
        if os.path.exists(final_mp4) and os.path.getsize(final_mp4) > 50000:
            FFMPEG_SUBMITTED.add(key)
            return
        all_ready = all(
            os.path.exists(os.path.join(pdir, sc["file"]))
            and os.path.getsize(os.path.join(pdir, sc["file"])) > 50000
            for sc in scenes
        )
        if not all_ready:
            return
        FFMPEG_SUBMITTED.add(key)
    fut = ffmpeg_pool.submit(run_ffmpeg_build, pid, pdir, v_key)
    ffmpeg_futures.append(fut)


def save_prod_state(pdir, state, refs_state=None):
    with STATE_LOCK:
        state_path = os.path.join(pdir, "flow_state.json")
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        if refs_state is not None:
            refs_path = os.path.join(pdir, "flow_refs_state.json")
            with open(refs_path, "w", encoding="utf-8") as f:
                json.dump(refs_state, f, ensure_ascii=False, indent=2)


def is_ref_image_2k(img_path):
    try:
        with Image.open(img_path) as im:
            w, h = im.size
            return w >= 1200 and h >= 2000
    except Exception:
        return False


def main():
    only_pids = sys.argv[1:] if len(sys.argv) > 1 else ALL_PIDS
    cfg = _esm.load_engine_settings() if _esm is not None else {}
    MAX_INFLIGHT = int(cfg.get("max_total_inflight") or 20)
    SUBMIT_DELAY_SEC = float(cfg.get("submit_delay_sec") or 12.0)
    FFMPEG_WORKERS = int(cfg.get("ffmpeg_render_workers") or 4)
    multi_acc_enabled = bool(cfg.get("multi_account_enabled", True))
    detected_accs = cfg.get("detected_flow_accounts") or [{"name": f"Google_{PROF_NAME}", "profile_name": PROF_NAME, "active": True}]
    active_flow_accs = [a for a in detected_accs if a.get("active", True)] if multi_acc_enabled else detected_accs[:1]
    if not active_flow_accs:
        active_flow_accs = [{"name": f"Google_{PROF_NAME}", "profile_name": PROF_NAME, "active": True}]

    print(
        f"⚙️ [ENGINE CONFIG] FFmpeg Workers={FFMPEG_WORKERS} | Max Inflight={MAX_INFLIGHT} | "
        f"Submit Delay={SUBMIT_DELAY_SEC}s | Active Flow Accounts={len(active_flow_accs)} ({', '.join(a['profile_name'] for a in active_flow_accs)})",
        flush=True,
    )

    ffmpeg_pool = concurrent.futures.ThreadPoolExecutor(max_workers=FFMPEG_WORKERS)
    poll_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max(15, MAX_INFLIGHT))
    ffmpeg_futures = []

    pending_queue = []
    inflight_tasks = {}
    prod_meta = {}

    def write_pipeline_heartbeat(step_text: str, is_running: bool = True):
        now_s = time.strftime("%H:%M:%S")
        active_list = [
            {
                "key": tk.get("key"),
                "pid": tk.get("pid"),
                "v_key": tk.get("v_key"),
                "sc_id": (tk.get("sc") or {}).get("id", tk.get("v_key")),
                "stage": tk.get("stage", tk.get("type")),
                "account": tk.get("account_name", PROF_NAME),
                "elapsed_sec": int(time.time() - (tk.get("submitted_at") or time.time())),
            }
            for tk in list(inflight_tasks.values())
        ]
        for p_id in only_pids:
            p_dir = os.path.join(PROJECTS_DIR, p_id)
            if not os.path.isdir(p_dir):
                continue
            p_inflight = [x for x in active_list if x["pid"] == p_id]
            p_queued = [q for q in pending_queue if q.get("pid") == p_id]
            st_obj = {
                "pid": p_id,
                "pid_os": os.getpid(),
                "is_running": is_running,
                "inflight_count": len(p_inflight),
                "queued_count": len(p_queued),
                "active_tasks": p_inflight,
                "accounts_active": [a["profile_name"] for a in active_flow_accs],
                "ffmpeg_workers": FFMPEG_WORKERS,
                "current_step_text": step_text,
                "updated_at": now_s,
            }
            try:
                with open(os.path.join(p_dir, "pipeline_status.json"), "w", encoding="utf-8") as sf:
                    json.dump(st_obj, sf, ensure_ascii=False, indent=2)
            except Exception:
                pass

    for pid in only_pids:
        pdir = os.path.join(PROJECTS_DIR, pid)
        marker_clean = os.path.join(pdir, ".cleaned_new")
        if os.path.exists(marker_clean):
            try:
                os.remove(marker_clean)
            except OSError:
                pass
        prompts_data = json.load(open(os.path.join(pdir, "prompts.json"), encoding="utf-8"))
        refs_path = os.path.join(pdir, "flow_refs_state.json")
        refs_state = json.load(open(refs_path, encoding="utf-8")) if os.path.exists(refs_path) else {"uploaded_prod_refs": {}, "variants": {}}
        refs_state.setdefault("variants", {})
        refs_state.setdefault("uploaded_prod_refs", {})
        state_path = os.path.join(pdir, "flow_state.json")
        state = {"uploaded_refs": {}, "scene_uuids": {}}
        if os.path.exists(state_path):
            try:
                state = json.load(open(state_path, encoding="utf-8"))
            except Exception:
                pass
        prod_meta[pid] = (pdir, prompts_data, state, refs_state)

        for v_key in list(prompts_data.get("videos", {}).keys()):
            if v_key not in prompts_data.get("videos", {}):
                continue
            v_info = prompts_data["videos"][v_key]
            char_key = v_info.get("character", "nv1")
            ck_low = (char_key or "").lower()
            m_nv = __import__("re").search(r"(nv\d+)", ck_low) or __import__("re").search(r"(nv\d+)", v_key.lower())
            base_char = m_nv.group(1) if m_nv else (ck_low if ck_low else "nv1")
            tpl_id_low = str(v_info.get("template_id") or prompts_data.get("template_id") or "").lower()
            is_pov_only = bool(v_info.get("pov_only") or "pov" in tpl_id_low or tpl_id_low == "do_an_vat")
            scene_dur_sec = int(v_info.get("scene_duration_sec") or prompts_data.get("scene_duration_sec") or 10)
            project_id = v_info.get("project_id") or "932bc2a1-07ea-4199-b147-80ab0018d41c"
            char_id = v_info.get("character_id") or ""
            voice_id = v_info.get("voice_id") or ""
            ref_img_rel = v_info["ref_image"]  # e.g. "v2-refimg.jpg"
            ref_img_abs = os.path.join(pdir, ref_img_rel)

            prod_uuids = refs_state.get("uploaded_prod_refs", {}).get(base_char) or refs_state.get(base_char, {}).get("prod_ref_uuids", [])
            if prod_uuids and not refs_state["uploaded_prod_refs"].get(base_char):
                refs_state["uploaded_prod_refs"][base_char] = prod_uuids[:1]
            primary_rel = (v_info.get("primary_product_refs") or prompts_data.get("primary_product_refs") or ["prod_1.jpg"])[0]
            primary_prod_img = os.path.join(pdir, "product_images", primary_rel)

            var_entry = refs_state["variants"].get(v_key, {})
            ref_uuid = var_entry.get("ref_image_uuid") or state.get("uploaded_refs", {}).get(ref_img_rel)
            has_unique_ref = bool(ref_uuid and os.path.exists(ref_img_abs) and os.path.getsize(ref_img_abs) > 10000)

            scenes = v_info["scenes"]
            char_v_code = v_info.get("char_v") or get_final_video_filename(pid, v_key).replace(f"{pid}_", "").replace(".mp4", "")
            out_thumb_proj = os.path.join(pdir, "thumbnails", f"{pid}_{char_v_code}_thumb.jpg")
            need_thumb = bool(
                cfg.get("auto_generate_thumbnail", True)
                and _esm is not None
                and not (os.path.exists(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 10000)
            )
            if has_unique_ref:
                state["uploaded_refs"][ref_img_rel] = ref_uuid
                save_prod_state(pdir, state, refs_state)
                needs_2k_upgrade = not is_ref_image_2k(ref_img_abs)
                if needs_2k_upgrade:
                    pending_queue.insert(0, {
                        "type": "upsample_ref_2k",
                        "key": f"{pid}_{v_key}_2k",
                        "pid": pid,
                        "pdir": pdir,
                        "v_key": v_key,
                        "project_id": project_id,
                        "ref_uuid": ref_uuid,
                        "out_file": ref_img_abs,
                        "retries": 0,
                    })
                if need_thumb:
                    pending_queue.append({
                        "type": "thumb_img",
                        "key": f"{pid}_{v_key}_thumb",
                        "pid": pid,
                        "pdir": pdir,
                        "v_key": v_key,
                        "char_v": char_v_code,
                        "base_char": base_char,
                        "primary_prod_img": primary_prod_img,
                        "project_id": project_id,
                        "char_id": char_id,
                        "ref_uuid": ref_uuid,
                        "prod_uuid": prod_uuids[0] if prod_uuids else None,
                        "out_file": out_thumb_proj,
                        "retries": 0,
                    })
                check_and_queue_ffmpeg(ffmpeg_pool, ffmpeg_futures, pid, pdir, v_key, scenes)
            else:
                needs_2k_upgrade = False
                # Queue a ref_img generation task for this variant!
                pending_queue.append({
                    "type": "ref_img",
                    "key": f"{pid}_{v_key}_ref",
                    "pid": pid,
                    "pdir": pdir,
                    "v_key": v_key,
                    "char_v": char_v_code,
                    "base_char": base_char,
                    "primary_prod_img": primary_prod_img,
                    "project_id": project_id,
                    "char_id": char_id,
                    "pov_only": is_pov_only,
                    "scene_duration_sec": scene_dur_sec,
                    "prod_uuids": prod_uuids,
                    "prompt_str": v_info["ref_image_prompt"],
                    "ref_img_rel": ref_img_rel,
                    "out_file": ref_img_abs,
                    "out_thumb_proj": out_thumb_proj,
                    "need_thumb": need_thumb,
                    "style": v_info.get("style", ""),
                    "scenes": scenes,
                    "voice_id": voice_id,
                    "retries": 0,
                })
                continue

            for sc in scenes:
                sc_id = sc["id"]
                out_mp4 = os.path.join(pdir, sc["file"])
                if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 50000:
                    print(f"✔ [{pid} | {sc_id}] Already downloaded ({os.path.getsize(out_mp4)//1024} KB)", flush=True)
                    continue

                existing_vid_uuid = state.get("scene_uuids", {}).get(sc_id)
                can_resume_inflight = bool(has_unique_ref and not needs_2k_upgrade and existing_vid_uuid and len(inflight_tasks) < MAX_INFLIGHT)
                init_stage = "upsample_1080p" if (existing_vid_uuid and str(existing_vid_uuid).endswith("_upsampled")) else "base_720p"
                task_obj = {
                    "type": "vid_scene",
                    "stage": init_stage,
                    "key": f"{pid}_{sc_id}",
                    "pid": pid,
                    "pdir": pdir,
                    "v_key": v_key,
                    "base_char": base_char,
                    "primary_prod_img": primary_prod_img,
                    "ref_img_abs": ref_img_abs,
                    "sc": sc,
                    "scene_duration_sec": int(sc.get("duration_sec") or scene_dur_sec),
                    "project_id": project_id,
                    "ref_uuid": ref_uuid,
                    "prod_uuid": prod_uuids[0] if prod_uuids else None,
                    "voice_id": voice_id,
                    "out_mp4": out_mp4,
                    "retries": 0,
                    "media_uuid": existing_vid_uuid if can_resume_inflight else None,
                    "submitted_at": time.time() if can_resume_inflight else 0,
                }
                if task_obj["media_uuid"]:
                    inflight_tasks[task_obj["key"]] = task_obj
                    print(f"🔄 [{pid} | {sc_id}] Resuming in-flight poll for media_uuid={existing_vid_uuid} ({init_stage})", flush=True)
                else:
                    pending_queue.append(task_obj)

    print(f"\n=== MULTI-THREADED PIPELINE READY: {len(inflight_tasks)} in-flight, {len(pending_queue)} tasks queued ===", flush=True)
    write_pipeline_heartbeat(
        f"🚀 Khởi động Đa Luồng ({len(active_flow_accs)} TK Google Flow | {FFMPEG_WORKERS} luồng FFmpeg): {len(inflight_tasks)} đang xử lý, {len(pending_queue)} hàng đợi",
        is_running=True,
    )
    safe_sync_ui()

    import socket
    try:
        with socket.create_connection(("flow.google.com", 443), timeout=3.0):
            pass
    except OSError as net_err:
        write_pipeline_heartbeat(f"❌ Lỗi kết nối mạng tới flow.google.com: {net_err}", is_running=False)
        raise RuntimeError(f"Network access to flow.google.com:443 is required before launching Chrome profile: {net_err}")

    with sync_playwright() as pw:
        print("Reading and refreshing auth cookies from persistent profile(s) & cookies_file...", flush=True)
        account_cookie_pool = []
        for acc_item in active_flow_accs:
            acc_prof = acc_item.get("profile_name") or PROF_NAME
            acc_sh_dir = gvt._resolve_flow_shared_dir(acc_prof)
            acc_p_dir, acc_c_file = profile_paths(acc_sh_dir, acc_prof)
            acc_saved = []
            if acc_c_file and os.path.exists(str(acc_c_file)):
                try:
                    c_json = json.load(open(str(acc_c_file), "r", encoding="utf-8"))
                    if isinstance(c_json, dict) and isinstance(c_json.get("cookies"), list):
                        acc_saved = [c for c in c_json["cookies"] if "GRECAPTCHA" not in c.get("name", "").upper()]
                    elif isinstance(c_json, list):
                        acc_saved = [c for c in c_json if "GRECAPTCHA" not in c.get("name", "").upper()]
                except Exception:
                    pass
            if acc_saved:
                merged_acc = {(c.get("domain", ""), c.get("name", "")): c for c in acc_saved}
                account_cookie_pool.append({
                    "name": acc_item.get("name") or acc_prof,
                    "profile_name": acc_prof,
                    "profile_dir": acc_p_dir,
                    "clean_cookies": list(merged_acc.values()),
                })

        # Warm-up primary profile ONLY if saved_cookies are missing/empty (prevents TargetClosedError if profile is busy)
        saved_cookies = []
        if cookies_file and os.path.exists(str(cookies_file)):
            try:
                c_json = json.load(open(str(cookies_file), "r", encoding="utf-8"))
                if isinstance(c_json, dict) and isinstance(c_json.get("cookies"), list):
                    saved_cookies = [c for c in c_json["cookies"] if "GRECAPTCHA" not in c.get("name", "").upper()]
                elif isinstance(c_json, list):
                    saved_cookies = [c for c in c_json if "GRECAPTCHA" not in c.get("name", "").upper()]
            except Exception as e:
                print(f"[WARN] Could not read cookies_file {cookies_file}: {e}", flush=True)

        raw_cookies = []
        if len(saved_cookies) < 5 and not account_cookie_pool:
            try:
                p_ctx = pw.chromium.launch_persistent_context(
                    str(profile_dir),
                    channel="chrome",
                    headless=False,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--window-position=-2000,-2000",
                        "--window-size=1280,800",
                    ],
                )
                if saved_cookies:
                    try:
                        p_ctx.add_cookies(saved_cookies)
                    except Exception as e:
                        print(f"[WARN] p_ctx.add_cookies: {e}", flush=True)
                p_page = p_ctx.pages[0] if p_ctx.pages else p_ctx.new_page()
                try:
                    p_page.goto("https://flow.google.com/project/932bc2a1-07ea-4199-b147-80ab0018d41c", wait_until="domcontentloaded", timeout=35000)
                    p_page.wait_for_timeout(2500)
                except Exception as e:
                    print(f"[WARN] Initial profile warm-up: {e}", flush=True)
                raw_cookies = p_ctx.cookies(["https://flow.google.com", "https://google.com", "https://www.google.com", "https://accounts.google.com"])
                p_ctx.close()
            except Exception as e_warm:
                print(f"[WARN] Skipping persistent profile warm-up ({e_warm}), using saved cookies pool...", flush=True)

        merged_by_key = {}
        for c in (saved_cookies + raw_cookies):
            if "GRECAPTCHA" not in c.get("name", "").upper():
                merged_by_key[(c.get("domain", ""), c.get("name", ""))] = c
        clean_cookies = list(merged_by_key.values())
        if not clean_cookies and account_cookie_pool:
            clean_cookies = list(account_cookie_pool[0].get("clean_cookies") or [])
        if not account_cookie_pool:
            account_cookie_pool.append({
                "name": f"Google_{PROF_NAME}",
                "profile_name": PROF_NAME,
                "profile_dir": profile_dir,
                "clean_cookies": clean_cookies,
            })
        elif clean_cookies:
            account_cookie_pool[0]["clean_cookies"] = clean_cookies

        cookie_map = {c["name"]: c["value"] for c in clean_cookies}
        cookie_hdr_box = ["; ".join(f"{k}={v}" for k, v in cookie_map.items())]
        print(f"Extracted {len(cookie_map)} clean deduplicated auth cookies across {len(account_cookie_pool)} account(s)!", flush=True)

        browser = pw.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--window-position=-2000,-2000",
                "--window-size=1280,800",
            ],
        )
        ctx_box = [None]
        page_box = [None]
        wiz_box = [None]
        dl_headers_box = [{}]
        ctx_uses = [0]
        cur_proj_box = [None]
        acc_idx_box = [0]
        cur_acc_box = [account_cookie_pool[0]["profile_name"]]

        def open_fresh_clean_context(project_id="932bc2a1-07ea-4199-b147-80ab0018d41c"):
            for attempt in range(1, 5):
                if ctx_box[0] is not None:
                    try:
                        ctx_box[0].close()
                    except Exception:
                        pass
                acc_entry = account_cookie_pool[acc_idx_box[0] % len(account_cookie_pool)]
                acc_idx_box[0] = (acc_idx_box[0] + 1) % len(account_cookie_pool)
                cur_acc_box[0] = acc_entry["profile_name"]
                use_cookies = acc_entry.get("clean_cookies") or clean_cookies
                print(
                    f"✨ [TK: {acc_entry['profile_name']}] Opening fresh clean Chrome context for project {project_id[:8]} (attempt {attempt})...",
                    flush=True,
                )
                try:
                    ctx = browser.new_context()
                    ctx.add_init_script(gvt._FLOW_HIJACK_BYPASS_JS)
                    ctx.add_cookies(use_cookies)
                    pg = ctx.new_page()
                    pg.goto(f"https://flow.google.com/project/{project_id}", wait_until="domcontentloaded", timeout=45000)
                    pg.evaluate(gvt._FLOW_HIJACK_BYPASS_JS)
                    pg.wait_for_function(
                        "() => window.WIZ_global_data && window.WIZ_global_data.SNlM0e && window.grecaptcha && window.grecaptcha.enterprise && typeof window.grecaptcha.enterprise.execute === 'function'",
                        timeout=40000,
                    )
                    pg.wait_for_timeout(1500)
                    wz = pg.evaluate(
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
                    live_c = ctx.cookies(["https://flow.google.com", "https://google.com", "https://accounts.google.com"])
                    c_map = {c["name"]: c["value"] for c in live_c if "GRECAPTCHA" not in c.get("name", "").upper()}
                    cookie_hdr_box[0] = "; ".join(f"{k}={v}" for k, v in c_map.items())
                    ctx_box[0] = ctx
                    page_box[0] = pg
                    wiz_box[0] = wz
                    dl_headers_box[0] = {
                        "Cookie": cookie_hdr_box[0],
                        "Referer": "https://flow.google.com/",
                        "User-Agent": wz["ua"],
                    }
                    ctx_uses[0] = 0
                    cur_proj_box[0] = project_id
                    return
                except Exception as e:
                    print(f"[WARN] open_fresh_clean_context ({acc_entry['profile_name']}) attempt {attempt} failed: {e}", flush=True)
                    time.sleep(3.0)
            raise RuntimeError("Failed to open clean Chrome context after 4 attempts")

        open_fresh_clean_context()
        last_submit_ts = [0.0]

        def ensure_single_prod_uuid(pid, pdir, state, refs_state, base_char, project_id, primary_prod_img):
            refs_state.setdefault("uploaded_prod_refs", {})
            cur_prod_uuids = refs_state["uploaded_prod_refs"].get(base_char) or []
            if cur_prod_uuids:
                return cur_prod_uuids[0]
            print(f"📤 [{pid} | {base_char.upper()}] Uploading 1 single-variant product image {os.path.basename(primary_prod_img)}...", flush=True)
            ok_u, u_id, err_u = upload_single_product_ref_in_page(
                page_box[0], wiz_box[0], project_id, primary_prod_img
            )
            if not ok_u or not u_id:
                print(f"⚠️ [{pid} | {base_char.upper()}] Product upload failed ({err_u})", flush=True)
                return None
            refs_state["uploaded_prod_refs"][base_char] = [u_id]
            save_prod_state(pdir, state, refs_state)
            print(f"✅ [{pid} | {base_char.upper()}] Uploaded single product image {os.path.basename(primary_prod_img)} -> uuid={u_id}", flush=True)
            time.sleep(2.5)
            return u_id

        def ensure_char_photo_uuid(pid, pdir, state, refs_state, base_char, project_id):
            refs_state.setdefault("uploaded_char_refs", {})
            cached_u = refs_state["uploaded_char_refs"].get(base_char)
            if cached_u:
                return cached_u
            chars_dir = os.path.join(WS_DIR, "flow_final_pipeline", "characters")
            for ext in ("jpg", "png", "jpeg"):
                cand_p = os.path.join(chars_dir, f"{base_char}_ref.{ext}")
                if os.path.isfile(cand_p) and os.path.getsize(cand_p) > 5000:
                    print(f"📤 [{pid} | {base_char.upper()}] Uploading character reference photo {os.path.basename(cand_p)}...", flush=True)
                    ok_c, c_uid, err_c = upload_single_product_ref_in_page(
                        page_box[0], wiz_box[0], project_id, cand_p, quality=96
                    )
                    if ok_c and c_uid:
                        refs_state["uploaded_char_refs"][base_char] = c_uid
                        save_prod_state(pdir, state, refs_state)
                        print(f"✅ [{pid} | {base_char.upper()}] Uploaded character photo -> uuid={c_uid}", flush=True)
                        time.sleep(2.0)
                        return c_uid
                    else:
                        print(f"⚠️ [{pid} | {base_char.upper()}] Character photo upload failed ({err_c})", flush=True)
            return None

        def fill_inflight_slots(wait_for_delay=False):
            while pending_queue and len(inflight_tasks) < MAX_INFLIGHT:
                elapsed_since_last = time.time() - last_submit_ts[0]
                if last_submit_ts[0] > 0 and elapsed_since_last < SUBMIT_DELAY_SEC:
                    if not wait_for_delay and inflight_tasks:
                        break
                    wait_rem = SUBMIT_DELAY_SEC - elapsed_since_last
                    print(f"⏱️ Waiting {wait_rem:.1f}s before next Google Flow request (15s delay)...", flush=True)
                    time.sleep(wait_rem)

                # Prefer a task matching the current open project context if ctx_uses < 12
                pick_idx = 0
                if cur_proj_box[0] and ctx_uses[0] < 12:
                    for idx_q, cand_t in enumerate(pending_queue):
                        if cand_t.get("project_id") == cur_proj_box[0]:
                            pick_idx = idx_q
                            break
                t = pending_queue.pop(pick_idx)
                pid = t["pid"]
                pdir, prompts_data, state, refs_state = prod_meta[pid]

                if ctx_uses[0] >= 12 or cur_proj_box[0] != t["project_id"]:
                    open_fresh_clean_context(t["project_id"])

                ctx_uses[0] += 1
                last_submit_ts[0] = time.time()

                t_type = t.get("type")
                if t_type == "upsample_ref_2k":
                    v_key = t["v_key"]
                    ok_2k, nbytes_2k, err_2k = upsample_image_2k_in_page(
                        page_box[0], wiz_box[0], t["project_id"], t["ref_uuid"], t["out_file"]
                    )
                    if not (ok_2k and nbytes_2k > 50000) and t["retries"] >= 2 and os.path.exists(t["out_file"]):
                        try:
                            from PIL import ImageFilter
                            with Image.open(t["out_file"]) as im_fb:
                                im_2k = im_fb.convert("RGB").resize((1536, 2752), Image.Resampling.LANCZOS)
                                im_2k = im_2k.filter(ImageFilter.UnsharpMask(radius=1.1, percent=115, threshold=2))
                                im_2k.save(t["out_file"], format="JPEG", quality=98, subsampling=0)
                            refs_dir = os.path.join(os.path.dirname(t["out_file"]), "refs")
                            os.makedirs(refs_dir, exist_ok=True)
                            shutil.copy2(t["out_file"], os.path.join(refs_dir, os.path.basename(t["out_file"])))
                            ok_2k = True
                            nbytes_2k = os.path.getsize(t["out_file"])
                        except Exception as e_loc2k:
                            err_2k = str(e_loc2k)
                    if ok_2k and nbytes_2k > 50000:
                        try:
                            ok_u2k, uuid_2k, _ = upload_single_product_ref_in_page(
                                page_box[0], wiz_box[0], t["project_id"], t["out_file"], quality=98
                            )
                            if ok_u2k and uuid_2k:
                                ref_rel_name = os.path.basename(t["out_file"])
                                state["uploaded_refs"][ref_rel_name] = uuid_2k
                                if v_key in refs_state.get("variants", {}):
                                    refs_state["variants"][v_key]["ref_image_uuid"] = uuid_2k
                                save_prod_state(pdir, state, refs_state)
                                for q_item in pending_queue:
                                    if q_item.get("pid") == pid and q_item.get("v_key") == v_key and q_item.get("type") in ("vid_scene", "thumb_img"):
                                        q_item["ref_uuid"] = uuid_2k
                        except Exception:
                            pass
                        print(f"✨ [{pid} | {v_key.upper()}] Upgraded existing Ref Image to 2K (1536x2752) & re-uploaded ({nbytes_2k//1024} KB)!", flush=True)
                        safe_sync_ui()
                    else:
                        t["retries"] += 1
                        print(f"⚠️ [{pid} | {v_key.upper()} 2K] SPrCad failed ({err_2k}) ({t['retries']}/4)", flush=True)
                        if t["retries"] <= 4:
                            pending_queue.insert(0, t)
                        open_fresh_clean_context(t["project_id"])

                elif t_type == "ref_img":
                    v_key = t["v_key"]
                    base_char = t["base_char"]
                    u_id = ensure_single_prod_uuid(
                        pid, pdir, state, refs_state, base_char, t["project_id"], t["primary_prod_img"]
                    )
                    if not u_id:
                        t["retries"] += 1
                        if t["retries"] <= 15:
                            pending_queue.insert(0, t)
                        open_fresh_clean_context(t["project_id"])
                        continue
                    if not t.get("char_id") and not t.get("pov_only"):
                        c_photo_uuid = ensure_char_photo_uuid(
                            pid, pdir, state, refs_state, base_char, t["project_id"]
                        )
                        if c_photo_uuid:
                            t["prod_uuids"] = [c_photo_uuid, u_id]
                            t["allow_multi_refs"] = True
                        else:
                            t["prod_uuids"] = [u_id]
                    else:
                        t["prod_uuids"] = [u_id]
                    ok, gen_uuid, err = generate_variant_ref_image_in_page(
                        page_box[0], wiz_box[0], cookie_hdr_box[0], dl_headers_box[0], t
                    )
                    if ok and gen_uuid:
                        refs_state["variants"][v_key] = {
                            "ref_image": t["ref_img_rel"],
                            "ref_image_uuid": gen_uuid,
                            "ref_image_path": t["out_file"],
                            "style": t["style"],
                        }
                        state["uploaded_refs"][t["ref_img_rel"]] = gen_uuid
                        save_prod_state(pdir, state, refs_state)
                        safe_sync_ui()

                        # Immediately insert the scene tasks (+ AI Thumbnail task) for this variant at the front of pending_queue!
                        # All scenes share the exact same ingredients: [gen_uuid (2K Ref Image), u_id (Product Image)] + voice_id!
                        new_scene_tasks = []
                        for sc in t["scenes"]:
                            sc_id = sc["id"]
                            out_mp4 = os.path.join(pdir, sc["file"])
                            if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 50000:
                                continue
                            new_scene_tasks.append({
                                "type": "vid_scene",
                                "stage": "base_720p",
                                "key": f"{pid}_{sc_id}",
                                "pid": pid,
                                "pdir": pdir,
                                "v_key": v_key,
                                "base_char": base_char,
                                "primary_prod_img": t["primary_prod_img"],
                                "ref_img_abs": t["out_file"],
                                "sc": sc,
                                "scene_duration_sec": int(sc.get("duration_sec") or t.get("scene_duration_sec") or 10),
                                "project_id": t["project_id"],
                                "ref_uuid": gen_uuid,
                                "prod_uuid": u_id,
                                "voice_id": t["voice_id"],
                                "out_mp4": out_mp4,
                                "retries": 0,
                                "media_uuid": None,
                                "submitted_at": 0,
                            })
                        if t.get("need_thumb") and t.get("out_thumb_proj"):
                            new_scene_tasks.append({
                                "type": "thumb_img",
                                "key": f"{pid}_{v_key}_thumb",
                                "pid": pid,
                                "pdir": pdir,
                                "v_key": v_key,
                                "char_v": t.get("char_v") or v_key,
                                "base_char": base_char,
                                "primary_prod_img": t["primary_prod_img"],
                                "project_id": t["project_id"],
                                "char_id": t.get("char_id") or "",
                                "ref_uuid": gen_uuid,
                                "prod_uuid": u_id,
                                "out_file": t["out_thumb_proj"],
                                "retries": 0,
                            })
                        pending_queue[:0] = new_scene_tasks
                    else:
                        t["retries"] += 1
                        print(f"⚠️ [{pid} | {v_key} REF] Image gen failed ({err}), recycling context ({t['retries']}/15)...", flush=True)
                        if t["retries"] <= 15:
                            pending_queue.insert(0, t)
                        open_fresh_clean_context(t["project_id"])

                elif t_type == "thumb_img":
                    v_key = t["v_key"]
                    char_v = t["char_v"]
                    out_thumb_proj = t["out_file"]
                    os.makedirs(os.path.dirname(out_thumb_proj), exist_ok=True)
                    thumbs_central_dir = os.path.join(WS_DIR, "thumbnails")
                    os.makedirs(thumbs_central_dir, exist_ok=True)
                    out_thumb_central = os.path.join(thumbs_central_dir, os.path.basename(out_thumb_proj))

                    u_id = t.get("prod_uuid") or ensure_single_prod_uuid(
                        pid, pdir, state, refs_state, t["base_char"], t["project_id"], t["primary_prod_img"]
                    )
                    ref_uuids_th = [x for x in [t.get("ref_uuid"), u_id] if x]
                    meta_th = _esm.build_thumbnail_prompt_for_variant(pid=pid, vkey=v_key) if _esm else {"prompt": f"9:16 commercial TikTok Shop thumbnail of {pid}"}
                    th_task = {
                        "pid": pid,
                        "v_key": f"{v_key}_thumb",
                        "project_id": t["project_id"],
                        "char_id": t.get("char_id") or "",
                        "prod_uuids": ref_uuids_th,
                        "allow_multi_refs": True,
                        "skip_reupload_2k": True,
                        "prompt_str": meta_th["prompt"],
                        "out_file": out_thumb_proj,
                    }
                    write_pipeline_heartbeat(f"🖼️ [{pid} | {char_v}] Đang tạo Ảnh Thumbnail AI 2K ({cur_acc_box[0]})...", is_running=True)
                    ok_th, th_uuid, err_th = generate_variant_ref_image_in_page(
                        page_box[0], wiz_box[0], cookie_hdr_box[0], dl_headers_box[0], th_task
                    )
                    if ok_th and os.path.isfile(out_thumb_proj) and os.path.getsize(out_thumb_proj) > 10000:
                        shutil.copy2(out_thumb_proj, out_thumb_central)
                        print(f"🖼️ [{pid} | {char_v}] Generated 2K AI Thumbnail -> {os.path.basename(out_thumb_central)} ({os.path.getsize(out_thumb_central)//1024} KB)!", flush=True)
                        final_mp4 = os.path.join(WS_DIR, "final_videos", f"{pid}_{char_v}.mp4")
                        if os.path.isfile(final_mp4) and os.path.getsize(final_mp4) > 50000 and _esm is not None:
                            _esm.inject_thumbnail_01s_into_video(final_mp4, out_thumb_central, duration_sec=float(cfg.get("thumbnail_duration_sec") or 0.1))
                        safe_sync_ui()
                    else:
                        t["retries"] += 1
                        print(f"⚠️ [{pid} | {char_v} THUMB] Thumbnail gen failed ({err_th}) ({t['retries']}/4)...", flush=True)
                        if t["retries"] <= 4:
                            pending_queue.append(t)
                        open_fresh_clean_context(t["project_id"])

                elif t_type == "upsample_1080p":
                    sc_id = t["sc"]["id"]
                    ok, up_uuid, err = submit_upsample_1080p_in_page(page_box[0], wiz_box[0], t)
                    if ok and up_uuid:
                        t["media_uuid"] = up_uuid
                        t["stage"] = "upsample_1080p"
                        t["submitted_at"] = time.time()
                        t["cookie_hdr"] = cookie_hdr_box[0]
                        t["wiz"] = wiz_box[0]
                        t["dl_headers"] = dict(dl_headers_box[0])
                        t["account_name"] = cur_acc_box[0]
                        state["scene_uuids"][sc_id] = up_uuid
                        save_prod_state(pdir, state)
                        inflight_tasks[t["key"]] = t
                        write_pipeline_heartbeat(f"✨ [{pid} | {sc_id}] Đang Upsample 1080p ({cur_acc_box[0]})...", is_running=True)
                    else:
                        t["retries"] += 1
                        print(f"⚠️ [{pid} | {sc_id}] 1080p Upsample submit failed ({err}) ({t['retries']}/5)...", flush=True)
                        if t["retries"] <= 5:
                            pending_queue.insert(0, t)
                        elif os.path.exists(t["out_mp4"] + ".720p.tmp"):
                            shutil.move(t["out_mp4"] + ".720p.tmp", t["out_mp4"])
                            print(f"⚠️ [{pid} | {sc_id}] Falling back to 720p MP4 after 5 upsample failures", flush=True)
                            safe_sync_ui()
                            check_and_queue_ffmpeg(
                                ffmpeg_pool, ffmpeg_futures, pid, pdir, t["v_key"], prompts_data["videos"][t["v_key"]]["scenes"]
                            )
                        open_fresh_clean_context(t["project_id"])

                else:
                    sc_id = t["sc"]["id"]
                    v_key = t["v_key"]
                    if not t.get("prod_uuid"):
                        u_id = ensure_single_prod_uuid(
                            pid, pdir, state, refs_state, t["base_char"], t["project_id"], t["primary_prod_img"]
                        )
                        if u_id:
                            t["prod_uuid"] = u_id
                            for q_item in pending_queue:
                                if q_item.get("pid") == pid and q_item.get("v_key") == v_key and q_item.get("type") in ("vid_scene", "thumb_img"):
                                    q_item["prod_uuid"] = u_id
                    # If retrying after a failed submission (e.g. account switch in multi-account mode),
                    # re-upload both the 2K Ref Image and Product Image to the current account's project and sync across all 3 scenes!
                    if t.get("retries", 0) > 0:
                        ref_img_local = t.get("ref_img_abs") or os.path.join(pdir, prompts_data["videos"][v_key]["ref_image"])
                        if os.path.isfile(ref_img_local):
                            ok_r, new_ref_u, _ = upload_single_product_ref_in_page(
                                page_box[0], wiz_box[0], t["project_id"], ref_img_local, quality=98
                            )
                            if ok_r and new_ref_u:
                                t["ref_uuid"] = new_ref_u
                                state["uploaded_refs"][os.path.basename(ref_img_local)] = new_ref_u
                                if v_key in refs_state.get("variants", {}):
                                    refs_state["variants"][v_key]["ref_image_uuid"] = new_ref_u
                                for q_item in pending_queue:
                                    if q_item.get("pid") == pid and q_item.get("v_key") == v_key and q_item.get("type") in ("vid_scene", "thumb_img"):
                                        q_item["ref_uuid"] = new_ref_u
                        if os.path.isfile(t["primary_prod_img"]):
                            ok_p, new_prod_u, _ = upload_single_product_ref_in_page(
                                page_box[0], wiz_box[0], t["project_id"], t["primary_prod_img"], quality=95
                            )
                            if ok_p and new_prod_u:
                                t["prod_uuid"] = new_prod_u
                                refs_state["uploaded_prod_refs"][t["base_char"]] = [new_prod_u]
                                for q_item in pending_queue:
                                    if q_item.get("pid") == pid and q_item.get("v_key") == v_key and q_item.get("type") in ("vid_scene", "thumb_img"):
                                        q_item["prod_uuid"] = new_prod_u
                        save_prod_state(pdir, state, refs_state)

                    t["worker_profile"] = cur_acc_box[0]
                    ok, ret_uuid, err = submit_scene_in_page(page_box[0], wiz_box[0], t)
                    if ok and ret_uuid:
                        t["media_uuid"] = ret_uuid
                        t["stage"] = "base_720p"
                        t["submitted_at"] = time.time()
                        t["cookie_hdr"] = cookie_hdr_box[0]
                        t["wiz"] = wiz_box[0]
                        t["dl_headers"] = dict(dl_headers_box[0])
                        t["account_name"] = cur_acc_box[0]
                        state["scene_uuids"][sc_id] = ret_uuid
                        save_prod_state(pdir, state)
                        inflight_tasks[t["key"]] = t
                        write_pipeline_heartbeat(f"🚀 [{pid} | {sc_id}] Đã gửi render cảnh 10s ({cur_acc_box[0]})", is_running=True)
                    else:
                        t["retries"] += 1
                        print(f"⚠️ [{pid} | {sc_id}] Submit failed ({err}), recycling clean context (retry {t['retries']}/15)...", flush=True)
                        if t["retries"] <= 15:
                            pending_queue.insert(0, t)
                        open_fresh_clean_context(t["project_id"])

        fill_inflight_slots(wait_for_delay=False)

        loop_start = time.time()
        while inflight_tasks or pending_queue:
            time.sleep(5.0)
            fill_inflight_slots(wait_for_delay=(len(inflight_tasks) == 0))
            if not inflight_tasks:
                continue

            poll_futs = {
                poll_pool.submit(poll_and_download_one, cookie_hdr_box[0], wiz_box[0], dl_headers_box[0], t): t
                for t in list(inflight_tasks.values())
            }
            status_summary = []
            freed_slot = False
            for fut in concurrent.futures.as_completed(poll_futs):
                t = poll_futs[fut]
                t_key = t["key"]
                pid = t["pid"]
                v_key = t["v_key"]
                sc_id = t["sc"]["id"]
                pdir, prompts_data, state, _ = prod_meta[pid]
                try:
                    res_state, nbytes = fut.result()
                except Exception:
                    res_state, nbytes = "error", None

                elapsed = int(time.time() - t["submitted_at"])
                if res_state == "ready_for_1080p":
                    print(f"🎬 [{pid} | {sc_id}] Base 720p ready ({nbytes//1024} KB in {elapsed}s) -> queueing 1080p Upsample (p0UkFb)...", flush=True)
                    inflight_tasks.pop(t_key, None)
                    freed_slot = True
                    t["type"] = "upsample_1080p"
                    t["stage"] = "upsample_1080p"
                    t["base_video_uuid"] = t["media_uuid"]
                    t["media_uuid"] = None
                    t["retries"] = 0
                    pending_queue.insert(0, t)

                elif res_state == "done":
                    print(f"📥 [{pid} | {sc_id}] Downloaded 1080p MP4 ({nbytes//1024} KB in {elapsed}s)!", flush=True)
                    inflight_tasks.pop(t_key, None)
                    freed_slot = True
                    write_pipeline_heartbeat(f"📥 [{pid} | {sc_id}] Tải xong cảnh 1080p ({nbytes//1024} KB)!", is_running=True)
                    safe_sync_ui()
                    check_and_queue_ffmpeg(
                        ffmpeg_pool,
                        ffmpeg_futures,
                        pid,
                        pdir,
                        v_key,
                        prompts_data["videos"][v_key]["scenes"],
                    )

                elif res_state.startswith("failed_") or ("rpc_err:[5]" in res_state and elapsed >= 15) or elapsed > 120:
                    inflight_tasks.pop(t_key, None)
                    freed_slot = True
                    t["retries"] += 1
                    if t.get("stage") == "upsample_1080p":
                        t["type"] = "upsample_1080p"
                        t["media_uuid"] = None
                        print(f"🔁 [{pid} | {sc_id}] 1080p Upsample {res_state} ({elapsed}s), retrying ({t['retries']}/5)...", flush=True)
                        if t["retries"] <= 5:
                            pending_queue.insert(0, t)
                        elif os.path.exists(t["out_mp4"] + ".720p.tmp"):
                            shutil.move(t["out_mp4"] + ".720p.tmp", t["out_mp4"])
                            print(f"⚠️ [{pid} | {sc_id}] Promoted 720p backup after 5 upsample failures", flush=True)
                            safe_sync_ui()
                            check_and_queue_ffmpeg(
                                ffmpeg_pool,
                                ffmpeg_futures,
                                pid,
                                pdir,
                                v_key,
                                prompts_data["videos"][v_key]["scenes"],
                            )
                    else:
                        t["type"] = "vid_scene"
                        t["media_uuid"] = None
                        state["scene_uuids"].pop(sc_id, None)
                        save_prod_state(pdir, state)
                        print(f"🔁 [{pid} | {sc_id}] Flow render {res_state} ({elapsed}s), fast-retrying ({t['retries']}/15)...", flush=True)
                        if t["retries"] <= 15:
                            pending_queue.append(t)
                else:
                    st_tag = "1080p" if t.get("stage") == "upsample_1080p" else "720p"
                    status_summary.append(f"{pid[-4:]}:{sc_id}[{st_tag}]({res_state.replace('running_','')})")

            if freed_slot and pending_queue:
                fill_inflight_slots(wait_for_delay=False)

            if status_summary:
                summary_line = (
                    f"⏳ [Đang xử lý={len(inflight_tasks)} | Hàng đợi={len(pending_queue)}] "
                    + ", ".join(status_summary[:10])
                )
                print(summary_line, flush=True)
                write_pipeline_heartbeat(summary_line, is_running=True)

            if time.time() - loop_start > 7200:
                print("Global timeout reached!", flush=True)
                break

        if ctx_box[0] is not None:
            try:
                ctx_box[0].close()
            except Exception:
                pass
        browser.close()

    for pid in only_pids:
        pdir, prompts_data, _, _ = prod_meta[pid]
        for v_key in list(prompts_data.get("videos", {}).keys()):
            if v_key in prompts_data.get("videos", {}):
                check_and_queue_ffmpeg(
                    ffmpeg_pool,
                    ffmpeg_futures,
                    pid,
                    pdir,
                    v_key,
                    prompts_data["videos"][v_key]["scenes"],
                )

    if ffmpeg_futures:
        write_pipeline_heartbeat(f"🎞️ Đang ghép {len(ffmpeg_futures)} Video Final 60FPS + Thumbnail 0.1s...", is_running=True)
    print(f"Waiting for {len(ffmpeg_futures)} parallel FFmpeg Final Video builds to finish...", flush=True)
    concurrent.futures.wait(ffmpeg_futures)
    ffmpeg_pool.shutdown(wait=True)
    poll_pool.shutdown(wait=False)
    write_pipeline_heartbeat("🎉 Đã hoàn tất toàn bộ tiến trình sản xuất Video Final & Thumbnail!", is_running=False)
    safe_sync_ui()
    print("\n🎉 ALL PRODUCTS × UNIQUE 2K REF IMAGES & FINAL 1080P VIDEOS COMPLETED AND SYNCED TO WEB UI!", flush=True)


if __name__ == "__main__":
    main()
