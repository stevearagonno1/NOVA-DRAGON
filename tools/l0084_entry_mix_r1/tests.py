"""Pre-measurement independent reference and corrected fill tests."""
import unittest
import numpy as np
try:
    from . import engine as E
except ImportError:
    import engine as E


def reference(o,h,l,c,atr,seg,i):
    """Independent literal specification; does not call engine exit code."""
    if i<0 or i+18>=len(c) or np.any(seg[i+1:i+19]!=seg[i]): return None
    q=float(o[i+1]);a=float(atr[i]);stop=q-1.5*a;target=q+1.5*a
    if not np.isfinite(a) or a<=0 or not np.isfinite(q) or q<=0 or stop<=0:return None
    for j in range(i+1,i+19):
        if o[j]<=stop:return ('stop',j,float(o[j]),True,False)
        if o[j]>=target:return ('target',j,target,True,False)
        s=l[j]<=stop;t=h[j]>=target
        if s and t:return ('stop',j,stop,False,True)
        if s:return ('stop',j,stop,False,False)
        if t:return ('target',j,target,False,False)
    return ('timeout',i+18,float(c[i+18]),False,False)


def panel(n=30):
    o=np.full(n,100.0);h=np.full(n,100.2);l=np.full(n,99.8);c=o.copy()
    atr=np.ones(n);seg=np.zeros(n,dtype=np.int64);mask=np.zeros(n,dtype=bool);mask[0]=True
    return o,h,l,c,atr,seg,mask


def key(t):return (t['outcome'],t['exit_bar'],t['exit'],t['gap_flag'],t['double_touch'])


class CorrectedEngineTests(unittest.TestCase):
    def check_case(self,case,mutate,expected):
        o,h,l,c,a,s,m=panel();mutate(o,h,l,c)
        ref=reference(o,h,l,c,a,s,0);self.assertEqual(ref,expected,case)
        scalar,_=E.simulate(o,h,l,c,a,s,m,'SYN',case)
        vector,bad=E.execute_many(o,h,l,c,a,s,[0],'SYN',case)
        self.assertEqual(len(scalar),1,case);self.assertEqual(len(vector),1,case)
        self.assertFalse(bool(bad[0]),case)
        self.assertEqual(key(scalar[0]),ref,case);self.assertEqual(key(vector[0]),ref,case)
        self.assertEqual(scalar[0]['holding_bars'],expected[1]-1+1,case)

    def test_four_audit_cases(self):
        cases=[
          ('fill_stop_then_later_target',lambda o,h,l,c:l.__setitem__(1,98.0) or h.__setitem__(3,102.0),('stop',1,98.5,False,False)),
          ('fill_target',lambda o,h,l,c:h.__setitem__(1,102.0),('target',1,101.5,False,False)),
          ('fill_double_touch',lambda o,h,l,c:(l.__setitem__(1,98.0),h.__setitem__(1,102.0)),('stop',1,98.5,False,True)),
          ('double_touch_after_exit',lambda o,h,l,c:(h.__setitem__(2,102.0),h.__setitem__(3,102.0),l.__setitem__(3,98.0)),('target',2,101.5,False,False)),
        ]
        for name,fn,expected in cases:
            with self.subTest(case=name):self.check_case(name,fn,expected)

    def test_adverse_and_favorable_open_gaps(self):
        for side,expected in [('adverse',('stop',2,97.0,True,False)),('favorable',('target',2,101.5,True,False))]:
            o,h,l,c,a,s,m=panel();o[2]=97.0 if side=='adverse' else 103.0
            r=reference(o,h,l,c,a,s,0);self.assertEqual(r,expected)
            for result in (E.simulate(o,h,l,c,a,s,m,'SYN',side)[0],E.execute_many(o,h,l,c,a,s,[0],'SYN',side)[0]):
                self.assertEqual(key(result[0]),expected)

    def test_timeout_horizon_and_cost_once(self):
        o,h,l,c,a,s,m=panel()
        for rows in (E.simulate(o,h,l,c,a,s,m,'SYN','timeout')[0],E.execute_many(o,h,l,c,a,s,[0],'SYN','timeout')[0]):
            t=rows[0];self.assertEqual((t['outcome'],t['exit_bar'],t['holding_bars']),('timeout',18,18))
            self.assertEqual(t['cost_dollars'],0.052)

    def test_incomplete_start_no_index_error(self):
        o,h,l,c,a,s,m=panel(10);m[0]=False
        rows,bad=E.execute_many(o,h,l,c,a,s,[-1,8,9,10,30],'SYN','bad')
        self.assertEqual(rows,[]);self.assertEqual(bad.tolist(),[True]*5)
        trades,counters=E.simulate(o,h,l,c,a,s,np.ones(10,bool),'SYN','short')
        self.assertEqual(trades,[]);self.assertGreater(counters['incomplete'],0)

    def test_gap_segment_prevents_bridge(self):
        o,h,l,c,a,s,m=panel();s[5:]=1
        self.assertIsNone(reference(o,h,l,c,a,s,0))
        rows,bad=E.execute_many(o,h,l,c,a,s,[0],'SYN','gap')
        self.assertEqual(rows,[]);self.assertTrue(bad[0])

    def test_nonoverlap_and_reentry_after_exit(self):
        o,h,l,c,a,s,_=panel(50);h[1]=102;h[3]=102
        mask=np.zeros(50,bool);mask[[0,1,2]]=True
        rows,_=E.simulate(o,h,l,c,a,s,mask,'SYN','reentry')
        self.assertEqual([t['fill_bar'] for t in rows],[1,2])
        self.assertEqual([t['exit_bar'] for t in rows],[1,3])
        self.assertTrue(all(rows[i+1]['fill_bar']>rows[i]['exit_bar'] for i in range(len(rows)-1)))

    def test_bad_multi_start_and_purge(self):
        o,h,l,c,a,s,m=panel(50);rows,bad=E.execute_many(o,h,l,c,a,s,[-2,0,20,22,30,50],'SYN','mix')
        self.assertEqual(bad.tolist(),[True,False,False,False,False,True])
        self.assertTrue(all(t['signal_bar'] in (0,20,22,30) for t in rows))
        kept=E.window_trades(rows,0,39,embargo=18)
        self.assertTrue(all(t['signal_bar']>=18 and t['signal_bar']+18<=39 for t in kept))

    def test_cash_book_stops_new_trades(self):
        n=6200;o=np.full(n,100.0);h=np.full(n,100.2);l=np.full(n,99.8);c=o.copy()
        atr=np.ones(n);seg=np.zeros(n,dtype=np.int64);mask=np.zeros(n,dtype=bool)
        mask[::2]=True
        # Every eligible entry stops on its fill bar: loss $0.352 including one RT cost.
        l[1::2]=98.0
        rows,cnt=E.simulate(o,h,l,c,atr,seg,mask,'SYN','cash')
        self.assertGreater(len(rows),0);self.assertLess(len(rows),n//2)
        self.assertTrue(all(abs(t['net_dollars']+0.352)<1e-10 for t in rows))
        self.assertGreater(cnt['rejected'],0)

    def test_each_window_has_fresh_state_and_purge_embargo(self):
        o,h,l,c,a,s,m=panel(70);m[:]=False;m[[0,27,28,29,40]]=True
        rows,counters=E.simulate_window(o,h,l,c,a,s,m,'SYN','window',10,49,18)
        self.assertEqual([t['signal_bar'] for t in rows],[28])
        self.assertEqual(rows[0]['fill_bar'],29)
        self.assertEqual(rows[0]['exit_bar'],46)
        self.assertEqual(counters['signals'],1)

    def test_atr_and_stop_rejection(self):
        o,h,l,c,a,s,m=panel();a[0]=np.nan
        self.assertEqual(E.simulate(o,h,l,c,a,s,m,'SYN','nan')[0],[])
        o,h,l,c,a,s,m=panel();a[0]=100
        self.assertEqual(E.execute_many(o,h,l,c,a,s,[0],'SYN','nonpositive-stop')[0],[])

if __name__=='__main__':unittest.main()


def run_all(phase='pre', m=None):
    """Run the complete constitutional integrity suite from integrity.py."""
    from . import integrity
    return integrity.run_all(phase, m=m)
