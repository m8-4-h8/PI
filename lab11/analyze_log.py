"""Аналіз логу інциденту BookingService (варіант 1): таймлайн, перше відхилення, симуляція алертів,
error budget, MTTR. Лише стандартна бібліотека."""
import json
from datetime import datetime, timedelta
from pathlib import Path

LOG = Path(__file__).parent / "data" / "incident_log.jsonl"
records = [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines()]
for r in records:
    r["ts"] = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
requests = [r for r in records if r["status"] is not None]
first_504 = next(r for r in requests if r["status"] == 504)


def hhmmss(ts: datetime) -> str:
    return ts.strftime("%H:%M:%S.%f")[:-3]


def fmt_delta(delta: timedelta) -> str:
    seconds = delta.total_seconds()
    return f"{int(seconds // 60)} хв {seconds % 60:04.1f} с ({seconds / 60:.2f} хв)"


# 1. Таймлайн
print("1. Таймлайн")
print(f"{'час':<13}{'рівень':<7}{'booking':<10}{'мс':>6}{'пул':>8}{'пул %':>7}{'статус':>8}")
for r in records:
    pool_pct = 100 * r["db_pool_active"] / r["db_pool_max"]
    print(f"{hhmmss(r['ts']):<13}{r['level']:<7}{str(r.get('booking_id')):<10}"
          f"{str(r['duration_ms']):>6}{r['db_pool_active']:>5}/{r['db_pool_max']:<2}{pool_pct:>6.0f}%{str(r['status']):>8}")

# 2. Перше відхилення: латентність виходить за смугу «норми» перших 5 запитів (+20%)
baseline = requests[:5]
band_max = max(r["duration_ms"] for r in baseline)
first_dev = next(r for r in requests if r["duration_ms"] > band_max * 1.2)
print(f"\n2. Норма (перші 5 запитів): {min(r['duration_ms'] for r in baseline)}–{band_max} мс; "
      f"перше відхилення > {band_max * 1.2:.0f} мс: {hhmmss(first_dev['ts'])} "
      f"{first_dev['booking_id']} {first_dev['duration_ms']} мс, пул {first_dev['db_pool_active']}/{first_dev['db_pool_max']}")


# 3. Симуляція алертів: умова істинна на кроці між рядками логу; алерт спрацьовує після `for`.
def fire_time(condition, hold: timedelta, series):
    start = None
    for r in series:
        if condition(r):
            start = start or r["ts"]
            if r["ts"] - start >= hold:
                return start + hold
        else:
            if start and r["ts"] - start >= hold:
                return start + hold
            start = None
    return start + hold if start else None


def predict_linear(r, window=timedelta(minutes=10), horizon_s=600):
    pts = [p for p in records if r["ts"] - window <= p["ts"] <= r["ts"]]
    if len(pts) < 3:
        return False
    xs = [(p["ts"] - pts[0]["ts"]).total_seconds() for p in pts]
    ys = [p["db_pool_active"] for p in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    value_now = my + slope * (xs[-1] - mx)
    return value_now + slope * horizon_s >= r["db_pool_max"]


ALERTS = [
    ("BookingDbPoolSaturationWarning: пул >= 60% for 2m", lambda r: r["db_pool_active"] / r["db_pool_max"] >= 0.60, timedelta(minutes=2), records),
    ("BookingDbPoolSaturationCritical: пул >= 75% for 1m", lambda r: r["db_pool_active"] / r["db_pool_max"] >= 0.75, timedelta(minutes=1), records),
    ("BookingDbPoolExhaustionPredicted: predict_linear(10m, +10m) >= max for 1m", predict_linear, timedelta(minutes=1), records),
    ("BookingLatencyP99High: p99 > 300 мс for 2m", lambda r: r["duration_ms"] > 300, timedelta(minutes=2), requests),
    ("BookingErrorRateHigh: 5xx > 5% for 2m", lambda r: r["status"] >= 500, timedelta(minutes=2), requests),
]
print(f"\n3. Симуляція алертів (перший 504: {hhmmss(first_504['ts'])})")
for name, cond, hold, series in ALERTS:
    t = fire_time(cond, hold, series)
    lead = first_504["ts"] - t
    sign = "ДО" if lead.total_seconds() > 0 else "ПІСЛЯ"
    print(f"  {name:<75} спрацював би о {hhmmss(t)} -> {fmt_delta(abs(lead))} {sign} першого 504")

# 4. Error budget
slo = 0.999
month_min = 30 * 24 * 60
budget = (1 - slo) * month_min
violation_start = next(r for r in requests if r["duration_ms"] > 300)
recovered = next(r for r in requests if r["ts"] > first_504["ts"] and r["status"] == 200)
burned = (recovered["ts"] - violation_start["ts"]).total_seconds() / 60
burned_errors_only = (recovered["ts"] - first_504["ts"]).total_seconds() / 60
print("\n4. Error budget (SLO 99.9% за 30 днів)")
print(f"  хвилин у місяці: 30 * 24 * 60 = {month_min}")
print(f"  бюджет: (1 - 0.999) * {month_min} = {budget:.1f} хв")
print(f"  порушення SLO: {hhmmss(violation_start['ts'])} ({violation_start['duration_ms']} мс > 300) "
      f"-> {hhmmss(recovered['ts'])} ({recovered['duration_ms']} мс) = {burned:.2f} хв -> {100 * burned / budget:.1f}% бюджету")
print(f"  (лише з першого ERROR: {hhmmss(first_504['ts'])} -> {hhmmss(recovered['ts'])} = {burned_errors_only:.2f} хв "
      f"-> {100 * burned_errors_only / budget:.1f}% бюджету)")

# 5. MTTR
print("\n5. MTTR")
print(f"  перший ERROR {hhmmss(first_504['ts'])} -> стабільний 200 {hhmmss(recovered['ts'])}: "
      f"{fmt_delta(recovered['ts'] - first_504['ts'])}")
after = [r for r in requests if r["ts"] >= recovered["ts"]]
print(f"  після відновлення: {[(hhmmss(r['ts']), r['duration_ms'], r['db_pool_active'], r['db_pool_max']) for r in after]}")
