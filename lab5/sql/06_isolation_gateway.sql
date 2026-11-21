-- Сесія B (платіжний шлюз): оновлює статус між двома читаннями оператора
\echo '--- B: UPDATE status = checked_in; COMMIT'
UPDATE bookings SET status = 'checked_in' WHERE id = 42;
