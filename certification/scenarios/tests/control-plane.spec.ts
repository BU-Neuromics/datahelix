import { test, expect } from "@playwright/test";
import { collectionUrl, sel, waitForApp } from "../support/app";
import { gql, gqlContext } from "../support/graphql";

// GOLDEN PATH 4 of 4 — CONTROL-PLANE SAVED VIEWS / DRAFTS
// Seam exercised: the Aperture control-plane document type (Aperture ADR-0032) —
// `{kind,name,payload}` documents on a structurally-recognized Hippo collection.
// Proves: with the ApertureDocument recipe seeded, a saved view is persisted
// SERVER-SIDE (survives a full reload / new browser context), not just in
// localStorage. This is the scenario that only holds when the recipe is present
// — if the SPA fell back to localStorage the footer would say so and the
// server-side assertion below would (correctly) fail.

test("a saved view persists to the control-plane store and survives reload", async ({ page }) => {
  await page.goto(collectionUrl("Book", { filters: "" , q: "Le Guin" }));
  await waitForApp(page);

  // The shell must report the Hippo-backed control plane (not local fallback).
  await expect(sel.controlPlaneStatus(page)).not.toHaveText(/local storage/i);

  const viewName = `cert-view-${Date.now()}`;
  await sel.saveViewButton(page).click();
  await page.getByTestId("save-view-name").or(page.getByLabel(/name/i)).first().fill(viewName);
  await page.getByRole("button", { name: /save|confirm/i }).click();

  // Verify server-side: an ApertureDocument of kind=savedView with this name
  // exists and carries a versioned envelope payload. Query is tolerant of the
  // generated plural name via a small fallback list.
  const ctx = await gqlContext();
  const doc = await findSavedView(ctx, viewName);
  expect(doc, "saved view was not persisted to the Hippo control-plane store").toBeTruthy();
  const envelope = JSON.parse(doc!.payload);
  expect(envelope).toHaveProperty("v");   // versioned envelope {v, data} (ADR-0032)
  expect(envelope).toHaveProperty("data");
  await ctx.dispose();

  // Survives a brand-new browser context (proves it's not browser-local).
  const fresh = await page.context().browser()!.newContext();
  const p2 = await fresh.newPage();
  await p2.goto(collectionUrl("Book"));
  await waitForApp(p2);
  await expect(sel.savedViewNamed(p2, viewName)).toBeVisible();
  await fresh.close();
});

// The control-plane collection's generated plural query name depends on Hippo's
// pluralizer; try the common forms rather than hard-coding one.
async function findSavedView(
  ctx: Awaited<ReturnType<typeof gqlContext>>,
  name: string,
): Promise<{ kind: string; name: string; payload: string } | null> {
  const candidates = ["apertureDocuments", "aperturedocuments", "ApertureDocuments"];
  for (const field of candidates) {
    try {
      const data = await gql<Record<string, any[]>>(
        ctx,
        `query CertCP { ${field}(limit: 500) { kind name payload } }`,
      );
      const hit = (data[field] ?? []).find(
        (d) => d.name === name && d.kind === "savedView",
      );
      if (hit) return hit;
      return null; // field resolved but no match
    } catch {
      // wrong field name for this deployment — try the next candidate
    }
  }
  return null;
}
