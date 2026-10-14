#!/usr/bin/env python3
"""Shared TypeSafe/JEV request validation, credential loading and redaction."""

import argparse
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
import urllib.parse

PROVIDERS = {
    "hosted": ("https://jevtypesafeai.com/api/v1/decide", "JEV_API_KEY"),
    "typesafe": ("https://api.typesafe.ai/v1/systemone", "TYPESAFE_API_KEY"),
}


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
        return re.sub(r"(?:jv_live_|ts_|sk-)[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._-]+|[A-Z_]*(?:API_KEY|PASSWORD|SECRET|TOKEN)[A-Z_]*\s*=\s*[^\s]+|-----BEGIN[\s\S]*?PRIVATE KEY-----[\s\S]*?-----END[\s\S]*?PRIVATE KEY-----", "[REDACTED]", value, flags=re.I)
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
