from dataclasses import dataclass, field


@dataclass(frozen=True)
class Customer:
    email: str
    phone: str = ""
    # Канали, на які клієнт погодився. Набір, а не прапорці wants_email/wants_sms:
    # новий канал не вимагає нового поля в моделі.
    channels: frozenset[str] = field(default_factory=lambda: frozenset({"email"}))

    def wants(self, channel: str) -> bool:
        return channel in self.channels


@dataclass(frozen=True)
class Order:
    id: int
    customer: Customer
    total: float
