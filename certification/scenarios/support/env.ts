// Endpoints the golden-path suite drives. Defaults match the certification
// compose stack (docker-compose.certify.yml); override via env for local runs
// against `npm run dev` + a local `hippo serve --graphql`.

export const APERTURE_URL =
  process.env.APERTURE_URL ?? "http://localhost:5173";

export const HIPPO_GRAPHQL_URL =
  process.env.HIPPO_GRAPHQL_URL ?? "http://localhost:8001/graphql";

// A bearer token if the booted Hippo requires one for POST /graphql. The
// certification stack runs Hippo with bridge disabled (auth out of seam scope),
// so this is normally empty.
export const HIPPO_TOKEN = process.env.HIPPO_TOKEN ?? "";
