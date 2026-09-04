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
- A new private Hugging Face Dataset is the consolidated publication target for both `colloqialized_prompt` and ToCASR content, separated by explicit dataset configurations.
- The existing public `colloqialized_prompt` repository remains unchanged until the consolidated private dataset has been verified and its later disposition is decided.
- The four original human-recording JSONL files remain preserved; their covered per-item Markdown may be deleted only after Hugging Face upload and remote readback succeed.
- ToCASR pipeline code is outside the WildClawBench GitHub publication scope because it belongs to a separate data-production project.
- The consolidated private dataset is named `Agentic ASR`, with the target Hugging Face repository slug `tterumiimurett1/agentic-asr`.
- Local `ToCASR/` assets publish under the `OSWorld` dataset family; local `colloqialized_prompt/` assets publish under the `WildClawBench` dataset family.
- Both dataset families reserve parallel structure for synthetic audio and human recordings, even though WildClawBench human recordings will be added later.
- `task0_template` is not formal WildClawBench data. Its derived clean/modified text, TTS audio, and ASR transcripts are excluded from publication and do not require conversion into canonical JSON.
- The four original OSWorld human-recording JSONL files are the sole transcript copies for those conditions. A small manifest and Hugging Face configuration may describe their model, variant, row count, checksum, and audio root, but must not duplicate transcript payloads.
- Each dataset family has a `bias_lists/` collection at family scope so synthetic and future human-recording ASR conditions reference the same versioned biasing scheme.
- The eight WildClawBench `_bias` conditions reference `WCB_task_details_biasing.json`; the two OSWorld biased human-recording conditions reference `OSWorld_biasing_list.json`. All ten are marked `bias_list_status: available` with source SHA-256 values.
- The supplied `OSworld_ASR.zip` was copied byte-for-byte to `ToCASR/OSworld_ASR.zip` before inspection; both copies have SHA-256 `fcf1fca8ae84974f3cea761ed3558c61186f3162e7d0734f034deb87b6ac18c4`.
- `OSworld_ASR.zip` contributes only Parakeet and Qwen with/without-bias conditions. Its additional Whisper run is explicitly excluded. Four canonical 1,755-row JSONL files were generated from successful records; retry failures, per-item text copies, and run logs are not formal dataset rows.
- The consolidated dataset is published privately at `tterumiimurett1/agentic-asr`, current verified revision `794a16d0513b5f4b9f4e644465fcb31352331e16`.
- Final remote readback verified 3,640 paths including Hugging Face's generated `.gitattributes`. The 3,570 LFS media objects remain unchanged, and all eight files in the Bias List increment matched byte-for-byte.
- After remote verification, the four covered OSWorld transcript directories were deleted: 7,020 per-recording Markdown files in total. The four canonical JSONL files and all README/WER/dataset reports remain.
- The benchmark-focused repository changes were published to GitHub branch `origin/prompt-overrides`. Local dataset roots and ToCASR production-pipeline code are excluded by the root `.gitignore`.

## Open decisions

- Whether future pipeline runs write Transcript Artifacts into ignored working directories or write Canonical Transcript Records directly.
- Whether the existing public `colloqialized_prompt` repository later adopts the consolidated dataset's repository-relative audio paths.
- Whether task images and each derived-audio family have sufficient licensing for eventual public release.
- The macOS Execution Host accelerator, persistent-storage allocation, and network access.
- The reproducible macOS benchmark bootstrap format and ownership of benchmark caches.

## Session documents

- [Context and glossary](./CONTEXT.md)
- [Transcript coverage evidence](./evidence/transcript-jsonl-coverage.md)
- [Hugging Face dataset inventory](./evidence/hugging-face-dataset-inventory.md)
- [Execution Host portability audit](./evidence/execution-host-portability.md)
- [`task0_template` usage audit](./evidence/task0-template-usage.md)
- [OSWorld ASR ZIP import audit](./evidence/osworld-asr-zip-import.md)
- [Hugging Face publication readback](./evidence/hugging-face-publication-readback.md)
- [Code and dataset publication boundary](./adr/0001-separate-code-and-dataset-publication.md)
- [Consolidated private dataset publication](./adr/0002-consolidate-private-dataset-publication.md)
- [Rebuild only the benchmark on the Execution Host](./adr/0003-rebuild-benchmark-on-macos-execution-host.md)
- [Separate OSWorld and WildClawBench dataset families](./adr/0004-separate-osworld-and-wildclawbench-families.md)
