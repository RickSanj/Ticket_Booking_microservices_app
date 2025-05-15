CREATE KEYSPACE IF NOT EXISTS bookings_db
    WITH REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : 3 };

USE bookings_db;

CREATE TABLE IF NOT EXISTS tickets (
    event_id int,
    ticket_id int,
    seat_number text,
    price decimal,
    PRIMARY KEY (event_id, ticket_id)
);


CREATE TABLE IF NOT EXISTS bookings (
    event_id int,
    ticket_id int,
    user_id int,
    booking_time timestamp,
    PRIMARY KEY (event_id, ticket_id)
);

INSERT INTO tickets (event_id, ticket_id, seat_number, price)
VALUES (1, 101, 'A1', 100.00);

INSERT INTO tickets (event_id, ticket_id, seat_number, price)
VALUES (1, 102, 'A2', 100.00);

INSERT INTO tickets (event_id, ticket_id, seat_number, price)
VALUES (1, 103, 'A3', 120.00);