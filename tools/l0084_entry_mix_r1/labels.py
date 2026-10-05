#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0084-ENTRY-MIX — evaluation-only rise label (never an input feature).

Label at t:
  * L[t] is the minimum low in the centred window t-5 .. t+5
  * within the next 24 bars the close reaches C[t]+2*ATR[t] before
    C[t]-ATR[t]; a simultaneous touch rejects the label
  * the complete label horizon (t+24) must exist
Signal i matches a label t within +/-2 bars.  Precision counts matched
signals; recall counts distinct labelled starts matched once; F1 is their
harmonic mean; median lead is median(i - t) over matched label starts.
"""
from __future__ import annotations

import numpy as np

LEAD_TOL = 2
CENTRE = 5
FWD = 24


def rise_labels(h, l, c, atr):
    n = len(c)
    lab = np.zeros(n, bool)
    for t in range(CENTRE, n - CENTRE):
        if t + FWD >= n:
            continue
        if not np.isfinite(atr[t]) or atr[t] <= 0:
            continue
        if l[t] != np.min(l[t - CENTRE:t + CENTRE + 1]):
            continue
        up = c[t] + 2 * atr[t]
        dn = c[t] - atr[t]
        hit_up = hit_dn = False
        for j in range(t + 1, t + FWD + 1):
            u = h[j] >= up
            d = l[j] <= dn
            if u and d:
                hit_up = hit_dn = True          # simultaneous -> reject
                break
            if u:
                hit_up = True
                break
            if d:
                hit_dn = True
                break
        if hit_up and not hit_dn:
            lab[t] = True
    return lab


def score(signal_mask, labels):
    """Precision / recall / F1 / median lead / counts."""
    sig = np.nonzero(signal_mask)[0]
    labs = np.nonzero(labels)[0]
    if len(labs) == 0:
        return dict(precision=np.nan, recall=np.nan, f1=np.nan,
                    median_lead=np.nan, n_signals=int(len(sig)),
                    n_labels=0, matched_signals=0, matched_labels=0)
    lab_set = set(labs.tolist())
    matched_signals = 0
    for i in sig:
        if any((i + d) in lab_set for d in range(-LEAD_TOL, LEAD_TOL + 1)):
            matched_signals += 1
    leads = []
    matched_labels = 0
    sig_sorted = np.sort(sig)
    for t in labs:
        cand = sig_sorted[np.abs(sig_sorted - t) <= LEAD_TOL]
        if cand.size:
            matched_labels += 1
            leads.append(int(cand[np.argmin(np.abs(cand - t))] - t))
    prec = matched_signals / len(sig) if len(sig) else np.nan
    rec = matched_labels / len(labs)
    f1 = (2 * prec * rec / (prec + rec)
          if prec and rec and np.isfinite(prec) and np.isfinite(rec)
          and (prec + rec) > 0 else np.nan)
    return dict(precision=float(prec) if np.isfinite(prec) else np.nan,
                recall=float(rec), f1=float(f1) if np.isfinite(f1) else np.nan,
                median_lead=float(np.median(leads)) if leads else np.nan,
                n_signals=int(len(sig)), n_labels=int(len(labs)),
                matched_signals=int(matched_signals),
                matched_labels=int(matched_labels))
