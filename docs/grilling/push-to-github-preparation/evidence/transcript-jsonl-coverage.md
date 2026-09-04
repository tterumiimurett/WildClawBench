# Transcript JSONL Coverage

This audit established the deletion gate for per-recording Markdown transcripts under `ToCASR/recorded_instruction/tasks_asr/`. Publication and deletion happened only after the read-only coverage proof completed.

| Model | Variant | Markdown files | Canonical JSONL | Coverage |
|---|---|---:|---|---:|
| `gpt-4o-transcribe` | `raw_asr` | 1,755 | `gpt-4o-transcribe/raw_asr.jsonl` | 100% |
| `gpt-4o-transcribe` | `typeless_ontology_fix` | 1,755 | `gpt-4o-transcribe/typeless_ontology_fix.jsonl` | 100% |
| `whisper_v3` | `raw_asr` | 1,755 | `whisper_v3/raw_asr.jsonl` | 100% |
| `whisper_v3` | `typeless_ontology_fix` | 1,755 | `whisper_v3/typeless_ontology_fix.jsonl` | 100% |

All four JSONL files live under `ToCASR/recorded_instruction/tasks_asr/<model>/`. Each contains 1,755 parseable records with the schema `task_id`, `source_task_id`, `take`, `audio`, and `transcript`.

## Verified invariants

- Every Markdown stem matches exactly one JSONL `task_id`; missing, extra, and duplicate IDs are all zero.
- All five fields are present and non-empty in every record.
- `source_task_id`, `take`, and `audio` mappings match; every referenced local audio path exists.
- The 1,755 recordings cover 351 source tasks with exactly five takes each.
- Spaces, punctuation, dashes, and internal newlines are identical. Each Markdown file is exactly its JSONL `transcript` plus one final LF byte.
- The repository validator passed with 1,755 recordings, 351 source tasks, and ASR required.
- Export-directory and ZIP copies of all four JSONL files are byte-identical to the canonical files; the ZIP passed its integrity check.

## Deleted transcript artifacts

Only these directories were covered by this proof and subsequently deleted:

```text
ToCASR/recorded_instruction/tasks_asr/gpt-4o-transcribe/raw_asr/
ToCASR/recorded_instruction/tasks_asr/gpt-4o-transcribe/typeless_ontology_fix/
ToCASR/recorded_instruction/tasks_asr/whisper_v3/raw_asr/
ToCASR/recorded_instruction/tasks_asr/whisper_v3/typeless_ontology_fix/
```

They contained exactly 7,020 Markdown files and no other files or subdirectories. They occupied 1.09 MiB; deletion primarily reduced file count.

Immediately before deletion, all 7,020 Markdown files were rechecked as exactly
their matching JSONL `transcript` encoded as UTF-8 plus one final LF. Immediately
after deletion, `validate_recorded_instruction.py --require-asr
--skip-audio-hashes` passed for 1,755 recordings and 351 source tasks.

The deletion occurred only after private Hugging Face revision
`f275a3da8a38403aefa7ab5f741c9b3a3c541a1d` passed remote path, LFS hash, and
small-file byte readback. These Markdown files were untracked, so local Git
cannot restore them; the canonical JSONL and verified private remote are the
recovery sources.

## Retained Markdown

The following documentation and reports are outside the deletion set:

```text
ToCASR/colloquial_instruction/tasks_asr/wer_report.md
ToCASR/raw_instruction/tasks_asr/wer_report.md
ToCASR/recorded_instruction/README.md
ToCASR/recorded_instruction/source/README.md
ToCASR/recorded_instruction/tasks_asr/wer_report.md
ToCASR/recorded_instruction/exports/AudioPrompts_asr_results/gpt-4o-transcribe/wer_report.md
ToCASR/recorded_instruction/exports/AudioPrompts_asr_results/whisper_v3/wer_report.md
final_dataset/dns-noise-wer10/REPORT.md
final_dataset/dns-noise-wer10/evidence/calibration/report.md
```
