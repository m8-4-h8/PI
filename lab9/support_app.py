"""Внутрішній інструмент служби підтримки: пошук гостя за прізвищем (варіант 1)."""
from flask import Flask, jsonify, request

from guest_db import make_db

app = Flask(__name__)
db = make_db()


# ВРАЗЛИВА версія -- залишена лише для демонстрації ін'єкції в тестах.
@app.route("/internal/support/guests-vulnerable")
def search_guests_vulnerable():
    last_name = request.args.get("last_name")
    query = f"SELECT id, email, phone, loyalty_points FROM guests " \
            f"WHERE last_name = '{last_name}'"          # <-- ІН'ЄКЦІЯ: дані вклеєні в текст SQL
    rows = db.execute(query).fetchall()
    return jsonify(rows)


# ВИПРАВЛЕНА версія: параметризований запит.
@app.route("/internal/support/guests")
def search_guests():
    last_name = request.args.get("last_name", "")
    if not last_name or len(last_name) > 100:
        return jsonify({"error": "last_name is required (1..100 chars)"}), 422
    rows = db.execute(
        "SELECT id, email, phone, loyalty_points FROM guests WHERE last_name = ?",
        (last_name,),                                   # значення передається окремо від SQL
    ).fetchall()
    return jsonify(rows)


if __name__ == "__main__":
    client = app.test_client()
    payload = "' OR '1'='1"
    for path in ("/internal/support/guests-vulnerable", "/internal/support/guests"):
        rows = client.get(path, query_string={"last_name": payload}).get_json()
        print(f"{path}?last_name={payload!r} -> {len(rows)} рядків: {rows}")
    rows = client.get("/internal/support/guests", query_string={"last_name": "O'Brien"}).get_json()
    print(f"/internal/support/guests?last_name=\"O'Brien\" -> {rows}")
