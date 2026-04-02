# Canon — BASS semantic artifact resolver
# Multi-stage build: install deps -> slim runtime

FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install ".[api]"

FROM python:3.12-slim

LABEL org.opencontainers.image.title="canon" \
      org.opencontainers.image.description="BASS semantic artifact resolver"

RUN groupadd -r bass && useradd -r -g bass -d /app bass
WORKDIR /app

COPY --from=builder /install /usr/local
COPY src/ ./src/

RUN mkdir -p /data/outputs && chown -R bass:bass /data /app

USER bass

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')" || exit 1

ENTRYPOINT ["uvicorn"]
CMD ["canon.api.app:app", "--host", "0.0.0.0", "--port", "8002"]
