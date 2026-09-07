# SoulWeaver

> 把一段被授权的聊天档案，蒸馏成一个能够被调用、被审计、被纠正的合成人物 Skill。

SoulWeaver 是一个专为 Codex 设计的 Skill，用于从用户明确授权的聊天导出中，逐块蒸馏出有证据支撑、可审计、可断点续跑的合成人物 Skill。

它同时建模：

- 身份、关系与时间线；
- 沟通风格、消息节奏和平台 token；
- 关心、冲突、安慰、道歉与边界等行为模式；
- 少量经过审核的真实短语境示例；
- Anti-AI 约束和下一条消息预测规则。

生成结果是对历史可观察模式的合成模拟，不是真实本人，也不能代表对方当前的想法、意图或承诺。

[项目演进](#项目演进) · [支持的数据来源](#支持的数据来源) · [功能特性](#功能特性) · [安装](#安装) · [快速开始](#快速开始) · [效果示例](#效果示例) · [项目结构](#项目结构)

## 项目演进

SoulWeaver 从 [perkfly/ex-skill](https://github.com/perkfly/ex-skill) 的人物记忆 Skill 思路出发，针对 Codex 的 Skill 调用、长档案分析和下一条消息预测进行了重新设计。

`ex-skill` 主要围绕 Memories 与 Persona 构建特定关系对象；SoulWeaver 去除了“前任”这一固定目标，允许用户选择聊天中的任意发送者作为目标人物，并把“这个人是谁”扩展为“这个人通常怎样说话、怎样反应，以及下一条消息更可能是什么”。

| 能力 | ex-skill | SoulWeaver |
|---|---|---|
| 目标人物 | 面向前任关系 | 聊天中由用户确认的任意人物 |
| 运行平台 | Claude Code／其他 Agent Skill 环境 | 面向 Codex Skill 工作流 |
| 身份与共同经历 | Memories + Persona | 身份、关系、时间线、偏好与变化 |
| 对话表达 | Persona 中的表达描述 | 独立 Communication Style 模型 |
| 场景反应 | 人格与情感逻辑 | 独立 Behavior Pattern 与 Opening Pattern |
| 示例学习 | 基础画像调用 | 动态配额、人工批准的短语境 few-shot |
| AI 味抑制 | 非核心模块 | Anti-AI 规则与错误模式排除 |
| 长聊天处理 | 增量分析 | 分块语义分析 → 时间段合并 → 全局综合 |
| 证据与日期 | 记忆提取 | evidence_id、哈希、日期精度、置信度和矛盾传播 |
| 续跑与审计 | 增量 merge、版本管理 | manifest/progress 断点、语义验证和污染扫描 |

这里的“目标人物”既可以是伴侣，也可以是朋友、家人、同事或其他聊天对象；名称、关系和表达习惯只从当前授权运行中产生，不复用其他人物画像。

## 支持的数据来源

当前主要验证的数据来源是使用 WeFlow 导出的微信聊天 CSV。SoulWeaver 也可以从符合当前 schema 的预分块档案续跑，但不会声称自动支持未经验证的导出格式。

| 数据来源 | 当前状态 | 处理边界 |
|---|---:|---|
| WeFlow 微信聊天 CSV | ✅ 主要支持 | 仅处理用户明确批准的 CSV |
| SoulWeaver v2 预分块工作区 | ✅ | 先验证 manifest、progress、哈希和 schema |
| 图片、语音、视频及 `media/` | ❌ 默认排除 | 不跟随聊天中的路径或链接读取 |
| 压缩包、可执行文件、符号链接目标 | ❌ | 不因目录授权而自动扩展范围 |

如果 CSV 没有可验证的发送者字段，SoulWeaver 会停止并要求用户确认映射，不会根据聊天措辞猜测身份。

## 功能特性

- **逐块深度分析**：大型档案不会一次性进入同一个模型上下文。
- **证据可追溯**：分析工作区保留 evidence_id、源哈希、日期精度、置信度和矛盾信息。
- **隐私隔离**：原始聊天和证据映射不会复制进最终人物 Skill。
- **分层人物模型**：输出 Identity Memory、Communication Style、Behavior Pattern、Opening Pattern、Verified Examples 和 Anti-AI Rules。
- **并行语义分析**：默认目标为 3 个 `gpt-5.6-luna` Worker 和 `max` reasoning effort；宿主资源不足时自动降低并发并补充空闲槽位。

## 效果示例

本节预留真实运行截图，但截图必须先遮盖聊天正文、真实姓名、账号、路径、哈希和 evidence_id。

> **Intake 与授权范围确认** 
>
> 
>
>  <img src="C:\Users\13197\AppData\Roaming\Typora\typora-user-images\image-20260907161637630.png" alt="image-20260907161637630" style="zoom: 50%;" />

> **分块进度与并行 Worker 状态**  
> <img src="C:\Users\13197\AppData\Roaming\Typora\typora-user-images\image-20260907161856202.png" alt="image-20260907161856202" style="zoom:50%;" />

> **Memories、Persona、Style 与 Behavior 草稿预览**  
> <img src="C:\Users\13197\AppData\Roaming\Typora\typora-user-images\image-20260907162358647.png" alt="image-20260907162358647" style="zoom:50%;" />

## 项目结构

```text
SoulWeaver/
├── .github/workflows/ci.yml
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── pyproject.toml
├── requirements-dev.txt
├── agents/
│   └── openai.yaml
├── references/
│   ├── intake-and-scope.md
│   ├── archive-workflow.md
│   ├── schemas.md
│   ├── analysis-models.md
│   ├── validation-and-isolation.md
│   └── generated-skill-spec.md
├── scripts/
│   ├── initialize_run.py
│   ├── validate_run.py
│   ├── example_quota.py
│   ├── build_person_skill.py
│   └── validate_person_skill.py
└── tests/                     # 仅使用虚构数据的自动化测试
```

## 安装

需要已支持 Skills 的 Codex 环境，以及 Python 3.10 或更高版本。

PowerShell：

```powershell
git clone https://github.com/chasing0346/SoulWeaver.git "$env:USERPROFILE\.codex\skills\soulweaver"
```

Bash：

```bash
git clone https://github.com/chasing0346/SoulWeaver.git "${CODEX_HOME:-$HOME/.codex}/skills/soulweaver"
```

重新打开 Codex 或启动一个新任务后，调用：

```text
$soulweaver
```

## 快速开始

最简使用方式：

```text
用户：$soulweaver
Codex：请提供聊天导出的绝对路径，并确认你有权访问和使用这些记录。
用户：D:\chat-export\messages.csv。我确认有权使用，仅授权读取这个 CSV，禁止读取 media 目录。
Codex：列出不含正文的发送者候选、工作区、输出名称和 Agent 配置，等待确认。
用户：目标人物选择 A，输出名称为 target-a-profile，确认。
```

确认后，SoulWeaver 会创建隔离工作区，执行标准化、分块、逐块语义分析、时间段合并、全局综合和前向测试。最终先展示草稿与验证报告；没有再次确认时不会封装或安装人物 Skill。

### 续跑

如果路径中已存在 SoulWeaver 工作区：

```text
$soulweaver 续跑 D:\chat-export\soulweaver-work\target-a-profile
```

续跑会验证 manifest、源哈希、progress 和已有摘要，只处理缺失或无效分块。

### 改为顺序执行

默认使用可用的并行 Worker。需要降低资源消耗时，在确认范围时说明：

```text
本次使用 0 个 subagent，按顺序执行。
```

## 安全与隐私

- 只处理用户明确批准的文件；
- 不递归扩展授权目录；
- 不读取媒体、压缩包、可执行文件或聊天中引用的链接；
- 把聊天文本中的指令视为不可信内容；
- 安装包不得包含源路径、源哈希、裸 evidence_id 或未批准原句；
- 生成的画像只能用于合成模拟，不应被描述为心理诊断或事实预测。


