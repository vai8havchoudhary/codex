from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from test_checkpoint_server import checkpoint, server
from test_named_councils import witness
from support import preflight


class GeminiFreshnessTests(unittest.TestCase):
    def historical(self, root, payload):
        clean = server.validate_checkpoint(payload, allow_legacy=True)
        canonical = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        handle = "c" * 32
        record = {"handle": handle, "created_at": "2026-08-30T00:00:00Z",
                  "digest": hashlib.sha256(canonical).hexdigest(), "checkpoint": clean}
        (root / f"{handle}.json").write_text(json.dumps(record))
        return record

    def test_same_id_multiple_roles_rejected_only_for_gemini_new_writes(self):
        raw = checkpoint(phase="review", native_agents=[witness(), witness(role="critic")])
        with self.assertRaisesRegex(server.CheckpointError, "distinct"):
            server.validate_checkpoint(raw)
        luna = dict(raw, council="luna-grok", leader_mode="luna-grok", leader_model="gpt-5.6-luna",
                    advisor_models=["grok-4.6"], native_agents=[witness(model="grok-4.6"), witness(role="critic", model="grok-4.6")])
        self.assertEqual(len(server.validate_checkpoint(luna)["native_agents"]), 2)

    def test_prior_gate_id_cannot_hide_by_omitting_witnesses_or_previous(self):
        for role in ("localizer", "critic", "recovery"):
            for include_previous in (False, True):
                with self.subTest(role=role, previous=include_previous), tempfile.TemporaryDirectory() as tmp:
                    store = server.CheckpointStore(Path(tmp))
                    old, _ = store.put(checkpoint(phase="plan", native_agents=[witness(role=role, verdict="OBSERVED")]))
                    with self.assertRaisesRegex(server.StoreError, "earlier same-run"):
                        store.put(checkpoint(phase="review", native_agents=[witness()],
                                             previous=old["handle"] if include_previous else None))

    def test_fresh_final_review_after_critic_and_idempotent_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = server.CheckpointStore(Path(tmp))
            prior, _ = store.put(checkpoint(phase="plan", native_agents=[witness(role="critic", verdict="APPROVE")]))
            review = checkpoint(phase="review", previous=prior["handle"], native_agents=[witness(agent_id="fresh-gemini-reviewer-12345")])
            record, _ = store.put(review)
            self.assertFalse(store.put(review)[1])
            complete = dict(review, phase="complete", status="complete", previous=record["handle"])
            final, _ = store.put(complete)
            self.assertFalse(store.put(complete)[1])
            self.assertFalse(store.put(review)[1])  # old immutable milestone remains idempotent
            self.assertEqual(store.get(final["handle"])["checkpoint"]["native_agents"], review["native_agents"])

    def test_failed_review_storable_but_repaired_review_requires_fresh_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = server.CheckpointStore(Path(tmp))
            raw = checkpoint(phase="review", native_agents=[witness(verdict="REQUEST_CHANGES")])
            prior, _ = store.put(raw)
            self.assertEqual(store.get(prior["handle"])["checkpoint"]["native_agents"][0]["verdict"], "REQUEST_CHANGES")
            with self.assertRaisesRegex(server.StoreError, "APPROVE"):
                store.put(dict(raw, phase="complete", status="complete", previous=prior["handle"]))
            with self.assertRaisesRegex(server.StoreError, "fresh"):
                store.put(checkpoint(phase="review", native_agents=[witness(reviewed_revision="repaired-diff")]))
            store.put(checkpoint(phase="review", native_agents=[witness(agent_id="fresh-after-repair-123456", reviewed_revision="repaired-diff")]))

    def test_historical_schema2_role_collision_digest_and_listing_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = checkpoint(phase="review", native_agents=[witness(), witness(role="critic")])
            historical = self.historical(root, raw)
            store = server.CheckpointStore(root)
            self.assertEqual(store.get(historical["handle"]), historical)
            self.assertEqual(store.list(run_id=None, limit=10)[0]["handle"], historical["handle"])
            with self.assertRaisesRegex(server.StoreError, "distinct"):
                store.put(raw)

    def test_historical_ready_reviewer_cannot_become_new_final_reviewer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            historical = self.historical(root, checkpoint(phase="preflight", native_agents=[witness(verdict="OBSERVED")]))
            store = server.CheckpointStore(root)
            self.assertEqual(store.get(historical["handle"]), historical)
            with self.assertRaisesRegex(server.StoreError, "fresh"):
                store.put(checkpoint(phase="review", native_agents=[witness()]))
            with self.assertRaisesRegex(server.StoreError, "not reserved"):
                store.put(checkpoint(phase="preflight", native_agents=[witness(verdict="OBSERVED")]))

    def test_prior_agent_in_other_run_does_not_collide(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = server.CheckpointStore(Path(tmp))
            store.put(checkpoint(run_id="other-run", phase="plan", native_agents=[witness(role="critic")]))
            store.put(checkpoint(phase="review", native_agents=[witness()]))


class DescriptorTests(unittest.TestCase):
    def test_item_fields_required_keys_types_and_limits_match_validator(self):
        examples = {
            "evidence": ({"kind": "packet", "summary": "gate=final-review; attempt=1; fresh=true; packet_sha256=" + "a" * 64,
                          "command": "git diff", "exit_code": None}, {"kind", "summary"}),
            "validation": ({"command": "python3 -m unittest", "status": "pass", "summary": "all passed", "exit_code": 0},
                            {"command", "status", "summary"}),
            "native_agents": (witness(), {"role", "model", "agent_id", "verdict", "summary", "transcript_ref"}),
        }
        for tool in server.tool_definitions()[:2]:
            for field, (valid, required) in examples.items():
                with self.subTest(tool=tool["name"], field=field):
                    schema = tool["inputSchema"]["properties"][field]["items"]
                    self.assertEqual(schema["type"], "object")
                    self.assertFalse(schema["additionalProperties"])
                    self.assertEqual(set(schema["required"]), required)
                    self.assertEqual(set(schema["properties"]), set(valid))
                    self.assertEqual(server.validate_checkpoint(checkpoint(phase="review", **{field: [valid]}))[field], [valid])
                    for key in required:
                        bad = dict(valid); del bad[key]
                        with self.assertRaises(server.CheckpointError):
                            server.validate_checkpoint(checkpoint(phase="review", **{field: [bad]}))
                    for key, prop in schema["properties"].items():
                        bad = dict(valid, **{key: []})
                        with self.assertRaises(server.CheckpointError):
                            server.validate_checkpoint(checkpoint(phase="review", **{field: [bad]}))
                        if "maxLength" in prop:
                            bad = dict(valid, **{key: "x" * (prop["maxLength"] + 1)})
                            with self.assertRaises(server.CheckpointError):
                                server.validate_checkpoint(checkpoint(phase="review", **{field: [bad]}))
                        if key == "exit_code":
                            self.assertEqual(prop["type"], ["integer", "null"])
                        else:
                            self.assertEqual(prop["type"], "string")
                    with self.assertRaises(server.CheckpointError):
                        server.validate_checkpoint(checkpoint(phase="review", **{field: [dict(valid, unexpected="no")]}))
        evidence = server.tool_definitions()[0]["inputSchema"]["properties"]["evidence"]["items"]
        for guessed in ("advisor_model", "catalog_admission", "council", "leader_model", "provider_id"):
            self.assertNotIn(guessed, evidence["properties"])

    def test_reviewed_revision_requirement_and_enums_are_explicit(self):
        props = server.tool_definitions()[0]["inputSchema"]["properties"]
        native = props["native_agents"]["items"]["properties"]
        self.assertIn("Required for role=reviewer", native["reviewed_revision"]["description"])
        self.assertEqual(set(native["verdict"]["enum"]), {"OBSERVED", "APPROVE", "REQUEST_CHANGES"})
        self.assertEqual(set(native["role"]["enum"]), {"localizer", "critic", "reviewer", "recovery"})
        self.assertEqual(set(props["validation"]["items"]["properties"]["status"]["enum"]), {"pending", "pass", "fail", "skipped"})
        bad = witness(); del bad["reviewed_revision"]
        with self.assertRaises(server.CheckpointError):
            server.validate_checkpoint(checkpoint(phase="review", native_agents=[bad]))


class CouncilPolicyTests(unittest.TestCase):
    def test_luna_generated_instructions_are_byte_identical(self):
        catalog, _ = preflight.load_authority()
        expected = ("ROOT SESSION ONLY: For the user's repository task use the installed codex-moa luna-grok skill and its shared policy. "
                    "Council=luna-grok; acting root model must be gpt-5.6-luna; native advisor/reviewer model must be grok-4.6. "
                    "Read the skill before task actions. Run council preflight; stop if the skill, checkpoint MCP, "
                    "or native spawn/wait tools are unavailable. Do not substitute models or simulate agent results. "
                    "One read-only localizer reused for plan criticism; reserve a second proven read-only final reviewer before edits. "
                    "Root is the single writer. CHILD AGENTS: ignore these root coordination obligations; retain your explicitly "
                    "assigned model and read-only role, answer the parent, and do not start a council or restart as the leader.")
        self.assertEqual(catalog.council_instructions("luna-grok"), expected)
        gemini = catalog.council_instructions("grok-gemini")
        for clause in ("NO tools", "NO READY", "NO send_input", "INITIAL", "distinct fresh final reviewer",
                       "at most one fresh transport retry", "CHILD AGENTS", "Root gathers repository evidence"):
            self.assertIn(clause, gemini)
        self.assertNotIn("reserve a second", gemini)

    def test_shipped_surfaces_route_gemini_to_evidence_only_policy(self):
        plugin = Path(__file__).resolve().parents[1]
        for relative in ("commands/run.md", "commands/review.md", "commands/grok-gemini.md",
                         "skills/grok-gemini/SKILL.md", "agents/critic.md", "agents/verifier.md"):
            text = (plugin / relative).read_text()
            for clause in ("supplied evidence", "NO tools", "READY", "follow-ups"):
                self.assertIn(clause, text, relative)
        policy = (plugin / "skills/codex-moa/SKILL.md").read_text()
        for clause in ("complete final diff", "relevant full resulting files", "packet_sha256", "attempt=1", "fresh=true",
                       "at most one fresh transport retry", "at most five minutes total", "at most two coherent repair rounds",
                       "stop blocked", "No critic fallback", "not an implementation repair"):
            self.assertIn(clause, policy)

    def test_public_docs_disclose_limits_and_historical_schema2(self):
        root = Path(__file__).resolve().parents[3]
        for relative in ("README.md", "SECURITY.md", "PRIVACY.md", "plugins/codex-moa/README.md"):
            text = (root / relative).read_text()
            for phrase in ("supplied evidence", "SHA-256", "schema-2", "continuation"):
                self.assertIn(phrase, text, relative)
