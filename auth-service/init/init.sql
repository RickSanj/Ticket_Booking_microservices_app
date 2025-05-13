CREATE DATABASE authorization;
\connect authorization;

CREATE TABLE logging_password (
    login VARCHAR(30),
    password VARCHAR(60),
    user_id INT
);
