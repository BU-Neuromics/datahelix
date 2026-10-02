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
// ADR-0041 / aperture#65, which HAS now shipped — aperture#70, released
// v0.6.0, Accepted 2026-10-02 — so the reason this file gives for stopping at
// the GraphQL seam no longer holds. The UI scenario this comment asked for is
// now writable and is the open work here; the DOM it would assert on exists
// in the certified pin (`aperture-0.6.0+mosaic-0.14.0`, fixture 1.1.0).

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
