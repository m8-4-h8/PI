-- Вартість INSERT: 200 000 нових бронювань з покривним індексом і без нього.
-- Обидва виміри в транзакції з ROLLBACK, щоб не змінювати дані.
\timing on
BEGIN;
INSERT INTO bookings (hotel_id, guest_email, total, status, created_at)
SELECT 1 + (random()*1999)::int, 'guest' || g || '@hotel.test',
       (random()*3000)::numeric(12,2), 'created', now()
FROM generate_series(1, 200000) g;
ROLLBACK;
DROP INDEX idx_bookings_paid_report;
BEGIN;
INSERT INTO bookings (hotel_id, guest_email, total, status, created_at)
SELECT 1 + (random()*1999)::int, 'guest' || g || '@hotel.test',
       (random()*3000)::numeric(12,2), 'created', now()
FROM generate_series(1, 200000) g;
ROLLBACK;
CREATE INDEX idx_bookings_paid_report
    ON bookings (status, created_at) INCLUDE (hotel_id, total);
VACUUM ANALYZE bookings;
