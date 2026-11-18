"""Lesson 1: the smallest possible agent.

An agent is a loop:
  1. Ask the model something, and tell it which tools it may use.
  2. If the model asks to use a tool, YOUR code runs it and sends back the result.
  3. Repeat until the model gives a final answer.
"""

import json
import anthropic

# Creates the connection to the model. It reads your key from the
# ANTHROPIC_API_KEY environment variable, so the key never lives in this file.
client = anthropic.Anthropic()

MODEL = "claude-sonnet-5-5"

# ---- 1. The tool DEFINITION: what the model sees ---------------------------
# This is a dictionary, just like a JSON object. The model reads the name and
# description to decide WHEN to use the tool, so write them clearly.
tools = [
    {
        "name": "get_account_health",
        "description": (
            "Return usage and support metrics for a customer account. "
            "Use when asked how an account is doing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"account": {"type": "string"}},
            "required": ["account"],
        },
    }
]


# ---- 2. The tool FUNCTION: what your code actually does --------------------
# Fake data for now. In Lesson 3 this will call a real data source.
def get_account_health(account):
    return {
        "account": account,
        "seats_purchased": 500,
        "seats_active": 470,
        "open_p1_tickets": 0,
        "renewal_date": "2027-02-01",
        "days_since_exec_contact": 12,
    }


# ---- 3. The LOOP: this is what makes it an agent ---------------------------
messages = [{"role": "user", "content": "Compare Acme and Globex"}]

while True:
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=tools,
        messages=messages,
    )

    # Keep the model's reply in the conversation history.
    messages.append({"role": "assistant", "content": response.content})

    # If the model didn't ask for a tool, it has given its final answer.
    if response.stop_reason != "tool_use":
        break

    # Otherwise, run each tool it asked for and send the results back.
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            print(f"[agent is calling tool: {block.name} with {block.input}]")
            result = get_account_health(**block.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            )
    messages.append({"role": "user", "content": tool_results})

# Print the final text answer.
print()
print(next(b.text for b in response.content if b.type == "text"))
