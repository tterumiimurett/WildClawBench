"""Strict, read-only adapters for the four approved comparison groups."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class Pair:
    corpus: str
    task_id: str
    condition: str
    reference: str
    candidate: str
    reference_path: str
    candidate_path: str

    @property
    def key(self) -> str:
        return f'{self.corpus}/{self.condition}/{self.task_id}'

    def manifest(self) -> dict:
        data = asdict(self)
        for field in ('reference', 'candidate'):
            data[f'{field}_sha256'] = digest(data.pop(field))
        data['key'] = self.key
        return data


def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def text_file(path: Path) -> str:
    value = path.read_text(encoding='utf-8')
    if not value.strip():
        raise ValueError(f'Empty input: {path}')
    return value


def jsonl(path: Path, field: str) -> dict[str, str]:
    rows = {}
    for number, line in enumerate(text_file(path).splitlines(), 1):
        row = json.loads(line)
        key, text = row.get('task_id'), row.get(field)
        if not isinstance(key, str) or not key or key in rows:
            raise ValueError(f'Invalid/duplicate ID: {path}:{number}')
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f'Empty {field}: {path}:{number}')
        rows[key] = text
    return rows


def same_keys(reference: dict, candidate: dict, source: Path) -> None:
    if reference.keys() != candidate.keys():
        raise ValueError(f'Coverage mismatch: {source}; missing={len(reference.keys() - candidate.keys())}, '
                         f'extra={len(candidate.keys() - reference.keys())}')


def load_pairs(root: Path) -> list[Pair]:
    pairs = []
    wcb = root / 'data' / 'colloqialized_prompt'
    clean = wcb / 'tasks_clean'
    reference = {p.relative_to(clean).as_posix(): text_file(p)
                 for p in sorted(clean.rglob('*.md')) if p.name != 'task0_template.md'}
    modified = wcb / 'tasks_modified'
    candidates = {p.relative_to(modified).as_posix(): text_file(p)
                  for p in sorted(modified.rglob('*.md')) if p.name != 'task0_template.md'}
    same_keys(reference, candidates, modified)
    for key, text in candidates.items():
        pairs.append(Pair('wcb', key, 'modified', reference[key], text,
                          str(clean / key), str(modified / key)))
    for path in sorted((wcb / 'tasks_asr').rglob('*.json')):
        records = json.loads(text_file(path))
        if not isinstance(records, list):
            raise ValueError(f'Expected ASR array: {path}')
        candidates = {}
        for record in records:
            if set(record) != {'audio', 'category', 'transcription'}:
                raise ValueError(f'Invalid WCB record schema: {path}')
            key = f"{record['category']}/{Path(record['audio']).stem}.md"
            text = record['transcription']
            if key in candidates or not isinstance(text, str) or not text.strip():
                raise ValueError(f'Duplicate/empty WCB candidate: {path}')
            candidates[key] = text
        same_keys(reference, candidates, path)
        condition = 'asr/' + path.relative_to(wcb / 'tasks_asr').with_suffix('').as_posix()
        for key, text in candidates.items():
            pairs.append(Pair('wcb', key, condition, reference[key], text, str(clean / key), str(path)))
    toc = root / 'data' / 'ToCASR'
    raw_path = toc / 'raw_instruction/instructions.jsonl'
    reference = jsonl(raw_path, 'instruction')
    colloquial_path = toc / 'colloquial_instruction/instructions.jsonl'
    candidates = jsonl(colloquial_path, 'colloquialized_instruction')
    same_keys(reference, candidates, colloquial_path)
    for key, text in candidates.items():
        pairs.append(Pair('tocasr', key, 'colloquial', reference[key], text, str(raw_path), str(colloquial_path)))
    asr = toc / 'colloquial_instruction/tasks_asr'
    for path in sorted(asr.rglob('*.jsonl')):
        candidates = jsonl(path, 'transcript')
        same_keys(reference, candidates, path)
        condition = 'asr/' + path.relative_to(asr).with_suffix('').as_posix()
        for key, text in candidates.items():
            pairs.append(Pair('tocasr', key, condition, reference[key], text, str(raw_path), str(path)))
    if not pairs or len({p.key for p in pairs}) != len(pairs):
        raise ValueError('Empty corpus or duplicate comparison key')
    return pairs


def calibration_tasks(pairs: list[Pair]) -> list[dict]:
    """Deterministic coverage sample, with auditable feature selection reasons."""
    import re
    features = {
        'structured_output': r'json|schema|字段|\|---',
        'path': r'/tmp|~/|\.xlsx|\.pdf|路径',
        'conditional': r'\bif\b|如果|若',
        'dependency': r'\bthen\b|fetched|download|然后|解压',
        'chinese': r'[\u4e00-\u9fff]',
        'long_instruction': r'.',
    }
    chosen = []
    for corpus in sorted({p.corpus for p in pairs}):
        refs = {getattr(p, 'source_task_id', p.task_id): p for p in pairs if p.corpus == corpus}
        used = set()
        for feature, pattern in features.items():
            options = [p for p in refs.values() if p.task_id not in used
                       and re.search(pattern, p.reference, re.I | re.S)]
            if not options:
                options = [p for p in refs.values() if p.task_id not in used]
            # Prefer rich cases; task ID breaks ties deterministically.
            options.sort(key=lambda p: (-len(p.reference), p.task_id))
            item = options[0]
            used.add(item.task_id)
            chosen.append({'corpus': corpus, 'task_id': item.task_id, 'selection_feature': feature,
                           'feature_present': bool(re.search(pattern, item.reference, re.I | re.S))})
    return chosen


@dataclass(frozen=True)
class RecordedPair(Pair):
    source_task_id: str
    take: int


def load_recorded_pairs(root: Path) -> list[RecordedPair]:
    """Load the separately authorized five-human recordings, never TTS candidates."""
    raw_path = root / 'data' / 'ToCASR/raw_instruction/instructions.jsonl'
    refs = jsonl(raw_path, 'instruction')
    recorded = root / 'data' / 'ToCASR/recorded_instruction'
    manifest = {}
    for line in text_file(recorded / 'manifest.jsonl').splitlines():
        row = json.loads(line)
        key = row['recording_id']
        if key in manifest or row['source_task_id'] not in refs or row['take'] not in range(1, 6):
            raise ValueError('Invalid recorded instruction manifest')
        if row['instruction'] != refs[row['source_task_id']]:
            raise ValueError('Recorded reference differs from current raw instruction')
        manifest[key] = row
    if {(row['source_task_id'], row['take']) for row in manifest.values()} != {
            (key, take) for key in refs for take in range(1, 6)}:
        raise ValueError('Recorded manifest does not cover five takes for every reference')
    pairs = []
    for path in sorted((recorded / 'tasks_asr').rglob('*.jsonl')):
        if path.stem not in ('raw_asr', 'raw_asr_bias', 'typeless_ontology_fix'):
            continue
        seen = set()
        for line in text_file(path).splitlines():
            row = json.loads(line)
            key = row['task_id']
            if key not in manifest or key in seen:
                raise ValueError(f'Duplicate/unmapped recording: {path}')
            seen.add(key)
            original = manifest[key]
            if any(row[field] != original[field] for field in ('source_task_id', 'take')):
                raise ValueError(f'Recording identity mismatch: {path}')
            if not isinstance(row['transcript'], str) or not row['transcript'].strip():
                raise ValueError(f'Empty recorded transcript: {path}')
            condition = path.relative_to(recorded / 'tasks_asr').with_suffix('').as_posix()
            pairs.append(RecordedPair('tocasr_recorded', key, condition, refs[row['source_task_id']],
                row['transcript'], str(raw_path), str(path), row['source_task_id'], row['take']))
        if seen != manifest.keys():
            raise ValueError(f'Recorded condition coverage mismatch: {path}')
    if not pairs:
        raise ValueError('No recorded conditions')
    return pairs


def load_target_pairs(root: Path) -> list[Pair]:
    """User-selected future scope: WCB Parakeet synthetic + modified, one human ASR set."""
    wcb = [p for p in load_pairs(root) if p.corpus == 'wcb'
           and (p.condition == 'modified' or p.condition.startswith('asr/parakeet/'))]
    recorded = [p for p in load_recorded_pairs(root) if p.condition == 'whisper_v3/raw_asr']
    if len(wcb) != 300 or len(recorded) != 1755:
        raise ValueError('Selected target scope changed; inspect inventory before proceeding')
    return wcb + recorded


def read_instruction_rows(path: Path) -> list[tuple[int, dict]]:
    rows = []
    seen = set()
    with path.open(encoding='utf-8') as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f'{path}:{number}: {exc.msg}') from exc
            if not isinstance(row, dict) or any(
                not isinstance(row.get(key), str) or not row[key].strip()
                for key in ('id', 'reference', 'candidate')
            ):
                raise ValueError(f'{path}:{number}: expected nonempty id, reference and candidate strings')
            if row['id'] in seen:
                raise ValueError(f'{path}:{number}: duplicate id {row["id"]!r}')
            seen.add(row['id'])
            rows.append((number, row))
    if not rows:
        raise ValueError(f'{path}: empty input')
    return rows


def load_custom_pairs(path: Path) -> list[Pair]:
    return [Pair('custom', row['id'], 'input', row['reference'], row['candidate'],
                 f'{path}:{number}', f'{path}:{number}') for number, row in read_instruction_rows(path)]
