import copy
import unittest

from agent_router import build_router_config


def sample():
    return {
        'model_list': [
            {'model_name': 'opencrabs-model', 'litellm_params': {
                'model': 'openai/existing', 'api_base': 'https://provider.example/v1',
                'api_key': 'os.environ/TOKEN_1', 'rpm': 4, 'tpm': 1000},
             'model_info': {'id': 'existing-id', 'max_input_tokens': 10000}},
            {'model_name': 'opencrabs-model', 'litellm_params': {
                'model': 'openai/existing', 'api_base': 'https://provider.example/v1',
                'api_key': 'two', 'rpm': 4}},
        ],
        'general_settings': {'master_key': 'master'},
        'router_settings': {'enable_pre_call_checks': True},
    }


class RouterTests(unittest.TestCase):
    def test_overlay_preserves_source_provider_limits_and_master_key(self):
        source = sample()
        before = copy.deepcopy(source)
        result = build_router_config(source, {'TOKEN_1': 'one'})
        self.assertEqual(source, before)
        self.assertEqual(result['general_settings'], source['general_settings'])
        self.assertEqual(result['model_list'][0], source['model_list'][0])
        self.assertTrue(result['router_settings']['enable_pre_call_checks'])
        self.assertEqual(result['router_settings']['retry_policy']['AuthenticationErrorRetries'], 0)
        self.assertEqual(result['router_settings']['max_fallbacks'], 5)
        self.assertTrue(result['router_settings']['enable_weighted_failover'])

    def test_duplicate_literal_and_env_credentials_do_not_add_capacity(self):
        source = sample()
        source['model_list'].append(copy.deepcopy(source['model_list'][0]))
        source['model_list'][-1]['litellm_params']['api_key'] = 'one'
        result = build_router_config(source, {
            'TOKEN_1': 'one', 'TOKEN_2': 'two', 'TOKEN_3': 'one'})
        self.assertEqual(len(result['model_list']), 2)

    def test_additional_token_never_invents_deployment_or_quota(self):
        result = build_router_config(sample(), {'TOKEN_1': 'one', 'TOKEN_12': 'new'})
        self.assertEqual(len(result['model_list']), 2)
        self.assertEqual(result['model_list'][0]['litellm_params']['tpm'], 1000)
        ids = [entry['model_info']['id'] for entry in result['model_list']]
        self.assertEqual(len(ids), len(set(ids)))

    def test_generated_ids_do_not_collide_with_later_existing_ids(self):
        source = sample()
        source['model_list'][0]['model_info'].pop('id')
        source['model_list'][1]['model_info'] = {'id': 'nova-deployment-1'}
        result = build_router_config(source, {'TOKEN_1': 'one'})
        self.assertNotEqual(result['model_list'][0]['model_info']['id'], 'nova-deployment-1')

    def test_missing_credential_error_does_not_expose_secret(self):
        source = sample()
        source['general_settings']['master_key'] = 'SECRET_DO_NOT_PRINT'
        with self.assertRaisesRegex(ValueError, 'missing its API credential') as error:
            build_router_config(source, {})
        self.assertNotIn('SECRET_DO_NOT_PRINT', str(error.exception))

    def test_missing_alias_never_invents_model(self):
        with self.assertRaisesRegex(ValueError, 'existing model alias'):
            build_router_config(sample(), {'AGENT_MODEL': 'unconfigured', 'TOKEN_1': 'one'})

    def test_same_key_different_upstream_is_preserved(self):
        source = sample()
        source['model_list'][1]['litellm_params']['api_key'] = 'one'
        source['model_list'][1]['litellm_params']['api_base'] = 'https://other.example/v1'
        result = build_router_config(source, {'TOKEN_1': 'one'})
        self.assertEqual(len(result['model_list']), 2)

    def test_duplicate_existing_ids_rejected(self):
        source = sample()
        source['model_list'][1]['model_info'] = {'id': 'existing-id'}
        with self.assertRaisesRegex(ValueError, 'IDs must be unique'):
            build_router_config(source, {'TOKEN_1': 'one'})


if __name__ == '__main__':
    unittest.main()
