# WildClawBench human ontology-fix publication

Verified on 2026-09-21 against public Hugging Face dataset `tterumiimurett1/agentic-asr`, immutable revision `de19aa31572449686166680810468dea86608329`.

## Model-version boundary

- GPT-5.6 Luna: OSWorld human-recording Parakeet and Qwen ontology fixes, and all four WildClawBench human-recording Parakeet and Qwen ontology fixes (with and without bias).
- GPT-5.4: other pre-existing ontology-fix results.
- The prior Parakeet `01男` 60-row ontology files in each bias condition were historical GPT-5.4 outputs. This run used raw ASR as input for all 600 Parakeet rows in each condition, including those 60; it did not read or reuse the old normalized outputs. Their historical checksums are recorded in the published manifest.

The normalization prompt is published at `wildclawbench/human_recordings/asr/ontology_fix_prompt.md` (SHA-256 `36ea5ad12ccf313be185a3cb187e63984c08b66eabf6c4ccccf6046de74dffe7`). `ontology_fix_manifest.json` records the ByteDance ModelHub provider, exact `gpt-5.6-luna` model, API version and endpoint, prompt hash, run settings, input/output hashes, and the three long-transcript exceptions handled in chunks by the same model. The API credential is neither recorded nor published.

## Published aggregates

| Condition | Rows | Published file | SHA-256 |
| --- | ---: | --- | --- |
| Parakeet, no bias | 600 | `wildclawbench/human_recordings/asr/parakeet/all-asr-data_parakeet-ctc_typeless-ontology-fix.json` | `3861e0852a181401e997a5ce97699733c581a243b7d951123d5688c0bc3840df` |
| Parakeet, bias | 600 | `wildclawbench/human_recordings/asr/parakeet/all-asr-data_parakeet-ctc_bias_typeless-ontology-fix.json` | `a662f6452453d66006f72eab56012c5fd797c319f680363ce9ef65888b41272b` |
| Qwen, no bias | 507 | `wildclawbench/human_recordings/asr/qwen/all-asr-data_qwen-omni_typeless-ontology-fix.json` | `fa092f95897619894a86c111541f1c139e403045e093b4d8c077e6e08289e9c6` |
| Qwen, bias | 507 | `wildclawbench/human_recordings/asr/qwen/all-asr-data_qwen-omni_bias_typeless-ontology-fix.json` | `734f1307dcbf27054419d1b69911ce045c55c2f4f5c1662fa549074d953903a5` |

All four outputs preserve every non-transcription source field, retain unique audio paths and nonempty transcript text, and match their published source/output checksums. Qwen is the pre-existing cleaned 507-recording subset; Parakeet remains the complete 600-recording set. The four dataset condition records explicitly identify `normalizer_model: gpt-5.6-luna`.

## Remote readback

The public revision has 4,256 paths, 4,254 indexed files, 48 conditions, and 53 Dataset Card viewer configurations. After the atomic Hugging Face commit, all ten submitted paths were downloaded at the immutable revision and compared byte-for-byte to the staging tree: four ASR aggregates, ontology manifest, normalization prompt, updated import manifest, Dataset Card, condition index, and file index. All ten matched. The GitHub data lock was updated to this revision and the new manifest hashes.
