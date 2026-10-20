# Support Tickets: SQL Data Audit

An audit of a customer-support ticket export (≈7,000 tickets, first half of 2025)
before judging whether a support chatbot launched on 1 April 2025 helps.
The question of the case: *can we trust the numbers a colleague's cleaning produced?*

The answer is in [`reports/data_audit.md`](reports/data_audit.md): ten checks, each with
the SQL that proves it and a short written conclusion (in Russian).

## Key findings

| # | Finding | Number |
|---|---------|--------|
| 1 | The export contains exact duplicates; cleaning keeps one copy of each | 7,033 → 6,760 rows |
| 2 | One channel was written two ways (`чат` / `Чат`) | 2,711 + 163 |
| 3 | Unknown topic is stored two ways (empty cell and the text `NULL`); the cleaning fixed only one | 278 fixed, **152 missed** → 430 real (6.4 %) |
| 4 | Two date formats; comparing dates as text puts every `DD.MM.YYYY` row "before April" | 3,337 vs **3,549** tickets after 1 April |
| 5 | The bot closed 1,667 tickets; 1,570 have no agent (an empty agent means "nobody handled it") | |
| 6 | 187 ticket numbers are missing, **155 of them after April** (32 before) | the bot may look better or worse than it is |
| 7 | First reply time in written channels (median) | 50.1 → 0.4 min, but the first reply is now the bot's |
| 8 | Returns within 7 days grew while "closed by bot" looks great | 6.2 % → 9.3 % |

The mean handling time before April is 29.7 min, the median 16 min: a few very long
tickets pull the mean up, so the median is the honest number for a typical ticket.

## What is in the repository

```
src/build_db.py          loads the CSV files into SQLite and rebuilds the `clean` table
src/first_queries.py     step 1: CSV -> SQLite, first SELECT / GROUP BY / ORDER BY queries
src/custom_functions.py  step 2: unicode_lower() and a MEDIAN() aggregate written in Python
src/sqlmd.py             runs every ```sql block of a Markdown report and prints the results
reports/data_audit.md    the audit: question, answer, SQL
tests/                   checks of the functions, the database and the report
data/                    synthetic course data (see data/NOTICE.md)
```

## Run it

Python 3.9+, standard library only.

```bash
python3 src/first_queries.py
python3 src/custom_functions.py
python3 src/sqlmd.py reports/data_audit.md     # all SQL of the audit
python3 -m unittest discover -s tests -v
```

## Notes

- `clean` reproduces the colleague's cleaning *including its gap* (the text `NULL`
  in `topic`), because finding that gap is the point of the audit.
- Custom SQLite functions: SQLite's built-in `lower()` does not handle Cyrillic
  (`Чат` stays `Чат`), so `unicode_lower()` is registered from Python; `MEDIAN()`
  is an aggregate class with `step()` / `finalize()`.
- Context: a learning case from the School 21 data-analysis intensive. Later steps
  of the original case (ticket triage, bot effectiveness, a memo) are not part of
  this repository.
