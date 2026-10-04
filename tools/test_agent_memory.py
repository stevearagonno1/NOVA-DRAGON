import json
import tempfile
import unittest
from pathlib import Path
from agent_combined import memory_snapshot


class MemoryTests(unittest.TestCase):
    def test_cgroup_total_is_distinct_from_process_rss(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'memory.current').write_text(str(300 * 1048576))
            (root / 'memory.max').write_text(str(512 * 1048576))
            (root / '123').mkdir()
            (root / '123/statm').write_text('10000 2560 0 0 0 0 0')
            (root / '123/environ').write_text('SECRET=must-not-be-read')
            snapshot = memory_snapshot({'gateway': 123, 'secret-role': 123}, root, root, 4096)
            self.assertEqual(snapshot, {'cgroup_mb': 300.0, 'limit_mb': 512.0,
                                        'rss_mb': {'gateway': 10.0}})
            self.assertNotIn('SECRET', json.dumps(snapshot))

    def test_unlimited_and_disappeared_process_are_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'memory.current').write_text('0')
            (root / 'memory.max').write_text('max')
            snapshot = memory_snapshot({'agent': 999}, root, root, 4096)
            self.assertEqual(snapshot, {'cgroup_mb': 0.0, 'limit_mb': None,
                                        'rss_mb': {'agent': None}})

    def test_v1_fallback_and_malformed_statm(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'memory').mkdir()
            (root / 'memory/memory.usage_in_bytes').write_text('1048576')
            (root / 'memory/memory.limit_in_bytes').write_text(str(2**63))
            (root / '7').mkdir()
            (root / '7/statm').write_text('bad')
            snapshot = memory_snapshot({'council': 7}, root, root, 4096)
            self.assertEqual(snapshot, {'cgroup_mb': 1.0, 'limit_mb': None,
                                        'rss_mb': {'council': None}})


if __name__ == '__main__':
    unittest.main()
