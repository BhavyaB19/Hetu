FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

COPY . .

EXPOSE 8000
# Migrate, load the illustrative demo case, then serve.
CMD ["sh", "-c", "alembic upgrade head && python -m app.cli fixtures/jan-mat-v-state.json && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
