#!/usr/bin/env python3
"""验证生成的人物 Skill，并扫描跨人物污染。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from example_quota import calculate_quota


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
OPAQUE_EVIDENCE_RE = re.compile(
    r"\b(?:msg-\d{3,}|sw-[a-z0-9-]+-m\d+)\b|\bevidence_ids?\b",
    re.IGNORECASE,
)
REQUIRED_REFERENCES = {
    "identity-memory.md",
    "communication-style.md",
    "behavior-patterns.md",
    "opening-patterns.md",
    "anti-ai-rules.md",
    "verified-examples.md",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", required=True)
    parser.add_argument("--expected-name", required=True)
    parser.add_argument("--run-workspace")
    parser.add_argument("--forbid", action="append", default=[])
    return parser.parse_args()


def load_text_files(root: Path) -> dict[Path, str]:
    result = {}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".yaml", ".yml", ".json", ".txt"}:
            result[path] = path.read_text(encoding="utf-8")
    return result


def main() -> int:
    args = parse_args()
    root = Path(args.skill_dir).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    if not root.is_dir():
        errors.append(f"Skill 目录不存在：{root}")
    skill_path = root / "SKILL.md"
    yaml_path = root / "agents" / "openai.yaml"
    if not skill_path.is_file():
        errors.append("缺少 SKILL.md")
    if not yaml_path.is_file():
        errors.append("缺少 agents/openai.yaml")
    if errors:
        print(json.dumps({"status": "failed", "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    skill_text = skill_path.read_text(encoding="utf-8")
    match = re.match(r"^---\r?\n(.*?)\r?\n---", skill_text, re.DOTALL)
    if not match:
        errors.append("SKILL.md frontmatter 无效")
        frontmatter = ""
    else:
        frontmatter = match.group(1)
    name_match = re.search(r"(?m)^name:\s*([^\r\n]+)$", frontmatter)
    description_match = re.search(r'(?m)^description:\s*"(.*)"$', frontmatter)
    actual_name = name_match.group(1).strip() if name_match else None
    if actual_name != args.expected_name:
        errors.append(f"Skill 名称不匹配：预期 {args.expected_name!r}，实际 {actual_name!r}")
    if not NAME_RE.fullmatch(args.expected_name) or len(args.expected_name) > 64:
        errors.append("预期的 Skill 名称无效")
    if not description_match:
        errors.append("缺少带引号的 description")
    elif len(description_match.group(1)) > 1024 or any(
        char in description_match.group(1) for char in "<>"
    ):
        errors.append("description 无效")

    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", skill_text)
    for relative in links:
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            errors.append(f"引用路径超出 Skill 目录：{relative}")
            continue
        if not target.is_file():
            errors.append(f"缺少链接的参考文件：{relative}")

    reference_dir = root / "references"
    present_references = {path.name for path in reference_dir.glob("*.md")}
    missing_references = sorted(REQUIRED_REFERENCES - present_references)
    if missing_references:
        errors.append(f"缺少必需参考文件：{missing_references}")
    if "evidence-index.md" in present_references:
        errors.append("安装包不得包含 evidence-index.md；证据映射必须留在分析工作区")

    yaml_text = yaml_path.read_text(encoding="utf-8")
    if f"${args.expected_name}" not in yaml_text:
        errors.append("agents/openai.yaml 的 default_prompt 未提及预期 Skill")
    short_match = re.search(r'(?m)^\s*short_description:\s*"(.*)"$', yaml_text)
    if not short_match or not 25 <= len(short_match.group(1)) <= 64:
        errors.append("short_description 必须包含 25–64 个字符")

    text_files = load_text_files(root)
    combined = "\n".join(text_files.values())
    if re.search(r"(?m)^\s*\[TODO:[^\]]*\]\s*$", combined):
        errors.append("发现未完成的 TODO 占位符")
    evidence_hits = OPAQUE_EVIDENCE_RE.findall(combined)
    if evidence_hits:
        errors.append(f"运行时文件中发现裸 evidence_id：{len(evidence_hits)} 处")

    forbidden = list(args.forbid)
    if args.run_workspace:
        workspace = Path(args.run_workspace).expanduser().resolve()
        scope_path = workspace / "scope.json"
        manifest_path = workspace / "manifest.json"
        if scope_path.is_file():
            scope = json.loads(scope_path.read_text(encoding="utf-8"))
            forbidden.extend(scope.get("forbidden_identifiers", []))
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for source in manifest.get("sources", []):
                source_path = source.get("path", "")
                forbidden.append(source_path)
                if source_path:
                    forbidden.append(Path(source_path).name)
            forbidden.append(str(workspace))

        runtime_manifest_path = workspace / "final" / "runtime-manifest.json"
        if not runtime_manifest_path.is_file():
            errors.append("工作区缺少 final/runtime-manifest.json")
        else:
            runtime_manifest = json.loads(
                runtime_manifest_path.read_text(encoding="utf-8")
            )
            if runtime_manifest.get("schema_version") != 2:
                errors.append("runtime-manifest schema_version 必须为 2")
            for gate in (
                "semantic_validation_passed",
                "date_propagation_passed",
                "actual_forward_test_passed",
            ):
                if runtime_manifest.get(gate) is not True:
                    errors.append(f"运行时门槛未通过：{gate}")
            eligible_turns = runtime_manifest.get("eligible_turns")
            if isinstance(eligible_turns, int) and eligible_turns >= 0:
                quota = calculate_quota(eligible_turns)
                if runtime_manifest.get("example_quota") != quota:
                    errors.append("runtime-manifest 的真实短例动态配额不正确")
                if runtime_manifest.get("selected_verbatim_examples") != quota:
                    errors.append("已选择真实短例数量与动态配额不一致")
                if quota and runtime_manifest.get("verbatim_examples_authorized") is not True:
                    errors.append("真实短例尚未获得用户封装授权")
            else:
                errors.append("runtime-manifest.eligible_turns 无效")

    for term in dict.fromkeys(item for item in forbidden if isinstance(item, str) and item):
        if term.casefold() in combined.casefold():
            errors.append(f"发现禁用标识：{term!r}")

    allowed_suffixes = {".md", ".yaml", ".yml"}
    unexpected = [
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() not in allowed_suffixes
    ]
    if unexpected:
        errors.append(f"封装中出现非预期文件类型：{unexpected}")

    result = {
        "status": "failed" if errors else "valid",
        "skill_name": args.expected_name,
        "files_scanned": len(text_files),
        "references": len(present_references),
        "forbidden_terms_checked": len(set(forbidden)),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
