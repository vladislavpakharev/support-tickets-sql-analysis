"""Runs the ```sql blocks of a Markdown report against the database.

    python3 src/sqlmd.py reports/data_audit.md

Blocks run top to bottom in one database, so a view created in an early block
is visible in the later ones. Each block is printed under the heading it
belongs to. The custom SQL functions unicode_lower() and MEDIAN() are
registered before the run.
"""

import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_db import connect  # noqa: E402
from custom_functions import Median, unicode_lower  # noqa: E402

MAX_ROWS = 30
FENCE = re.compile(r"```sql\s*\n(.*?)```", re.DOTALL)


def split_statements(sql):
    """Split a block on ';' (a ';' inside quotes does not split)."""
    statements, buffer = [], ""
    for char in sql:
        buffer += char
        if char == ";" and sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        statements.append(buffer.strip())
    return [s for s in statements if any(l.strip() and not l.strip().startswith("--")
                                         for l in s.splitlines())]


def blocks(text):
    """Yield (heading, sql) for every ```sql block."""
    heading = ""
    position = 0
    for match in FENCE.finditer(text):
        for line in text[position:match.start()].splitlines():
            if line.startswith("#"):
                heading = line.lstrip("# ").strip()
        position = match.end()
        yield heading, match.group(1)


def run(path):
    con = connect()
    con.create_function("unicode_lower", 1, unicode_lower)
    con.create_aggregate("MEDIAN", 1, Median)
    text = Path(path).read_text(encoding="utf-8")
    failures = 0
    for heading, sql in blocks(text):
        print("\n== " + heading[:100])
        for statement in split_statements(sql):
            try:
                cursor = con.execute(statement)
                rows = cursor.fetchmany(MAX_ROWS + 1)
            except sqlite3.Error as error:
                failures += 1
                print("   ERROR: %s" % error)
                continue
            if cursor.description is None:
                continue
            print("   " + " | ".join(column[0] for column in cursor.description))
            for row in rows[:MAX_ROWS]:
                print("   " + " | ".join(str(value) for value in row))
            if len(rows) > MAX_ROWS:
                print("   ... (first %d rows shown)" % MAX_ROWS)
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 src/sqlmd.py REPORT.md")
        sys.exit(1)
    sys.exit(run(sys.argv[1]))
