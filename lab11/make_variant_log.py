"""Варіант 1: той самий лог із PDF, але для BookingService мережі готелів.

Змінюються лише назва сервісу, ідентифікатори (order_id -> booking_id) і тексти повідомлень.
Усі timestamp, trace_id, duration_ms, db_pool_active, db_pool_max, status, error_code -- без змін.
"""
import json
from pathlib import Path

MESSAGES = {
    "charge authorized": "booking confirmed",
    "charge authorized, pool nearing capacity": "booking confirmed, rooms-db pool nearing capacity",
    "authorization failed": "booking failed",
    "on-call paged: saturation alert fired 6 minutes ago": "on-call paged: saturation alert fired 6 minutes ago",
    "db connection pool resized by on-call": "rooms-db connection pool resized by on-call",
}

src = Path(__file__).parent / "data" / "incident_log_original.jsonl"
dst = Path(__file__).parent / "data" / "incident_log.jsonl"
with dst.open("w", encoding="utf-8") as out:
    for line in src.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        converted = {}
        for key, value in record.items():
            if key == "service":
                value = "booking-service"
            if key == "message":
                value = MESSAGES[value]
            if key == "order_id":
                key, value = "booking_id", value and value.replace("ord_", "bk_")
            converted[key] = value
        out.write(json.dumps(converted, ensure_ascii=False, separators=(",", ":")) + "\n")
print(f"written {dst}")
