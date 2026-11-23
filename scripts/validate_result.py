#!/usr/bin/env python3
"""Validate a literature-review result.json (structure + cross-references + counts).

Usage:
    python3 validate_result.py RESULT.json

Checks (errors block delivery; warnings should be explained in uncertainty):
  * required top-level fields and status enum
  * research_product / evidence_matrix / uncertainty sub-fields
  * screening_flow counts are consistent with screening_records
  * every evidence row has source_id/excerpt/location/claim/strength (4-level enum)
  * every evidence_id referenced by sections/conclusions resolves to an evidence row
  * every evidence row source_id resolves to a sources entry
  * claim_ids (C#) and evidence ids (E#) are unique
  * audit block present with the three sub-audits
  * coverage: included sources cited, themes have evidence, evidence rows used

Pure stdlib; no third-party packages.
"""
import json
import re
import sys

STRENGTHS = {"proven", "suggestive", "contested", "not_reported"}
SCREENING_STATUS = {"included", "excluded_duplicate", "excluded_irrelevant",
                    "excluded_other", "abstract_only"}


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("usage: validate_result.py RESULT.json", file=sys.stderr)
        return 2
    data = load(sys.argv[1])
    errors, warnings = [], []

    # ---- top level ----
    for field in ("case_id", "status", "research_product", "evidence_matrix",
                  "uncertainty", "sources", "change_record"):
        if field not in data:
            errors.append(f"missing top-level field: {field}")
    if data.get("status") not in ("success", "partial", "failed", "in_progress"):
        errors.append(f"status must be success|partial|failed|in_progress, got {data.get('status')!r}")

    rp = data.get("research_product", {})
    for field in ("research_question", "type", "themes", "sections", "conclusions"):
        if field not in rp:
            errors.append(f"research_product missing field: {field}")

    em = data.get("evidence_matrix", {})
    for field in ("screening_records", "evidence_rows"):
        if field not in em:
            errors.append(f"evidence_matrix missing field: {field}")

    un = data.get("uncertainty", {})
    for field in ("conflicts", "biases", "gaps", "undetermined"):
        if field not in un:
            errors.append(f"uncertainty missing field: {field}")

    if errors:
        return report(errors, warnings)

    # ---- sources & ids ----
    sources = {s.get("id") for s in data.get("sources", []) if isinstance(s, dict)}
    rows = em.get("evidence_rows", [])
    eids = [r.get("id") for r in rows if isinstance(r, dict)]
    if len(eids) != len(set(eids)):
        errors.append("duplicate evidence row ids")
    if eids and not all(re.fullmatch(r"E\d+", str(i) or "") for i in eids):
        warnings.append("evidence row ids should be E1, E2, ...")

    for r in rows:
        rid = r.get("id", "?")
        for f in ("source_id", "excerpt", "location", "claim", "strength"):
            if f not in r:
                errors.append(f"evidence row {rid}: missing {f}")
        if r.get("strength") not in STRENGTHS:
            errors.append(f"evidence row {rid}: bad strength {r.get('strength')!r}")
        if r.get("source_id") not in sources:
            errors.append(f"evidence row {rid}: unknown source_id {r.get('source_id')!r}")

    # ---- screening flow consistency ----
    recs = em.get("screening_records", [])
    for rec in recs:
        if rec.get("status") not in SCREENING_STATUS:
            errors.append(f"screening record {rec.get('id','?')}: bad status {rec.get('status')!r}")
        if not rec.get("reason"):
            warnings.append(f"screening record {rec.get('id','?')}: empty reason")
    flow = em.get("screening_flow")
    if isinstance(flow, dict):
        cnt = {}
        for rec in recs:
            cnt[rec.get("status")] = cnt.get(rec.get("status"), 0) + 1
        checks = [
            ("included", cnt.get("included", 0)),
            ("abstract_only", cnt.get("abstract_only", 0)),
            ("duplicates_removed", cnt.get("excluded_duplicate", 0)),
            ("excluded_irrelevant", cnt.get("excluded_irrelevant", 0)),
            ("excluded_other", cnt.get("excluded_other", 0)),
        ]
        for key, actual in checks:
            if key in flow and flow[key] != actual:
                errors.append(f"screening_flow.{key}={flow[key]} but records have {actual}")
        if "screened" in flow and flow["screened"] != len(recs) - cnt.get("excluded_duplicate", 0):
            errors.append("screening_flow.screened inconsistent with records")
    else:
        warnings.append("screening_flow missing; counts cannot be cross-checked")

    # ---- claim references ----
    eid_set = set(eids)
    used_eids, claim_ids = set(), []
    paragraphs = []
    for sec in rp.get("sections", []):
        paragraphs.extend(sec.get("paragraphs", []))
    paragraphs.extend(rp.get("conclusions", []))
    for p in paragraphs:
        cid = p.get("claim_id", "?")
        claim_ids.append(cid)
        if p.get("strength") not in STRENGTHS:
            errors.append(f"claim {cid}: bad strength {p.get('strength')!r}")
        for eid in p.get("evidence_ids", []):
            if eid not in eid_set:
                errors.append(f"claim {cid}: references unknown evidence id {eid!r}")
            used_eids.add(eid)
        if not p.get("evidence_ids"):
            errors.append(f"claim {cid}: no evidence_ids")
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("duplicate claim_ids")

    # ---- audit block ----
    audit = data.get("audit")
    if not isinstance(audit, dict):
        errors.append("missing audit block (second-pass audit is mandatory)")
    else:
        for sub in ("citation_audit", "coverage_check", "wording_audit"):
            if sub not in audit:
                errors.append(f"audit missing sub-audit: {sub}")

    # ---- coverage warnings ----
    cited = {r.get("source_id") for r in rows if r.get("id") in used_eids}
    included = {rec.get("id") for rec in recs if rec.get("status") == "included"}
    for sid in sorted(included - cited):
        warnings.append(f"included source {sid} is never cited by any claim")
    orphan = [e for e in eids if e not in used_eids]
    if orphan:
        warnings.append(f"evidence rows never used by any claim: {orphan}")
    theme_evidence = {r.get("source_id") for r in rows}
    for t in rp.get("themes", []):
        supporters = set(t.get("supported_by", []))
        if not supporters & theme_evidence:
            warnings.append(f"theme {t.get('id','?')} has no evidence-backed source")

    return report(errors, warnings)


def report(errors, warnings):
    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"OK: 0 error(s), {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
