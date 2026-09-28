from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
import sqlglot
from sqlglot import exp

from jobs_pipeline.stats import wilson

ROOT = Path(__file__).parent.parent
SQL_FILES = (
    ROOT / "sql" / "ddl_events.sql",
    ROOT / "sql" / "views.sql",
    ROOT / "sql" / "dq_checks.sql",
)


def _statements(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    parts = [p.strip() for p in text.split(";") if p.strip()]
    return parts


@pytest.mark.parametrize("sql_file", SQL_FILES, ids=lambda p: p.name)
def test_sql_parses_bigquery(sql_file: Path) -> None:
    for stmt in _statements(sql_file):
        sqlglot.parse_one(stmt, read="bigquery")


def test_wilson_known_values() -> None:
    low, high = wilson(10, 20, z=1.96)
    assert low == pytest.approx(0.2993, abs=0.001)
    assert high == pytest.approx(0.7007, abs=0.001)


def _final_select(view: str, group_col: str) -> str:
    text = (ROOT / "sql" / "views.sql").read_text(encoding="utf-8")
    block = text.split(f"jobs.{view}` AS", 1)[1].split(";", 1)[0]
    return block[block.rindex(f"\nSELECT\n  {group_col},") :]


@pytest.mark.parametrize(
    ("view", "group_col"),
    [("response_rate_by_title_family", "title_family"), ("response_rate_by_cv_version", "cv_version")],
)
def test_response_rate_sql_matches_stats_wilson(view: str, group_col: str) -> None:
    duck_sql = sqlglot.transpile(_final_select(view, group_col), read="bigquery", write="duckdb")[0]
    con = duckdb.connect()
    cases = [("a", 20, 10), ("b", 2, 1), ("c", 40, 0), ("d", 35, 35), ("e", 29, 7)]
    con.execute(f"CREATE TABLE base({group_col} VARCHAR, n_applied BIGINT, n_replied BIGINT)")
    con.executemany("INSERT INTO base VALUES (?, ?, ?)", cases)
    rows = {r[0]: r for r in con.execute(duck_sql).fetchall()}
    assert set(rows) == {c[0] for c in cases}
    for key, n, k in cases:
        _, _n, _k, rate, low, high, flag = rows[key]
        want_low, want_high = wilson(k, n)
        assert low == pytest.approx(max(0.0, want_low), abs=1e-9)
        assert high == pytest.approx(min(1.0, want_high), abs=1e-9)
        assert rate == pytest.approx(k / n)
        assert flag == ("insufficient_n" if n < 30 else "ok")
