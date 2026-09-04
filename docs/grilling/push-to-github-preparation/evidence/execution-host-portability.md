# Execution Host Portability Audit

This audit identified what must be versioned or reconstructed before WildClawBench workloads move from the local workstation to the user's macOS Execution Host. The final scope decision is narrower than the initial audit.

## Reconstruction boundary

The 19 GB local working tree and `.venv-asr` are not portable deployment units. An Execution Host should reconstruct the project from:

1. a GitHub code checkout at a fixed revision;
2. Hugging Face datasets at fixed revisions, downloaded into declared data directories;
3. separately downloaded benchmark Docker images and task workspaces;
4. a newly created, pinned Python environment;
5. model weights downloaded into a server-side Runtime Cache; and
6. secrets supplied through a server secret store or untracked `.env` file.

## Observed benchmark prerequisites

- A Docker-capable macOS host, Python 3, FFmpeg, `yt-dlp`, and Hugging Face download tooling.
- Root requirements currently include WeasyPrint, PyMuPDF, Requests, `yt-dlp`, ModelScope, `python-dotenv`, and PyYAML.
- ToCASR additionally uses OpenAI, Faster Whisper, and JiWER, but only JiWER is declared in `ToCASR/requirements-wer.txt`.
- Benchmark preparation separately downloads selected Docker images, task workspaces, media, and model weights.

## Portability blockers

- `ToCASR/get_data.py` contains a hard-coded `/mnt/bn/...` source path.
- Several ToCASR scripts import helpers from the ignored nested `colloqialized_prompt/scripts` tree.
- There is no complete pinned ASR dependency manifest or lockfile.
- The local `.venv-asr` targets macOS arm64 and cannot be copied to a Linux server.
- ASR and TTS paths include internal endpoints and require server-side credentials and suitable network access.
- Faster Whisper downloads `deepdml/faster-whisper-large-v3-turbo-ct2` into a model cache by default.

## Final workload boundary

**`benchmark` profile**:
Docker daemon, harness images, task workspaces, benchmark assets, and benchmark Python dependencies.

**Finalized dataset assets**:
Download audio and ASR records from the pinned private Hugging Face Dataset. The
ToCASR production pipeline, its model runtime, internal endpoints, local virtual
environment, and model caches do not move to the Execution Host.

This keeps the GitHub checkout benchmark-focused while the dataset is downloaded
separately as immutable input data.
