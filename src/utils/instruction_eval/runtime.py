"""Resumable model calls with content-addressed artifacts and bounded retries."""
from __future__ import annotations

from datetime import datetime, timezone
from collections import deque
import json
import os
from pathlib import Path
import threading
import time
from typing import Callable

from .corpus import digest
from .evidence import PROTOCOL, prepare, resolve
from .scoring import InvalidEvaluation

DEFAULT_MODEL = 'openai/gpt-5.4-mini'
OPENROUTER_URL = 'https://openrouter.ai/api/v1'


def write_json(path: Path, value: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f'.{os.getpid()}.{threading.get_ident()}.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class ModelCallFailure(RuntimeError):
    """Contains only safe status metadata, never request URLs or authentication."""

    @classmethod
    def from_attempt(cls, error: dict) -> ModelCallFailure:
        detail = error.get('validation_message') or error['type']
        if error.get('http_status'):
            detail = f"HTTP {error['http_status']} ({detail})"
        return cls(f"{error['stage']} failed after {error['attempt']} attempts: {detail}")


class TokenBudget:
    """Conservative rolling-minute admission budget shared by this process's workers."""

    def __init__(self, tpm: int, qpm: int = 100) -> None:
        self.tpm = tpm
        self.qpm = qpm
        self.entries = deque()
        self.lock = threading.Lock()

    def reserve(self, tokens: int) -> None:
        if tokens > self.tpm:
            raise ModelCallFailure('One request exceeds the configured TPM reservation budget')
        while True:
            with self.lock:
                now = time.monotonic()
                while self.entries and now - self.entries[0][0] >= 60:
                    self.entries.popleft()
                if len(self.entries) < self.qpm and sum(value for _, value in self.entries) + tokens <= self.tpm:
                    self.entries.append((now, tokens))
                    return
                delay = max(.01, 60 - (now - self.entries[0][0]))
            time.sleep(min(delay, 30))


class ModelRuntime:
    def __init__(self, root: Path, output: Path, *, timeout: float = 240,
                 interval: float = .1, retries: int = 3, max_tokens: int = 24000,
                 tpm: int = 1_000_000, qpm: int = 100) -> None:
        try:
            from dotenv import dotenv_values
            from openai import OpenAI
        except ImportError as exc:
            raise ModelCallFailure('Install the judge dependencies: python -m pip install openai python-dotenv') from exc
        key = os.environ.get('OPENROUTER_API_KEY') or dotenv_values(root / '.env').get('OPENROUTER_API_KEY')
        if not key:
            raise ModelCallFailure('Set OPENROUTER_API_KEY in the environment or repository .env')
        self.client = OpenAI(base_url=OPENROUTER_URL, api_key=key, timeout=timeout, max_retries=0)
        self.output = output
        self.timeout, self.interval, self.retries, self.max_tokens = timeout, interval, retries, max_tokens
        self.lock = threading.Lock()
        self.next_call = 0.0
        self.backend_hash = digest(OPENROUTER_URL)
        self.token_budget = TokenBudget(tpm, qpm)

    def wait(self) -> None:
        with self.lock:
            delay = max(0, self.next_call - time.monotonic())
            self.next_call = max(time.monotonic(), self.next_call) + self.interval
        if delay:
            time.sleep(delay)

    def call(self, stage: str, model: str, prompt: str, data: dict,
             validate: Callable[[dict], None]) -> tuple[dict, str]:
        data = prepare(data)
        prompt = prompt + '\n\n' + PROTOCOL
        request = {'stage': stage, 'model': model, 'prompt': prompt, 'data': data,
                   'backend_sha256': self.backend_hash, 'max_tokens': self.max_tokens,
                   'response_format': {'type': 'json_object'},
                   'protocol': 'instruction-eval-evidence-ids-v1'}
        key = digest(canonical(request))
        path = self.output / 'calls' / f'{key}.json'
        if path.exists():
            cached = json.loads(path.read_text(encoding='utf-8'))
            validate(cached['result'])
            return cached['result'], key
        # A logical call keeps its attempt budget across workers and resumes.
        # Successful cache lookup above still takes precedence over historical failures.
        previous = []
        for failure_path in (self.output / 'failures').glob(f'{key}-*.json'):
            artifact = json.loads(failure_path.read_text(encoding='utf-8'))
            previous.append(artifact)
        last = max(previous, key=lambda item: item['error']['attempt']) if previous else None
        used_attempts = last['error']['attempt'] if last else 0
        if used_attempts >= self.retries:
            raise ModelCallFailure.from_attempt(last['error'])
        repair_feedback = None
        if last and 'validation_message' in last['error']:
            repair_feedback = {
                'instruction': 'The previous output failed structural validation. Return a complete corrected JSON artifact; preserve semantic rules.',
                'validation_error': last['error']['validation_message'],
                'previous_output': last['raw_output']}
        for attempt in range(used_attempts + 1, self.retries + 1):
            self.wait()
            started = time.monotonic()
            parts, finish, usage, response_model = [], None, None, model
            stream = None
            try:
                messages = [{'role': 'system', 'content': prompt},
                            {'role': 'user', 'content': canonical(data)}]
                if repair_feedback:
                    messages.append({'role': 'user', 'content': canonical(repair_feedback)})
                # Reserve UTF-8 byte count + output ceiling + framing allowance.
                # This is deliberately conservative, not a provider token-meter claim.
                self.token_budget.reserve(len(canonical(messages).encode('utf-8')) + self.max_tokens + 1024)
                started = time.monotonic()
                stream = self.client.chat.completions.create(
                    model=model, messages=messages,
                    response_format=request['response_format'],
                    max_tokens=self.max_tokens, stream=True,
                    stream_options={'include_usage': True})
                for chunk in stream:
                    if time.monotonic() - started > self.timeout:
                        raise TimeoutError('Model response deadline exceeded')
                    response_model = chunk.model or response_model
                    if chunk.usage:
                        usage = chunk.usage.model_dump()
                    if chunk.choices:
                        choice = chunk.choices[0]
                        if choice.delta.content:
                            parts.append(choice.delta.content)
                        if choice.finish_reason:
                            finish = choice.finish_reason
                if finish != 'stop':
                    raise InvalidEvaluation(f'Incomplete response: finish_reason={finish}')
                raw = ''.join(parts).strip()
                if raw.startswith('```') and raw.endswith('```'):
                    raw = '\n'.join(raw.splitlines()[1:-1])
                wire_result = json.loads(raw)
                result = resolve(wire_result, data)
                validate(result)
                write_json(path, {'request': request, 'result': result, 'wire_result': wire_result, 'response_model': response_model,
                                  'attempt': attempt, 'repair_feedback': repair_feedback, 'finish_reason': finish,
                                  'usage': usage, 'duration_seconds': time.monotonic() - started,
                                  'created_at': datetime.now(timezone.utc).isoformat()})
                return result, key
            except Exception as exc:
                # API exception messages may contain request URLs; never serialize or print them.
                error = {'type': type(exc).__name__, 'stage': stage, 'attempt': attempt,
                         'http_status': getattr(exc, 'status_code', None)}
                if error['http_status'] == 429:
                    on_rate_limit = getattr(self.token_budget, 'rate_limited', None)
                    if on_rate_limit is not None:
                        on_rate_limit()
                if isinstance(exc, (InvalidEvaluation, json.JSONDecodeError)):
                    error['validation_message'] = str(exc)
                    repair_feedback = {
                        'instruction': 'The previous output failed structural validation. Return a complete corrected JSON artifact; preserve semantic rules.',
                        'validation_error': str(exc), 'previous_output': ''.join(parts)}
                write_json(self.output / 'failures' / f'{key}-{attempt}.json',
                           {'error': error, 'request': request, 'raw_output': ''.join(parts),
                            'finish_reason': finish, 'usage': usage,
                            'duration_seconds': time.monotonic() - started})
                if attempt == self.retries:
                    raise ModelCallFailure.from_attempt(error) from None
                time.sleep(min(8, 2 ** attempt))
            finally:
                if stream is not None:
                    stream.close()
        raise AssertionError('Unreachable')
