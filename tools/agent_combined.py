#!/usr/bin/env python3
"""Supervise the existing LiteLLM gateway and Telegram agent in one Render service."""
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from agent_bootstrap import prepare, storage_mode, private_write
from agent_router import build_router_config

def gateway_key(config, env):
    key = env.get('LITELLM_API_KEY') or config.get('general_settings', {}).get('master_key')
    if isinstance(key, str) and key.startswith('os.environ/'):
        key = env.get(key.removeprefix('os.environ/'))
    if not isinstance(key, str) or not key.strip():
        raise ValueError('Set LITELLM_API_KEY or configure general_settings.master_key')
    return key

def main():
    import yaml  # supplied by litellm[proxy]
    env = dict(os.environ)
    port = int(env.get('PORT', '10000'))
    if not 1 <= port <= 65535:
        raise ValueError('Invalid PORT')
    config_path = Path('/opt/nova-agent/litellm_config.yaml')
    config = yaml.safe_load(config_path.read_text())
    if not isinstance(config, dict):
        raise ValueError('Invalid LiteLLM config')
    env['LITELLM_API_KEY'] = gateway_key(config, env)
    env['LITELLM_BASE_URL'] = f'http://127.0.0.1:{port}/v1'
    # The gateway owns the public port and keeps /v1 URLs unchanged.
    env['PORT'] = str(8080 if port != 8080 else 8081)
    state = Path('/state')
    mode = storage_mode(env, state.is_mount())
    env['NOVA_COUNCIL_PORT'] = str(next(p for p in (8090, 8091, 8092) if p not in (port, int(env['PORT']))))
    env['NOVA_COUNCIL_KEY'] = secrets.token_urlsafe(32)
    workspace = prepare(state, env)
    env.update(GIT_ASKPASS=str(state / 'git-askpass.py'), GIT_TERMINAL_PROMPT='0', GH_TOKEN=env['GITHUB_TOKEN'])
    runtime_path = state / 'litellm_runtime.yaml'
    private_write(runtime_path, yaml.safe_dump(build_router_config(config, env), sort_keys=False))
    env['NOVA_COUNCIL_ROUTE_FILE'] = str(runtime_path)
    children = []
    def stop(_signum=None, _frame=None):
        for child in children:
            if child.poll() is None:
                child.terminate()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        gateway = subprocess.Popen(['litellm', '--config', str(runtime_path), '--host', '0.0.0.0', '--port', str(port)], env=env)
        children.append(gateway)
        deadline = time.monotonic() + 120
        while True:
            if gateway.poll() is not None:
                raise ValueError('LiteLLM stopped during startup')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=1):
                    break
            except OSError:
                if time.monotonic() > deadline:
                    raise ValueError('LiteLLM startup timed out')
                time.sleep(1)
        # The bootstrap already wrote private config/keys; the agent uses them.
        council = subprocess.Popen(['python3', '/opt/nova-agent/agent_council.py', 'serve'], cwd=workspace, env=env)
        children.append(council)
        council_deadline = time.monotonic() + 15
        while True:
            if council.poll() is not None:
                raise ValueError('Background review service stopped during startup')
            try:
                with socket.create_connection(('127.0.0.1', int(env['NOVA_COUNCIL_PORT'])), timeout=1):
                    break
            except OSError:
                if time.monotonic() > council_deadline:
                    raise ValueError('Background review service startup timed out')
                time.sleep(0.2)
        agent = subprocess.Popen(['opencrabs', 'daemon'], cwd=workspace, env=env)
        children.append(agent)
        print('NOVA combined: gateway + Telegram agent; storage=' + mode + '; /v1 retained.', flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(1)
        raise ValueError('A service process stopped; stopping its peer so Render can restart the pair')
    finally:
        stop()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()

if __name__ == '__main__':
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as exc:
        print('NOVA combined stopped: ' + str(exc), file=sys.stderr)
        sys.exit(1)
