from notifications.gateways.base import MessageGateway


class FlakyGateway(MessageGateway):
    """Імітує збій мережі: перші `fail_times` спроб падають, далі передає реальному шлюзу."""

    def __init__(self, inner: MessageGateway, fail_times: int) -> None:
        self._inner = inner
        self._failures_left = fail_times

    def send(self, address: str, text: str) -> None:
        if self._failures_left > 0:
            self._failures_left -= 1
            raise ConnectionError("network error")
        self._inner.send(address, text)
