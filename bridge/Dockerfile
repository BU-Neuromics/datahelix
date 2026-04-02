# Bridge — BASS API gateway (nginx reverse proxy)
#
# Bridge's application layer is not yet implemented. This image provides
# the gateway routing pattern (single exposed port, internal fan-out)
# using nginx until the full Bridge auth/proxy service ships.

FROM nginx:1.27-alpine

LABEL org.opencontainers.image.title="bridge" \
      org.opencontainers.image.description="BASS API gateway (nginx proxy)"

RUN addgroup -S bass && adduser -S bass -G bass

COPY bridge/nginx.conf /etc/nginx/nginx.conf

RUN mkdir -p /var/cache/nginx /var/run && \
    chown -R bass:bass /var/cache/nginx /var/run /etc/nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:8080/bridge/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
