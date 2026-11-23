# QBR Prep Agent (no-code version)

A small, tested AI agent that prepares a Technical Account Manager for a customer QBR,
built with no code. Give it an account name and it reads usage, support tickets and
renewal data, then writes a short brief with risks, talking points and a "Data gaps"
section for anything it couldn't verify.

It runs in a Claude Project. A Google Sheet holds the data, and
`project_instructions.md` is the whole "program": the instructions pasted into the
Project. This is the no-code twin of the Python agent in the parent folder.

> **All data in this repo is fictional.** Account names are borrowed from TV and film.
> Nothing here comes from any real company or customer.

> **The data is a snapshot.** Renewal and ticket dates were set in mid-November 2026, so
> day counts only match if you say "as of 2026-11-21". The Acme LLC row is a test row
> added to see how the agent handles similar account names.

> **Built as a learning project, with Claude acting as a tutor.** I ran, tested and
> modified every piece, and the findings below come from my own test runs.

## Files

- `project_instructions.md`: the instructions the Project runs on
- `QBR Agent Demo Accounts (fictional data) - Accounts.csv` and `... - Tickets.csv`:
  the two tabs of the sheet, exported

## What I found testing it

- **Missing data held up.** Unknown accounts (Wayne Enterprises), blank fields (Pied
  Piper's renewal date, Initech's executive contact) and facts the sheet doesn't have
  (Soylent's NPS score) all came back as "Data gaps", with nothing invented.
- **Multi-step questions worked.** "Which low-adoption accounts renew in the next 90
  days?" returned the right accounts, and left out Pied Piper because it has no renewal
  date.
- **Length stayed under the limit** in two Hooli runs (295 and 345 words), but the limit
  is only requested, not enforced. The Python version enforces it in code.
- **Date math is done by the model, so it can slip.** One ticket age came back as 11
  days when it was 12. The Python version does this in SQL.
- **Name matching is where a prompt runs out.** Under my first rule, "Acme Inc" silently
  picked "Acme" when "Acme LLC" also existed. I tightened the rule twice (suffixes count
  as part of the name; reply with only a question when two accounts could match). The
  agent now names both accounts and asks which one I mean, but it still writes the Acme
  brief underneath. A prompt can ask the model to stop; it can't make it.

## Compared with the Python version

The no-code version was much faster to build and handled the same tests. The Python
version adds guarantees (length, exact matching), repeatable automated tests, and
least-privilege data access, because each tool returns only the rows asked for. An
exact-match lookup also has no way to "helpfully" write a brief for an ambiguous name:
"Acme Inc" simply returns not found. Here the
whole workbook is in context for every question.
