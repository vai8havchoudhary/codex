from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from support import PreflightTestCase, preflight
from test_checkpoint_server import checkpoint, server


def witness(**overrides):
    result = {"role": "reviewer", "model": "gemini-3.7-flash-high",
              "agent_id": "01a05414-b798-7270-95f2-fef4144bbffa", "verdict": "APPROVE",
              "summary": "Returned review: final diff and gate evidence approved.",
              "transcript_ref": "run.jsonl:42", "reviewed_revision": "diff-sha256:" + "a" * 64}
    result.update(overrides)
    return result


class NamedPreflightTests(PreflightTestCase):
    def test_missing_unsafe_tampered_or_stale_derived_catalog_refused(self):
        for mutation in ("missing", "symlink", "malformed", "stale", "unmanaged"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.run_named(root, council="luna-grok")
                path = root / "cliproxy-council-models.json"
                if mutation == "missing":
                    path.unlink()
                elif mutation == "symlink":
                    path.unlink()
                    path.symlink_to(root / "models.json")
                elif mutation == "malformed":
                    path.write_text("{")
                elif mutation == "unmanaged":
                    path.write_text('{"models": []}')
                else:
                    value = json.loads(path.read_text())
                    value["models"][0]["context_window"] = 1234
                    path.write_text(json.dumps(value))
                with self.assertRaises(preflight.PreflightError):
                    preflight.run_preflight(url="http://127.0.0.1:8317", config=root / "config.toml",
                        grok_model=None, gemini_model="gemini-3.7-flash-high", council="luna-grok",
                        models_response_file=root / "models.json", codex_models_response_file=root / "codex-models.json", timeout=1)

    def run_named(self, root, **overrides):
        ids = ["grok-4.6", "gemini-3.7-flash-high"]
        openai, codex = self.files(root, ids, ids)
        config = self.config(root)
        args = dict(url="http://127.0.0.1:8317", config=config,
                    grok_model="grok-4.6", gemini_model="gemini-3.7-flash-high",
                    models_response_file=openai, codex_models_response_file=codex, timeout=1)
        args.update(overrides)
        return preflight.run_preflight(**args)

    def test_both_named_councils_bind_exact_leader_and_advisor(self):
        for name, leader, advisor in (("luna-grok", "gpt-5.6-luna", "grok-4.6"),
                                      ("grok-gemini", "grok-4.6", "gemini-3.7-flash-high")):
            with self.subTest(council=name), tempfile.TemporaryDirectory() as tmp:
                result = self.run_named(Path(tmp), council=name, leader_model=leader)
                self.assertEqual((result.council, result.leader_model, result.advisor_model), (name, leader, advisor))
                self.assertEqual(result.luna_model, "gpt-5.6-luna")

    def test_gemini_led_and_wrong_runtime_leader_refused(self):
        for options in ({"council": "gemini-led"}, {"council": "luna-grok", "leader_model": "grok-4.6"}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(preflight.PreflightError):
                    self.run_named(Path(tmp), **options)

    def test_luna_named_profile_tampering_refused(self):
        for mutation in ("model", "model_provider", "developer_instructions", "model_instructions_file", "model_catalog_json"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.run_named(root, council="luna-grok")
                path = root / "luna-grok.config.toml"
                data = path.read_text()
                lines = [line for line in data.splitlines() if not line.startswith(mutation + " =")]
                path.write_text("\n".join(lines) + f'\n{mutation} = "wrong"\n')
                with self.assertRaises(preflight.PreflightError):
                    preflight.run_preflight(url="http://127.0.0.1:8317", config=root / "config.toml",
                        grok_model=None, gemini_model="gemini-3.7-flash-high", council="luna-grok",
                        models_response_file=root / "models.json", codex_models_response_file=root / "codex-models.json", timeout=1)

    def test_named_councils_work_from_exact_installed_cache_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consumer, _ = self.installed_cache(root, ("1.1.0", "99.0.0"))
            result = self.run_named(root / "config", council="luna-grok", plugin_root=consumer)
            self.assertEqual(result.leader_model, "gpt-5.6-luna")


class WitnessTests(unittest.TestCase):
    def test_shipped_review_instructions_and_negative_verdict_storage_agree(self):
        plugin = Path(__file__).resolve().parents[1]
        for relative in ("commands/review.md", "agents/verifier.md", "skills/codex-moa/SKILL.md"):
            with self.subTest(instructions=relative):
                text = (plugin / relative).read_text()
                self.assertIn("APPROVE", text)
                self.assertIn("REQUEST_CHANGES", text)
                self.assertNotIn("APPROVE or BLOCK", text)
                self.assertNotIn("APPROVE|BLOCK", text)
        with tempfile.TemporaryDirectory() as tmp:
            store = server.CheckpointStore(Path(tmp))
            review = checkpoint(phase="review", native_agents=[witness(verdict="REQUEST_CHANGES")])
            record, _ = store.put(review)
            self.assertEqual(store.get(record["handle"])["checkpoint"]["native_agents"][0]["verdict"], "REQUEST_CHANGES")
            with self.assertRaisesRegex(server.StoreError, "APPROVE"):
                store.put(dict(review, phase="complete", status="complete", previous=record["handle"]))

    def test_checkpoint_and_model_authority_council_contracts_agree(self):
        import checkpoint_schema
        catalog, _ = preflight.load_authority()
        self.assertEqual(checkpoint_schema.COUNCILS, catalog.COUNCILS)
        for tool in server.tool_definitions()[:2]:
            self.assertEqual(set(tool["inputSchema"]["properties"]["council"]["enum"]), set(catalog.COUNCILS))

    def test_both_council_reviews_can_complete_and_round_trip(self):
        for name, leader, advisor in (("grok-gemini", "grok-4.6", "gemini-3.7-flash-high"), ("luna-grok", "gpt-5.6-luna", "grok-4.6")):
            with self.subTest(council=name), tempfile.TemporaryDirectory() as tmp:
                store = server.CheckpointStore(Path(tmp))
                review = checkpoint(council=name, leader_mode=name, leader_model=leader,
                    advisor_models=[advisor], phase="review", native_agents=[witness(model=advisor)])
                prior, _ = store.put(review)
                complete = dict(review, phase="complete", status="complete", previous=prior["handle"])
                final, _ = store.put(complete)
                self.assertEqual(store.get(final["handle"])["checkpoint"]["native_agents"], [witness(model=advisor)])

    def test_complete_requires_real_shaped_review_witness_and_passing_gate(self):
        variants = [dict(native_agents=[]), dict(native_agents=[witness(verdict="REQUEST_CHANGES")]),
                    dict(native_agents=[witness(model="grok-4.6")]),
                    dict(native_agents=[witness(agent_id="claimed")]),
                    dict(native_agents=[witness(reviewed_revision="")]),
                    dict(native_agents=[witness(transcript_ref="")]),
                    dict(validation=[]), dict(previous=None), dict(status="active")]
        for override in variants:
            with self.subTest(override=override), tempfile.TemporaryDirectory() as tmp:
                store = server.CheckpointStore(Path(tmp))
                value = checkpoint(phase="complete", status="complete", previous="a" * 32, native_agents=[witness()])
                value.update(override)
                with self.assertRaises(server.StoreError):
                    store.put(value)

    def test_new_gemini_led_and_mismatched_council_identities_refused(self):
        for override in (dict(leader_mode="gemini-led"), dict(council="luna-grok"),
                         dict(leader_model="gpt-5.6-luna-advisor"), dict(advisor_models=[]),
                         dict(advisor_models=["gemini-3.7-flash-advisor"]), dict(schema_version=1)):
            with self.subTest(override=override), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(server.StoreError):
                    server.CheckpointStore(Path(tmp)).put(checkpoint(**override))

    def test_same_run_cannot_switch_councils_with_or_without_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = server.CheckpointStore(Path(tmp))
            record, _ = store.put(checkpoint())
            for previous in (None, record["handle"]):
                with self.subTest(previous=previous), self.assertRaisesRegex(server.StoreError, "council identity"):
                    store.put(checkpoint(council="luna-grok", leader_mode="luna-grok", leader_model="gpt-5.6-luna",
                                         advisor_models=["grok-4.6"], previous=previous))

    def test_complete_must_follow_actual_review_without_changed_witnesses_or_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = server.CheckpointStore(Path(tmp))
            review = checkpoint(phase="review", native_agents=[witness()])
            prior, _ = store.put(review)
            for override in (dict(native_agents=[witness(reviewed_revision="different")]), dict(changed_paths=["other.py"]),
                             dict(validation=[{"command": "different gate", "status": "pass", "summary": "ok", "exit_code": 0}])):
                with self.subTest(override=override), self.assertRaisesRegex(server.StoreError, "completion must"):
                    value = dict(review, phase="complete", status="complete", previous=prior["handle"])
                    value.update(override)
                    store.put(value)

    def test_legacy_gemini_complete_readable_but_not_writable_or_resumable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = checkpoint(schema_version=1, phase="complete", status="complete", leader_mode="gemini-led",
                             leader_model="gemini-3.7-flash-high", advisor_models=["grok-4.6"])
            raw.pop("council")
            clean = server.validate_checkpoint(raw, allow_legacy=True)
            handle = "b" * 32
            record = {"handle": handle, "created_at": "2026-08-30T00:00:00Z", "digest": server.checkpoint_digest(clean), "checkpoint": clean}
            (root / f"{handle}.json").write_text(json.dumps(record))
            store = server.CheckpointStore(root)
            self.assertEqual(store.get(handle)["checkpoint"], clean)
            self.assertEqual(store.list(run_id=None, limit=10)[0]["handle"], handle)
            with self.assertRaisesRegex(server.StoreError, "read-only"):
                store.put(raw)
            with self.assertRaisesRegex(server.StoreError, "council identity"):
                store.put(checkpoint(previous=handle))

    def test_witness_secret_fields_and_secret_values_refused(self):
        for bad in (witness(api_key="not-a-real-secret-fixture"), witness(summary="Bearer not-a-real-secret-fixture-value")):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(server.StoreError):
                    server.CheckpointStore(Path(tmp)).put(checkpoint(native_agents=[bad]))
