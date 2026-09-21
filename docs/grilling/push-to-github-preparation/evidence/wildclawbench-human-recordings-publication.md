# WildClawBench Human Recordings Publication

- Hugging Face dataset: `tterumiimurett1/agentic-asr` (public)
- Verified revision: `daaf90531993bf8564cd222a6b520f8300b5c2aa`
- Remote paths: 4,250
- Indexed payload files: 4,248
- Indexed payload bytes: 4,621,065,494

The WildClawBench human-recordings collection contains 600 original audio
files from 10 participants, with 60 files per participant. Parakeet's biased
and unbiased aggregates retain the unfiltered 600-file set. Qwen's biased and
unbiased aggregates use the same cleaned 507-file subset: 93 recordings were
removed as dirty data before import. The supplied metadata does not state the
dirty-data exclusion criteria.

Remote readback checked all 600 audio objects using their Hugging Face LFS
SHA-256 values and found zero mismatches. The four ASR aggregates, import
manifest, Dataset Card, `metadata/conditions.jsonl`, and
`metadata/files.jsonl` were downloaded at the pinned revision and matched the
local publication tree byte-for-byte.

The repository-wide condition manifest now has 44 rows, the Dataset Card has
49 viewer configurations, and the file index has 4,248 rows. The two files
outside the file index are `.gitattributes` and `metadata/files.jsonl` itself.

An upload-boundary comparison against the preceding revision found 605 added
files, no removed files, and only three changed existing indexed files: the
Dataset Card, the condition manifest, and one OSWorld import manifest. The
OSWorld manifest change corrects its Bias List reference from the ambiguous
`bias_lists/OSWorld_biasing_list.json` to the repository-root-relative
`osworld/bias_lists/OSWorld_biasing_list.json`; no existing audio or ASR payload
was changed.
