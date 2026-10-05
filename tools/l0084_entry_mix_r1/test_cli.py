import contextlib
import io
import unittest

try:
    from . import cli
except ImportError:
    from l0084_entry_mix_r1 import cli


class CliSafetyTests(unittest.TestCase):
    def test_measure_is_closed_before_remote_access(self):
        with self.assertRaisesRegex(RuntimeError,"measurement gate is intentionally closed"):
            cli.main(["measure"])

    def test_legacy_force_and_skip_switches_removed(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                cli.main(["measure","--force"])
        self.assertEqual(cm.exception.code,2)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                cli.main(["measure","--skip-triples"])
        self.assertEqual(cm.exception.code,2)

    def test_summarize_fails_closed_until_full_metrics_audit(self):
        with self.assertRaisesRegex(RuntimeError,"independent raw-ledger reconciliation"):
            cli.main(["summarize"])

    def test_audit_requires_explicit_full_rebuild(self):
        with self.assertRaisesRegex(RuntimeError,"Only `audit --rebuild-all`"):
            cli.main(["audit"])


if __name__ == "__main__":
    unittest.main()
