-- Крок 2. Покривний індекс: ті самі ключі + hotel_id і total у INCLUDE,
-- щоб запит читав лише індекс (Index Only Scan) і не ходив у таблицю.
DROP INDEX IF EXISTS idx_bookings_status_created;
CREATE INDEX idx_bookings_paid_report
    ON bookings (status, created_at) INCLUDE (hotel_id, total);
VACUUM ANALYZE bookings;   -- оновлює visibility map, без неї Index Only Scan ходить у heap
