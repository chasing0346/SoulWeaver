# v2 验证与隔离

验证必须覆盖结构、证据、语义深度、日期传播、真实示例、运行时行为、隐私和跨人物污染。

## 单分块验证

每个已完成语义摘要都要验证：

- UTF-8 JSON 与 schema v2；
- 准确 chunk_id 和源 SHA-256；
- 每个 evidence_id 属于该分块；
- `analysis_provenance.mode = llm_semantic`；
- `assigned_chunk_ids` 只包含当前分块；
- progress 包含 `analysis_method: llm_semantic`、`semantic_validated: true` 和独立校验时间；
- 目标风格只引用目标发送者；
- 示例 turn 的发送者、顺序和相邻关系正确；
- 事件和关系里程碑包含日期精度与历史状态；
- 不包含无证据诊断或当前意图断言。

只有上述验证成功才能标记 complete。JSON、哈希和 evidence_id 有效不等于语义有效。

## 反批量模板检查

对整个档案执行：

- 统计规范化后的完全重复 claim；
- 当同一自然语言 claim 出现在超过 `max(5, 10% × 分块数)` 的分块中时阻止综合，除非它是明确列入白名单的结构性声明；
- 重复实例占全部 claim 超过 35% 时发出高风险警告并人工抽查；
- 大型档案全部 `uncertainties_and_contradictions` 为空时发出高风险警告；
- 检查摘要是否被同一批脚本时间戳集中写入；时间本身不直接判错，但与高重复、无日期和无矛盾同时出现时阻止综合。

不得用摘要文件体积或字段数量代替语义深度。

## 日期与里程碑传播

- 分块中的高置信关系里程碑必须进入对应时间段摘要；
- 时间段中的高置信历史事件必须进入 `identity-memory.md`，或在 `final/audit/evidence-map.json` 记录排除理由；
- “现实当前状态未知”不能覆盖历史已确认事件；
- 日期精度只能保持或降低，不能无证据提高；
- 讨论、计划和已完成必须分别保留；
- 至少实际测试认识日期、关系起点、关键阶段变化和一个证据不足问题。

## 真实短例验证

令 `E` 为有效相邻 turn 数，按 `Q = min(E, min(24, max(3, round(sqrt(E/100)))))` 计算配额。验证：

- 入选数量等于 Q；
- 用户明确批准原文进入最终 Skill；
- 每条是同一真实相邻窗口，通常 2–6 条消息；
- 默认不超过 240 个可见字符；
- 发送者顺序、时间顺序和 source hash 有效；
- 场景、时间和反应模式具有多样性；
- 无高敏第三方、账号、金额、链接、健康、工作机密或无关内容；
- `verified-examples.md` 中没有 evidence_id；
- 完整映射只存在 `final/audit/example-selection.json`。

## 运行时 Markdown 验证

安装包所有 Markdown 和 YAML 必须：

- 不包含 `evidence_id` 标签、`msg-数字`、运行 evidence 前缀、源路径或哈希；
- 身份文件保留精确历史事实和必要日期；
- 真实原句只出现在 `verified-examples.md`；
- 不包含原始长档案、分析提示或 progress；
- 不把真实例句当作当前事件；
- 不包含其他人物标识。

## 跨人物隔离

每次运行只能从通用 SoulWeaver 指令和当前授权数据源开始。不得打开已安装人物 Skill 或其他运行工作区作为模板。

为当前运行创建禁用标识列表，包含已知先前／示例人物名称、slug、源目录、run_id、证据前缀和独特事实。扫描最终工作区与安装包；任何命中都会阻止封装。

## 实际前向测试

不得预先手写 `after` 并直接标记 `pass`。必须先构建隔离草稿，再使用该草稿的真实运行时路由生成输出；测试记录至少包括：

- 测试输入；
- 实际生成输出；
- 生成时间和所用草稿哈希；
- 读取的运行时参考文件；
- 独立判定的通过／失败理由。

每条记录使用稳定的 `scenario_key`，并包含 `input`、`actual_output`、`draft_hash`、`references_read`、`evaluation_mode: independent_review` 和 `result`。缺少实际输出或独立判定的记录不能计入通过数量。

至少测试：

1. 普通问候；
2. 状态更新；
3. 疲劳或工作压力；
4. 无 emoji 的亲密表达；
5. 明确 token 输入；
6. 轻度调侃；
7. 明确拒绝；
8. 道歉与修复；
9. 隐私或自主权；
10. 冲突或受伤；
11. 含糊 token 或媒体；
12. 认识或关系起点日期；
13. 关键阶段变化；
14. 证据不足的记忆问题；
15. 配置查询。

前向测试报告必须标记 `execution_mode: actual_skill_runtime`。静态候选、模板答案和只做正则检查的结果不能通过封装门槛。

## 封装检查

运行 `scripts/validate_run.py`、`scripts/build_person_skill.py` 和 `scripts/validate_person_skill.py`，并人工检查：

- schema v2 深度语义摘要全部完成；
- 日期和高置信里程碑传播完整；
- 动态真实示例配额与授权匹配；
- `runtime-manifest.json` 全部门槛为 true；
- 运行时包没有裸 evidence_id；
- Skill 名称、frontmatter、链接和 UI prompt 有效；
- 不存在 scaffold TODO、禁用标识、源路径或意外文件；
- 安装后草稿与安装目录哈希一致。
