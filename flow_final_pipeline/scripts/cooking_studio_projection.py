# -*- coding: utf-8 -*-
"""Read cooking manifests into the shared Studio/Matrix project contract."""
import json
from pathlib import Path


def build_project(folder):
    folder = Path(folder)
    manifest = json.loads((folder / 'cooking_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('studio_hidden'):
        return None
    pid = manifest['project_id']
    recipe = manifest.get('recipe') or {}
    audio_mode = recipe.get('audio_mode', 'asmr')
    voice_id = str(recipe.get('voice_id') or '') if audio_mode == 'voice' else ''
    voice_name = str(recipe.get('voice_name') or '') if audio_mode == 'voice' else ''
    voice_short = voice_name.split('(')[0].strip() if voice_name else ''

    clips = manifest.get('clips', [])
    final = Path(manifest.get('final_video_path') or folder / '__missing_final__')
    done = manifest.get('status') == 'done' and final.is_file()
    scenes = []
    for i, clip in enumerate(clips, 1):
        image, video = folder / clip['storyboard_file'], folder / clip['file']
        raw_recipe_clip = recipe.get('clips', [])[i - 1] if i - 1 < len(recipe.get('clips', [])) else {}
        voiceover = clip.get('voiceover') or raw_recipe_clip.get('voiceover') or []
        actions_vn = clip.get('actions_vn') or raw_recipe_clip.get('actions_vn') or []
        desc_items = actions_vn if actions_vn else clip.get('actions', [])
        scenes.append({
            'scene_number': i,
            'scene_title': clip['title'],
            'scene_description': ' → '.join(desc_items),
            'dialogue_vn': ' • '.join(voiceover) if audio_mode == 'voice' and voiceover else '',
            'voiceover': list(voiceover) if audio_mode == 'voice' else [],
            'actions': clip.get('actions', []),
            'actions_vn': list(actions_vn),
            'image_prompt': clip.get('image_prompt', ''),
            'video_prompt': clip.get('prompt', ''),
            'image_path': str(image) if image.is_file() else '',
            'video_path': str(video) if video.is_file() and clip.get('video_done') else '',
            'duration_sec': clip.get('duration_sec', 8) - clip.get('editorial_trim_start_sec', 0),
            'status': 'done' if video.is_file() and clip.get('video_done') else 'queued',
        })
    storyboard_paths = [s['image_path'] for s in scenes if s['image_path']]
    ref = storyboard_paths[0] if storyboard_paths else ''
    ws_thumbs = folder.parent.parent / 'thumbnails'
    proj_thumbs = folder / 'thumbnails'
    thumb_candidates = [
        manifest.get('thumbnail_path') or '',
        ws_thumbs / f'{pid}_pov_thumb.jpg',
        ws_thumbs / f'{pid}_nv1_v1_thumb.jpg',
        proj_thumbs / f'{pid}_pov_thumb.jpg',
        proj_thumbs / f'{pid}_nv1_v1_thumb.jpg',
    ]
    if proj_thumbs.is_dir():
        for ext in ('*.jpg', '*.png', '*.jpeg'):
            for tp in sorted(proj_thumbs.glob(ext)):
                if not tp.name.endswith(('_scene_ref.jpg', '_raw2k.jpg')):
                    thumb_candidates.append(tp)
    thumb_candidates.append(folder / 'qa_gpt_thumbnail_open.jpg')
    thumb_path = next(
        (str(Path(c)) for c in thumb_candidates if c and Path(c).is_file() and Path(c).stat().st_size > 1000),
        '',
    )

    version = 'V2' if manifest.get('master_prompt_version') else 'V1'
    if pid.startswith('pov_cooking_'):
        name = f"{manifest['dish']} · Demo {version} · Nấu ăn POV"
        hook_badge = f"Demo {version}"
    else:
        badge = f"Có Voice · {voice_short}" if (audio_mode == 'voice' and voice_short) else ('Có Voice' if audio_mode == 'voice' else 'ASMR')
        name = f"{manifest['dish']} · Nấu ăn POV ({badge})"
        hook_badge = voice_short if (audio_mode == 'voice' and voice_short) else ('Có Voice' if audio_mode == 'voice' else 'ASMR')
    hook_label = f"Kịch bản 1: {manifest.get('dish', '')} • {hook_badge}".strip(' •')

    state = manifest.get('status', 'prepared')
    from engine_settings_manager import is_os_pid_running
    try:
        live = json.loads((folder / 'pipeline_status.json').read_text(encoding='utf-8'))
        running = bool(live.get('is_running') and is_os_pid_running(live.get('pid_os', 0)))
        step_text = live.get('current_step_text') or manifest.get('status_message', '')
    except (OSError, ValueError):
        running = False
        step_text = manifest.get('status_message', '')

    done_boards = sum(bool(s['image_path']) for s in scenes)
    done_vids = sum(s['status'] == 'done' for s in scenes)
    done_refs = int(done_boards >= max(1, len(scenes))) if scenes else int(bool(ref))
    done_thumbs = int(bool(thumb_path))
    total_steps = max(1, len(scenes) * 2 + 1)
    raw_pct = min(95, int(round((done_boards + done_vids) * 100.0 / total_steps)))
    progress_pct = 100 if done else (max(8, raw_pct) if running else raw_pct)

    rendered_files = []
    for pat in ('storyboard_*.jpg', 'cooking_s*.mp4', '*_thumb*.jpg', '*_thumb*.png'):
        for fp in folder.glob(pat):
            if fp.is_file() and fp not in rendered_files:
                rendered_files.append(fp)
    rendered_files_count = len(rendered_files)
    rendered_size_mb = round(sum(fp.stat().st_size for fp in rendered_files) / (1024 * 1024), 1)
    all_imgs = ([thumb_path] if thumb_path else []) + [p for p in storyboard_paths if p != thumb_path]

    status = 'done' if done else ('failed' if state == 'error' else ('vid_gen' if running else 'queued'))
    product = {
        'id': pid + '_pov',
        'vkey': 'pov',
        'char_v_code': 'pov',
        'pipeline_kind': 'cooking_storyboard',
        'product_name': name,
        'hook_label': hook_label,
        'dish': manifest.get('dish', ''),
        'audio_mode': audio_mode,
        'voice_id': voice_id,
        'voice_name': voice_name,
        'has_subtitles': bool(recipe.get('has_subtitles')),
        'status': status,
        'product_image_path': ref,
        'primary_product_image_path': ref,
        'thumbnail_path': thumb_path,
        'has_thumbnail': bool(thumb_path),
        'slide_overlay_image_paths': storyboard_paths[:5],
        'all_product_image_paths': all_imgs[:8],
        'final_video_path': str(final) if done else '',
        'final_video_mtime': int(final.stat().st_mtime) if done else 0,
        'output_dir': str(folder),
        'project_dir': str(folder),
        'scenes': scenes,
        'num_scenes': len(scenes),
        'seconds_per_scene': 8,
        'duration_sec': manifest.get('final_duration_sec'),
        'aspect': '9:16',
    }
    settings = {
        'num_scenes': len(scenes),
        'seconds_per_scene': 8,
        'aspect': '9:16',
        'video_resolution': '1080p',
        'audio_mode': audio_mode,
        'voice_id': voice_id,
        'voice_name': voice_name,
        'has_subtitles': bool(recipe.get('has_subtitles')),
        'profile': manifest.get('profile', ''),
        'img_model': 'Storyboard native 2K',
        'vid_model': 'Flow',
        'role_skill_file': 'Template/Nấu Ăn POV Storyboard/ROLE_SKILL.md',
    }
    result = {
        'id': pid,
        'name': name,
        'full_product_name': manifest.get('dish', '') or name,
        'dish': manifest.get('dish', ''),
        'audio_mode': audio_mode,
        'voice_id': voice_id,
        'voice_name': voice_name,
        'profile': manifest.get('profile', ''),
        'pipeline_kind': 'cooking_storyboard',
        'template_code': '005',
        'template_name': 'Nấu Ăn POV Storyboard',
        'videos_per_character': 1,
        'final_videos_dir': str(folder.parent.parent / 'final_videos'),
        'project_dir': str(folder),
        'primary_product_image_path': ref,
        'slide_overlay_image_paths': storyboard_paths[:5],
        'all_product_image_paths': all_imgs[:8],
        'products': [product],
        'settings': settings,
        'total_products': 1,
        'done_products': int(done),
        'running_products': int(running),
        'failed_products': int(state == 'error'),
        'thumbnails_count': done_thumbs,
        'deleted_finals_count': 0,
        'has_rendered_cache': bool(rendered_files_count > 0),
        'rendered_files_count': rendered_files_count,
        'rendered_size_mb': rendered_size_mb,
        'is_clean_new': not bool(rendered_files_count > 0),
        'is_running': running,
        'progress_pct': progress_pct,
        'logs': [step_text] if step_text else [],
        'role_skill_file': settings['role_skill_file'],
        'live_status': {
            'is_running': running,
            'done_refs': done_refs,
            'done_storyboards': done_boards,
            'done_scenes': done_vids,
            'total_scenes': len(scenes),
            'done_thumbnails': done_thumbs,
            'done_finals': int(done),
            'total_variants': 1,
            'progress_pct': progress_pct,
            'current_step': step_text,
            'current_step_text': step_text,
        },
    }
    return result


def sync_projects(projects_dir):
    items = []
    for source in sorted(Path(projects_dir).glob('*/cooking_manifest.json')):
        try:
            project = build_project(source.parent)
            if project is None:
                continue
            target = source.parent / 'project.json'
            temporary = target.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(target)
            items.append({k: v for k, v in project.items() if k not in ('products', 'logs')})
        except (ValueError, KeyError, OSError):
            continue
    return items
