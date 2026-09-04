# Hugging Face Publication Readback

## Published target

- Dataset: `tterumiimurett1/agentic-asr`
- Visibility: private
- Verified revision: `f275a3da8a38403aefa7ab5f741c9b3a3c541a1d`
- Uploaded payload: approximately 1.7 GB

The dataset card exposes 41 configurations across parallel `osworld/` and
`wildclawbench/` families. The condition manifest contains 36 ASR conditions.
Ten bias-assisted conditions are marked `bias_list_status: pending` because the
underlying Bias List files have not yet been supplied.

## Remote readback result

The authenticated Hub API reported `private: true`. Recursive tree comparison
found all 3,637 staged paths plus one platform-generated `.gitattributes` file,
with no missing staged path.

- 3,570 remote LFS media objects matched the local file size and SHA-256.
- All 67 staged JSON, JSONL, and Markdown files were downloaded at the pinned
  revision and matched the staged bytes exactly.
- All 41 dataset-card data-file paths exist in the published tree.
- All WildClawBench aggregate transcript strings remain exact; only their stale
  `data/tasks_tts/...` audio paths were rewritten to published relative paths.

## OSWorld ZIP boundary

The supplied ZIP contributed exactly four canonical conditions: Parakeet TDT
0.6B v2 and Qwen2.5-Omni-7B, each with and without biasing. Each condition has
1,755 rows. The ZIP's additional Whisper run, failed retry rows, per-recording
text copies, and runtime logs were not uploaded.

The pre-existing OSWorld Whisper v3 JSONLs remain as separately produced
conditions; they are not the additional Whisper run from the supplied ZIP.
