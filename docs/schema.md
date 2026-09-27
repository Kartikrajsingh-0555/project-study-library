# Schema and loan rules

| Record | Fields |
| --- | --- |
| Resource | id, title, subject, description, total copies |
| Member | id, name |
| Loan | id, resource id, member id, borrowed date, due date, returned date |

Each loan references one member and one resource. A null return date means that the loan is active.

## Constraints

- Resource titles and member names cannot be empty.
- Total copies must be a positive integer.
- Loans must reference existing records.
- A member may hold at most one active loan for the same resource.
- A due date cannot precede the borrowing date.

Available copies are total copies minus active loans. There is no separate availability field to keep in sync.

## Borrowing transaction

Acquire a write reservation before checking stock. Validate the member and resource, count active loans, and insert the new loan only if a copy remains. Roll back on any failure. The last-copy test must use two separate database connections.

Returns update history instead of deleting the loan. A resource becomes overdue after its due date, not on the due date itself.

## Search

Index the title, subject and description. Rank matching resources using normalised TF-IDF vectors. Recommendations use another resource's metadata as the query and exclude that source from the results.
