"""Step 2. Counting people and time: custom SQLite functions.

Run from the repository root:  python3 src/custom_functions.py

SQLite has no unicode-aware lower() and no MEDIAN(), so both are written in
Python and registered in the database:

  unicode_lower(text)  lower case for any text, including Cyrillic
  MEDIAN(column)       aggregate function (one object per group, step() for
                       every row, finalize() at the end)

sqlmd.py registers the same two functions before running a report.
"""

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_db import connect  # noqa: E402


def unicode_lower(text):
    """Lower case for any text. SQLite passes None for NULL, keep it as is."""
    if text is None:
        return None
    return text.lower()


class Median:
    """Median as a SQLite aggregate: NULLs are ignored, no values -> NULL."""

    def __init__(self):
        self.values = []

    def step(self, value):
        if value is not None:
            self.values.append(value)

    def finalize(self):
        if not self.values:
            return None
        ordered = sorted(self.values)
        middle = len(ordered) // 2
        if len(ordered) % 2 == 1:
            return ordered[middle]
        return (ordered[middle - 1] + ordered[middle]) / 2


def main():
    con = connect()
    con.create_function("unicode_lower", 1, unicode_lower)
    con.create_aggregate("MEDIAN", 1, Median)
    cur = con.cursor()

    print("1. Rows in the directory vs. distinct people")
    print(cur.execute("SELECT COUNT(*), COUNT(DISTINCT login) FROM agents").fetchone())

    print("1a. Which row is redundant (identical in every column)")
    for row in cur.execute("""
        SELECT id, login, team, hired_at, COUNT(*)
        FROM agents
        GROUP BY id, login, team, hired_at
        HAVING COUNT(*) > 1
    """):
        print(row)

    print("2. Shifts with fewer than 6 people (count people, not rows)")
    for row in cur.execute("""
        SELECT team, COUNT(DISTINCT login)
        FROM agents
        GROUP BY team
        HAVING COUNT(DISTINCT login) < 6
        ORDER BY team
    """):
        print(row)

    print("3. Channels in the raw export: built-in lower()")
    for row in cur.execute("""
        SELECT lower(channel), COUNT(*) FROM tickets GROUP BY lower(channel) ORDER BY 1
    """):
        print(row)

    print("3a. Channels in the raw export: unicode_lower()")
    for row in cur.execute("""
        SELECT unicode_lower(channel), COUNT(*) FROM tickets GROUP BY unicode_lower(channel) ORDER BY 1
    """):
        print(row)

    # Mean vs. median: a few extremely long tickets pull the mean up (29.7 min),
    # while a typical ticket takes about 16 minutes. The median is the number
    # I would give a manager: it describes the typical ticket.
    print("4. Handling time before April: mean and median")
    print(cur.execute("""
        SELECT ROUND(AVG(handle_min), 1), MEDIAN(handle_min)
        FROM clean
        WHERE period = 'до'
    """).fetchone())

    print("5. The same median: custom SQL aggregate vs. statistics.median")
    sql_median = cur.execute(
        "SELECT MEDIAN(handle_min) FROM clean WHERE period = 'до'"
    ).fetchone()[0]
    values = [r[0] for r in cur.execute(
        "SELECT handle_min FROM clean WHERE period = 'до' AND handle_min IS NOT NULL"
    )]
    print(sql_median, statistics.median(values))


if __name__ == "__main__":
    main()
