from abc import ABC, abstractmethod


class MessageGateway(ABC):
    """Транспорт, що реально доставляє повідомлення (SMTP, SMS-провайдер, push-сервіс)."""

    @abstractmethod
    def send(self, address: str, text: str) -> None:
        """Кидає ConnectionError, якщо доставка не вдалася."""
