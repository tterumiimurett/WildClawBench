---
status: accepted
---

# Separate code and dataset publication

WildClawBench publishes executable code, small configuration, schemas, documentation, and reproducibility metadata through GitHub, while audio, canonical transcript records, and dataset-level artifacts belong in Hugging Face Dataset repositories. This boundary keeps Git history cloneable without discarding the versioning, provenance, and validation required for the datasets; local transcript intermediates are deleted only after the corresponding private Hugging Face publication passes remote readback.
