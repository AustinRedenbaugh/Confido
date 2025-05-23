-- Drop the table if it already exists
DROP TABLE IF EXISTS insurance_details;
-- Create the insurance_details table
CREATE TABLE insurance_details (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    accepted BOOLEAN NOT NULL DEFAULT TRUE
);