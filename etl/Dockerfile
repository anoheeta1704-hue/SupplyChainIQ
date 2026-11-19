FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev && rm -rf /var/lib/apt/lists/*

COPY backend/app /app/backend/app
COPY etl/pipeline.py /app/etl/pipeline.py
COPY storage /app/storage
COPY data-generator /app/data-generator

RUN pip install --no-cache-dir pandas sqlalchemy psycopg2-binary pydantic-settings structlog redis

WORKDIR /app
CMD ["python", "etl/pipeline.py"]
