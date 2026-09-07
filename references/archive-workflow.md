# 深度档案工作流

本流程适用于单个聊天文件、多个明确批准的文件，或已有的预分块档案。最终目标是逐块语义蒸馏，而不是快速生成格式正确但内容空泛的摘要。

## 断点目录结构

```text
analysis-work/
├── scope.json
├── manifest.json
├── progress.json
├── normalized/
├── chunks/
├── chunk-stats/
├── chunk-summaries/
├── period-summaries/
├── final/
│   └── audit/
├── tests/
└── draft-skill/
```

原始材料必须保留在已批准的源路径，不得复制进生成的 Skill。`normalized/` 和 `chunks/` 只保留分析必需的最少结构化字段。

## 源文件清单与标准化

确认后，为每个批准的数据源计算 SHA-256，并记录准确路径、大小、类型和哈希。绝不枚举或计算被拒绝同级文件的哈希。

把每条消息标准化为一行一个 JSON 对象：

```json
{"evidence_id":"run-id-m000001","timestamp":"ISO-8601-or-null","sender_id":"stable-source-sender","sender_role":"target|user|third_party|unknown","text":"message text","source_id":"source-001"}
```

保留原始顺序、时间戳、消息边界和可见平台 token。不得展开媒体占位符或推断缺失内容。使用当前运行专属证据前缀；归属不确定时保留为 `unknown`，且不能支持目标人物的风格结论。

## 分块

- 保留完整消息；实际可行时保留相邻“用户 → 目标人物回复 burst”。
- 使用由运行、时间分组和序号派生的稳定 chunk_id。
- 每个分块必须能安全放入一个独立模型上下文。不能因为源数据只有一个文件就创建巨型分块。
- 在 `manifest.json` 中记录路径、SHA-256、source_id、消息／证据数量、时间段和分组键。
- 不得在 commentary 或最终回复中输出聊天正文。

## 两条分析轨道

### A. 确定性统计

程序可以批量计算并写入 `chunk-stats/<chunk-id>.json`：

- 消息数量、角色数量、时间范围；
- 字符长度、burst 大小、标点、问号与换行；
- 已识别 token 的计数与组合；
- 可用相邻 turn 数；
- 文件哈希和 evidence_id 成员。

程序不得生成身份事实、关系判断、事件含义、Persona、情绪解释、反应模式、示例语义或自然语言结论。

### B. 模型深度语义分析

每个 `chunk-summaries/<chunk-id>.json` 必须来自一次只读取该分块的模型语义分析：

1. 读取一个被分配分块及对应统计；
2. 区分目标人物、用户、第三方和关系层面证据；
3. 提取事件、关系里程碑、精确日期、行为、反例、矛盾和示例候选；
4. 写入单独摘要；
5. 校验 JSON、chunk_id、源哈希、evidence_id、角色和语义字段；
6. 立即更新该 chunk 的 progress。

禁止：

- 用关键词命中或固定模板填充语义字段；
- 用程序为所有分块批量生成自然语言 claim；
- 将全部分块装入一个模型上下文；
- 在分析完全部分块后一次性批量写入摘要；
- 只因为 JSON、哈希和 evidence_id 正确就把语义摘要标为完成。

`progress.json` 中的完成条目必须包含 `analysis_method: "llm_semantic"`、`semantic_validated: true` 和独立的 `validated_at`。

## 并发

完成 intake 范围确认后，深度语义分析默认使用以下 worker 配置：

- 目标为三个分析 subagent；
- 每个 subagent 固定使用 `gpt-5.6-luna`；
- 每个 subagent 固定使用 `max` reasoning effort；
- 若宿主并发上限包含主 Agent，只启动当前可用的最大数量，并在槽位释放后继续补充 worker；
- 用户明确要求更低并发或顺序执行时，以用户要求为准。

并发执行时：

- 同时最多三个且不超过宿主可用上限；
- 分配互不重叠的 chunk_id；
- 每个 Agent 只能读取获分配的分块、统计、schema 和输出路径；
- 每个分块完成后立即写入；
- 主 Agent 逐个验证后更新 progress。

如果 subagent 不可用，本批次只尝试一次，然后切换为顺序小批次。顺序执行仍然必须逐块进行真实模型分析，并在运行记录中注明未能采用默认 worker 配置。

## 续跑与旧版本

每批开始前验证 manifest、progress 和已有摘要。只有同时满足以下条件的摘要才可复用：

- schema v2；
- 源哈希与 evidence_id 成员有效；
- `analysis_provenance.mode` 为 `llm_semantic`；
- progress 标记 `semantic_validated: true`；
- 没有异常模板重复或语义校验失败。

旧 v1 工作区可以复用源清单、标准化消息、分块和确定性统计，但旧语义摘要必须标记为 `stale_semantic` 并重新分析。不得因为旧摘要结构有效而跳过深度分析。

## 时间段语义合并

全部分块完成后，按月份或稳定时间段合并。每个时间段必须由模型在独立上下文中读取该时间段的已验证摘要，并输出：

- 精确时间线和关系里程碑；
- 重复身份／关系、风格和行为；
- 变化、反例、矛盾和未知；
- 示例候选排名；
- 源分块与 evidence_id 映射。

程序只负责分组和校验，不能通过拼接或模板直接生成月度自然语言摘要。保留事件日期、日期精度、历史／当前状态和证据成员。

## 最终综合与证据传播

第一次全局综合只读取时间段摘要，并分别完成：

1. 身份、关系与时间线；
2. Persona 与行为；
3. 沟通风格与 token；
4. 真实示例选择；
5. Anti-AI 校准。

之后为重要结论和入选示例定点回查小型原始窗口。每个高置信关系里程碑必须从分块传播到时间段摘要，再进入最终身份记忆，或在 `final/audit/evidence-map.json` 中记录明确排除理由。

安装包不复制 evidence_id 映射。`final/audit/` 保留 claim 与 evidence_id、源哈希、时间戳、传播状态和示例选择记录，供后续审计与纠正。
