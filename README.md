# Study Library

A local catalog for lending study resources and finding related material.

## Scope

- Store resources, members and borrowing history in SQLite.
- Check available copies before recording a loan.
- Record returns and list overdue loans.
- Search resource descriptions and suggest related resources.

## Current state

The schema and lending rules are defined. Database operations and the command-line interface will follow in separate milestones. This initial revision does not contain an executable application.

## Design

Python and SQLite keep the application usable without a database server. Search will start with TF-IDF and cosine similarity over resource metadata.

See [the schema and loan rules](docs/schema.md).

## Milestones

- [x] Define records, relationships and lending rules.
- [ ] Implement catalog operations, borrowing and returns.
- [ ] Add search, recommendations and a sample catalog.
- [ ] Test concurrent borrowing and document the CLI.

The initial version is a local administration tool, without a login system. Sample resources will be fictional.
