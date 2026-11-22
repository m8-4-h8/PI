"""Завдання 3. Circuit Breaker як явна стейт-машина: Closed -> Open -> Half-Open."""
import threading
import time
from collections.abc import Callable
from enum import Enum
from typing import TypeVar

T = TypeVar("T")


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Виклик відхилено без звернення до залежності: розмикач відкритий."""


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int, recovery_timeout: float,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._clock = clock
        self._lock = threading.Lock()
        self._state = State.CLOSED
        self.failure_count = 0
        self._opened_at = 0.0
        self._trial_in_progress = False
        self.transitions: list[tuple[State, State]] = []

    @property
    def state(self) -> State:
        with self._lock:
            self._maybe_half_open()
            return self._state

    def _move(self, new: State) -> None:
        self.transitions.append((self._state, new))
        self._state = new

    def _maybe_half_open(self) -> None:
        if self._state is State.OPEN and self._clock() - self._opened_at >= self.recovery_timeout:
            self._move(State.HALF_OPEN)
            self._trial_in_progress = False

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            self._maybe_half_open()
            if self._state is State.OPEN:
                raise CircuitOpenError(f"{self.name}: circuit is open")
            if self._state is State.HALF_OPEN:
                if self._trial_in_progress:          # рівно один пробний виклик
                    raise CircuitOpenError(f"{self.name}: trial call already in progress")
                self._trial_in_progress = True
        try:
            result = fn()
        except Exception:
            self._on_failure()
            raise
        self._on_success()
        return result

    def _on_success(self) -> None:
        with self._lock:
            if self._state is State.HALF_OPEN:
                self._move(State.CLOSED)
                self._trial_in_progress = False
            self.failure_count = 0

    def _on_failure(self) -> None:
        with self._lock:
            if self._state is State.HALF_OPEN:
                self._trip()
                return
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self._trip()

    def _trip(self) -> None:
        self._move(State.OPEN)
        self._opened_at = self._clock()
        self.failure_count = 0                       # після повернення в Closed рахуємо з нуля
        self._trial_in_progress = False
