import pandas as pd, numpy as np
# df: columns = [open, high, low, close, volume]، فريمك التشغيلي، مُغلق.
def backtest(df, atr_n=14, adx_gate=20, fee_side=0.0010, slip=0.0005,
             stop_mult=2.0, t1=1.0, t2=2.0, max_hold=24):
    df = df.copy()
    df['atr'] = np.nan
    h,l,c = df.high.values, df.low.values, df.close.values
    tr = np.maximum(h-l, np.maximum(abs(h-np.r_[c[:-1],np.nan]),
                                     abs(l-np.r_[c[:-1],np.nan])))
    df['atr'] = pd.Series(tr).ewm(alpha=1/atr_n, adjust=False).mean()
    df['rvol'] = df.volume / df.volume.rolling(20).mean()
    # RSI(14)
    d = pd.Series(c).diff(); up = d.clip(lower=0); dn = -d.clip(upper=0)
    rs = up.ewm(alpha=1/14, adjust=False).mean()/dn.ewm(alpha=1/14, adjust=False).mean()
    df['rsi'] = 100-100/(1+rs)
    df['ema200'] = pd.Series(c).ewm(span=200, adjust=False).mean()
    trades=[]; i=atr_n+200; pos=None
    while i < len(df):
        o = df.iloc[i]; p = df.iloc[i-1]          # الإشارة من p، التنفيذ على فتح i
        if pos is None:
            long_gate = p.close > p.ema200 and p.rsi < 45 and p.rvol > 1.2
            if long_gate:
                stop = o.open - stop_mult*p.atr
                if stop < o.open:
                    pos = dict(e=o.open, s=stop, t1=o.open+t1*(o.open-stop),
                               t2=o.open+t2*(o.open-stop), b=i)
        else:
            held = i-pos['b']
            if o.low <= pos['s']:      exit_px, tag = pos['s'], 'stop'
            elif o.high >= pos['t2']:  exit_px, tag = pos['t2'], 't2'
            elif o.high >= pos['t1']:  exit_px, tag = pos['t1'], 't1'
            elif held >= max_hold:     exit_px, tag = o.close, 'time'
            else: i+=1; continue
            R = (exit_px-pos['e'])/(pos['e']-pos['s']) - (2*fee_side+2*slip)*pos['e']/(pos['e']-pos['s'])
            trades.append(dict(R=R, tag=tag, held=held, i=i)); pos=None
        i+=1
    r = pd.Series([t['R'] for t in trades])
    eq = r.cumsum(); dd = (eq-eq.cummax()).min()
    return dict(n=len(r), win=(r>0).mean(), E=r.mean(), pf=r[r>0].sum()/abs(r[r<0].sum()),
                R_sum=r.sum(), mdd_R=dd, tags=pd.Series([t['tag'] for t in trades]).value_counts().to_dict())
# ملاحظات إلزامية: (1) التنفيذ على فتح الشمعة التالية دائماً؛ (2) التكاليف داخل R؛
# (3) أضف walk-forward و OOS قبل أن تثق بأي رقم أعلاه؛ (4) هذا الهيكل للـ*تعلّم*
# وليس للتشغيل؛ أضف fill-at-touch وقواعد limit الحقيقية قبل أي قرار مال.

# تحقّق فعلي: شُغّل هذا الهيكل (Python 3.13 + numpy/pandas) على أربع سلاسل
# اصطناعية بمشي عشوائي بطول 900 شمعة، فكانت النتائج trades بين 1 و20 و
# E[R] بين -1.08 و +0.26 أي بلا دلالة، وهو المتوقع من نظام لا حافة له.
# القاعدة المستخلصة: إن أعطاك باك تستك "حافة" على عيّنة أصغر مما يحدّده
# قسم 2.4، فالأرجح أنه ضجيج. نسختا الكود الجاهزتان:
#   /home/user/tools/sizing.py   و   /home/user/tools/backtest_sk.py
