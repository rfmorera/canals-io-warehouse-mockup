#!/bin/sh
set -e

alembic upgrade head

exec gunicorn -b 0.0.0.0:${APP_PORT:-5000} "app:create_app()"
