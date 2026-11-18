"""Lesson 4: a repeatable test list for the QBR agent.

    python3 evals.py        # run every test once
    python3 evals.py 3      # run every test 3 times (model answers vary run to run)

Each run is saved in eval_results/ so you can compare runs over time.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Phrases that signal "I don't have that data". Checks look for ANY of these.
GAP_WORDS = ["no record", "not on file", "missing", "no data", "not available",
             "isn't available", "no renewal", "don't have", "do not have", "unknown",
             "not provided", "not listed"]

# ---- The test list ----------------------------------------------------------
# Each test is a question plus checks on the answer. Available checks:
#   must_call         tools the agent must have called
#   must_contain      every one of these must appear in the answer
#   any_of            a list of lists: from each inner list, at least one must appear
#   must_not_contain  none of these may appear
#   max_words         answer length limit
CASES = [
    {
        "name": "Hooli brief: flags old tickets, cites tools",
        "question": "Prep me for Hooli's QBR.",
        "must_call": ["get_usage", "get_open_tickets", "get_renewal_info"],
        "must_contain": ["T-4075", "T-4099", "[get_"],
        "max_words": 450,
    },
    {
        "name": "Initech: admits missing executive contact",
        "question": "Prep me for Initech's QBR.",
        "must_contain": ["[get_"],
        "any_of": [["exec"], GAP_WORDS],
    },
    {
        "name": "Soylent: admits missing champion",
        "question": "Prep me for Soylent's QBR.",
        "any_of": [["champion"], GAP_WORDS],
    },
    {
        "name": "Pied Piper: admits missing renewal record, no invented date",
        "question": "Prep me for Pied Piper's QBR.",
        "must_call": ["get_renewal_info"],
        "any_of": [["no renewal", "renewal record", "no record", "not on file",
                    "missing", "don't have", "isn't available", "not available"]],
        "must_not_contain": ["renewal date: 20", "renews on 20", "renews 20"],
    },
    {
        "name": "Unknown account: says so, invents no numbers",
        "question": "Prep me for Wayne Enterprises' QBR.",
        "any_of": [["no account", "not found", "couldn't find", "could not find",
                    "no record", "doesn't exist", "does not exist", "isn't in", "not in"]],
        "must_not_contain": ["$"],
    },
    {
        "name": "Renewals question uses the portfolio tool",
        "question": "Which accounts renew in the next 60 days?",
        "must_call": ["find_renewals_within"],
        "must_contain": ["Vandelay", "Umbrella"],
    },
    {
        "name": "Low adoption question uses the at-risk tool",
        "question": "Which accounts have low adoption?",
        "must_call": ["get_at_risk_accounts"],
        "must_contain": ["Vandelay", "Pied Piper", "Acme", "Hooli"],
        "must_not_contain": ["Globex", "Soylent", "Umbrella"],
    },
    {
        "name": "Chaining: low adoption AND renewing soon",
        "question": "Which low-adoption accounts renew in the next 90 days?",
        "must_call": ["get_at_risk_accounts", "find_renewals_within"],
        "must_contain": ["Vandelay", "Acme", "Hooli"],
    },
]


def check_case(case, answer, calls):
    """Run every check for one test. Returns a list of (description, passed)."""
    text = answer.lower()
    results = []
    for tool in case.get("must_call", []):
        results.append((f"called {tool}", tool in calls))
    for s in case.get("must_contain", []):
        results.append((f"mentions '{s}'", s.lower() in text))
    for options in case.get("any_of", []):
        results.append((f"mentions one of {options[:3]}...", any(o.lower() in text for o in options)))
    for s in case.get("must_not_contain", []):
        results.append((f"does NOT mention '{s}'", s.lower() not in text))
    if "max_words" in case:
        n = len(answer.split())
        results.append((f"under {case['max_words']} words (got {n})", n <= case["max_words"]))
    return results


def main():
    repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    # Imported here so check_case above can be tested without an API key.
    from agent import run_agent

    log = []
    total_pass = 0
    total_runs = 0

    for case in CASES:
        passes = 0
        for i in range(repeats):
            calls = []
            try:
                answer = run_agent(case["question"], calls=calls, quiet=True)
                error = None
            except Exception as e:  # keep going even if one run crashes
                answer, error = "", str(e)

            checks = check_case(case, answer, calls)
            ok = error is None and all(passed for _, passed in checks)
            passes += ok
            log.append({
                "test": case["name"], "run": i + 1, "passed": ok, "error": error,
                "tools_called": calls, "answer": answer,
                "failed_checks": [d for d, passed in checks if not passed],
            })
            if not ok:
                print(f"  FAIL  {case['name']} (run {i + 1})")
                if error:
                    print(f"        error: {error}")
                for d, passed in checks:
                    if not passed:
                        print(f"        - {d}")

        total_pass += passes
        total_runs += repeats
        print(f"{'PASS' if passes == repeats else 'FAIL'}  {passes}/{repeats}  {case['name']}")

    print(f"\nOverall: {total_pass}/{total_runs} runs passed")

    out_dir = Path(__file__).parent / "eval_results"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    out_file.write_text(json.dumps(log, indent=2))
    print(f"Saved details to {out_file.name}")


if __name__ == "__main__":
    main()
