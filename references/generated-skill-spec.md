# 生成人物 Skill v2 规范

封装一个自包含的运行时 Skill。它不得依赖 SoulWeaver、源档案、分析断点或其他人物 Skill，但证据审计映射保留在原分析工作区。

## 必需安装结构

```text
<confirmed-slug>/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── identity-memory.md
    ├── communication-style.md
    ├── behavior-patterns.md
    ├── opening-patterns.md
    ├── anti-ai-rules.md
    └── verified-examples.md
```

不得包含原始分块、标准化消息、私密源路径、哈希、progress、分析提示词、审计 evidence_id 映射或未经批准原文。

## 运行时内容与审计内容分层

安装包 Markdown 只保留模型能够直接利用的内容：

- 精确但经过隐私筛选的历史事实和时间线；
- 可观察的沟通与行为规则；
- 统计范围和必要置信度说明；
- 用户批准的真实短语境；
- Anti-AI、token 和边界规则。

裸 evidence_id 对运行时没有语义价值，因此禁止进入安装包。以下内容只保存在分析工作区：

```text
final/audit/evidence-map.json
final/audit/example-selection.json
```

`evidence-map.json` 维护 claim、日期、evidence_id、源哈希、传播路径和排除理由。`example-selection.json` 维护真实短例与源证据映射。用户请求证据审计时，应回到获授权的分析工作区，而不是让安装后的 Skill 编造或展示编号。

## 生成的 `SKILL.md`

入口文件必须：

- 明确输出是经授权的合成模拟；
- 区分角色回复与记忆／配置查询；
- 把预测下一条消息定义为运行时目标；
- 使用已确认披露前缀；
- 优先处理拒绝、隐私、暂停和现实容量；
- 身份／历史问题路由到 `identity-memory.md`；
- 普通生成路由到风格、行为、开场、Anti-AI 和选定真实示例；
- 选择回复前解码平台 token；
- 避免声称知道真实人物当前意图；
- 不显示或编造 evidence_id；
- 声明用户当前纠正优先于保存历史。

## 真实示例

`verified-examples.md` 必须包含动态配额内、经过用户批准和隐私审查的真实相邻短语境。每条包括：

- 示例编号和场景；
- 2–6 条按原顺序排列的用户／目标消息；
- 简短的反应特点；
- 可选的阶段说明。

不得包含 evidence_id、源路径、时间戳精确到可识别个人的程度，或与场景无关的上下文。普通模拟最多读取最接近的 1–3 条示例。

## 历史事实

`identity-memory.md` 必须保留证据明确的历史日期、关系里程碑与日期精度。现实当前状态未知时单独说明，不能删除历史事实。高置信里程碑若不进入运行时文件，必须在工作区审计映射中记录隐私或相关性排除理由。

## 封装门槛

`build_person_skill.py` 必须读取 `runtime-manifest.json` 并确认：

- 深度语义验证通过；
- 日期传播验证通过；
- 实际运行前向测试通过；
- 真实短例数量等于动态配额；
- 用户批准短原文进入最终 Skill；
- 运行时 Markdown 中裸 evidence_id 数量为 0。

未满足任一条件时停止封装，不得降级成“只有释义和编号”的 Skill。

## 安装

先在已确认草稿目录构建并验证。展示准确安装目标并等待批准。安装后比较全部哈希，确认没有修改无关 Skill。
