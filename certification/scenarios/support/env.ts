// Endpoints the golden-path suite drives. Defaults match the certification
// compose stack (docker-compose.certify.yml); override via env for local runs
// against `npm run dev` + a local `mosaic serve --graphql` (ADR-0004 —
// formerly `hippo serve --graphql`).

export const APERTURE_URL =
  process.env.APERTURE_URL ?? "http://localhost:5173";

export const MOSAIC_GRAPHQL_URL =
  process.env.MOSAIC_GRAPHQL_URL ?? "http://localhost:8001/graphql";

// A bearer token if the booted Mosaic requires one for POST /graphql. The
// certification stack runs Mosaic with bridge disabled (auth out of seam
// scope), so this is normally empty.
export const MOSAIC_TOKEN = process.env.MOSAIC_TOKEN ?? "";
