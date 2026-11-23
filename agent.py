"""Lesson 3: a QBR prep agent backed by a real SQLite database.

Run it like this:
    python3 agent.py "Prep me for Acme's QBR"
    python3 agent.py "Compare Acme and Globex"
    python3 agent.py "Which accounts renew in the next 60 days?"
"""

import json
from datetime import date
import sys
import anthropic
import data_tools

client = anthropic.Anthropic()
MODEL = "claude-sonnet-5-5"
MAX_STEPS = 10  # safety limit: the loop can never run forever
MAX_WORDS = 400    # guardrail: keep this in sync with rule 5 in the system prompt
MAX_REWRITES = 2   # guardrail: how many times we'll ask for a shorter version

# ---- 1. The SYSTEM PROMPT: the agent's playbook ----------------------------
# This is where your real TAM experience goes. Edit it and watch the output change.
SYSTEM_PROMPT = """You are a QBR prep assistant for a Technical Account Manager.

Your job: given an account, gather data with your tools and produce a short QBR brief.

Rules:
1. Only state facts about an account that come from your tools. After each fact,
   name the tool it came from in brackets, like [get_usage].
2. Anything that is your judgment or general experience, not tool data, must be
   labeled "Recommendation:" so the reader can tell it apart from facts.
3. If data you need is missing or a tool returns an error, say so in a
   "Data gaps" section. Never guess or invent numbers, names, or dates.
4. Format the brief with these sections: Snapshot, Risks, Opportunities,
   Talking points for the meeting, Data gaps.
5. Keep it under 400 words. This is a hard limit: if the brief runs long, cut
   Opportunities first, then detail in Snapshot. A busy TAM will read this five minutes
   before the call.
6. If asked a portfolio question (several accounts, not one brief), answer with
   a short ranked list instead of the full brief format.
7. Flag any tickets regardless of level that are open for more than 14 days.
8. Match account names exactly. Treat suffixes such as Inc, LLC, Corp or Ltd as part of the name,
not as noise to ignore. If the requested name isn't an exact match for a name in the Accounts tab,
say which account you matched at the top of the brief. If the request could refer to two or more accounts,
such as "Acme Inc" when both "Acme" and "Acme LLC" exist, don't pick one: ask which account the user means and stop.
"""
SYSTEM_PROMPT += f"\nToday's date is {date.today().isoformat()}."

# ---- 2. The DATA: now a real database ---------------------------------------
# The fake dictionary is gone. setup_db.py builds accounts.db, and data_tools.py
# holds the functions that query it.

# ---- 3. The TOOL FUNCTIONS: a lookup table of tool name -> function ---------
TOOL_FUNCTIONS = {
    "get_usage": data_tools.get_usage,
    "get_open_tickets": data_tools.get_open_tickets,
    "get_renewal_info": data_tools.get_renewal_info,
    "find_renewals_within": data_tools.find_renewals_within,
    "get_at_risk_accounts": data_tools.get_at_risk_accounts,
}

# ---- 4. The TOOL DEFINITIONS: what the model sees ---------------------------
ACCOUNT_SCHEMA = {
    "type": "object",
    "properties": {"account": {"type": "string", "description": "Customer account name, e.g. 'Acme'"}},
    "required": ["account"],
}

tools = [
    {
        "name": "get_usage",
        "description": "Product adoption for an account: seats purchased vs. active, and the 30-day login trend. "
                       "Use to judge adoption and engagement.",
        "input_schema": ACCOUNT_SCHEMA,
    },
    {
        "name": "get_open_tickets",
        "description": "Open support tickets for an account, with priority, date opened, days open, and subject. "
                       "Use to find unresolved issues that could affect the relationship.",
        "input_schema": ACCOUNT_SCHEMA,
    },
    {
        "name": "get_renewal_info",
        "description": "Renewal date, days until renewal, annual contract value, the customer champion, and days "
                       "since the last executive contact. Use to judge renewal timing and relationship strength. "
                       "Fields can be null when the data is missing.",
        "input_schema": ACCOUNT_SCHEMA,
    },
    {
        "name": "find_renewals_within",
        "description": "List ALL accounts renewing within the next N days, soonest first. "
                       "Use for portfolio questions like 'what renews this quarter?', not for one account.",
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "Look-ahead window in days, e.g. 60"}},
            "required": ["days"],
        },
    },
    {
        "name": "get_at_risk_accounts",
        "description": "List ALL accounts using fewer than 50% of their purchased seats, "
                       "worst first. Use for portfolio questions like 'which accounts have "
                       "low adoption?', not for one account.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


# ---- 5. The GUARDRAIL: enforce the length limit in code --------------------
# Rule 5 in the prompt ASKS for a short brief. This function CHECKS, and if the
# brief is too long it sends it back for a rewrite. The model can ignore a request;
# it can't skip a check that your code runs.
def enforce_length(answer, messages, quiet=False):
    for _ in range(MAX_REWRITES):
        words = len(answer.split())
        if words <= MAX_WORDS:
            return answer
        if not quiet:
            print(f"[guardrail: {words} words is over the {MAX_WORDS}-word limit, asking for a shorter version]")
        messages.append({
            "role": "user",
            "content": (f"That is {words} words. Rewrite it in under {MAX_WORDS} words. "
                        "Keep the section headings and the [tool_name] citations. "
                        "Cut Opportunities first, then detail in Snapshot. Add nothing new."),
        })
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=tools,
            tool_choice={"type": "none"},  # rewrite only; no more tool calls
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})
        answer = next(b.text for b in response.content if b.type == "text")

    # Still too long after every retry. Don't chop it mid-sentence; say so honestly.
    words = len(answer.split())
    if words > MAX_WORDS:
        answer += f"\n\n[Note: this brief is {words} words, over the {MAX_WORDS}-word limit.]"
    return answer


# ---- 6. The LOOP, now wrapped in a function --------------------------------
def run_agent(question, calls=None, quiet=False):
    messages = [{"role": "user", "content": question}]

    for step in range(MAX_STEPS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            answer = next(b.text for b in response.content if b.type == "text")
            return enforce_length(answer, messages, quiet)

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                if calls is not None:
                    calls.append(block.name)  # lets the test script see which tools ran
                if not quiet:
                    print(f"[step {step + 1}: calling {block.name} with {block.input}]")
                func = TOOL_FUNCTIONS.get(block.name)
                if func is None:
                    result = {"error": f"Unknown tool '{block.name}'."}
                else:
                    result = func(**block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })
        messages.append({"role": "user", "content": tool_results})

    return "Stopped: the agent hit the step limit without finishing."


if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "Prep me for Acme's QBR."
    print()
    print(run_agent(question))
