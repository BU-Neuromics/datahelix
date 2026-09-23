import { test, expect } from "../support/fixtures";
import { gql, gqlContext } from "../support/graphql";

// FIXTURE CAPABILITY CHECK (not a fifth golden-path UI loop) — reference
// traversal, fixture v1.1.0.
//
// Verifies at the GraphQL seam only, deliberately: Book.co_authors (a real
// stored multivalued forward reference) and Author.books (an `inverse:`-
// declared virtual reverse edge, mosaic ADR-0011) are both queryable against
// the certified pin. This is what BU-Neuromics/datahelix#92 asked the fixture
// to make possible.
//
// What this does NOT do: assert anything about Aperture's result-table UI
// (a to-one column with no repetition, an exploded to-many repeating anchor
// rows with its grain stated on screen, CSV parity). That is Aperture
// ADR-0041 / aperture#65 — still a Proposed ADR pending ratification, with no
// referenced-column display shipped yet (Aperture's `renderCell` only ever
// prints a ref's id or a refList's count today). Asserting on DOM that
// doesn't exist yet would just be a scenario that fails until someone ships
// unrelated frontend work — the fixture and the UI golden path are tracked
// separately on purpose. Add the UI scenario here once aperture#65 ships.

test("Book.co_authors (forward to-many) and Author.books (inverse reverse edge) are queryable", async ({}) => {
  const ctx = await gqlContext();

  // Forward to-many: The Hobbit was seeded with two co_authors alongside its
  // required `author` — one row, one to-one field, one to-many field.
  const hobbit = await gql<{ books: { items: any[] } }>(
    ctx,
    `query CertCoAuthors {
       books(
         filters: [{ field: "title", value: "The Hobbit" }]
         limit: 10
         offset: 0
       ) {
         items {
           title
           author { name }
           coAuthors { name }
           coAuthorsCount
         }
       }
     }`,
  );
  const items = hobbit.books?.items ?? [];
  expect(items, "The Hobbit was not found via the books list field").toHaveLength(1);
  const book = items[0];
  expect(book.author?.name).toBe("J. R. R. Tolkien"); // to-one: unchanged grain
  expect(book.coAuthorsCount).toBe(2); // free count field (ADR-0011-style)
  const coAuthorNames = (book.coAuthors ?? []).map((a: any) => a.name).sort();
  expect(coAuthorNames).toEqual(["Jane Austen", "Ursula K. Le Guin"]);

  // Reverse edge: Tolkien's `books` is derived from every Book.author pointing
  // at him — declared via `inverse: author`, no code, schema-only (mosaic
  // ADR-0011). The Hobbit is his only authored Book (co-authorship above
  // doesn't count — co_authors is a separate, non-inverting slot).
  const tolkien = await gql<{ authors: { items: any[] } }>(
    ctx,
    `query CertReverseEdge {
       authors(
         filters: [{ field: "name", value: "J. R. R. Tolkien" }]
         limit: 10
         offset: 0
       ) {
         items { name booksCount books { title } }
       }
     }`,
  );
  const authorItems = tolkien.authors?.items ?? [];
  expect(authorItems, "J. R. R. Tolkien was not found via the authors list field").toHaveLength(1);
  expect(authorItems[0].booksCount).toBe(1);
  expect((authorItems[0].books ?? []).map((b: any) => b.title)).toEqual(["The Hobbit"]);

  await ctx.dispose();
});
