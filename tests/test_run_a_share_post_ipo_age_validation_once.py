from __future__ import annotations

# ruff: noqa: E401, E701, E702
import importlib.util, json, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ipo_age_once", ROOT / "scripts/run_a_share_post_ipo_age_validation_once.py"
)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def test_bootstrap_literal_centered_golden() -> None:
    mean, p_value, lower = runner._bootstrap((0.01, -0.02, 0.03, 0.04, -0.01))
    assert (mean, p_value, lower) == pytest.approx((0.01, 0.1212878712128787, -0.006))


def test_report_has_aggregate_values_and_exact_six_gates() -> None:
    report = runner._report((0.02,) * 23, (0.01,) * 23, invalid=0)
    assert report["status"] == "VALIDATION_PASS"
    assert tuple(report["gates"]) == (
        "interval_count_20_to_23",
        "zero_invalid_and_50_pairs_each",
        "mean_active_positive",
        "centered_bootstrap_p_value_lte_1_60",
        "centered_bootstrap_lower_bound_positive",
        "seasoned_annualized_exceeds_young",
    )
    assert all(type(v) is bool for v in report["gates"].values()) and set(report).isdisjoint(
        {"pairs", "symbols", "monthly_returns", "months"}
    )


@pytest.mark.parametrize("values", ((0.01,) * 22, (0.01,) * 24, (0.01,) * 22 + (float("nan"),)))
def test_exact_months_and_nonfinite_fail_closed(values: tuple[float, ...]) -> None:
    with pytest.raises(runner.ValidationError):
        runner._report(values, values, invalid=0)


def test_marker_is_atomic_and_not_reusable(tmp_path: Path) -> None:
    marker = tmp_path / "private" / "claim.consumed"
    runner._claim(marker, {"commit": "a" * 40})
    assert json.loads(marker.read_text())["status"] == "CLAIMED_BEFORE_QFQ_OPEN_ACCESS"
    with pytest.raises(runner.ValidationError, match="already exists"):
        runner._claim(marker, {})


def test_prepare_is_pre_outcome_and_requires_23x50(tmp_path: Path) -> None:
    class Result:
        def fetchall(self):
            return [
                (f"d{m}", f"e{m}", f"x{m}", f"y{m}-{p}", f"s{m}-{p}", "Main", 1.0, 1.0)
                for m in range(23)
                for p in range(50)
            ]

    class Conn:
        def __init__(self):
            self.sql = ""
            self.sqls: list[str] = []

        def execute(self, sql, *args):
            self.sql = sql
            self.sqls.append(sql)
            if "SELECT ts_code,trade_date,adj_factor" in sql:
                _, entry, exit_day, *symbols = args[0]
                return type(
                    "Identity",
                    (),
                    {
                        "fetchall": lambda _: [
                            (symbol, day, 1.0, runner.preflight.CLASSIFICATION, False, "a" * 64)
                            for symbol in symbols
                            for day in (entry, exit_day)
                        ]
                    },
                )()
            return Result()

    database = tmp_path / "db"
    database.write_bytes(b"fixture")
    conn = Conn()
    prepared = runner._prepare(conn, database, runner._sha(database))
    assert len(prepared.intervals) == 23 and all(len(v) == 50 for v in prepared.pairs.values())
    assert (
        "qfq_open" not in conn.sql and "development" not in conn.sql and "holdout" not in conn.sql
    )
    prepared_sql = "\n".join(conn.sqls)
    assert "bu AS (SELECT * FROM bars WHERE key_n=1)" in prepared_sql
    assert "f.n-f.first_w=19" in prepared_sql
    assert "synthetic_data IS NOT DISTINCT FROM false" in prepared_sql
    assert "coalesce(regexp_full_match(row_hash,'[0-9a-f]{64}'),false)" in prepared_sql


def test_precheck_failure_does_not_claim_or_open_outcomes(tmp_path: Path, monkeypatch) -> None:
    database, marker = tmp_path / "db", tmp_path / "claim"
    database.write_bytes(b"fixture")
    monkeypatch.setattr(runner, "_bindings", lambda *_: {"commit": "a" * 40})
    monkeypatch.setattr(
        runner, "_prepare", lambda *_: (_ for _ in ()).throw(runner.ValidationError("missing"))
    )

    class Duck:
        @staticmethod
        def connect(*_a, **_k):
            return type("C", (), {"close": lambda self: None})()

    monkeypatch.setitem(sys.modules, "duckdb", Duck)
    with pytest.raises(runner.ValidationError):
        runner.run_once(database, marker, "a" * 40)
    assert not marker.exists()
