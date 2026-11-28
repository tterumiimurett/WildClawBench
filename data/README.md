# WCB 与 OSWorld 数据目录

复现实验使用 Hugging Face 上的 [Agentic ASR 固定版本](https://huggingface.co/datasets/tterumiimurett1/agentic-asr/tree/de19aa31572449686166680810468dea86608329)。[数据锁](../configs/datasets/agentic-asr.lock.json)记录了本地路径、远端路径、转写条件和文件清单校验值。下表按**音频是怎么产生的**区分数据；ASR 转写是对相应音频的识别结果。

## 找数据

本地路径均相对于当前仓库根目录。数量核对自本机音频文件及固定版本的 HF 文件列表，单位是音频文件数。

| 基准与来源 | 当前本地位置 | HF 目录 | 内容 |
|---|---|---|---|
| WCB · TTS | `data/colloqialized_prompt/tasks_tts/` | `wildclawbench/synthetic/` | 60 条正式任务音频，转写在本地同级 `tasks_asr/`。本机另有 1 条模板音频 |
| WCB · 真人朗读 | `data/colloqialized_prompt/human_recordings/` | `wildclawbench/human_recordings/` | 10 位参与者，600 条录音。按数据锁，Parakeet 每个条件有 600 条结果，Qwen 使用清洗后的 507 条 |
| OSWorld · 原始指令 TTS | `data/ToCASR/raw_instruction/` | `osworld/synthetic/raw_instruction/` | 351 条 WAV，配有参考指令和转写 |
| OSWorld · 口语指令 TTS | `data/ToCASR/colloquial_instruction/` | `osworld/synthetic/colloquial_instruction/` | 351 条 WAV，与原始指令按任务配对 |
| OSWorld · 真人朗读 | `data/ToCASR/recorded_instruction/` | `osworld/human_recordings/` | 351 个任务，每个 5 条录音，共 1,755 条 MP3 |
| OSWorld · 加噪实验 | `data/final_dataset/dns-noise-wer10/` | `osworld/dns_noise_wer10/` | 351 对原始／口语音频，共 702 条 WAV，附实验清单、评估与来源记录 |

任务图像和识别偏置词表也有独立映射，见数据锁中的 `local_to_hf`。要按识别模型或条件选转写，可查固定版本中的 `metadata/conditions.jsonl`。

## TODO（仓库整理完成后）

- [ ] 用 Hugging Face 数据集 `tterumiimurett1/Talk2AgentBench` 中的 WCB 数据，完整替换 `tterumiimurett1/agentic-asr` 中的 WCB 真人录音数据（`wildclawbench/human_recordings/`）。

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
