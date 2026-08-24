# DataHelix `solo` recipe — single-container production MVP.
#
# One container, one published port: nginx fronts the Aperture SPA (/) and
# reverse-proxies the data plane (/graphql, /docs, /health) to
# `mosaic serve --graphql` on SQLite. Process supervision via supervisord;
# the entrypoint runs the migrate-on-boot step first.
#
# The LinkML Modeler and its cors-proxy sidecar were removed by platform
# ADR-0005: not wired into anything, the only from-source build in a
# production recipe (an exception to decision 1.4), and the last pin on EOL
# Node 20. There is now no Node in this image at all.
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

ARG MOSAIC_IMAGE=ghcr.io/bu-neuromics/mosaic@sha256:ded29427e210253505fe42a9d58205418bc9df8e609a960fb34c30300ea8d278
ARG APERTURE_IMAGE=ghcr.io/bu-neuromics/aperture@sha256:0f710fa7b886089eb932e3b6c82ed62e87efb06d3252ff1fa2d48e1ad29ca083

FROM ${APERTURE_IMAGE} AS aperture

# ── Final stage: the bundle ─────────────────────────────────────────────────
FROM ${MOSAIC_IMAGE}

ARG MOSAIC_IMAGE
ARG APERTURE_IMAGE
ARG VERSION=dev
ARG REVISION=unknown

# Inner-pair provenance: a deploy gate can read these labels and verify the
# pair against the certification ledger (proposal §4.4).
LABEL org.opencontainers.image.title="datahelix-solo" \
      org.opencontainers.image.description="DataHelix solo recipe — Aperture + Mosaic, single container, SQLite" \
      org.opencontainers.image.source="https://github.com/BU-Neuromics/datahelix" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.datahelix.solo.mosaic-image="${MOSAIC_IMAGE}" \
      org.datahelix.solo.aperture-image="${APERTURE_IMAGE}"

USER root

# git: Mode R schema pull-on-boot (entrypoint.sh). libstdc++6 is gone with the
# node binary it supported.
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx supervisor git \
    && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled/default

# Static bundle
COPY --from=aperture /usr/share/nginx/html /srv/aperture

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
