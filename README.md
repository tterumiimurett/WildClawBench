# Intent Retention

Score how much of a reference instruction survives a rewrite or an ASR transcript. Intent Retention checks the requested actions and their requirements, then checks whether the candidate introduced harmful extra actions.

## Score your first pair

From the repository root, install the judge dependencies and set `OPENROUTER_API_KEY` in your environment or the local `.env` file.

```bash
python -m pip install openai python-dotenv
python -m eval.score examples/instruction-pairs.jsonl
```

Each input line has a unique ID and two texts. The [example file](examples/instruction-pairs.jsonl) includes English and Chinese pairs.

```json
{"id":"en-example","reference":"Save the report as a PDF","candidate":"Save the report as a CSV"}
```

In a run with the default judge, the English example produced the following row. The judge marked the report as retained and the requested PDF format as lost.

```json
{"id":"en-example","status":"scored","retention":0.5,"final_score":0.5}
```

The command sends the texts to OpenRouter and writes one JSON line per pair to standard output in input order. `retention` is the degree to which the original actions and requirements are preserved. `final_score` also deducts harmful extra actions. Both range from 0 to 1. Rows requiring review or failing validation carry a status, a reason and null scores. The command exits with status 1 if any pair could not be scored.

The default judge is `openai/gpt-5.4-mini`. Use `--model` to select an OpenRouter model that supports JSON output. All judging stages use that model. Use `--output` to choose where detailed judgments and cached calls are saved (default `output/intent-retention/`). Save the printed JSONL by redirecting standard output to a file.

## Explore the repository

| To | Open |
|---|---|
| Understand the calculation and inspect the judge prompts | [Scoring rules](docs/instruction-evaluation.md) · [Prompts](docs/instruction-evaluation-prompts.md) |
| Run WER, CER, AER and other baselines | [Baseline guide](docs/instruction-baselines.md) |
| Reproduce WCB and OSWorld correlation tables from saved scores | [Experiments](experiments/README.md) |
| Find benchmark recordings and transcripts on Hugging Face | [Datasets](data/README.md) |
| Run agents on the original WildClawBench tasks | [Upstream benchmark and attribution](docs/wildclawbench.md) |
