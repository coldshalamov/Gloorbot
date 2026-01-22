FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Copy the category list from repository root (Render's rootDir is apps/coordinator)
# This file is at ../../PARALLEL/urls.txt relative to the Dockerfile
COPY ../../PARALLEL/urls.txt /app/data/urls.txt

ENV PORT=8000
CMD ["sh", "-c", "uvicorn coordinator_app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
