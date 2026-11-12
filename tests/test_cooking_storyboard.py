"""Offline contract checks; never call generation providers."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'flow_final_pipeline/scripts'
sys.path.insert(0, str(SCRIPTS))
import cooking_recipe_ai as recipe_ai
import cooking_storyboard_engine as cooking
import run_all_7_videos_mt as mt


class Page:
    def __init__(self):
        self.payload = None

    def evaluate(self, source, arg=None):
        if arg is None:
            return 'offline-token'
        self.payload = json.loads(json.loads(arg['fReq'])[0][0][1])
        return {'status': 200, 'text': 'offline-rpc-result'}


class CookingContractTests(unittest.TestCase):
    def test_six_actions_each_and_eight_second_timeline(self):
        clips = cooking.build_prompts(cooking.DEFAULT_RECIPE)
        self.assertEqual(len(clips), 3)
        for clip in clips:
            self.assertEqual(len(clip['actions']), 6)
            self.assertEqual(clip['duration_sec'], 8)
            self.assertIn('SHOT 6, 6.5-8.0s', clip['prompt'])
            self.assertIn('Never display the contact sheet', clip['prompt'])

    def test_invalid_recipe_panel_count(self):
        with self.assertRaises(ValueError):
            cooking.build_prompts({'dish_en': 'Food', 'clips': [{'title': 'Bad', 'start_state': '', 'actions': ['only one']}]})

    def test_action_drives_camera_and_new_hero_stays_in_pot(self):
        self.assertIn('stream', cooking.shot_direction('Pour broth'))
        self.assertIn('utensil tip', cooking.shot_direction('Stir broth'))
        clips = cooking.build_prompts(cooking.DEFAULT_RECIPE)
        self.assertIn('not the entire circular rim', clips[0]['image_prompt'])
        self.assertIn('No serving bowl', clips[-1]['actions'][-1])

    def test_path_escape_is_rejected(self):
        for value in ('../outside', 'C:\\outside', '', 'two/levels'):
            with self.assertRaises(ValueError):
                cooking.project_folder(value)

    def test_storyboard_is_the_only_video_reference(self):
        page = Page()
        task = {'pid': 'offline', 'project_id': 'offline-project', 'ref_uuid': 'uploaded-native-2k',
                'voice_id': '', 'storyboard_only': True, 'sc': {'id': 's1', 'prompt': 'six shots', 'duration_sec': 8}}
        with patch.object(mt.gvt, '_parse_batchexecute_wrb', return_value=(True, [None, 100, None, []], None)):
            ok, _, _ = mt.submit_scene_in_page(page, {'at': 'x', 'bl': 'x', 'fsid': 'x'}, task)
        self.assertTrue(ok)
        item = page.payload[0][0]
        self.assertEqual(item[1], [[None, 'uploaded-native-2k']])
        self.assertEqual(item[2], 'abra_r2v_8s')
        self.assertEqual(item[7], [])

    def test_product_pipeline_keeps_two_reference_guard(self):
        ok, _, error = mt.submit_scene_in_page(Page(), {}, {'pid': 'offline', 'project_id': 'p', 'ref_uuid': 'one', 'voice_id': '', 'sc': {'id': 's1'}})
        self.assertFalse(ok)
        self.assertIn('Missing prod_uuid', error)

    def test_live_api_needs_review_before_video(self):
        with patch.object(cooking, 'get_status', return_value={'is_running': False, 'clips': []}):
            with self.assertRaisesRegex(ValueError, 'xác nhận'):
                cooking.launch_stage('offline', 'video', reviewed=False)

    def test_auto_script_generator_avoids_hotpot_bleed_and_builds_valid_voice_prompts(self):
        for dish in ('Sườn xào chua ngọt', 'Thịt kho tàu trứng cút', 'Cá hồi áp chảo sốt chanh dây', 'Trà đào cam sả'):
            rec = recipe_ai.generate_cooking_recipe_and_script(
                dish_name=dish,
                num_clips=3,
                audio_mode='voice',
                voice_region='south',
                prefer_ai=False,
            )
            ready = cooking.ensure_recipe_ready(recipe=rec, dish=dish, voice_id='voice_nu_nam_am_thuc', audio_mode='voice')
            clips = cooking.build_prompts(ready)
            self.assertEqual(len(clips), 3)
            for c in clips:
                self.assertEqual(len(c['actions']), 6)
                self.assertEqual(len(c['voiceover']), 3)
                self.assertNotIn('pink-orange cooked shrimp', c['image_prompt'])
                self.assertNotIn('raw shrimp after cooked shrimp', c['prompt'])
                self.assertIn('VOICEOVER TIMELINE:', c['prompt'])

    def test_voices_and_accounts_discovery_and_account_project_resolution(self):
        voices = cooking.list_cooking_voices()
        self.assertGreaterEqual(len(voices), 2)
        resolved_v = cooking.resolve_cooking_voice(voices[0]['key'], profile='leviettung04')
        self.assertTrue(resolved_v['voice_id'])

        accounts = cooking.list_cooking_flow_accounts()
        self.assertGreaterEqual(len(accounts), 1)
        for acc in accounts:
            prof, proj_uuid = cooking.resolve_cooking_account(acc['profile_name'], explicit_project_uuid='auto')
            self.assertEqual(prof, acc['profile_name'])
            self.assertEqual(len(proj_uuid), 36)

    def test_one_click_auto_create_and_launch_uses_auto_stage_without_live_calls(self):
        test_pid = 'qa_offline_cook_unit_test'
        folder = cooking.project_folder(test_pid)
        shutil.rmtree(folder, ignore_errors=True)
        try:
            with patch.object(cooking, 'launch_stage', return_value={
                'ok': True,
                'project_id': test_pid,
                'stage': 'auto',
                'profile': 'leviettung04',
                'flow_project_id': '7f17875b-4450-40a4-9362-d504f82eda57',
                'pid_os': 99999,
            }) as mock_launch:
                res = cooking.auto_create_and_launch(
                    dish='Cánh gà chiên nước mắm',
                    voice_id='voice_nu_nam_am_thuc',
                    profile='leviettung04',
                    project_id=test_pid,
                )
            self.assertTrue(res['ok'])
            self.assertEqual(res['stage'], 'auto')
            self.assertEqual(res['audio_mode'], 'voice')
            mock_launch.assert_called_once()
            self.assertTrue((folder / 'cooking_manifest.json').is_file())
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_resilient_final_ffmpeg_handles_silent_clip_and_optional_subtitles(self):
        if not shutil.which('ffmpeg'):
            self.skipTest('ffmpeg not installed')
        test_pid = 'qa_offline_ffmpeg_cook_test'
        final_out = cooking.ROOT / 'final_videos' / f'{test_pid}_final.mp4'
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'space folder'
            folder.mkdir(parents=True)
            # Clip 1: video only (no audio stream!)
            c1 = folder / 'cooking_s1_1080p.mp4'
            subprocess.run(
                ['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=360x640:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(c1)],
                check=True,
            )
            # Clip 2: video + audio
            c2 = folder / 'cooking_s2_1080p.mp4'
            subprocess.run(
                ['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=navy:s=360x640:d=1', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-shortest', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(c2)],
                check=True,
            )
            manifest = {
                'project_id': test_pid,
                'dish': 'Sườn xào chua ngọt',
                'recipe': {'audio_mode': 'voice', 'has_subtitles': True},
                'clips': [
                    {'id': 's1', 'title': 'Cảnh 1', 'file': 'cooking_s1_1080p.mp4', 'voiceover': ['Áp chảo sườn non vàng xém', 'Phi tỏi thơm dậy mùi', 'Đảo đều tay trên lửa vừa']},
                    {'id': 's2', 'title': 'Cảnh 2', 'file': 'cooking_s2_1080p.mp4', 'voiceover': ['Rưới sốt chua ngọt sánh đỏ', 'Áo đều quanh từng dẻ sườn', 'Gắp miếng sườn bóng mượt']},
                ],
            }
            try:
                built = cooking.build_cooking_final_video(test_pid, folder, manifest)
                self.assertTrue(built.is_file())
                self.assertEqual(manifest['status'], 'done')
                self.assertGreater(built.stat().st_size, 5000)
            finally:
                final_out.unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
