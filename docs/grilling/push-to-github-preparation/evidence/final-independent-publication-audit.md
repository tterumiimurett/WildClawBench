# Final Independent Dataset Publication Audit

- Status: **PASS**
- Audited: 2026-09-04
- Dataset: `tterumiimurett1/agentic-asr` (private)
- Pinned revision: `794a16d0513b5f4b9f4e644465fcb31352331e16`

The machine-readable publication interface is
[`configs/datasets/agentic-asr.lock.json`](../../../../configs/datasets/agentic-asr.lock.json).
GitHub stores this lock and the benchmark code; Hugging Face is the sole
canonical location for dataset payloads.

## Local-to-Hugging-Face mapping

| Local source | Published Hugging Face location | Publication rule |
|---|---|---|
| `ToCASR/raw_instruction/` | `osworld/synthetic/raw_instruction/` | Canonical instruction, audio, ASR, and reports |
| `ToCASR/colloquial_instruction/` | `osworld/synthetic/colloquial_instruction/` | Canonical instruction, audio, ASR, and reports |
| `ToCASR/recorded_instruction/` | `osworld/human_recordings/` | 1,755 MP3 recordings, manifest, canonical ASR JSONL, metadata, and reports |
| `ToCASR/images/` | `osworld/task_images/` | 351 task images |
| `final_dataset/dns-noise-wer10/` | `osworld/dns_noise_wer10/` | 351 paired records, 702 WAV files, reports, and selected provenance |
| `ToCASR/bias_lists/OSWorld_biasing_list.json` | `osworld/bias_lists/OSWorld_biasing_list.json` | Byte-identical copy |
| `colloqialized_prompt/tasks_clean/` and `tasks_modified/` | `wildclawbench/synthetic/prompts.jsonl` | 60 formal tasks consolidated; `task0_template` excluded |
| `colloqialized_prompt/tasks_tts/` | `wildclawbench/synthetic/audio/` | 60 formal WAV files; `task0_template` excluded |
| `colloqialized_prompt/tasks_asr/` | `wildclawbench/synthetic/asr/` | Transcript text preserved; audio paths made repository-relative |
| `colloqialized_prompt/bias_lists/WCB_task_details_biasing.json` | `wildclawbench/bias_lists/WCB_task_details_biasing.json` | Byte-identical copy |

## Transcript replacement gate

The deleted OSWorld per-recording transcript Markdown was recovered from the
pre-deletion `tasks_asr.zip` backup and independently checked against the four
original canonical JSONL files.

| Model | Variant | Markdown | JSONL rows | JSONL SHA-256 |
|---|---|---:|---:|---|
| GPT-4o Transcribe | raw | 1,755 | 1,755 | `9c62beeb21c5daf0c4f4d4ad7c14aa724b323a51094bbfa9f079fca7a4c9c164` |
| GPT-4o Transcribe | typeless ontology fix | 1,755 | 1,755 | `bb1ef017874e6314bf33b94c15bd5cd4e8105ed9963df9a651c543c9531a907b` |
| Whisper v3 | raw | 1,755 | 1,755 | `5b920289dd526e2bd99eb1afe2bf42013ae1d98905522f1aa5987b04d81ba062` |
| Whisper v3 | typeless ontology fix | 1,755 | 1,755 | `278e9cd7c1114227c035834f4944237313fe1774e947e3b3941ebec9187d6855` |

Every Markdown path was `<task_id>.md`, and every file was exactly the
corresponding JSONL `transcript` encoded as UTF-8 plus one final LF byte.
Missing, extra, duplicate, content-mismatch, task/take-mapping, and audio-path
failures were all zero. The archive JSONL, local canonical JSONL, and pinned
Hugging Face JSONL were byte-identical for all four conditions.

## Pinned remote acceptance

The pinned private revision was verified by recursive tree comparison, LFS
metadata comparison, and small-file readback.

- Remote tree: 3,640 paths; expected tree: 3,640 paths; missing and extra: 0.
- File manifest: 3,638 unique indexed paths and 1,688,400,051 indexed bytes.
- LFS media: 1,755 MP3, 1,464 WAV, and 351 PNG files; SHA-256 and size failures: 0.
- Indexed structured/document files: 33 JSON, 26 JSONL, and 9 Markdown files; readback failures: 0.
- ASR conditions: 36; Dataset Viewer configurations: 41; missing referenced paths: 0.
- All indexed JSON and JSONL payloads parsed successfully.

The remote integrity roots are:

| Artifact | Rows | SHA-256 |
|---|---:|---|
| `metadata/files.jsonl` | 3,638 | `c29462e42b67fb22034a33b29fb5fb25cb7edea4a88ab65a87f0ffec740cad74` |
| `metadata/conditions.jsonl` | 36 | `2fde967d9ed2c91d7908a61cb8441c8ad835a58231688961abda44388768f1e0` |
| `README.md` | n/a | `d62aea7eedbedfc5bee9e0e6a108735bc8319cb622c31f642eb92181fa85fe45` |

## Bias-list acceptance

- OSWorld: 351 of 351 tasks, SHA-256
  `797ab1863b645bebca8776c5e699f600da49f9d54f402f74630239b605521d58`.
- WildClawBench: 60 of 60 formal tasks, SHA-256
  `052d04975c5fc9cab2a569672b7f8f5ad4877d8f03c862eb78895cce491f6d6a`;
  `task0_template` is excluded.
- The WeChat sources, local canonical files, and pinned Hugging Face files are
  byte-identical. All ten biased conditions are marked `available`.

## OSWorld ZIP inclusion boundary

Only Parakeet TDT 0.6B v2 and Qwen2.5-Omni-7B, each with and without biasing,
were imported from `OSworld_ASR.zip`. Every imported condition contains 1,755
complete rows. Failed retry rows, per-recording text copies, logs, and the ZIP
itself are not canonical dataset content.

The ZIP's additional Whisper run differs from the pre-existing Whisper v3
condition in 425 transcripts and was not uploaded under any additional run
path. The pre-existing Whisper v3 JSONL remains a separate canonical condition.

## GitHub publication rule

This audit and the dataset lock may be published to GitHub. Audio, images,
transcript JSON/JSONL, bias-list payloads, archives, model caches, run outputs,
credentials, signed download URLs, and machine-specific absolute paths must
remain outside the Git repository.
