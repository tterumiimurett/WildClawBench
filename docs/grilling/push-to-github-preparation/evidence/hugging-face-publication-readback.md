# Hugging Face Publication Readback

## Published target

- Dataset: `tterumiimurett1/agentic-asr`
- Visibility: private
- Current verified revision: `794a16d0513b5f4b9f4e644465fcb31352331e16`
- Uploaded payload: approximately 1.7 GB

The dataset card exposes 41 configurations across parallel `osworld/` and
`wildclawbench/` families. The condition manifest contains 36 ASR conditions.
Ten bias-assisted conditions are marked `bias_list_status: available` and
reference their family-scoped Bias List path and SHA-256.

## Remote readback result

The authenticated Hub API reported `private: true`. The initial recursive tree
comparison found all 3,637 staged paths plus one platform-generated
`.gitattributes` file, with no missing staged path.

- 3,570 remote LFS media objects matched the local file size and SHA-256.
- All 67 staged JSON, JSONL, and Markdown files were downloaded at the pinned
  revision and matched the staged bytes exactly.
- All 41 dataset-card data-file paths exist in the published tree.
- All WildClawBench aggregate transcript strings remain exact; only their stale
  `data/tasks_tts/...` audio paths were rewritten to published relative paths.

## Bias List follow-up

Two supplied files were added in an eight-file incremental commit:

- `osworld/bias_lists/OSWorld_biasing_list.json`: 351/351 tasks, SHA-256
  `797ab1863b645bebca8776c5e699f600da49f9d54f402f74630239b605521d58`.
- `wildclawbench/bias_lists/WCB_task_details_biasing.json`: 60/60 formal tasks,
  3,119 task-local unique terms, SHA-256
  `052d04975c5fc9cab2a569672b7f8f5ad4877d8f03c862eb78895cce491f6d6a`.

At revision `794a16d0513b5f4b9f4e644465fcb31352331e16`, remote readback
verified 3,640 paths: 3,639 dataset payload files plus the Hub-generated
`.gitattributes`. All eight incremental files matched byte-for-byte, all 3,570
previous LFS media objects remained present, all ten biased conditions were
`available`, and no `pending` condition remained.

## OSWorld ZIP boundary

The supplied ZIP contributed exactly four canonical conditions: Parakeet TDT
0.6B v2 and Qwen2.5-Omni-7B, each with and without biasing. Each condition has
1,755 rows. The ZIP's additional Whisper run, failed retry rows, per-recording
text copies, and runtime logs were not uploaded.

The pre-existing OSWorld Whisper v3 JSONLs remain as separately produced
conditions; they are not the additional Whisper run from the supplied ZIP.
