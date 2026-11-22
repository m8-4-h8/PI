import pytest

from resilience.circuit_breaker import CircuitBreaker, CircuitOpenError, State


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class Dependency:
    def __init__(self):
        self.calls = 0
        self.healthy = False

    def __call__(self):
        self.calls += 1
        if not self.healthy:
            raise ConnectionError("room-inventory is down")
        return "ok"


def test_all_four_transitions_and_no_calls_while_open():
    clock, dep = Clock(), Dependency()
    cb = CircuitBreaker("room-inventory", failure_threshold=3, recovery_timeout=10, clock=clock)

    # Closed -> Open після 3 послідовних невдач
    for _ in range(3):
        with pytest.raises(ConnectionError):
            cb.call(dep)
    assert cb.state is State.OPEN and dep.calls == 3

    # Open: миттєва відмова, залежність НЕ викликається
    for _ in range(5):
        with pytest.raises(CircuitOpenError):
            cb.call(dep)
    clock.now += 9.9
    with pytest.raises(CircuitOpenError):
        cb.call(dep)
    assert dep.calls == 3

    # Open -> Half-Open рівно через recovery_timeout; пробний виклик невдалий -> Open
    clock.now += 0.1
    assert cb.state is State.HALF_OPEN
    with pytest.raises(ConnectionError):
        cb.call(dep)
    assert dep.calls == 4 and cb.state is State.OPEN and cb.failure_count == 0

    # знову Half-Open; пробний виклик успішний -> Closed
    clock.now += 10
    dep.healthy = True
    assert cb.call(dep) == "ok"
    assert cb.state is State.CLOSED and cb.failure_count == 0 and dep.calls == 5

    assert cb.transitions == [
        (State.CLOSED, State.OPEN),
        (State.OPEN, State.HALF_OPEN),
        (State.HALF_OPEN, State.OPEN),
        (State.OPEN, State.HALF_OPEN),
        (State.HALF_OPEN, State.CLOSED),
    ]


def test_half_open_allows_exactly_one_trial_call():
    clock = Clock()
    cb = CircuitBreaker("payment", failure_threshold=1, recovery_timeout=5, clock=clock)
    with pytest.raises(ZeroDivisionError):
        cb.call(lambda: 1 / 0)
    clock.now += 5
    inner_results = []

    def slow_trial():
        # поки пробний виклик триває, другий виклик має бути відхилений
        with pytest.raises(CircuitOpenError):
            cb.call(lambda: inner_results.append("second call reached dependency"))
        return "trial ok"

    assert cb.call(slow_trial) == "trial ok"
    assert inner_results == [] and cb.state is State.CLOSED


def test_success_in_closed_resets_failure_count():
    cb = CircuitBreaker("housekeeping", failure_threshold=3, recovery_timeout=5, clock=Clock())
    dep = Dependency()
    for _ in range(2):
        with pytest.raises(ConnectionError):
            cb.call(dep)
    dep.healthy = True
    cb.call(dep)
    assert cb.failure_count == 0 and cb.state is State.CLOSED


def test_breakers_do_not_share_state():
    clock = Clock()
    payment = CircuitBreaker("payment", 3, 30, clock)
    inventory = CircuitBreaker("room-inventory", 3, 10, clock)
    for _ in range(3):
        with pytest.raises(ConnectionError):
            inventory.call(Dependency())
    assert inventory.state is State.OPEN
    assert payment.call(lambda: "charged") == "charged" and payment.state is State.CLOSED
