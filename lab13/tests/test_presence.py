import simulate_presence
from messenger.presence import BATCH_WINDOW, PresenceService


def make_pair():
    service = PresenceService()
    service.connect(1, 0)          # Аліса
    service.connect(2, 0)          # Боб дивиться чат з Алісою
    service.subscribe(2, [1])
    service.tick(BATCH_WINDOW)
    service.events = 0
    return service


def test_short_background_inside_grace_sends_nothing():
    service = make_pair()
    service.disconnect(1, 10, "background")
    service.tick(20)
    service.connect(1, 25)                       # повернулась за 15 с < 30 с
    for t in range(26, 80):
        service.tick(t)

    assert service.events == 0 and service.absorbed_flaps == 1


def test_offline_after_grace_goes_only_to_subscribers_with_last_seen_of_disconnect():
    service = make_pair()
    service.connect(3, 0)                        # Карл онлайн, але чат з Алісою не відкритий
    service.disconnect(1, 10, "background")
    for t in range(11, 45):
        service.tick(t)

    assert service.events == 1
    assert service.visible[1] == "offline" and service.last_seen[1] == 10


def test_flapping_inside_one_batch_window_is_coalesced_to_last_state():
    service = make_pair()
    service.connect(4, 0)
    service.subscribe(2, [1, 4])
    service.disconnect(4, 1, "logout")           # logout: grace = 0
    service.tick(1)
    service.connect(4, 1.5)
    service.tick(1.6)
    service.events = 0
    service.frames = 0
    service.tick(BATCH_WINDOW * 3)

    assert service.events == 1 and service.frames == 1   # один кадр, лише останній стан


def test_subscriptions_are_capped():
    service = PresenceService()
    snapshot = service.subscribe(1, list(range(2, 100)))
    assert len(snapshot) == 20


def test_zone_failure_fanout_is_orders_of_magnitude_smaller():
    result = simulate_presence.run(users=1_500, quiet=True)

    assert result["smart"] * 20 < result["naive"]
    assert result["fail_smart"] * 50 < result["fail_naive"]
    assert result["absorbed"] > 0.9 * result["victims"]
