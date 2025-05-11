-- CREATE DATABASE event_db;
-- Switch to database
\c event_db;

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    date_time TIMESTAMP,
    venue VARCHAR(255),
    performer VARCHAR(255)
);

-- Insert a sample event
INSERT INTO events (title, date_time, venue, performer)
VALUES 
('Rock Concert', '2025-07-01 19:00:00', 'Arena Lviv', 'John Smith');
