import pytest

import simulate_dedup
from messenger.dedup import Clock, Crash, DedupCache, Device, MessageService, MessageStore


@pytest.fixture
def env():
    clock = Clock()
    store = MessageStore()
    cache = DedupCache(clock)
    return clock, store, cache


def test_retry_with_same_id_does_not_create_second_row(env):
    clock, store, cache = env
    service = MessageService(store, cache, clock)
    alice = Device(1, device_id=101)
    item = alice.compose(conversation_id=7, text="привіт")

    first = service.send(7, item.message_id, 1, item.text, attempt=1)
    again = service.send(7, item.message_id, 1, item.text, attempt=2)   # ACK загубився -> повтор

    assert store.row_count() == 1
    assert again.duplicate and again.server_seq == first.server_seq


def test_crash_after_persist_then_redis_failover_is_caught_by_store_lookup(env):
    clock, store, cache = env
    crash_once = iter([False, True])        # after_claim: ні, after_persist: так
    service = MessageService(store, cache, clock, faults=lambda point: next(crash_once, False))
    item = Device(1, 101).compose(7, "оплата за обід")

    with pytest.raises(Crash):
        service.send(7, item.message_id, 1, item.text, attempt=1)
    cache.flush()                           # Redis failover: ключ dedup втрачено
    clock.advance(5)
    ack = service.send(7, item.message_id, 1, item.text, attempt=2)

    assert store.row_count() == 1
    assert ack.duplicate and service.stats.dup_from_store == 1


def test_live_pending_answers_in_progress_and_stale_pending_is_taken_over(env):
    clock, store, cache = env
    crash_once = iter([True])               # впали одразу після claim, до запису
    service = MessageService(store, cache, clock, faults=lambda point: next(crash_once, False))
    item = Device(1, 101).compose(7, "x")

    with pytest.raises(Crash):
        service.send(7, item.message_id, 1, item.text, attempt=1)
    clock.advance(3)
    assert service.send(7, item.message_id, 1, item.text, attempt=2).in_progress
    clock.advance(MessageService.LEASE)
    ack = service.send(7, item.message_id, 1, item.text, attempt=3)

    assert ack.server_seq == 1 and not ack.duplicate
    assert service.stats.took_over_stale == 1 and store.row_count() == 1


def test_receiver_drops_duplicates_and_fills_gap_via_sync(env):
    clock, store, cache = env
    service = MessageService(store, cache, clock)
    alice, bob = Device(1, 101), Device(2, 202)
    seqs = [service.send(7, alice.compose(7, f"m{i}").message_id, 1, f"m{i}", 1).server_seq for i in range(3)]
    m1, m2, m3 = (store.messages[7][s] for s in seqs)

    assert bob.on_deliver(m1) == "shown"
    assert bob.on_deliver(m1) == "duplicate"
    assert bob.on_deliver(m3) == "gap"      # m2 загубився
    bob.sync(store, 7)

    assert [m.server_seq for m in bob.timeline[7]] == [1, 2, 3]
    assert bob.stats.duplicates_dropped == 1 and bob.stats.recovered_by_sync == 2


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_lossy_network_every_member_sees_each_message_exactly_once_in_order(seed):
    result = simulate_dedup.run(seed=seed, messages=3_000, quiet=True)

    assert result["ok"]
    assert result["rows"] == result["composed"]
    assert result["arrived"] - result["crashes"]["after_claim"] > result["rows"]   # без dedup були б дублі
