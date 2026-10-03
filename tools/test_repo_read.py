import base64
import tomllib
import unittest
from unittest.mock import patch
import agent_repo_read as reader
import agent_bootstrap as boot

class ReadToolsTests(unittest.TestCase):
    def test_fixed_read_tools(self):
        config = tomllib.loads(boot.readonly_tools_text())
        self.assertEqual(len(config['tools']), 5)
        for tool in config['tools']:
            self.assertFalse(tool['requires_approval'])
            self.assertNotIn('{{', tool['command'])
            self.assertTrue(tool['command'].startswith('python3 /opt/nova-agent/agent_repo_read.py '))
        self.assertIn('approval_policy = "ask"', boot.config_text('1', 'https://example.com', 'm', 8080))

    def test_sensitive_and_traversal_paths_rejected(self):
        for path in ['/etc/passwd', '../keys.toml', 'docs/../README.md', '.env', 'litellm_config.yaml', 'docs/keys.toml', 'docs/secrets.txt', 'a\\b.md']:
            with self.assertRaises(ValueError, msg=path):
                reader.safe_path(path)
        self.assertEqual(reader.safe_path('docs/journal/001.md'), 'docs/journal/001.md')

    def test_pinned_source_and_ignored_shell_input(self):
        sha = 'a' * 40
        item = {'type': 'file', 'encoding': 'base64', 'size': 5, 'sha': 'b' * 40, 'content': base64.b64encode(b'hello').decode()}
        with patch.object(reader, 'get', side_effect=[{'sha': sha}, item]) as fetch:
            result = reader.execute('read', {'path': 'README.md', 'command': 'rm -rf /'})
        self.assertEqual(result['content'], 'hello')
        self.assertEqual(fetch.call_args.args[0], '/contents/README.md?ref=' + sha)

    def test_large_and_binary_rejected(self):
        for size, data in [(reader.LIMIT + 1, b'x'), (1, b'\0')]:
            with patch.object(reader, 'get', side_effect=[{'sha': 'a' * 40}, {'type': 'file', 'encoding': 'base64', 'size': size, 'sha': 'b', 'content': base64.b64encode(data).decode()}]):
                with self.assertRaises(ValueError):
                    reader.execute('read', {'path': 'README.md'})

    def test_redaction_and_no_redirects(self):
        with patch.dict(reader.os.environ, {'GITHUB_TOKEN': 'synthetic-sensitive'}):
            self.assertEqual(reader.redact('synthetic-sensitive ghp_abcdef'), '[REDACTED] [REDACTED]')
        self.assertIsNone(reader.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.test'))

    def test_project_cost_arithmetic_is_decimal_exact_and_local(self):
        with patch.object(reader,'get') as network:
            round_trip=reader.execute('calculate',{'expression':'0.13 + 0.13'})
            dollars=reader.execute('calculate',{'expression':'20 * (0.13 + 0.13) / 100'})
        network.assert_not_called()
        self.assertEqual(round_trip['result'],'0.26')
        self.assertEqual(dollars['result'],'0.052')
        self.assertFalse(dollars['rounded'])
        self.assertFalse(dollars['input_provenance_verified'])

    def test_decimal_precision_and_rounding_are_reported(self):
        self.assertEqual(reader.calculate('0.1 + 0.2')['result'],'0.3')
        self.assertEqual(reader.calculate('10 * 2')['result'],'20')
        self.assertEqual(reader.calculate('-2 * (3 + 4)')['result'],'-14')
        self.assertEqual(reader.calculate('1 / 8')['result'],'0.125')
        self.assertTrue(reader.calculate('1 / 3')['rounded'])
        self.assertFalse(reader.calculate('1 / 8')['rounded'])

    def test_calculator_rejects_code_variables_large_values_and_zero_division(self):
        for expression in ['1/0','2**10','1//2','abs(-1)','True','x+1','__import__(1)',
                           '1;2','[1]','1e10','10000000000000000','1+'*50+'1','0.1%']:
            with self.assertRaises(ValueError,msg=expression):reader.calculate(expression)

    def test_calculator_tool_and_numeric_policy_require_sources_and_arithmetic(self):
        env={'TELEGRAM_BOT_TOKEN':'synthetic-test-token','TELEGRAM_OWNER_ID':'12345',
             'GITHUB_TOKEN':'synthetic-gh-token','LITELLM_API_KEY':'synthetic-key'}
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d,patch.object(boot,'run'),patch.dict(boot.os.environ):
            state=Path(d);(state/'repo/.git/hooks').mkdir(parents=True)
            boot.prepare(state,env)
            policy=(state/'opencrabs/AGENTS.md').read_text()
        self.assertIn('use nova_repo_calculate for arithmetic',policy)
        self.assertIn('explicitly withdraw it and correct it',policy)
        self.assertIn('0.23% is inconsistent',policy)
        import agent_council
        self.assertIn('do not invent computed totals',agent_council.SYSTEM)
        self.assertIn('withdraw it',agent_council.SYSTEM)
        config=tomllib.loads(boot.readonly_tools_text())
        tool=next(t for t in config['tools'] if t['name']=='nova_repo_calculate')
        self.assertFalse(tool['requires_approval'])
        self.assertEqual(tool['params'][0]['name'],'expression')

if __name__ == '__main__':
    unittest.main()
