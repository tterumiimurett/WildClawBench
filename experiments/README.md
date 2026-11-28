# Reproduce the WCB and OSWorld correlation tables

Use Python 3.11 or newer. Both commands read the included score snapshots and write CSV to standard output. They run offline after SciPy is installed.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r experiments/requirements.txt
python experiments/reproduce.py wcb
python experiments/reproduce.py osworld
```

| Table | Inputs and interpretation |
|---|---|
| [WCB](wcb/comparison600.csv) | 60 tasks × 10 configurations, including Safety. Each row pairs the average of three execution scores with eight instruction metrics. Error and distance columns already contain 1 − error or distance. Flat, Shapley and Native are saved per-row scores. The output gives Pearson and Spearman correlations over the same 600 rows. |
| [OSWorld](osworld/separate_asr_category_scores.csv) | Each row gives one agent, ASR condition and category. Each coefficient compares available category means for a single agent and condition. The archived table includes lexical similarity, SemDist and Retention. Missing categories are omitted per metric. Constant inputs or fewer than three complete categories yield empty coefficients. |

The WCB configurations share tasks. The OSWorld execution results are category aggregates. Their task and speaker denominators are unconfirmed. Interpret the OSWorld coefficients descriptively and use the reported category counts when comparing metrics. The tables reproduce statistics from recorded scores. Rerunning agents or model judges is a separate experiment.

## Score new instructions

Use the [Intent Retention quick start](../README.md) to score your own JSONL. To compare lexical or AER baselines on the same inputs, run the following commands from the repository root.

```bash
python eval/evaluate_instruction_baselines.py --input examples/instruction-pairs.jsonl --metrics lexical --output output/example-lexical
python eval/evaluate_instruction_baselines.py --input examples/instruction-pairs.jsonl --metrics aer --output output/example-aer
```

Lexical scoring runs offline. AER uses the same OpenRouter credentials as Intent Retention. SemDist requires a local embedding model snapshot. See the [baseline guide](../docs/instruction-baselines.md) and the [dataset guide](../data/README.md).
