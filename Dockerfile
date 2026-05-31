# Build stage
FROM python:3.11-slim as builder

WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Final stage
FROM python:3.11-slim

RUN useradd -m appuser
WORKDIR /code

COPY --from=builder /build/wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache /wheels/*

COPY ./app /code/app
COPY ./docs /code/docs
COPY ./certs /code/certs

# Static assets directories
RUN mkdir -p /code/app/static/avatars

RUN chown -R appuser:appuser /code
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8086", "--proxy-headers", "--forwarded-allow-ips", "*"]
