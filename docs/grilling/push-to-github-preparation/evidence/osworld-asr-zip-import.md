# OSWorld ASR ZIP Import Audit

## Source preservation

The supplied WeChat file was copied, without extraction or modification, to
`ToCASR/OSworld_ASR.zip` before inspection.

- Size: approximately 4.9 MiB compressed
- SHA-256: `fcf1fca8ae84974f3cea761ed3558c61186f3162e7d0734f034deb87b6ac18c4`
- The source file and `ToCASR` copy have the same SHA-256.
- ZIP integrity testing succeeded.
- The archive contains 8,810 members and 22,960,704 uncompressed bytes.

## Result conditions

The archive contains five result streams, not four:

| Model | Biasing | Raw rows | Successful rows | Failed retry rows | Unique successful audio |
|---|---:|---:|---:|---:|---:|
| Parakeet TDT 0.6B v2 | no | 2,649 | 1,755 | 894 | 1,755 |
| Qwen2.5-Omni-7B | no | 1,757 | 1,755 | 2 | 1,755 |
| faster-whisper-large-v3-turbo | no | 1,755 | 1,755 | 0 | 1,755 |
| Parakeet TDT 0.6B v2 | yes | 1,755 | 1,755 | 0 | 1,755 |
| Qwen2.5-Omni-7B | yes | 1,756 | 1,755 | 1 | 1,755 |

For every stream, the set of successful `audio_name` values exactly matches
the 1,755 recordings in `ToCASR/recorded_instruction/manifest.jsonl`.
`task_id` and `speaker_id` also match the manifest's source task and take with
zero mismatches. Every successful record has a non-empty transcript.

The failed records are append-only retry history. Filtering to
`status == "complete"` yields exactly one canonical transcript per recording
for every condition.

## Bias-list provenance

The biased Parakeet and Qwen records name
`OSWorld_biasing_list.json` as their biasing source and record the number of
task bias terms, but the Bias List payload itself is not present in the ZIP.
The stored source values are server-local absolute or project-relative paths.
The initial publication therefore marked the Bias List as pending. The later
supplied `OSWorld_biasing_list.json` covers all 351 tasks and has SHA-256
`797ab1863b645bebca8776c5e699f600da49f9d54f402f74630239b605521d58`.
For both biased run manifests, all 351 per-task term counts match this file
with zero mismatches. The published conditions are now marked `available`.

## Non-canonical archive contents

In addition to five `results.jsonl` files, the archive contains five run logs,
five manifests, 8,775 per-recording text files, and six stdout/waiter logs.
These duplicate successful transcript payloads or contain server-local paths
and retry details. They should not be treated as canonical Dataset Viewer
records.

## Additional Whisper run

The without-bias Whisper stream is complete but was not mentioned in the
supplied description of two models. It is not byte-equivalent to the existing
Whisper raw transcript set: 1,330 of 1,755 transcript strings match exactly and
425 differ. It must be preserved under a distinct run identity if published;
it must not overwrite the existing Whisper JSONL.

## Import decision and outputs

Only the two user-selected model families were imported. The additional
Whisper without-bias run is excluded from Agentic ASR.

| Model | Biasing | Canonical output | Rows | SHA-256 |
|---|---:|---|---:|---|
| Parakeet TDT 0.6B v2 | no | `tasks_asr/parakeet_tdt_0.6b_v2/raw_asr.jsonl` | 1,755 | `975eff04bd25dc50b4c0a3719f0cecabdefd94d08e99a97c2edbd0e87210603d` |
| Parakeet TDT 0.6B v2 | yes | `tasks_asr/parakeet_tdt_0.6b_v2/raw_asr_bias.jsonl` | 1,755 | `0a0c99806d1f4b539d9ddbe8674b30ca4d7fbcb04eb4ac9dda21f686a67b228a` |
| Qwen2.5-Omni-7B | no | `tasks_asr/qwen2.5_omni_7b/raw_asr.jsonl` | 1,755 | `478ea0914046b7c1e1360adb266f77dcbae829b9b7de42cfb2ead034f8902e15` |
| Qwen2.5-Omni-7B | yes | `tasks_asr/qwen2.5_omni_7b/raw_asr_bias.jsonl` | 1,755 | `e6a7c6eb150b87eb1e0b0c8db8db5853980ef7f4feeeea28390bc6e0b77e17d9` |

Each output has the established five-field schema: `task_id`,
`source_task_id`, `take`, `audio`, and `transcript`. Each has 1,755 unique task
IDs, 1,755 unique audio paths, no empty transcripts, exact coverage of the
recording manifest, and no task/take mapping errors. Bias-assisted outputs are
marked `bias_list_status: available` in
`tasks_asr/osworld_asr_import_manifest.json` and reference the versioned Bias
List by path and SHA-256.

Failed retry rows were excluded from canonical outputs: 894 for Parakeet
without bias, two for Qwen without bias, zero for Parakeet with bias, and one
for Qwen with bias. Per-item text copies and runtime logs remain inside the
source ZIP but are not formal dataset rows.
