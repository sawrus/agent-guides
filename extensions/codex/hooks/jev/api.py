#!/usr/bin/env python3
"""Shared TypeSafe/JEV client: request validation, credentials, redaction, budget ledger and hook evaluation."""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.error
import urllib.request
import urllib.parse
import uuid

PROVIDERS = {
    "hosted": ("https://jevtypesafeai.com/api/v1/decide", "JEV_API_KEY"),
    "typesafe": ("https://api.typesafe.ai/v1/systemone", "TYPESAFE_API_KEY"),
}
JSON_FILE_LIMIT = 2_000_000
JEV_MODEL = "jev-1.13.0"
REQUEST_LIMIT = 32768
RESPONSE_LIMIT = 262144
HOOK_TIMEOUT_SECONDS = 8
RESERVATION_USD = .02
MAX_CHARGE_USD = 5
BUDGET_LOCK_ATTEMPTS = 20
BUDGET_LOCK_WAIT = .02


# Every token family matches only at a token start, so identifiers such as tests_and_review_evidence,
# parts_inventory_service or task-ask-me stay intact (QR-D3). `ts_` is also a common word part, so it needs a digit;
# OpenAI/Anthropic (`sk-`, `sk-proj-`, `sk-ant-`) and gateway (`jv_live_`) keys need a digit or 20+ characters.
TOKEN = re.compile(
    r"(?<![A-Za-z0-9_-])(?:"
    r"ts_(?=[A-Za-z0-9_-]*[0-9])[A-Za-z0-9_-]{8,}"
    r"|(?:sk-|jv_live_)(?:[A-Za-z0-9_-]{20,}|(?=[A-Za-z0-9_-]*[0-9])[A-Za-z0-9_-]{8,})"
    r"|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|AKIA[0-9A-Z]{16}(?![0-9A-Z])"
    r"|xox[abprs]-[A-Za-z0-9-]{10,})")


def key_for(project, name):
    if os.environ.get(name):
        return os.environ[name]
    path = project / ".env"
    if not path.is_file() or path.stat().st_size > 65536:
        return None
    for line in path.read_text(encoding='utf-8').splitlines():
        match = re.match(r"^\s*(?:export\s+)?" + name + r"\s*=\s*(.*?)\s*$", line)
        if match:
            value = match[1]
            if value.startswith(("'", '"')):
                value = value[1:].split(value[0], 1)[0]
            else:
                value = value.split(" #", 1)[0].strip()
            return value or None
    return None


def redact(value):
    if isinstance(value, dict):
        return {k: "[REDACTED]" if re.search(r"api.?key|password|secret|(?:^|_)token$|authorization|cookie|credential", k, re.I) else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return TOKEN.sub("[REDACTED]", re.sub(r"Bearer\s+[A-Za-z0-9._-]+|[A-Z_]*(?:API_KEY|PASSWORD|SECRET|TOKEN)[A-Z_]*\s*=\s*[^\s]+|-----BEGIN[\s\S]*?PRIVATE KEY-----[\s\S]*?-----END[\s\S]*?PRIVATE KEY-----", "[REDACTED]", value, flags=re.I))
    return value


def validate(body):
    if not isinstance(body, dict):
        raise ValueError("request must be an object")
    questions = body.get("questions")
    if "state" not in body or not isinstance(questions, dict) or not questions:
        raise ValueError("state and nonempty questions required")
    for q in questions.values():
        if not isinstance(q, dict) or not q.get("instructions"):
            raise ValueError("question instructions required")
        kind, criteria = q.get("type"), q.get("criteria")
        if kind == "choice" and isinstance(criteria, dict) and 2 <= len(criteria) <= 255:
            continue
        if kind == "score" and isinstance(criteria, list) and 2 <= len(criteria) <= 10:
            continue
        if kind != "noul":
            raise ValueError("invalid question type or criteria")


def answers_for(result, questions):
    answers = result.get("answers", {})
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise ValueError("invalid answers")
    clean = {}
    for name, question in questions.items():
        answer = answers[name]
        kind = question["type"]
        if not isinstance(answer, dict) or answer.get("type") != kind:
            raise ValueError("invalid answer type")
        if kind == "noul":
            p = answer.get("noul")
            if not isinstance(p, (float, int)) or isinstance(p, bool) or not 0 <= p <= 1:
                raise ValueError("invalid probability")
            clean[name] = {"type": kind, "noul": p}
            continue
        probabilities = answer.get("probabilities")
        confidence = answer.get("confidence")
        if not isinstance(probabilities, dict) or not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            raise ValueError("invalid distribution")
        if not all(isinstance(p, (float, int)) and not isinstance(p, bool) and 0 <= p <= 1 for p in probabilities.values()) or abs(sum(probabilities.values()) - 1) > .03:
            raise ValueError("invalid probability mass")
        if kind == "choice":
            selected = answer.get("choice")
            if set(probabilities) != set(question["criteria"]) or selected not in probabilities or probabilities[selected] < max(probabilities.values()):
                raise ValueError("invalid choice")
            clean[name] = {"type": kind, "choice": selected, "confidence": confidence, "probabilities": probabilities}
        else:
            score = answer.get("score")
            levels = len(question["criteria"])
            if not isinstance(score, (int, float)) or not 0 <= score <= levels - 1 or not all(k in {str(i) for i in range(levels)} for k in probabilities):
                raise ValueError("invalid score")
            clean[name] = {"type": kind, "score": score, "confidence": confidence, "probabilities": probabilities}
    return clean


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_json(path, default=None):
    try:
        if path.stat().st_size > JSON_FILE_LIMIT:
            return default
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def scrub(value, project):
    value = redact(value)
    # Also remove exact locally configured credentials, including unknown key formats.
    keys = [key_for(project, name) for name in ('JEV_API_KEY', 'TYPESAFE_API_KEY')]
    def clean(v):
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()}
        if isinstance(v, list):
            return [clean(x) for x in v]
        if isinstance(v, str):
            for key in keys:
                if key:
                    v = v.replace(key, '[REDACTED]')
            v = re.sub(r'(?i)(password|secret|token|api[_-]?key|authorization)\s*[:=]\s*["\']?[^\s"\',;]+', r'\1=[REDACTED]', v)
        return v
    return clean(value)


def save_json(path, data):
    if path.is_symlink():
        raise ValueError('redirected runtime file')
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def budget_lock(path):
    lock = path.with_suffix('.lock')
    acquired = False
    for _ in range(BUDGET_LOCK_ATTEMPTS):
        try:
            lock.mkdir()
            acquired = True
            break
        except FileExistsError:
            time.sleep(BUDGET_LOCK_WAIT)
    if not acquired:
        raise ValueError('budget busy')
    try:
        yield
    finally:
        lock.rmdir()


def reserve_budget():
    configured = os.environ.get('AGENTIC_JEV_BUDGET_FILE')
    if not configured:
        return None
    path = Path(configured)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('redirected budget')
    token = uuid.uuid4().hex
    with budget_lock(path):
        data = read_json(path)
        if not isinstance(data, dict) or data.get('committed_usd', MAX_CHARGE_USD) + sum(data.get('pending', {}).values()) + RESERVATION_USD > data.get('limit_usd', 0):
            raise ValueError('budget exhausted')
        data.setdefault('pending', {})[token] = RESERVATION_USD
        save_json(path, data)
    return path, token


def settle_budget(reservation, cost):
    if not reservation:
        return
    path, token = reservation
    with budget_lock(path):
        data = read_json(path)
        estimate = data['pending'].pop(token)
        data['committed_usd'] += cost if isinstance(cost, (int, float)) and 0 <= cost <= MAX_CHARGE_USD else estimate
        data['calls'] = data.get('calls', 0) + 1
        save_json(path, data)


def hook_endpoint(settings):
    """(endpoint, key variable) the hooks use: JEV_API_URL > settings.jev.api_url > official; None if unsafe."""
    endpoint = os.environ.get('JEV_API_URL') or settings.get('api_url') or PROVIDERS["typesafe"][0]
    url = urllib.parse.urlsplit(endpoint)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.fragment:
        return None, None
    return endpoint, 'TYPESAFE_API_KEY' if url.hostname == 'api.typesafe.ai' else 'JEV_API_KEY'


def evaluate(project, settings, request):
    endpoint, key_name = hook_endpoint(settings)
    if not endpoint:
        return {'status': 'fallback', 'reason_code': 'invalid_endpoint'}
    key = key_for(project, key_name)
    if not key:
        return {'status': 'fallback', 'reason_code': 'missing_key'}
    validate(request)
    # Non-ASCII stays UTF-8: escaped Cyrillic costs about six bytes per character against the request limit.
    if len(json.dumps(request, ensure_ascii=False).encode()) > REQUEST_LIMIT:
        return {'status': 'fallback', 'reason_code': 'request_too_large'}
    body = json.dumps({'model': JEV_MODEL, **request}, ensure_ascii=False).encode()
    req = urllib.request.Request(endpoint, body, {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json; charset=utf-8'})
    reservation = reserve_budget()
    cost = None
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=HOOK_TIMEOUT_SECONDS) as response:
            raw = response.read(RESPONSE_LIMIT + 1)
        if len(raw) > RESPONSE_LIMIT:
            raise ValueError('response too large')
        result = json.loads(raw)
        cost = result.get('usage', {}).get('cost_usd')
        if result.get('model') != JEV_MODEL:
            raise ValueError('unexpected model')
        return {'status': 'evaluated', 'answers': answers_for(result, request['questions']),
                'usage': {k: result.get('usage', {}).get(k) for k in ('input_tokens', 'cost_usd')},
                'response': result}
    finally:
        settle_budget(reservation, cost)


def run(args):
    project = Path(args.project_dir).resolve()
    manifest = project / ".agentic.json"
    settings = json.loads(manifest.read_text()).get("settings", {}).get("jev", {}) if manifest.is_file() else {}
    switch = os.environ.get("AGENTIC_ENABLE_JEV", "").lower()
    enabled = settings.get("enabled", False) or args.enabled or switch in ("1", "y", "yes", "true")
    if args.disabled or switch in ("0", "n", "no", "false") or settings.get("enabled") is False:
        enabled = False
    endpoint = args.api_url or os.environ.get("JEV_API_URL") or settings.get("api_url") or PROVIDERS["typesafe"][0]
    url = urllib.parse.urlsplit(endpoint)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.fragment:
        raise ValueError("invalid API URL")
    provider = "typesafe" if url.hostname == "api.typesafe.ai" else "hosted" if url.hostname == "jevtypesafeai.com" else "custom"
    key_name = "TYPESAFE_API_KEY" if provider == "typesafe" else "JEV_API_KEY"
    if args.status:
        return {"enabled": bool(enabled), "api_url": endpoint, "key_available": bool(enabled and key_for(project, key_name)), "paid_calls": 0}
    if not enabled:
        return {"status": "fallback", "reason_code": "disabled"}
    if not args.input:
        raise ValueError("--input required")
    path = Path(args.input)
    if path.stat().st_size > 32768:
        raise ValueError("input too large")
    body = redact(json.loads(path.read_text()))
    validate(body)
    body = {"model": "jev-1.13.0", "state": body["state"], "questions": body["questions"]}
    if args.dry_run:
        return {"status": "dry_run", "provider": provider, "request": body}
    key = key_for(project, key_name)
    if not key:
        return {"status": "fallback", "reason_code": "missing_key"}
    request = urllib.request.Request(endpoint, json.dumps(body).encode(), {"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=10) as response:
        data = response.read(262145)
    if len(data) > 262144:
        raise ValueError("response too large")
    result = json.loads(data)
    if result.get("model") != "jev-1.13.0":
        raise ValueError("unexpected model")
    usage = result.get("usage", {})
    return {"status": "evaluated", "provider": provider, "model": result["model"], "answers": answers_for(result, body["questions"]), "usage": {k: usage[k] for k in ("input_tokens", "cost_usd") if isinstance(usage.get(k), (int, float))}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--api-url")
    parser.add_argument("--enabled", action="store_true")
    parser.add_argument("--disabled", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true")
    try:
        result = run(parser.parse_args())
    except (OSError, ValueError, TypeError, KeyError, AttributeError, urllib.error.URLError):
        result = {"status": "fallback", "reason_code": "request_failed"}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
