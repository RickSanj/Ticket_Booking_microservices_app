CREATE TABLE logging_password (
    login VARCHAR(30),
    password VARCHAR(60),
    admin BOOLEAN,
    user_id INT
);

INSERT INTO logging_password (login, password, admin, user_id)