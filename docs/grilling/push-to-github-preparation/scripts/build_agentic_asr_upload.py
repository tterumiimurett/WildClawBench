#!/usr/bin/env python3
"""Build the curated Agentic ASR Hugging Face upload tree.

Large media files are hard-linked into a temporary staging tree so this step
does not consume a second copy of the payload on the local disk.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
STAGE = Path("/private/tmp/agentic-asr-upload")
TOCASR = ROOT / "ToCASR"
WILDCLAW = ROOT / "colloqialized_prompt"
DNS = ROOT / "final_dataset" / "dns-noise-wer10"
OSWORLD_BIAS_SOURCE = TOCASR / "bias_lists" / "OSWorld_biasing_list.json"
WILDCLAW_BIAS_SOURCE = WILDCLAW / "bias_lists" / "WCB_task_details_biasing.json"
OSWORLD_BIAS_PATH = "osworld/bias_lists/OSWorld_biasing_list.json"
WILDCLAW_BIAS_PATH = "wildclawbench/bias_lists/WCB_task_details_biasing.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_file(source: Path, target: Path) -> None:
    require(source.is_file(), f"missing source file: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


PATH_REPLACEMENTS = (
    (r"/Users/[^/]+/Documents/playground/WildClawBench/ToCASR/raw_instruction/instructions\.jsonl", "osworld/synthetic/raw_instruction/instructions.jsonl"),
    (r"/Users/[^/]+/Documents/playground/WildClawBench/ToCASR/raw_instruction/tasks_asr", "osworld/synthetic/raw_instruction/asr"),
    (r"/Users/[^/]+/Documents/playground/WildClawBench/ToCASR/colloquial_instruction/tasks_asr", "osworld/synthetic/colloquial_instruction/asr"),
    (r"/Users/[^/]+/Documents/playground/WildClawBench/ToCASR/recorded_instruction/task_config\.json", "osworld/human_recordings/task_config.json"),
    (r"/Users/[^/]+/Documents/playground/WildClawBench/ToCASR/recorded_instruction/tasks_asr", "osworld/human_recordings/asr"),
    (r"/Users/[^/]+/Documents/playground/WildClawBench/ToCASR/task_config\.json", "osworld/metadata/task_config.json"),
    (r"/Users/[^/]+/miniconda3/bin/python", "python3"),
)


def copy_sanitized_text(source: Path, target: Path) -> None:
    require(source.is_file(), f"missing source text file: {source}")
    text = source.read_text(encoding="utf-8")
    for pattern, replacement in PATH_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def hardlink_file(source: Path, target: Path) -> None:
    require(source.is_file(), f"missing source media: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    os.link(source, target)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid JSONL at {path}:{number}: {exc}") from exc
            require(isinstance(value, dict), f"non-object JSONL row at {path}:{number}")
            rows.append(value)
    return rows


def strip_one_final_newline(text: str) -> str:
    if text.endswith("\r\n"):
        return text[:-2]
    if text.endswith("\n"):
        return text[:-1]
    return text


configs: list[dict[str, Any]] = []
conditions: list[dict[str, Any]] = []


def add_config(name: str, data_file: Path) -> None:
    require(re.fullmatch(r"[a-z0-9][a-z0-9._-]*", name) is not None, f"bad config: {name}")
    relative = data_file.relative_to(STAGE).as_posix()
    require(not any(item["config_name"] == name for item in configs), f"duplicate config: {name}")
    configs.append(
        {
            "config_name": name,
            "data_files": [{"split": "data", "path": relative}],
        }
    )


def add_condition(
    *,
    family: str,
    collection: str,
    model: str,
    variant: str,
    biasing: bool,
    data_file: Path,
    audio_root: str,
    rows: int,
    source_fidelity: str,
) -> None:
    condition = {
        "family": family,
        "collection": collection,
        "model": model,
        "variant": variant,
        "biasing": biasing,
        "bias_list_status": "not_applicable",
        "data_file": data_file.relative_to(STAGE).as_posix(),
        "audio_root": audio_root,
        "rows": rows,
        "sha256": sha256(data_file),
        "source_fidelity": source_fidelity,
    }
    if biasing:
        if family == "osworld":
            condition["bias_list"] = OSWORLD_BIAS_PATH
            condition["bias_list_sha256"] = sha256(OSWORLD_BIAS_SOURCE)
        elif family == "wildclawbench":
            condition["bias_list"] = WILDCLAW_BIAS_PATH
            condition["bias_list_sha256"] = sha256(WILDCLAW_BIAS_SOURCE)
        else:
            raise RuntimeError(f"unknown biased family: {family}")
        condition["bias_list_status"] = "available"
    conditions.append(condition)


def stage_osworld_synthetic() -> None:
    for source_name, destination_name in (
        ("raw_instruction", "raw_instruction"),
        ("colloquial_instruction", "colloquial_instruction"),
    ):
        source_root = TOCASR / source_name
        target_root = STAGE / "osworld" / "synthetic" / destination_name
        audio_files = sorted((source_root / "audio").glob("*.wav"))
        require(len(audio_files) == 351, f"expected 351 {source_name} WAV files")
        for source in audio_files:
            hardlink_file(source, target_root / "audio" / source.name)

        instructions = target_root / "instructions.jsonl"
        copy_file(source_root / "instructions.jsonl", instructions)
        require(len(read_jsonl(instructions)) == 351, f"expected 351 {source_name} instructions")
        add_config(f"osworld-synthetic-{destination_name.replace('_', '-')}-instructions", instructions)

        for source in sorted((source_root / "tasks_asr").glob("*/*.jsonl")):
            relative = source.relative_to(source_root / "tasks_asr")
            target = target_root / "asr" / relative
            copy_file(source, target)
            rows = len(read_jsonl(target))
            require(rows == 351, f"expected 351 rows in {source}")
            model = relative.parent.name
            variant = relative.stem
            config_name = "-".join(
                (
                    "osworld",
                    "synthetic",
                    destination_name.replace("_", "-"),
                    model.replace("_", "-"),
                    variant.replace("_", "-"),
                )
            )
            add_config(config_name, target)
            add_condition(
                family="osworld",
                collection=f"synthetic/{destination_name}",
                model=model,
                variant=variant,
                biasing=False,
                data_file=target,
                audio_root=(target_root / "audio").relative_to(STAGE).as_posix(),
                rows=rows,
                source_fidelity="byte_identical_copy",
            )

        reports = target_root / "reports"
        copy_sanitized_text(source_root / "tasks_asr" / "wer_report.json", reports / "wer_report.json")
        copy_sanitized_text(source_root / "tasks_asr" / "wer_report.md", reports / "wer_report.md")


def stage_osworld_human() -> None:
    source_root = TOCASR / "recorded_instruction"
    target_root = STAGE / "osworld" / "human_recordings"

    audio_files = sorted((source_root / "source" / "All Recordings").glob("*.mp3"))
    require(len(audio_files) == 1755, "expected 1,755 OSWorld human MP3 files")
    for source in audio_files:
        hardlink_file(source, target_root / "source" / "All Recordings" / source.name)

    for relative in (
        Path("manifest.jsonl"),
        Path("source_metadata.json"),
        Path("task_config.json"),
    ):
        copy_file(source_root / relative, target_root / relative)
    copy_sanitized_text(source_root / "README.md", target_root / "README.md")
    copy_sanitized_text(source_root / "source" / "README.md", target_root / "source" / "README.md")
    manifest_target = target_root / "manifest.jsonl"
    require(len(read_jsonl(manifest_target)) == 1755, "expected 1,755 human manifest rows")
    add_config("osworld-human-recordings-manifest", manifest_target)

    selected = (
        Path("gpt-4o-transcribe/raw_asr.jsonl"),
        Path("gpt-4o-transcribe/typeless_ontology_fix.jsonl"),
        Path("whisper_v3/raw_asr.jsonl"),
        Path("whisper_v3/typeless_ontology_fix.jsonl"),
        Path("parakeet_tdt_0.6b_v2/raw_asr.jsonl"),
        Path("parakeet_tdt_0.6b_v2/raw_asr_bias.jsonl"),
        Path("qwen2.5_omni_7b/raw_asr.jsonl"),
        Path("qwen2.5_omni_7b/raw_asr_bias.jsonl"),
    )
    for relative in selected:
        source = source_root / "tasks_asr" / relative
        target = target_root / "asr" / relative
        copy_file(source, target)
        require(source.read_bytes() == target.read_bytes(), f"copy changed bytes: {source}")
        rows = len(read_jsonl(target))
        require(rows == 1755, f"expected 1,755 rows in {source}")
        model = relative.parent.name
        variant = relative.stem
        biased = variant.endswith("_bias")
        add_config(
            "-".join(
                (
                    "osworld",
                    "human",
                    model.replace("_", "-"),
                    variant.replace("_", "-"),
                )
            ),
            target,
        )
        add_condition(
            family="osworld",
            collection="human_recordings",
            model=model,
            variant=variant,
            biasing=biased,
            data_file=target,
            audio_root="osworld/human_recordings/source/All Recordings",
            rows=rows,
            source_fidelity="byte_identical_copy",
        )

    metadata = target_root / "metadata"
    import_manifest = json.loads(
        (source_root / "tasks_asr" / "osworld_asr_import_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    import_manifest["bias_list"] = OSWORLD_BIAS_PATH
    write_json(metadata / "osworld_asr_import_manifest.json", import_manifest)
    copy_file(
        source_root / "tasks_asr" / "gpt-4o-transcribe" / "reference_validation_overrides.jsonl",
        metadata / "reference_validation_overrides.jsonl",
    )
    reports = target_root / "reports"
    copy_sanitized_text(source_root / "tasks_asr" / "wer_report.json", reports / "wer_report.json")
    copy_sanitized_text(source_root / "tasks_asr" / "wer_report.md", reports / "wer_report.md")


def stage_osworld_dns_noise() -> None:
    target_root = STAGE / "osworld" / "dns_noise_wer10"
    source_manifest = read_jsonl(DNS / "manifest.jsonl")
    raw_instructions = {
        row["task_id"]: row["instruction"]
        for row in read_jsonl(DNS / "instructions" / "raw.jsonl")
    }
    colloquial_instructions = {
        row["task_id"]: row["colloquialized_instruction"]
        for row in read_jsonl(DNS / "instructions" / "colloquial.jsonl")
    }
    evaluations = {
        row["task_id"]: row
        for row in read_jsonl(DNS / "evaluation" / "combined" / "tasks.jsonl")
    }
    require(len(source_manifest) == 351, "expected 351 DNS-noise manifest rows")
    require(len(raw_instructions) == 351, "expected 351 DNS raw instructions")
    require(len(colloquial_instructions) == 351, "expected 351 DNS colloquial instructions")
    require(len(evaluations) == 351, "expected 351 DNS combined evaluation rows")

    rows: list[dict[str, Any]] = []
    for source_row in source_manifest:
        task_id = source_row["task_id"]
        source_pair = DNS / "pairs" / task_id
        raw_source = source_pair / "raw.wav"
        colloquial_source = source_pair / "colloquial.wav"
        raw_target = target_root / "pairs" / task_id / "raw.wav"
        colloquial_target = target_root / "pairs" / task_id / "colloquial.wav"
        hardlink_file(raw_source, raw_target)
        hardlink_file(colloquial_source, colloquial_target)
        require(sha256(raw_source) == source_row["raw_sha256"], f"raw hash mismatch: {task_id}")
        require(
            sha256(colloquial_source) == source_row["colloquial_sha256"],
            f"colloquial hash mismatch: {task_id}",
        )
        evaluation = evaluations[task_id]
        rows.append(
            {
                "task_id": task_id,
                "split": source_row["split"],
                "raw_audio": raw_target.relative_to(STAGE).as_posix(),
                "colloquial_audio": colloquial_target.relative_to(STAGE).as_posix(),
                "raw_sha256": source_row["raw_sha256"],
                "colloquial_sha256": source_row["colloquial_sha256"],
                "raw_instruction": raw_instructions[task_id],
                "colloquial_instruction": colloquial_instructions[task_id],
                "transcription_state": source_row["transcription_state"],
                "asr_prediction": evaluation["prediction"],
                "reference": evaluation["reference"],
                "wer": evaluation["wer"],
                "substitutions": evaluation["substitutions"],
                "deletions": evaluation["deletions"],
                "insertions": evaluation["insertions"],
            }
        )
    records = target_root / "records.jsonl"
    write_jsonl(records, rows)
    add_config("osworld-dns-noise-wer10", records)

    copy_file(DNS / "REPORT.md", target_root / "reports" / "REPORT.md")
    copy_file(DNS / "state.json", target_root / "metadata" / "state.json")
    for source in sorted((DNS / "evaluation").glob("*/*")):
        if source.is_file():
            copy_file(source, target_root / "reports" / "evaluation" / source.relative_to(DNS / "evaluation"))


def stage_osworld_images() -> None:
    images = sorted((TOCASR / "images").glob("*.png"))
    require(len(images) == 351, "expected 351 OSWorld task images")
    for source in images:
        hardlink_file(source, STAGE / "osworld" / "task_images" / source.name)


def stage_osworld_shared_metadata() -> None:
    copy_file(TOCASR / "task_config.json", STAGE / "osworld" / "metadata" / "task_config.json")


def stage_wildclawbench() -> None:
    target_root = STAGE / "wildclawbench" / "synthetic"
    clean_root = WILDCLAW / "tasks_clean"
    modified_root = WILDCLAW / "tasks_modified"
    audio_root = WILDCLAW / "tasks_tts"
    clean_files = sorted(
        path for path in clean_root.rglob("*.md") if path.name != "task0_template.md"
    )
    require(len(clean_files) == 60, "expected 60 formal WildClawBench clean prompts")
    prompt_rows: list[dict[str, Any]] = []
    for clean in clean_files:
        relative = clean.relative_to(clean_root)
        modified = modified_root / relative
        audio = audio_root / relative.with_suffix(".wav")
        require(modified.is_file(), f"missing colloquial prompt: {modified}")
        require(audio.is_file(), f"missing TTS WAV: {audio}")
        target_audio = target_root / "audio" / relative.with_suffix(".wav")
        hardlink_file(audio, target_audio)
        prompt_rows.append(
            {
                "task_id": clean.stem,
                "category": relative.parent.as_posix(),
                "clean_prompt": strip_one_final_newline(clean.read_text(encoding="utf-8")),
                "colloquial_prompt": strip_one_final_newline(modified.read_text(encoding="utf-8")),
                "audio": target_audio.relative_to(STAGE).as_posix(),
            }
        )
    prompts = target_root / "prompts.jsonl"
    write_jsonl(prompts, prompt_rows)
    add_config("wildclawbench-synthetic-prompts", prompts)

    aggregate_files = sorted((WILDCLAW / "tasks_asr").glob("*/*.json"))
    require(len(aggregate_files) == 20, "expected 20 WildClawBench aggregate ASR JSON files")
    for source in aggregate_files:
        source_rows = json.loads(source.read_text(encoding="utf-8"))
        require(isinstance(source_rows, list) and len(source_rows) == 60, f"bad aggregate: {source}")
        transformed: list[dict[str, Any]] = []
        for row in source_rows:
            require(set(row) == {"audio", "category", "transcription"}, f"bad schema: {source}")
            old_audio = row["audio"]
            require(old_audio.startswith("data/tasks_tts/"), f"unexpected audio path: {old_audio}")
            relative_audio = Path(old_audio.removeprefix("data/tasks_tts/"))
            require((audio_root / relative_audio).is_file(), f"missing aggregate audio: {old_audio}")
            transformed.append(
                {
                    "audio": (target_root / "audio" / relative_audio).relative_to(STAGE).as_posix(),
                    "category": row["category"],
                    "transcription": row["transcription"],
                }
            )
        relative = source.relative_to(WILDCLAW / "tasks_asr")
        target = target_root / "asr" / relative
        write_json(target, transformed)
        require(
            [row["transcription"] for row in transformed]
            == [row["transcription"] for row in source_rows],
            f"transcription changed: {source}",
        )
        family = relative.parent.name
        condition_name = relative.stem.removeprefix("all-asr-data_")
        variant = (
            "typeless_ontology_fix"
            if condition_name.endswith("_typeless-ontology-fix")
            else "raw_asr"
        )
        biased = "_bias" in condition_name
        model_name = condition_name.removesuffix("_typeless-ontology-fix").removesuffix("_bias")
        add_config(
            f"wildclawbench-synthetic-{family}-{condition_name}".replace("_", "-"),
            target,
        )
        add_condition(
            family="wildclawbench",
            collection="synthetic",
            model=model_name,
            variant=variant,
            biasing=biased,
            data_file=target,
            audio_root="wildclawbench/synthetic/audio",
            rows=60,
            source_fidelity="transcript_exact_audio_path_rewritten",
        )


def stage_bias_lists() -> None:
    copy_file(OSWORLD_BIAS_SOURCE, STAGE / OSWORLD_BIAS_PATH)
    copy_file(WILDCLAW_BIAS_SOURCE, STAGE / WILDCLAW_BIAS_PATH)
    osworld_text = f"""# OSWorld Bias List\n\n`OSWorld_biasing_list.json` covers all 351 OSWorld tasks. Each task stores the\nconfig-derived terms, image-derived terms, and their stable deduplicated union.\nThe union length matches the recorded `task_biasing_terms` for every task in\nboth the Parakeet and Qwen biased-run manifests (zero mismatches).\n\nSHA-256: `{sha256(OSWORLD_BIAS_SOURCE)}`\n"""
    wildclaw_text = f"""# WildClawBench Bias List\n\n`WCB_task_details_biasing.json` covers all 60 formal WildClawBench tasks and\ncontains 3,119 non-empty, task-local unique Bias List terms. `task0_template`\nis not part of this file because it is not a formal benchmark task.\n\nSHA-256: `{sha256(WILDCLAW_BIAS_SOURCE)}`\n"""
    for relative, text in (
        ("osworld/bias_lists/README.md", osworld_text),
        ("wildclawbench/bias_lists/README.md", wildclaw_text),
    ):
        path = STAGE / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def write_dataset_card() -> None:
    lines = ["---", "pretty_name: Agentic ASR", "configs:"]
    for config in configs:
        lines.append(f"- config_name: {config['config_name']}")
        lines.append("  data_files:")
        for item in config["data_files"]:
            lines.append(f"  - split: {item['split']}")
            lines.append(f"    path: {item['path']}")
    lines.extend(
        [
            "---",
            "",
            "# Agentic ASR",
            "",
            "Private consolidated audio and ASR result dataset for the OSWorld and",
            "WildClawBench benchmark families.",
            "",
            "## Layout",
            "",
            "- `osworld/`: synthetic raw/colloquial speech, human recordings, DNS-noise",
            "  pairs, task images, ASR results, and reports.",
            "- `wildclawbench/`: 60 formal colloquialized prompts, their synthetic speech,",
            "  and 20 ASR condition tables. `task0_template` derivatives are excluded.",
            "- `metadata/conditions.jsonl`: model, variant, biasing, row count, checksum,",
            "  and audio-root metadata without duplicating transcript payloads.",
            "- `metadata/files.jsonl`: repository-wide file hashes and sizes.",
            "",
            "## Important provenance notes",
            "",
            "The four original OSWorld human-recording ASR JSONLs are preserved byte for",
            "byte. Their `audio` values are relative to `osworld/human_recordings/`.",
            "Parakeet TDT 0.6B v2 and Qwen2.5-Omni-7B with/without-bias results from",
            "`OSworld_ASR.zip` are included. The ZIP's additional Whisper run is excluded.",
            "Existing, separately produced Whisper v3 JSONLs remain as their own conditions.",
            "",
            "Bias-assisted conditions reference their published, versioned source files:",
            "`osworld/bias_lists/OSWorld_biasing_list.json` and",
            "`wildclawbench/bias_lists/WCB_task_details_biasing.json`. The condition manifest",
            "records each file's SHA-256 and marks all ten biased conditions `available`.",
            "",
            "WildClawBench aggregate ASR transcript strings are unchanged. Only their stale",
            "`data/tasks_tts/...` audio paths were rewritten to repository-relative paths.",
            "",
            "This private migration does not by itself establish redistribution rights for",
            "a future public release. Review source licenses before changing visibility.",
            "",
        ]
    )
    (STAGE / "README.md").write_text("\n".join(lines), encoding="utf-8")


def write_metadata() -> None:
    conditions.sort(key=lambda row: (row["family"], row["collection"], row["model"], row["variant"]))
    write_jsonl(STAGE / "metadata" / "conditions.jsonl", conditions)
    require(not any(row["bias_list_status"] == "pending" for row in conditions), "pending bias condition remains")
    require(sum(row["bias_list_status"] == "available" for row in conditions) == 10, "expected 10 available bias conditions")

    file_rows: list[dict[str, Any]] = []
    for path in sorted(item for item in STAGE.rglob("*") if item.is_file()):
        if path == STAGE / "metadata" / "files.jsonl":
            continue
        stat = path.stat()
        file_rows.append(
            {
                "path": path.relative_to(STAGE).as_posix(),
                "bytes": stat.st_size,
                "sha256": sha256(path),
            }
        )
    write_jsonl(STAGE / "metadata" / "files.jsonl", file_rows)


def main() -> None:
    require((ROOT / ".git").exists(), f"repository root not found: {ROOT}")
    require(not STAGE.exists(), f"staging directory already exists: {STAGE}")
    STAGE.mkdir(parents=True)
    stage_osworld_synthetic()
    stage_osworld_human()
    stage_osworld_dns_noise()
    stage_osworld_images()
    stage_osworld_shared_metadata()
    stage_wildclawbench()
    stage_bias_lists()
    write_dataset_card()
    write_metadata()
    print(json.dumps({"stage": str(STAGE), "configs": len(configs), "conditions": len(conditions)}))


if __name__ == "__main__":
    main()
