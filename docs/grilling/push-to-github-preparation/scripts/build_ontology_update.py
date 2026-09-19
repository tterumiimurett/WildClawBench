#!/usr/bin/env python3
"""Build the incremental Agentic ASR OSWorld ontology update."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
BASE = Path("/private/tmp/agentic-asr-ontology-base")
UPDATE = Path("/private/tmp/agentic-asr-ontology-update")
ASR = ROOT / "ToCASR" / "recorded_instruction" / "tasks_asr"
PROMPT_SHA = "36ea5ad12ccf313be185a3cb187e63984c08b66eabf6c4ccccf6046de74dffe7"
BIAS_PATH = "osworld/bias_lists/OSWorld_biasing_list.json"
BIAS_SHA = "797ab1863b645bebca8776c5e699f600da49f9d54f402f74630239b605521d58"

SOURCES = [
    ("parakeet_tdt_0.6b_v2", "typeless_ontology_fix.jsonl", False),
    ("parakeet_tdt_0.6b_v2", "bias_typeless_ontology_fix.jsonl", True),
    ("qwen2.5_omni_7b", "typeless_ontology_fix.jsonl", False),
    ("qwen2.5_omni_7b", "bias_typeless_ontology_fix.jsonl", True),
]


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def copy(source: Path, relative: str) -> Path:
    target = UPDATE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def update_readme() -> None:
    text = (BASE / "README.md").read_text(encoding="utf-8")
    anchors = {
        "parakeet_tdt_0.6b_v2": "- config_name: osworld-human-parakeet-tdt-0.6b-v2-raw-asr-bias\n  data_files:\n  - split: data\n    path: osworld/human_recordings/asr/parakeet_tdt_0.6b_v2/raw_asr_bias.jsonl\n",
        "qwen2.5_omni_7b": "- config_name: osworld-human-qwen2.5-omni-7b-raw-asr-bias\n  data_files:\n  - split: data\n    path: osworld/human_recordings/asr/qwen2.5_omni_7b/raw_asr_bias.jsonl\n",
    }
    for model, anchor in anchors.items():
        require(text.count(anchor) == 1, f"README anchor missing: {model}")
        slug = model.replace("_", "-")
        addition = (
            f"- config_name: osworld-human-{slug}-typeless-ontology-fix\n"
            "  data_files:\n  - split: data\n"
            f"    path: osworld/human_recordings/asr/{model}/typeless_ontology_fix.jsonl\n"
            f"- config_name: osworld-human-{slug}-bias-typeless-ontology-fix\n"
            "  data_files:\n  - split: data\n"
            f"    path: osworld/human_recordings/asr/{model}/bias_typeless_ontology_fix.jsonl\n"
        )
        text = text.replace(anchor, anchor + addition)
    old = "Existing, separately produced Whisper v3 JSONLs remain as their own conditions."
    new = old + "\n\nThe four Parakeet/Qwen ontology-fix conditions were derived with ByteDance\nModelHub `gpt-5.6-luna`. Exact transcript deduplication reduced 7,020 source\nrows to 3,333 model requests; task identity, audio references, and take metadata\nremain unchanged. See `osworld/human_recordings/metadata/ontology_fix_manifest.json`."
    require(text.count(old) == 1, "README provenance anchor missing")
    (UPDATE / "README.md").write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    require(BASE.is_dir(), f"missing base: {BASE}")
    require(not UPDATE.exists(), f"update exists: {UPDATE}")
    UPDATE.mkdir(parents=True)
    provenance = json.loads((ASR / "ontology_fix_manifest.json").read_text())
    require(provenance["normalizer"]["model"] == "gpt-5.6-luna", "wrong model")
    new_conditions = []
    for model, name, biased in SOURCES:
        source = ASR / model / name
        rows = read_jsonl(source)
        require(len(rows) == 1755 and len({r["task_id"] for r in rows}) == 1755, f"bad rows: {source}")
        relative = f"osworld/human_recordings/asr/{model}/{name}"
        copy(source, relative)
        row = {
            "family": "osworld", "collection": "human_recordings", "model": model,
            "variant": "typeless_ontology_fix", "biasing": biased,
            "bias_list_status": "available" if biased else "not_applicable",
            "data_file": relative, "audio_root": "osworld/human_recordings/source/All Recordings",
            "rows": 1755, "sha256": sha256(source),
            "source_fidelity": "ontology_normalized_metadata_preserved",
            "normalizer_model": "gpt-5.6-luna", "normalizer_prompt_sha256": PROMPT_SHA,
        }
        if biased:
            row.update({"bias_list": BIAS_PATH, "bias_list_sha256": BIAS_SHA})
        new_conditions.append(row)
    copy(ASR / "ontology_fix_manifest.json", "osworld/human_recordings/metadata/ontology_fix_manifest.json")
    copy(ASR / "osworld_asr_import_manifest.json", "osworld/human_recordings/metadata/osworld_asr_import_manifest.json")

    conditions = read_jsonl(BASE / "metadata/conditions.jsonl") + new_conditions
    conditions.sort(key=lambda r: (r["family"], r["collection"], r["model"], r["biasing"], r["variant"]))
    require(len(conditions) == 40, "expected 40 conditions")
    write_jsonl(UPDATE / "metadata/conditions.jsonl", conditions)
    update_readme()

    indexed = {row["path"]: row for row in read_jsonl(BASE / "metadata/files.jsonl")}
    require(len(indexed) == 3638, "unexpected base index")
    changed = [p for p in UPDATE.rglob("*") if p.is_file() and p != UPDATE / "metadata/files.jsonl"]
    require(len(changed) == 8, f"expected 8 changed/new files, got {len(changed)}")
    for path in changed:
        relative = path.relative_to(UPDATE).as_posix()
        indexed[relative] = {"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)}
    require(len(indexed) == 3643, "expected 3643 indexed files")
    write_jsonl(UPDATE / "metadata/files.jsonl", [indexed[key] for key in sorted(indexed)])
    print(json.dumps({"update_files": 9, "conditions": 40, "indexed_files": 3643}))


if __name__ == "__main__":
    main()
