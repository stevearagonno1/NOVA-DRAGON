#!/usr/bin/env python3
"""Read-only wiring checks; --check-model makes one small tool-selection request."""
import argparse
import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from agent_bootstrap import settings

def request(url, headers=None, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = Request(url, data=data, headers={'Content-Type': 'application/json', **(headers or {})})
    try:
        with urlopen(req, timeout=45) as response:
            return json.load(response)
    except HTTPError as exc:
        # Never echo upstream body or URL: Telegram URLs include the bot token.
        raise ValueError(f'Connection check returned HTTP {exc.code}') from None
    except (URLError, TimeoutError, json.JSONDecodeError):
        raise ValueError('Connection check failed: network, timeout, or invalid JSON') from None

def tool_call_valid(response):
    try:
        calls = response['choices'][0]['message']['tool_calls']
        return any(c.get('function', {}).get('name') == 'nova_probe' and
                   json.loads(c['function']['arguments']) == {'value': 'ok'} for c in calls)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-model', action='store_true', help='one small billable model request')
    args = parser.parse_args()
    _, base, model = settings(os.environ)
    tg = 'https://api.telegram.org/bot' + os.environ['TELEGRAM_BOT_TOKEN']
    me = request(tg + '/getMe')
    if not me.get('ok'):
        raise ValueError('Telegram bot authentication was not accepted')
    info = request(tg + '/getWebhookInfo')
    if info.get('result', {}).get('url'):
        raise ValueError('This bot has an active webhook; choose a separate bot for this polling service')
    print('PASS Telegram bot: @' + me['result'].get('username', '(unnamed)'))
    gh = request('https://api.github.com/repos/stevearagonno1/NOVA-DRAGON',
                 {'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'], 'Accept': 'application/vnd.github+json'})
    if gh.get('full_name', '').lower() != 'stevearagonno1/nova-dragon':
        raise ValueError('GitHub repository check did not match')
    print('PASS repository read access')
    auth = {'Authorization': 'Bearer ' + os.environ['LITELLM_API_KEY']}
    models = request(base + '/models', auth)
    if model not in [m.get('id') for m in models.get('data', [])]:
        raise ValueError('Configured model was not listed by the gateway')
    print('PASS model listed: ' + model)
    if args.check_model:
        result = request(base + '/chat/completions', auth, {
            'model': model, 'max_tokens': 256,
            'messages': [{'role': 'user', 'content': 'Call nova_probe with value exactly ok. Do not answer with text.'}],
            'tools': [{'type': 'function', 'function': {'name': 'nova_probe',
                      'description': 'Harmless connection test; no side effects.',
                      'parameters': {'type': 'object', 'properties': {'value': {'type': 'string'}},
                                     'required': ['value'], 'additionalProperties': False}}}],
            'tool_choice': {'type': 'function', 'function': {'name': 'nova_probe'}}})
        if not tool_call_valid(result):
            raise ValueError('Model did not return a structured tool call; tool capability is unconfirmed')
        print('PASS structured tool selection (streaming and multi-step tools still require a real chat test)')

if __name__ == '__main__':
    try:
        main()
    except ValueError as exc:
        print('CHECK STOPPED: ' + str(exc), file=sys.stderr)
        sys.exit(1)
