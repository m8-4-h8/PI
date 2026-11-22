import random

import pytest

from resilience.retry import TransientError, backoff_delay, retry


def flaky(fail_times, error=TransientError):
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise error("boom")
        return "ok"
    return fn, calls


def test_recovers_on_n_plus_one_attempt():
    fn, calls = flaky(3)
    sleeps = []
    assert retry(fn, max_attempts=5, sleep=sleeps.append, rng=random.Random(1)) == "ok"
    assert calls["n"] == 4 and len(sleeps) == 3


def test_gives_up_after_max_attempts():
    fn, calls = flaky(10)
    with pytest.raises(TransientError):
        retry(fn, max_attempts=3, sleep=lambda _: None)
    assert calls["n"] == 3


def test_non_transient_error_is_not_retried():
    fn, calls = flaky(1, error=ValueError)
    with pytest.raises(ValueError):
        retry(fn, max_attempts=5, sleep=lambda _: None)
    assert calls["n"] == 1


def test_full_jitter_is_random_and_bounded():
    rng = random.Random(7)
    for attempt in range(6):
        cap = min(0.1 * 2 ** attempt, 1.0)
        delays = [backoff_delay(attempt, 0.1, 1.0, rng) for _ in range(200)]
        assert all(0 <= d <= cap for d in delays)
        assert len(set(delays)) > 150                      # не фіксовані значення
        assert min(delays) < cap * 0.2 and max(delays) > cap * 0.8   # покриває весь діапазон
