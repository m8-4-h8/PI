-- Лабораторна №5, варіант 1: таблиця bookings мережі готелів (5 млн рядків).
-- Детермінована генерація: фіксований seed і фіксована "поточна" дата 2026-11-21.
DROP TABLE IF EXISTS bookings;

CREATE TABLE bookings (
    id          BIGSERIAL PRIMARY KEY,
    hotel_id    INT           NOT NULL,
    guest_email TEXT          NOT NULL,
    total       NUMERIC(12,2) NOT NULL,
    status      TEXT          NOT NULL DEFAULT 'created',
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT now()
);

SELECT setseed(0.42);

INSERT INTO bookings (hotel_id, guest_email, total, status, created_at)
SELECT
    1 + (random()*1999)::int,
    'guest' || (random()*300000)::int || '@hotel.test',
    (random()*3000)::numeric(12,2),
    (ARRAY['created','paid','checked_in','cancelled'])[floor(random()*4+1)],
    timestamptz '2026-11-21 00:00:00+02' - (random() * interval '730 days')
FROM generate_series(1, 5000000);

ANALYZE bookings;
