-- Сесія A (оператор підтримки), рівень READ COMMITTED
\echo '--- A: BEGIN ISOLATION LEVEL READ COMMITTED'
BEGIN ISOLATION LEVEL READ COMMITTED;
\echo '--- A: перше читання'
SELECT id, total, status FROM bookings WHERE id = 42;
SELECT pg_sleep(2);   -- у цей час сесія B оновлює статус
\echo '--- A: друге читання'
SELECT id, total, status FROM bookings WHERE id = 42;

COMMIT;
