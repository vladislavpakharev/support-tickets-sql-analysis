"""Builds the SQLite database used by the analysis.

Tables created by connect():

  agents   raw support-agent directory, every column is TEXT
  tickets  raw export of support tickets, every column is TEXT, empty cell = ''
  clean    the tickets after a colleague's cleaning (this is the thing under audit):
             * exact duplicate rows removed (SELECT DISTINCT *),
             * dates written as DD.MM.YYYY HH:MM converted to YYYY-MM-DD HH:MM:SS,
             * channel 'Чат' unified to 'чат', empty topic replaced by 'без темы',
             * empty agent / numbers turned into NULL / integers,
             * derived columns: period, month, written, first_reply_min,
               resolve_hours, came_back, next_bot_result.
           The colleague's cleaning is reproduced as it was, including its known
           gap: the *text* 'NULL' in `topic` is not treated as a missing topic.
           Finding this gap is part of reports/data_audit.md.

Run `python3 src/build_db.py` to print the row counts.
"""

import csv
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CUTOFF = "2025-04-01"  # the bot was launched on this date: 'до' / 'после'

SCHEMA = {
    "agents": "CREATE TABLE agents (id TEXT, login TEXT, team TEXT, hired_at TEXT)",
    "tickets": """CREATE TABLE tickets (
        id TEXT, created_at TEXT, client_id TEXT, channel TEXT, topic TEXT,
        priority TEXT, bot_result TEXT, agent_id TEXT, first_reply_at TEXT,
        resolved_at TEXT, handle_min TEXT, status TEXT, reopened TEXT, csat TEXT)""",
}

CLEAN_SQL = """
CREATE TEMP TABLE base AS
SELECT
    id,
    CAST(substr(id, 2) AS INTEGER) AS num,
    CASE WHEN created_at LIKE '__.__.____ __:__'
         THEN substr(created_at, 7, 4) || '-' || substr(created_at, 4, 2) || '-' ||
              substr(created_at, 1, 2) || ' ' || substr(created_at, 12, 5) || ':00'
         ELSE created_at END                                 AS created,
    client_id,
    CASE WHEN channel = 'Чат' THEN 'чат' ELSE channel END    AS channel,
    CASE WHEN topic = '' THEN 'без темы' ELSE topic END      AS topic,
    CAST(priority AS INTEGER)                                AS priority,
    CASE WHEN bot_result = '' THEN 'нет' ELSE bot_result END AS bot_result,
    NULLIF(agent_id, '')                                     AS agent_id,
    CAST(NULLIF(handle_min, '') AS INTEGER)                  AS handle_min,
    NULLIF(first_reply_at, '')                               AS first_reply_at,
    NULLIF(resolved_at, '')                                  AS resolved_at,
    status,
    CAST(reopened AS INTEGER)                                AS reopened,
    CAST(NULLIF(csat, '') AS INTEGER)                        AS csat
FROM (SELECT DISTINCT * FROM tickets);

CREATE INDEX temp.base_client ON base(client_id, topic, created);

CREATE TABLE clean AS
SELECT
    a.id, a.num, a.created,
    CASE WHEN a.created >= '%(cutoff)s' THEN 'после' ELSE 'до' END AS period,
    substr(a.created, 1, 7)                                        AS month,
    a.client_id, a.channel,
    CASE WHEN a.channel = 'телефон' THEN 0 ELSE 1 END              AS written,
    a.topic, a.priority, a.bot_result, a.agent_id, a.handle_min,
    ROUND((julianday(a.first_reply_at) - julianday(a.created)) * 1440, 1) AS first_reply_min,
    ROUND((julianday(a.resolved_at)   - julianday(a.created)) * 24, 1)   AS resolve_hours,
    a.status, a.reopened, a.csat,
    -- came back: same client, same (known) topic, a new ticket within 7 days
    EXISTS (SELECT 1 FROM base b
            WHERE b.client_id = a.client_id AND b.topic = a.topic
              AND a.topic NOT IN ('без темы', 'NULL')
              AND b.created > a.created
              AND julianday(b.created) - julianday(a.created) <= 7)    AS came_back,
    (SELECT b.bot_result FROM base b
     WHERE b.client_id = a.client_id AND b.topic = a.topic
       AND a.topic NOT IN ('без темы', 'NULL')
       AND b.created > a.created
       AND julianday(b.created) - julianday(a.created) <= 7
     ORDER BY b.created LIMIT 1)                                   AS next_bot_result
FROM base a
ORDER BY a.num;

DROP TABLE temp.base;
""" % {"cutoff": CUTOFF}


def _load_csv(con, table):
    con.execute(SCHEMA[table])
    with open(DATA_DIR / (table + ".csv"), encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        header = next(reader)
        marks = ", ".join("?" for _ in header)
        con.executemany("INSERT INTO %s VALUES (%s)" % (table, marks), reader)


def connect(path=":memory:"):
    """Return a connection with agents, tickets and clean already loaded."""
    con = sqlite3.connect(path)
    for table in SCHEMA:
        con.execute("DROP TABLE IF EXISTS " + table)
        _load_csv(con, table)
    con.execute("DROP TABLE IF EXISTS clean")
    con.executescript(CLEAN_SQL)
    con.commit()
    return con


if __name__ == "__main__":
    connection = connect()
    for name in ("agents", "tickets", "clean"):
        count = connection.execute("SELECT COUNT(*) FROM " + name).fetchone()[0]
        print("%s: %d rows" % (name, count))
