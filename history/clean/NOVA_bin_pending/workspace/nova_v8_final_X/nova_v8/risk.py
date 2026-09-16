"""Deterministic portfolio protection and audit layer.

The core research sleeves remain independent.  This module provides a second
layer for a combined portfolio replay: it can audit conflicts without changing
the approved baseline, or run in strict mode and fail closed when exposure or
loss limits are exceeded.  Limits are safety defaults, not historical
optimisation parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from . import config as C


@dataclass(frozen=True)
class RiskDecision:
    accepted: bool
    reasons: tuple[str, ...]


def _parse_time(value: Any):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _strategy(rec: dict) -> str:
    return str(rec.get("strategy") or rec.get("kind") or rec.get("category") or "unknown")


def _notional(rec: dict) -> float:
    value = rec.get("notional_usd")
    try:
        if value is not None and float(value) > 0:
            return float(value)
    except (TypeError, ValueError):
        pass
    if _strategy(rec) == "grid":
        return float(C.GRID_CAPITAL_USD)
    return float(C.NOTIONAL_BASE) * max(1, int(rec.get("mult", 1) or 1))


def _pnl(rec: dict) -> float:
    try:
        return float(rec.get("pnl_usd", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def audit_records(records: list[dict], mode: str | None = None) -> dict:
    """Audit records in chronological entry order.

    A strict hypothetical path is always simulated to produce meaningful
    ``would_block`` reasons.  In ``audit`` mode the original independent result
    remains accepted, while the report exposes what strict portfolio mode would
    have rejected.  In ``strict`` mode blocked records are marked rejected.
    """
    mode = (mode or C.PORTFOLIO_RISK_MODE).lower()
    def _sort_key(r):
        t = _parse_time(r.get("entry_time"))
        return (t.timestamp() if t is not None else float("-inf"),
                int(r.get("entry_bar", 0)))

    ordered = sorted(records, key=_sort_key)
    active: list[dict] = []
    accepted: list[dict] = []
    blocked: list[dict] = []
    realized = 0.0
    peak = 0.0
    daily: dict[str, float] = {}
    halted = False

    def expire(now):
        nonlocal realized, peak, halted
        keep = []
        for item in active:
            xt = _parse_time(item.get("exit_time"))
            if xt is not None and xt <= now:
                realized += _pnl(item)
                dt = xt.date().isoformat()
                daily[dt] = daily.get(dt, 0.0) + _pnl(item)
            else:
                keep.append(item)
        active[:] = keep
        peak = max(peak, realized)
        if (peak - realized) > C.PORTFOLIO_CAPITAL_USD * C.RISK_MAX_DRAWDOWN_PCT:
            halted = True

    for rec in ordered:
        rec["risk_accepted"] = True
        rec["risk_reason"] = ""
        rec["risk_would_block"] = False
        now = _parse_time(rec.get("entry_time"))
        if now is not None:
            expire(now)
        strategy = _strategy(rec)
        symbol = str(rec.get("symbol", ""))
        notional = _notional(rec)
        gross = sum(_notional(x) for x in active)
        symbol_gross = sum(_notional(x) for x in active if str(x.get("symbol", "")) == symbol)
        strategy_gross = sum(_notional(x) for x in active if _strategy(x) == strategy)
        reasons = []
        if halted:
            reasons.append("portfolio_drawdown_halt")
        if len(active) >= C.RISK_MAX_OPEN_POSITIONS:
            reasons.append("max_open_positions")
        # Multiple tranches of one long-cycle series are one intentional sleeve
        # position; they must not collide with themselves.  A different sleeve
        # or series on the same symbol still consumes the collision budget.
        same_symbol_other_series = sum(
            1 for x in active
            if str(x.get("symbol", "")) == symbol
            and not (_strategy(x) == strategy
                     and str(x.get("series", "")) == str(rec.get("series", "")))
        )
        if same_symbol_other_series >= C.RISK_MAX_OPEN_PER_SYMBOL:
            reasons.append("symbol_collision")
        if gross + notional > C.PORTFOLIO_CAPITAL_USD * C.RISK_MAX_GROSS_EXPOSURE_PCT:
            reasons.append("gross_exposure")
        if symbol_gross + notional > C.PORTFOLIO_CAPITAL_USD * C.RISK_MAX_SYMBOL_EXPOSURE_PCT:
            reasons.append("symbol_exposure")
        if strategy_gross + notional > C.PORTFOLIO_CAPITAL_USD * C.RISK_MAX_STRATEGY_EXPOSURE_PCT:
            reasons.append("strategy_exposure")
        dt = now.date().isoformat() if now is not None else "unknown"
        if daily.get(dt, 0.0) < -(C.PORTFOLIO_CAPITAL_USD * C.RISK_MAX_DAILY_LOSS_PCT):
            reasons.append("daily_loss_limit")

        rec["risk_would_block"] = bool(reasons)
        rec["risk_reason"] = ",".join(reasons)
        strict_accept = not reasons
        rec["risk_accepted"] = strict_accept if mode == "strict" else True
        if strict_accept:
            active.append(rec)
            accepted.append(rec)
        else:
            blocked.append(rec)

    # Close remaining accepted positions for the final realised audit total.
    for item in active:
        realized += _pnl(item)
    return {
        "mode": mode,
        "total": len(records),
        "strict_accepted": len(accepted),
        "would_block": len(blocked),
        "reported_accepted": sum(1 for r in records if r.get("risk_accepted", True)),
        "gross_final_open": sum(_notional(x) for x in active),
        "realized_pnl": realized,
        "halted": halted,
        "accepted_records": accepted,
        "blocked_records": blocked,
    }


def write_report(result: dict, path) -> None:
    """Write a human-readable risk audit without altering the approved report."""
    lines = [
        "NOVA_V8 — Portfolio Risk Audit / حماية المحفظة",
        "",
        f"الوضع: {result['mode']} (audit لا يغيّر Baseline؛ strict يرفض السجلات المحظورة)",
        f"إجمالي السجلات: {result['total']}",
        f"المقبولة في المحاكاة الصارمة: {result['strict_accepted']}",
        f"التي كان سيحظرها الحارس: {result['would_block']}",
        f"المقبولة في التقرير الحالي: {result['reported_accepted']}",
        f"التعرض المفتوح النهائي التقريبي: {result['gross_final_open']:.2f}$",
        f"الصافي المحقق التقريبي: {result['realized_pnl']:.2f}$",
        f"حالة Kill/Halt: {'مفعلة' if result['halted'] else 'غير مفعلة'}",
        "",
        "قواعد الحماية: حد إجمالي، حد للعملة، حد للاستراتيجية، منع تصادم العملة، حد عدد الصفقات، وسحب رأسمالي.",
        "القيم الافتراضية دفاعية وليست معايرة تاريخية؛ لا تعني أن النظام صالح للأموال الخارجية.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
