# Cappella — BASS workflow / harmonization engine
# Multi-stage build: install deps -> slim runtime

FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

LABEL org.opencontainers.image.title="cappella" \
      org.opencontainers.image.description="BASS workflow harmonization engine"

RUN groupadd -r bass && useradd -r -g bass -d /app bass
WORKDIR /app

COPY --from=builder /install /usr/local
COPY src/ ./src/

RUN mkdir -p /data && chown -R bass:bass /data /app

USER bass

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')" || exit 1

ENTRYPOINT ["uvicorn"]
CMD ["cappella.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8003"]
