"""Adapter for agents preparing Template 005 from a recipe or dish name."""
import json
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[2] / 'flow_final_pipeline/scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from cooking_storyboard_engine import ensure_recipe_ready, prepare, write_json


def generate_project_from_template(pid, pdir, info_data, characters_data, videos_per_character=1, **kwargs):
    recipe_path = Path(pdir) / 'cooking_recipe.json'
    if recipe_path.is_file():
        recipe = json.loads(recipe_path.read_text(encoding='utf-8-sig'))
    else:
        dish = str((info_data or {}).get('dish') or kwargs.get('dish') or '').strip()
        if not dish:
            raise ValueError('Template 005 cần tên món ăn (dish) hoặc cooking_recipe.json. Mở Cooking Studio (#005) để gõ tên món + chọn giọng đọc; không dùng link sản phẩm.')
        recipe = ensure_recipe_ready(
            dish=dish,
            voice_id=str((info_data or {}).get('voice_id') or kwargs.get('voice_id') or '').strip(),
            audio_mode=str((info_data or {}).get('audio_mode') or kwargs.get('audio_mode') or 'auto').strip(),
        )
        write_json(recipe_path, recipe)
    manifest = prepare(pid, recipe)
    return {
        'product_id': pid,
        'product_name': manifest['dish'],
        'template_id': 'cooking_pov_storyboard',
        'template_code': '005',
        'template_name': 'Nấu Ăn POV Storyboard',
        'pipeline_kind': 'cooking_storyboard',
        'videos_per_character': 1,
        'videos': {},
        'cooking_manifest': 'cooking_manifest.json',
    }
