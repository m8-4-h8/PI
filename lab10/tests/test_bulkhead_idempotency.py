import threading
import time

import pytest

from resilience.bulkhead import Bulkhead, BulkheadFullError
from resilience.idempotency import FakePaymentGateway, PaymentEndpoint


def test_hung_payment_pool_does_not_block_inventory_pool():
    payment_pool = Bulkhead("payment", max_concurrent=4)
    inventory_pool = Bulkhead("room-inventory", max_concurrent=2)
    release = threading.Event()

    hung = [payment_pool.submit(release.wait, 5) for _ in range(4)]   # усі потоки payment зависли
    time.sleep(0.05)
    with pytest.raises(BulkheadFullError):                             # п'ятий запит -- миттєва відмова
        payment_pool.submit(lambda: "charge")

    start = time.perf_counter()
    result = inventory_pool.submit(lambda: {"double": 3}).result(timeout=1)
    elapsed = time.perf_counter() - start
    assert result == {"double": 3} and elapsed < 0.5
    assert not any(f.done() for f in hung)                             # payment усе ще висить

    release.set()
    assert all(f.result(timeout=1) for f in hung)
    payment_pool.shutdown()
    inventory_pool.shutdown()


BODY = {"booking_id": "bk_42", "amount": "4500.00", "currency": "UAH"}


def test_same_idempotency_key_charges_exactly_once():
    gateway = FakePaymentGateway()
    endpoint = PaymentEndpoint(gateway)
    first = endpoint.post_payment("key-123", BODY)
    second = endpoint.post_payment("key-123", BODY)      # мобільний застосунок повторив запит
    assert first == second and first.status == 201
    assert gateway.charges == 1


def test_different_keys_are_different_payments():
    gateway = FakePaymentGateway()
    endpoint = PaymentEndpoint(gateway)
    endpoint.post_payment("key-1", BODY)
    endpoint.post_payment("key-2", {**BODY, "booking_id": "bk_43"})
    assert gateway.charges == 2


def test_reused_key_with_other_body_is_rejected():
    gateway = FakePaymentGateway()
    endpoint = PaymentEndpoint(gateway)
    endpoint.post_payment("key-1", BODY)
    assert endpoint.post_payment("key-1", {**BODY, "amount": "1.00"}).status == 422
    assert gateway.charges == 1


def test_missing_key_is_rejected():
    assert PaymentEndpoint(FakePaymentGateway()).post_payment(None, BODY).status == 400


def test_concurrent_duplicates_charge_once():
    gateway = FakePaymentGateway()
    original = gateway.charge

    def slow_charge(*args):
        time.sleep(0.1)
        return original(*args)
    gateway.charge = slow_charge
    endpoint = PaymentEndpoint(gateway)
    results = []
    threads = [threading.Thread(target=lambda: results.append(endpoint.post_payment("key-x", BODY)))
               for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert gateway.charges == 1
    assert sorted(r.status for r in results) == [201, 409, 409, 409, 409]
