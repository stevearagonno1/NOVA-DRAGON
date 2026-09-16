"""Independent strategy-sleeve registry.

The registry gives every strategy a stable identity and an explicit activation
state.  Sleeves can live in the same package while keeping signals, ledgers,
and risk budgets separate.  The two newly approved sleeves are research-ready
when selected explicitly, but remain outside the default core Baseline.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    title: str
    status: str
    live_enabled: bool = False
    shares_core_signals: bool = False


STRATEGIES: tuple[StrategySpec, ...] = (
    StrategySpec("directional", "Directional trigger sleeve", "active"),
    StrategySpec("grid", "Spot grid sleeve", "active"),
    StrategySpec("btc_leadlag", "BTC lead-lag sleeve", "active"),
    StrategySpec("long_cycle", "Long-horizon cycle sleeve", "research_ready"),
    StrategySpec("market_open", "Market-open expansion sleeve", "research_ready"),
)

_BY_ID = {s.strategy_id: s for s in STRATEGIES}


def get(strategy_id: str) -> StrategySpec:
    try:
        return _BY_ID[strategy_id]
    except KeyError as exc:
        raise KeyError(f"unknown strategy sleeve: {strategy_id}") from exc


def ids() -> tuple[str, ...]:
    return tuple(s.strategy_id for s in STRATEGIES)


def active_ids() -> tuple[str, ...]:
    return tuple(s.strategy_id for s in STRATEGIES if s.status == "active")
