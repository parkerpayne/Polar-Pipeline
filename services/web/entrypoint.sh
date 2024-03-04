#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"

    while ! nc -z $RABBIT_HOST $RABBIT_PORT; do
      sleep 0.1
    done

    echo "RabbitMQ started"
fi

python manage.py create_db

exec "$@"
