DO $$
DECLARE current_date DATE := CURRENT_DATE;
end_date DATE := CURRENT_DATE + INTERVAL '21 days';
slot_time TIME;
day DATE;
BEGIN FOR day IN
SELECT generate_series(current_date, end_date, '1 day')::date LOOP -- Skip Sundays (DOW = 0)
    IF EXTRACT(
        DOW
        FROM day
    ) != 0 THEN slot_time := TIME '08:00';
WHILE slot_time <= TIME '16:30' LOOP -- This assumes your server/session timezone is set to UTC-4
INSERT INTO appt_slots (start_time)
VALUES ((day + slot_time)::timestamptz);
slot_time := slot_time + INTERVAL '30 minutes';
END LOOP;
END IF;
END LOOP;
END $$;
-- Populate insurance_details with sample values
INSERT INTO insurance_details (name, accepted)
VALUES ('BlueCross BlueShield', TRUE),
    ('UnitedHealthcare', TRUE),
    ('Aetna', TRUE),
    ('Cigna', FALSE),
    ('Humana', TRUE),
    ('Kaiser Permanente', FALSE);