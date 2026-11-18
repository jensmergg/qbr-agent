"""The data layer: each function here answers one question from the database.

Two safety habits live in this file:
  1. The database is opened READ-ONLY, so a bug (or a confused agent) can't change data.
  2. Queries use ? placeholders instead of pasting text into the SQL, which
     prevents SQL injection.
"""

import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).parent / "accounts.db"


def _connect():
    # mode=ro means read-only: least privilege, enforced by the database itself.
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row  # lets us read columns by name
    return conn


def _find_account(conn, name):
    # lower() on both sides so "acme", "Acme" and "ACME" all match.
    return conn.execute(
        "SELECT id, name, arr_usd FROM accounts WHERE lower(name) = lower(?)",
        (name.strip(),),
    ).fetchone()


def _not_found(name):
    return {"error": f"No account named '{name}' found."}


def get_usage(account):
    with closing(_connect()) as conn:
        acct = _find_account(conn, account)
        if acct is None:
            return _not_found(account)
        row = conn.execute(
            """SELECT seats_purchased, seats_active, logins_trend_30d
               FROM usage WHERE account_id = ?""",
            (acct["id"],),
        ).fetchone()
        if row is None:
            return {"account": acct["name"], "error": "No usage data on file."}
        return {"account": acct["name"], **dict(row)}


def get_open_tickets(account):
    with closing(_connect()) as conn:
        acct = _find_account(conn, account)
        if acct is None:
            return _not_found(account)
        rows = conn.execute(
            """SELECT id, priority, opened, subject,
                      CAST(julianday(date('now','localtime')) - julianday(opened) AS INTEGER) AS days_open
               FROM tickets
               WHERE account_id = ? AND status = 'open'
               ORDER BY priority, opened""",
            (acct["id"],),
        ).fetchall()
        return {"account": acct["name"], "open_tickets": [dict(r) for r in rows]}


def get_renewal_info(account):
    with closing(_connect()) as conn:
        acct = _find_account(conn, account)
        if acct is None:
            return _not_found(account)
        row = conn.execute(
            """SELECT renewal_date, champion, last_exec_contact,
                      CAST(julianday(renewal_date) - julianday(date('now','localtime')) AS INTEGER) AS days_to_renewal,
                      CAST(julianday(date('now','localtime')) - julianday(last_exec_contact) AS INTEGER) AS days_since_exec_contact
               FROM renewals WHERE account_id = ?""",
            (acct["id"],),
        ).fetchone()
        result = {"account": acct["name"], "arr_usd": acct["arr_usd"]}
        if row is None:
            result["error"] = "No renewal record on file."
        else:
            result.update(dict(row))  # a NULL in the database arrives here as None
        return result


def find_renewals_within(days):
    """Portfolio question: which accounts renew in the next N days?"""
    days = int(days)
    with closing(_connect()) as conn:
        rows = conn.execute(
            """SELECT a.name, a.arr_usd, r.renewal_date,
                      CAST(julianday(r.renewal_date) - julianday(date('now','localtime')) AS INTEGER) AS days_to_renewal
               FROM renewals r
               JOIN accounts a ON a.id = r.account_id
               WHERE julianday(r.renewal_date) - julianday(date('now','localtime')) BETWEEN 0 AND ?
               ORDER BY r.renewal_date""",
            (days,),
        ).fetchall()
        return {"within_days": days, "renewals": [dict(r) for r in rows]}


def get_at_risk_accounts():
    """Portfolio question: which accounts use fewer than half their seats?"""
    with closing(_connect()) as conn:
        rows = conn.execute(
            """SELECT a.name, u.seats_purchased, u.seats_active,
                      ROUND(100.0 * u.seats_active / u.seats_purchased) AS utilization_pct
               FROM usage u
               JOIN accounts a ON a.id = u.account_id
               WHERE 1.0 * u.seats_active / u.seats_purchased < 0.5
               ORDER BY utilization_pct"""
        ).fetchall()
        return {"at_risk_accounts": [dict(r) for r in rows]}
