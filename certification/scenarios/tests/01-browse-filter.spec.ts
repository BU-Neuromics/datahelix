import { test, expect } from "../support/fixtures";
import { collectionUrl, sel, waitForApp } from "../support/app";

// GOLDEN PATH 1 of 4 — BROWSE / FILTER
// Collection ids are the introspected Query field names (aperture 0.2.0).
// Seams exercised: introspection enrichment + filter SDL (Aperture ADR-0029/0030).
// Proves: the SPA introspects the booted Mosaic, renders the Book collection,
// derives facets from the filter input shape (enum `format`, boolean `in_print`,
// ref `author`), and a facet selection narrows the result set.
//
// Fixture rows (see fixtures/bootstrap/data/seed.yaml): 5 Books, of which 4 are
// in_print (Pride, Emma, Left Hand, Hobbit) and 1 is not (Dispossessed);
// format spans hardcover/paperback/ebook/audiobook.

test("browse the Book collection and narrow it with a facet", async ({ page }) => {
  await page.goto(collectionUrl("books"));
  await waitForApp(page);

  // All five seeded Books are listed.
  const rows = sel.rowsFor(page);
  await expect(rows).toHaveCount(5 + 1); // +1 header row; adjust if the table has no header row
  await expect(page.getByText("Pride and Prejudice")).toBeVisible();

  // The facet panel is present (capability derived from the filter input object).
  await expect(sel.facetPanel(page)).toBeVisible();

  // Narrow by the boolean facet in_print=false → only "The Dispossessed" remains.
  // Facet options are keyed <filter-field>-<value> — the LinkML slot name the
  // server filters on (in_print), not the humanized column label ("In print").
  await sel.facetOption(page, "in_print-false").first().click();
  await expect(page.getByText("The Dispossessed")).toBeVisible();
  await expect(page.getByText("Pride and Prejudice")).toBeHidden();

  // The filter must be reflected in URL state (nuqs `filters`), so a browse
  // state is shareable/reproducible — a portal invariant.
  await expect(page).toHaveURL(/filters=/);
});
