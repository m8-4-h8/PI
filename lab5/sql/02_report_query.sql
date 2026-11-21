-- Щотижневий звіт: топ-20 готелів за сумою оплачених бронювань за поточний рік.
SELECT hotel_id, SUM(total) AS total_paid
FROM bookings
WHERE status = 'paid' AND created_at >= '2026-01-01'
GROUP BY hotel_id
ORDER BY total_paid DESC
LIMIT 20;
