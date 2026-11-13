# -*- coding: utf-8 -*-
"""POV cooking: one native 2K six-panel storyboard per 8-second clip.

Supports both:
  1. 1-Click Auto Final (`stage='auto'`): Dish name + selected Voice + selected Flow Account
     -> Auto-generated 6-panel recipe & 3-beat Vietnamese voiceover -> Native 2K storyboards
     -> 2K re-upload -> 8s full-screen clips -> 1080p upsample -> 1080p 60FPS Final MP4.
  2. 2-Stage Reviewed Workflow (`stage='storyboards'` then `stage='video'` with `reviewed=True`):
     Separates storyboard inspection from paid video submissions.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import unicodedata
import uuid

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = Path(__file__).resolve().parent
for _p in (str(ROOT), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_LAUNCH_LOCK = threading.Lock()
DEFAULT_FLOW_PROJECT_UUID = os.environ.get("FLOW_DEFAULT_PROJECT_ID", "").strip()
DEFAULT_VOICE_ID = '29f2a669-6ea7-4486-939e-5cef9db7f211'


def project_folder(project_id):
    if not project_id or Path(project_id).name != project_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in project_id):
        raise ValueError('Invalid project ID')
    return ROOT / 'projects' / project_id


CONTINUITY = (
    "The same matte warm-ivory pot with pale interior, bright white kitchen, soft window light from camera left. "
    "Neutral ivory highlights, gently warm midtones, clean whites without an overall yellow cast. "
    "Only a narrow softly blurred background strip with pale wood utensils. Same adult hands, natural short nails, "
    "no jewelry; clear glass prep bowls, wooden spatula and wooden chopsticks. Only one active hand and "
    "one utensil at a time; chopsticks are exactly one pair held together by one hand, never two opposing pairs. No face or presenter. "
    "Photorealistic food-commercial 85-100mm macro lens look, readable contact point, realistic wet textures "
    "and restrained glossy highlights. Once seasoning is added: rich orange-red broth, distinct red oil ribbons, "
    "clear bubbling detail; fresh red tomatoes, yellow corn, green leaves and pink-orange cooked shrimp. "
    "Do not color the unseasoned broth red or add ingredients before their specified step."
)

GENERIC_CONTINUITY = (
    "The same clean cookware vessel throughout the recipe, bright clean white home kitchen, soft natural window light from camera left. "
    "Neutral ivory highlights, gently warm midtones, clean whites without an overall yellow cast. "
    "Only a narrow softly blurred background strip with pale wood utensils. Same adult hands, natural short nails, "
    "no jewelry; clear glass prep bowls, wooden spatula and wooden chopsticks. Only one active hand and "
    "one utensil at a time; chopsticks are exactly one pair held together by one hand, never two opposing pairs. No face or presenter. "
    "Photorealistic food-commercial 85-100mm macro lens look, readable contact point, realistic wet textures "
    "and restrained glossy highlights. Keep ingredient colors, sauce consistency and cooking progression strictly faithful "
    "to each step; do not add ingredients before their specified step."
)

MASTER_PROMPT_VERSION = '2.0-reference-macro'
COMPOSITION = (
    'Tight food-commercial crop through the pot sides: show the interior and immediate action, '
    'not the entire circular rim, both handles, a wide countertop or a large black stove. '
    'Food and the action occupy 85-95% of the frame. Hand and vessel enter partially from the upper edge. '
    'Source, moving ingredient and landing/contact point must be visually connected. '
    'Freeze the middle of the action, never a static before/after substitute. '
)


def build_continuity(recipe):
    """Return dish-accurate visual continuity while keeping DEFAULT_RECIPE byte-identical."""
    if not isinstance(recipe, dict):
        return GENERIC_CONTINUITY
    custom = str(recipe.get('visual_continuity') or '').strip()
    if custom:
        return custom
    dish_txt = f"{recipe.get('dish', '')} {recipe.get('dish_en', '')}".lower()
    if ('shrimp' in dish_txt or 'tôm' in dish_txt) and ('hotpot' in dish_txt or 'lẩu thái' in dish_txt):
        return CONTINUITY
    return GENERIC_CONTINUITY


def shot_direction(action):
    """Choose framing by visible action instead of rotating angles by shot index."""
    text = action.lower()
    if any(word in text for word in ('hero', 'lift', 'raise')):
        return 'Low oblique food-level macro; focus on the lifted food with the pot softly behind, liquid dripping back into the pot.'
    if any(word in text for word in ('pour', 'stream')):
        return 'High oblique macro; focus on a continuous stream and its landing point, the source vessel partly cropped at the top.'
    if any(word in text for word in ('stir', 'sweep', 'press', 'toss', 'flip', 'coat')):
        return 'Oblique macro on the utensil tip touching food; one short deliberate sweep, ingredients displaced physically then settling.'
    if any(word in text for word in ('simmer', 'bubbl', 'cooking moment', 'carameliz')) and not any(word in text for word in ('add', 'lower', 'drop', 'slide')):
        return 'Close surface macro; focus on moving bubbles, oil patterns and moist ingredient texture, steam remains translucent.'
    return 'High oblique close macro on ingredient release and first contact; natural gravity, small realistic bounce and settling.'


DEFAULT_RECIPE = {
    "dish": "Lẩu Thái tôm nấm",
    "dish_en": "Thai-style shrimp and mushroom hotpot",
    "clips": [
        {"title": "Phi thơm và nấu nền", "start_state": "Empty clean pot; all ingredients still separate.", "actions": [
            "Tilt a small clear glass bowl and pour one continuous thin golden oil stream into the empty ivory pot; oil spreads into a reflective film.",
            "Tilt a clear glass bowl to drop thin crushed lemongrass into the established oil; show pieces mid-fall and tiny bubbles at contact.",
            "Tilt a clear glass bowl so purple-white shallot slices tumble onto the established lemongrass; translucent layers catch the light.",
            "Stir the lemongrass and shallots once with the wooden spatula; aromatics glisten without burning.",
            "Tip glossy ripe red tomato wedges from a clear glass bowl into the established aromatics; first wedges land while others fall; no seafood or mushrooms yet.",
            "Pour clear broth into the tomatoes and aromatics; end with the pot half full and light steam."
        ]},
        {"title": "Tạo vị nước lẩu và cho rau nấm", "start_state": "Pot half full of broth with lemongrass, shallots and tomato wedges from clip 1; no seafood yet.", "actions": [
            "Stir one spoonful of red Thai chili paste into the existing broth; broth becomes orange-red.",
            "Drop two torn kaffir lime leaves into the orange-red broth; keep existing tomato and aromatics.",
            "Add thin pale galangal slices to the broth; slices land on the visible surface.",
            "Show the same seasoned broth gently simmering, small bubbles and wisps of steam; no hand action.",
            "Tip a small cluster of oyster mushrooms from a clear glass bowl into the simmering orange-red broth; visible landing ripples.",
            "Tip three yellow corn rounds from a clear glass bowl into the same pot; natural falling arc and small splash, mushrooms remain visible."
        ]},
        {"title": "Nấu tôm và hoàn thiện", "start_state": "Simmering orange-red broth with tomatoes, aromatics, lime leaves, mushrooms and corn from clip 2.", "actions": [
            "Lower peeled raw shrimp one by one into the simmering broth with wooden cooking chopsticks.",
            "Show a later cooking moment: the same shrimp now opaque pink and curled in gently bubbling broth; no raw shrimp remain.",
            "Add a small handful of clean fresh bok choy leaves to the shrimp and mushrooms in the pot.",
            "Gently press the green leaves into the hot broth with the same wooden spatula; leaves soften but stay green.",
            "Show the finished hotpot surface in close macro: glossy cooked pink shrimp, mushrooms, yellow corn and green leaves in rich orange-red broth with distinct oil ribbons and gentle bubbling.",
            "Hero shot: wooden chopsticks slowly lift one cooked pink-orange shrimp and a mushroom above the SAME finished pot toward the lens; broth droplets fall back, keep the food in focus and the pot softly behind. No serving bowl."
        ]}
    ]
}


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Voice & Account Discovery / Resolution Helpers
# ---------------------------------------------------------------------------

def list_cooking_voices():
    """Return selectable Vietnamese voices from the Voice Library, sorted with food/story voices first."""
    try:
        from character_library_manager import get_character_library_state
        state = get_character_library_state()
        raw_voices = list(state.get('voices_list') or [])
    except Exception:
        raw_voices = []

    items = []
    for v in raw_voices:
        tone_style = str(v.get('tone_style') or '').strip()
        cats_txt = ' '.join(str(x) for x in (v.get('recommended_categories') or [])).lower()
        name_txt = str(v.get('name') or '').lower()
        is_cooking_fit = (
            tone_style in ('sweet_foodie', 'chill_story')
            or any(k in cats_txt or k in name_txt for k in ('đồ ăn', 'ăn vặt', 'ẩm thực', 'đặc sản', 'nấu ăn'))
        )
        items.append({
            'key': str(v.get('key') or ''),
            'voice_id': str(v.get('voice_id') or ''),
            'name': str(v.get('name') or v.get('key') or ''),
            'gender': str(v.get('gender') or 'female'),
            'region': str(v.get('region') or 'north'),
            'region_label': str(v.get('region_label') or 'Miền Bắc'),
            'tone_style': tone_style,
            'tone_label': str(v.get('tone_label') or ''),
            'owner_profile': str(v.get('owner_profile') or ''),
            'account_voice_ids': dict(v.get('account_voice_ids') or {}),
            'sample_vn_abs': str(v.get('sample_vn_abs') or ''),
            'sample_url': str(v.get('sample_url') or ''),
            'sample_dialogue_vn': str(v.get('sample_dialogue_vn') or ''),
            'has_audio_preview': bool(v.get('sample_vn_abs') or v.get('sample_url')),
            'recommended_for_cooking': bool(is_cooking_fit),
        })

    def _sort_key(item):
        # Prioritize V2 default voice first, then sweet_foodie/chill_story voices, then other food voices, then the rest
        is_v2_default = 0 if item['voice_id'] == DEFAULT_VOICE_ID else 1
        tone_rank = 0 if item['tone_style'] in ('sweet_foodie', 'chill_story') else (1 if item['recommended_for_cooking'] else 2)
        return (0 if item['recommended_for_cooking'] else 1, is_v2_default, tone_rank, item['key'])

    items.sort(key=_sort_key)
    return items


def resolve_cooking_voice(voice_id_or_key, profile=''):
    """Resolve a voice key, UUID, or display name into full voice metadata + account-mapped UUID."""
    raw = str(voice_id_or_key or '').strip()
    if not raw or raw.lower() in ('none', 'asmr', 'off', 'no_voice'):
        return {
            'voice_id': '',
            'resolved_voice_id': '',
            'key': '',
            'name': 'Chỉ ASMR (Không lời)',
            'gender': 'female',
            'region': 'north',
            'owner_profile': '',
            'delivery_en': '',
        }

    voices = list_cooking_voices()
    matched = None
    for v in voices:
        if raw.lower() in (v['key'].lower(), v['voice_id'].lower(), v['name'].lower()):
            matched = v
            break

    resolved_id = raw
    try:
        from character_library_manager import resolve_voice_id_for_account
        resolved_id = resolve_voice_id_for_account(raw, profile) or raw
    except Exception:
        if matched and matched.get('voice_id'):
            resolved_id = matched['voice_id']

    if matched:
        reg_en = {
            'south': 'Southern Vietnamese (Saigon accent)',
            'central': 'Central Vietnamese (Hue/Da Nang accent)',
        }.get(matched['region'], 'Northern Vietnamese (Hanoi accent)')
        gen_en = 'young adult male' if matched['gender'] == 'male' else 'young adult female'
        delivery_en = (
            f"Natural {reg_en} cooking narrator ({gen_en} voice), same selected voice throughout, "
            "warm appetizing food-creator delivery, clear consonants"
        )
        return {
            'voice_id': matched['voice_id'] or resolved_id,
            'resolved_voice_id': resolved_id,
            'key': matched['key'],
            'name': matched['name'],
            'gender': matched['gender'],
            'region': matched['region'],
            'owner_profile': matched.get('owner_profile') or '',
            'delivery_en': delivery_en,
        }

    return {
        'voice_id': raw,
        'resolved_voice_id': resolved_id,
        'key': '',
        'name': raw,
        'gender': 'female',
        'region': 'north',
        'owner_profile': '',
        'delivery_en': 'Natural Vietnamese cooking narrator, same selected voice throughout, clear warm delivery',
    }


def _parse_flow_cookie_header(raw_api_key):
    """Convert `flow_cookie:k=v; ...` from accounts.json into Playwright cookie objects."""
    text = str(raw_api_key or '').strip()
    if 'flow_cookie:' not in text:
        return []
    cookie_part = text.split('flow_cookie:', 1)[1].strip()
    out = []
    for seg in cookie_part.split(';'):
        seg = seg.strip()
        if not seg or '=' not in seg:
            continue
        name, val = seg.split('=', 1)
        name = name.strip()
        val = val.strip()
        if not name or 'GRECAPTCHA' in name.upper():
            continue
        if name.startswith('__Host-'):
            out.append({'name': name, 'value': val, 'url': 'https://flow.google.com', 'secure': True})
        else:
            out.append({
                'name': name,
                'value': val,
                'domain': '.google.com',
                'path': '/',
                'secure': name.startswith('__Secure-'),
            })
    return out


def load_cooking_cookies(profile):
    """Load saved Flow cookies for `profile` from cookie JSON files or `accounts.json`."""
    prof = str(profile or '').strip()
    if not prof:
        return []
    candidate_files = []
    try:
        from google_flow_auth import profile_paths
        import grok_video_tool as gvt
        _, c_path = profile_paths(gvt._resolve_flow_shared_dir(prof), prof)
        if c_path:
            candidate_files.append(Path(c_path))
    except Exception:
        pass
    candidate_files.extend([
        ROOT / 'cookies' / f'{prof}.json',
        ROOT / 'data' / 'google_flow_grok' / 'cookies' / f'{prof}.json',
    ])

    for fp in candidate_files:
        if fp.is_file() and fp.stat().st_size > 50:
            try:
                data = json.loads(fp.read_text(encoding='utf-8'))
                cookies = data.get('cookies', []) if isinstance(data, dict) else data
                clean = [c for c in cookies if isinstance(c, dict) and 'GRECAPTCHA' not in str(c.get('name', '')).upper()]
                if clean:
                    return clean
            except Exception:
                continue

    # Fallback: read `flow_cookie:` from accounts.json
    for acc_file in (ROOT / 'data' / 'google_flow_grok' / 'accounts.json', ROOT / 'accounts.json'):
        if acc_file.is_file():
            try:
                items = json.loads(acc_file.read_text(encoding='utf-8'))
                if isinstance(items, list):
                    for it in items:
                        it_prof = str(it.get('profile_name') or '').split('@')[0].strip()
                        if it_prof.lower() == prof.lower():
                            parsed = _parse_flow_cookie_header(it.get('api_key', ''))
                            if parsed:
                                return parsed
            except Exception:
                continue
    return []


def has_cooking_cookies(profile):
    return bool(load_cooking_cookies(profile))


def _is_valid_uuid(val):
    try:
        uuid.UUID(str(val or '').strip())
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def list_cooking_flow_accounts():
    """List all configured Google Flow accounts with email, tier tag, credits, project_id, and cookie status."""
    by_prof = {}
    order = []

    def _upsert(prof, **fields):
        prof = str(prof or '').strip()
        if not prof:
            return
        if prof not in by_prof:
            by_prof[prof] = {
                'profile_name': prof,
                'name': f'Google_{prof}',
                'email': '',
                'tag': '',
                'credits': None,
                'project_id': DEFAULT_FLOW_PROJECT_UUID,
                'active': True,
                'has_cookies': False,
            }
            order.append(prof)
        cur = by_prof[prof]
        for k, v in fields.items():
            if v is not None and v != '':
                if k == 'project_id' and not _is_valid_uuid(v):
                    continue
                cur[k] = v

    # 1. Rich account entries from accounts.json
    for acc_file in (ROOT / 'data' / 'google_flow_grok' / 'accounts.json', ROOT / 'accounts.json'):
        if acc_file.is_file():
            try:
                items = json.loads(acc_file.read_text(encoding='utf-8'))
                if isinstance(items, list):
                    for it in items:
                        name = str(it.get('name') or '').strip()
                        if any(skip in name.lower() for skip in ('grok', 'codex', 'cliproxy')):
                            continue
                        prof = str(it.get('profile_name') or '').split('@')[0].strip()
                        if not prof:
                            continue
                        _upsert(
                            prof,
                            name=name or f'Google_{prof}',
                            email=str(it.get('google_email') or '').strip(),
                            tag=str(it.get('tag') or '').strip(),
                            credits=it.get('credits'),
                            project_id=str(it.get('proxy_url') or '').strip(),
                            active=bool(it.get('active', True)),
                        )
            except Exception:
                pass

    # 2. Worker accounts metadata (`Flow_nhieu_worker_accounts.json`)
    worker_file = ROOT / 'data' / 'google_flow_grok' / 'Flow_nhieu_worker_accounts.json'
    if worker_file.is_file():
        try:
            w_items = json.loads(worker_file.read_text(encoding='utf-8'))
            if isinstance(w_items, list):
                for w in w_items:
                    if w.get('is_grok'):
                        continue
                    pdir = str(w.get('profile_dir') or '').strip()
                    prof = Path(pdir).name if pdir else str(w.get('email') or '').split('@')[0].strip()
                    if not prof:
                        continue
                    _upsert(
                        prof,
                        email=str(w.get('email') or '').strip(),
                        credits=w.get('credits_remaining') if by_prof.get(prof, {}).get('credits') is None else by_prof[prof]['credits'],
                        project_id=str(w.get('project_id') or '').strip(),
                    )
        except Exception:
            pass

    # 3. Any additional cookie files discovered by engine_settings_manager
    try:
        from engine_settings_manager import list_available_flow_accounts
        for extra in list_available_flow_accounts():
            prof = str(extra.get('profile_name') or '').strip()
            if prof and prof not in by_prof:
                _upsert(
                    prof,
                    name=str(extra.get('name') or f'Google_{prof}'),
                    project_id=str(extra.get('project_id') or DEFAULT_FLOW_PROJECT_UUID),
                    active=bool(extra.get('active', True)),
                )
    except Exception:
        pass

    results = []
    for prof in order:
        item = by_prof[prof]
        item['has_cookies'] = has_cooking_cookies(prof)
        ident = item['email'] or item['name'] or prof
        if ident.startswith('Google_') and item['email']:
            ident = item['email']
        badges = []
        if item.get('tag'):
            badges.append(str(item['tag']))
        if isinstance(item.get('credits'), (int, float)):
            badges.append(f"{int(item['credits']):,} credits")
        badge_str = f" [{' • '.join(badges)}]" if badges else ''
        prof_suffix = f" ({prof})" if prof.lower() not in ident.lower() else ''
        cookie_note = '' if item['has_cookies'] else ' — Chưa có Cookie'
        item['display_label'] = f"{ident}{badge_str}{prof_suffix}{cookie_note}"
        results.append(item)

    results.sort(key=lambda a: (0 if a['has_cookies'] else 1, 0 if a.get('tag') == 'Ultra' else 1))
    return results


def resolve_cooking_account(profile='', explicit_project_uuid='', manifest=None):
    """Resolve account profile and matching Flow project UUID."""
    accounts = list_cooking_flow_accounts()
    prof = str(profile or '').strip()
    if not prof:
        ready = next((a for a in accounts if a.get('has_cookies')), None)
        prof = (ready or accounts[0])['profile_name'] if accounts else ''

    acc = next((a for a in accounts if a['profile_name'].lower() == prof.lower()), None)
    if acc:
        prof = acc['profile_name']

    # Preserve existing Flow project UUID when resuming a project on the same profile
    if isinstance(manifest, dict) and manifest.get('flow_project_id') and manifest.get('profile') == prof:
        if _is_valid_uuid(manifest['flow_project_id']):
            return prof, manifest['flow_project_id']

    exp_uuid = str(explicit_project_uuid or '').strip()
    if exp_uuid and exp_uuid.lower() != 'auto' and _is_valid_uuid(exp_uuid):
        # If caller left the legacy default UUID while selecting a non-default account that owns a distinct Flow project,
        # prefer the selected account's actual Flow project UUID so uploads/generations succeed on that account.
        if exp_uuid == DEFAULT_FLOW_PROJECT_UUID and acc and acc.get('project_id') and acc['project_id'] != DEFAULT_FLOW_PROJECT_UUID:
            return prof, acc['project_id']
        return prof, exp_uuid

    if acc and _is_valid_uuid(acc.get('project_id')):
        return prof, acc['project_id']
    try:
        from engine_settings_manager import get_default_flow_project_id
        dyn_pid = get_default_flow_project_id(prof) or get_default_flow_project_id('')
        if _is_valid_uuid(dyn_pid):
            return prof, dyn_pid
    except Exception:
        pass
    return prof, (exp_uuid if _is_valid_uuid(exp_uuid) else '')


# ---------------------------------------------------------------------------
# Prompt Builder & Recipe Auto-Enrichment
# ---------------------------------------------------------------------------

def build_prompts(recipe):
    audio_mode = recipe.get('audio_mode', 'asmr')
    if audio_mode not in ('asmr', 'voice'):
        raise ValueError('audio_mode must be asmr or voice')
    if audio_mode == 'voice' and not str(recipe.get('voice_id', '')).strip():
        raise ValueError('Chọn voice_id cho phiên bản có voice.')

    continuity_text = build_continuity(recipe)
    dish_check = f"{recipe.get('dish', '')} {recipe.get('dish_en', '')}".lower()
    backward_food_guard = 'raw shrimp after cooked shrimp' if ('shrimp' in dish_check or 'tôm' in dish_check) else 'raw ingredients reappearing after cooked state'

    voice_info = resolve_cooking_voice(recipe.get('voice_id', '')) if audio_mode == 'voice' else None
    voice_delivery = (
        str(recipe.get('voice_delivery_en') or '').strip()
        or (voice_info or {}).get('delivery_en')
        or 'Natural Vietnamese cooking narrator, same selected voice throughout, clear warm delivery'
    )

    clips = []
    for i, raw in enumerate(recipe['clips'], 1):
        if len(raw['actions']) != 6:
            raise ValueError('Each cooking clip must contain exactly six ordered actions')
        actions = raw['actions']
        image_prompt = (
            'Create ONE photorealistic vertical 9:16 storyboard contact sheet with EXACTLY SIX equal panels, '
            'arranged in 2 columns x 3 rows. Reading order is left to right, then top to bottom. '
            'This is an instructional cooking storyboard, each panel shows exactly one distinct action. '
            f"DISH: {recipe['dish_en']}. START STATE: {raw['start_state']}\n"
            + '\n'.join(f'PANEL {n}: {a} CAMERA AND ACTION: {shot_direction(a)}' for n, a in enumerate(actions, 1))
            + '\nCONTINUITY: ' + continuity_text
            + '\nCOMPOSITION IN EVERY PANEL: ' + COMPOSITION
            + (' Use the supplied previous storyboard only to match cookware, kitchen, hands and lighting; depict the NEW actions above.' if i > 1 else '')
            + ' Exactly six panels with thin straight clean dividers, no inset panels. No text, numbering, '
            'captions, logos, watermarks, extra fingers, malformed utensils, duplicated ingredients or backward cooking states.'
        )
        times = [(0, 1.3), (1.3, 2.6), (2.6, 3.9), (3.9, 5.2), (5.2, 6.5), (6.5, 8)]
        motion = (
            f'FIRST FRAME AND OPENING SHOT: independently filmed FULL-SCREEN close-up: {actions[0]} '
            'Reconstruct this as a single camera shot, not an animation of the sheet or a zoom into it. '
            'Complete this opening action before the first hard cut. '
            'Create ONE 8-second vertical 9:16 photorealistic POV cooking video. The supplied SIX-PANEL '
            'storyboard is ONLY a chronological action map, NOT the video layout or an opening frame. '
            'Convert its panels into SIX sequential FULL-SCREEN shots, one panel per shot, in reading order. '
            'Never display the contact sheet, grid, split screen, borders or multiple panels, including the first frame. '
            'Hard cuts. Start directly inside the first cooking action. Food or the immediate action fills 85-95% '
            'of every shot. Macro close-up from the cook viewpoint, no zoom out. CONTINUITY: ' + continuity_text
            + f" START STATE: {raw['start_state']}\n"
            + '\nCOMPOSITION: ' + COMPOSITION.replace('Freeze the middle of the action, never a static before/after substitute.', 'Begin already poised at the action, perform one legible movement, end as ingredients settle. Match the storyboard crop. No orbit or zoom out.')
            + '\n'.join(f'SHOT {n}, {a:.1f}-{b:.1f}s: full-screen. {shot_direction(action)} {action}' for n, ((a, b), action) in enumerate(zip(times, actions), 1))
            + '\nRealistic hand movement, fluid physics and subtle steam. ASMR only, synchronized gentle sizzling, '
            'pouring, simmering and utensils matching the visible action. No music, speech, dialogue, captions, '
            'subtitles, logos or watermark. No extra hands/fingers, warped tools, food morphing, teleporting '
            f'ingredients, changing pot/kitchen, {backward_food_guard}, or visible storyboard grid.'
        )
        narration = list(raw.get('voiceover') or [])
        if audio_mode == 'voice':
            if len(narration) != 3 or any(not isinstance(t, str) or not t.strip() for t in narration):
                raise ValueError('Mỗi clip có voice cần đúng 3 câu voiceover tiếng Việt.')
            if any(len(t.split()) > 15 for t in narration):
                raise ValueError('Mỗi cụm thoại tối đa 15 từ; nên dùng 6–10 từ để đọc tự nhiên.')
            motion = motion.replace('ASMR only, synchronized gentle sizzling,', 'Quiet cooking SFX under the narration, synchronized gentle sizzling,')
            motion = motion.replace('No music, speech, dialogue, captions,', 'No music, presenter dialogue, captions,')
            motion += f'\nVOICEOVER TIMELINE: {voice_delivery}; do not read English directions. Finish before 7.7s. Lower cooking sounds under speech. '
            motion += '\n'.join(f'[{a}-{b}s] Voice says: {json.dumps(text.strip(), ensure_ascii=False)}' for (a, b), text in zip([(0, 2.6), (2.6, 5.2), (5.2, 7.7)], narration))

        clip_entry = {
            'id': f's{i}',
            'title': raw['title'],
            'duration_sec': 8,
            'actions': actions,
            'image_prompt': image_prompt,
            'prompt': motion,
            'file': f'cooking_s{i}_1080p.mp4',
            'storyboard_file': f'storyboard_s{i}_2k.jpg',
        }
        if raw.get('actions_vn'):
            clip_entry['actions_vn'] = list(raw['actions_vn'])
        if narration:
            clip_entry['voiceover'] = [str(x).strip() for x in narration if str(x).strip()]
        clips.append(clip_entry)
    return clips


def ensure_recipe_ready(recipe=None, dish='', voice_id='', audio_mode='', num_clips=3, custom_notes='', has_subtitles=False):
    """Build or enrich a cooking recipe so dish + voice selection works immediately end-to-end."""
    from cooking_recipe_ai import generate_cooking_recipe_and_script

    raw_voice = str(voice_id or (recipe or {}).get('voice_id') or '').strip()
    mode = str(audio_mode or (recipe or {}).get('audio_mode') or '').strip().lower()
    if mode not in ('asmr', 'voice'):
        mode = 'voice' if raw_voice and raw_voice.lower() not in ('none', 'asmr', 'off') else 'asmr'

    v_meta = resolve_cooking_voice(raw_voice) if mode == 'voice' else resolve_cooking_voice('')
    effective_voice_id = v_meta['voice_id'] if mode == 'voice' else ''
    voice_region = v_meta.get('region') or 'north'

    target_dish = str(dish or (recipe or {}).get('dish') or '').strip() or DEFAULT_RECIPE['dish']

    if not isinstance(recipe, dict) or not recipe.get('clips'):
        generated = generate_cooking_recipe_and_script(
            dish_name=target_dish,
            num_clips=num_clips,
            audio_mode=mode,
            voice_region=voice_region,
            custom_notes=custom_notes,
        )
        recipe = dict(generated)
    else:
        recipe = json.loads(json.dumps(recipe))
        recipe['dish'] = str(recipe.get('dish') or target_dish).strip()
        if not str(recipe.get('dish_en') or '').strip():
            gen_meta = generate_cooking_recipe_and_script(
                dish_name=recipe['dish'],
                num_clips=len(recipe['clips']),
                audio_mode=mode,
                voice_region=voice_region,
                prefer_ai=False,
            )
            recipe['dish_en'] = gen_meta['dish_en']
            recipe.setdefault('visual_continuity', gen_meta.get('visual_continuity', ''))

        # Auto-fill missing Vietnamese voiceover lines if user switched an ASMR recipe to Voice mode
        if mode == 'voice':
            needs_vo = any(
                len(c.get('voiceover') or []) != 3 or any(not str(x).strip() for x in (c.get('voiceover') or []))
                for c in recipe['clips']
            )
            if needs_vo:
                gen_vo = generate_cooking_recipe_and_script(
                    dish_name=recipe['dish'],
                    num_clips=len(recipe['clips']),
                    audio_mode='voice',
                    voice_region=voice_region,
                    prefer_ai=False,
                )
                for idx, clip_obj in enumerate(recipe['clips']):
                    if len(clip_obj.get('voiceover') or []) != 3 or any(not str(x).strip() for x in (clip_obj.get('voiceover') or [])):
                        fallback_clip = gen_vo['clips'][min(idx, len(gen_vo['clips']) - 1)]
                        clip_obj['voiceover'] = list(fallback_clip['voiceover'])
                    if not clip_obj.get('actions_vn') and idx < len(gen_vo['clips']):
                        clip_obj['actions_vn'] = list(gen_vo['clips'][idx].get('actions_vn') or [])

    recipe['audio_mode'] = mode
    recipe['voice_id'] = effective_voice_id
    if mode == 'voice':
        recipe['voice_key'] = v_meta.get('key', '')
        recipe['voice_name'] = v_meta.get('name', '')
        recipe['voice_delivery_en'] = v_meta.get('delivery_en', '')
        recipe['has_subtitles'] = bool(has_subtitles or recipe.get('has_subtitles', False))
    else:
        recipe.pop('voice_key', None)
        recipe.pop('voice_name', None)
        recipe.pop('voice_delivery_en', None)
        recipe['has_subtitles'] = False
    return recipe


def make_cooking_project_id(dish):
    s = str(dish or 'mon_ngon').replace('đ', 'd').replace('Đ', 'D')
    ascii_text = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower()
    slug = re.sub(r'[^a-z0-9]+', '_', ascii_text).strip('_')[:28] or 'mon_ngon'
    return f"cook_{slug}_{time.strftime('%m%d_%H%M%S')}"


def sync_cooking_project(folder):
    """Write `project.json` inside `folder` and notify Web Studio state cleanly."""
    try:
        from cooking_studio_projection import build_project
        proj = build_project(folder)
        if proj is not None:
            write_json(Path(folder) / 'project.json', proj)
    except Exception:
        pass
    try:
        from sync_web_ui_state import sync_web_ui
        sync_web_ui()
    except Exception:
        pass


def prepare(project_id, recipe=None):
    folder = project_folder(project_id)
    manifest_file = folder / 'cooking_manifest.json'
    if manifest_file.exists():
        existing = json.loads(manifest_file.read_text(encoding='utf-8'))
        if recipe is not None and recipe != existing['recipe']:
            raise ValueError('Công thức đã thay đổi. Hãy tạo dự án mới để giữ đúng ảnh và job đang có.')
        return existing
    recipe = recipe or DEFAULT_RECIPE
    if not isinstance(recipe, dict) or not recipe.get('dish') or not recipe.get('dish_en') or not 1 <= len(recipe.get('clips', [])) <= 6:
        raise ValueError('Công thức cần tên món và từ 1 đến 6 clip, mỗi clip đúng 6 hành động.')
    manifest = {
        'project_id': project_id,
        'master_prompt_version': MASTER_PROMPT_VERSION,
        'dish': recipe['dish'],
        'dish_en': recipe['dish_en'],
        'recipe': recipe,
        'clips': build_prompts(recipe),
        'status': 'prepared',
        'pipeline_kind': 'cooking_storyboard',
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'format': {'aspect': '9:16', 'duration_per_clip': 8, 'panels': 6, 'layout': '2x3', 'native_2k_required': True},
    }
    write_json(manifest_file, manifest)
    sync_cooking_project(folder)
    return manifest


def get_status(project_id):
    folder = project_folder(project_id)
    manifest_file = folder / 'cooking_manifest.json'
    if not manifest_file.is_file():
        raise FileNotFoundError('Chưa có dự án nấu ăn này.')
    manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
    from engine_settings_manager import is_os_pid_running
    status_file = folder / 'pipeline_status.json'
    status = json.loads(status_file.read_text(encoding='utf-8')) if status_file.is_file() else {}
    manifest['is_running'] = bool(status.get('is_running') and is_os_pid_running(status.get('pid_os', 0)))
    return manifest


def list_recent_cooking_projects(limit=20):
    projects_dir = ROOT / 'projects'
    if not projects_dir.is_dir():
        return []
    found = []
    for mf in projects_dir.glob('*/cooking_manifest.json'):
        try:
            data = json.loads(mf.read_text(encoding='utf-8'))
            if data.get('studio_hidden'):
                continue
            rec = data.get('recipe') or {}
            found.append({
                'project_id': data.get('project_id') or mf.parent.name,
                'dish': data.get('dish') or '',
                'status': data.get('status') or 'prepared',
                'audio_mode': rec.get('audio_mode', 'asmr'),
                'voice_name': rec.get('voice_name', ''),
                'profile': data.get('profile', ''),
                'num_clips': len(data.get('clips') or []),
                'has_final': bool(data.get('final_video_path') and Path(data['final_video_path']).is_file()),
                'mtime': mf.stat().st_mtime,
            })
        except Exception:
            continue
    found.sort(key=lambda x: x['mtime'], reverse=True)
    for item in found:
        item.pop('mtime', None)
    return found[:limit]


def stop_stage(project_id):
    folder = project_folder(project_id)
    status_file = folder / 'pipeline_status.json'
    manifest_file = folder / 'cooking_manifest.json'
    if not manifest_file.is_file():
        raise FileNotFoundError('Chưa có dự án nấu ăn này.')
    killed = False
    if status_file.is_file():
        try:
            st = json.loads(status_file.read_text(encoding='utf-8'))
            pid_os = int(st.get('pid_os') or 0)
            if pid_os > 0:
                if sys.platform == 'win32':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid_os)], capture_output=True, timeout=10)
                else:
                    os.kill(pid_os, 9)
                killed = True
        except Exception:
            pass
    manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
    if manifest.get('status') not in ('done', 'boards_ready'):
        manifest['status'] = 'stopped'
    manifest['status_message'] = '⏹️ Đã dừng tiến trình theo yêu cầu. Các ảnh/clip đã tạo vẫn được giữ nguyên.'
    manifest.pop('is_running', None)
    write_json(manifest_file, manifest)
    write_json(status_file, {
        'pid': project_id,
        'pid_os': 0,
        'is_running': False,
        'current_step_text': manifest['status_message'],
        'updated_at': time.strftime('%H:%M:%S'),
    })
    sync_cooking_project(folder)
    return {'ok': True, 'project_id': project_id, 'killed': killed, 'status': manifest['status']}


def _resolve_cooking_video_provider(explicit_provider: str = '', manifest: dict = None) -> str:
    raw = str(explicit_provider or (manifest or {}).get('video_provider') or '').strip().lower()
    if raw in ('google_flow', 'google_vids'):
        return raw
    try:
        import engine_settings_manager as _esm
        cfg_prov = str(_esm.load_engine_settings().get('video_provider') or 'google_flow').strip().lower()
        if cfg_prov in ('google_flow', 'google_vids'):
            return cfg_prov
    except Exception:
        pass
    return 'google_flow'


def launch_stage(project_id, stage, profile='', project_uuid='', reviewed=False, video_provider=''):
    if stage not in ('storyboards', 'video', 'auto'):
        raise ValueError('Chỉ hỗ trợ bước storyboards, video hoặc auto.')
    with _LAUNCH_LOCK:
        manifest = get_status(project_id)
        if manifest['is_running']:
            raise ValueError('Dự án đang chạy. Không gửi job trùng; xem tiến trình hoặc đợi hoàn tất.')
        eff_provider = _resolve_cooking_video_provider(video_provider, manifest)
        if stage == 'video':
            if not reviewed:
                raise ValueError('Hãy kiểm tra và xác nhận các storyboard trước khi tạo video.')
            if eff_provider == 'google_vids':
                if not all(c.get('native_2k') for c in manifest['clips']):
                    raise ValueError('Chưa đủ storyboard tải 2K gốc; không gửi video.')
            else:
                if not all(c.get('native_2k') and c.get('uploaded_2k_uuid') for c in manifest['clips']):
                    raise ValueError('Chưa đủ storyboard tải 2K và upload lại; không gửi video.')
            manifest['storyboards_reviewed'] = True
        if video_provider in ('google_flow', 'google_vids'):
            manifest['video_provider'] = eff_provider
        if stage == 'video' or video_provider in ('google_flow', 'google_vids'):
            manifest.pop('is_running', None)
            write_json(project_folder(project_id) / 'cooking_manifest.json', manifest)

        resolved_profile, resolved_uuid = resolve_cooking_account(profile, project_uuid, manifest=manifest)
        if not resolved_profile:
            raise ValueError('Chưa có tài khoản Google Flow nào được cấu hình. Hãy mở tab Tài Khoản & Flow để thêm tài khoản trước!')
        if not has_cooking_cookies(resolved_profile):
            raise ValueError(f'Tài khoản Flow "{resolved_profile}" chưa có phiên đăng nhập (Cookie) đã lưu.')
        if not _is_valid_uuid(resolved_uuid):
            raise ValueError(f'Tài khoản Flow "{resolved_profile}" chưa có Google Flow Project ID hợp lệ.')

        folder = project_folder(project_id)
        prov_badge = 'Google Vids Omni 1080p' if eff_provider == 'google_vids' else 'Google Flow'
        step_label = {
            'auto': f'🚀 Đang chạy tự động trọn gói (Storyboard 2K → Video Final 1080p qua {prov_badge}) trên tài khoản {resolved_profile}',
            'storyboards': f'🖼️ Đang mở Flow tạo Storyboard 2K trên tài khoản {resolved_profile}',
            'video': f'🎬 Đang tạo Video 8s 1080p qua {prov_badge} trên tài khoản {resolved_profile}',
        }[stage]
        cmd_args = [
            sys.executable, '-u', str(Path(__file__).resolve()),
            project_id, '--stage', stage, '--profile', resolved_profile, '--flow-project', resolved_uuid,
            '--video-provider', eff_provider,
        ]
        with open(folder / 'cooking_run.log', 'a', encoding='utf-8') as log:
            proc = subprocess.Popen(
                cmd_args,
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            )
        write_json(folder / 'pipeline_status.json', {
            'pid': project_id,
            'pid_os': proc.pid,
            'is_running': True,
            'current_step_text': step_label,
            'updated_at': time.strftime('%H:%M:%S'),
        })
        sync_cooking_project(folder)
        return {
            'ok': True,
            'project_id': project_id,
            'stage': stage,
            'profile': resolved_profile,
            'flow_project_id': resolved_uuid,
            'video_provider': eff_provider,
            'pid_os': proc.pid,
        }


def auto_create_and_launch(
    dish,
    voice_id='',
    audio_mode='auto',
    profile='',
    project_uuid='',
    num_clips=3,
    custom_notes='',
    has_subtitles=False,
    recipe=None,
    project_id='',
    stage='auto',
    video_provider='',
):
    """1-Click helper: Dish + Voice + Account -> Auto-script + Prepare + Launch Auto Final."""
    ready_recipe = ensure_recipe_ready(
        recipe=recipe,
        dish=dish,
        voice_id=voice_id,
        audio_mode=audio_mode,
        num_clips=num_clips,
        custom_notes=custom_notes,
        has_subtitles=has_subtitles,
    )
    pid = str(project_id or '').strip() or make_cooking_project_id(ready_recipe['dish'])
    manifest = prepare(pid, ready_recipe)
    launch_kwargs = dict(stage=stage, profile=profile, project_uuid=project_uuid, reviewed=(stage == 'auto'))
    if video_provider:
        launch_kwargs['video_provider'] = video_provider
    launched = launch_stage(pid, **launch_kwargs)
    return {
        'ok': True,
        'project_id': pid,
        'dish': manifest['dish'],
        'audio_mode': ready_recipe.get('audio_mode', 'asmr'),
        'voice_id': ready_recipe.get('voice_id', ''),
        'voice_name': ready_recipe.get('voice_name', ''),
        'profile': launched['profile'],
        'flow_project_id': launched['flow_project_id'],
        'video_provider': launched.get('video_provider', 'google_flow'),
        'stage': stage,
        'pid_os': launched['pid_os'],
        'manifest': get_status(pid),
    }


# ---------------------------------------------------------------------------
# FFmpeg Post-Production (Audio-Safe Concat + Optional Clean Subtitles)
# ---------------------------------------------------------------------------

def _probe_media_info(mp4_path):
    """Return `(duration_sec, has_audio)` for an MP4 clip via ffprobe."""
    dur = 8.0
    has_audio = False
    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type:format=duration', '-of', 'json', str(mp4_path)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode == 0 and r.stdout.strip():
            info = json.loads(r.stdout)
            raw_dur = (info.get('format') or {}).get('duration')
            if raw_dur is not None:
                dur = max(0.5, float(raw_dur))
            streams = info.get('streams') or []
            has_audio = any(s.get('codec_type') == 'audio' for s in streams)
    except Exception:
        pass
    return dur, has_audio


def _fmt_ass_time(seconds):
    total_cs = max(0, int(round(float(seconds) * 100)))
    h = total_cs // 360000
    m = (total_cs % 360000) // 6000
    s = (total_cs % 6000) // 100
    cs = total_cs % 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _write_cooking_ass_subtitles(ass_path, clips, effective_durations):
    """Write a clean, food-commercial ASS subtitle file timed to each clip's 3 narration beats."""
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: CookingSub,Arial,48,&H00FFFFFF,&H0066E0FF,&H00000000,&H64000000,"
        "-1,0,0,0,100,100,0,0,1,3.2,1.0,2,54,54,215,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = []
    cursor = 0.0
    base_slots = [(0.06, 2.56), (2.60, 5.16), (5.20, 7.68)]
    for clip, clip_dur in zip(clips, effective_durations):
        narration = clip.get('voiceover') or []
        scale = clip_dur / 8.0 if clip_dur > 0 else 1.0
        for (st_rel, ed_rel), line in zip(base_slots, narration):
            txt = str(line or '').strip().replace('\n', ' ')
            if not txt:
                continue
            st_abs = cursor + st_rel * scale
            ed_abs = min(cursor + clip_dur - 0.05, cursor + ed_rel * scale)
            if ed_abs > st_abs + 0.2:
                events.append(f"Dialogue: 0,{_fmt_ass_time(st_abs)},{_fmt_ass_time(ed_abs)},CookingSub,,0,0,0,,{{\\fad(120,120)}}{txt}")
        cursor += clip_dur

    if not events:
        return False
    Path(ass_path).write_text(header + '\n'.join(events) + '\n', encoding='utf-8-sig')
    return True


def build_cooking_final_video(project_id, folder, manifest, save_cb=None):
    """Concatenate rendered 1080p cooking clips into a 1080x1920 60FPS Final MP4 (with audio fallback & optional subtitles)."""
    folder = Path(folder)
    clips = manifest['clips']
    inputs = []
    filters = []
    effective_durations = []

    for i, clip in enumerate(clips):
        clip_path = folder / clip['file']
        if not clip_path.is_file():
            raise FileNotFoundError(f"Thiếu file video cảnh {clip['id']}: {clip_path}")
        raw_dur, has_audio = _probe_media_info(clip_path)
        trim_start = max(0.0, float(clip.get('editorial_trim_start_sec') or 0.0))
        eff_dur = max(0.5, raw_dur - trim_start)
        effective_durations.append(eff_dur)

        inputs += ['-i', str(clip_path)]
        v_trim = f"trim=start={trim_start:.3f},setpts=PTS-STARTPTS," if trim_start > 0 else "setpts=PTS-STARTPTS,"
        filters.append(
            f"[{i}:v]{v_trim}scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,setsar=1,fps=60[v{i}]"
        )
        if has_audio:
            a_trim = f"atrim=start={trim_start:.3f},asetpts=PTS-STARTPTS," if trim_start > 0 else "asetpts=PTS-STARTPTS,"
            filters.append(f"[{i}:a]{a_trim}aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]")
        else:
            filters.append(f"anullsrc=channel_layout=stereo:sample_rate=48000:d={eff_dur:.3f}[a{i}]")

    concat_inputs = ''.join(f'[v{i}][a{i}]' for i in range(len(clips)))
    want_subs = bool(
        (manifest.get('recipe') or {}).get('audio_mode') == 'voice'
        and (manifest.get('recipe') or {}).get('has_subtitles')
    )
    ass_name = 'cooking_subtitles.ass'
    has_ass = False
    if want_subs:
        has_ass = _write_cooking_ass_subtitles(folder / ass_name, clips, effective_durations)

    if has_ass:
        filters.append(f"{concat_inputs}concat=n={len(clips)}:v=1:a=1[vcat][a];[vcat]ass={ass_name}[v]")
    else:
        filters.append(f"{concat_inputs}concat=n={len(clips)}:v=1:a=1[v][a]")

    final = ROOT / 'final_videos' / f'{project_id}_final.mp4'
    final.parent.mkdir(parents=True, exist_ok=True)
    temporary_final = folder / 'cooking_final_encoding.mp4'

    audio_label = 'Voice + ASMR' if (manifest.get('recipe') or {}).get('audio_mode') == 'voice' else 'ASMR gốc'
    if save_cb:
        save_cb(f'🎞️ Đang ghép Final 1080p 60FPS ({audio_label})...')

    subprocess.run(
        [
            'ffmpeg', '-y', '-v', 'error',
            *inputs,
            '-filter_complex', ';'.join(filters),
            '-map', '[v]', '-map', '[a]',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-threads', '2',
            '-c:a', 'aac', '-b:a', '192k',
            '-movflags', '+faststart',
            str(temporary_final),
        ],
        cwd=str(folder),
        check=True,
        timeout=240,
    )
    temporary_final.replace(final)
    final_dur, _ = _probe_media_info(final)
    manifest['status'] = 'done'
    manifest['final_video_path'] = str(final)
    manifest['final_duration_sec'] = round(final_dur, 2)
    return final


# ---------------------------------------------------------------------------
# Main Runner (`storyboards` | `video` | `auto`)
# ---------------------------------------------------------------------------

def run(project_id, stage='storyboards', profile='', project_uuid='', video_provider=''):
    import run_all_7_videos_mt as mt
    from playwright.sync_api import sync_playwright

    if stage not in ('storyboards', 'video', 'auto'):
        raise ValueError('stage must be storyboards, video, or auto')

    folder = project_folder(project_id)
    manifest = prepare(project_id)
    manifest_file = folder / 'cooking_manifest.json'
    eff_provider = _resolve_cooking_video_provider(video_provider, manifest)
    manifest['video_provider'] = eff_provider
    profile, project_uuid = resolve_cooking_account(profile, project_uuid, manifest=manifest)

    def save(message):
        manifest['status_message'] = message
        manifest.pop('is_running', None)
        write_json(manifest_file, manifest)
        write_json(folder / 'pipeline_status.json', {
            'pid': project_id,
            'pid_os': os.getpid(),
            'is_running': manifest['status'] not in ('boards_ready', 'done', 'error', 'stopped'),
            'current_step_text': message,
            'updated_at': time.strftime('%H:%M:%S'),
        })
        sync_cooking_project(folder)
        print(message, flush=True)

    cookies = load_cooking_cookies(profile)
    if not cookies:
        raise RuntimeError(f'No saved Flow session for selected profile: {profile}')

    if eff_provider == 'google_flow' and stage == 'video' and manifest.get('flow_project_id') and (manifest['flow_project_id'] != project_uuid or manifest.get('profile') != profile):
        raise ValueError('Dùng đúng tài khoản và dự án Flow đã upload storyboard, hoặc chạy chế độ Tự động / tạo lại storyboard.')

    recipe = manifest.get('recipe') or {}
    audio_mode = recipe.get('audio_mode', 'asmr')
    voice_meta = resolve_cooking_voice(recipe.get('voice_id', ''), profile=profile) if audio_mode == 'voice' else resolve_cooking_voice('')
    resolved_voice_id = voice_meta['resolved_voice_id'] if audio_mode == 'voice' else ''
    voice_owner = voice_meta.get('owner_profile') or ''

    manifest['profile'] = profile
    manifest['flow_project_id'] = project_uuid
    manifest['status'] = stage
    if stage == 'auto':
        manifest['auto_mode'] = True

    need_flow_browser = (stage in ('storyboards', 'auto')) or (stage == 'video' and eff_provider == 'google_flow')
    if stage == 'auto' and eff_provider == 'google_vids':
        # Nếu toàn bộ Storyboard 2K đã có sẵn trên ổ đĩa, không cần mở Chrome/Flow ở bước Auto!
        all_boards_ready = all(
            c.get('native_2k')
            and (folder / c['storyboard_file']).is_file()
            and c.get('sha256')
            and hashlib.sha256((folder / c['storyboard_file']).read_bytes()).hexdigest() == c.get('sha256')
            for c in manifest['clips']
        )
        if all_boards_ready:
            need_flow_browser = False

    try:
        if need_flow_browser:
            save(f'🌐 Đang mở phiên Google Flow ({profile}) cho món "{manifest["dish"]}"...')
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    channel='chrome',
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled', '--window-position=-2000,-2000', '--window-size=1280,800'],
                )
                try:
                    ctx = browser.new_context()
                    ctx.add_init_script(mt.gvt._FLOW_HIJACK_BYPASS_JS)
                    ctx.add_cookies(cookies)
                    pg = ctx.new_page()
                    pg.goto(f'https://flow.google.com/project/{project_uuid}', wait_until='domcontentloaded', timeout=45000)
                    pg.evaluate(mt.gvt._FLOW_HIJACK_BYPASS_JS)
                    pg.wait_for_function('() => window.WIZ_global_data?.SNlM0e && window.grecaptcha?.enterprise?.execute', timeout=40000)
                    wiz = pg.evaluate('() => ({at:WIZ_global_data.SNlM0e,bl:WIZ_global_data.cfb2h,fsid:WIZ_global_data.FdrFJe,ua:navigator.userAgent})')
                    live_cookies = ctx.cookies(['https://flow.google.com', 'https://google.com', 'https://accounts.google.com'])
                    cookie_map = {c['name']: c['value'] for c in live_cookies if 'GRECAPTCHA' not in c['name'].upper()}
                    cookie_hdr = '; '.join(f'{name}={value}' for name, value in cookie_map.items())
                    headers = {'Cookie': cookie_hdr, 'Referer': 'https://flow.google.com/', 'User-Agent': wiz['ua']}

                    # Phase 1: Native 2K Storyboards + Re-upload (for both 'storyboards' and 'auto')
                    if stage in ('storyboards', 'auto'):
                        previous = None
                        total_clips = len(manifest['clips'])
                        for idx, clip in enumerate(manifest['clips'], 1):
                            board = folder / clip['storyboard_file']
                            board_valid = (
                                clip.get('native_2k')
                                and board.is_file()
                                and clip.get('sha256')
                                and hashlib.sha256(board.read_bytes()).hexdigest() == clip.get('sha256')
                            )
                            if not board_valid:
                                save(f"🖼️ [{idx}/{total_clips}] Đang tạo Storyboard 6 ô 2K cho cảnh {clip['id']} ({clip['title']})...")
                                task = {
                                    'pid': project_id,
                                    'v_key': clip['id'],
                                    'project_id': project_uuid,
                                    'char_id': '',
                                    'prod_uuids': [previous] if previous else [],
                                    'prompt_str': clip['image_prompt'],
                                    'out_file': str(board),
                                    'skip_reupload_2k': True,
                                    'require_native_2k': True,
                                }
                                ok, generated, error = mt.generate_variant_ref_image_in_page(pg, wiz, cookie_hdr, headers, task)
                                if not ok:
                                    raise RuntimeError(error)
                                with Image.open(board) as im:
                                    if im.width < 1500 or im.height < 2600:
                                        raise RuntimeError(f'Native 2K dimensions invalid: {im.size}')
                                    clip['storyboard_dimensions'] = list(im.size)
                                clip['native_2k'] = True
                                clip['generated_uuid'] = generated
                                clip['sha256'] = hashlib.sha256(board.read_bytes()).hexdigest()
                                clip.pop('uploaded_2k_uuid', None)
                                save(f"✅ [{idx}/{total_clips}] Đã tải Storyboard 2K gốc {clip['id']}: {clip['storyboard_dimensions']}")

                            if not clip.get('uploaded_2k_uuid'):
                                ok, uploaded, error = mt.upload_single_product_ref_in_page(pg, wiz, project_uuid, str(board), quality=98)
                                if not ok:
                                    raise RuntimeError(f'2K re-upload required: {error}')
                                clip['uploaded_2k_uuid'] = uploaded
                                save(f"☁️ [{idx}/{total_clips}] Đã upload lại bản 2K {clip['id']} làm tham chiếu video ({uploaded[:8]}...)")
                            previous = clip['uploaded_2k_uuid']

                        if stage == 'auto':
                            manifest['storyboards_reviewed'] = True
                            if eff_provider == 'google_vids':
                                save('🎬 Đã xong toàn bộ Storyboard 2K! Chuyển sang tạo Video Native 1080p qua Google Vids Web (Không reCAPTCHA)...')
                            else:
                                save('🎬 Đã xong toàn bộ Storyboard 2K! Chuyển thẳng sang tạo Video 8s & Upscale 1080p...')

                    # Phase 2A: Google Flow 8s Video Generation + 1080p Upsampling
                    if stage in ('video', 'auto') and eff_provider == 'google_flow':
                        total_clips = len(manifest['clips'])
                        active_voice_id = resolved_voice_id
                        for idx, clip in enumerate(manifest['clips'], 1):
                            board = folder / clip['storyboard_file']
                            if not clip.get('native_2k') or not clip.get('uploaded_2k_uuid') or not board.is_file():
                                raise RuntimeError('Run and review storyboards before video stage')
                            if hashlib.sha256(board.read_bytes()).hexdigest() != clip['sha256']:
                                raise RuntimeError('Storyboard changed after 2K upload; regenerate/re-upload before video')
                            out = folder / clip['file']
                            if out.is_file() and out.stat().st_size > 50000 and clip.get('video_done'):
                                save(f"✅ [{idx}/{total_clips}] Cảnh {clip['id']} đã có sẵn bản 1080p, bỏ qua.")
                                continue

                            task = {
                                'pid': project_id,
                                'project_id': project_uuid,
                                'sc': clip,
                                'ref_uuid': clip['uploaded_2k_uuid'],
                                'voice_id': active_voice_id,
                                'storyboard_only': True,
                                'worker_profile': profile,
                                'out_mp4': str(out),
                            }
                            media = clip.get('video_uuid')
                            if not media:
                                save(f"🎬 [{idx}/{total_clips}] Đang gửi tạo video 8s cảnh {clip['id']} ({clip['title']})...")
                                ok, media, error = mt.submit_scene_in_page(pg, wiz, task)
                                if not ok and active_voice_id and voice_owner and profile.lower() != voice_owner.lower():
                                    # Foreign custom voice UUID not cloned on secondary account -> fallback cleanly to prompt voiceover
                                    active_voice_id = ''
                                    task['voice_id'] = ''
                                    save(f"ℹ️ Tài khoản phụ {profile} chưa có bản sao Voice UUID riêng, chuyển sang đọc thoại trực tiếp theo kịch bản...")
                                    ok, media, error = mt.submit_scene_in_page(pg, wiz, task)
                                if not ok:
                                    raise RuntimeError(error)
                                clip['video_uuid'] = media
                                save(f"⏳ [{idx}/{total_clips}] Đã gửi cảnh {clip['id']} ({media[:8]}...), đang chờ render 720p...")

                            def poll(uid, stage_name):
                                task.update(media_uuid=uid, stage=stage_name)
                                deadline = time.monotonic() + 600
                                while time.monotonic() < deadline:
                                    status, size = mt.poll_and_download_one(cookie_hdr, wiz, headers, task)
                                    if status in ('done', 'ready_for_1080p'):
                                        return
                                    if status in ('failed', 'error', 4) or str(status).startswith(('dl_err', 'failed_')):
                                        raise RuntimeError(f'{clip["id"]}: {status}')
                                    save(f"⏳ [{idx}/{total_clips}] Đang xử lý {clip['id']} ({stage_name}): {status}")
                                    time.sleep(5)
                                raise TimeoutError('Flow job still pending; resume uses saved UUID, no paid resubmit')

                            poll(media, 'base_720p')
                            upscale = clip.get('upscale_uuid')
                            if not upscale:
                                task['base_video_uuid'] = media
                                ok, upscale, error = mt.submit_upsample_1080p_in_page(pg, wiz, task)
                                if not ok:
                                    raise RuntimeError(error)
                                clip['upscale_uuid'] = upscale
                                save(f"✨ [{idx}/{total_clips}] Đang nâng cấp cảnh {clip['id']} lên chuẩn 1080p...")
                            poll(upscale, 'upsample_1080p')
                            clip['video_done'] = True
                            save(f"✅ [{idx}/{total_clips}] Đã tải xong video 1080p cảnh {clip['id']}!")
                finally:
                    browser.close()

        # Phase 2B: Google Vids Web Native 1080p Video Generation (Zero Browser, Zero reCAPTCHA)
        if stage in ('video', 'auto') and eff_provider == 'google_vids':
            import google_vids_client as gvc

            vids_model = 'omni'
            try:
                import engine_settings_manager as _esm
                vids_model = str(_esm.load_engine_settings().get('google_vids_model') or 'omni').strip().lower()
            except Exception:
                pass

            client = gvc.get_google_vids_client()
            total_clips = len(manifest['clips'])
            for idx, clip in enumerate(manifest['clips'], 1):
                board = folder / clip['storyboard_file']
                if not clip.get('native_2k') or not board.is_file():
                    raise RuntimeError('Run and review storyboards before video stage')
                if clip.get('sha256') and hashlib.sha256(board.read_bytes()).hexdigest() != clip['sha256']:
                    raise RuntimeError('Storyboard changed after 2K generation; regenerate before video')
                out = folder / clip['file']
                if out.is_file() and out.stat().st_size > 50000 and clip.get('video_done'):
                    save(f"✅ [{idx}/{total_clips}] Cảnh {clip['id']} đã có sẵn bản 1080p, bỏ qua.")
                    continue

                save(
                    f"🌐 [{idx}/{total_clips}] Đang tạo Video Native 1080p (8s) cho cảnh {clip['id']} ({clip['title']}) "
                    f"qua Google Vids Web ({profile} • {vids_model.upper()} • Không reCAPTCHA)..."
                )
                res_v = client.generate_video(
                    out_mp4=out,
                    prompt=clip['prompt'],
                    image_paths=[str(board)],
                    profile_name=profile,
                    model=vids_model,
                    aspect_ratio='9:16',
                    resolution='1080p',
                    duration_sec=int(clip.get('duration_sec') or 8),
                    ingredient_role='storyboard',
                )
                if not res_v.get('ok'):
                    raise RuntimeError(res_v.get('error') or f'Google Vids lỗi ở cảnh {clip["id"]}')
                clip['video_done'] = True
                clip['video_provider'] = 'google_vids'
                save(
                    f"✅ [{idx}/{total_clips}] Đã tải xong video Native 1080p cảnh {clip['id']} qua Google Vids "
                    f"({round(res_v['bytes']/1048576, 2)} MB trong {res_v['elapsed_sec']}s)!"
                )

        if stage == 'storyboards':
            manifest['status'] = 'boards_ready'
            save('✅ Đã tải và upload lại toàn bộ Storyboard 2K gốc. Bạn có thể xem trước hoặc bấm Tạo Video.')
        else:
            final = build_cooking_final_video(project_id, folder, manifest, save_cb=save)
            save(f'🎉 Hoàn tất Video Final 1080p 60FPS: {final}')
        return manifest
    except Exception as exc:
        manifest['status'] = 'error'
        save(str(exc))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project_id', nargs='?', default='', help='Project ID (auto-generated if omitted with --dish)')
    parser.add_argument('--stage', choices=['prepare', 'storyboards', 'video', 'auto'], default='prepare')
    parser.add_argument('--profile', default='')
    parser.add_argument('--flow-project', default='auto')
    parser.add_argument('--video-provider', choices=['auto', 'google_flow', 'google_vids'], default='auto')
    parser.add_argument('--recipe', help='Recipe JSON with dish, dish_en and clips (six actions per clip)')
    parser.add_argument('--dish', default='', help='Dish name in Vietnamese for auto-generated script')
    parser.add_argument('--voice', default='', help='Voice key or UUID from Voice Library (omit or "asmr" for ASMR)')
    parser.add_argument('--audio-mode', choices=['auto', 'asmr', 'voice'], default='auto')
    parser.add_argument('--num-clips', type=int, default=3, help='Number of 8s clips (1..6, default 3)')
    parser.add_argument('--subtitles', action='store_true', help='Burn clean Vietnamese voiceover subtitles on Final MP4')
    args = parser.parse_args()

    loaded_recipe = json.loads(Path(args.recipe).read_text(encoding='utf-8-sig')) if args.recipe else None
    if loaded_recipe is not None or args.dish or args.voice or args.audio_mode != 'auto':
        loaded_recipe = ensure_recipe_ready(
            recipe=loaded_recipe,
            dish=args.dish,
            voice_id=args.voice,
            audio_mode=args.audio_mode,
            num_clips=args.num_clips,
            has_subtitles=args.subtitles,
        )
    pid = args.project_id or make_cooking_project_id((loaded_recipe or DEFAULT_RECIPE)['dish'])
    if loaded_recipe is not None:
        prepare(pid, loaded_recipe)
    v_prov = '' if args.video_provider == 'auto' else args.video_provider
    result = prepare(pid, loaded_recipe) if args.stage == 'prepare' else run(pid, args.stage, args.profile, args.flow_project, video_provider=v_prov)
    print(json.dumps({
        'project_id': result['project_id'],
        'dish': result.get('dish', ''),
        'status': result['status'],
        'final_video_path': result.get('final_video_path', ''),
    }, ensure_ascii=False))
