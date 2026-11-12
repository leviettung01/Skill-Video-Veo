import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'flow_final_pipeline/scripts'))
from cooking_studio_projection import build_project, sync_projects


class CookingStudioProjectionTests(unittest.TestCase):
    def test_manifest_becomes_one_final_with_real_scenes_and_prompts(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / 'demo'
            folder.mkdir()
            final = folder / 'final.mp4'
            final.write_bytes(b'fixture')
            (folder / 'board.jpg').write_bytes(b'fixture')
            (folder / 'scene.mp4').write_bytes(b'fixture')
            thumbs_dir = folder / 'thumbnails'
            thumbs_dir.mkdir()
            (thumbs_dir / 'demo_pov_thumb.jpg').write_bytes(b'x' * 2048)
            manifest = {
                'project_id': 'demo',
                'dish': 'Món test',
                'status': 'done',
                'final_video_path': str(final),
                'recipe': {'audio_mode': 'voice', 'voice_id': 'v-uuid', 'voice_name': 'Phương Thảo (Nữ Miền Nam)'},
                'clips': [{
                    'id': 's1',
                    'title': 'Cảnh test',
                    'storyboard_file': 'board.jpg',
                    'file': 'scene.mp4',
                    'video_done': True,
                    'prompt': 'video prompt',
                    'image_prompt': 'image prompt',
                    'actions': ['A'],
                    'actions_vn': ['Thao tác một'],
                    'voiceover': ['Câu một', 'Câu hai', 'Câu ba'],
                    'duration_sec': 8,
                    'editorial_trim_start_sec': 1.25,
                }],
            }
            (folder / 'cooking_manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            project = build_project(folder)
            self.assertEqual(project['done_products'], 1)
            self.assertIn('Có Voice · Phương Thảo', project['name'])
            self.assertEqual(project['products'][0]['voice_id'], 'v-uuid')
            self.assertEqual(project['products'][0]['scenes'][0]['duration_sec'], 6.75)
            self.assertEqual(project['products'][0]['scenes'][0]['video_prompt'], 'video prompt')
            self.assertEqual(project['products'][0]['scenes'][0]['voiceover'], ['Câu một', 'Câu hai', 'Câu ba'])
            self.assertEqual(project['template_code'], '005')
            self.assertEqual(project['thumbnails_count'], 1)
            self.assertTrue(project['products'][0]['has_thumbnail'])
            self.assertIn('Kịch bản 1: Món test', project['products'][0]['hook_label'])
            self.assertEqual(project['live_status']['done_refs'], 1)
            self.assertEqual(project['live_status']['done_thumbnails'], 1)
            self.assertEqual(len(project['slide_overlay_image_paths']), 1)
            first, second = sync_projects(temporary), sync_projects(temporary)
            self.assertEqual([p['id'] for p in first], [p['id'] for p in second])
            final.unlink()
            self.assertEqual(build_project(folder)['done_products'], 0)

    def test_internal_take_is_not_listed(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'cooking_manifest.json').write_text('{"studio_hidden":true}', encoding='utf-8')
            self.assertIsNone(build_project(folder))


if __name__ == '__main__':
    unittest.main()
