#!/usr/bin/env python3
"""Build the incremental Agentic ASR update for supplied Bias Lists."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
BASE = Path("/private/tmp/agentic-asr-bias-base")
UPDATE = Path("/private/tmp/agentic-asr-bias-update")
OSWORLD_SOURCE = ROOT / "ToCASR" / "bias_lists" / "OSWorld_biasing_list.json"
WILDCLAW_SOURCE = (
    ROOT / "colloqialized_prompt" / "bias_lists" / "WCB_task_details_biasing.json"
)
OSWORLD_PATH = "osworld/bias_lists/OSWorld_biasing_list.json"
WILDCLAW_PATH = "wildclawbench/bias_lists/WCB_task_details_biasing.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes())
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def copy(source: Path, relative_target: str) -> Path:
    require(source.is_file(), f"missing source: {source}")
    target = UPDATE / relative_target
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def validate_sources() -> tuple[str, str]:
    osworld = json.loads(OSWORLD_SOURCE.read_text(encoding="utf-8"))
    require(set(osworld) == {"metadata", "tasks"}, "unexpected OSWorld schema")
    require(osworld["metadata"]["task_count"] == 351, "bad OSWorld task_count")
    require(len(osworld["tasks"]) == 351, "expected 351 OSWorld tasks")
    require(
        len({row["task_id"] for row in osworld["tasks"]}) == 351,
        "duplicate OSWorld task IDs",
    )
    for row in osworld["tasks"]:
        expected = list(
            dict.fromkeys(row["config_biasing_list"] + row["image_biasing_list"])
        )
        require(row["biasing_list"] == expected, f"bad merged list: {row['task_id']}")
        require(
            all(isinstance(term, str) and term.strip() for term in row["biasing_list"]),
            f"invalid OSWorld term: {row['task_id']}",
        )

    wildclaw = json.loads(WILDCLAW_SOURCE.read_text(encoding="utf-8"))
    require(isinstance(wildclaw, list) and len(wildclaw) == 60, "expected 60 WCB tasks")
    identities = [f"{row['task']}_{row['taskname']}" for row in wildclaw]
    require(len(set(identities)) == 60, "duplicate WCB task identity")
    require(sum(len(row["list"]) for row in wildclaw) == 3119, "unexpected WCB term count")
    for row in wildclaw:
        terms = row["list"]
        require(len(terms) == len(set(terms)), f"duplicate WCB terms: {row['taskname']}")
        require(
            all(isinstance(term, str) and term.strip() for term in terms),
            f"invalid WCB term: {row['taskname']}",
        )
    return sha256(OSWORLD_SOURCE), sha256(WILDCLAW_SOURCE)


def update_conditions(osworld_sha: str, wildclaw_sha: str) -> None:
    source = BASE / "metadata" / "conditions.jsonl"
    rows = read_jsonl(source)
    for row in rows:
        if not row["biasing"]:
            continue
        if row["family"] == "osworld":
            row["bias_list"] = OSWORLD_PATH
            row["bias_list_sha256"] = osworld_sha
        elif row["family"] == "wildclawbench":
            row["bias_list"] = WILDCLAW_PATH
            row["bias_list_sha256"] = wildclaw_sha
        else:
            raise RuntimeError(f"unknown biased family: {row['family']}")
        row["bias_list_status"] = "available"
    require(sum(row["biasing"] for row in rows) == 10, "expected 10 biased conditions")
    require(
        sum(row["bias_list_status"] == "available" for row in rows) == 10,
        "expected 10 available Bias Lists",
    )
    require(not any(row["bias_list_status"] == "pending" for row in rows), "pending remains")
    write_jsonl(UPDATE / "metadata" / "conditions.jsonl", rows)


def update_dataset_card() -> None:
    source = BASE / "README.md"
    text = source.read_text(encoding="utf-8")
    old = """Bias-assisted conditions are present, but the underlying Bias List files have
not yet been supplied. They are explicitly marked `pending`; no placeholder
vocabulary has been fabricated."""
    new = """Bias-assisted conditions reference their published, versioned source files:
`osworld/bias_lists/OSWorld_biasing_list.json` and
`wildclawbench/bias_lists/WCB_task_details_biasing.json`. The condition manifest
records each file's SHA-256 and marks all ten biased conditions `available`."""
    require(text.count(old) == 1, "dataset-card pending paragraph not found exactly once")
    target = UPDATE / "README.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text.replace(old, new), encoding="utf-8")


def write_bias_readmes(osworld_sha: str, wildclaw_sha: str) -> None:
    osworld_text = f"""# OSWorld Bias List

`OSWorld_biasing_list.json` covers all 351 OSWorld tasks. Each task stores the
config-derived terms, image-derived terms, and their stable deduplicated union.
The union length matches the recorded `task_biasing_terms` for every task in
both the Parakeet and Qwen biased-run manifests (zero mismatches).

SHA-256: `{osworld_sha}`
"""
    wildclaw_text = f"""# WildClawBench Bias List

`WCB_task_details_biasing.json` covers all 60 formal WildClawBench tasks and
contains 3,119 non-empty, task-local unique Bias List terms. `task0_template`
is not part of this file because it is not a formal benchmark task.

SHA-256: `{wildclaw_sha}`
"""
    for relative, text in (
        ("osworld/bias_lists/README.md", osworld_text),
        ("wildclawbench/bias_lists/README.md", wildclaw_text),
    ):
        path = UPDATE / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def update_import_manifest(osworld_sha: str) -> None:
    source = ROOT / "ToCASR" / "recorded_instruction" / "tasks_asr" / "osworld_asr_import_manifest.json"
    value = json.loads(source.read_text(encoding="utf-8"))
    value["bias_list"] = OSWORLD_PATH
    value["bias_list_sha256"] = osworld_sha
    require(
        all(
            row["bias_list_status"] == "available"
            for row in value["conditions"]
            if row["biasing_enabled"]
        ),
        "local import manifest still has pending biased conditions",
    )
    write_json(
        UPDATE / "osworld" / "human_recordings" / "metadata" / "osworld_asr_import_manifest.json",
        value,
    )


def update_file_index() -> None:
    source_rows = read_jsonl(BASE / "metadata" / "files.jsonl")
    by_path = {row["path"]: row for row in source_rows}
    require(len(by_path) == len(source_rows) == 3636, "unexpected base file index")
    changed = [
        path
        for path in UPDATE.rglob("*")
        if path.is_file() and path != UPDATE / "metadata" / "files.jsonl"
    ]
    require(len(changed) == 7, f"expected 7 changed/new payload files, got {len(changed)}")
    for path in changed:
        relative = path.relative_to(UPDATE).as_posix()
        by_path[relative] = {
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    require(len(by_path) == 3638, f"expected 3,638 indexed payloads, got {len(by_path)}")
    write_jsonl(UPDATE / "metadata" / "files.jsonl", [by_path[key] for key in sorted(by_path)])


def main() -> None:
    require((ROOT / ".git").exists(), f"repository root not found: {ROOT}")
    require(BASE.is_dir(), f"missing downloaded base: {BASE}")
    require(not UPDATE.exists(), f"update directory already exists: {UPDATE}")
    UPDATE.mkdir(parents=True)
    osworld_sha, wildclaw_sha = validate_sources()
    copy(OSWORLD_SOURCE, OSWORLD_PATH)
    copy(WILDCLAW_SOURCE, WILDCLAW_PATH)
    update_conditions(osworld_sha, wildclaw_sha)
    update_dataset_card()
    write_bias_readmes(osworld_sha, wildclaw_sha)
    update_import_manifest(osworld_sha)
    update_file_index()
    print(
        json.dumps(
            {
                "update_files": sum(path.is_file() for path in UPDATE.rglob("*")),
                "osworld_sha256": osworld_sha,
                "wildclawbench_sha256": wildclaw_sha,
            }
        )
    )


if __name__ == "__main__":
    main()
