import unittest
import catalog


class CatalogueTests(unittest.TestCase):
    def test_administrative_function_is_not_promoted_by_family_name(self):
        d={'scope':'dust_sweep_if_due','definition':'async def dust_sweep_if_due():\n    await REST.dust_transfer([])'}
        self.assertIn('external_side_effect', catalog.definition_flags(d))
        self.assertIn('administrative_dust_conversion', catalog.definition_flags(d))

    def test_nested_unresolved_values_are_preserved_as_blockers(self):
        self.assertTrue(catalog.unresolved({'n':{'expression':'lookback'}}))
        self.assertTrue(catalog.unresolved({'anchors':[{'unresolved':True}]}))
        self.assertFalse(catalog.unresolved({'period':14,'level':0}))

    def test_native_label_is_not_a_readiness_proof(self):
        r={'id':'B','source_version_ids':['V'],'settings':{},'primitive':{'kind':'L85'},'readiness':'runnable_native'}
        item=catalog.classify_bull(r, {'V':{'id':'V','definition_id':'D'}}, {}, {}, {})
        self.assertFalse(item['market_ready'])
        self.assertIn('missing_definition',item['blockers'])

    def test_exact_bound_source_retains_confirmation_requirement(self):
        base={'id':'V','family':'RSI','definition_id':'D','settings':{'n':14},'asset':None,'origin':'x','signal':'s','timing':'close'}
        row={'id':'B','source_version_ids':['V'],'settings':{'n':14},'primitive':{'kind':'L85'},'confirmation':'GREEN','timing':'NOW'}
        result=catalog.classify_bull(row,{'V':base},{'D':{'definition':'reviewed formula'}},{'V':base},{})
        self.assertEqual(result['existing_source_bindings'],['V'])
        self.assertFalse(result['market_ready'])

    def test_settings_change_never_inherits_existing_binding(self):
        b={'id':'V','family':'RSI','definition_id':'D','settings':{'n':14},'asset':None,'origin':'x','signal':'s','timing':'close'}
        g={**b,'settings':{'n':21}}
        result=catalog.classify_bull({'id':'B','source_version_ids':['V'],'settings':{'n':14}}, {'V':b},{'D':{}},{'V':g},{})
        self.assertEqual(result['existing_source_bindings'],[])


if __name__=='__main__':unittest.main()
