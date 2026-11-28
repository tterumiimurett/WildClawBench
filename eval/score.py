"""Score user-supplied instruction pairs with Intent Retention."""
import argparse
import json
from pathlib import Path

from src.utils.instruction_eval.corpus import load_custom_pairs
from src.utils.instruction_eval.evaluator import Evaluator
from src.utils.instruction_eval.runtime import DEFAULT_MODEL, ModelCallFailure, ModelRuntime


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='JSONL rows with id, reference and candidate')
    parser.add_argument('--model', default=DEFAULT_MODEL, help='OpenRouter model ID')
    parser.add_argument('--output', type=Path, default=Path('output/intent-retention'),
                        help='directory for cached calls and detailed judgments')
    args = parser.parse_args(argv)
    try:
        pairs = load_custom_pairs(args.input)
        runtime = ModelRuntime(Path(__file__).resolve().parents[1], args.output)
    except (OSError, ValueError, ModelCallFailure) as exc:
        parser.error(str(exc))
    evaluator = Evaluator(runtime, dict.fromkeys(('decompose', 'audit', 'forward', 'reverse'), args.model))
    exit_code = 0
    for pair in pairs:
        result = evaluator.evaluate(pair)
        score = result['score']
        row = {'id': pair.task_id, 'status': score['status'], 'retention': score.get('retention'),
               'final_score': score.get('final_score')}
        if score['status'] != 'scored':
            exit_code = 1
            reasons = list(result['stage_errors'].values()) or score.get('review_reasons', [])
            row['reason'] = '; '.join(reasons) or result['error']
        print(json.dumps(row, ensure_ascii=False), flush=True)
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
