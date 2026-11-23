# QBR Prep Agent

A small, tested AI agent that prepares a Technical Account Manager for a customer QBR. Give it an account name and it pulls usage, support tickets, and renewal data, then writes a short brief with risks, talking points, and a "Data gaps" section for anything it couldn't verify.

> **All data in this repo is fictional.** Account names are borrowed from TV and film. Nothing here comes from any real company or customer.
>
> **Built as a learning project, with Claude acting as a tutor.** I ran, tested, and modified every piece, and the "What went wrong" section below comes from my own test runs.

## What it does

    python3 agent.py "Prep me for Hooli's QBR"
    python3 agent.py "Which accounts have low adoption?"
    python3 agent.py "Which low-adoption accounts renew in the next 90 days?"

The agent chooses which tools to call, combines the results, and answers. For a single account it writes a brief with Snapshot, Risks, Opportunities, Talking points, and Data gaps sections.

## How it works

- **Playbook (system prompt):** every fact must cite the tool it came from, opinions must be labeled "Recommendation:", missing data goes in "Data gaps" instead of being guessed, and tickets open over 14 days get flagged.
- **Five read-only tools** (`data_tools.py`): `get_usage`, `get_open_tickets`, `get_renewal_info`, `find_renewals_within`, `get_at_risk_accounts`. Each runs one reviewed SQL query against a local SQLite database.
- **The loop** (`agent.py`): the model asks for a tool, my code runs it and returns the result, repeat until the model answers.

## Safety design

- The database connection is **read-only**, enforced by SQLite, not just by the prompt. No tool can change data or send anything.
- Queries use **parameter placeholders**, so text from the model is never pasted into SQL.
- The agent writes no SQL of its own. It can only call the five tools above.
- A **step cap** (`MAX_STEPS`) stops runaway loops.
- A **length guardrail** checks every answer in code. If a brief is over `MAX_WORDS`, it is sent back for a shorter rewrite (up to twice). If it is still too long, a note is appended instead of cutting text off.

## Testing

`evals.py` holds 8 test questions with automatic checks: which tools were called, required and forbidden phrases, citations, and word limits. Every run is saved to `eval_results/`.

    python3 evals.py 3     # run each test 3 times, since answers vary

Latest result: **24/24 runs passed** at the 400-word limit.

## What went wrong, and what I changed

1. **No clock.** The agent couldn't tell how long a ticket had been open because models don't know today's date. Fix: put the current date in the prompt.
2. **A length limit the model overshot.** With a 450-word limit, the Hooli brief passed only 1 of 3 runs (480 and 471 words on the failures). Tightening the prompt (a lower limit plus an instruction on what to cut first) took it to 3 of 3. I then added the code guardrail, because a prompt can't guarantee compliance.
3. **A test that was wrong, not the agent.** One Initech run failed because my check looked for specific phrases and the agent worded the gap differently. The answer was correct. I widened the check.
4. **A bug in my own tool, caught by the agent.** It noted that a tool reported 60 days to renewal when the dates showed 61. My SQL used the current time of day and truncated the result. Fix: compare dates, not timestamps.

## What I learned

- **An agent is a loop.** The model asks for a tool, my code runs it, and the result goes
  back until there's a final answer. The model never touches my systems directly, so I
  decide what it can reach.
- **Cite, label, admit gaps.** Facts name their source, opinions are labeled
  "Recommendation:", and anything missing goes under "Data gaps". That is what stops it
  inventing things.
- **Test, don't trust.** Fixed questions, repeated runs and saved results. When a test
  fails, I check the test as well as the agent. Mine was wrong once.
- **A prompt asks; code enforces.** Length limits and exact name matching only became
  guarantees once code did the work. I also built the same agent with no code, in a
  Claude Project reading a Google Sheet. It was much faster to build and passed the same
  kinds of tests, but it can only ask for these things. See [`nocode/`](nocode/) for the
  instructions, data and findings.

## Limitations

- Fictional data, one local database, no authentication or logging. This is a learning project, not a production system.
- The checks are keyword-based. They catch missing citations and invented dates, but not whether a recommendation is any good.
- 8 test cases run 3 times each is a small sample.
- A strict word limit costs detail. At 150 words the agent dropped the Opportunities section entirely.
- Test data dates are relative to the day the database is built, so results drift over time.

## Run it yourself

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY="your-key-here"
    python3 setup_db.py
    python3 agent.py "Prep me for Acme's QBR"

`lessons/` holds earlier versions of the agent from the first two lessons.
