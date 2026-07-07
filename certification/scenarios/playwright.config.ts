import { defineConfig, devices } from "@playwright/test";
import { APERTURE_URL } from "./support/env";

// The certification suite is small BY POLICY (platform ADR-0001): one
// golden-path scenario per product loop, under a hard wall-clock budget. The
// budget is enforced twice — here (globalTimeout) and by run_composition.sh
// (BUDGET_SECONDS, which also covers artifact pull + boot + seed). A new
// scenario that would blow the budget must merge with or replace another, or
// move to the non-blocking nightly tier.
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,          // golden path is a sequenced journey; keep it legible
  forbidOnly: !!process.env.CI,
  retries: 0,                    // a flake IS a certification signal — don't paper over it
  workers: 1,
  reporter: [["list"], ["json", { outputFile: "playwright-report.json" }]],
  globalTimeout: 5 * 60 * 1000,  // 5 min for the whole suite (well under the 10-min run budget)
  timeout: 60 * 1000,            // 60s per scenario
  expect: { timeout: 10 * 1000 },
  use: {
    baseURL: APERTURE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
