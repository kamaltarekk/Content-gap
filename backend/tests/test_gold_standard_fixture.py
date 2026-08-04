"""Phase 0 acceptance gate: the gold-standard fixture is diagnosable against the frozen schemas.

Asserts:
- every expected gap has >= 1 evidence id and all referenced ids resolve;
- severity and confidence are separate (present on every gap; at least one gap has different
  severity/confidence labels, proving they are not collapsed);
- every enum-typed field uses a canonical value from docs/schemas/enums.json;
- content-piece evidence spans are verbatim substrings of the piece original_text, and VoC spans
  match their verbatim phrase (Arabic preserved, never rewritten).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENUMS = json.loads((ROOT / "docs" / "schemas" / "enums.json").read_text(encoding="utf-8"))["enums"]
FIXTURE = json.loads((ROOT / "fixtures" / "gold_standard" / "gold_standard.json").read_text(encoding="utf-8"))


def _evidence_ids() -> set[str]:
    ids: set[str] = set()
    for cp in FIXTURE["content_pieces"]:
        for span in cp["evidence_spans"]:
            ids.add(span["id"])
    for span in FIXTURE["voc_evidence_spans"]:
        ids.add(span["id"])
    return ids


def test_every_expected_gap_has_resolvable_evidence() -> None:
    known = _evidence_ids()
    for gap in FIXTURE["expected_gaps"]:
        assert gap["evidence_ids"], f"{gap['id']} has no evidence ids"
        missing = [e for e in gap["evidence_ids"] if e not in known]
        assert not missing, f"{gap['id']} references unknown evidence ids: {missing}"


def test_claim_and_context_evidence_resolves() -> None:
    known = _evidence_ids()
    for claim in FIXTURE["claims"]:
        for e in claim["evidence_ids"] + claim.get("proof_evidence_ids", []):
            assert e in known, f"{claim['id']} references unknown evidence id {e}"
    ctx = FIXTURE["context_version"]
    for key in ("attention_evidence_ids", "desire_evidence_ids", "persuasion_evidence_ids"):
        refs = ctx[key]
        assert len(refs) >= 2, f"{key} needs >= 2 evidence refs (spec 8.1)"
        for e in refs:
            assert e in known, f"context {key} references unknown evidence id {e}"


def test_severity_and_confidence_are_separate() -> None:
    labelled_differently = False
    for gap in FIXTURE["expected_gaps"]:
        assert gap["severity"] in ENUMS["severity_level"]
        assert gap["confidence"] in ENUMS["confidence_level"]
        assert 0 <= gap["severity_score"] <= 100
        assert 0 <= gap["confidence_score"] <= 100
        if gap["severity"] != gap["confidence"]:
            labelled_differently = True
    assert labelled_differently, "No gap demonstrates severity != confidence; they may be collapsed"


def test_all_enum_fields_are_canonical() -> None:
    checks = [
        ("context_version", "purchase_type", "purchase_type"),
        ("context_version", "primary_bottleneck", "primary_bottleneck"),
        ("context_version", "primary_decision_maker_role", "buying_group_role"),
        ("context_version", "primary_language", None),
    ]
    del checks  # entity + piece + gap checks below are the substantive ones
    for e in FIXTURE["entities"]:
        assert e["entity_type"] in ENUMS["entity_type"]
        if "competitor_type" in e:
            assert e["competitor_type"] in ENUMS["competitor_type"]
    ctx = FIXTURE["context_version"]
    assert ctx["purchase_type"] in ENUMS["purchase_type"]
    assert ctx["primary_bottleneck"] in ENUMS["primary_bottleneck"]
    assert ctx["primary_decision_maker_role"] in ENUMS["buying_group_role"]
    for cp in FIXTURE["content_pieces"]:
        assert cp["content_format"] in ENUMS["content_format"], cp["id"]
        assert cp["language_code"] in ENUMS["language_code"], cp["id"]
    for voc in FIXTURE["voc_entries"]:
        assert voc["bank_type"] in ENUMS["bank_type"], voc["id"]
    for claim in FIXTURE["claims"]:
        assert claim["claim_type"] in ENUMS["claim_type"], claim["id"]
        assert claim["proof_status"] in ENUMS["claim_proof_status"], claim["id"]
        assert claim["finding_status"] in ENUMS["finding_status"], claim["id"]
    for gap in FIXTURE["expected_gaps"]:
        assert gap["gap_type"] in ENUMS["gap_type"], gap["id"]
        assert gap["gap_status"] in ENUMS["gap_status"], gap["id"]
        assert gap["root_cause_type"] in ENUMS["root_cause_type"], gap["id"]
        assert gap["primary_bottleneck"] in ENUMS["primary_bottleneck"], gap["id"]
        if "journey_stage" in gap:
            assert gap["journey_stage"] in ENUMS["journey_stage"], gap["id"]
        if "micro_decision_type" in gap:
            assert gap["micro_decision_type"] in ENUMS["micro_decision_type"], gap["id"]
        if gap.get("buying_group_role"):
            assert gap["buying_group_role"] in ENUMS["buying_group_role"], gap["id"]


def test_evidence_spans_are_verbatim() -> None:
    for cp in FIXTURE["content_pieces"]:
        original = cp["original_text"]
        for span in cp["evidence_spans"]:
            assert span["quoted_text"] in original, (
                f"span {span['id']} is not a verbatim substring of {cp['id']}"
            )
            assert span["language_code"] in ENUMS["language_code"]
    # VoC spans must equal the verbatim phrase they capture (Arabic never rewritten).
    voc_by_span = {s["id"]: s["quoted_text"] for s in FIXTURE["voc_evidence_spans"]}
    for voc in FIXTURE["voc_entries"]:
        span_text = voc_by_span[voc["evidence_span_id"]]
        assert voc["verbatim_phrase"] == span_text, f"{voc['id']} phrase rewritten vs its span"


def test_fixture_shape_matches_spec_minimums() -> None:
    assert sum(1 for e in FIXTURE["entities"] if e["entity_type"] == "brand") == 1
    assert sum(1 for e in FIXTURE["entities"] if e["entity_type"] == "competitor") == 2
    assert 15 <= len(FIXTURE["content_pieces"]) <= 20
    statuses = {g["gap_status"] for g in FIXTURE["expected_gaps"]}
    # confirmed, probable, false (rejected), white-space (candidate), non-content blocker
    assert {"confirmed", "probable", "rejected", "candidate", "non_content_blocker"} <= statuses
    types = {g["gap_type"] for g in FIXTURE["expected_gaps"]}
    assert "market_white_space" in types and "false_opportunity" in types and "non_content_gap" in types
