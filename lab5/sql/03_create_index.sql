-- Крок 1. Композитний B-Tree: спочатку рівність (status), потім діапазон (created_at).
CREATE INDEX idx_bookings_status_created
    ON bookings (status, created_at);
ANALYZE bookings;
