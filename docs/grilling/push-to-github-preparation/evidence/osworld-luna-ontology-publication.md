# OSWorld Luna Ontology Publication

- Hugging Face dataset: `tterumiimurett1/agentic-asr` (public)
- Verified revision: `93e7056b503d3bfd2124ebf0953cd93ac79287eb`
- Commit: `osworld: add Parakeet and Qwen Luna ontology variants`
- Normalizer: ByteDance ModelHub `gpt-5.6-luna`
- Prompt SHA-256: `36ea5ad12ccf313be185a3cb187e63984c08b66eabf6c4ccccf6046de74dffe7`

Four OSWorld human-recording conditions were added: Parakeet and Qwen, each
with unbiased ontology and bias-plus-ontology variants. Every condition has
1,755 rows and 1,755 unique task IDs. All non-transcript fields match the
corresponding raw source row, and all transcripts are non-empty.

Exact input-text deduplication reduced 7,020 source rows to 3,333 Luna calls.
The remote readback downloaded all nine files in the incremental commit and
matched each one byte-for-byte. The published repository contains 3,645 paths,
the file index contains 3,643 payload rows, the condition manifest contains 40
conditions, and the dataset card exposes 45 viewer configurations.
