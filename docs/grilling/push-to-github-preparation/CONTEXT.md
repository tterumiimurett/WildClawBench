# ASR Dataset Publication

This context defines the durable assets and intermediate artifacts involved in publishing WildClawBench ASR data and its supporting code.

## Language

**Source Audio**:
An immutable audio input obtained from a declared source and used as the basis for transcription or transformation.
_Avoid_: Raw file, original file

**Derived Audio**:
Audio produced from Source Audio or task text by synthesis, degradation, normalization, or another reproducible transformation.
_Avoid_: Generated file, processed file

**Transcript Artifact**:
A per-item Markdown file emitted during transcription or normalization as an intermediate working representation.
_Avoid_: Markdown result, main transcription

**Canonical Transcript Record**:
A structured record that preserves a transcript together with the stable identity and provenance needed to validate and reuse it.
_Avoid_: JSON output, consolidated file

**Coverage Proof**:
Machine-checked evidence that every Transcript Artifact maps to exactly one Canonical Transcript Record with the same stable identity and transcript payload under a declared serialization convention.
_Avoid_: File-count check, spot check

**Dataset Manifest**:
A metadata-only index that identifies canonical data files and records their model condition, transcript variant, row count, checksum, and audio root without copying transcript payloads.
_Avoid_: Merged transcript table, duplicate JSONL

**Bias List**:
A versioned, family-scoped artifact containing the contextual vocabulary or phrases supplied to an ASR condition. Bias-assisted result metadata references its Bias List by stable identity rather than embedding an unexplained copy.
_Avoid_: Bias prompt, keyword file

**Code Repository**:
The versioned home for executable code, small configuration, schemas, documentation, and reproducibility metadata.
_Avoid_: GitHub data repository

**Dataset Repository**:
The versioned home for Source Audio, Derived Audio, Canonical Transcript Records, and dataset-level metadata.
_Avoid_: Audio folder, large-file repository

**Execution Host**:
A remote machine that reconstructs the project from versioned code and dataset assets and performs model execution outside the local workstation.
_Avoid_: Backup server, copied environment

**Runtime Cache**:
Replaceable model weights, package caches, and generated runtime state used by an Execution Host but not treated as canonical project data.
_Avoid_: Model dataset, repository files

**OSWorld Dataset Family**:
The publication identity for assets currently stored under the local `ToCASR/` tree, including synthetic and human-recording conditions derived from OSWorld tasks.
_Avoid_: ToCASR dataset, 2C ASR

**WildClawBench Dataset Family**:
The publication identity for assets currently stored under the local `colloqialized_prompt/` tree, with parallel space for synthetic and future human-recording conditions.
_Avoid_: WER Bench Dataset Family, Colloquialized Prompt dataset

**Agentic ASR Dataset**:
The private Hugging Face Dataset repository `tterumiimurett1/agentic-asr` that contains the OSWorld and WildClawBench Dataset Families without merging their task identities or benchmark provenance.
_Avoid_: Agentec ASR, WER Bench ASR
