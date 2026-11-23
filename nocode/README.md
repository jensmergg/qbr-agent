# QBR No Code Prep Agent

A small, tested AI agent that prepares a Technical Account Manager for a customer QBR, not built with Python but built as a no-code agent. . Give it an account name and it pulls usage, support tickets, and renewal data, then writes a short brief with risks, talking points, and a "Data gaps" section for anything it couldn't verify.

This is run in a Claude Project where a Google Sheet contains the data and the instructions file is the "program". 

> **All data in this repo is fictional.** Account names are borrowed from TV and film. Nothing here comes from any real company or customer.

> **Note: The data is a snapshot** - renewal dates and ticket dates were set mid-November so day counts only match if you say "as of 2026-11-21". Acme LLC is a test row added to see how it would handle similar names. 
>
> **Built as a learning project, with Claude acting as a tutor.** I ran, tested, and modified every piece, and the "What went wrong" section below comes from my own test runs.
