#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""منفِّذ Binance USDⓈ-M Testnet لـ F-197 على فريم الساعة (1h) مع مسجّل شموع ساعي (F-157/F-193).

القواعد المجمّدة (وثيقة L0007-hyp-lab-five-year.md وتوجيهات الإدارة):
  1) المعاملات: SOL/XLM/LINK/FIL على trig=0.0025 وlock=0.0045 (هضبة 8/8 معتمدة).
  2) الدخول: نواة MSS الافتراضية (F-126: body_ratio=0.50, range_atr=0.80, lookback=20).
  3) الخروج: dual trailing كما في L0007-tf1h (wide=0.0020, tight=0.0008, stop=2.0×ATR).
  4) البيانات: طلب REST واحد لكل عملة بعد إغلاق شمعة الساعة من:
     https://data-api.binance.vision/api/v3/klines (سبب ترك WebSocket: حجب DNS لنطاق stream.binance.com).
  5) الارتداد إلى الأرشيف ممنوع إلا بعلم صريح --allow-archive، وعندها تُطبع
     في الترويسة عبارة «بيانات أرشيف — ليست حيّة» وتُحجب أي إشارة أو مركز.
  6) رفض قاطع (raise) لأي شمعة close_time أقدم من 90 دقيقة في الوضع الحي — لا إشارة، لا مركز، لا تسجيل.
  7) المسجّل لا يكتب إلا ما وصل فعلاً من المصدر (لا اختلاق لأي أعمدة: ما لم يُقَس يُكتب «غير مقاسة»).
  8) التنفيذ: Binance USDⓈ-M Testnet فقط (https://testnet.binancefuture.com). لا مال حقيقي.
     المفتاح من متغيرات بيئة Render (BINANCE_TESTNET_API_KEY/SECRET)، بصلاحيات تداول فقط وبلا سحب.
     وإن فشل أمر يُسجَّل ولا يُعاد أعمى.
  9) لا تعديل داخل nova_v8/** — المنفِّذ يستورد ولا يعدّل. وcanary قبل أي تشغيل.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import hmac
import json
import logging
import os
import pathlib
import subprocess
import sys
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# استيراد من hyp_lab بلا مساس بـ nova_v8/** المجمّد
REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "hyp_lab"))
sys.path.insert(0, str(REPO))

from common import TF_MINUTES, atr, hh, ll, load, to_bars  # noqa: E402
import F_126_mss_core as M126  # noqa: E402
import F_197_dual_trail as M197  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("f197_executor")

# ══════════════════════════════════════════════════════════════════════════════
# الثوابت المجمّدة (L0007-tf1h)
# ══════════════════════════════════════════════════════════════════════════════
SYMBOLS = ["SOLUSDT", "XLMUSDT", "LINKUSDT", "FILUSDT"]
TRIG = 0.0025           # عتبة تسليح التتبع (0.25%)
LOCK = 0.0045           # حد قفل الأرباح الأدنى عند التسليح (0.45%)
WIDE = M197.WIDE        # التتبع الواسع 0.0020 عند ربح <= 1%
TIGHT = M197.TIGHT      # التتبع الخانق 0.0008 عند ربح > 1%
STOP_ATR_MULT = 2.0     # الوقف القاسي الأولي 2.0×ATR14
NOTIONAL_DEFAULT = 20.0  # §27  # القيمة الاسمية للصفقة بالدولار (عقد L0007)
TIMEFRAME = "1h"
LOOKBACK_MSS = 20
BODY_RATIO_MSS = 0.50
RANGE_ATR_MSS = 0.80
MAX_CANDLE_AGE_MINUTES = 90.0  # الحد الأقصى لعمر الشمعة الحية (90 دقيقة)

# عناوين واجهات البرمجة
BINANCE_DATA_REST_URL = "https://data-api.binance.vision/api/v3/klines"
FUTURES_TESTNET_BASE_URL = "https://testnet.binancefuture.com"
FORBIDDEN_LIVE_HOSTS = ("fapi.binance.com", "api.binance.com")


# ══════════════════════════════════════════════════════════════════════════════
# 1) بوابة الكاناري الإلزامية قبل أي تشغيل
# ══════════════════════════════════════════════════════════════════════════════
def run_canary_gate() -> bool:
    """تشغيل tools/canary.py للتأكد من سلامة البيئة والمحرك والبيانات قبل أي تنفيذ."""
    canary_script = REPO / "tools" / "canary.py"
    if not canary_script.exists():
        log.error("ملف الكاناري غير موجود: %s", canary_script)
        return False
    log.info("جاري فحص بوابة الكاناري الإلزامية (tools/canary.py)...")
    res = subprocess.run([sys.executable, str(canary_script)], capture_output=True, text=True)
    if res.returncode == 0:
        log.info("✅ اجتاز الكاناري بنجاح: البيئة والمحرك مطابقان للمرجع الموثق.")
        return True
    else:
        log.error("❌ فشل الكاناري! لا يمكن بدء المنفذ.\n%s\n%s", res.stdout, res.stderr)
        return False


# ══════════════════════════════════════════════════════════════════════════════
# 2) جلب البيانات بطلب REST واحد مع تطبيق حواجز الأمان
# ══════════════════════════════════════════════════════════════════════════════
def get_storage_dir() -> pathlib.Path:
    """تحديد مجلد التخزين الدائم (Render Persistent Disk أو المسار المعتمد)."""
    p = os.getenv("RENDER_DISK_PATH") or os.getenv("RECORDER_DIR") or str(REPO / "data" / "recorder")
    path = pathlib.Path(p)
    path.mkdir(parents=True, exist_ok=True)
    return path


def fetch_klines_rest_single(
    symbol: str,
    limit: int = 100,
    allow_archive: bool = False,
    raw_data_override: list | None = None,
    simulate_net_error: Exception | None = None,
) -> Tuple[pd.DataFrame, str, bool]:
    """طلب REST واحد لكل عملة لجلب الشموع الساعية من data-api.binance.vision.

    القواعد:
      - WebSocket ممنوع (بسبب حجب DNS لنطاق stream.binance.com على شبكة المستخدم).
      - رفض قاطع (raise) لأي شمعة close_time أقدم من 90 دقيقة في الوضع الحي.
      - الارتداد إلى الأرشيف ممنوع إلا بعلم صريح --allow-archive.
      - لا اختلاق لأي أعمدة غير موجودة في المصدر.
      - دعم الحقن (raw_data_override / simulate_net_error) للاختبارات المعزولة بلا شبكة.
    ترجع: (df, source_name, is_archive)
    """
    now_ms = int(time.time() * 1000)
    raw_data = None
    rest_error = simulate_net_error

    if raw_data_override is not None:
        raw_data = raw_data_override
    elif simulate_net_error is None:
        import urllib.request
        params = urllib.parse.urlencode({
            "symbol": symbol,
            "interval": "1h",
            "limit": limit,
        })
        url = f"{BINANCE_DATA_REST_URL}?{params}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NOVA-Dragon/8.0; +https://github.com)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    raw_data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            rest_error = exc

    # معالجة نجاح طلب REST (أو البيانات المحقونة للاختبار)
    if raw_data is not None and isinstance(raw_data, list) and len(raw_data) > 0:
        rows = []
        for k in raw_data:
            close_time = int(k[6])
            # نتجاهل الشمعة الحية التي لا تزال مفتوحة
            if close_time > now_ms:
                continue
            rows.append({
                "open_time": int(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "_close_time": close_time,
            })
        if rows:
            latest_close = rows[-1]["_close_time"]
            age_minutes = (now_ms - latest_close) / 60000.0
            # القاعدة 4: رفض قاطع (raise) لأي شمعة أقدم من 90 دقيقة في الوضع الحي
            if age_minutes > MAX_CANDLE_AGE_MINUTES:
                raise RuntimeError(
                    f"رفض قاطع: شمعة {symbol} المستلمة من REST أقدم من 90 دقيقة (مغلقة منذ {age_minutes:.1f} دقيقة). "
                    "لا إشارة، لا مركز، لا تسجيل."
                )
            df = pd.DataFrame(rows)
            df = df[["open_time", "open", "high", "low", "close", "volume"]]
            return df, f"REST {BINANCE_DATA_REST_URL}", False

    # في حال فشل طلب REST المباشر:
    if not allow_archive:
        # القاعدة 3: الارتداد إلى الأرشيف ممنوع إلا بعلم صريح --allow-archive
        raise RuntimeError(
            f"فشل طلب REST لـ {symbol} من {BINANCE_DATA_REST_URL} ({rest_error}). "
            "الارتداد إلى الأرشيف ممنوع إلا بعلم صريح --allow-archive."
        )

    # مسار الأرشيف المسموح به فقط عند وجود العلم الصريح --allow-archive
    archive_file = REPO / "crypto_archive" / f"{symbol}_1m.parquet"
    if archive_file.exists():
        df1m = load(str(archive_file))
        df1h = to_bars(df1m, 60).tail(limit).copy()
        df1h["open_time"] = [int(ts.timestamp() * 1000) for ts in df1h.index]
        df1h = df1h[["open_time", "open", "high", "low", "close", "volume"]].copy()
        return df1h, f"crypto_archive/{symbol}_1m.parquet (بيانات أرشيف — ليست حيّة)", True

    raise RuntimeError(f"تعذّر توفير شموع 1h للرمز {symbol} (الأرشيف غير موجود)")


# ══════════════════════════════════════════════════════════════════════════════
# 3) مسجّل الشموع الساعي (Parquet / CSV بترميز utf-8-sig)
# ══════════════════════════════════════════════════════════════════════════════
def record_hourly_candles(symbol: str, df_klines: pd.DataFrame, storage_dir: pathlib.Path) -> Tuple[pathlib.Path, pathlib.Path]:
    """تسجيل الشموع الساعية في ملفات Parquet وCSV.

    القواعد:
      - الأعمدة المكتوبة هي فقط الأعمدة المقروءة فعلياً من المصدر (open_time, open, high, low, close, volume).
      - لا اختلاق لأي أرقام لم ترد في الأصل.
      - كتابة CSV دائماً بترميز utf-8-sig عملاً بالقاعدة 6 من AGENTS.md.
      - لا يحتاج أي مفتاح API.
    """
    storage_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = storage_dir / f"{symbol}_1h.parquet"
    csv_path = storage_dir / f"{symbol}_1h.csv"

    # التأكد من الترتيب وعدم وجود أعمدة غريبة
    clean_cols = ["open_time", "open", "high", "low", "close", "volume"]
    df_to_save = df_klines[clean_cols].copy()

    if parquet_path.exists():
        try:
            old_df = pd.read_parquet(parquet_path)
            combined = pd.concat([old_df, df_to_save])
            combined = combined.drop_duplicates(subset=["open_time"], keep="last").sort_values("open_time")
        except Exception:
            combined = df_to_save
    else:
        combined = df_to_save

    combined.to_parquet(parquet_path, index=False)
    combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return parquet_path, csv_path


# ══════════════════════════════════════════════════════════════════════════════
# 4) عميل Binance USDⓈ-M Testnet والتنفيذ الآمن
# ══════════════════════════════════════════════════════════════════════════════
class BinanceFuturesTestnetClient:
    """عميل مخصص لـ Binance USDⓈ-M Futures Testnet."""

    def __init__(self, api_key: str | None = None, api_secret: str | None = None, dry_run: bool = False):
        self.base_url = FUTURES_TESTNET_BASE_URL
        for forbidden in FORBIDDEN_LIVE_HOSTS:
            if forbidden in self.base_url:
                raise ValueError(f"حظر أمان قاطع: محاولة الاتصال بالنظام الحي {forbidden}!")

        self.api_key = api_key or os.getenv("BINANCE_TESTNET_API_KEY") or os.getenv("BINANCE_API_KEY") or ""
        self.api_secret = api_secret or os.getenv("BINANCE_TESTNET_API_SECRET") or os.getenv("BINANCE_API_SECRET") or ""
        self.dry_run = dry_run or not (self.api_key and self.api_secret)

    def _sign(self, params: dict) -> str:
        query = urllib.parse.urlencode(sorted(params.items()))
        return hmac.new(self.api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()

    def place_order(self, symbol: str, side: str, qty: float, order_type: str = "MARKET") -> dict:
        """إرسال أمر إلى Testnet. إن فشل يُسجَّل ولا يُعاد أعمى."""
        if self.dry_run:
            log.info("[DRY-RUN Testnet] محاكاة أمر: %s %s qty=%.4f type=%s", side, symbol, qty, order_type)
            return {
                "status": "FILLED",
                "symbol": symbol,
                "side": side,
                "origQty": str(qty),
                "executedQty": str(qty),
                "orderId": int(time.time() * 1000),
                "dry_run": True,
            }

        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": f"{qty:.4f}".rstrip("0").rstrip("."),
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000,
        }
        params["signature"] = self._sign(params)

        import urllib.request
        url = f"{self.base_url}/fapi/v1/order"
        data = urllib.parse.urlencode(params).encode("utf-8")
        headers = {
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                log.info("تم تنفيذ أمر Testnet: orderId=%s symbol=%s side=%s", result.get("orderId"), symbol, side)
                return result
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8")
            log.error("❌ فشل أمر Testnet لـ %s (%s): HTTP %s - الرد: %s. لن يُعاد أعمى.",
                      symbol, side, exc.code, err_body)
            return {"status": "FAILED", "code": exc.code, "error": err_body}
        except Exception as exc:
            log.error("❌ خطأ غير متوقع أثناء إرسال أمر %s: %s. لن يُعاد أعمى.", symbol, exc)
            return {"status": "FAILED", "error": str(exc)}


# ══════════════════════════════════════════════════════════════════════════════
# 5) آلة حالات الاستراتيجية F-197 مع خروج Dual Trailing
# ══════════════════════════════════════════════════════════════════════════════
class F197PositionTracker:
    """مدير حالات المراكز لـ F-197 dual trail على شمعة الساعة."""

    def __init__(self, state_file: pathlib.Path, client: BinanceFuturesTestnetClient, notional: float = NOTIONAL_DEFAULT):
        self.state_file = state_file
        self.client = client
        self.notional = notional
        self.positions: Dict[str, dict] = self._load_state()

    def _load_state(self) -> Dict[str, dict]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                log.warning("تعذّر قراءة ملف الحالة: %s. بدء حالة جديدة.", exc)
        return {sym: {"status": "FLAT", "last_trade": None} for sym in SYMBOLS}

    def save_state(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.positions, f, ensure_ascii=False, indent=2)

    def process_symbol_bar(self, symbol: str, df: pd.DataFrame, is_archive: bool) -> dict:
        """معالجة شمعة الرمز:
        إذا كانت البيانات من الأرشيف (بموجب --allow-archive)، تُحجب أي إشارة أو مركز حمايةً للحساب.
        """
        # تجهيز إطار زمني مرتب للمؤشرات
        df_calc = df.copy()
        if "open_time" in df_calc.columns and not isinstance(df_calc.index, pd.DatetimeIndex):
            df_calc.index = pd.to_datetime(df_calc["open_time"], unit="ms", utc=True)
        df_calc = df_calc.sort_index()

        last_idx = df_calc.index[-1]
        last_bar = df_calc.iloc[-1]
        open_px = float(last_bar["open"])
        close_px = float(last_bar["close"])
        high_px = float(last_bar["high"])
        low_px = float(last_bar["low"])
        vol = float(last_bar["volume"])

        # القاعدة 3: عند الارتداد للأرشيف، تُحجب أي إشارة أو مركز
        if is_archive:
            return {
                "symbol": symbol,
                "candle": {
                    "time": last_idx.isoformat(),
                    "open": open_px,
                    "high": high_px,
                    "low": low_px,
                    "close": close_px,
                    "volume": vol,
                },
                "signal": {
                    "status": "محجوبة (بيانات أرشيف — ليست حيّة)",
                    "mss_signal": False,
                },
                "position": {
                    "status": "محجوب (بيانات أرشيف — ليست حيّة)",
                },
            }

        # ── الحساب الحي الطبيعي ──
        pos = self.positions.get(symbol, {"status": "FLAT", "last_trade": None})
        atr_series = atr(df_calc, 14)
        atr_val = float(atr_series.iloc[-1])
        mss_series = M126.mss_signal(df_calc, body_ratio=BODY_RATIO_MSS, range_atr=RANGE_ATR_MSS, lookback=LOOKBACK_MSS)
        mss_signal_val = bool(mss_series.iloc[-1])

        hh_series = hh(df_calc, LOOKBACK_MSS)
        hh_val = float(hh_series.iloc[-1])
        body_val = abs(close_px - open_px)
        range_val = max(high_px - low_px, 1e-9)
        body_ratio = body_val / range_val
        range_atr_ratio = range_val / max(atr_val, 1e-9)

        signal_info = {
            "mss_signal": mss_signal_val,
            "hh_20": round(hh_val, 4),
            "body_ratio": round(body_ratio, 4),
            "range_atr_ratio": round(range_atr_ratio, 4),
            "atr_14": round(atr_val, 4),
        }

        # فحص المركز المفتوح (Dual Exit)
        if pos.get("status") == "OPEN":
            entry_px = float(pos["entry_price"])
            hard_stop = float(pos["hard_stop"])
            peak_px = max(float(pos.get("peak_price", entry_px)), high_px)
            pos["peak_price"] = peak_px

            gain = (peak_px - entry_px) / entry_px
            eff_stop = hard_stop
            armed = False

            if gain >= TRIG:
                armed = True
                trail = WIDE if gain <= 0.01 else TIGHT
                local_stop = max(entry_px * (1.0 + LOCK), peak_px * (1.0 - trail))
                eff_stop = max(hard_stop, local_stop)

            pos["effective_stop"] = eff_stop
            pos["gain_pct"] = round(gain * 100, 3)
            pos["armed"] = armed

            if low_px <= eff_stop:
                exit_px = min(eff_stop, high_px)
                log.info("🔔 خروج F-197 dual لـ %s: ضرب الوقف عند %.4f (دخول %.4f)", symbol, exit_px, entry_px)
                order_res = self.client.place_order(symbol=symbol, side="SELL", qty=pos["quantity"])
                pnl = pos["quantity"] * (exit_px * (1.0 - 0.0013) - entry_px)
                pos["last_trade"] = {
                    "entry_time": pos["entry_time"],
                    "exit_time": last_idx.isoformat(),
                    "entry_price": entry_px,
                    "exit_price": exit_px,
                    "quantity": pos["quantity"],
                    "pnl_usd": round(pnl, 4),
                    "exit_reason": "dual_trail_stop" if armed else "hard_stop",
                    "order_response": order_res,
                }
                pos["status"] = "FLAT"

        # فحص مركز محايد ودخول جديد
        elif pos.get("status") == "FLAT":
            if mss_signal_val:
                log.info("🚀 إشارة دخول MSS لـ %s عند %s (إغلاق=%.4f)", symbol, last_idx, close_px)
                entry_est = close_px
                qty = self.notional / entry_est
                if symbol == "XLMUSDT":
                    qty = round(qty)
                elif symbol in ("SOLUSDT", "LINKUSDT", "FILUSDT"):
                    qty = round(qty, 2)

                order_res = self.client.place_order(symbol=symbol, side="BUY", qty=qty)
                hard_stop = entry_est - STOP_ATR_MULT * atr_val
                pos["status"] = "OPEN"
                pos["entry_time"] = last_idx.isoformat()
                pos["entry_price"] = entry_est
                pos["quantity"] = qty
                pos["hard_stop"] = hard_stop
                pos["effective_stop"] = hard_stop
                pos["peak_price"] = entry_est
                pos["gain_pct"] = 0.0
                pos["armed"] = False
                pos["order_id"] = order_res.get("orderId")

        self.positions[symbol] = pos
        self.save_state()

        return {
            "symbol": symbol,
            "candle": {
                "time": last_idx.isoformat(),
                "open": open_px,
                "high": high_px,
                "low": low_px,
                "close": close_px,
                "volume": vol,
            },
            "signal": signal_info,
            "position": dict(pos),
        }


# ══════════════════════════════════════════════════════════════════════════════
# 6) دورة التشغيل وتوليد السجل
# ══════════════════════════════════════════════════════════════════════════════
def process_single_symbol(
    symbol: str,
    client: BinanceFuturesTestnetClient,
    tracker: F197PositionTracker,
    storage_dir: pathlib.Path,
    allow_archive: bool = False,
    raw_data_override: list | None = None,
    simulate_net_error: Exception | None = None,
) -> dict:
    """معالجة رمز واحد: جلب الشمعة -> تسجيل في Parquet/CSV -> معالجة الإشارة والمركز."""
    df_klines, source_name, is_archive = fetch_klines_rest_single(
        symbol,
        limit=100,
        allow_archive=allow_archive,
        raw_data_override=raw_data_override,
        simulate_net_error=simulate_net_error,
    )
    # لا يُسجَّل في القرص إلا بعد اجتياز فحص حداثة الشمعة (<=90 دقيقة) وفحص الشبكة
    p_path, c_path = record_hourly_candles(symbol, df_klines, storage_dir)
    res = tracker.process_symbol_bar(symbol, df_klines, is_archive=is_archive)
    res["source_name"] = source_name
    res["is_archive"] = is_archive
    res["parquet_file"] = str(p_path)
    res["csv_file"] = str(c_path)
    return res


def run_cycle(client: BinanceFuturesTestnetClient, tracker: F197PositionTracker, storage_dir: pathlib.Path, allow_archive: bool) -> List[dict]:
    results = []
    for sym in SYMBOLS:
        log.info("جاري طلب شمعة %s...", sym)
        res = process_single_symbol(sym, client, tracker, storage_dir, allow_archive=allow_archive)
        results.append(res)
    return results


def format_execution_log(results: List[dict], canary_passed: bool) -> str:
    """تنسيق تقرير سجل التشغيل مع الالتزام الصارم بكل ضوابط الأمان."""
    lines = []
    lines.append("═" * 78)
    lines.append(" NOVA_V8 — سجل تشغيل منفِّذ F-197/1h (Binance USDⓈ-M Testnet)")
    lines.append("═" * 78)
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"  تاريخ ووقت التشغيل : {now_str}")
    lines.append(f"  بوابة الكاناري       : {'✅ PASS' if canary_passed else '❌ FAIL'}")
    lines.append("  المعاملات المجمّدة  : trig=0.0025 | lock=0.0045 | stop=2.0×ATR | notional=20$")

    any_archive = any(r.get("is_archive") for r in results)
    if any_archive:
        lines.append("  ⚠️ تحذير الحالة     : «بيانات أرشيف — ليست حيّة» (حجب كامل للإشارات والمراكز)")
    else:
        lines.append("  حالة البيانات       : بيانات حيّة مستلمة عبر REST")

    lines.append("  مجرى البيانات        : طلب REST واحد لكل عملة (WebSocket ملغى: حجب DNS لنطاق stream.binance.com)")
    lines.append("  المسجّل الساعي       : Parquet/CSV بترميز utf-8-sig (أعمدة حقيقية فقط بلا اختلاق)")
    lines.append("─" * 78)

    for r in results:
        sym = r["symbol"]
        c = r["candle"]
        s = r["signal"]
        p = r["position"]
        src = r.get("source_name", "غير محدد")
        is_arch = r.get("is_archive", False)

        lines.append(f"\n▶ [{sym}] — فريم 1h:")
        lines.append(f"  • المصدر الفعلي    : {src}")
        lines.append(f"  1) الشمعة المقروءة : وقت {c['time']}")
        lines.append(f"     الأسعار         : Open={c['open']:<9.4f} | High={c['high']:<9.4f} | Low={c['low']:<9.4f} | Close={c['close']:<9.4f}")
        lines.append(f"     الحجم والصفقات  : Volume={c['volume']:<10.2f} | صفقات التدفق (F-157/F-193): غير مقاسة")

        if is_arch:
            lines.append(f"  2) الإشارة المولّدة : {s.get('status')}")
            lines.append(f"  3) حالة المركز     : {p.get('status')}")
        else:
            lines.append(f"  2) الإشارة المولّدة : MSS_Signal={'🟢 TRUE' if s.get('mss_signal') else '⚪ FALSE'}")
            lines.append(f"     المقاييس        : HH(20)={s.get('hh_20')} | نسبة الجسم={s.get('body_ratio')} | المدى/ATR={s.get('range_atr_ratio')} | ATR14={s.get('atr_14')}")
            status_tag = f"🟢 مفتوح (OPEN)" if p.get("status") == "OPEN" else "⚪ محايد (FLAT)"
            lines.append(f"  3) حالة المركز     : {status_tag}")
            if p.get("status") == "OPEN":
                lines.append(f"     تفاصيل المركز   : سعر الدخول={p.get('entry_price')} | الوقف الفعّال={p.get('effective_stop')} | الربح={p.get('gain_pct')}%")
            elif p.get("last_trade"):
                lt = p["last_trade"]
                lines.append(f"     آخر صفقة مغلقة  : ربح/خسارة={lt.get('pnl_usd'):+.2f}$ ({lt.get('exit_reason')})")

        lines.append(f"  4) التخزين           : {r.get('csv_file')} + parquet")

    lines.append("\n" + "═" * 78)
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# نقطة الإدخال الرئيسية
# ══════════════════════════════════════════════════════════════════════════════
def main() -> int:
    parser = argparse.ArgumentParser(description="منفِّذ Testnet لـ F-197/1h مع مسجّل شموع ساعي")
    parser.add_argument("--once", action="store_true", default=True, help="تشغيل دورة واحدة فورية للتسليم والفحص")
    parser.add_argument("--allow-archive", action="store_true", help="السماح الصريح بالارتداد للأرشيف في غياب الاتصال (يحجب الإشارات والمراكز)")
    parser.add_argument("--daemon", action="store_true", help="تشغيل مستمر عند رأس كل ساعة")
    parser.add_argument("--skip-canary", action="store_true", help="تخطي فحص الكاناري (غير مستحسن)")
    parser.add_argument("--dry-run", action="store_true", help="فرض وضع المحاكاة بدون إرسال إلى الشبكة")
    args = parser.parse_args()

    # دعم متغير البيئة ALLOW_ARCHIVE إن وُجد
    allow_archive = args.allow_archive or (os.getenv("ALLOW_ARCHIVE", "").lower() in ("1", "true", "yes"))

    if not args.skip_canary:
        canary_ok = run_canary_gate()
        if not canary_ok:
            sys.exit(1)
    else:
        canary_ok = False

    storage_dir = get_storage_dir()
    state_file = storage_dir / "f197_testnet_state.json"
    client = BinanceFuturesTestnetClient(dry_run=args.dry_run)
    tracker = F197PositionTracker(state_file=state_file, client=client, notional=NOTIONAL_DEFAULT)

    if args.daemon:
        log.info("بدء وضع الخدمة المستمرة (Daemon)...")
        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            seconds_until_next_hour = 3600 - (now.minute * 60 + now.second) + 15
            log.info("بانتظار إغلاق شمعة الساعة القادمة خلال %d ثانية...", seconds_until_next_hour)
            time.sleep(seconds_until_next_hour)
            results = run_cycle(client, tracker, storage_dir, allow_archive=allow_archive)
            report = format_execution_log(results, canary_ok)
            print(report, flush=True)
    else:
        results = run_cycle(client, tracker, storage_dir, allow_archive=allow_archive)
        report = format_execution_log(results, canary_ok)
        print(report, flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
