"""Step 1. First queries: load a CSV into SQLite and ask basic questions.

Run from the repository root:  python3 src/first_queries.py
"""

import csv
import sqlite3

# SQLite can keep the database in memory, no file on disk is needed.
con = sqlite3.connect(":memory:")
cur = con.cursor()

# 1. Create an empty table: all columns are TEXT, exactly as they are in the CSV.
cur.execute("""
CREATE TABLE agents (
    id TEXT,
    login TEXT,
    team TEXT,       -- shift
    hired_at TEXT
)
""")

# 2. Read the CSV: every row of the file becomes a tuple of four values.
with open("data/agents.csv", encoding="utf-8") as source:
    rows = [(r["id"], r["login"], r["team"], r["hired_at"]) for r in csv.DictReader(source)]

# 3. Insert all tuples with one command; each ? is replaced by a value of the tuple.
cur.executemany("INSERT INTO agents VALUES (?, ?, ?, ?)", rows)
con.commit()

print("1. First three agents")
for row in cur.execute("SELECT login, team FROM agents LIMIT 3"):
    print(row)

print("2. Number of rows in the directory")
print(cur.execute("SELECT COUNT(*) FROM agents").fetchone())

print("3. Three agents hired earliest")
for row in cur.execute("SELECT login, hired_at FROM agents ORDER BY hired_at LIMIT 3"):
    print(row)

print("4. Rows per shift")
for row in cur.execute("SELECT team, COUNT(*) FROM agents GROUP BY team ORDER BY team"):
    print(row)

print("5. Agents hired in 2025")
for row in cur.execute("SELECT login, hired_at FROM agents WHERE hired_at LIKE '2025%' ORDER BY hired_at"):
    print(row)
