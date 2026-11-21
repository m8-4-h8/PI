#!/usr/bin/env bash
# Відтворення всіх вимірів Лабораторної №5.
# Потрібен PostgreSQL 13+, напр.: docker run -e POSTGRES_PASSWORD=pass -p 5432:5432 postgres:16
# Запуск: PGHOST=localhost PGPORT=5432 PGUSER=postgres PGPASSWORD=pass ./run_lab.sh
set -euo pipefail
cd "$(dirname "$0")"
P="psql -X -v ON_ERROR_STOP=1"
Q="$(grep -v '^--' sql/02_report_query.sql)"
mkdir -p results

$P -f sql/01_seed_bookings.sql
$P -c "DROP INDEX IF EXISTS idx_bookings_status_created; DROP INDEX IF EXISTS idx_bookings_paid_report;"
$P -c "EXPLAIN (ANALYZE, BUFFERS) $Q" > /dev/null            # прогрів кешу
$P -c "EXPLAIN (ANALYZE, BUFFERS) $Q" > results/explain_before.txt

$P -f sql/03_create_index.sql
$P -c "EXPLAIN (ANALYZE, BUFFERS) $Q" > /dev/null
$P -c "EXPLAIN (ANALYZE, BUFFERS) $Q" > results/explain_after_index1.txt

$P -f sql/04_covering_index.sql
$P -c "EXPLAIN (ANALYZE, BUFFERS) $Q" > /dev/null
$P -c "EXPLAIN (ANALYZE, BUFFERS) $Q" > results/explain_after_index2.txt

$P -f sql/05_insert_cost.sql > results/insert_cost.txt

for lvl in read_committed repeatable_read serializable; do
    $P -qc "UPDATE bookings SET status = 'paid' WHERE id = 42"
    psql -X -f "sql/06_isolation_${lvl}_operator.sql" > /tmp/op.txt 2>&1 &
    sleep 1
    psql -X -f sql/06_isolation_gateway.sql > /tmp/gw.txt 2>&1
    wait
    { echo "=== Сесія A (оператор)"; cat /tmp/op.txt; echo; echo "=== Сесія B (шлюз)"; cat /tmp/gw.txt; } \
        > "results/isolation_${lvl}.txt"
done
grep -h "Execution Time" results/explain_*.txt
