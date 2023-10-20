#!/bin/bash
# Start Gunicorn server
gunicorn -k uvicorn.workers.UvicornWorker -w 1 -b 0.0.0.0:80 api_app.main:app --access-logfile - --error-logfile -
# Run Alembic migrations
alembic upgrade head
