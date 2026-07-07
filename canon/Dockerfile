# Canon — DataHelix semantic artifact resolver
# Multi-stage build: install deps -> slim runtime

FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install ".[api]"

FROM python:3.12-slim

LABEL org.opencontainers.image.title="canon" \
      org.opencontainers.image.description="DataHelix semantic artifact resolver"

RUN groupadd -r datahelix && useradd -r -g datahelix -d /app datahelix
WORKDIR /app

COPY --from=builder /install /usr/local
COPY src/ ./src/

RUN mkdir -p /data/outputs && chown -R datahelix:datahelix /data /app

USER datahelix

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')" || exit 1

ENTRYPOINT ["uvicorn"]
CMD ["canon.api.app:app", "--host", "0.0.0.0", "--port", "8002"]
