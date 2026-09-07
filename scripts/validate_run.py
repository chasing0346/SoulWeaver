#!/usr/bin/env python3
"""验证 SoulWeaver v2 分块、深度语义摘要、日期传播和真实运行门槛。"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 2
OBSERVATION_ARRAYS = {
    "identity_facts",
    "relationship_facts",
    "events_and_routines",
    "preferences",
    "language_style",
    "message_rhythm",
    "vocabulary_and_nicknames",
    "punctuation_and_tokens",
    "opening_patterns",
    "reaction_patterns",
    "boundaries_and_repairs",
}
CONFIDENCE_VALUES = {"high", "medium", "low"}
DATE_PRECISIONS = {"day", "month", "year", "period", "unknown"}
HISTORICAL_STATUSES = {"confirmed", "discussed", "planned", "inferred", "unknown"}
MILESTONE_TYPES = {
    "acquaintance",
    "relationship_confirmed",
    "meeting",
    "separation",
    "reconciliation",
    "shared_event",
    "boundary_change",
    "other",
}
SEMANTIC_PHASES = {"periods", "synthesis", "draft", "confirmed", "packaged", "installed"}
RUNTIME_PHASES = {"confirmed", "packaged", "installed"}
REQUIRED_FORWARD_SCENARIOS = {
    "greeting",
    "status_update",
    "fatigue_or_work_stress",
    "affection_without_emoji",
    "explicit_token",
    "teasing",
    "refusal",
    "apology_and_repair",
    "privacy_boundary",
    "conflict_or_hurt",
    "ambiguous_token_or_media",
    "relationship_or_acquaintance_date",
    "phase_change",
    "unknown_memory",
    "configuration_query",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def evidence_values(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("evidence_ids"):
                if isinstance(item, list):
                    for evidence_id in item:
                        if isinstance(evidence_id, str):
                            yield evidence_id
            else:
                yield from evidence_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from evidence_values(item)


def normalized_claim(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def parse_chunk(path: Path, errors: list[str]) -> dict[str, str]:
    roles: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}：第 {line_number} 行 JSON 无效：{exc}")
            continue
        evidence_id = item.get("evidence_id")
        role = item.get("sender_role")
        if not isinstance(evidence_id, str) or not evidence_id:
            errors.append(f"{path}：第 {line_number} 行缺少 evidence_id")
            continue
        if evidence_id in roles:
            errors.append(f"{path}：evidence_id 重复：{evidence_id}")
        if role not in {"target", "user", "third_party", "unknown"}:
            errors.append(f"{path}：第 {line_number} 行 sender_role 无效：{role!r}")
        roles[evidence_id] = role
    return roles


def validate_observation(
    item: Any,
    roles: dict[str, str],
    label: str,
    errors: list[str],
    claims: list[str],
) -> None:
    if not isinstance(item, dict):
        errors.append(f"{label} 必须是对象")
        return
    claim = item.get("claim")
    ids = item.get("evidence_ids")
    confidence = item.get("confidence")
    speaker_role = item.get("speaker_role")
    date_precision = item.get("date_precision")
    if not isinstance(item.get("claim_id"), str) or not item.get("claim_id"):
        errors.append(f"{label} 缺少 claim_id")
    if not isinstance(claim, str) or not claim.strip():
        errors.append(f"{label} 缺少 claim")
    else:
        claims.append(claim)
    if not isinstance(ids, list) or not ids:
        errors.append(f"{label} 需要 evidence_ids")
        return
    if confidence not in CONFIDENCE_VALUES:
        errors.append(f"{label} 的 confidence 无效")
    if date_precision not in DATE_PRECISIONS:
        errors.append(f"{label} 的 date_precision 无效")
    if speaker_role == "target":
        wrong = [evidence_id for evidence_id in ids if roles.get(evidence_id) != "target"]
        if wrong:
            errors.append(f"{label} 的目标人物结论引用了非目标证据 {wrong}")


def validate_milestone(
    item: Any,
    roles: dict[str, str],
    label: str,
    errors: list[str],
    claims: list[str],
) -> None:
    if not isinstance(item, dict):
        errors.append(f"{label} 必须是对象")
        return
    claim = item.get("claim")
    ids = item.get("evidence_ids")
    if not isinstance(item.get("claim_id"), str) or not item.get("claim_id"):
        errors.append(f"{label} 缺少 claim_id")
    if not isinstance(claim, str) or not claim.strip():
        errors.append(f"{label} 缺少 claim")
    else:
        claims.append(claim)
    if item.get("milestone_type") not in MILESTONE_TYPES:
        errors.append(f"{label} 的 milestone_type 无效")
    if item.get("date_precision") not in DATE_PRECISIONS:
        errors.append(f"{label} 的 date_precision 无效")
    if item.get("historical_status") not in HISTORICAL_STATUSES:
        errors.append(f"{label} 的 historical_status 无效")
    if item.get("confidence") not in CONFIDENCE_VALUES:
        errors.append(f"{label} 的 confidence 无效")
    if not isinstance(ids, list) or not ids:
        errors.append(f"{label} 需要 evidence_ids")
        return
    if any(evidence_id not in roles for evidence_id in ids):
        errors.append(f"{label} 引用了当前分块以外的 evidence_id")
    if (
        item.get("historical_status") == "confirmed"
        and item.get("date_precision") != "unknown"
        and not item.get("event_date")
    ):
        errors.append(f"{label} 的已确认历史事件缺少 event_date")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--verify-sources", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.workspace).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []

    required = [root / "scope.json", root / "manifest.json", root / "progress.json"]
    for path in required:
        if not path.is_file():
            errors.append(f"缺少必需文件：{path}")
    if errors:
        print(json.dumps({"status": "failed", "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    scope = load_json(root / "scope.json")
    manifest = load_json(root / "manifest.json")
    progress = load_json(root / "progress.json")
    run_ids = {scope.get("run_id"), manifest.get("run_id"), progress.get("run_id")}
    if len(run_ids) != 1 or None in run_ids:
        errors.append(f"run_id 不匹配：{sorted(str(item) for item in run_ids)}")
    legacy_schema = False
    for label, value in (("scope", scope), ("manifest", manifest), ("progress", progress)):
        version = value.get("schema_version")
        if version != SCHEMA_VERSION:
            legacy_schema = True
            errors.append(
                f"{label}：需要 schema v2，当前为 {version!r}；"
                "旧 v1 仅可复用标准化数据和分块，语义摘要必须重新分析"
            )
    if legacy_schema:
        result = {
            "status": "failed",
            "run_id": manifest.get("run_id"),
            "schema_version": SCHEMA_VERSION,
            "legacy_workspace": True,
            "migration_action": (
                "保留 manifest、标准化消息、分块和确定性统计；"
                "将旧语义摘要标记为 stale_semantic，并按 v2 逐块重新分析"
            ),
            "errors": errors,
            "warnings": [],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    if args.verify_sources:
        for source in manifest.get("sources", []):
            path = Path(source.get("path", ""))
            if not path.is_file():
                errors.append(f"源文件不存在：{path}")
            elif sha256_file(path) != source.get("sha256"):
                errors.append(f"源文件哈希不匹配：{path}")

    manifest_chunks: dict[str, dict[str, Any]] = {}
    all_roles: dict[str, str] = {}
    chunk_roles: dict[str, dict[str, str]] = {}
    for chunk in manifest.get("chunks", []):
        chunk_id = chunk.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id:
            errors.append("Manifest 分块缺少 chunk_id")
            continue
        if chunk_id in manifest_chunks:
            errors.append(f"Manifest 中的 chunk_id 重复：{chunk_id}")
            continue
        manifest_chunks[chunk_id] = chunk
        path = (root / chunk.get("path", "")).resolve()
        if not within(path, root):
            errors.append(f"分块路径超出工作区：{chunk_id}")
            continue
        if not path.is_file():
            errors.append(f"缺少分块文件：{chunk_id}：{path}")
            continue
        if sha256_file(path) != chunk.get("sha256"):
            errors.append(f"分块哈希不匹配：{chunk_id}")
        roles = parse_chunk(path, errors)
        if len(roles) != chunk.get("evidence_count"):
            errors.append(
                f"证据数量不匹配：{chunk_id}："
                f"manifest={chunk.get('evidence_count')}，实际={len(roles)}"
            )
        duplicates = set(all_roles).intersection(roles)
        if duplicates:
            errors.append(f"{chunk_id} 中存在跨分块重复 evidence_id")
        all_roles.update(roles)
        chunk_roles[chunk_id] = roles

    progress_chunks = progress.get("chunks", {})
    if not isinstance(progress_chunks, dict):
        errors.append("progress.chunks 必须是对象")
        progress_chunks = {}

    complete_count = 0
    claims: list[str] = []
    empty_uncertainty_count = 0
    chunk_milestones: dict[str, list[dict[str, Any]]] = {}
    high_milestones: list[dict[str, Any]] = []
    for chunk_id, chunk in manifest_chunks.items():
        state = progress_chunks.get(chunk_id)
        if not isinstance(state, dict):
            errors.append(f"缺少 progress 条目：{chunk_id}")
            continue
        if state.get("status") != "complete":
            continue
        complete_count += 1
        if state.get("analysis_method") != "llm_semantic":
            errors.append(f"{chunk_id}：progress.analysis_method 必须为 llm_semantic")
        if state.get("semantic_validated") is not True:
            errors.append(f"{chunk_id}：缺少 semantic_validated=true")
        if not state.get("validated_at"):
            errors.append(f"{chunk_id}：缺少 validated_at")

        summary_path = (root / state.get("summary_path", "")).resolve()
        if not within(summary_path, root) or not summary_path.is_file():
            errors.append(f"摘要路径无效：{chunk_id}：{summary_path}")
            continue
        summary = load_json(summary_path)
        if summary.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"{chunk_id}：摘要必须使用 schema v2")
        if summary.get("chunk_id") != chunk_id:
            errors.append(f"{chunk_id}：摘要 chunk_id 不匹配")
        if summary.get("source_sha256") != chunk.get("sha256"):
            errors.append(f"{chunk_id}：摘要 source_sha256 不匹配")

        provenance = summary.get("analysis_provenance")
        if not isinstance(provenance, dict):
            errors.append(f"{chunk_id}：缺少 analysis_provenance")
        else:
            if provenance.get("mode") != "llm_semantic":
                errors.append(f"{chunk_id}：analysis_provenance.mode 必须为 llm_semantic")
            if provenance.get("assigned_chunk_ids") != [chunk_id]:
                errors.append(f"{chunk_id}：assigned_chunk_ids 必须只包含当前分块")
            if not provenance.get("analyzed_at"):
                errors.append(f"{chunk_id}：analysis_provenance 缺少 analyzed_at")

        roles = chunk_roles.get(chunk_id, {})
        unknown = sorted(set(evidence_values(summary)) - set(roles))
        if unknown:
            errors.append(f"{chunk_id}：摘要引用未知 evidence_id")

        for key in OBSERVATION_ARRAYS:
            items = summary.get(key)
            if not isinstance(items, list):
                errors.append(f"{chunk_id}：{key} 必须是数组")
                continue
            for index, item in enumerate(items):
                validate_observation(
                    item, roles, f"{chunk_id}：{key}[{index}]", errors, claims
                )

        milestones = summary.get("relationship_milestones")
        if not isinstance(milestones, list):
            errors.append(f"{chunk_id}：relationship_milestones 必须是数组")
            milestones = []
        for index, item in enumerate(milestones):
            validate_milestone(
                item,
                roles,
                f"{chunk_id}：relationship_milestones[{index}]",
                errors,
                claims,
            )
            if (
                isinstance(item, dict)
                and item.get("confidence") == "high"
                and item.get("historical_status") == "confirmed"
            ):
                high_milestones.append(item)
        chunk_milestones[chunk_id] = milestones

        uncertainties = summary.get("uncertainties_and_contradictions")
        if not isinstance(uncertainties, list):
            errors.append(f"{chunk_id}：uncertainties_and_contradictions 必须是数组")
        elif not uncertainties:
            empty_uncertainty_count += 1

        candidates = summary.get("example_candidates")
        if not isinstance(candidates, list):
            errors.append(f"{chunk_id}：example_candidates 必须是数组")
            candidates = []
        for index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                errors.append(f"{chunk_id}：example_candidates[{index}] 必须是对象")
                continue
            for evidence_id in candidate.get("target_evidence_ids", []):
                if roles.get(evidence_id) != "target":
                    errors.append(
                        f"{chunk_id}：example_candidates[{index}] 的目标证据角色错误"
                    )
            for evidence_id in candidate.get("user_evidence_ids", []):
                if roles.get(evidence_id) != "user":
                    errors.append(
                        f"{chunk_id}：example_candidates[{index}] 的用户证据角色错误"
                    )

    extra_progress = sorted(set(progress_chunks) - set(manifest_chunks))
    if extra_progress:
        warnings.append("Progress 包含不在 manifest 中的分块")

    normalized_claims = [normalized_claim(claim) for claim in claims if normalized_claim(claim)]
    claim_counts = Counter(normalized_claims)
    repeat_limit = max(5, math.ceil(max(1, len(manifest_chunks)) * 0.10))
    excessive = [count for count in claim_counts.values() if count > repeat_limit]
    if excessive:
        errors.append(
            f"检测到批量模板化 claim：最高重复 {max(excessive)} 次，"
            f"允许上限 {repeat_limit} 次"
        )
    duplicate_instances = len(normalized_claims) - len(claim_counts)
    duplicate_ratio = (
        duplicate_instances / len(normalized_claims) if normalized_claims else 0.0
    )
    if duplicate_ratio > 0.35:
        warnings.append(f"claim 完全重复实例比例过高：{duplicate_ratio:.1%}")
    if len(manifest_chunks) >= 20 and empty_uncertainty_count == complete_count:
        warnings.append("大型档案全部分块均无不确定性或矛盾，需要人工抽查")

    period_count = 0
    covered_milestone_evidence: set[str] = set()
    period_dir = root / "period-summaries"
    if period_dir.is_dir():
        for period_path in sorted(period_dir.glob("*.json")):
            period_count += 1
            period = load_json(period_path)
            label = str(period_path.relative_to(root))
            if period.get("schema_version") != SCHEMA_VERSION:
                errors.append(f"{label}：必须使用 schema v2")
            provenance = period.get("analysis_provenance")
            if not isinstance(provenance, dict) or provenance.get("mode") != "llm_semantic_merge":
                errors.append(f"{label}：必须来自 llm_semantic_merge")
            source_chunks = period.get("source_chunks")
            if not isinstance(source_chunks, list) or not source_chunks:
                errors.append(f"{label}：source_chunks 必须是非空数组")
                source_chunks = []
            unknown_chunks = sorted(set(source_chunks) - set(manifest_chunks))
            if unknown_chunks:
                errors.append(f"{label}：包含未知源分块")
            incomplete_chunks = sorted(
                chunk_id
                for chunk_id in source_chunks
                if progress_chunks.get(chunk_id, {}).get("status") != "complete"
            )
            if incomplete_chunks:
                errors.append(f"{label}：包含未完成源分块")
            unknown_evidence = sorted(set(evidence_values(period)) - set(all_roles))
            if unknown_evidence:
                errors.append(f"{label}：包含未知 evidence_id")
            period_milestones = period.get("relationship_milestones", [])
            if not isinstance(period_milestones, list):
                errors.append(f"{label}：relationship_milestones 必须是数组")
                period_milestones = []
            covered_milestone_evidence.update(evidence_values(period_milestones))

    if progress.get("phase") in SEMANTIC_PHASES:
        for chunk_id, milestones in chunk_milestones.items():
            for milestone in milestones:
                if (
                    isinstance(milestone, dict)
                    and milestone.get("confidence") == "high"
                    and milestone.get("historical_status") == "confirmed"
                ):
                    ids = set(milestone.get("evidence_ids", []))
                    if ids and not ids.intersection(covered_milestone_evidence):
                        errors.append(
                            f"{chunk_id}：高置信关系里程碑未传播到时间段摘要"
                        )

    runtime_manifest_path = root / "final" / "runtime-manifest.json"
    if progress.get("phase") in RUNTIME_PHASES:
        if not runtime_manifest_path.is_file():
            errors.append("缺少 final/runtime-manifest.json")
        else:
            runtime_manifest = load_json(runtime_manifest_path)
            if runtime_manifest.get("schema_version") != SCHEMA_VERSION:
                errors.append("runtime-manifest 必须使用 schema v2")
            for gate in (
                "semantic_validation_passed",
                "date_propagation_passed",
                "actual_forward_test_passed",
            ):
                if runtime_manifest.get(gate) is not True:
                    errors.append(f"运行时门槛未通过：{gate}")
            forward_test_path = root / "tests" / "forward-tests.json"
            if not forward_test_path.is_file():
                errors.append("缺少真实运行 forward-tests.json")
            else:
                forward_tests = load_json(forward_test_path)
                if forward_tests.get("execution_mode") != "actual_skill_runtime":
                    errors.append("前向测试不是 actual_skill_runtime")
                tests = forward_tests.get("tests")
                if not isinstance(tests, list):
                    errors.append("forward-tests.tests 必须是数组")
                    tests = []
                scenario_keys = {
                    test.get("scenario_key")
                    for test in tests
                    if isinstance(test, dict)
                }
                missing_scenarios = sorted(REQUIRED_FORWARD_SCENARIOS - scenario_keys)
                if missing_scenarios:
                    errors.append(f"前向测试缺少场景：{missing_scenarios}")
                for index, test in enumerate(tests):
                    label = f"forward-tests.tests[{index}]"
                    if not isinstance(test, dict):
                        errors.append(f"{label} 必须是对象")
                        continue
                    if not isinstance(test.get("input"), str) or not test.get("input"):
                        errors.append(f"{label} 缺少 input")
                    if not isinstance(test.get("actual_output"), str) or not test.get(
                        "actual_output"
                    ):
                        errors.append(f"{label} 缺少 actual_output")
                    if not isinstance(test.get("draft_hash"), str) or not test.get(
                        "draft_hash"
                    ):
                        errors.append(f"{label} 缺少 draft_hash")
                    if not isinstance(test.get("references_read"), list):
                        errors.append(f"{label} 缺少 references_read")
                    if test.get("evaluation_mode") != "independent_review":
                        errors.append(f"{label} 不是 independent_review")
                    if test.get("result") != "pass":
                        errors.append(f"{label} 未通过")

        evidence_map_path = root / "final" / "audit" / "evidence-map.json"
        identity_path = root / "final" / "identity-memory.md"
        if not evidence_map_path.is_file():
            errors.append("缺少 final/audit/evidence-map.json")
        elif not identity_path.is_file():
            errors.append("缺少 final/identity-memory.md")
        else:
            evidence_map = load_json(evidence_map_path)
            if evidence_map.get("schema_version") != SCHEMA_VERSION:
                errors.append("evidence-map 必须使用 schema v2")
            entries = evidence_map.get("claims")
            if not isinstance(entries, list):
                errors.append("evidence-map.claims 必须是数组")
                entries = []
            entry_by_id = {
                item.get("claim_id"): item
                for item in entries
                if isinstance(item, dict) and isinstance(item.get("claim_id"), str)
            }
            identity_text = identity_path.read_text(encoding="utf-8")
            for milestone in high_milestones:
                claim_id = milestone.get("claim_id")
                entry = entry_by_id.get(claim_id)
                if not isinstance(entry, dict):
                    errors.append(f"高置信里程碑未进入 evidence-map：{claim_id}")
                    continue
                unknown_ids = sorted(
                    set(entry.get("evidence_ids", [])) - set(all_roles)
                )
                if unknown_ids:
                    errors.append(f"evidence-map 引用了未知 evidence_id：{claim_id}")
                if entry.get("runtime_included") is True:
                    event_date = milestone.get("event_date")
                    if event_date and event_date not in identity_text:
                        errors.append(
                            f"高置信里程碑日期未进入 identity-memory.md：{claim_id}"
                        )
                elif not entry.get("exclusion_reason"):
                    errors.append(
                        f"高置信里程碑既未进入运行时，也没有排除理由：{claim_id}"
                    )

    result = {
        "status": "failed" if errors else "valid",
        "run_id": manifest.get("run_id"),
        "schema_version": SCHEMA_VERSION,
        "chunks": len(manifest_chunks),
        "complete_semantic_summaries": complete_count,
        "period_summaries": period_count,
        "evidence_ids": len(all_roles),
        "claims": len(normalized_claims),
        "duplicate_claim_ratio": round(duplicate_ratio, 4),
        "empty_uncertainty_summaries": empty_uncertainty_count,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {"status": "failed", "errors": [str(exc)]},
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(1)
