# Push to GitHub Preparation

Status: complete.

This session prepares the WildClawBench code and ASR datasets for separate publication to GitHub and Hugging Face without losing transcript content or provenance.

## Confirmed decisions

- GitHub is the Code Repository; Hugging Face hosts Dataset Repository content, including audio.
- Per-item Transcript Artifacts may be deleted only when Coverage Proof succeeds against Canonical Transcript Records.
- README files, WER reports, and dataset reports are retained.
- Transcript equality is strict: spaces, punctuation, dashes, and internal newlines must match. A declared final-file newline is serialization rather than transcript content.
- Hugging Face publication must complete and pass remote readback before local Transcript Artifacts are deleted.
- New Hugging Face publication starts private; public release is a later decision.
- The `colloqialized_prompt` dataset is part of the Hugging Face publication scope.
- The local workstation does not have enough storage for the model runtime; model execution moves to an Execution Host.
- The Execution Host must reconstruct the project from versioned code and dataset assets rather than depending on a copy of the local working directory.
- Dataset-pipeline code and its model runtime do not move to the Execution Host; only finalized audio and ASR records are published as dataset assets.
- The benchmark is rebuilt from the GitHub checkout on a macOS Execution Host.
- A public Hugging Face Dataset is the consolidated publication target for both `colloqialized_prompt` and ToCASR content, separated by explicit dataset configurations.
- The existing public `colloqialized_prompt` repository remains separate; the consolidated `agentic-asr` repository is also public and is the canonical cross-benchmark dataset.
- The four original human-recording JSONL files remain preserved; their covered per-item Markdown may be deleted only after Hugging Face upload and remote readback succeed.
- ToCASR pipeline code is outside the WildClawBench GitHub publication scope because it belongs to a separate data-production project.
- The consolidated public dataset is named `Agentic ASR`, at Hugging Face repository `tterumiimurett1/agentic-asr`.
- Local `ToCASR/` assets publish under the `OSWorld` dataset family; local `colloqialized_prompt/` assets publish under the `WildClawBench` dataset family.
- Both dataset families use parallel structure for synthetic audio and human recordings. WildClawBench now includes 600 recordings from 10 participants.
- `task0_template` is not formal WildClawBench data. Its derived clean/modified text, TTS audio, and ASR transcripts are excluded from publication and do not require conversion into canonical JSON.
- The four original OSWorld human-recording JSONL files are the sole transcript copies for those conditions. A small manifest and Hugging Face configuration may describe their model, variant, row count, checksum, and audio root, but must not duplicate transcript payloads.
- Each dataset family has a `bias_lists/` collection at family scope so synthetic and future human-recording ASR conditions reference the same versioned biasing scheme.
- The twelve WildClawBench `_bias` conditions reference `WCB_task_details_biasing.json`; four OSWorld biased human-recording conditions reference `OSWorld_biasing_list.json`. All sixteen are marked `bias_list_status: available` with source SHA-256 values.
- The supplied `OSworld_ASR.zip` was copied byte-for-byte to `ToCASR/OSworld_ASR.zip` before inspection; both copies have SHA-256 `fcf1fca8ae84974f3cea761ed3558c61186f3162e7d0734f034deb87b6ac18c4`.
- `OSworld_ASR.zip` contributes only Parakeet and Qwen with/without-bias conditions. Its additional Whisper run is explicitly excluded. Four canonical 1,755-row JSONL files were generated from successful records; retry failures, per-item text copies, and run logs are not formal dataset rows.
- The consolidated dataset is public at `tterumiimurett1/agentic-asr`, current verified revision `de19aa31572449686166680810468dea86608329`.
- Four OSWorld human-recording ontology variants for Parakeet TDT 0.6B v2 and Qwen2.5-Omni-7B were generated with `gpt-5.6-luna`; bias precedes ontology in biased condition names.
- Four WildClawBench human-recording ontology variants for Parakeet CTC and Qwen Omni were generated from raw ASR with `gpt-5.6-luna` (600/600/507/507 rows). The two old 60-row Parakeet `01男` GPT-5.4 outputs were not reused. All other pre-existing ontology-fix results remain attributed to GPT-5.4.
- Latest remote readback verified 4,256 paths including Hugging Face's generated `.gitattributes`. The ten newly uploaded or updated files, including four ontology aggregates, the prompt, provenance, Dataset Card, and repository indexes, matched the local staging tree byte-for-byte.
- After remote verification, the four covered OSWorld transcript directories were deleted: 7,020 per-recording Markdown files in total. The four canonical JSONL files and all README/WER/dataset reports remain.
- The benchmark-focused repository changes were published to GitHub branch `origin/prompt-overrides`. Local dataset roots and ToCASR production-pipeline code are excluded by the root `.gitignore`.
- GitHub pins the public Dataset through `configs/datasets/agentic-asr.lock.json`; the lock contains the immutable revision, integrity roots, logical entrypoints, and local-to-Hugging-Face mapping, but no dataset payload.
- A final independent audit revalidated all 7,020 deleted transcript Markdown files from the pre-deletion archive and revalidated the pinned Hugging Face revision. Its verdict is `PASS`.

## Open decisions

- Whether future pipeline runs write Transcript Artifacts into ignored working directories or write Canonical Transcript Records directly.
- Whether the existing public `colloqialized_prompt` repository later adopts the consolidated dataset's repository-relative audio paths.
- Whether task images and each derived-audio family have sufficient licensing for eventual public release.
- The macOS Execution Host accelerator, persistent-storage allocation, and network access.
- The reproducible macOS benchmark bootstrap format and ownership of benchmark caches.

## Session documents

- [Agentic ASR dataset lock](../../../configs/datasets/agentic-asr.lock.json)
- [Context and glossary](./CONTEXT.md)
- [Transcript coverage evidence](./evidence/transcript-jsonl-coverage.md)
- [Hugging Face dataset inventory](./evidence/hugging-face-dataset-inventory.md)
- [Execution Host portability audit](./evidence/execution-host-portability.md)
- [`task0_template` usage audit](./evidence/task0-template-usage.md)
- [OSWorld ASR ZIP import audit](./evidence/osworld-asr-zip-import.md)
- [Hugging Face publication readback](./evidence/hugging-face-publication-readback.md)
- [Final independent publication audit](./evidence/final-independent-publication-audit.md)
- [WildClawBench human-recordings publication](./evidence/wildclawbench-human-recordings-publication.md)
- [WildClawBench human ontology-fix publication](./evidence/wildclawbench-human-ontology-publication.md)
- [Code and dataset publication boundary](./adr/0001-separate-code-and-dataset-publication.md)
- [Consolidated private dataset publication](./adr/0002-consolidate-private-dataset-publication.md)
- [Rebuild only the benchmark on the Execution Host](./adr/0003-rebuild-benchmark-on-macos-execution-host.md)
- [Separate OSWorld and WildClawBench dataset families](./adr/0004-separate-osworld-and-wildclawbench-families.md)
