"""Мінімальна модель Kafka: топік = журнал (append-only), споживачі читають за offset.

Події не видаляються після читання (retention), кожна consumer group має власний offset.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Event:
    offset: int
    type: str
    key: str
    payload: dict


@dataclass
class Topic:
    name: str
    events: list[Event] = field(default_factory=list)

    def publish(self, type_: str, key: str, payload: dict) -> Event:
        event = Event(len(self.events), type_, key, payload)
        self.events.append(event)
        return event


class ConsumerGroup:
    """Offset зберігається брокером. Його комітять лише ПІСЛЯ обробки -> at-least-once."""

    def __init__(self, topic: Topic, group_id: str) -> None:
        self.topic = topic
        self.group_id = group_id
        self.committed_offset = 0

    def poll(self, max_events: int = 100) -> list[Event]:
        return self.topic.events[self.committed_offset:self.committed_offset + max_events]

    def commit(self, event: Event) -> None:
        self.committed_offset = event.offset + 1

    @property
    def lag(self) -> int:
        return len(self.topic.events) - self.committed_offset
