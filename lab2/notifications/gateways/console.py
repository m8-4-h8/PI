from notifications.gateways.base import MessageGateway


class ConsoleGateway(MessageGateway):
    def __init__(self, label: str) -> None:
        self._label = label

    def send(self, address: str, text: str) -> None:
        print(f"Sending {self._label} to {address}: {text}")
