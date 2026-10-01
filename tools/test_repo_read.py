import base64
import tomllib
import unittest
from unittest.mock import patch
import agent_repo_read as reader
import agent_bootstrap as boot

class ReadToolsTests(unittest.TestCase):
    def test_fixed_read_tools(self):
        config = tomllib.loads(boot.readonly_tools_text())
        self.assertEqual(len(config['tools']), 4)
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

if __name__ == '__main__':
    unittest.main()
