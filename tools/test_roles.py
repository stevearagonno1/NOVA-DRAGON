import unittest
from unittest.mock import patch
import agent_council as council
from agent_router import build_router_config
class RolesTests(unittest.TestCase):
    def test_interactive_alias_has_only_slot_four_source_unchanged(self):
        source={'model_list':[{'model_name':'opencrabs-model','litellm_params':{'model':'openai/existing','api_key':'key'+str(i)}} for i in range(10)]}
        cfg=build_router_config(source,{},lead_slot=4)
        active=[r for r in cfg['model_list'] if r['model_name']=='opencrabs-model']
        self.assertEqual(len(active),1);self.assertEqual(active[0]['litellm_params']['api_key'],'key3')
        self.assertEqual(len(cfg['model_list']),10)
        self.assertTrue(all(r['model_name']=='opencrabs-model' for r in source['model_list']))
    def test_direct_advice_lead_and_advisor_only_tested_credentials(self):
        with patch.object(council,'stream_model_call',return_value='ok') as call:
            council.model_call('s','u',slot=0)
            self.assertEqual(call.call_args.kwargs['candidate_indices'],(3,6))
            council.model_call('s','u',slot=1)
            self.assertEqual(call.call_args.kwargs['candidate_indices'],(6,3))
