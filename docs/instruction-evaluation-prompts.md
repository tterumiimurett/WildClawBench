# Intent Retention judge prompts

The scorer reads these files at runtime. Follow the sequence to inspect the instructions behind an individual score.

| Stage | Instructions |
|---|---|
| Build a requirement tree for each instruction and check its coverage | [Decompose](../eval/prompts/instruction_eval/decompose.md) · [Audit](../eval/prompts/instruction_eval/audit.md) |
| Check which reference actions and requirements survive | [Forward](../eval/prompts/instruction_eval/check_forward.md) |
| Resolve outstanding forward judgments | [Targeted adjudication](../eval/prompts/instruction_eval/adjudicate_forward.md) |
| Identify harmful extra actions introduced by the candidate | [Reverse](../eval/prompts/instruction_eval/check_reverse.md) |

Decomposition, audit, forward judgment and adjudication share the [retention rules](../eval/prompts/instruction_eval/retention_rules.md). Judges cite source spans using IDs from the [evidence catalog](../src/utils/instruction_eval/evidence.py). The [scoring rules](instruction-evaluation.md) describe how validated judgments become scores.
