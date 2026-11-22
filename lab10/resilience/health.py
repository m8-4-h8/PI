"""Завдання 5. HousekeepingService: /health/live, /health/ready і graceful shutdown (stdlib)."""
import json
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class FakeDbPool:
    def __init__(self) -> None:
        self.available = True
        self.closed = False

    def ping(self) -> bool:
        return self.available and not self.closed

    def close(self) -> None:
        self.closed = True


class HousekeepingService:
    def __init__(self, port: int = 0, db: FakeDbPool | None = None) -> None:
        self.db = db or FakeDbPool()
        self.shutting_down = False
        self.log: list[str] = []
        self._in_flight = 0
        self._cond = threading.Condition()
        service = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):          # тиша в консолі
                pass

            def _json(self, status: int, body: dict) -> None:
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                url = urlparse(self.path)
                if url.path == "/health/live":
                    # Liveness: лише «процес живий і обробляє HTTP». Жодних залежностей!
                    return self._json(200, {"status": "alive"})
                if url.path == "/health/ready":
                    # Readiness: чи можна зараз слати сюди трафік.
                    if service.shutting_down:
                        return self._json(503, {"status": "shutting_down"})
                    if not service.db.ping():
                        return self._json(503, {"status": "db_unavailable"})
                    return self._json(200, {"status": "ready"})
                if url.path == "/tasks":
                    with service._cond:
                        service._in_flight += 1
                    try:
                        work = float(parse_qs(url.query).get("work", ["0"])[0])
                        time.sleep(work)            # імітація роботи з БД
                        return self._json(200, {"tasks": ["clean room 305"], "db_closed": service.db.closed})
                    finally:
                        with service._cond:
                            service._in_flight -= 1
                            service._cond.notify_all()
                return self._json(404, {"error": "not found"})

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()

    @property
    def in_flight(self) -> int:
        with self._cond:
            return self._in_flight

    def graceful_shutdown(self, deregistration_wait: float = 5.0, drain_timeout: float = 30.0) -> None:
        # Крок 1: отримали SIGTERM.
        self.log.append("1. SIGTERM received")
        # Крок 2: дерегістрація -- readiness віддає 503, балансувальник перестає слати трафік.
        self.shutting_down = True
        self.log.append("2. readiness -> 503, waiting for load balancer to deregister")
        time.sleep(deregistration_wait)
        # Крок 3: чекаємо завершення запитів, що вже виконуються.
        with self._cond:
            finished = self._cond.wait_for(lambda: self._in_flight == 0, timeout=drain_timeout)
        self.log.append(f"3. in-flight requests drained (all finished: {finished})")
        self.server.shutdown()
        # Крок 4: закриваємо ресурси (пул БД, продюсер Kafka тощо) і виходимо.
        self.db.close()
        self.server.server_close()
        self.log.append("4. resources closed, exiting")


def main() -> None:
    service = HousekeepingService(port=8080)
    service.start()
    done = threading.Event()

    def on_sigterm(signum, frame):
        threading.Thread(target=lambda: (service.graceful_shutdown(), done.set())).start()

    signal.signal(signal.SIGTERM, on_sigterm)
    print(f"HousekeepingService on :{service.port}  (kill -TERM {__import__('os').getpid()})")
    done.wait()
    print("\n".join(service.log))


if __name__ == "__main__":
    main()
