import math
def atr(high, low, close, n=14):
    trs=[]
    for i in range(1,len(close)):
        trs.append(max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1])))
    # Wilder smoothing
    a=sum(trs[:n])/n; out=[None]*n+[a]
    for tr in trs[n:]:
        a=(a*(n-1)+tr)/n; out.append(a)
    return out[-1]

def position_size(equity, risk_pct, entry, stop, fee_rt=0.0020, slip=0.0005):
    """risk_pct = 0.005 for 0.5%. fee_rt = round-trip fee (decimal).
    نموذج مبسّط: نفترض أن الفروك+الانزلاق نسبيان لسعر الدخول في الطرفين
    (تقريب صالح؛ عدّله على بياناتك الفعلية)."""
    stop_dist = abs(entry - stop)
    if stop_dist <= 0:
        raise ValueError("stop must differ from entry")
    cost_per_unit = entry * (fee_rt + slip)     # تكلفة الوحدة الواحدة (ذهاب/إياب)
    risk_per_unit = stop_dist + cost_per_unit   # المخاطرة الحقيقية للوحدة
    qty = (equity * risk_pct) / risk_per_unit
    notional = qty * entry
    fees = qty * cost_per_unit
    return {"qty": qty, "notional": notional, "true_risk": qty * risk_per_unit,
            "stop_pct": stop_dist / entry * 100, "costs": fees,
            "costs_as_R": fees / (equity * risk_pct)}

def atr_stop(entry, atr_val, k=2.0, side="long"):
    """الوقف من الهيكل/التقلب: k=1.5 اختراق، 2.0 يومي، 2.5–3.0 سوينغ."""
    return entry - k * atr_val if side == "long" else entry + k * atr_val

def ou_halflife(prices):
    """نصف عمر الارتداد للمتوسط: يحدد المهلة والهدف."""
    import numpy as np
    y=np.asarray(prices,float); y=np.log(y); dy=np.diff(y); ylag=y[:-1]
    X=np.column_stack([np.ones(len(ylag)), ylag])
    beta=np.linalg.lstsq(X, dy, rcond=None)[0]
    a=beta[1]
    return None if a>=0 else -math.log(2)/a

if __name__=="__main__":
    # مثال: حساب 20,000$، مخاطرة 0.5%، دخول 60,000 ووقف 58,200 (≈3% )
    print(position_size(20000, 0.005, 60000, 58200))
    print("stop for ATR=900, k=2 :", atr_stop(60000, 900, 2.0))
    # ملاحظة: إن كانت costs_as_R > 0.15 فصفقتك "تعمل لأجل المنصّة"
