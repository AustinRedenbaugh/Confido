-- Drop the table if it already exists
DROP TABLE IF EXISTS appt_slots;
-- Create the appt_slots table
CREATE TABLE appt_slots (
    id SERIAL PRIMARY KEY,
    start_time TIMESTAMPTZ NOT NULL,
    is_available BOOLEAN NOT NULL DEFAULT TRUE
);