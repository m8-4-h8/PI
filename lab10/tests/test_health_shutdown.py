import json
import threading
import time
import urllib.error
import urllib.request

from resilience.health import HousekeepingService


def get(port, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_live_and_ready_have_different_logic():
    service = HousekeepingService()
    service.start()
    assert get(service.port, "/health/ready")[0] == 200
    service.db.available = False                          # БД недоступна
    assert get(service.port, "/health/ready") == (503, {"status": "db_unavailable"})
    assert get(service.port, "/health/live") == (200, {"status": "alive"})   # процес не перезапускаємо
    service.db.available = True
    service.graceful_shutdown(deregistration_wait=0, drain_timeout=1)


def test_graceful_shutdown_order():
    service = HousekeepingService()
    service.start()
    port = service.port
    slow = {}
    t = threading.Thread(target=lambda: slow.update(r=get(port, "/tasks?work=0.6")))
    t.start()
    time.sleep(0.1)
    assert service.in_flight == 1

    shutdown = threading.Thread(target=service.graceful_shutdown, kwargs={"deregistration_wait": 0.2})
    shutdown.start()
    time.sleep(0.1)
    assert get(port, "/health/ready") == (503, {"status": "shutting_down"})   # крок 2
    assert get(port, "/health/live")[0] == 200
    t.join()
    shutdown.join()
    status, body = slow["r"]
    assert status == 200 and body["db_closed"] is False   # запит завершився до закриття ресурсів
    assert service.db.closed
    assert [line[0] for line in service.log] == ["1", "2", "3", "4"]
