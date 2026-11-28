"""Write the two main correlation tables to standard output as CSV."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
import sys

from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parent
WCB_METRICS = ('wer_cer', 'semdist', 'aer', 'atomic', 'semantic_wer',
               'flat_retention_score', 'shapley_retention_score', 'native_projection_score')
OSWORLD_METRICS = ('lexical', 'semdist', 'retention')


def correlate(rows, metric):
    pairs = [(float(row[metric]), float(row['execution'])) for row in rows
             if row[metric] and row['execution']]
    if len(pairs) < 3:
        return len(pairs), '', ''
    scores, execution = zip(*pairs)
    if len(set(scores)) == 1 or len(set(execution)) == 1:
        return len(pairs), '', ''
    return len(pairs), pearsonr(scores, execution).statistic, spearmanr(scores, execution).statistic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('benchmark', choices=['wcb', 'osworld'])
    benchmark = parser.parse_args().benchmark
    writer = csv.writer(sys.stdout, lineterminator='\n')
    if benchmark == 'wcb':
        with (ROOT / 'wcb/comparison600.csv').open() as source:
            rows = list(csv.DictReader(source))
        writer.writerow(['metric', 'task_configurations', 'pearson', 'spearman'])
        for metric in WCB_METRICS:
            writer.writerow([metric, *correlate(rows, metric)])
    else:
        groups = defaultdict(list)
        with (ROOT / 'osworld/separate_asr_category_scores.csv').open() as source:
            for row in csv.DictReader(source):
                groups[row['agent'], row['condition']].append(row)
        writer.writerow(['agent', 'condition', 'metric', 'categories', 'pearson', 'spearman'])
        for (agent, condition), rows in sorted(groups.items()):
            for metric in OSWORLD_METRICS:
                writer.writerow([agent, condition, metric, *correlate(rows, metric)])


if __name__ == '__main__':
    main()
