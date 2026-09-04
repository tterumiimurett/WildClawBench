# Hugging Face Dataset Inventory

This inventory distinguishes unique dataset assets, redundant exports, and natural dataset configurations. It was used to define the later private publication.

## Unique audio and image assets

| Dataset block | Count | Size | Kind |
|---|---:|---:|---|
| `ToCASR/raw_instruction/audio` | 351 WAV | 163 MB | clean raw TTS |
| `ToCASR/colloquial_instruction/audio` | 351 WAV | 190 MB | clean colloquial TTS |
| `ToCASR/recorded_instruction/source/All Recordings` | 1,755 MP3 | 408 MB | human recordings, five takes for each of 351 tasks |
| `ToCASR/images` | 351 PNG | 197 MB | task-associated images |
| `final_dataset/dns-noise-wer10/pairs` | 702 WAV | 356 MB | 351 raw/colloquial noisy pairs |

SHA-256 comparison of all 3,159 audio files found no byte-identical audio shared between the ToCASR roots and `final_dataset`. The DNS-noise audio is a distinct derived condition, not a duplicate of clean audio.

## Natural ToCASR dataset configurations

**`clean_tts_pairs`**:
351 rows pairing raw and colloquial clean TTS audio, references, model outputs, and optional task images.

**`human_recordings`**:
1,755 rows containing recording identity, source task, take, MP3, reference, hashes, and four model-and-variant transcripts.

**`dns_noise_wer10`**:
351 paired rows containing 702 unique noisy WAV files, split assignments, pair manifests, evaluation, and provenance.

The 75 MB `final_dataset` evidence tree is reproducibility material rather than a training split.

## Verified redundant copies

- Four ASR JSONL files under `recorded_instruction/exports/` are byte-identical to their canonical `tasks_asr/` files.
- Exported WER reports duplicate the canonical reports.
- `final_dataset` raw and colloquial instruction JSONL files are byte-identical to the corresponding ToCASR instruction JSONL files.
- Four `to_terumi` JSON files are byte-identical to their `colloqialized_prompt/tasks_asr/gemini/` counterparts.
- Large ZIP files are packaging artifacts with macOS metadata and are not canonical dataset representations.

## Existing `colloqialized_prompt` repository

`colloqialized_prompt/` is already an independent public Hugging Face Dataset repository at `tterumiimurett1/colloqialized_prompt`. Its remote and local committed `main` point to the same revision.

The current local worktree contains pre-existing, unstaged changes:

- 203 tracked per-item ASR Markdown files are deleted locally.
- 20 aggregate JSON files and four ZIP files are untracked.
- `AGENTS.md` is modified.

Of the 203 deleted ASR Markdown files, 200 formal-task transcripts are covered byte-for-byte by aggregate JSON. The three `task0_template.md` transcripts are intentionally excluded because `task0_template` is not a formal benchmark task. `tasks_clean/` and `tasks_modified/` Markdown files are prompt records, not ASR Transcript Artifacts.

The 20 aggregate JSON files use `data/tasks_tts/...` audio paths while the repository currently stores WAV files at `tasks_tts/...`; publication requires one consistent layout.

## Published repository boundary

- The existing public `colloqialized_prompt` repository remains unchanged.
- A new consolidated private Dataset, `tterumiimurett1/agentic-asr`, contains parallel `osworld/` and `wildclawbench/` families.
- OSWorld and WildClawBench each have a family-scoped `bias_lists/` directory. All ten bias-assisted conditions now reference their supplied Bias List path and SHA-256 and are marked `available`.
- WildClawBench code remains in GitHub; ToCASR production-pipeline code and local dataset trees remain outside the GitHub repository.
