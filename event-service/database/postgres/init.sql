DROP DATABASE IF EXISTS event_db;

CREATE DATABASE event_db;

-- Switch to the newly created database
\connect event_db;


CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    date TIMESTAMP,
    venue VARCHAR(255)
);


INSERT INTO events (title, description, date, venue)
VALUES ('Rock Concert', 'A thrilling rock concert with live performances.', '2025-07-01 19:00:00', 'Arena Lviv');
