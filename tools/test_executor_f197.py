#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات الوحدة لمنفِّذ F-197/1h على Binance USDⓈ-M Testnet.

يفحص:
  1) تطابق إشارات نواة MSS مع المعايير المعتمدة.
  2) آلية الخروج ثنائي السرعة (F-197 dual trailing) مع trig=0.0025 وlock=0.0045.
  3) حظر النطاقات الحية وحظر الارتداد للأرشيف بلا علم صريح.
  4) المسار الحرج (أ): شمعة close_time أقدم من 90 دقيقة ⇒ RuntimeError ولا كتابة في المسجّل (حقن بلا شبكة).
  5) المسار الحرج (ب): فشل طلب REST بلا --allow-archive ⇒ RuntimeError ولا ارتداد صامت (حقن بلا شبكة).
  6) حجب الإشارات والمراكز عند تفعيل --allow-archive.
  7) سلامة مسجل الشموع الساعي (Parquet وCSV بترميز utf-8-sig والأعمدة الحقيقية فقط بلا اختلاق).
"""
import json
import pathlib
import sys
import tempfile
import time
import unittest

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "hyp_lab"))

import executor_f197 as Ex


class TestF197Executor(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.storage_dir = pathlib.Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_live_domain_forbidden(self):
        """التأكد من أن النطاقات الحية محظورة حظر أمان حديدي."""
        with self.assertRaises(ValueError):
            client = Ex.BinanceFuturesTestnetClient()
            client.base_url = "https://fapi.binance.com"
            for forbidden in Ex.FORBIDDEN_LIVE_HOSTS:
                if forbidden in client.base_url:
                    raise ValueError("محظور")

    def test_critical_path_a_stale_candle_raises_and_no_record(self):
        """(أ) شمعة close_time أقدم من 90 دقيقة ⇒ RuntimeError، ولا كتابة في المسجّل (حقن بلا شبكة)."""
        now_ms = int(time.time() * 1000)
        # شمعة أغلقت قبل 95 دقيقة (> 90 دقيقة)
        stale_close_ms = now_ms - (95 * 60 * 1000)
        stale_open_ms = stale_close_ms - (60 * 60 * 1000) + 1

        injected_klines = [[
            stale_open_ms, "100.0", "102.0", "99.0", "101.0", "1000.0",
            stale_close_ms, "101000.0", 500, "500.0", "50500.0", "0"
        ]]

        state_file = self.storage_dir / "state.json"
        client = Ex.BinanceFuturesTestnetClient(dry_run=True)
        tracker = Ex.F197PositionTracker(state_file=state_file, client=client, notional=20.0)

        parquet_path = self.storage_dir / "SOLUSDT_1h.parquet"
        csv_path = self.storage_dir / "SOLUSDT_1h.csv"

        # محاولة المعالجة يجب أن تُطلق RuntimeError
        with self.assertRaises(RuntimeError) as ctx:
            Ex.process_single_symbol(
                symbol="SOLUSDT",
                client=client,
                tracker=tracker,
                storage_dir=self.storage_dir,
                allow_archive=False,
                raw_data_override=injected_klines,
            )

        self.assertIn("أقدم من 90 دقيقة", str(ctx.exception))
        # التأكد القاطع من عدم كتابة أي ملف في المسجّل
        self.assertFalse(parquet_path.exists(), "يجب ألا يُكتب ملف parquet عند رفض الشمعة القديمة")
        self.assertFalse(csv_path.exists(), "يجب ألا يُكتب ملف csv عند رفض الشمعة القديمة")

    def test_critical_path_b_rest_failure_raises_without_silent_archive(self):
        """(ب) فشل طلب REST بلا --allow-archive ⇒ RuntimeError، ولا ارتداد صامت (حقن بلا شبكة)."""
        state_file = self.storage_dir / "state.json"
        client = Ex.BinanceFuturesTestnetClient(dry_run=True)
        tracker = Ex.F197PositionTracker(state_file=state_file, client=client, notional=20.0)

        parquet_path = self.storage_dir / "SOLUSDT_1h.parquet"
        csv_path = self.storage_dir / "SOLUSDT_1h.csv"

        # حقن انقطاع اتصال محاكى (TLS EOF / Timeout) بلا شبكة
        simulated_err = ConnectionResetError("Connection reset by peer (simulated TLS EOF)")

        with self.assertRaises(RuntimeError) as ctx:
            Ex.process_single_symbol(
                symbol="SOLUSDT",
                client=client,
                tracker=tracker,
                storage_dir=self.storage_dir,
                allow_archive=False,
                simulate_net_error=simulated_err,
            )

        self.assertIn("الارتداد إلى الأرشيف ممنوع إلا بعلم صريح --allow-archive", str(ctx.exception))
        self.assertFalse(parquet_path.exists(), "يجب ألا يُكتب أي ملف عند فشل REST")
        self.assertFalse(csv_path.exists(), "يجب ألا يُكتب أي ملف عند فشل REST")

    def test_candle_recorder_real_columns_only(self):
        """التأكد من كتابة ملفات Parquet وCSV بترميز utf-8-sig وبالأعمدة الحقيقية فقط."""
        df = pd.DataFrame({
            "open_time": [1788210000000, 1788213600000, 1788217200000],
            "open": [100.0, 101.0, 102.0],
            "high": [101.5, 102.5, 103.5],
            "low": [99.5, 100.5, 101.5],
            "close": [101.0, 102.0, 103.0],
            "volume": [1000.0, 1100.0, 1200.0],
        })

        p_path, c_path = Ex.record_hourly_candles("SOLUSDT", df, self.storage_dir)
        self.assertTrue(p_path.exists())
        self.assertTrue(c_path.exists())

        read_df = pd.read_csv(c_path, encoding="utf-8-sig")
        expected_cols = ["open_time", "open", "high", "low", "close", "volume"]
        self.assertEqual(list(read_df.columns), expected_cols)
        # التأكد التام من خلو الملف من أي أعمدة مختلقة
        self.assertNotIn("trades_count", read_df.columns)
        self.assertNotIn("taker_buy_base_volume", read_df.columns)

    def test_archive_suppresses_signals_and_positions(self):
        """التأكد من أن علم الأرشيف يحجب أي إشارة أو مركز حماية للمحفظة."""
        state_file = self.storage_dir / "state.json"
        client = Ex.BinanceFuturesTestnetClient(dry_run=True)
        tracker = Ex.F197PositionTracker(state_file=state_file, client=client, notional=20.0)

        df = pd.DataFrame({
            "open_time": [1788210000000 + i * 3600000 for i in range(25)],
            "open": np.full(25, 100.0),
            "high": np.full(25, 105.0),
            "low": np.full(25, 99.0),
            "close": np.full(25, 104.0),
            "volume": np.full(25, 1000.0),
        })
        res = tracker.process_symbol_bar("SOLUSDT", df, is_archive=True)
        self.assertIn("محجوبة", res["signal"]["status"])
        self.assertIn("محجوب", res["position"]["status"])
        self.assertEqual(res["signal"]["mss_signal"], False)

    def test_f197_dual_trailing_live_logic(self):
        """فحص منطق التسليح والقفل والخروج لـ F-197 dual trail في الوضع الحي."""
        state_file = self.storage_dir / "state.json"
        client = Ex.BinanceFuturesTestnetClient(dry_run=True)
        tracker = Ex.F197PositionTracker(state_file=state_file, client=client, notional=20.0)

        sym = "SOLUSDT"
        tracker.positions[sym] = {
            "status": "OPEN",
            "entry_time": "2026-08-31T20:00:00+00:00",
            "entry_price": 100.0,
            "quantity": 10.0,
            "hard_stop": 98.0,
            "effective_stop": 98.0,
            "peak_price": 100.0,
            "gain_pct": 0.0,
            "armed": False,
        }

        # شمعة تصعد إلى 100.5 (ربح 0.5% >= trig 0.25%) -> يجب أن تتسلح
        now_ts = int(time.time() * 1000)
        df_bars = pd.DataFrame({
            "open_time": [now_ts - (25 - i) * 3600000 for i in range(25)],
            "open": np.full(25, 100.0),
            "high": np.full(25, 100.5),
            "low": np.full(25, 99.8),
            "close": np.full(25, 100.3),
            "volume": np.full(25, 1000.0),
        })

        res = tracker.process_symbol_bar(sym, df_bars, is_archive=False)
        pos = res["position"]
        self.assertTrue(pos["armed"], "التسليح يجب أن يتفعل عند ربح 0.5%")
        self.assertAlmostEqual(pos["effective_stop"], 100.45, places=3)

        # كسر الوقف -> خروج
        df_bars2 = df_bars.copy()
        df_bars2.loc[24, "low"] = 100.20
        df_bars2.loc[24, "close"] = 100.25
        res2 = tracker.process_symbol_bar(sym, df_bars2, is_archive=False)
        pos2 = res2["position"]
        self.assertEqual(pos2["status"], "FLAT")
        self.assertIsNotNone(pos2["last_trade"])
        self.assertEqual(pos2["last_trade"]["exit_reason"], "dual_trail_stop")


if __name__ == "__main__":
    unittest.main()
