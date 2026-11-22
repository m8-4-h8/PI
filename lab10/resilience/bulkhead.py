"""Завдання 4.1. Bulkhead: окремий, обмежений пул потоків на кожну залежність."""
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from collections.abc import Callable


class BulkheadFullError(Exception):
    """Пул залежності вичерпано: відмовляємо одразу, а не стаємо в нескінченну чергу."""


class Bulkhead:
    def __init__(self, name: str, max_concurrent: int, max_queue: int = 0) -> None:
        self.name = name
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent, thread_name_prefix=name)
        self._slots = threading.BoundedSemaphore(max_concurrent + max_queue)

    def submit(self, fn: Callable, *args) -> Future:
        if not self._slots.acquire(blocking=False):
            raise BulkheadFullError(f"{self.name}: no free slots")
        future = self._executor.submit(fn, *args)
        future.add_done_callback(lambda _: self._slots.release())
        return future

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
