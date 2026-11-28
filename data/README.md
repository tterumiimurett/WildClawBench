# WCB 与 OSWorld 数据

音频、指令、ASR 转写和文件校验值统一发布在 [Talk2AgentBench 固定版本](https://huggingface.co/datasets/tterumiimurett1/Talk2AgentBench/tree/a521bf8725f37cce415f3f20c790f471b4574fc4)，可直接下载。[数据锁](../configs/datasets/talk2agentbench.lock.json)记录版本与清单 SHA-256。

**WildClawBench（WCB）** 收录 60 个中英文命令行智能体任务，例如整理报告和检索信息。原始采集中，每个任务由 10 位熟悉中英文的读者分别朗读。当前版本按每个任务 10 个读者编号组织，补录时同一编号可能换人。8 个涉及 URL 的任务各录了指定读法和自由读法，其余 52 个任务的两个版本共用同一份录音。

**OSWorld** 收录 351 个英文图形桌面任务，例如编辑文档、填写电子表格。整套采集共有 98 位参与者，每个任务有 5 份真人录音，共 1,755 条。清单按任务和录音序号标识每条音频。[采集说明，论文 §3.1](https://arxiv.org/html/2609.38867v1#S3.SS1)

| 基准 | HF 目录 | 覆盖范围 |
|---|---|---|
| OSWorld 真人 | `osworld/human_recordings/` | 351 个任务，每个 5 条录音，共 1,755 条。12 个 ASR 条件均覆盖全部录音 |
| OSWorld 原始／口语指令 TTS | `osworld/synthetic/` | 两种指令各 351 条音频，各有 4 个完整 ASR 条件 |
| OSWorld 加噪 | `osworld/dns_noise_wer10/` | 351 对原始／口语音频，共 702 条 |
| WCB 真人 | `wildclawbench/human_recordings/` | 60 个任务 × 10 个读者槽位 × 2 种 URL 读法，共 1,200 条。8 个 ASR 条件各覆盖 194 条 |
| WCB TTS | `wildclawbench/synthetic/` | 60 个任务，20 个 ASR 条件均覆盖全部任务 |

WCB 真人录音的清单以 `(speaker, task, version)` 标识样本，`file` 相对于 `wildclawbench/human_recordings/`。1,200 条记录对应 680 份不同音频，84 条记录标有局部合成修补区间。转写按音频哈希、任务与读者槽位从历史结果匹配。

## 历史实验

已有实验使用 [agentic-asr 固定版本](https://huggingface.co/datasets/tterumiimurett1/agentic-asr/tree/de19aa31572449686166680810468dea86608329)。[历史数据锁](../configs/datasets/agentic-asr.lock.json)记录原始输入和转写条件。该版本的 WCB 真人集有 600 条录音，Parakeet 每个条件覆盖 600 条，Qwen 每个条件覆盖 507 条。[实验指南](../experiments/README.md)说明如何用保存的分数复算主表。

## 本地目录布局

原目录和文件均保留原名。评估代码从上表的本地位置取数。GitHub 保存代码、索引和版本信息，音频与完整转写由 HF 提供。

| 原根目录条目 | 当前位置 | 用途 |
|---|---|---|
| `colloqialized_prompt/` | `data/colloqialized_prompt/` | WCB 数据，有独立的 `.git`。指令评估、历史 prompt 实验、运行脚本和数据发布脚本使用此目录 |
| `ToCASR/` | `data/ToCASR/` | OSWorld 数据及生产脚本。指令评估和数据发布脚本使用此目录 |
| `final_dataset/` | `data/final_dataset/` | OSWorld 加噪条件及证据；数据发布脚本按此根目录读取 |
| `to_terumi/`、`to_terumi.zip` | `archive/` 下同名目录和文件 | 历史交付。包内 4 份 Gemini JSON 与解压目录、WCB 的 `tasks_asr/gemini/` 对应文件逐份一致，每份 60 条 |
| `ToCASR_w-audio.zip` | `archive/ToCASR_w-audio.zip` | 包含 351 WAV、351 PNG、任务配置及两个脚本的快照 |
| `colloqialized_prompt.zip` | `archive/colloqialized_prompt.zip` | 包含 125 WAV、Markdown 和脚本的历史快照，内容范围与正式 60 条 WCB TTS 不同 |
| `WCB_ASR_TEXTS.tar.gz`、`。` | `archive/` 下同名文件 | 两文件逐字节相同，包内有 156 份文本、3 个 JSONL 和说明 |
| `wcb_asr_qwen_parakeet_three_methods_180条.tar.gz` | `archive/` 下同名文件 | 180 份文本及 JSON、CSV、JSONL 等对照材料 |
| `tutorial/`、`tutorial.zip` | `archive/` 下同名目录和文件 | 本地模型调用示例和历史打包版本 |

当前根目录的 `tasks/` 保存 WCB 任务定义，`workspace/` 和 `Images/` 用于运行时素材，`output/` 保存运行产物。指标实现的本地入口在 `eval/` 和 `src/utils/instruction_eval/`，两张公开主表的复算入口见[实验指南](../experiments/README.md)，历史实验材料在本地 `eval/experiments/`。

### 使用本地数据的入口

- [指令语料加载器](../src/utils/instruction_eval/corpus.py)读取 `data/` 下的两个数据目录。基线及自研评估应继续读取相同任务、音频条件和转写。
- `eval/script/{run_asr,run_modified,run_typeless_asr}.sh` 和 `eval/experiments/20260717_productivity_flow_prompt_variants/{run_experiment,analyze_prompt_text}.py` 已指向新的 WCB 根目录；这些历史脚本所需的部分 Markdown 子目录在当前数据版本中已由 JSON 转写汇总代替。
- 维护工作区的发布脚本目录中的 `build_agentic_asr_upload.py`、`build_bias_list_update.py`、`build_ontology_update.py`、`publish_wcb_human_ontology.py` 包含本地数据路径。历史发布记录中的原始路径保留作来源证据。
- [忽略规则](../.gitignore)覆盖本地数据和归档；数据索引保存在 Git 中。
