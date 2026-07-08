import { test as base } from "@playwright/test";
import type { BrowserContext, Page } from "@playwright/test";
import { MOSAIC_GRAPHQL_URL, MOSAIC_TOKEN } from "./env";

// Local-run affordance: the certification stack serves the SPA behind an nginx
// reverse proxy that forwards /graphql to mosaic and injects the bearer
// (compose/aperture-nginx.certify.conf). When driving a bare `npm run dev`
// SPA locally there is no proxy — set LOCAL_GRAPHQL_PROXY=1 and the browser's
// same-origin /graphql calls are rewritten to MOSAIC_GRAPHQL_URL with
// MOSAIC_TOKEN, emulating the deployed topology. CI never sets it.
//
// Exported so scenarios that open EXTRA browser contexts (e.g. the
// control-plane reload-survival check) can apply the same emulation to them —
// the deployed nginx proxy fronts every context alike. No-op when
// LOCAL_GRAPHQL_PROXY is unset, so CI behavior is unchanged.
export async function emulateGraphqlProxy(target: Page | BrowserContext): Promise<void> {
  if (process.env.LOCAL_GRAPHQL_PROXY !== "1") return;
  await target.route("**/graphql", (route) =>
    route.continue({
      url: MOSAIC_GRAPHQL_URL,
      headers: {
        ...route.request().headers(),
        authorization: `Bearer ${MOSAIC_TOKEN || "certify"}`,
      },
    }),
  );
}

export const test = base.extend({
  page: async ({ page }, use) => {
    await emulateGraphqlProxy(page);
    await use(page);
  },
});
export { expect } from "@playwright/test";
