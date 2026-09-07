#!/usr/bin/env python3
"""在取得明确授权后，初始化一个隔离的 SoulWeaver 分析运行。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--deny", action="append", default=[])
    parser.add_argument("--target-display-name", required=True)
    parser.add_argument("--target-sender", action="append", required=True)
    parser.add_argument("--user-sender", action="append", required=True)
    parser.add_argument("--output-display-name", required=True)
    parser.add_argument("--skill-name", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--subagents", type=int, default=3)
    parser.add_argument("--subagent-model", default="gpt-5.6-luna")
    parser.add_argument("--subagent-reasoning-effort", default="max")
    parser.add_argument("--forbid", action="append", default=[])
    parser.add_argument("--verbatim-examples-authorized", action="store_true")
    parser.add_argument("--authorization-confirmed", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.authorization_confirmed:
        raise SystemExit("拒绝初始化：必须提供 --authorization-confirmed")
    if not SLUG_RE.fullmatch(args.skill_name) or len(args.skill_name) > 64:
        raise SystemExit("Skill 名称无效：只能使用小写 ASCII 字母、数字和连字符")
    if args.subagents < 0 or args.subagents > 3:
        raise SystemExit("--subagents 必须介于 0 和 3 之间")

    workspace = Path(args.workspace).expanduser().resolve()
    if workspace.exists() and any(workspace.iterdir()):
        raise SystemExit(f"工作区不是空目录：{workspace}")

    denied = [Path(item).expanduser().resolve() for item in args.deny]
    sources: list[Path] = []
    for item in args.source:
        source = Path(item).expanduser().resolve()
        if not source.is_file():
            raise SystemExit(f"已批准的数据源不是可读文件：{source}")
        if any(source == deny or path_is_within(source, deny) for deny in denied):
            raise SystemExit(f"已批准的数据源与拒绝列表冲突：{source}")
        sources.append(source)

    workspace.mkdir(parents=True, exist_ok=True)
    for name in (
        "normalized",
        "chunks",
        "chunk-stats",
        "chunk-summaries",
        "period-summaries",
        "final",
        "final/audit",
        "audits",
        "tests",
        "draft-skill",
    ):
        (workspace / name).mkdir()

    run_id = args.run_id or f"sw-{uuid.uuid4().hex[:12]}"
    created_at = utc_now()
    source_records = []
    for index, source in enumerate(sources, start=1):
        source_records.append(
            {
                "source_id": f"source-{index:03d}",
                "path": str(source),
                "sha256": sha256_file(source),
                "size_bytes": source.stat().st_size,
                "format": source.suffix.lower().lstrip(".") or "other",
            }
        )

    scope = {
        "schema_version": 2,
        "run_id": run_id,
        "authorized_at": created_at,
        "authorization_confirmed": True,
        "read_allowlist": [str(path) for path in sources],
        "read_denylist": [str(path) for path in denied],
        "write_allowlist": [str(workspace)],
        "target": {
            "display_name": args.target_display_name,
            "sender_ids": list(dict.fromkeys(args.target_sender)),
        },
        "user_sender_ids": list(dict.fromkeys(args.user_sender)),
        "output": {
            "display_name": args.output_display_name,
            "skill_name": args.skill_name,
        },
        "subagents": {
            "authorized": args.subagents > 0,
            "target_count": args.subagents,
            "max_concurrency": args.subagents,
            "model": args.subagent_model,
            "reasoning_effort": args.subagent_reasoning_effort,
            "capacity_fallback": "use_available_slots_and_refill",
        },
        "verbatim_examples": {
            "authorized_for_packaging": args.verbatim_examples_authorized,
            "quota_policy": "min(E, min(24, max(3, round(sqrt(E/100)))))",
            "candidate_preview_required": True,
        },
        "forbidden_identifiers": list(dict.fromkeys(args.forbid)),
    }
    manifest = {
        "schema_version": 2,
        "run_id": run_id,
        "sources": source_records,
        "chunks": [],
    }
    progress = {
        "schema_version": 2,
        "run_id": run_id,
        "phase": "normalize",
        "chunks": {},
        "analysis_policy": {
            "deterministic_statistics_only": True,
            "semantic_analysis_method": "llm_semantic",
            "period_merge_method": "llm_semantic_merge",
        },
        "updated_at": created_at,
    }

    write_json(workspace / "scope.json", scope)
    write_json(workspace / "manifest.json", manifest)
    write_json(workspace / "progress.json", progress)
    print(
        json.dumps(
            {
                "status": "initialized",
                "run_id": run_id,
                "workspace": str(workspace),
                "sources": len(source_records),
                "skill_name": args.skill_name,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
