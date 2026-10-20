import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from build_db import connect  # noqa: E402
from custom_functions import Median, unicode_lower  # noqa: E402
import sqlmd  # noqa: E402


class CustomFunctionTests(unittest.TestCase):
    def test_unicode_lower_handles_cyrillic_and_null(self):
        self.assertEqual(unicode_lower("Чат"), "чат")
        self.assertIsNone(unicode_lower(None))

    def test_median_odd_even_and_nulls(self):
        con = connect()
        con.create_aggregate("MEDIAN", 1, Median)
        con.execute("CREATE TABLE t (g TEXT, v REAL)")
        con.executemany("INSERT INTO t VALUES (?, ?)",
                        [("odd", 5), ("odd", 1), ("odd", 3),
                         ("even", 1), ("even", 2), ("even", 3), ("even", 10),
                         ("nulls", None)])
        rows = dict(con.execute("SELECT g, MEDIAN(v) FROM t GROUP BY g"))
        self.assertEqual(rows, {"odd": 3, "even": 2.5, "nulls": None})


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = connect()

    def one(self, sql):
        return self.con.execute(sql).fetchone()[0]

    def test_cleaning_removes_exact_duplicates_only(self):
        self.assertEqual(self.one("SELECT COUNT(*) FROM tickets"), 7033)
        self.assertEqual(self.one("SELECT COUNT(DISTINCT id) FROM tickets"), 6760)
        self.assertEqual(self.one("SELECT COUNT(*) FROM clean"), 6760)

    def test_dates_are_unified_and_periods_split_correctly(self):
        self.assertEqual(self.one("SELECT COUNT(*) FROM clean WHERE created LIKE '__.__.____%'"), 0)
        self.assertEqual(self.one("SELECT COUNT(*) FROM clean WHERE period = 'после'"), 3549)

    def test_known_gap_of_the_colleagues_cleaning_is_reproduced(self):
        # the text 'NULL' is still there - this is what the audit reports
        self.assertEqual(self.one("SELECT COUNT(*) FROM clean WHERE topic = 'NULL'"), 152)
        self.assertEqual(self.one("SELECT COUNT(*) FROM clean WHERE topic = 'без темы'"), 278)


class ReportTests(unittest.TestCase):
    def test_every_sql_block_of_the_audit_runs(self):
        report = Path(__file__).resolve().parents[1] / "reports" / "data_audit.md"
        blocks = list(sqlmd.blocks(report.read_text(encoding="utf-8")))
        self.assertEqual(len(blocks), 10)
        with contextlib.redirect_stdout(io.StringIO()):
            code = sqlmd.run(report)
        self.assertEqual(code, 0)

    def test_statement_splitter_ignores_semicolons_in_quotes(self):
        self.assertEqual(sqlmd.split_statements("SELECT ';'; SELECT 2;"), ["SELECT ';';", "SELECT 2;"])


if __name__ == "__main__":
    unittest.main()
