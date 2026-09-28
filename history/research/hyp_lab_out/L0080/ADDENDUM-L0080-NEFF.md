# ADDENDUM-L0080-NEFF — تصحيح حجم العينة الفعلي للتركيبات الـ27 (L0081/P1)

> تصحيح إحصائي فقط. لم يُعَد تشغيل قياس L0080 ولا الاختيار. الأرقام الأصلية تبقى؛ يُضاف N_eff وWilson عليه فقط.

## المرشّح: GATE_ADX | FVG_3BAR_BASE | CONF_MACD (holdout)

| المقياس | اسمي | مصحّح على N_eff |
|---|---:|---:|
| decided | 1670 | N_eff ≈ 1459 |
| concurrency (لكل أصل) | — | 1.144 |
| win_rate | 0.5383 | 0.5383 |
| Wilson lower | 0.5144 | **0.5127** (> 0.50 → يصمد) |
| retention_fraction | 0.2499 | حد التصفية المجانية = 0.7249 |

بوابة ADX + تأكيد MACD يُخفِّفان تداخل إشارات FVG: معامل التزامن ينزل إلى ≈ 1.14 (قريب من 1)،
فيبقى N_eff قريبًا من العدد الاسمي وWilson المصحّح فوق 0.50. **المرشّح يصمد أمام تصحيح N_eff.**

## للمقارنة

| التركيبة | decided | win_rate | concurrency | N_eff | Wilson اسمي | Wilson على N_eff |
|---|---:|---:|---:|---:|---:|---:|
| `GATE_NONE\|FVG_3BAR_BASE\|CONF_NONE` (خام) | 6581 | 0.5125 | 1.380 | 4770 | 0.5005 | **0.4983** (< 0.50 يسقط) |
| `GATE_EMA200\|FVG_3BAR_BASE\|CONF_NONE` | 3994 | 0.5233 | 1.193 | 3348 | 0.5078 | 0.5064 |
| `GATE_ADX\|FVG_3BAR_BASE\|CONF_MACD` | 1670 | 0.5383 | 1.144 | 1459 | 0.5144 | 0.5127 |

## التركيبات الصامدة أمام N_eff (holdout, decided≥200, Wilson_neff>0.50)

| التركيبة | decided | win_rate | concurrency | N_eff | Wilson اسمي | Wilson على N_eff |
|---|---:|---:|---:|---:|---:|---:|
| `GATE_ADX|FVG_3BAR_BASE|CONF_MACD` | 1670 | 0.5383 | 1.144 | 1459 | 0.5144 | 0.5127 |
| `GATE_ADX|FVG_3BAR_BASE|CONF_OBV` | 1602 | 0.5350 | 1.142 | 1403 | 0.5105 | 0.5088 |
| `GATE_ADX|FVG_3BAR_BASE|CONF_NONE` | 1840 | 0.5310 | 1.161 | 1584 | 0.5081 | 0.5064 |
| `GATE_EMA200|FVG_3BAR_BASE|CONF_NONE` | 3994 | 0.5233 | 1.193 | 3348 | 0.5078 | 0.5064 |
| `GATE_EMA200|FVG_3BAR_BASE|CONF_OBV` | 3201 | 0.5230 | 1.166 | 2746 | 0.5056 | 0.5043 |
| `GATE_EMA200|FVG_3BAR_BASE|CONF_MACD` | 3112 | 0.5231 | 1.155 | 2694 | 0.5056 | 0.5043 |

**النمط:** التركيبات الخام عالية التغطية (FVG وحده) تسقط تحت 0.50 بعد التصحيح؛ التركيبات المبوَّبة بـADX
(تزامن ≈ 1) تصمد. هذا يدعم اختيار `GATE_ADX|FVG_3BAR_BASE|CONF_MACD` كمرشّح P4 الوحيد.

المصدر: `history/research/hyp_lab_out/L0081/neff_recompute_l0080.csv`.
