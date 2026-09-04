# `task0_template` Usage Audit

This is a read-only trace of `task0_template.md` through the benchmark and the
historical `colloqialized_prompt` artifact pipeline.

## Benchmark execution

The normal WildClawBench category runner does not execute the template.

- `eval/run_batch.py` defines exactly six category directories in
  `ALL_CATEGORIES`.
- For a category run, it searches only
  `tasks/<category>/*task_*.md`.
- `tasks/task0_template.md` is at the root of `tasks/`, outside all six category
  directories.
- The six category directories contain 60 task files in total; the repository
  README separately describes `tasks/task0_template.md` as the annotated
  starting point for creating new tasks.

Therefore `--category all` runs 60 benchmark tasks and never selects
`task0_template.md`. A user could explicitly pass the template to `--task`, but
that is not a valid benchmark run: its ID and workspace path are placeholders.

Prompt overrides follow the path of each already-selected canonical task.
Consequently `colloqialized_prompt/tasks_modified/task0_template.md` is also
not selected by a normal 60-task prompt-override run.

## Historical data-generation path

The template was nevertheless processed by the old dataset pipeline because
the batch selectors did not exclude it:

1. `generate_dataset.py extract` recursively selected every Markdown file
   under `tasks/`, producing `tasks_clean/task0_template.md`.
2. The generate stage recursively selected every clean Markdown file,
   producing `tasks_modified/task0_template.md`.
3. The TTS stage recursively selected every modified Markdown file, producing
   `tasks_tts/task0_template.wav`.
4. Both ASR entry points recursively selected every WAV under `tasks_tts/`, so
   they also selected the template audio.
5. Transcript normalization recursively selected every raw-ASR Markdown file.

The committed template WAV is valid 24 kHz, 16-bit mono PCM, lasts 36.9875
seconds, and is 1,775,444 bytes. The Hugging Face repository commit contains
three corresponding template transcripts:

- GPT-4o raw
- Whisper V3 raw
- Whisper V3 typeless/normalized

There is no GPT-4o typeless template transcript because that condition only has
a partial 20-task output set.

## Aggregate JSON boundary

The current aggregate JSON files contain only the 60 formal benchmark tasks.
Their records use the six benchmark category names and category-relative audio
paths. None contains `task0_template`. This is why the three template
transcripts are the only locally deleted ASR Markdown files without an
aggregate JSON counterpart.

## Interpretation

`task0_template` is a reusable authoring fixture, not benchmark data. Its clean
Markdown source remains useful as documentation, but its colloquialized text,
TTS audio, and ASR transcripts are accidental pipeline products caused by broad
recursive file discovery. They are not needed to reproduce the 60-task WER
Bench dataset or to run WildClawBench.

## Decision

The user confirmed that `task0_template` is not formal data and does not need
to be retained as dataset content. Its derived prompt, TTS, and ASR artifacts
are excluded from canonical WildClawBench publication and do not need a JSON
replacement before cleanup. The authoring template under the benchmark's
`tasks/` directory remains part of the GitHub code/documentation surface.
