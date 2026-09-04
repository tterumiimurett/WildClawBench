---
status: accepted
---

# Rebuild only the benchmark on the macOS Execution Host

The dataset-generation pipeline and its model environment will not be migrated to the Execution Host or published as part of the WildClawBench GitHub repository because they belong to a separate data-production project. Finalized audio and ASR records are distributed through Hugging Face, while the benchmark is reconstructed independently from the GitHub checkout on the user's macOS server; local virtual environments and model caches are not copied.
