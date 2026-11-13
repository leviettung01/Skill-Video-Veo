import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'flow_final_pipeline' / 'scripts'))
from fashion_motion_control_engine import resolve_fashion_prompt_image_refs, encode_flow_structured_prompt_Nj


class InlineRefsTest(unittest.TestCase):
    def test_all_individual_outfit_chips_are_attached_and_encoded(self):
        segments = []
        assets = {}
        for key in ['last_frame', 'shorts', 'beige', 'office']:
            assets[key] = 'uuid-' + key
            segments.extend([{'type': 'text', 'text': 'Switch to '},
                             {'type': 'media', 'asset_key': key, 'title': key + '.png'}])
        refs = resolve_fashion_prompt_image_refs(segments, assets)
        encoded = encode_flow_structured_prompt_Nj(segments, assets, allowed_image_uuids=refs)
        chips = [part[1][0][0] for part in encoded[2][0] if len(part) == 2 and part[0] is None]
        self.assertEqual(chips, refs)
        self.assertEqual(len(chips), 4)

    def test_missing_continuity_frame_stops_submission(self):
        with self.assertRaisesRegex(ValueError, 'Missing uploaded image'):
            resolve_fashion_prompt_image_refs([{'type': 'media', 'asset_key': 'last_frame'}], {})

    def test_limit_is_not_silently_truncated(self):
        segments = [{'type': 'media', 'asset_key': str(i)} for i in range(6)]
        with self.assertRaisesRegex(ValueError, 'supported limit'):
            resolve_fashion_prompt_image_refs(segments, {str(i): str(i) for i in range(6)})


if __name__ == '__main__':
    unittest.main()
