"""Lesson 2: a QBR prep agent with three tools and a playbook.

Run it like this:
    python3 agent.py "Prep me for Acme's QBR"
    python3 agent.py "Compare Acme and Globex"
"""

import json
from datetime import date
import sys
import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-5-5"
MAX_STEPS = 10  # safety limit: the loop can never run forever

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
   "Data gaps" section.
4. Format the brief with these sections: Snapshot, Risks, Opportunities,
   Talking points for the meeting, Data gaps.
5. Keep it under 450 words. A busy TAM will read this five minutes before the call.
6. Flag any tickets regardless of level that are open for more than 14 days.
"""
SYSTEM_PROMPT += f"\nToday's date is {date.today().isoformat()}."

# ---- 2. The DATA: fake for now, real in Lesson 3 ---------------------------
ACCOUNTS = {
    "acme": {
        "usage": {"seats_purchased": 500, "seats_active": 180,
                  "logins_trend_30d": "down 22% vs prior 30 days"},
        "tickets": [
            {"id": "T-4012", "priority": "P1", "opened": "2026-10-28",
             "subject": "SSO login failures for contractors"},
            {"id": "T-4107", "priority": "P1", "opened": "2026-11-05",
             "subject": "SCIM provisioning sync stalled"},
            {"id": "T-3988", "priority": "P3", "opened": "2026-10-20",
             "subject": "Request: custom audit report"},
        ],
        "renewal": {"date": "2027-02-01", "arr_usd": 120000,
                    "champion": "Dana Whitfield, IT Director",
                    "days_since_exec_contact": 94},
    },
    "globex": {
        "usage": {"seats_purchased": 800, "seats_active": 720,
                  "logins_trend_30d": "up 6% vs prior 30 days"},
        "tickets": [
            {"id": "T-4090", "priority": "P3", "opened": "2026-11-09",
             "subject": "Question about SAML attribute mapping"},
        ],
        "renewal": {"date": "2027-06-30", "arr_usd": 240000,
                    "champion": "Priya Raman, Security Lead",
                    "days_since_exec_contact": 21},
    },
    "initech": {
        "usage": {"seats_purchased": 200, "seats_active": 110,
                  "logins_trend_30d": "flat"},
        "tickets": [
            {"id": "T-4031", "priority": "P2", "opened": "2026-11-01",
             "subject": "Intermittent MFA prompt loops"},
        ],
        # Note: no executive contact info on purpose. A good agent should notice.
        "renewal": {"date": "2027-03-15", "arr_usd": 60000,
                    "champion": "Sam Ortiz, IT Manager"},
    },
}


def find_account(name):
    return ACCOUNTS.get(name.strip().lower())


# ---- 3. The TOOL FUNCTIONS: what your code does ----------------------------
def get_usage(account):
    record = find_account(account)
    if record is None:
        return {"error": f"No account named '{account}' found."}
    return {"account": account, **record["usage"]}


def get_open_tickets(account):
    record = find_account(account)
    if record is None:
        return {"error": f"No account named '{account}' found."}
    return {"account": account, "open_tickets": record["tickets"]}


def get_renewal_info(account):
    record = find_account(account)
    if record is None:
        return {"error": f"No account named '{account}' found."}
    return {"account": account, **record["renewal"]}


# A lookup table: tool name -> function. Adding a tool later means adding a line here.
TOOL_FUNCTIONS = {
    "get_usage": get_usage,
    "get_open_tickets": get_open_tickets,
    "get_renewal_info": get_renewal_info,
}

# ---- 4. The TOOL DEFINITIONS: what the model sees --------------------------
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
        "description": "Open support tickets for an account, with priority, date opened, and subject. "
                       "Use to find unresolved issues that could affect the relationship.",
        "input_schema": ACCOUNT_SCHEMA,
    },
    {
        "name": "get_renewal_info",
        "description": "Renewal date, annual contract value, the customer champion, and days since the last "
                       "executive contact. Use to judge renewal timing and relationship strength.",
        "input_schema": ACCOUNT_SCHEMA,
    },
]


# ---- 5. The LOOP, now wrapped in a function --------------------------------
def run_agent(question):
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
            return next(b.text for b in response.content if b.type == "text")

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
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
