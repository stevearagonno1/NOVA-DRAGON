#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0084-ENTRY-MIX — neighbour enumeration (+-20% one numeric parameter).

Paper section 10: at most one provisional finalist per prefix plus the final
hypothesis; register first; change ONE numeric period, threshold or band
multiplier by +-20% at a time; fix mode, component count, costs, container
and assets; no categorical/pivot/execution perturbations; no promotion.
"""
from __future__ import annotations

from . import indicators as I

FACTORS = (1.2, 0.8)


def enumerate_neighbours(members):
    """Yield neighbour specs for a candidate's member settings."""
    for member in members:
        toks = I.numeric_tokens(member)
        for idx in range(len(toks)):
            for factor in FACTORS:
                new_name, spec = I.perturb_name(member, idx, factor)
                if new_name is None:
                    continue
                yield (f"{member}#{idx}#{factor:g}", {
                    "member": member, "param": toks[idx][2],
                    "old": toks[idx][1], "new": spec["new"],
                    "factor": factor, "new_name": new_name})
