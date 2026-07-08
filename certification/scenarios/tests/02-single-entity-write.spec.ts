import { test, expect } from "../support/fixtures";
import { newEntityFormUrl, sel, waitForApp, collectionUrl } from "../support/app";
import { countCollection, gqlContext } from "../support/graphql";

// GOLDEN PATH 2 of 4 — SINGLE-ENTITY WRITE
// Seam exercised: create mutation derived from the entity's input type
// (Aperture ADR-0027 write portal; form model from schemaModel.deriveWriteModel).
// Proves: the SPA renders a create form from introspection, submits a single
// `create<Entity>` mutation, and the new entity is retrievable at the seam.

test("create a single Author through the derived form", async ({ page }) => {
  const ctx = await gqlContext();
  const before = await countCollection(ctx, "authors");

  await page.goto(newEntityFormUrl("authors"));
  await expect(sel.entityForm(page)).toBeVisible({ timeout: 20_000 });

  const unique = `Cert Author ${Date.now()}`;
  await sel.fieldInput(page, "name").fill(unique);
  await sel.fieldInput(page, "bio").fill("Created by the certification golden path.");
  await sel.submitButton(page).click();

  // UI lands back on the collection and shows the new row.
  await page.goto(collectionUrl("authors"));
  await waitForApp(page);
  await expect(page.getByText(unique)).toBeVisible();

  // Verify at the seam: exactly one new Author committed (not a client illusion).
  const after = await countCollection(ctx, "authors");
  expect(after).toBe(before + 1);
  await ctx.dispose();
});
