#!/usr/bin/env python3
"""JEV spawn routing: host model pools, tiers, prices, role defaults and deterministic spawn rules.

Pure functions over parsed data; hook.py owns all file and network I/O.
"""
import os
import re

VERSION = 2
TIERS = ('fast', 'balanced', 'frontier')
CLAUDE_TIERS = {'fast': 'haiku', 'balanced': 'sonnet', 'frontier': 'opus'}
MIN_TIERS = 2
TIER_MAP_VERSION = 1
COST_DIGITS = 2
REVIEW_DEFAULT = 'gpt-6-luna'
LIGHTWEIGHT = re.compile(r'fast.*affordable.*easier|lightweight', re.I)
TOML_MODEL = re.compile(r'^\s*model\s*=\s*["\']([^"\']+)', re.M)
ROLE_ALIASES = {'instruction_reviewer': 'instruction-reviewer', 'memory_curator': 'memory-curator', 'designer': 'analyst'}
CLAUDE_MODELS = (
    {'id': 'haiku', 'description': 'Claude Haiku: fastest, most affordable lightweight model for routine coding, exploration and read-only review.', 'prices': None},
    {'id': 'sonnet', 'description': 'Claude Sonnet: balanced default coding model for implementation and verification.', 'prices': None},
    {'id': 'opus', 'description': 'Claude Opus: most capable and most expensive model for complex planning and architecture.', 'prices': None},
)
CLAUDE_ALIASES = frozenset(m['id'] for m in CLAUDE_MODELS)


def canonical_role(role):
    role = role if isinstance(role, str) else ''
    return ROLE_ALIASES.get(role, role)


def claude_alias(model):
    model = model.lower() if isinstance(model, str) else ''
    return next((alias for alias in ('haiku', 'sonnet', 'opus') if alias in model), None)


def _string_map(value):
    return {k: v for k, v in value.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(value, dict) else {}


def load_defaults(data, host=None):
    """Parsed model-defaults.json: v2 `{version, roles, tiers, hosts: {host: {roles, tiers}}}` or the legacy flat
    role map. A host section wins: a combined install keeps Codex ids at the top level, which Claude cannot use."""
    if not isinstance(data, dict):
        return {'roles': {}, 'tiers': {}}
    section = (data.get('hosts') or {}).get(host) if isinstance(data.get('hosts'), dict) else None
    if data.get('version') == VERSION and isinstance(section, dict):
        return load_defaults({**section, 'version': VERSION})
    if data.get('version') == VERSION:
        tiers = _string_map(data.get('tiers'))
        return {'roles': _string_map(data.get('roles')), 'tiers': {t: m for t, m in tiers.items() if t in TIERS}}
    return {'roles': _string_map(data), 'tiers': {}}


def model_pool(defaults):
    return set(defaults['roles'].values()) | set(defaults['tiers'].values())


def codex_models(catalog, defaults, profile_texts):
    """Listed catalog models that a role default, a tier or a user profile pin refers to."""
    pool = model_pool(defaults) | {m[1] for m in (TOML_MODEL.search(text) for text in profile_texts) if m}
    models = catalog.get('models', []) if isinstance(catalog, dict) else []
    return [{'id': m['slug'], 'description': m.get('description', ''), 'prices': None}
            for m in models if isinstance(m, dict) and m.get('visibility') == 'list' and m.get('slug') in pool]


def claude_models(defaults):
    """Claude's Agent tool accepts only model aliases; restrict candidates to aliases in use."""
    aliases = {claude_alias(model) for model in model_pool(defaults)} & CLAUDE_ALIASES
    return [dict(m) for m in CLAUDE_MODELS if len(aliases) < MIN_TIERS or m['id'] in aliases]


def price(cost):
    """Input+output price from an OpenCode cost dict or the first band of a price list; None when unknown."""
    band = cost[0] if isinstance(cost, list) and cost else cost
    if not isinstance(band, dict):
        return None
    values = [band.get(key) for key in ('input', 'output')]
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0 for v in values):
        return None
    return float(sum(values))


def opencode_tiers(models):
    """Two priced models give fast/frontier; three or more add balanced at the lower median price."""
    priced = sorted((price(m.get('prices')), m['id']) for m in models if price(m.get('prices')) is not None)
    if len(priced) < MIN_TIERS or len(priced) != len(models) or priced[0][0] == priced[-1][0]:
        return {}
    tiers = {'fast': priced[0][1], 'frontier': priced[-1][1]}
    if len(priced) > MIN_TIERS:
        tiers['balanced'] = priced[(len(priced) - 1) // 2][1]
    return tiers


def candidate_overrides(overrides, ids):
    """settings.jev.tiers entries count only when their model is a candidate."""
    return {t: m for t, m in _string_map(overrides).items() if t in TIERS and m in ids}


def host_tiers(host, models, configured, overrides):
    """Tier -> model for this host; settings.jev.tiers override only with candidate models."""
    ids = {m['id'] for m in models}
    base = opencode_tiers(models) if host == 'opencode' else {t: m for t, m in configured.items() if m in ids}
    if host == 'claude' and not base:
        base = {t: m for t, m in CLAUDE_TIERS.items() if m in ids}
    return {**base, **candidate_overrides(overrides, ids)}


def load_tier_map(data):
    """Parsed opencode-model-tiers.json v1 `{roles: {role: tier}, providers: {p: {tier: id}}}`; anything else is empty."""
    version = data.get('version') if isinstance(data, dict) else None
    if type(version) is not int or version != TIER_MAP_VERSION:
        return {'roles': {}, 'providers': {}}
    roles = {role: tier for role, tier in _string_map(data.get('roles')).items() if tier in TIERS}
    providers = data.get('providers') if isinstance(data.get('providers'), dict) else {}
    return {'roles': roles, 'providers': {name: {t: m for t, m in _string_map(tiers).items() if t in TIERS}
                                          for name, tiers in providers.items() if isinstance(name, str)}}


def provider_of(model):
    return model.split('/', 1)[0] if isinstance(model, str) and '/' in model else None


def map_provider(tier_map, ids, preferred):
    """One provider only: a set preference must qualify itself (>=2 tier models in `ids`); file order applies
    only without a preference, so a role on another provider never routes to this map's models."""
    qualifying = [name for name, tiers in tier_map['providers'].items()
                  if len({m for m in tiers.values() if m in ids}) >= MIN_TIERS]
    if preferred:
        return preferred if preferred in qualifying else None
    return next(iter(qualifying), None)


def tier_map_tiers(tier_map, models, preferred):
    ids = {m['id'] for m in models}
    provider = map_provider(tier_map, ids, preferred)
    return {t: m for t, m in tier_map['providers'][provider].items() if m in ids} if provider else {}


def spawn_tiers(event, models, defaults, overrides, tier_map):
    """(tiers, cost_source). OpenCode: complete distinct prices, else the shipped tier map, else no tiers."""
    host = event.get('host')
    if host != 'opencode':
        return host_tiers(host, models, defaults['tiers'], overrides), 'tier_order'
    base, source = opencode_tiers(models), 'catalog_price'
    if not base:
        preferred = os.environ.get('AGENTIC_JEV_MODEL_PROVIDER') or provider_of(event.get('role_default'))
        base, source = tier_map_tiers(tier_map, models, preferred), 'tier_map'
    tiers = {**base, **candidate_overrides(overrides, {m['id'] for m in models})}
    # Override-only tiers have no price basis, so they are ranked like the configured hosts.
    return tiers, (source if base else 'tier_order' if tiers else None)


def candidates(models, tiers, cost_source):
    available = {m['id']: m for m in models}
    chosen = [(tier, tiers[tier]) for tier in TIERS if tiers.get(tier) in available]
    if cost_source != 'catalog_price':
        return [{'tier': t, 'model': m, 'relative_cost': TIERS.index(t) + 1} for t, m in chosen]
    prices = {m: price(available[m].get('prices')) for _, m in chosen}
    lowest = min((p for p in prices.values() if p), default=None)
    return [{'tier': t, 'model': m, 'relative_cost': round(prices[m] / lowest, COST_DIGITS) if lowest and prices[m] else None}
            for t, m in chosen]


def tier_of(tiers, model):
    return next((tier for tier in TIERS if tiers.get(tier) == model), None)


def review_model(models, settings):
    """Only claim cheapest when every eligible candidate has comparable prices."""
    prices = [(price(m.get('prices')), m['id']) for m in models]
    if prices and all(p is not None for p, _ in prices):
        return min(prices)[1], 'cheapest_eligible_catalog_price'
    configured = os.environ.get('AGENTIC_JEV_REVIEW_MODEL') or settings.get('lightweight_model') or REVIEW_DEFAULT
    if any(m['id'] == configured for m in models):
        return configured, 'configured_lightweight_price_unknown'
    return None


def lightweight_model(event, settings, models):
    configured = event.get('lightweight_model') or os.environ.get('AGENTIC_JEV_LIGHTWEIGHT_MODEL') or settings.get('lightweight_model')
    if configured or event.get('host') == 'opencode':
        return configured
    if event.get('host') == 'claude':
        return CLAUDE_TIERS['fast']
    return next((m['id'] for m in models if LIGHTWEIGHT.search(m.get('description', ''))), None)


def routed(model, reason, source):
    return {'result': {'status': 'routed', 'model': model, 'reason_code': reason},
            'fields': {'model_source': source, 'outcome': 'rule_applied'}}


def review_tier(tiers):
    return (tiers['fast'], 'tier_fast_price_unknown') if (tiers or {}).get('fast') else None


def spawn_rule(event, settings, models, tiers=None):
    """Deterministic spawn outcomes that never ask JEV; `keep_native` blocks the role-default fallback."""
    if event.get('configuration_unavailable'):
        return {'result': {'status': 'fallback', 'reason_code': 'project_configuration_unavailable'}, 'keep_native': True}
    if event.get('pinned_model') or event.get('continuation'):
        return {'result': {'status': 'preserved', 'reason_code': 'explicit_model_or_continuation'},
                'keep_native': True, 'fields': {'model_source': 'pinned', 'outcome': 'rule_applied'}}
    if len(models) == 1:
        return routed(models[0]['id'], 'single_eligible_model', 'single_eligible')
    if event.get('agent') == 'instruction-reviewer':
        chosen = review_model(models, {**settings, 'lightweight_model': lightweight_model(event, settings, models)}) or review_tier(tiers)
        return routed(chosen[0], chosen[1], 'review_model') if chosen else None
    return None


def opencode_role_default(event, tiers, role_tiers, ids):
    """A catalog profile model wins; otherwise the role's tier from the shipped map (native agents by type)."""
    explicit = event.get('role_default')
    if isinstance(explicit, str) and explicit in ids:
        return explicit, 'profile'
    model = tiers.get(role_tiers.get(event.get('agent') or event.get('native_agent_type') or ''))
    return (model, 'role_tier') if model in ids else (None, None)


def role_default_model(event, defaults, models, tiers=None, role_tiers=None):
    """(model, source). OpenCode: profile or role tier; Codex and Claude read model-defaults.json."""
    host, ids = event.get('host'), {m['id'] for m in models}
    if host == 'opencode':
        return opencode_role_default(event, tiers or {}, role_tiers or {}, ids)
    model = defaults['roles'].get(event.get('agent') or '')
    model = claude_alias(model) if host == 'claude' else model
    return (model, 'defaults') if model in ids else (None, None)


def plan_spawn(event, models, defaults, settings, tier_map=None):
    """Spawn plan without I/O: a deterministic `result`, or `role_ctx` and `pool` for the model question."""
    tier_map = tier_map or load_tier_map(None)
    tiers, cost_source = spawn_tiers(event, models, defaults, settings.get('tiers'), tier_map)
    rule = spawn_rule(event, settings, models, tiers)
    if rule:
        rule.setdefault('fields', {}).update(cost_source=cost_source, role_default_source=None)
        return rule
    default, source = role_default_model(event, defaults, models, tiers, tier_map['roles'])
    plan = {'tiers': tiers, 'role_default': default, 'fields': {'cost_source': cost_source, 'role_default_source': source}}
    pool = candidates(models, tiers, cost_source)
    if len(pool) < MIN_TIERS:
        return {**plan, 'result': {'status': 'fallback', 'reason_code': 'no_tier_routing'}}
    if event.get('host') == 'codex' and event.get('assignment_unavailable'):
        # QR-D12: an encrypted assignment always ended in `clarify`; the call cannot change the outcome.
        return {**plan, 'result': {'status': 'fallback', 'reason_code': 'assignment_unavailable'}}
    return {**plan, 'role_ctx': role_context(event, tiers, default), 'pool': pool}


def role_context(event, tiers, default):
    return {'role': event.get('agent'), 'role_description': event.get('role_description'),
            'role_default': {'model': default, 'tier': tier_of(tiers, default)} if default else None,
            'assignment': event.get('prompt'), 'assignment_unavailable': event.get('assignment_unavailable')}


def map_model(plan, selected):
    if selected not in plan['tiers']:
        plan['result'].update(status='fallback', reason_code='clarification_needed')
        return
    plan['result']['model'] = plan['tiers'][selected]
    plan['fields'].update(applied=True, outcome='jev_applied', tier=selected, model_source='jev_tier')


def apply_role_default(plan):
    """Any non-pinned spawn fallback runs the role's default model instead of inheriting the session model."""
    result, fields = plan['result'], plan.setdefault('fields', {})
    if result.get('status') == 'fallback' and not result.get('model') and not plan.get('keep_native') and plan.get('role_default'):
        result['model'] = plan['role_default']
        fields.update(outcome='role_default_applied', model_source='role_default',
                      tier=tier_of(plan.get('tiers', {}), plan['role_default']))
    fields.setdefault('model_source', 'none')
    fields.setdefault('tier', None)
    result.update(tier=fields['tier'], model_source=fields['model_source'])
