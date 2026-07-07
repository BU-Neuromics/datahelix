import { Page, expect, Locator } from "@playwright/test";

// --- URL state ---------------------------------------------------------------
// Aperture drives its main view off URL state (nuqs keys, documented in
// web/src/features/collections/urlState.ts): collection, page, q, filters,
// entity, form, workflow. Navigating by URL is the most stable way to place the
// SPA into a known state for a golden-path step, independent of nav-chrome DOM.

export function collectionUrl(collection: string, extra: Record<string, string> = {}): string {
  const p = new URLSearchParams({ collection, ...extra });
  return `/?${p.toString()}`;
}

export function newEntityFormUrl(collection: string): string {
  return `/?${new URLSearchParams({ collection, form: "new" }).toString()}`;
}

export function workflowUrl(workflowId: string): string {
  return `/?${new URLSearchParams({ workflow: workflowId }).toString()}`;
}

// --- Resilient locators ------------------------------------------------------
// Centralized so that when the built SPA's DOM firms up (aperture#15/#16) only
// this file changes. Each locator prefers a data-testid, then falls back to an
// accessible role/name — the SPA emits serializable view-descriptions
// (Aperture ADR-0009), so stable testids/roles are the intended contract.

export const sel = {
  collectionTable: (p: Page): Locator =>
    p.getByTestId("collection-table").or(p.getByRole("table")).first(),

  rowsFor: (p: Page): Locator =>
    p.getByTestId("collection-row").or(p.getByRole("row")),

  facetPanel: (p: Page): Locator =>
    p.getByTestId("facet-panel").or(p.getByRole("complementary")).first(),

  facetOption: (p: Page, value: string): Locator =>
    p.getByTestId(`facet-option-${value}`).or(
      p.getByRole("checkbox", { name: new RegExp(value, "i") }),
    ),

  entityForm: (p: Page): Locator =>
    p.getByTestId("entity-form").or(p.getByRole("form")).first(),

  fieldInput: (p: Page, field: string): Locator =>
    p.getByTestId(`field-${field}`).or(p.getByLabel(new RegExp(field, "i"))),

  submitButton: (p: Page): Locator =>
    p.getByTestId("form-submit").or(p.getByRole("button", { name: /save|create|submit/i })),

  saveViewButton: (p: Page): Locator =>
    p.getByTestId("save-view").or(p.getByRole("button", { name: /save view/i })),

  savedViewNamed: (p: Page, name: string): Locator =>
    p.getByTestId(`saved-view-${name}`).or(p.getByRole("link", { name })),

  controlPlaneStatus: (p: Page): Locator =>
    p.getByTestId("control-plane-status").or(p.getByText(/control plane|local storage/i)).first(),

  workflowNext: (p: Page): Locator =>
    p.getByTestId("workflow-next").or(p.getByRole("button", { name: /next|continue/i })),

  workflowCommit: (p: Page): Locator =>
    p.getByTestId("workflow-commit").or(p.getByRole("button", { name: /commit|finish|create all/i })),

  workflowSuccess: (p: Page): Locator =>
    p.getByTestId("workflow-success").or(p.getByText(/committed|created|success/i)).first(),
};

// Wait for the SPA shell + first data render. The SPA derives its capabilities
// from a `ApertureIntrospection` query on load; the table is our "ready" signal.
export async function waitForApp(p: Page): Promise<void> {
  await expect(p.locator("body")).toBeVisible();
  // The collection view should render a table once introspection + list resolve.
  await expect(sel.collectionTable(p)).toBeVisible({ timeout: 20_000 });
}
