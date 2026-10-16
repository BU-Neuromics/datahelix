import type { Locator, Page } from "@playwright/test";
import { test, expect, emulateGraphqlProxy } from "../support/fixtures";
import { collectionUrl, queryUrl, sel } from "../support/app";
import { gql, gqlContext } from "../support/graphql";

// GOLDEN PATH 5 of 5 — QUERY RESULT TABLE (referenced-class columns)
// Seam exercised: Aperture ADR-0041 traversal columns over Mosaic's nested
// GraphQL selections — forward to-one, forward to-many, and an `inverse:`
// reverse edge (mosaic ADR-0011) — plus the query view's Save view
// (aperture#81/#84) and structured values (aperture#82). BU-Neuromics/datahelix#107.
//
// Proves, through the UI rather than the transport (05 keeps the GraphQL-seam
// check):
//   - a to-one column shows the referenced VALUE, with no row repetition;
//   - a to-many column offers how many / list them / one row each, keeps anchor
//     grain for the first two, and for "one row each" repeats the anchor per
//     member AND states the grain change on screen (ADR-0041 item 6 — a
//     correctness property: the total above counts anchors, the table counts
//     pairs, the note reconciles them);
//   - a reverse edge (Author.books) is offered and traversable; one the
//     endpoint does not advertise (Book → Review) is listed with its reason
//     (Aperture ADR-0029), never silently absent;
//   - CSV and JSON exports carry the chosen columns at the grain on screen, and
//     the export note names its unit;
//   - a structured value (Book.dimensions, an inlined value object, fixture
//     1.2.0) and a reference read through a list read as TEXT on screen and in
//     every export — never "[object Object]" (aperture#82);
//   - a query saved as a view persists server-side and reopens, in a fresh
//     browser context, with its columns;
//   - with the Fields panel open over a result, the panel, the table and the
//     pager each keep their own area — nothing paints over the table
//     (aperture#85, 0.7.1).
//
// Fixture rows (fixtures/bootstrap/data/seed.yaml): The Hobbit (author Tolkien,
// co_authors Austen + Le Guin, dimensions 20.3 × 13.5); Austen wrote Pride and
// Emma, both with dimensions. Earlier scenarios add rows before this file runs
// (02 an Author; 03 an Author, a Book and a Review; 04 a saved view), so every
// assertion is either on named seeded rows or self-consistent (counts read off
// the page), never a hard-coded total.

const LEAK = /\[object Object\]/;

test("Books with linked authors: to-one, how many / list them / one row each, and exports at the screen's grain", async ({ page }) => {
  await runQuery(page, "Books");
  const table = sel.queryTable(page);

  await test.step("a structured value reads as text", async () => {
    const hobbit = await rowsWhere(table, "Title", "The Hobbit");
    expect(hobbit).toHaveLength(1);
    expect(hobbit[0]["Dimensions"]).toMatch(/height_cm: 20\.3/);
    expect(hobbit[0]["Dimensions"]).toMatch(/width_cm: 13\.5/);
    await expect(table).not.toContainText(LEAK);
  });

  await sel.fieldsButton(page).click();

  await test.step("a reverse edge the endpoint does not advertise is listed, with its reason", async () => {
    const gated = sel.gatedReferenceLink(page, /Review/);
    await expect(gated).toBeVisible();
    await expect(gated).toContainText(/filter only/i);
    await expect(gated).toContainText(/no reverse edge/i);
  });

  await test.step("a to-one column shows the value, with no row repetition and no mode choice", async () => {
    const author = await openLink(page, /\(its author\)/);
    const bio = sel.referenceField(author, "Bio");
    await bio.getByRole("checkbox").check();
    await expect(bio.getByRole("radio")).toHaveCount(0);
    await expect(table.getByRole("columnheader", { name: "Author → Bio" })).toBeVisible();
    // The header renders as soon as the box is ticked; the value arrives with
    // the re-read that fetches author { bio }. Poll the data, not the header.
    // One element = one row: a to-one column never repeats the anchor.
    await expect.poll(async () => (await rowsWhere(table, "Title", "The Hobbit")).map((r) => r["Author → Bio"]))
      .toEqual(["English writer and philologist."]);
  });

  const coAuthors = await openLink(page, /its co authors/);
  const coName = sel.referenceField(coAuthors, "Name");

  await test.step("a to-many column defaults to 'how many', at anchor grain", async () => {
    await coName.getByRole("checkbox").check();
    await expect(coName.getByRole("radio", { name: "how many" })).toBeChecked();
    await expect(table.getByRole("columnheader", { name: "Author → Name" })).toBeVisible();
    // Until the re-read adds coAuthors { name } the count reads 0 -- poll.
    await expect.poll(async () => (await rowsWhere(table, "Title", "The Hobbit")).map((r) => r["Author → Name"]))
      .toEqual(["2"]);
  });

  await test.step("'list them' joins the members, still at anchor grain", async () => {
    await coName.getByRole("radio", { name: "list them" }).check();
    await expect(sel.queryGrain(page)).toHaveCount(0);
    await expect.poll(async () => (await rowsWhere(table, "Title", "The Hobbit")).map((r) => r["Author → Name"]))
      .toEqual(["Jane Austen; Ursula K. Le Guin"]);
  });

  let pairs = 0;
  let anchors = 0;
  await test.step("'one row each' repeats the anchor per member and states the grain change", async () => {
    await coName.getByRole("radio", { name: "one row each" }).check();
    const grain = sel.queryGrain(page);
    await expect(grain).toHaveText(/Exploded by .*co authors.* — \d+ rows from \d+ books on this page/);
    [pairs, anchors] = numbers(await grain.textContent(), /— (\d+) rows from (\d+) books/);
    // The note reconciles the two counts on screen: rows in the table, anchors
    // in the total above it.
    await expect(table.locator("tbody tr")).toHaveCount(pairs);
    const [total] = numbers(await sel.queryTotal(page).textContent(), /(\d+) matching books/);
    expect(anchors).toBe(total);
    expect(pairs).toBeGreaterThan(anchors);

    const hobbit = await rowsWhere(table, "Title", "The Hobbit");
    expect(hobbit.map((r) => r["Author → Name"]).sort()).toEqual(["Jane Austen", "Ursula K. Le Guin"]);
    // The anchor's own values and its to-one column repeat down the block.
    for (const row of hobbit) {
      expect(row["Author → Bio"]).toBe("English writer and philologist.");
      expect(row["Dimensions"]).toMatch(/height_cm: 20\.3/);
    }
    await expect(table).not.toContainText(LEAK);
  });

  await test.step("the Fields panel, the table and the pager each keep their own area", async () => {
    // With both reference groups expanded the Fields panel is at its tallest.
    // Before aperture#85 its content painted over the table and the pager;
    // now each sits in its own box, top to bottom, with no overlap.
    // (Before #85 the panel was squeezed to zero height — so not even
    // "visible" — while its content spilled over the table.)
    await expect(sel.fieldsPanel(page), "the Fields panel has no area of its own").toBeVisible();
    const fields = (await sel.fieldsPanel(page).boundingBox())!;
    const tableTop = (await sel.queryTable(page).boundingBox())!;
    expect(fields.y + fields.height, "the Fields panel overlaps the results table").toBeLessThanOrEqual(tableTop.y + 0.5);
    // The table scrolls inside its own box, which ends above the pager.
    await expect(sel.queryTableBox(page)).toBeVisible();
    const box = (await sel.queryTableBox(page).boundingBox())!;
    const pager = (await sel.queryPager(page).boundingBox())!;
    expect(box.y + box.height, "the results table overlaps the pager").toBeLessThanOrEqual(pager.y + 0.5);
  });

  await test.step("CSV export carries the screen's columns at the screen's grain", async () => {
    const csv = parseCsv(await download(page, "CSV"));
    const [header, ...lines] = csv;
    // Dotted names for files (aperture#81): anchor slots by slot name,
    // traversals by class path + slot. (Only names that would collide fall back
    // to the GraphQL path.)
    expect(header).toEqual(expect.arrayContaining(["title", "dimensions", "Author.name", "Author.bio"]));
    expect(lines).toHaveLength(pairs);
    const col = (name: string) => header.indexOf(name);
    const hobbit = lines.filter((l) => l[col("title")] === "The Hobbit");
    expect(hobbit.map((l) => l[col("Author.name")]).sort()).toEqual(["Jane Austen", "Ursula K. Le Guin"]);
    for (const l of hobbit) expect(l[col("Author.bio")]).toBe("English writer and philologist.");
    for (const l of hobbit) expect(l[col("dimensions")]).toMatch(/height_cm: 20\.3/);
    expect(csv.flat().join("\n")).not.toMatch(LEAK);
    await expect(sel.exportNote(page)).toHaveText(new RegExp(`Exported ${pairs} rows from ${anchors} books`));
  });

  await test.step("JSON export carries the same rows, structured values kept as structure", async () => {
    const rows = JSON.parse(await download(page, "JSON")) as Record<string, unknown>[];
    expect(rows).toHaveLength(pairs);
    const hobbit = rows.filter((r) => r["title"] === "The Hobbit");
    expect(hobbit.map((r) => r["Author.name"]).sort()).toEqual(["Jane Austen", "Ursula K. Le Guin"]);
    for (const r of hobbit) expect(r["dimensions"]).toMatchObject({ height_cm: 20.3, width_cm: 13.5 });
  });
});

test("Authors through the reverse books edge: structured values and references read through a list", async ({ page }) => {
  await runQuery(page, "Authors");
  const table = sel.queryTable(page);
  await sel.fieldsButton(page).click();

  const books = await openLink(page, /its books/);
  // The reverse edge is offered as a real, selectable link — not gated.
  await expect(sel.gatedReferenceLink(page, /Book/)).toHaveCount(0);

  await test.step("structured values through a list are listed as text", async () => {
    const dims = sel.referenceField(books, "Dimensions");
    await dims.getByRole("checkbox").check();
    await dims.getByRole("radio", { name: "list them" }).check();
    await expect.poll(async () => (await rowsWhere(table, "Name", "Jane Austen"))[0]?.["Book → Dimensions"] ?? "")
      .toMatch(/height_cm: 19\.8.*; .*height_cm: 19\.8/);
    await expect(table).not.toContainText(LEAK);
  });

  await test.step("a reference read through a list, one row each, reads as its id (the aliquots.location shape)", async () => {
    const author = sel.referenceField(books, "Author");
    await author.getByRole("checkbox").check();
    // "list them": each member's id, not a blank (aperture#82 — joinIds used
    // to drop object-valued members). Polled: the value arrives with the
    // re-read that adds books { author }.
    await author.getByRole("radio", { name: "list them" }).check();
    await expect(sel.queryGrain(page)).toHaveCount(0);
    await expect.poll(async () => (await rowsWhere(table, "Name", "Jane Austen"))[0]?.["Book → Author"] ?? "")
      .toBe("author-austen; author-austen");
    await expect(table).not.toContainText(LEAK);

    // "one row each" belongs to the link: every column through it explodes.
    await author.getByRole("radio", { name: "one row each" }).check();
    await expect(sel.queryGrain(page)).toHaveText(/Exploded by .*books.* — \d+ rows from \d+ authors on this page/);
    await expect.poll(async () => (await rowsWhere(table, "Name", "Jane Austen")).map((r) => r["Book → Author"]))
      .toEqual(["author-austen", "author-austen"]);
    const austen = await rowsWhere(table, "Name", "Jane Austen");
    expect(austen).toHaveLength(2);
    for (const row of austen) {
      expect(row["Book → Author"]).toBe("author-austen");
      expect(row["Book → Dimensions"]).toMatch(/^width_cm: 12\.9 · height_cm: 19\.8$|^height_cm: 19\.8 · width_cm: 12\.9$/);
    }
    await expect(table).not.toContainText(LEAK);

    const csv = parseCsv(await download(page, "CSV"));
    const [header, ...lines] = csv;
    const austenLines = lines.filter((l) => l[header.indexOf("name")] === "Jane Austen");
    expect(austenLines.map((l) => l[header.indexOf("Book.author")])).toEqual(["author-austen", "author-austen"]);
    expect(csv.flat().join("\n")).not.toMatch(LEAK);
  });
});

test("a query saved as a view persists server-side and reopens with its columns", async ({ page }) => {
  // A shared link restores the query AND its columns (aperture#75).
  await page.goto(
    queryUrl(
      { v: 1, anchor: "Book", mode: "AND", criteria: [] },
      { paths: [{ path: ["coAuthors", "name"], mode: "explode" }, { path: ["author", "bio"] }] },
    ),
  );
  await expect(sel.queryResults(page)).toBeVisible({ timeout: 20_000 });
  await expect(sel.queryGrain(page)).toBeVisible();

  const viewName = `cert-query-${Date.now()}`;
  await sel.saveViewButton(page).click();
  await page.getByTestId("save-view-name").fill(viewName);
  await page.getByTestId("save-view-confirm").click();
  await expect(sel.savedViewNamed(page, viewName)).toBeVisible();

  // Server-side: the document carries the query and its column choices.
  const ctx = await gqlContext();
  const data = await gql<{ apertureDocuments: { items: { name: string; payload: string }[] } }>(
    ctx,
    `query CertSavedQuery {
       apertureDocuments(filters: [{ field: "kind", value: "savedView" }], limit: 500, offset: 0) {
         items { name payload }
       }
     }`,
  );
  await ctx.dispose();
  const doc = data.apertureDocuments.items.find((d) => d.name === viewName);
  expect(doc, "saved query view was not persisted to the control-plane store").toBeTruthy();
  const saved = JSON.parse(doc!.payload).data.state.query;
  expect(saved.qs.anchor).toBe("Book");
  expect(saved.cols.paths).toEqual(
    expect.arrayContaining([expect.objectContaining({ path: ["coAuthors", "name"], mode: "explode" })]),
  );

  // Reopens from the nav in a brand-new browser context: the query view, with
  // its columns and its stated grain.
  const fresh = await page.context().browser()!.newContext();
  await emulateGraphqlProxy(fresh);
  const p2 = await fresh.newPage();
  await p2.goto(collectionUrl("books"));
  await sel.savedViewNamed(p2, viewName).click();
  await expect(sel.queryResults(p2)).toBeVisible({ timeout: 20_000 });
  await expect(sel.queryAnchor(p2)).toHaveValue("Book");
  const t2 = sel.queryTable(p2);
  await expect(t2.getByRole("columnheader", { name: "Author → Name" })).toBeVisible();
  await expect(t2.getByRole("columnheader", { name: "Author → Bio" })).toBeVisible();
  await expect(sel.queryGrain(p2)).toBeVisible();
  const hobbit = await rowsWhere(t2, "Title", "The Hobbit");
  expect(hobbit.map((r) => r["Author → Name"]).sort()).toEqual(["Jane Austen", "Ursula K. Le Guin"]);
  await fresh.close();
});

// --- helpers ------------------------------------------------------------------

async function runQuery(page: Page, anchorLabel: string): Promise<void> {
  await page.goto(queryUrl());
  await sel.queryAnchor(page).selectOption({ label: anchorLabel });
  await sel.queryRun(page).click();
  await expect(sel.queryResults(page)).toBeVisible({ timeout: 20_000 });
}

/** Expand a "Through a reference" link group and return it. */
async function openLink(page: Page, label: RegExp): Promise<Locator> {
  const group = sel.referenceLink(page, label);
  // Fail fast and legibly (expect timeout, not the 60s test timeout) when the
  // link is not offered at all.
  await expect(group, `no "Through a reference" link matching ${label}`).toBeVisible();
  const toggle = group.getByRole("button").first();
  if ((await toggle.getAttribute("aria-expanded")) !== "true") await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  return group;
}

/** The table's body rows as header → cell text, for rows whose `column` equals `value`. */
async function rowsWhere(table: Locator, column: string, value: string): Promise<Record<string, string>[]> {
  const headers = (await table.locator("thead th").allTextContents()).map((h) => h.trim());
  const rows = await table.locator("tbody tr").evaluateAll((trs) =>
    trs.map((tr) => Array.from(tr.querySelectorAll("td"), (td) => (td.textContent ?? "").trim())),
  );
  return rows
    .map((cells) => Object.fromEntries(headers.map((h, i) => [h, cells[i] ?? ""])))
    .filter((r) => r[column] === value);
}

async function download(page: Page, kind: "CSV" | "JSON"): Promise<string> {
  const [file] = await Promise.all([page.waitForEvent("download"), sel.exportButton(page, kind).click()]);
  const stream = await file.createReadStream();
  const chunks: Buffer[] = [];
  for await (const c of stream) chunks.push(c as Buffer);
  return Buffer.concat(chunks).toString("utf8");
}

function numbers(text: string | null, pattern: RegExp): number[] {
  const m = (text ?? "").match(pattern);
  if (!m) throw new Error(`"${text}" does not match ${pattern}`);
  return m.slice(1).map(Number);
}

/** RFC 4180 CSV → rows of fields (quoted fields, doubled quotes, CRLF). */
function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); rows.push(row); row = []; field = "";
    } else field += c;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  return rows;
}
