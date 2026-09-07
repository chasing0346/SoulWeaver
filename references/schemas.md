# SoulWeaver v2 产物 Schema

统一使用 UTF-8 JSON。未知值使用 `null` 或明确不确定性，不能编造。v2 将确定性统计、模型语义结论、运行时内容与审计证据分开。

## `manifest.json`

```json
{
  "schema_version": 2,
  "run_id": "unique-run-id",
  "sources": [
    {
      "source_id": "source-001",
      "path": "absolute-approved-path",
      "sha256": "hex",
      "size_bytes": 0,
      "format": "txt|json|jsonl|csv|html|other"
    }
  ],
  "chunks": [
    {
      "chunk_id": "run-period-001",
      "path": "chunks/run-period-001.jsonl",
      "stats_path": "chunk-stats/run-period-001.json",
      "sha256": "hex",
      "source_ids": ["source-001"],
      "period": {"start": null, "end": null},
      "group_key": "period-001",
      "message_count": 0,
      "evidence_count": 0,
      "eligible_turn_count": 0
    }
  ]
}
```

## `progress.json`

```json
{
  "schema_version": 2,
  "run_id": "unique-run-id",
  "phase": "intake|normalize|chunks|periods|synthesis|draft|confirmed|packaged|installed",
  "chunks": {
    "run-period-001": {
      "status": "pending|in_progress|complete|failed|stale|stale_semantic",
      "summary_path": "chunk-summaries/run-period-001.json",
      "analysis_method": "llm_semantic",
      "semantic_validated": false,
      "validated_at": null,
      "error": null
    }
  },
  "updated_at": "ISO-8601"
}
```

## 通用语义观察

```json
{
  "claim_id": "run-id-c000001",
  "claim": "简洁、具体、可观察的释义",
  "occurred_at": "YYYY-MM-DD|YYYY-MM|null",
  "date_precision": "day|month|year|period|unknown",
  "evidence_ids": ["run-id-m000001"],
  "confidence": "high|medium|low",
  "scope": "stable|phase_specific|single_event|unknown",
  "speaker_role": "target|user|relationship|unknown",
  "counter_evidence_ids": [],
  "notes": null
}
```

不得把当前不确定性覆盖到历史事实：历史事件证据明确时保留其日期，再单独描述当前状态未知。

## 关系里程碑

```json
{
  "claim_id": "run-id-c000002",
  "milestone_type": "acquaintance|relationship_confirmed|meeting|separation|reconciliation|shared_event|boundary_change|other",
  "claim": "双方确认关系",
  "event_date": "YYYY-MM-DD|YYYY-MM|null",
  "date_precision": "day|month|year|period|unknown",
  "historical_status": "confirmed|discussed|planned|inferred|unknown",
  "evidence_ids": ["run-id-m000010", "run-id-m000011"],
  "confidence": "high|medium|low",
  "counter_evidence_ids": [],
  "notes": null
}
```

## 分块统计

`chunk-stats/<chunk-id>.json` 只能包含确定性结果：

```json
{
  "schema_version": 2,
  "chunk_id": "run-period-001",
  "source_sha256": "hex",
  "message_count": 0,
  "target_message_count": 0,
  "user_message_count": 0,
  "eligible_turn_count": 0,
  "length_statistics": {},
  "burst_statistics": {},
  "punctuation_statistics": {},
  "token_statistics": {}
}
```

## 分块语义摘要

```json
{
  "schema_version": 2,
  "chunk_id": "run-period-001",
  "source_sha256": "manifest 中记录的分块哈希",
  "period": {"start": null, "end": null},
  "analysis_provenance": {
    "mode": "llm_semantic",
    "analyzer_version": "soulweaver-v2",
    "analyzed_at": "ISO-8601",
    "assigned_chunk_ids": ["run-period-001"]
  },
  "identity_facts": [],
  "relationship_facts": [],
  "relationship_milestones": [],
  "events_and_routines": [],
  "preferences": [],
  "language_style": [],
  "message_rhythm": [],
  "vocabulary_and_nicknames": [],
  "punctuation_and_tokens": [],
  "opening_patterns": [],
  "reaction_patterns": [],
  "boundaries_and_repairs": [],
  "example_candidates": [
    {
      "candidate_id": "run-id-x000001",
      "scenario": "简短场景标签",
      "context_evidence_ids": ["run-id-m000001", "run-id-m000002"],
      "user_evidence_ids": ["run-id-m000001"],
      "target_evidence_ids": ["run-id-m000002"],
      "reaction_shape": "简洁反应分析",
      "privacy_level": "low|medium|high",
      "confidence": "high|medium|low"
    }
  ],
  "uncertainties_and_contradictions": []
}
```

关于目标人物沟通方式的结论必须引用 `sender_role: target` 的证据。关系层面结论可以引用双方消息，但必须标记为 `relationship`。`assigned_chunk_ids` 必须只包含当前 chunk。

## 时间段摘要

```json
{
  "schema_version": 2,
  "group_key": "period-001",
  "source_chunks": ["run-period-001"],
  "analysis_provenance": {
    "mode": "llm_semantic_merge",
    "analyzer_version": "soulweaver-v2",
    "analyzed_at": "ISO-8601"
  },
  "timeline": [],
  "relationship_milestones": [],
  "recurring_identity_and_relationship": [],
  "recurring_style": [],
  "recurring_reactions": [],
  "token_statistics": [],
  "example_candidates": [],
  "changes_from_prior_period": [],
  "uncertainties_and_contradictions": []
}
```

`timeline` 和 `relationship_milestones` 必须保留源事件的日期、日期精度、历史状态、evidence_id 和 source chunk。

## 真实短例动态配额

令 `E` 为经过发送者、顺序、隐私和相邻性验证的“用户 → 目标人物回复 burst”数量：

```text
Q = 0                                      当 E = 0
Q = min(E, min(24, max(3, round(sqrt(E/100)))))  当 E > 0
```

约 1,000 个有效 turn 对应 3 条，约 10,000 个对应 10 条，最终上限 24 条。每条通常包含 2–6 条相邻消息，总可见字符默认不超过 240；确需更长必须单独说明并重新取得批准。

`final/audit/example-selection.json`：

```json
{
  "schema_version": 2,
  "eligible_turns": 10000,
  "quota": 10,
  "verbatim_examples_authorized": true,
  "selected_examples": [
    {
      "example_id": "example-001",
      "scenario": "场景",
      "period": "YYYY-MM",
      "messages": [
        {"role": "user", "text": "经批准的短原句"},
        {"role": "target", "text": "经批准的短原句"}
      ],
      "source_evidence_ids": ["run-id-m000001", "run-id-m000002"],
      "visible_characters": 0,
      "privacy_level": "low",
      "approved": true
    }
  ]
}
```

源 evidence_id 只存在于工作区审计 JSON，不进入安装包。

`final/audit/evidence-map.json`：

```json
{
  "schema_version": 2,
  "claims": [
    {
      "claim_id": "run-id-c000002",
      "runtime_file": "identity-memory.md",
      "runtime_text": "双方在 YYYY-MM-DD 确认关系",
      "event_date": "YYYY-MM-DD",
      "evidence_ids": ["run-id-m000010", "run-id-m000011"],
      "source_sha256": ["hex"],
      "runtime_included": true,
      "exclusion_reason": null
    }
  ]
}
```

每个高置信历史里程碑必须出现在该映射中。`runtime_included: true` 时，其日期和自然语言事实必须进入对应运行时文件；未进入时必须提供具体隐私或相关性排除理由。

## 最终工作区产物

`final/` 必须包含：

```text
profile.json
runtime-manifest.json
identity-memory.md
communication-style.md
behavior-patterns.md
opening-patterns.md
anti-ai-rules.md
verified-examples.md
validation-report.json
audit/evidence-map.json
audit/example-selection.json
```

运行时 Markdown 不得包含裸 evidence_id、源路径、哈希或没有原句的证据编号。`verified-examples.md` 只包含已批准的真实短语境及场景说明。

`runtime-manifest.json`：

```json
{
  "schema_version": 2,
  "semantic_validation_passed": true,
  "date_propagation_passed": true,
  "actual_forward_test_passed": true,
  "eligible_turns": 10000,
  "example_quota": 10,
  "selected_verbatim_examples": 10,
  "verbatim_examples_authorized": true,
  "opaque_evidence_ids_in_runtime": 0
}
```

`profile.json` 使用 `schema_version: 2`。只有用户批准完整草稿和真实短例候选后，才能把 `confirmed` 设置为 `true`。
