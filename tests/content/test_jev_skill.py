"""Verify paid-call boundaries with synthetic keys and a mocked HTTP opener."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("jev_helper", ROOT / "extensions/codex/hooks/jev/api.py")
jev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jev)


class JevApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.args = argparse.Namespace(project_dir=str(self.project), input=str(self.project / "request.json"), enabled=False, disabled=False, provider=None, api_url=None, status=False, dry_run=False)
        self.request = json.loads((ROOT / "docs/jev-integration/example-request.json").read_text())
        (self.project / "request.json").write_text(json.dumps(self.request))
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def configure(self, enabled=True, provider="hosted"):
        (self.project / ".agentic.json").write_text(json.dumps({"settings":{"jev":{"enabled":enabled,"api_url":jev.PROVIDERS[provider][0]}}}))

    def test_disabled_stops_before_input_key_and_network_even_with_override(self):
        self.configure(False)
        self.args.enabled = True
        self.args.input = "/does/not/exist"
        with patch.object(jev, "key_for", side_effect=AssertionError("key read")), patch.object(jev.urllib.request, "build_opener", side_effect=AssertionError("network")):
            self.assertEqual(jev.run(self.args)["reason_code"], "disabled")

    def test_provider_key_separation_and_dry_run_redaction(self):
        self.configure(provider="typesafe")
        (self.project / ".env").write_text("JEV_API_KEY=hosted-secret\n")
        self.assertEqual(jev.run(self.args)["reason_code"], "missing_key")
        self.request["state"]["password"] = "must-not-send"
        (self.project / "request.json").write_text(json.dumps(self.request))
        self.args.dry_run = True
        with patch.object(jev, "key_for", side_effect=AssertionError("key read")):
            self.assertNotIn("must-not-send", json.dumps(jev.run(self.args)))

    def test_hosted_and_official_requests_share_contract_without_key_leak(self):
        for provider, key_name in [("hosted","JEV_API_KEY"),("typesafe","TYPESAFE_API_KEY")]:
            self.configure(provider=provider)
            (self.project / ".env").write_text(f"export {key_name}='mock-secret'\n")
            response = MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps({"model":"jev-1.13.0","answers":{"model":{"type":"choice","choice":"fast","confidence":1,"probabilities":{"fast":1,"balanced":0,"frontier":0,"clarify":0},"leak":"mock-secret"}},"usage":{"cost_usd":.0001,"credits_remaining_usd":100}}).encode()
            opener = MagicMock()
            opener.open.return_value = response
            with patch.object(jev.urllib.request, "build_opener", return_value=opener):
                result = jev.run(self.args)
                request = opener.open.call_args.args[0]
                self.assertEqual(request.full_url, jev.PROVIDERS[provider][0])
                self.assertEqual(json.loads(request.data)["questions"], self.request["questions"])
                self.assertEqual(result["status"], "evaluated")
                self.assertNotIn("mock-secret", json.dumps(result))
                self.assertNotIn("credits_remaining_usd", json.dumps(result))

    def test_invalid_distribution_is_rejected(self):
        with self.assertRaises(ValueError):
            jev.answers_for({"answers":{"model":{"type":"choice","choice":"fast","confidence":1,"probabilities":{"fast":0,"balanced":1,"frontier":0,"clarify":0}}}}, self.request["questions"])
