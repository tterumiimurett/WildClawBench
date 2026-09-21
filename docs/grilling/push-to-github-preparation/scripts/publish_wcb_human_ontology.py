#!/usr/bin/env python3
"""Atomically add WildClawBench human ontology results to Agentic ASR.

Prepare the small upload files in the existing hard-linked staging tree, then
publish them in one Hugging Face commit guarded by the pinned parent revision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
STAGE = Path("/private/tmp/agentic-asr-upload")
LOCAL = ROOT / "colloqialized_prompt" / "human_recordings" / "asr"
PROMPT = ROOT / "colloqialized_prompt" / "prompts" / "normalize_transcript.md"
LOCK = ROOT / "configs" / "datasets" / "agentic-asr.lock.json"
REMOTE_ROOT = "wildclawbench/human_recordings/asr"
FILES = (
    "parakeet/all-asr-data_parakeet-ctc_typeless-ontology-fix.json",
    "parakeet/all-asr-data_parakeet-ctc_bias_typeless-ontology-fix.json",
    "qwen/all-asr-data_qwen-omni_typeless-ontology-fix.json",
    "qwen/all-asr-data_qwen-omni_bias_typeless-ontology-fix.json",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def stage_files() -> list[str]:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    require(lock["dataset"]["revision"] == "daaf90531993bf8564cd222a6b520f8300b5c2aa", "unexpected source revision")
    require(STAGE.is_dir(), f"existing staging tree missing: {STAGE}")
    old_index = {row["path"]: row for row in read_jsonl(STAGE / "metadata/files.jsonl")}
    require(len(old_index) == lock["integrity"]["indexed_files"], "staging index count differs from lock")
    require(sha256(STAGE / "metadata/files.jsonl") == lock["integrity"]["files_manifest"]["sha256"], "staging index differs from lock")

    provenance = json.loads((LOCAL / "ontology_fix_manifest.json").read_text(encoding="utf-8"))
    require(provenance["normalizer"]["model"] == "gpt-5.6-luna", "wrong normalizer")
    require(provenance["normalizer"]["prompt_sha256"] == sha256(PROMPT), "prompt hash mismatch")
    by_output = {row["output"]: row for row in provenance["conditions"]}
    require(set(by_output) == set(FILES), "ontology provenance has missing/extra outputs")

    changed = []
    for relative in (*FILES, "ontology_fix_manifest.json", "import_manifest.json"):
        source = LOCAL / relative
        require(source.is_file(), f"missing local file: {source}")
        if relative in by_output:
            require(sha256(source) == by_output[relative]["output_sha256"], f"provenance hash mismatch: {relative}")
        target = STAGE / REMOTE_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        changed.append(target.relative_to(STAGE).as_posix())
    prompt_target = STAGE / REMOTE_ROOT / "ontology_fix_prompt.md"
    shutil.copy2(PROMPT, prompt_target)
    changed.append(prompt_target.relative_to(STAGE).as_posix())

    conditions_path = STAGE / "metadata/conditions.jsonl"
    conditions = read_jsonl(conditions_path)
    require(len(conditions) == 44, "expected 44 existing conditions")
    old_conditions = {
        (row["model"], row["biasing"]): row
        for row in conditions
        if row["family"] == "wildclawbench" and row["collection"] == "human_recordings"
    }
    require(len(old_conditions) == 4, "expected four raw human conditions")
    for relative in FILES:
        model = "parakeet-ctc" if relative.startswith("parakeet/") else "qwen-omni"
        biased = "_bias_" in relative
        base = dict(old_conditions[(model, biased)])
        path = f"{REMOTE_ROOT}/{relative}"
        base.update({
            "variant": "typeless_ontology_fix",
            "data_file": path,
            "sha256": sha256(STAGE / path),
            "source_fidelity": "source_metadata_preserved_transcription_normalized",
            "normalizer_model": "gpt-5.6-luna",
            "normalizer_prompt_sha256": provenance["normalizer"]["prompt_sha256"],
            "ontology_fix_manifest": f"{REMOTE_ROOT}/ontology_fix_manifest.json",
        })
        conditions.append(base)
    conditions.sort(key=lambda row: (row["family"], row["collection"], row["model"], row["variant"]))
    write_jsonl(conditions_path, conditions)
    changed.append("metadata/conditions.jsonl")

    readme_path = STAGE / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    require(readme.count("\n---\n") == 1, "unexpected Dataset Card front matter")
    front, body = readme.split("\n---\n", 1)
    configs = []
    for relative in FILES:
        path = f"{REMOTE_ROOT}/{relative}"
        condition_name = Path(relative).stem.removeprefix("all-asr-data_")
        name = f"wildclawbench-human-recordings-{condition_name}".replace("_", "-")
        require(f"- config_name: {name}\n" not in front, f"config already exists: {name}")
        configs.extend([
            f"- config_name: {name}", "  data_files:", "  - split: data", f"    path: {path}",
        ])
    front += "\n" + "\n".join(configs)
    note = (
        "\nFor WildClawBench human recordings, four additional ontology-fix conditions "
        "were generated with ByteDance ModelHub `gpt-5.6-luna`, matching the "
        "OSWorld human-recording Parakeet/Qwen fixes. Other existing fixes use "
        "GPT-5.4. The prior 60-row Parakeet 01男 fixes were not reused; the "
        "full 600 rows per condition were regenerated from raw ASR. Parakeet covers all 600 "
        "recordings per condition; Qwen covers its cleaned 507-recording subset. "
        "The prompt, its hash, input/output hashes, model settings, and row counts "
        "are recorded in `wildclawbench/human_recordings/asr/ontology_fix_manifest.json`.\n"
    )
    readme_path.write_text(front + "\n---\n" + body.rstrip() + "\n" + note, encoding="utf-8")
    changed.append("README.md")

    for path in changed:
        file = STAGE / path
        old_index[path] = {"path": path, "bytes": file.stat().st_size, "sha256": sha256(file)}
    index_path = STAGE / "metadata/files.jsonl"
    write_jsonl(index_path, [old_index[path] for path in sorted(old_index)])
    changed.append("metadata/files.jsonl")
    require(len(old_index) == 4254, "expected 10 newly indexed files")
    require(len(conditions) == 48, "expected 48 conditions")
    print(json.dumps({"staged_paths": changed, "indexed_files": len(old_index), "conditions": len(conditions)}, ensure_ascii=False), flush=True)
    return changed


def publish(changed: list[str]) -> None:
    from huggingface_hub import CommitOperationAdd, HfApi

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    revision = lock["dataset"]["revision"]
    repo_id = lock["dataset"]["repo_id"]
    api = HfApi()
    info = api.repo_info(repo_id, repo_type="dataset")
    require(info.sha == revision, f"remote revision changed: {info.sha}")
    operations = [CommitOperationAdd(path_in_repo=path, path_or_fileobj=str(STAGE / path)) for path in changed]
    result = api.create_commit(
        repo_id=repo_id,
        repo_type="dataset",
        operations=operations,
        commit_message="wildclawbench: add Luna ontology fixes for human recordings",
        parent_commit=revision,
    )
    print(json.dumps({"commit_oid": result.oid, "commit_url": result.commit_url}, ensure_ascii=False), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Create the remote commit after local staging")
    args = parser.parse_args()
    changed = stage_files()
    if args.publish:
        publish(changed)


if __name__ == "__main__":
    main()
