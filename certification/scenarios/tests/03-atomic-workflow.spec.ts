import { test, expect } from "../support/fixtures";
import { workflowUrl, sel } from "../support/app";
import { countCollection, gqlContext } from "../support/graphql";

// GOLDEN PATH 3 of 4 — ATOMIC MULTI-ENTITY WORKFLOW (the batch unit-of-work seam)
// Seam exercised: `batchPut` / batch unit-of-work (Aperture ADR-0028; Hippo #84).
// Proves the load-bearing cross-component contract: a guided workflow STAGES a
// linked set (Author → Book → Review, the Book/Review referencing the
// not-yet-committed parents by batch ref), runs a whole-set dry-run, then
// commits ALL-OR-NOTHING in one Hippo batch. Nothing is visible until commit.
//
// Requires the SPA to be built with a workflow config that stages this set
// (VITE_WORKFLOWS); the certification image bakes a "catalog-entry" workflow.
// If no workflow is configured the runner has nothing to drive — that is itself
// a certification failure (the loop is unavailable), not a skip.

const WORKFLOW_ID = process.env.CERT_WORKFLOW_ID ?? "catalog-entry";

test("stage a linked Author→Book→Review set and commit it atomically", async ({ page }) => {
  const ctx = await gqlContext();
  const [authors0, books0, reviews0] = await Promise.all([
    countCollection(ctx, "authors"),
    countCollection(ctx, "books"),
    countCollection(ctx, "reviews"),
  ]);

  await page.goto(workflowUrl(WORKFLOW_ID));
  await expect(page.getByTestId("workflow-runner").or(page.getByRole("form"))).toBeVisible({
    timeout: 20_000,
  });

  const stamp = Date.now();
  // Step 1 — Author
  await sel.fieldInput(page, "name").fill(`WF Author ${stamp}`);
  await sel.workflowNext(page).click();
  // Step 2 — Book (author is resolved intra-batch to step 1's staged Author)
  await sel.fieldInput(page, "title").fill(`WF Book ${stamp}`);
  await sel.workflowNext(page).click();
  // Step 3 — Review (book resolved intra-batch to step 2's staged Book)
  await sel.fieldInput(page, "rating").fill("5");
  await sel.fieldInput(page, "body").fill("Committed atomically by the golden path.");

  // Mid-workflow, NOTHING is committed yet — staging is inert (ADR-0028).
  expect(await countCollection(ctx, "books")).toBe(books0);

  // Stage the final step → the review screen (still nothing committed).
  await sel.workflowNext(page).click();
  // Whole-set dry-run, then the atomic commit (enabled only by a clean
  // validation — ADR-0028's review gate).
  await sel.workflowValidate(page).click();
  await sel.workflowCommit(page).click();
  await expect(sel.workflowSuccess(page)).toBeVisible();

  // All three landed together — the linked set committed as one unit.
  const [authors1, books1, reviews1] = await Promise.all([
    countCollection(ctx, "authors"),
    countCollection(ctx, "books"),
    countCollection(ctx, "reviews"),
  ]);
  expect(authors1).toBe(authors0 + 1);
  expect(books1).toBe(books0 + 1);
  expect(reviews1).toBe(reviews0 + 1);
  await ctx.dispose();
});
