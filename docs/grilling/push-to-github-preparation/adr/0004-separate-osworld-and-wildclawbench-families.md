---
status: accepted
---

# Separate OSWorld and WildClawBench dataset families

The consolidated private ASR dataset separates local ToCASR assets into an `OSWorld` family and local `colloqialized_prompt` assets into a `WildClawBench` family. Both families reserve parallel synthetic-audio and human-recording structure so future WildClawBench human recordings can be added without changing the dataset's conceptual hierarchy or conflating different task sources.

Each family also reserves a family-scoped `bias_lists/` collection. Bias-assisted ASR conditions refer to a versioned Bias List from either synthetic or human-recording data. No placeholder bias-list payload is published before the real artifact is available.
