#!/usr/bin/env python3
"""Fixed-repository GET-only tools. No shell commands or caller-selected URLs."""
import base64
import ast
from decimal import Decimal, localcontext, DecimalException, Inexact
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

def calculate(expression):
    """Small decimal arithmetic only: no eval, variables, calls, paths or IO."""
    if not isinstance(expression,str) or not expression.strip() or len(expression)>160 or not re.fullmatch(r'[0-9. +*/()\t\r\n-]+',expression):
        raise ValueError('Only a bounded arithmetic expression is allowed')
    expression=expression.strip()
    try:tree=ast.parse(expression,mode='eval')
    except (SyntaxError,ValueError):raise ValueError('Invalid arithmetic expression') from None
    if len(list(ast.walk(tree)))>40:raise ValueError('Arithmetic expression is too complex')
    def number(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):
            token=ast.get_source_segment(expression,node)
            if not re.fullmatch(r'(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)',token):
                raise ValueError('Only decimal literals are allowed')
            value=Decimal(token)
        elif isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            value=number(node.operand)
            if isinstance(node.op,ast.USub):value=-value
        elif isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
            left,right=number(node.left),number(node.right)
            if isinstance(node.op,ast.Add):value=left+right
            elif isinstance(node.op,ast.Sub):value=left-right
            elif isinstance(node.op,ast.Mult):value=left*right
            else:
                if right==0:raise ValueError('Division by zero is not allowed')
                value=left/right
        else:raise ValueError('Unsupported arithmetic operation')
        if not value.is_finite() or abs(value)>Decimal('1e15'):
            raise ValueError('Arithmetic value exceeds its limit')
        return value
    try:
        with localcontext() as ctx:
            ctx.prec=50
            value=number(tree.body)
            result=format(value,'f')
            if '.' in result:result=result.rstrip('0').rstrip('.')
            if value==0:result='0'
            if len(result)>500:raise ValueError('Arithmetic result exceeds its limit')
            return {'expression':expression,'result':result,'precision_digits':50,
                    'rounded':bool(ctx.flags[Inexact]),'input_provenance_verified':False}
    except DecimalException:raise ValueError('Invalid decimal arithmetic') from None

def execute(operation, params):
    if not isinstance(params, dict):
        raise ValueError('Parameters must be an object')
    if operation == 'calculate':
        return calculate(params.get('expression'))
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
