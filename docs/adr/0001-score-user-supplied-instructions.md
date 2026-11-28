# 外部使用者可以用自己的指令跑分

评分工具应接受使用者提供的样本。使用发布版本的数据做研究时，WCB 和 OSWorld 的完整数据由 Hugging Face 提供，GitHub 保存评分代码、小型示例和数据版本索引。

因此，用自己的样本跑分是独立的验收场景。新用户无需还原研究者机器上的数据目录，也无需先下载两个基准的数据。

首版支持用 Intent Retention 给新样本打分。WCB 的 Flat、Shapley 和 Native 保留实验表格所用的逐样本历史分数，供复算相关性。GitHub 首页以一个输入、运行、读分的完整例子作为主入口，另设 WCB 执行框架和实验表格复现入口。

公开命令接受含有 `id`、`reference` 和 `candidate` 的 JSONL。各阶段共用一个 OpenRouter 模型，逐条返回 `retention` 和 `final_score`。未能评分的样本保留状态和原因，分数置空。
