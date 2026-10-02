#!/usr/bin/env python3
"""Build a private LiteLLM runtime overlay without changing the source config.

Keys are credentials, not independent brains or guaranteed independent quotas.
This module never calls a provider and never prints credentials.
See https://docs.litellm.ai/docs/routing for router_settings.
"""
import copy


def _resolved_key(value, env):
    if isinstance(value, str) and value.startswith('os.environ/'):
        value = env.get(value.removeprefix('os.environ/'))
    if not isinstance(value, str) or not value.strip():
        raise ValueError('A model deployment is missing its API credential')
    return value


def build_router_config(source, env):
    """Return a new config with bounded same-model key failover.

    Existing model names, provider endpoints, credentials, limits and general
    settings stay intact. Only configured deployments are used; extra TOKEN_N
    variables never invent a deployment, provider, model or quota.
Duplicate keys for the same alias/upstream count once, not as extra capacity.
The result contains secrets and must be saved with mode 0600, never logged.
"""
    if not isinstance(source, dict) or not isinstance(source.get('model_list'), list):
        raise ValueError('LiteLLM config must contain a model_list')
    result = copy.deepcopy(source)
    alias = env.get('AGENT_MODEL', 'opencrabs-model')
    models = result['model_list']
    if not models:
        raise ValueError('LiteLLM model_list is empty')
    target = []
    for entry in models:
        if not isinstance(entry, dict) or not isinstance(entry.get('litellm_params'), dict):
            raise ValueError('Invalid model deployment')
        if entry.get('model_name') == alias:
            target.append(entry)
    if not target:
        raise ValueError('AGENT_MODEL must match an existing model alias')
    seen = set()
    retained = []
    ids = set()
    reserved_ids = {str(entry.get('model_info', {}).get('id')) for entry in models
                    if isinstance(entry.get('model_info'), dict)
                    and entry['model_info'].get('id') is not None}
    for index, entry in enumerate(models):
        params = entry['litellm_params']
        if entry.get('model_name') == alias:
            identity = (alias, params.get('model'), params.get('api_base'),
                        params.get('api_version'), _resolved_key(params.get('api_key'), env))
            if identity in seen:
                continue
            seen.add(identity)
        info = entry.setdefault('model_info', {})
        if not isinstance(info, dict):
            raise ValueError('Invalid model_info')
        deployment_id = info.get('id')
        if deployment_id is None:
            deployment_id = 'nova-deployment-' + str(index + 1)
            while deployment_id in ids or deployment_id in reserved_ids:
                deployment_id += '-new'
            info['id'] = deployment_id
        if str(deployment_id) in ids:
            raise ValueError('Deployment IDs must be unique')
        ids.add(str(deployment_id))
        retained.append(entry)
    result['model_list'] = retained
    router = result.setdefault('router_settings', {})
    if not isinstance(router, dict):
        raise ValueError('Invalid router_settings')
    router.update({
        'routing_strategy': 'simple-shuffle',
        'enable_weighted_failover': True,
        'num_retries': 2,
        'max_fallbacks': 5,
        'allowed_fails': 1,
        'cooldown_time': 60,
        'timeout': 90,
        'retry_policy': {
            'AuthenticationErrorRetries': 0,
            'BadRequestErrorRetries': 0,
            'ContentPolicyViolationErrorRetries': 0,
            'NotFoundErrorRetries': 0,
            'TimeoutErrorRetries': 2,
            'RateLimitErrorRetries': 2,
            'InternalServerErrorRetries': 2,
        },
        'allowed_fails_policy': {
            'AuthenticationErrorAllowedFails': 0,
            'RateLimitErrorAllowedFails': 0,
        },
    })
    return result
