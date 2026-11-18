"""Builds accounts.db, a small SQLite database of fake customer data.

Safe to re-run: it rebuilds the tables from scratch each time.
Dates are relative to today, so the story stays realistic whenever you run it.

    python3 setup_db.py
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "accounts.db"
today = date.today()


def ago(days):
    return (today - timedelta(days=days)).isoformat()


def ahead(days):
    return (today + timedelta(days=days)).isoformat()


conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ---- The schema: four tables, linked by account id -------------------------
cur.executescript("""
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS usage;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS renewals;

CREATE TABLE accounts (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    industry  TEXT,
    arr_usd   INTEGER
);
CREATE TABLE usage (
    account_id        INTEGER,
    seats_purchased   INTEGER,
    seats_active      INTEGER,
    logins_trend_30d  TEXT
);
CREATE TABLE tickets (
    id          TEXT PRIMARY KEY,
    account_id  INTEGER,
    priority    TEXT,      -- P1 (urgent) to P3 (low)
    status      TEXT,      -- 'open' or 'closed'
    opened      TEXT,      -- YYYY-MM-DD
    subject     TEXT
);
CREATE TABLE renewals (
    account_id         INTEGER,
    renewal_date       TEXT,
    champion           TEXT,
    last_exec_contact  TEXT   -- NULL means we have no record of one
);
""")

# ---- The data --------------------------------------------------------------
cur.executemany("INSERT INTO accounts VALUES (?, ?, ?, ?)", [
    (1, "Acme", "Software", 120000),
    (2, "Globex", "Manufacturing", 240000),
    (3, "Initech", "Financial services", 60000),
    (4, "Umbrella Corp", "Healthcare", 180000),
    (5, "Hooli", "Technology", 400000),
    (6, "Soylent", "Food and beverage", 45000),
    (7, "Vandelay Industries", "Logistics", 95000),
    (8, "Pied Piper", "Technology", 30000),
])

cur.executemany("INSERT INTO usage VALUES (?, ?, ?, ?)", [
    (1, 500, 180, "down 22% vs prior 30 days"),
    (2, 800, 720, "up 6% vs prior 30 days"),
    (3, 200, 110, "flat"),
    (4, 350, 300, "up 2% vs prior 30 days"),
    (5, 1200, 430, "down 35% vs prior 30 days"),
    (6, 90, 85, "up 12% vs prior 30 days"),
    (7, 150, 40, "down 10% vs prior 30 days"),
    (8, 60, 20, "flat"),
])

cur.executemany("INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?)", [
    ("T-4012", 1, "P1", "open", ago(20), "SSO login failures for contractors"),
    ("T-4107", 1, "P1", "open", ago(12), "SCIM provisioning sync stalled"),
    ("T-3988", 1, "P3", "open", ago(28), "Request: custom audit report"),
    ("T-3801", 1, "P2", "closed", ago(60), "Slow admin console load"),
    ("T-4090", 2, "P3", "open", ago(8), "Question about SAML attribute mapping"),
    ("T-4031", 3, "P2", "open", ago(16), "Intermittent MFA prompt loops"),
    ("T-3950", 4, "P3", "closed", ago(40), "Password policy question"),
    ("T-4120", 5, "P1", "open", ago(3), "Admin console returns 500 errors"),
    ("T-4118", 5, "P1", "open", ago(5), "Mass logout across all users"),
    ("T-4099", 5, "P2", "open", ago(19), "Audit log export incomplete"),
    ("T-4075", 5, "P2", "open", ago(33), "Okta sync delay"),
    ("T-4101", 7, "P3", "open", ago(9), "Question about onboarding templates"),
])

# Note the gaps on purpose: Initech has no exec contact (NULL), Soylent has no
# champion (NULL), and Pied Piper has no renewals row at all.
cur.executemany("INSERT INTO renewals VALUES (?, ?, ?, ?)", [
    (1, ahead(76), "Dana Whitfield, IT Director", ago(94)),
    (2, ahead(225), "Priya Raman, Security Lead", ago(21)),
    (3, ahead(118), "Sam Ortiz, IT Manager", None),
    (4, ahead(38), "Wen Li, Head of IT", ago(45)),
    (5, ahead(61), "Gavin Bell, CTO Office", ago(130)),
    (6, ahead(290), None, ago(60)),
    (7, ahead(20), "Art Kramer, Operations Director", ago(200)),
])

conn.commit()
conn.close()
print(f"Built {DB_PATH.name} with 8 accounts.")
