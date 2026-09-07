#!/usr/bin/env python3
"""从已确认的 SoulWeaver 最终产物构建一个自包含人物 Skill。"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from example_quota import calculate_quota


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
OPAQUE_EVIDENCE_RE = re.compile(
    r"\b(?:msg-\d{3,}|sw-[a-z0-9-]+-m\d+)\b|\bevidence_ids?\b",
    re.IGNORECASE,
)
REFERENCE_FILES = (
    "identity-memory.md",
    "communication-style.md",
    "behavior-patterns.md",
    "opening-patterns.md",
    "anti-ai-rules.md",
    "verified-examples.md",
)
REQUIRED_CONTROL_FILES = ("validation-report.json", "runtime-manifest.json")


def json_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-dir", required=True)
    parser.add_argument("--output-parent", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    final_dir = Path(args.final_dir).expanduser().resolve()
    output_parent = Path(args.output_parent).expanduser().resolve()
    profile_path = final_dir / "profile.json"
    if not profile_path.is_file():
        raise SystemExit(f"缺少 profile.json：{profile_path}")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if profile.get("schema_version") != 2:
        raise SystemExit("不支持的 profile schema_version")
    if profile.get("confirmed") is not True or not profile.get("confirmed_at"):
        raise SystemExit("拒绝封装尚未确认的画像")

    display_name = profile.get("display_name")
    skill_name = profile.get("skill_name")
    description = profile.get("description")
    prefix = profile.get("disclosure_prefix", "（合成模拟回应）")
    for label, value in (
        ("display_name", display_name),
        ("skill_name", skill_name),
        ("description", description),
        ("disclosure_prefix", prefix),
    ):
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f"{label} 无效")
    if not SLUG_RE.fullmatch(skill_name) or len(skill_name) > 64:
        raise SystemExit("skill_name 无效")
    if len(description) > 1024 or "<" in description or ">" in description:
        raise SystemExit("description 无效")

    for name in REFERENCE_FILES:
        if not (final_dir / name).is_file():
            raise SystemExit(f"缺少最终产物：{name}")
    for name in REQUIRED_CONTROL_FILES:
        if not (final_dir / name).is_file():
            raise SystemExit(f"缺少最终控制产物：{name}")

    validation_report = json.loads(
        (final_dir / "validation-report.json").read_text(encoding="utf-8")
    )
    if validation_report.get("schema_version") != 2:
        raise SystemExit("不支持的 validation-report schema_version")
    if validation_report.get("status") not in {"valid", "passed"}:
        raise SystemExit("最终验证报告未通过")

    runtime_manifest = json.loads(
        (final_dir / "runtime-manifest.json").read_text(encoding="utf-8")
    )
    if runtime_manifest.get("schema_version") != 2:
        raise SystemExit("不支持的 runtime-manifest schema_version")
    for gate in (
        "semantic_validation_passed",
        "date_propagation_passed",
        "actual_forward_test_passed",
    ):
        if runtime_manifest.get(gate) is not True:
            raise SystemExit(f"运行时门槛未通过：{gate}")

    eligible_turns = runtime_manifest.get("eligible_turns")
    selected_examples = runtime_manifest.get("selected_verbatim_examples")
    if not isinstance(eligible_turns, int) or eligible_turns < 0:
        raise SystemExit("runtime-manifest.eligible_turns 无效")
    expected_quota = calculate_quota(eligible_turns)
    if runtime_manifest.get("example_quota") != expected_quota:
        raise SystemExit(
            f"真实短例配额不匹配：预期 {expected_quota}，"
            f"实际 {runtime_manifest.get('example_quota')!r}"
        )
    if selected_examples != expected_quota:
        raise SystemExit(
            f"真实短例数量不匹配：预期 {expected_quota}，实际 {selected_examples!r}"
        )
    if expected_quota and runtime_manifest.get("verbatim_examples_authorized") is not True:
        raise SystemExit("真实短例尚未获得用户封装授权")
    if runtime_manifest.get("opaque_evidence_ids_in_runtime") != 0:
        raise SystemExit("运行时文件仍包含裸 evidence_id")

    audit_dir = final_dir / "audit"
    evidence_map_path = audit_dir / "evidence-map.json"
    example_selection_path = audit_dir / "example-selection.json"
    if not evidence_map_path.is_file():
        raise SystemExit("缺少 final/audit/evidence-map.json")
    if not example_selection_path.is_file():
        raise SystemExit("缺少 final/audit/example-selection.json")
    example_selection = json.loads(example_selection_path.read_text(encoding="utf-8"))
    if example_selection.get("schema_version") != 2:
        raise SystemExit("不支持的 example-selection schema_version")
    selected = example_selection.get("selected_examples")
    if not isinstance(selected, list) or len(selected) != expected_quota:
        raise SystemExit("example-selection 中的真实短例数量与动态配额不一致")
    verified_examples_text = (final_dir / "verified-examples.md").read_text(
        encoding="utf-8"
    )
    for index, example in enumerate(selected):
        if not isinstance(example, dict) or example.get("approved") is not True:
            raise SystemExit(f"真实短例 {index + 1} 未获得批准")
        messages = example.get("messages")
        if not isinstance(messages, list) or not 2 <= len(messages) <= 6:
            raise SystemExit(f"真实短例 {index + 1} 必须包含 2–6 条相邻消息")
        visible_characters = sum(
            len(message.get("text", ""))
            for message in messages
            if isinstance(message, dict)
        )
        if visible_characters > 240:
            raise SystemExit(f"真实短例 {index + 1} 超过 240 个可见字符")
        for message in messages:
            text = message.get("text") if isinstance(message, dict) else None
            if not isinstance(text, str) or not text:
                raise SystemExit(f"真实短例 {index + 1} 包含空消息")
            if text not in verified_examples_text:
                raise SystemExit(
                    f"真实短例 {index + 1} 的已批准原句未进入 verified-examples.md"
                )

    for name in REFERENCE_FILES:
        text = (final_dir / name).read_text(encoding="utf-8")
        if OPAQUE_EVIDENCE_RE.search(text):
            raise SystemExit(f"{name} 中发现裸 evidence_id")

    output_parent.mkdir(parents=True, exist_ok=True)
    destination = output_parent / skill_name
    if destination.exists():
        raise SystemExit(f"拒绝覆盖已有输出：{destination}")

    skill_text = f'''---
name: {skill_name}
description: {json_string(description)}
---

# {display_name}

这是基于经蒸馏和证据审计的授权材料构建的合成人物模拟。它不是真实本人，也不能揭示对方当前未表达的想法、意图、承诺或行动。

## 运行时目标

进行角色互动时，预测 {display_name} 最可能发送的下一条消息或短消息段，不要以通用助手方式回答。每条模拟角色回复都以 `{prefix}` 开头。如果用户询问记忆、配置、证据或置信度，使用说明方式回答，不进行角色扮演。

## 决策顺序

1. 优先尊重明确拒绝、隐私、自主权、暂停请求和现实容量。
2. 同时解码文字与平台 emoji／表情包 token。
3. 选择一个主反应模式，最多增加一个次模式。
4. 应用目标人物特定的长度、节奏、词汇、称呼、标点和 token 规则。
5. 只选择最接近的 1–3 个已批准真实短语境学习措辞、节奏和停止点。
6. 淘汰助手式候选，在一个自然消息 burst 完成后停止。
7. 添加披露前缀，只输出最终结果。

## 目标人物专属参考文件

- 普通生成读取 [references/communication-style.md](references/communication-style.md) 和 [references/anti-ai-rules.md](references/anti-ai-rules.md)。
- 问候、重新进入对话和开场读取 [references/opening-patterns.md](references/opening-patterns.md)。
- 亲密、关心、安慰、生气、冲突、道歉、边界和压力场景读取 [references/behavior-patterns.md](references/behavior-patterns.md)。
- 只有相近场景示例能改善回复时，才读取 [references/verified-examples.md](references/verified-examples.md)。
- 身份、关系、历史、日常、偏好和记忆问题读取 [references/identity-memory.md](references/identity-memory.md)。

安装包不包含源证据编号。用户询问证据审计时，只能说明当前文件中的置信度和局限；需要核对源证据时，应回到仍获授权的 SoulWeaver 分析工作区，不能编造编号。

## Token 与行为门槛

类似微信的文本中，短格式 `[名称]` 通常表示 emoji 或表情包 token；已知媒体和系统占位符需要单独处理。结合上下文解释 token，并遵循当前目标人物测得的触发规则与条件数量。不得把高频称呼、emoji、道歉、问题或长消息模式变成强制后缀。

## 边界

- 不得诊断人物，也不得从历史行为推断当前意图。
- 不得复述无关聊天历史、私密源路径或第三方细节。
- 不得把历史示例当作当前事件。
- 保留历史事实、日期、不确定性和矛盾；当前状态未知不能抹去已确认历史。
- 用户当前纠正优先于已保存历史；在配置模式中说明纠正，不能静默改写记录。
'''

    short_description = f"基于授权证据模拟{display_name}的关系记忆、语言风格与反应模式"
    if not 25 <= len(short_description) <= 64:
        short_description = "基于授权聊天证据生成下一条消息、关系记忆与行为模式的合成人物模拟"
    openai_yaml = f'''interface:
  display_name: {json_string(display_name)}
  short_description: {json_string(short_description)}
  default_prompt: {json_string(f"使用 ${skill_name}，根据已确认的人物模型生成一条简洁的合成下一消息回复。")}
policy:
  allow_implicit_invocation: true
'''

    temporary_root = Path(tempfile.mkdtemp(prefix="soulweaver-build-", dir=str(output_parent)))
    temporary_skill = temporary_root / skill_name
    try:
        (temporary_skill / "agents").mkdir(parents=True)
        (temporary_skill / "references").mkdir()
        (temporary_skill / "SKILL.md").write_text(skill_text, encoding="utf-8")
        (temporary_skill / "agents" / "openai.yaml").write_text(openai_yaml, encoding="utf-8")
        for name in REFERENCE_FILES:
            shutil.copy2(final_dir / name, temporary_skill / "references" / name)
        os.replace(temporary_skill, destination)
    finally:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)

    print(json.dumps({"status": "built", "skill_dir": str(destination)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
