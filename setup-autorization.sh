docker compose -f autorization-dc.yml up -d

docker exec -i postgres_container createdb autorization -U admin

docker exec -i postgres_container psql autorization -U admin -c "CREATE TABLE logging_password (
    login           varchar(30),
    password        varchar(60),
    user_id         int);"
