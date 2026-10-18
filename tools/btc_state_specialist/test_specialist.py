import unittest
import numpy as np
import specialist as S

class StateResearchTests(unittest.TestCase):
    def test_both_verified_archive_time_column_names_are_supported(self):
        import io,pandas as pd
        d=S.fixture();frame=pd.DataFrame({'close_time_utc':pd.to_datetime(d['dt'],unit='s',utc=True),'open':d['o'],'high':d['h'],'low':d['l'],'close':d['c'],'volume':d['v'],'minutes':d['minutes']})
        for name in ['close_time_utc','time_utc']:
            source=frame.rename(columns={'close_time_utc':name}).to_csv(index=False)
            loaded=S.load_data(io.StringIO(source));self.assertEqual(len(loaded['c']),420)

    def test_late_alert_is_accepted_and_duplicate_does_not_catch_two_states(self):
        states=[(2,5),(8,8)]
        self.assertEqual(S.score(np.array([False,False,False,True,True,False,False,False,False]),states),
                         {'alerts':2,'caught':1,'missed':1,'repeated':1,'delays':[1],'first_indices':[3]})

    def test_adjacent_days_are_separate_states(self):
        self.assertEqual(S.runs([False,True,True,True,False],['a','a','a','b','b']),[(1,2),(3,3)])

    def test_no_signal_rows_remain(self):
        self.assertEqual(S.score(np.zeros(5,bool),[(1,3)])['missed'],1)

    def test_fixture_has_no_leaking_inputs_and_all_registered_rows(self):
        d=S.fixture();g=S.grid();m=S.masks(d,g)
        self.assertEqual(set(m),{q['id'] for q in g})
        for cut in [260,350]:
            pre=S.masks({k:v[:cut] for k,v in d.items()},g)
            for key in m:self.assertTrue(np.array_equal(m[key][:cut],pre[key]),key)
        z={k:v.copy() for k,v in d.items()}
        for k in ['o','h','l','c']:z[k][350:]*=1.1
        changed=S.masks(z,g)
        for key in m:self.assertTrue(np.array_equal(m[key][:350],changed[key][:350]),key)

    def test_state_definition_uses_prior_high_excluding_current(self):
        d=S.fixture();state=S.state_mask(d,'2024-01')
        ref=[]
        for i in range(len(d['c'])):
            valid=i>=260 and d['minutes'][i-60:i+1].tolist()==[15]*61
            valid=valid and S.day(d['dt'][i])==S.day(d['dt'][i-4]) if i>=4 else False
            ref.append(bool(valid and S.month(d['dt'][i])=='2024-01' and
                            d['c'][i]/d['c'][i-4]-1>=.005 and d['c'][i]>max(d['h'][i-12:i])))
        self.assertTrue(np.array_equal(state,ref))

    def test_numerical_reference_ema_atr_and_band(self):
        import indicators84 as I
        d=S.fixture();c,h,l=[d[k] for k in ['c','h','l']]
        e=[];a=[];prev_e=None;prev_a=None
        for i,x in enumerate(c):
            prev_e=x if prev_e is None else prev_e*19/21+x*2/21;e.append(prev_e)
            tr=max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) if i else h[i]-l[i]
            prev_a=tr if prev_a is None else prev_a*13/14+tr/14;a.append(prev_a)
        np.testing.assert_allclose(I.ema(c,20)[19:],e[19:],rtol=1e-12)
        np.testing.assert_allclose(I.wilder_atr(h,l,c,14)[13:],a[13:],rtol=1e-12)
        bands=I.bollinger(c,20,2)[0]
        for i in [30,120,350]:
            x=c[i-19:i+1];self.assertAlmostEqual(bands[i],float(np.mean(x)-2*np.std(x)),places=9)

if __name__=='__main__':unittest.main()
