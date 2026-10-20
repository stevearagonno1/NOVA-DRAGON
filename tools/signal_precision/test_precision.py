import unittest
import numpy as np
import precision as P


class PrecisionTests(unittest.TestCase):
    def test_counts_false_alerts_outside_rises_and_censors_tail(self):
        # Four eligible decisions: success, failure, failure, unresolved.
        c = np.array([100., 101., 100., 99.])
        raw, rows = P.evaluate(c, {'signal': np.ones(4, bool)}, np.ones(4, bool), 1, .005)
        row = rows[0]
        self.assertEqual((row['true_alerts'], row['false_alerts'], row['unresolved_alerts']), (1, 2, 1))
        self.assertEqual(row['precision'], 1 / 3)
        self.assertEqual(row['alerts'], 4)
        self.assertEqual(P.audit(raw, rows), 1)

    def test_current_bar_and_beyond_horizon_do_not_count(self):
        raw, rows = P.evaluate([100., 100., 110.], {'s': [True, False, False]}, [True]*3, 1, .005)
        self.assertEqual(rows[0]['false_alerts'], 1)

    def test_full_horizon_required_even_if_early_target_hit(self):
        _, rows = P.evaluate([100., 110.], {'s': [True, False]}, [True]*2, 2, .005)
        self.assertEqual(rows[0]['unresolved_alerts'], 1)
        self.assertIsNone(rows[0]['precision'])

    def test_exact_threshold_and_zero_alerts(self):
        _, rows = P.evaluate([100., 101., 100.], {'s': [True, False, False], 'zero': [False]*3}, [True]*3, 1, .01)
        self.assertEqual(rows[0]['true_alerts'], 1)
        self.assertIsNone(rows[1]['precision'])
        self.assertEqual(rows[1]['opportunity_coverage'], 0)

    def test_audit_rederives_labels_and_counts(self):
        raw, rows = P.evaluate([100., 110., 100.], {'s': [True, True, False]}, [True]*3, 1, .005)
        rows[0]['false_alerts'] = 0
        with self.assertRaises(AssertionError):
            P.audit(raw, rows)

    def test_invalid_inputs_rejected(self):
        for c, h in [([100., float('nan')], 1), ([100., 0.], 1), ([100., 101.], 0)]:
            with self.assertRaises(ValueError):
                P.evaluate(c, {'s': [True]*len(c)}, [True]*len(c), h, .005)

    def test_singletons_exclude_inherited_composites(self):
        grid = P.singletons()
        self.assertEqual(len(grid), 536)
        self.assertFalse(any(q['origin']=='registered_L0092_setting' and q['settings']['mode']!='STANDALONE' for q in grid))


if __name__ == '__main__':
    unittest.main()
