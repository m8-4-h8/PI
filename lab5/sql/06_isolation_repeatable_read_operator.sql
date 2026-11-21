-- Сесія A (оператор підтримки), рівень REPEATABLE READ
\echo '--- A: BEGIN ISOLATION LEVEL REPEATABLE READ'
BEGIN ISOLATION LEVEL REPEATABLE READ;
\echo '--- A: перше читання'
SELECT id, total, status FROM bookings WHERE id = 42;
SELECT pg_sleep(2);   -- у цей час сесія B оновлює статус
\echo '--- A: друге читання'
SELECT id, total, status FROM bookings WHERE id = 42;
\echo '--- A: UPDATE (часткове повернення)'
UPDATE bookings SET total = total - 100 WHERE id = 42;
COMMIT;
