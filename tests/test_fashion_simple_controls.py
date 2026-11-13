"""Regression checks for simple fashion inputs; no live provider requests."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'flow_final_pipeline' / 'scripts'))
import fashion_ai_video_analyzer as analyzer
import fashion_motion_control_engine as engine


class FashionSimpleControlsTests(unittest.TestCase):
    def test_failed_or_missing_or_synthetic_scene_cannot_become_final(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(analyzer, 'synthesize_fashion_scene_video_from_2k_frames', side_effect=AssertionError('Not an AI output')):
                for scene in [dict(id='s1', status='failed:not_found_5'), dict(id='s1', status='done'), dict(id='s1', status='done', output_provenance='synthetic_preview')]:
                    with self.subTest(scene=scene):
                        result = analyzer.render_fashion_postprod_final_video('test', folder, {'scenes':[scene]}, folder)
                        self.assertFalse(result['ok'])

    def test_partial_scene_set_cannot_become_final(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 's1.mp4').write_bytes(b'x' * 12000)
            result = analyzer.render_fashion_postprod_final_video('test', folder, {'scenes':[
                dict(id='s1', status='done', output_video_file='s1.mp4'),
                dict(id='s2', status='done', output_video_file='s2.mp4')]}, folder)
            self.assertFalse(result['ok'])
            self.assertFalse((Path(folder) / 'test_final.mp4').exists())

    def test_prepare_keeps_template_and_reuses_successful_image_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); folder=root/'project'; folder.mkdir()
            char=root/'identity.png'; char.write_bytes(b'identity')
            prod=root/'product.png'; prod.write_bytes(b'product')
            original={'project_id':'project','source_template_code':'FVT_026','base_char_2k':{'path':str(char)},
                      'outfits':[{'id':'my_product','path':str(prod)}], 'generation_mode':'chained_i2v'}
            calls=[]
            def generate(**kwargs):
                calls.append(kwargs)
                dest=folder/kwargs['output_filename']; dest.write_bytes(b'image')
                return {'ok':True,'path':str(dest)}
            def bind(**kwargs):
                self.assertEqual(kwargs['template_code'],'FVT_026')
                self.assertEqual(kwargs['base_char_path'],kwargs['char_sheet_path'])
                self.assertEqual(len(kwargs['outfit_items']),1)
                self.assertEqual(kwargs['outfit_items'][0]['id'],'my_product')
                return {'ok':True,'source_template_code':'FVT_026','scenes':[{'id':'s1','duration_sec':8}]}
            with patch.object(engine,'FASHION_STUDIO_DIR',str(root)), patch.object(engine,'generate_fashion_2k_asset_on_flow',side_effect=generate), patch.object(engine,'apply_fashion_video_template_to_project',side_effect=bind):
                self.assertTrue(engine.prepare_simple_fashion_inputs('project',original)['ok'])
                self.assertTrue(engine.prepare_simple_fashion_inputs('project',original)['ok'])
            self.assertEqual(len(calls),2)
            self.assertIn('ONE person',calls[0]['prompt_str'])
            self.assertIn('No invented accessories',calls[1]['prompt_str'])

    def test_preparation_failure_stops_before_video_submission(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'project';folder.mkdir()
            path=folder/'fashion_project.json'
            path.write_text(json.dumps({'input_flow':'simple','scenes':[{'id':'s1','status':'preparing'}]}),encoding='utf-8')
            with patch.object(engine,'FASHION_STUDIO_DIR',temp), patch.object(engine,'prepare_simple_fashion_inputs',return_value={'ok':False,'error':'Image provider unavailable'}):
                result=engine.run_fashion_motion_project_on_flow('project')
            self.assertFalse(result['ok'])
            saved=json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(saved['status'],'failed_input_preparation')
            self.assertEqual(saved['scenes'][0]['status'],'failed:input_preparation')

    def test_multi_account_failover_demotes_expired_snlm0e_profile(self):
        engine._UNHEALTHY_FLOW_PROFILES.clear()
        candidates_initial = engine._get_ordered_flow_account_candidates('leviettung04')
        self.assertGreaterEqual(len(candidates_initial), 2)
        self.assertEqual(candidates_initial[0], 'leviettung04')
        engine._mark_flow_profile_unhealthy('leviettung04', "Phiên đăng nhập Google Flow của 'leviettung04' đã hết hạn (thiếu SNlM0e).")
        candidates_after = engine._get_ordered_flow_account_candidates('leviettung04')
        self.assertNotEqual(candidates_after[0], 'leviettung04')
        self.assertEqual(candidates_after[-1], 'leviettung04')
        engine._mark_flow_profile_healthy('leviettung04')

    def test_multitask_live_progress_for_fashion_and_cooking(self):
        import engine_settings_manager as esm
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            f_json = root / 'fashion_project.json'
            f_json.write_text(json.dumps({
                'project_id': 'fashion_fvt_050_test',
                'title': '[FVT_050] Trend Biến Hình',
                'status': 'running_flow',
                'status_message': 'Đang render Cảnh 1...',
                'scenes': [
                    {'id': 's1', 'scene_index': 1, 'status': 'rendering_720p', 'elapsed_sec': 20},
                    {'id': 's2', 'scene_index': 2, 'status': 'ready'},
                ],
            }), encoding='utf-8')
            f_prog = esm._get_fashion_project_live_progress('fashion_fvt_050_test', f_json)
            self.assertTrue(f_prog['is_running'])
            self.assertEqual(f_prog['pipeline_kind'], 'fashion_motion')
            self.assertGreaterEqual(f_prog['progress_pct'], 10)

            c_dir = root / 'cooking_lau_bo_test'
            c_dir.mkdir()
            (c_dir / 'cooking_manifest.json').write_text(json.dumps({
                'project_id': 'cooking_lau_bo_test',
                'dish': 'Lẩu bò nhúng dấm',
                'status': 'running_video',
                'status_message': 'Đang tạo clip 2/3...',
                'clips': [
                    {'id': 'clip_01', 'title': 'Cảnh 1', 'actions': ['A'], 'storyboard_file': 'sb1.png', 'file': 'c1.mp4', 'video_done': True},
                    {'id': 'clip_02', 'title': 'Cảnh 2', 'actions': ['B'], 'storyboard_file': 'sb2.png', 'file': 'c2.mp4', 'video_done': False},
                ],
            }), encoding='utf-8')
            (c_dir / 'pipeline_status.json').write_text(json.dumps({
                'pid': 'cooking_lau_bo_test',
                'pid_os': 99999,
                'is_running': True,
                'current_step_text': 'Đang tạo clip 2/3...',
            }), encoding='utf-8')
            with patch('engine_settings_manager.is_os_pid_running', return_value=True):
                c_prog = esm._get_cooking_project_live_progress('cooking_lau_bo_test', str(c_dir))
            self.assertTrue(c_prog['is_running'])
            self.assertEqual(c_prog['pipeline_kind'], 'cooking_storyboard')
            self.assertGreater(c_prog['progress_pct'], 0)

    def test_uploaded_ref_image_uuid_populated_in_beluga_aa_payload(self):
        import run_all_7_videos_mt as r7
        captured_evals = []

        class DummyPage:
            def evaluate(self, script, arg=None):
                captured_evals.append((script, arg))
                if arg is None:
                    return 'dummy-rcap-token'
                return {'status': 500, 'text': 'stop'}

        page = DummyPage()
        wiz = {'bl': 'bl_test', 'fsid': '123', 'at': 'at_test', 'ua': 'ua_test'}
        r7.generate_variant_ref_image_in_page(page, wiz, '', {}, {
            'pid': 'fashion_test',
            'v_key': 'deconstructed_outfit_flatlay_2k',
            'project_id': 'proj_uuid_1',
            'char_id': '',
            'prod_uuids': ['uploaded-media-uuid-1234'],
            'allow_multi_refs': False,
            'prompt_str': 'Extract garment',
            'out_file': 'out.png',
        })
        self.assertEqual(len(captured_evals), 2)
        f_req = json.loads(captured_evals[1][1]['fReq'])
        payload_ogi = json.loads(f_req[0][0][1])
        yb = payload_ogi[1][0]
        self.assertEqual(yb[2], [['uploaded-media-uuid-1234', None, None, None, 1]])
        self.assertEqual(yb[10], [])


if __name__ == '__main__':
    unittest.main()
