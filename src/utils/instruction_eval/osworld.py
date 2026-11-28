"""Read the supplied aggregate score CSV without guessing condition/take mappings."""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
from pathlib import Path
from statistics import mean, stdev


def read_aggregate_scores(path: Path) -> dict:
    source_bytes = path.read_bytes()
    rows = list(csv.reader(source_bytes.decode('utf-8-sig').splitlines()))
    agent, entries = None, []

    def percentage(value: str) -> float:
        if not value.endswith('%'):
            raise ValueError('Expected percentage text in OSWorld score CSV')
        result = float(value[:-1]) / 100
        if not 0 <= result <= 1:
            raise ValueError('Score outside [0,1]')
        return result

    for line, row in enumerate(rows, 1):
        if not any(value.strip() for value in row):
            continue
        if len(row) != 8:
            raise ValueError(f'Expected 8 columns at CSV row {line}')
        if row[0].startswith('Agent:'):
            agent = row[0].split(':', 1)[1].strip()
            if row[1:6] != ['1', '2', '3', '4', '5']:
                raise ValueError('Unexpected human column labels')
            continue
        if not agent:
            raise ValueError('Condition without preceding agent header')
        scores = [percentage(value) for value in row[1:6]]
        average, deviation = percentage(row[6]), percentage(row[7])
        # Source is rounded to 0.01 percentage point; allow that rounding only.
        tolerance = .000051
        entries.append({'source_row': line, 'agent': agent, 'condition_label': row[0],
                        'column_scores': dict(zip(['1', '2', '3', '4', '5'], scores)),
                        'reported_average': average, 'reported_sample_stddev': deviation,
                        'recomputed_average': mean(scores), 'recomputed_sample_stddev': stdev(scores),
                        'average_reconciles': abs(mean(scores) - average) <= tolerance,
                        'stddev_reconciles': abs(stdev(scores) - deviation) <= tolerance,
                        'transcript_condition': None, 'take_mapping': None,
                        'mapping_status': 'awaiting_user_confirmation'})
    counts = Counter((entry['agent'], entry['condition_label']) for entry in entries)
    return {'source_path': str(path.resolve()), 'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
            'granularity': 'agent_condition_column_aggregate', 'has_task_ids': False,
            'condition_rows': len(entries), 'observations': len(entries) * 5,
            'duplicate_labels': [{'agent': agent, 'label': label, 'count': count}
                                 for (agent, label), count in counts.items() if count > 1],
            'entries': entries}
