import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch
import agent_bootstrap as boot
from agent_git_guard import permitted
from agent_preflight import tool_call_valid

class SetupTests(unittest.TestCase):
    def test_free_and_persistent_storage_modes(self):
        self.assertEqual(boot.storage_mode({}, False), 'ephemeral')
        self.assertEqual(boot.storage_mode({'AGENT_STORAGE_MODE': 'persistent'}, True), 'persistent')
        with self.assertRaises(ValueError):
            boot.storage_mode({'AGENT_STORAGE_MODE': 'persistent'}, False)
        with self.assertRaises(ValueError):
            boot.storage_mode({'AGENT_STORAGE_MODE': 'unknown'}, True)

    def env(self):
        return {'TELEGRAM_BOT_TOKEN': 'synthetic-test-token', 'TELEGRAM_OWNER_ID': '12345',
                'GITHUB_TOKEN': 'synthetic-github', 'LITELLM_API_KEY': 'synthetic-key'}

    def test_missing_and_wrong_owner_rejected(self):
        with self.assertRaises(ValueError):
            boot.settings({})
        env = self.env(); env['TELEGRAM_OWNER_ID'] = '123,456'
        with self.assertRaises(ValueError):
            boot.settings(env)

    def test_credentials_in_gateway_url_rejected(self):
        env = self.env(); env['LITELLM_BASE_URL'] = 'https://secret@example.com/v1'
        with self.assertRaises(ValueError):
            boot.settings(env)

    def test_owner_only_and_approval_config(self):
        config = tomllib.loads(boot.config_text('12345', 'https://example.com/v1', 'model', 10000))
        self.assertEqual(config['channels']['telegram']['allowed_users'], [12345])
        self.assertEqual(config['channels']['telegram']['bot_owner'], [12345])
        self.assertEqual(config['agent']['approval_policy'], 'ask')
        self.assertFalse(config['a2a']['enabled'])

    def test_secrets_are_valid_toml_and_private(self):
        env = self.env(); env['LITELLM_API_KEY'] = 'test"\\\nkey'
        with tempfile.TemporaryDirectory() as d, patch.object(boot, 'run'), patch.dict(boot.os.environ):
            state = Path(d)
            (state / 'repo/.git/hooks').mkdir(parents=True)
            boot.prepare(state, env)
            keys = state / 'opencrabs/keys.toml'
            parsed = tomllib.loads(keys.read_text())
            self.assertEqual(parsed['providers']['custom']['nova']['api_key'], env['LITELLM_API_KEY'])
            self.assertEqual(keys.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(env['LITELLM_API_KEY'], (state / 'opencrabs/config.toml').read_text())

    def test_restart_never_discards_pending_work(self):
        with tempfile.TemporaryDirectory() as d, patch.object(boot, 'run') as runner, patch.dict(boot.os.environ):
            state = Path(d); (state / 'repo/.git/hooks').mkdir(parents=True)
            pending = state / 'repo/pending.md'; pending.write_text('keep')
            boot.prepare(state, self.env())
            self.assertEqual(pending.read_text(), 'keep')
            commands = [call.args[0] for call in runner.call_args_list]
            self.assertFalse(any(x in c for c in commands for x in ['clone', 'switch', 'reset', 'clean', 'pull']))

    def test_push_guard(self):
        sha = 'a' * 40
        self.assertTrue(permitted([f'refs/heads/agent/x {sha} refs/heads/agent/x {sha}']))
        for target in ['refs/heads/main', 'refs/heads/master', 'refs/tags/v1']:
            self.assertFalse(permitted([f'HEAD {sha} {target} {sha}']))
        self.assertFalse(permitted([f'HEAD {"0"*40} refs/heads/agent/x {sha}']))
        self.assertFalse(permitted(['malformed']))

    def test_tool_probe_does_not_accept_plain_text(self):
        self.assertFalse(tool_call_valid({'choices': [{'message': {'content': 'ok'}}]}))
        self.assertTrue(tool_call_valid({'choices': [{'message': {'tool_calls': [
            {'function': {'name': 'nova_probe', 'arguments': json.dumps({'value': 'ok'})}}]}}]}))

if __name__ == '__main__':
    unittest.main()
