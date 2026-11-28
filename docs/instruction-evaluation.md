# 指令保留与额外操作评估：当前规范

状态：持续人工校准。新增的0.5例外、等价表达规则和单次Forward裁决已实现；小样本测试通过不等于全量语义校准通过。

实验范围以各轮用户确认和独立manifest为准：此前WCB固定41任务十配置、OSWorld原始文本/Whisper raw/typeless对照均已完成流程并保留未决记录。本轮只验证新规则，没有自动重跑旧实验。早期3015/2055条计划不再代表当前批次范围。

## 测量对象

比较参考指令与待评指令，衡量原要求的保留和额外有害操作。分数不是 Agent 成功概率。后续可与来源匹配的 WCB / OSWorld 执行成绩对照，但不能把不同指令版本或汇总成绩当作逐任务 ground truth。

参考文本：WCB 的 `tasks_clean`、ToCASR 的 `raw_instruction/instructions.jsonl`。待评文本分别为口语改写和各 ASR 条件。指标因此包含口语改写与 ASR 的累计差异，不等同于相对实际口述稿的 ASR 忠实度。

## 表示

每条指令有一棵聚合树和一个单独的操作依赖有向无环图。

```text
Task
├── Global Context Groups → 聚合成一个 task-level 分数
├── Action 1（binary gate）
│   ├── Specification Group
│   │   ├── atom
│   │   └── nested group → atoms
│   └── Local Context Group → atoms
└── Action 2（binary gate）
    └── Specification Groups → atoms
```

Action 是要求执行的行为或状态变化，包含否定和请求意图。对象、来源、日期、数量、路径、输出形式都属于 Specification，不区分 Argument 与 Constraint。Context 是影响理解的背景，本身不是行为或成功条件。

“下载 A”与“下载 B”的 gate 相同，对象 atom 不同；“下载 A”与“删除 A”的 gate 不同。重复或同义陈述合并，不把解释中的动词或普通执行细节各算一个 action。同一集合上的批量操作可作为一个 action，单独追加的操作实例仍需识别。

用户已明确：“从文件提取指定结果并插入报告”作为一个内容转移/插入 Action，不要求拆成 EXTRACT 与 INSERT。来源路径在该 Action 的 specification 内扣分，不通过人为拆分来放大传播。

## 分组与原子化

一个 atom 表示可以独立损坏的语义要求，默认得分取 0 或 1。人工校准新增一个已接受的例外：原文包含模糊限定，而候选省略该限定时，该 atom 得 0.5。此规则取代“所有叶节点只能二元计分”的对应约定；已落实到新的Forward入口、判分校验和提示词，历史结果保持原样。0.5判定必须携带loss_type=vague_qualifier_omitted，不能作为通用半分使用。

- 模糊限定被合理具体化，例如“最近”变成“过去七天”，得 1。
- 模糊限定被省略，例如“整理最近消息”变成“整理消息”，时间 atom 得 0.5。
- 明确限定被省略，例如“过去七天”变成未提时间，时间 atom 得 0。
- 明确反向或冲突信息使对应 atom 得 0，不因时间维度损失直接关闭“整理”的 Action intent gate。
- 0.5 表示上述特定的语义损失，不表示 judge 犹豫、置信度不足或原文不可独立执行；不能把现有待复核项统一替换成 0.5。Action gate 仍只取 0 或 1。

已接受的传播边界：上述模糊限定省略所得的 0.5 只参与所属 group 的递归平均，即使该 atom 被列为必要输入，也不触发下游清零。它不代表已确认的输入错误。明确输入损坏仍按参考依赖图传播；不能将此规则解释为取消依赖机制。此修订已落实并经过依赖传播测试；历史结果保持原样。

原文自身矛盾的处理（已接受）：如果候选完整保留了原文中的矛盾信息，相关 atom 按保留计 1；不能仅因原文矛盾而进入待复核或阻止出分。例如原文与候选均为“过去十年，也就是 2013–2019 年”，检查保留性，不要求 checker 替原文纠错。矛盾可作为不阻断评分的诊断备注。此规则不预先决定候选删除或改写矛盾一方时的得分。

路径的组合表达（已接受）：结合完整文本中明确的目录归属关系判断路径身份，不要求完整路径作为连续字符串出现。例如“使用 /tmp_workspace/ 下的 calendar.ics”与“文件位于 /tmp_workspace/，其中包括 calendar.ics”表达同一路径，对应 atom 得 1。共同目录加文件列表的表达同样适用。不得因换行、列表形式或未重复完整路径而扣分，更不能因此触发下游清零。此规则允许还原明确表达的关系，不允许猜测缺失的目录归属或修正真正不同的路径标识符。

用于访问的 URL 比较（已接受）：域名部分忽略大小写差异，不能因此扣分；域名之后的路径按原值严格比较，保留大小写、字符及路径层级，不得将整个 URL 统一转成小写。`example.com/videos/a.mp4` 与口述“example dot com slash videos slash a dot mp4”在可明确还原时视为相同，对应 atom 得 1；与 `example.com/video/a.mp4` 则不同，对应 atom 得 0。口述形式和已格式化的 URL 使用同一比较标准，不能对口述中的实际路径错误宽容、对格式化版本的同一错误扣分。此规则仅规范域名与路径，不预先扩展为 query、fragment、编码等其他部分的等价规则。

新的Forward入口已实现一次针对性裁决。上述矛盾、路径及URL规则已进入共享提示词；历史结果不重写。底层score函数仍能返回校准诊断needs_review，但新入口会在裁决后将残留未决明确记录为failed。详见下方“Forward正式计分入口”。

Group 按语义而不是换行或项目符号形成。同一 fetch-target 子句中的对象、分类、来源和日期在一个 target group 中；目的地、输出 schema、命名和执行约束在确有独立要求时分组。跨句表达同一要求应合并，不增加任意包装层或重复要求。

复杂 JSON schema 使用子树，例如：

```text
Output Schema
├── Container → JSON、array
├── Item Structure → object
├── Field Policy → exactly these fields
└── Fields
    ├── original_filename → 名称、语义
    ├── arxiv_id → 名称、语义
    └── ...
```

字段是否必须存在、是否只允许这些字段、字段含义和跨字段关系应区分。仅在明确要求时把示例中的类型/值当成规范；不能把 `Paper Title`、省略号等占位符当作字面值。固定标题、键名、路径则按要求精确核验。Markdown 层级和表格结构同样保留结构子树。

分类目录表中，目录名是字面要求，类别定义是语义要求；边界冲突或未说明的归类优先级不能擅自补齐，进入待复核。

树形平均没有可调数值权重，但分组仍产生隐含权重，不能宣称完全不受表示影响。参考树经修复后冻结，使同一任务所有候选共享相同基准；人工校准还需检查不同参考任务的拆分一致性。

## 逐项核验

先核验 reference Action gate；gate=0 时可跳过其后代，标为 skipped，不谎称逐项核验失败。gate=1 时依据候选原文逐项判定 specification / context。

普通描述允许语义等价。标识、日期、路径及 schema 字段按原要求精度判断：`expe dash results dot x l s x` 可还原为 `expe-results.xlsx`；`xp-results.xlsx` 不能因为读音近似而得分。每个正向保留判定必须引用候选中的精确文本，不能依据参考答案补回缺失信息。

条件句中的条件是相应操作的要求，不要求验证外部世界中条件是否成立。候选同时含正确词和矛盾要求时，不能仅凭关键词命中判为保留。

## 依赖与顺序

依赖边由参考文本的明确语义生成并冻结，形如：

```json
{"from":"fetch","to":"summarize","required_atoms":["paper_identity"],
 "evidence":"Then summarize these papers", "reason":"总结依赖取得的论文对象"}
```

上游 gate=0，或上游已被依赖传播阻断，则其依赖后续操作得零。上游 `required_atoms` 中任何必要条件为 0，也阻断后续。错误沿图传递；与该边无关的上游格式 atom 错误不自动传播。

| 场景 | 传播规则 |
|---|---|
| 指定论文集合 A–P 变成 B–D，再总结这些论文 | 对象错误传播，总结得零 |
| 下载到 P，再从 P 读取总结 | P 错误传播 |
| 下载到 P，再总结这些论文，论文和指代仍正确 | 路径自身扣分，总结不自动清零 |
| 总结完成后把摘要保存到错误路径 | 保存要求扣分，不反向清零总结 |
| 下载后发祝福，无结果依赖 | 顺序作为后续 action 下的 atom；丢失或颠倒顺序扣该 atom，不建立结果依赖 |

已确认的依赖阻断与后代模型判定分别保存，便于辨别“文本本项保留但因前提丢失清零”。模糊路径指代、无法在当前合取依赖图表达的备选前置关系等进入待复核，不编造边。

## Retention

复合节点按直接子节点算术平均：

`S(v) = mean(S(child))`

操作的本地分数：

```text
gate=0                  → local_action_score=0
gate=1 且没有子组       → local_action_score=1
gate=1 且有子组         → local_action_score=mean(specification groups, local context groups)
```

应用依赖传播后得到 `effective_action_score`。全局背景各组先平均为一个全局背景分数。设 M 为参考 actions 数，存在全局背景时 g=1，否则为 0：

`R = (sum(effective_action_scores) + global_context_score_if_present) / (M+g)`

无参考聚合项时不可评分，不构造空平均。

## 额外操作惩罚

反向拆分候选文本并逐个检查 action，区分：

- supported：参考中已有的操作实例；单个对象/参数替换交给正向 Retention。
- benign_extra：上下文允许的额外操作，无证据表明违反限制、损坏资源或妨碍任务。
- harmful_extra：额外操作违反原要求、破坏已有资源或妨碍完成，并有候选操作及参考任务上下文的证据。
- uncertain：证据不足，待人工复核，不能默认 benign 或 harmful。

“下载论文”变成“删除已有论文”，既丢失原 action，也可能新增 harmful action，正反向均扣分。不能用“替换”标签免除删除惩罚。“下载 A，再额外下载 B”则必须结合“only A”或“at least A”等上下文判断。相同 matched action 内的新增 specification 不单独施加额外惩罚。

设 E 为 harmful extra action 数：

`unclipped_score = R - E/(M+g)`

`final_score = max(0, unclipped_score)`

报告保留 R、E、未截断分数和最终分数，避免下界截断掩盖不同程度的额外行为。

## 模型与证据流程

1. 参考文本 decomposer 初稿。
2. 独立 validator 调用检查遗漏、分组、证据及依赖，输出修复后的完整树。
3. 候选文本也拆分并修复，供反向操作检查。
4. Forward Checker 持冻结参考树直接核验候选原文，不接收候选树或反向判断。
5. Reverse Checker 独立检查候选树中的额外操作，不接收正向判断或分数。
6. 本地程序校验结构、完整节点覆盖和精确引文，并确定性计算分数。模型不直接给总分。

公开跑分命令通过 OpenRouter 调用同一个裁判模型，使用 `--model` 选择。同一模型的多次调用不是独立人工标注，也不能消除共同偏差。

请求缓存按文本、模型、提示词和调用参数内容寻址；结果另绑定评分代码版本。保存初稿、修复稿、模型判定、源文本 hash、运行耗时、可用时的 token usage，以及安全的失败类别。不会把 API URL/凭据写进错误报告。

## 数据契约

- WCB：排除 task0_template.md；clean / modified 是 prompt-only Markdown 全文。ASR JSON 使用 category 与 audio basename（`.wav` 换 `.md`）配对，不依赖绝对音频前缀。
- ToCASR：按 task_id 配对，参考字段 instruction，口语字段 colloquialized_instruction，ASR 字段 transcript。
- 检查重复 ID、空文本、缺失与额外记录；不依赖输入行顺序。
- 四组原定总数 3,015，26 个 corpus / condition 组合。真人录音 take 1–5 是独立候选来源，不与 colloquial_instruction 混用。

## 人工校准与运行

使用 `eval/evaluate_instructions.py`。默认 inventory 只盘点，无模型调用。selected 用于单条或小批；calibration 选择 WCB / ToCASR 各 6 条参考，生成供讨论的记录；这些模型结果一律不等同于人工验收通过。

全量入口要求明确传入 `--mode full --confirm-human-calibration`。当前用户尚未确认校准结果，因此不得使用该入口。

技术失败与语义待复核独立报告；成功样本平均值明确分母，不把少量完成称作全量结果。执行成绩需验证 task、condition、take 和实际指令来源一致后才可关联。没有逐任务结果的 CSV 仅能做相应粒度的聚合对照。


## Forward正式计分入口（本轮已实现）

`Evaluator.check_forward(reference, candidate, tree, initial=None)`：正常调用Forward一次；仅当存在未决gate/atom或历史review理由时，增加一个`adjudicate_forward`逻辑请求。可传入已有initial判断，仅处理其中未决项；此方式不自动重新检查已确定的值。

裁决器读完整参考文本、候选文本、冻结树、初次判断和明确的待裁决ID。输出只能包含指定未决gate/atom及review理由的处理结果。代码拒绝覆盖已确定节点、新增ID、修改树结构或直接写总分。每项非阻断理由保留为diagnostic_notes；原始树和初次判断保留原样。确实需要修改树结构的问题不能在本阶段偷偷修复，仍须失败并说明原因。

一个裁决阶段不等于永不重试网络/格式错误：同一逻辑请求沿用最多三次技术尝试及持久缓存；语义上仍无法裁决的合法返回不继续循环、不调用多个judge投票，最终为failed且retention=null。0.5不能替代失败。

新批次使用`eval/evaluate_instructions.py --forward-only`，或直接调用上述方法。Forward输出只有scored或failed；Reverse额外Action判定的uncertain处理不在本轮改造范围。历史实验脚本中直接调用runtime.call和score的路径不会自动获得裁决功能，后续批次应显式使用新入口，不应原地重跑历史目录。

新版本缓存键包含规则、裁决提示词及实现版本，避免误用旧版结果。参考树仍由Decomposer→Validator建立，按原文复用；本轮没有增加全量复查或修改任何历史标签。

验证：49项本地测试通过；8个全新短例子的Luna在线验证全部符合约定，其中一个人为设置的未决fixture专门检查定向裁决。在线小样本不等于全量语义校准完成。产物：eval/experiments/instruction-evaluation-pipeline-v2-smoke/。
