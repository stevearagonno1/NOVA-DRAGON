#!/usr/bin/env python3
"""Fixed-repository GET-only tools. No shell commands or caller-selected URLs."""
import base64
import json
import os
import re
import sys
from pathlib import PurePosixPath
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = 'https://api.github.com/repos/stevearagonno1/NOVA-DRAGON'
LIMIT = 65536

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def safe_path(value):
    if not isinstance(value, str) or not value or len(value) > 500:
        raise ValueError('A repository-relative text path is required')
    path = PurePosixPath(value)
    if value.startswith('/') or '\\' in value or any(p in ('.', '..', '') for p in value.split('/')):
        raise ValueError('Invalid repository path')
    denied = {'litellm_config.yaml', 'keys.toml', 'config.toml', 'credentials', 'git-askpass.py'}
    if any(p.startswith('.') or p.lower() in denied or 'secret' in p.lower() for p in path.parts):
        raise ValueError('Credential and hidden paths are unavailable')
    if path.suffix.lower() not in {'.md', '.txt', '.py', '.rs', '.sh', '.json', '.csv', '.toml', '.yaml', '.yml'}:
        raise ValueError('Only supported text files are available')
    return value

def get(endpoint):
    req = Request(ROOT + endpoint, method='GET', headers={
        'Accept': 'application/vnd.github+json', 'User-Agent': 'NOVA-readonly-tools',
        'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN']})
    with build_opener(NoRedirect).open(req, timeout=25) as response:
        raw = response.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('API response exceeds the read limit')
    return json.loads(raw)

def commit_info(item):
    return {'sha': item['sha'], 'date': item['commit']['committer']['date'],
            'subject': item['commit']['message'].splitlines()[0]}

def execute(operation, params):
    if not isinstance(params, dict):
        raise ValueError('Parameters must be an object')
    if operation == 'status':
        item = get('/commits/main')
        return {'repository': 'stevearagonno1/NOVA-DRAGON', 'branch': 'main', **commit_info(item)}
    if operation == 'commits':
        return [commit_info(x) for x in get('/commits?sha=main&per_page=10')]
    if operation == 'list':
        prefix = params.get('prefix', 'docs/journal/')
        if not isinstance(prefix, str) or len(prefix) > 500 or prefix.startswith('/') or '..' in prefix or '\\' in prefix:
            raise ValueError('Invalid path prefix')
        tree = get('/git/trees/main?recursive=1')
        entries = []
        for item in tree['tree']:
            if item['type'] != 'blob' or not item['path'].startswith(prefix):
                continue
            try:
                safe_path(item['path'])
            except ValueError:
                continue
            entries.append({'path': item['path'], 'size': item.get('size'), 'sha': item['sha']})
        return {'branch': 'main', 'tree_sha': tree['sha'], 'total_matching': len(entries),
                'truncated': tree.get('truncated', False) or len(entries) > 300,
                'files': entries[:300]}
    if operation == 'read':
        path = safe_path(params.get('path'))
        # Pin both the source and returned provenance to the same commit.
        commit = get('/commits/main')['sha']
        item = get('/contents/' + quote(path, safe='/') + '?ref=' + commit)
        if not isinstance(item, dict) or item.get('type') != 'file' or item.get('encoding') != 'base64':
            raise ValueError('Not a supported regular text file')
        if item.get('size', LIMIT + 1) > LIMIT:
            raise ValueError('File exceeds 64 KiB; request a smaller source file')
        raw = base64.b64decode(item['content'])
        if len(raw) > LIMIT or b'\0' in raw:
            raise ValueError('File is too large or binary')
        return {'path': path, 'commit': commit, 'blob_sha': item['sha'], 'content': raw.decode('utf-8')}
    raise ValueError('Unsupported read operation')

def redact(text):
    for name, secret in os.environ.items():
        if re.search(r'(TOKEN|KEY|PASSWORD|SECRET)', name, re.I) and len(secret) >= 8:
            text = text.replace(secret, '[REDACTED]')
    return re.sub(r'(?:github_pat_[A-Za-z0-9_]+|gh[pousr]_[A-Za-z0-9]+)', '[REDACTED]', text)

def main():
    try:
        with open(os.environ['OPENCRABS_PARAMS'], encoding='utf-8') as handle:
            params = json.load(handle)
        result = execute(sys.argv[1], params)
        print(redact(json.dumps(result, ensure_ascii=False)))
    except Exception as exc:
        # Exception bodies may contain request details: expose only class and safe validation errors.
        message = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(json.dumps({'error': redact(message)}, ensure_ascii=False))
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
