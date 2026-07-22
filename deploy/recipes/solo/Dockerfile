# DataHelix `solo` recipe — single-container production MVP.
#
# One container, one published port: nginx fronts the Aperture SPA (/), the
# LinkML Modeler (/modeler/), and reverse-proxies the data plane (/graphql,
# /docs, /health) to `mosaic serve --graphql` on SQLite. Process supervision
# via supervisord; the entrypoint runs the migrate-on-boot step first.
# See README.md and proposals/deployment-recipes.md (§2.1).
#
# Built FROM the published, digest-pinned certified pair (platform ADR-0001,
# proposal decision 1.4/§4.4 middle path): the pins below MUST match
# certification/composition.lock.json — CI enforces this via check_pins.py,
# and the digests are recorded as OCI labels so a deploy gate can verify the
# bundle's provenance. Never build components from source in this recipe.
#
# NOTE (ADR-0004 Phase R done): the certified frontier pins Mosaic 0.12.1,
# published as ghcr.io/bu-neuromics/mosaic; the ledger key is now `mosaic`.
# The CLI inside the image is `mosaic`.

ARG MOSAIC_IMAGE=ghcr.io/bu-neuromics/mosaic@sha256:2ac3e3c10f86bbbb9d98ea770e46be641c1465f24d051cf6f799ff9bda1b884b
ARG APERTURE_IMAGE=ghcr.io/bu-neuromics/aperture@sha256:e240dc8a63c7f85fb5af3bddae4377a9d4aee282160a701c7d1a9611bda39af0

# The Modeler has no published image yet; build its static bundle at a pinned
# commit (self-contained multi-stage build landed via linkml-modeler-app#149).
ARG MODELER_REPO=https://github.com/BU-Neuromics/linkml-modeler-app.git
# Pinned to the squashed self-contained-Docker commit on the modeler's `dev`
# (BU-Neuromics/linkml-modeler-app#150).
ARG MODELER_REF=6a6f4723169d9953d050d3de9cb340a7a8f09c55

FROM ${APERTURE_IMAGE} AS aperture

# ── Modeler build stage ─────────────────────────────────────────────────────
FROM node:20-alpine AS modeler-build
ARG MODELER_REPO
ARG MODELER_REF
RUN apk add --no-cache git \
    && corepack enable && corepack prepare pnpm@10.33.0 --activate
WORKDIR /src
# fetch-by-ref works for both branch names and commit SHAs
RUN git init -q . \
    && git remote add origin "${MODELER_REPO}" \
    && git fetch -q --depth 1 origin "${MODELER_REF}" \
    && git checkout -q FETCH_HEAD
RUN pnpm install --frozen-lockfile --filter @linkml-editor/web...
# Base path /modeler/; git relay via the bundle's same-origin /cors-proxy.
RUN pnpm --filter @linkml-editor/core build \
    && VITE_BASE_URL=/modeler/ VITE_GIT_CORS_PROXY=/cors-proxy \
       pnpm --filter @linkml-editor/web build
# The CORS proxy ships as a tiny node service; install its runtime deps here.
RUN cd packages/proxy && npm install --omit=dev

# node runtime for the CORS proxy (glibc build — the final stage is Debian).
FROM node:20-slim AS node-runtime

# ── Final stage: the bundle ─────────────────────────────────────────────────
FROM ${MOSAIC_IMAGE}

ARG MOSAIC_IMAGE
ARG APERTURE_IMAGE
ARG MODELER_REF
ARG VERSION=dev
ARG REVISION=unknown

# Inner-pair provenance: a deploy gate can read these labels and verify the
# pair against the certification ledger (proposal §4.4).
LABEL org.opencontainers.image.title="datahelix-solo" \
      org.opencontainers.image.description="DataHelix solo recipe — Aperture + Mosaic + LinkML Modeler, single container, SQLite" \
      org.opencontainers.image.source="https://github.com/BU-Neuromics/datahelix" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.datahelix.solo.mosaic-image="${MOSAIC_IMAGE}" \
      org.datahelix.solo.aperture-image="${APERTURE_IMAGE}" \
      org.datahelix.solo.modeler-ref="${MODELER_REF}"

USER root

# libstdc++6: runtime dep of the node binary copied below (python-slim lacks it)
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx supervisor git libstdc++6 \
    && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled/default

# Static bundles + CORS proxy + node runtime
COPY --from=aperture /usr/share/nginx/html /srv/aperture
COPY --from=modeler-build /src/packages/web/dist /srv/modeler
COPY --from=modeler-build /src/packages/proxy /srv/cors-proxy
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node

COPY nginx.conf /etc/nginx/conf.d/solo.conf
COPY supervisord.conf /etc/supervisor/conf.d/solo.conf
COPY entrypoint.sh /usr/local/bin/solo-entrypoint
RUN chmod +x /usr/local/bin/solo-entrypoint && mkdir -p /project

WORKDIR /project
EXPOSE 8080

# Healthy = nginx is up AND the data plane behind it answers.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

ENTRYPOINT ["/usr/local/bin/solo-entrypoint"]
