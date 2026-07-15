from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path

import pytest

from quant_system.backtest import permanent_portfolio as family42


ROOT = Path(__file__).resolve().parents[1]
SUPPLEMENT = (
    ROOT
    / "research/definitions/a_share_family42_cleanroom_mechanical_supplement_v1.json"
)
MANIFEST = ROOT / "research/definitions/a_share_family42_cleanroom_code_manifest_v1.json"
MODULE = ROOT / "src/quant_system/backtest/permanent_portfolio.py"
TEST_FILE = ROOT / "tests/test_permanent_portfolio_cleanroom.py"


def _rows(
    sessions: list[tuple[date, dict[str, float]]],
    *,
    volume: float = 2_000_000.0,
) -> tuple[family42.PriceVolumeRow, ...]:
    return tuple(
        family42.PriceVolumeRow(session, symbol, closes[symbol], volume)
        for session, closes in sessions
        for symbol in family42.SYMBOLS
    )


def _dataset(
    sessions: list[tuple[date, dict[str, float]]],
    *,
    volume: float = 2_000_000.0,
) -> family42.Family42Dataset:
    return family42.dataset_from_rows(
        _rows(sessions, volume=volume),
        source_sha256="a" * 64,
        snapshot_id="synthetic",
    )


def _closes(**overrides: float) -> dict[str, float]:
    result = {symbol: 100.0 for symbol in family42.SYMBOLS}
    result.update(overrides)
    return result


def test_accepted_supplement_and_manifest_bind_exact_current_bytes() -> None:
    supplement = family42.load_mechanical_supplement(SUPPLEMENT)
    assert supplement["family_number"] == 42
    assert supplement["implementation_ready"] is True
    assert supplement["boundary"]["strategy_candidate_available"] is False

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_commit"] == "2294adf0d94248fd08e0456a17da2cdc0108ced5"
    assert manifest["source_tree"] == "e1a9f69535adba5b2c17bfbed9451f6361ba3912"
    assert manifest["supplement"]["sha256"] == family42.SUPPLEMENT_SHA256
    assert manifest["implementation"]["sha256"] == hashlib.sha256(
        MODULE.read_bytes()
    ).hexdigest()
    assert manifest["tests"]["sha256"] == hashlib.sha256(TEST_FILE.read_bytes()).hexdigest()
    assert manifest["boundary"] == {
        "legacy_strategy_code_or_functions_used": False,
        "legacy_result_values_used": False,
        "real_data_opened": False,
        "outcomes_opened": False,
        "strategy_execution_authorized": False,
        "retrospective_mechanics_only": True,
        "strategy_candidate_available": False,
        "broker_order_paper_live_auto_available": False,
        "commit_or_push_authorized": False,
    }


def test_exact_183_gate_identity_matches_accepted_supplement() -> None:
    supplement = family42.load_mechanical_supplement(SUPPLEMENT)
    identities = family42.family42_gate_ids()
    assert len(identities) == 183
    assert len(set(identities)) == 183
    assert list(identities) == supplement["gates"]["ids"]
    assert identities[0] == (
        "core.development_2018_2021.offset_01.total_return_positive"
    )
    assert identities[143].endswith("offset_12.annualized_volatility_lt_csi300")
    assert identities[174].startswith("bootstrap.")
    assert identities[179] == "capacity.510300_SH.median_volume_proxy_ge_1000000"


def test_initial_cost_is_parameterized_and_every_offset_starts_four_by_twenty_five() -> None:
    dataset = _dataset(
        [
            (date(2018, 1, 2), _closes()),
            (date(2018, 1, 3), _closes(**{"510300.SH": 110.0})),
            (date(2018, 2, 1), _closes(**{"510300.SH": 110.0})),
        ]
    )
    twenty = family42.run_strategy(dataset, offset_month=2, cost_bps=20)
    fifty = family42.run_strategy(dataset, offset_month=12, cost_bps=50)

    for run in (twenty, fifty):
        first = run.ledger[0]
        assert first.start_weights == family42.TARGET_WEIGHTS
        assert first.initial_turnover == 1.0
        assert first.rebalance_turnover == 0.0
        assert first.portfolio_gross_factor == pytest.approx(1.025)
    assert twenty.ledger[0].initial_cost_fraction == pytest.approx(0.002)
    assert twenty.ledger[0].net_factor == pytest.approx(1.025 * 0.998)
    assert fifty.ledger[0].initial_cost_fraction == pytest.approx(0.005)
    assert fifty.ledger[0].net_factor == pytest.approx(1.025 * 0.995)

    boundary = twenty.ledger[1]
    assert boundary.rebalanced is True
    assert boundary.drifted_weights != family42.TARGET_WEIGHTS
    expected_turnover = 0.5 * sum(
        abs(dict(family42.TARGET_WEIGHTS)[symbol] - weight)
        for symbol, weight in boundary.drifted_weights
    )
    assert boundary.rebalance_turnover == pytest.approx(expected_turnover)
    assert boundary.rebalance_cost_fraction == pytest.approx(0.002 * expected_turnover)
    assert boundary.end_weights == family42.TARGET_WEIGHTS


def test_annual_schedule_uses_first_common_session_and_never_double_trades_initial_close() -> None:
    dataset = _dataset(
        [
            (date(2018, 1, 2), _closes()),
            (date(2018, 1, 3), _closes()),
            (date(2018, 2, 1), _closes()),
            (date(2018, 2, 2), _closes()),
            (date(2019, 1, 2), _closes()),
            (date(2019, 2, 1), _closes()),
        ]
    )
    assert family42.annual_rebalance_dates(dataset, 1) == (date(2019, 1, 2),)
    assert family42.annual_rebalance_dates(dataset, 2) == (
        date(2018, 2, 1),
        date(2019, 2, 1),
    )
    january = family42.run_strategy(dataset, offset_month=1, cost_bps=50)
    assert january.ledger[0].initial_turnover == 1.0
    assert january.ledger[0].rebalanced is False
    assert sum(item.rebalanced for item in january.ledger) == 1


def test_strategy_and_comparators_use_identical_20_and_50_bps_initial_costs() -> None:
    dataset = _dataset(
        [
            (date(2018, 1, 2), _closes()),
            (date(2018, 1, 3), _closes()),
            (date(2018, 1, 4), _closes()),
        ]
    )
    runs = family42.run_reported_costs(dataset)
    assert {cost for cost, _, _ in runs.strategies} == {20, 50}
    for cost, expected in ((20, 0.998), (50, 0.995)):
        strategy = runs.strategy(cost, 12)
        csi = runs.comparator("csi300", cost)
        cash = runs.comparator("cash", cost)
        assert strategy.ledger[0].net_factor == pytest.approx(expected)
        assert csi.ledger[0].net_factor == pytest.approx(expected)
        assert cash.ledger[0].net_factor == pytest.approx(expected)
        assert all(not item.rebalanced for item in csi.ledger)
        assert all(not item.rebalanced for item in cash.ledger)


def test_split_drawdown_uses_continuous_pre_split_running_peak() -> None:
    dataset = _dataset(
        [
            (date(2021, 12, 30), _closes()),
            (date(2021, 12, 31), _closes(**{symbol: 200.0 for symbol in family42.SYMBOLS})),
            (date(2022, 1, 3), _closes()),
            (date(2022, 1, 4), _closes(**{symbol: 110.0 for symbol in family42.SYMBOLS})),
        ]
    )
    result = family42.run_strategy(dataset, offset_month=12, cost_bps=50)
    metrics = family42.split_metrics(result, "validation_2022_2023")
    assert result.ledger[0].wealth == pytest.approx(1.99)
    assert result.ledger[1].running_peak == pytest.approx(1.99)
    assert metrics.maximum_drawdown == pytest.approx(-0.5)
    assert metrics.observation_count == 2


def _write_csv(path: Path, *, mutation: str | None = None) -> str:
    rows: list[dict[str, str]] = []
    for session in ("20180102", "20180103", "20180201"):
        for symbol in family42.SYMBOLS:
            rows.append(
                {
                    "snapshot_id": "fixture",
                    "ts_code": symbol,
                    "trade_date": session,
                    "open": "99",
                    "close": "100",
                    "high": "101",
                    "low": "98",
                    "volume": "2000000",
                    "amount": "0",
                    "provider_source": family42.PROVIDER_SOURCE,
                    "adjustment": "qfq",
                    "nav_available": "False",
                }
            )
    if mutation == "duplicate":
        rows.append(dict(rows[0]))
    elif mutation == "missing":
        rows = [row for row in rows if row["ts_code"] != "511880.SH"]
    elif mutation == "provenance":
        rows[0]["provider_source"] = "other"
    elif mutation == "negative_volume":
        rows[0]["volume"] = "-1"
    elif mutation == "non_equity_bad_volume":
        rows[1]["volume"] = "not-used"
    columns = list(family42.CSV_HEADER)
    if mutation == "header":
        columns[-1] = "changed"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_liquidity_csv(path: Path, *, mutation: str | None = None) -> str:
    rows = [
        {
            "ts_code": symbol,
            "name": f"fixture-{symbol}",
            "rows": "2063",
            "data_start": "2018-01-02",
            "data_end": "2026-07-07",
            "amount_materialized": "True",
            "turnover_materialized": "True",
            "nav_materialized": "False",
            "premium_discount_materialized": "False",
            "median_amount": str(200_000_000 + index),
            "median_turnover_rate": "1",
            "amount_missing_rate": "0",
            "turnover_missing_rate": "0",
            "field_status": "AMOUNT_MATERIALIZED",
        }
        for index, symbol in enumerate(family42.DEFENSIVE_SYMBOLS)
    ]
    if mutation == "duplicate":
        rows.append(dict(rows[0]))
    elif mutation == "missing":
        rows.pop()
    elif mutation == "window":
        rows[0]["data_start"] = "2018-01-03"
    elif mutation == "missingness":
        rows[0]["amount_missing_rate"] = "0.1"
    elif mutation == "malformed_required":
        rows[0]["median_amount"] = "nan"
    elif mutation == "extra_irrelevant":
        extra = dict(rows[0])
        extra.update(
            {
                "ts_code": "159999.SZ",
                "name": "",
                "rows": "not-an-integer",
                "data_start": "not-a-date",
                "data_end": "not-a-date",
                "amount_materialized": "False",
                "median_amount": "nan",
                "amount_missing_rate": "nan",
                "field_status": "",
            }
        )
        rows.extend((extra, dict(extra)))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=family42.LIQUIDITY_HEADER)
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_source_loader_binds_hash_header_provenance_and_common_rows(tmp_path) -> None:
    path = tmp_path / "fixture.csv"
    digest = _write_csv(path)
    dataset = family42._load_family42_csv_with_expected_identity(
        path,
        expected_source_sha256=digest,
    )
    assert dataset.source_sha256 == digest
    assert dataset.snapshot_id == "fixture"
    assert tuple(item.session_date for item in dataset.sessions) == (
        date(2018, 1, 2),
        date(2018, 1, 3),
        date(2018, 2, 1),
    )
    assert all(item.equity_volume == 2_000_000 for item in dataset.sessions)

    with pytest.raises(family42.Family42Error, match="SHA-256 changed"):
        family42.load_family42_csv(path)
    with pytest.raises(family42.Family42Error, match="SHA-256 changed"):
        family42._load_family42_csv_with_expected_identity(
            path,
            expected_source_sha256="0" * 64,
        )


def test_non_equity_volume_is_not_an_extra_capacity_requirement(tmp_path) -> None:
    path = tmp_path / "non-equity-volume.csv"
    digest = _write_csv(path, mutation="non_equity_bad_volume")
    dataset = family42._load_family42_csv_with_expected_identity(
        path,
        expected_source_sha256=digest,
    )
    assert len(dataset.sessions) == 3


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("header", "header"),
        ("duplicate", "duplicate"),
        ("missing", "absent"),
        ("provenance", "provenance"),
        ("negative_volume", "finite and nonnegative"),
    ],
)
def test_source_loader_fails_closed_on_malformed_selected_slice(
    tmp_path,
    mutation: str,
    message: str,
) -> None:
    path = tmp_path / f"{mutation}.csv"
    digest = _write_csv(path, mutation=mutation)
    with pytest.raises(family42.Family42Error, match=message):
        family42._load_family42_csv_with_expected_identity(
            path,
            expected_source_sha256=digest,
        )


def test_source_capture_rejects_symlink_and_replacement(
    monkeypatch,
    tmp_path,
) -> None:
    target = tmp_path / "fixture.csv"
    digest = _write_csv(target)
    link = tmp_path / "link.csv"
    link.symlink_to(target)
    with pytest.raises(family42.Family42Error, match="cannot safely open"):
        family42._load_family42_csv_with_expected_identity(
            link,
            expected_source_sha256=digest,
        )

    replacement = tmp_path / "replacement.csv"
    replacement.write_bytes(target.read_bytes())
    real_read = family42.os.read
    replaced = False

    def replacing_read(descriptor: int, count: int) -> bytes:
        nonlocal replaced
        chunk = real_read(descriptor, count)
        if chunk and not replaced:
            os.replace(replacement, target)
            replaced = True
        return chunk

    monkeypatch.setattr(family42.os, "read", replacing_read)
    with pytest.raises(family42.Family42Error, match="during descriptor capture"):
        family42._load_family42_csv_with_expected_identity(
            target,
            expected_source_sha256=digest,
        )
    assert replaced is True


def test_liquidity_loader_binds_bytes_and_rejects_public_fixture(tmp_path) -> None:
    path = tmp_path / "liquidity.csv"
    digest = _write_liquidity_csv(path)
    amounts = family42._load_defensive_median_amounts_with_expected_identity(
        path,
        expected_source_sha256=digest,
    )
    assert set(amounts) == set(family42.DEFENSIVE_SYMBOLS)
    assert all(value >= 200_000_000 for value in amounts.values())
    with pytest.raises(family42.Family42Error, match="SHA-256 changed"):
        family42.load_defensive_median_amounts(path)


def test_liquidity_loader_ignores_contract_irrelevant_extra_rows(tmp_path) -> None:
    path = tmp_path / "liquidity-extra.csv"
    digest = _write_liquidity_csv(path, mutation="extra_irrelevant")
    amounts = family42._load_defensive_median_amounts_with_expected_identity(
        path,
        expected_source_sha256=digest,
    )
    assert set(amounts) == set(family42.DEFENSIVE_SYMBOLS)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("duplicate", "duplicate"),
        ("missing", "missing"),
        ("window", "window"),
        ("missingness", "zero missingness"),
        ("malformed_required", "finite and nonnegative"),
    ],
)
def test_liquidity_loader_rejects_malformed_evidence(
    tmp_path,
    mutation: str,
    message: str,
) -> None:
    path = tmp_path / f"liquidity-{mutation}.csv"
    digest = _write_liquidity_csv(path, mutation=mutation)
    with pytest.raises(family42.Family42Error, match=message):
        family42._load_defensive_median_amounts_with_expected_identity(
            path,
            expected_source_sha256=digest,
        )


def test_liquidity_capture_rejects_symlink(tmp_path) -> None:
    target = tmp_path / "liquidity.csv"
    digest = _write_liquidity_csv(target)
    link = tmp_path / "liquidity-link.csv"
    link.symlink_to(target)
    with pytest.raises(family42.Family42Error, match="cannot safely open"):
        family42._load_defensive_median_amounts_with_expected_identity(
            link,
            expected_source_sha256=digest,
        )


def test_dataset_rejects_duplicates_nonfinite_and_unexpected_symbols() -> None:
    base = list(
        _rows(
            [
                (date(2018, 1, 2), _closes()),
                (date(2018, 1, 3), _closes()),
            ]
        )
    )
    with pytest.raises(family42.Family42Error, match="duplicate"):
        family42.dataset_from_rows(
            (*base, base[0]),
            source_sha256="a" * 64,
            snapshot_id="x",
        )
    bad = list(base)
    bad[0] = family42.PriceVolumeRow(date(2018, 1, 2), "BAD", 100.0, 1.0)
    with pytest.raises(family42.Family42Error, match="unexpected"):
        family42.dataset_from_rows(bad, source_sha256="a" * 64, snapshot_id="x")
    bad = list(base)
    bad[0] = family42.PriceVolumeRow(
        date(2018, 1, 2),
        family42.SYMBOLS[0],
        math.nan,
        1.0,
    )
    with pytest.raises(family42.Family42Error, match="finite"):
        family42.dataset_from_rows(bad, source_sha256="a" * 64, snapshot_id="x")


def test_pcg64_three_month_circular_bootstrap_nonconstant_golden() -> None:
    values = tuple(float(value) for value in range(1, 25))
    starts = family42.circular_block_start_indices(24, draws=3, seed=20_260_710)
    result = family42.family42_bootstrap(values, draws=3, seed=20_260_710)
    assert starts == (
        (18, 14, 16, 22, 12, 18, 17, 2),
        (14, 5, 10, 7, 14, 11, 18, 11),
        (22, 23, 11, 19, 21, 15, 10, 19),
    )
    assert result.uncentered_means == pytest.approx((15.875, 13.25, 16.5))
    assert result.centered_means == pytest.approx((3.375, 0.75, 4.0))
    assert result.lower_bound == pytest.approx(13.253125)
    assert result.diagnostic_p_value == pytest.approx(0.25)
    assert family42.BOOTSTRAP_Q == pytest.approx(0.05 / (42 * 2))


def test_bootstrap_and_correlation_fail_closed() -> None:
    with pytest.raises(family42.Family42Error, match="exactly 24"):
        family42.family42_bootstrap(tuple(range(23)), draws=3)
    with pytest.raises(family42.Family42Error, match="variance"):
        family42.pearson_sample((1.0, 1.0), (1.0, 2.0))
    assert family42.pearson_sample((1.0, 2.0, 3.0), (3.0, 2.0, 1.0)) == pytest.approx(
        -1.0
    )


def _long_synthetic_dataset() -> family42.Family42Dataset:
    rows: list[family42.PriceVolumeRow] = []
    step = 0
    for year in range(2018, 2027):
        final_month = 6 if year == 2026 else 12
        for month in range(1, final_month + 1):
            for day in (2, 16):
                session = date(year, month, day)
                for index, symbol in enumerate(family42.SYMBOLS):
                    drift = 0.004 + 0.001 * index
                    wave = 0.02 * math.sin((step + 1) * (index + 1) / 3.0)
                    close = 100.0 * math.exp(drift * step + wave)
                    rows.append(
                        family42.PriceVolumeRow(
                            session,
                            symbol,
                            close,
                            2_000_000.0 + index,
                        )
                    )
                step += 1
    return family42.dataset_from_rows(
        rows,
        source_sha256="b" * 64,
        snapshot_id="long-synthetic",
    )


def test_synthetic_evaluation_emits_exact_183_checks_without_promotion() -> None:
    result = family42._evaluate_family42(
        _long_synthetic_dataset(),
        defensive_median_amounts_cny={
            "511010.SH": 200_000_000.0,
            "518880.SH": 300_000_000.0,
            "511880.SH": 400_000_000.0,
        },
    )
    assert len(result.diagnostic_checks) == 183
    assert tuple(
        item.gate_id for item in result.diagnostic_checks
    ) == family42.family42_gate_ids()
    assert not isinstance(result, family42.Family42Evaluation)
    assert not hasattr(result, "checks")
    assert result.classification == "SYNTHETIC_MECHANICS_TEST_ONLY_NOT_FORMAL_ADJUDICATION"
    assert result.formal_adjudication_available is False
    assert result.strategy_candidate_available is False
    assert {cost for cost, _, _ in result.runs.strategies} == {20, 50}


def test_formal_evaluation_accepts_paths_only_and_rejects_forged_dataset(
    tmp_path,
) -> None:
    synthetic = _long_synthetic_dataset()
    object.__setattr__(synthetic, "_source_token", object())
    with pytest.raises(TypeError, match="unexpected keyword argument 'dataset'"):
        family42.evaluate_family42(
            dataset=synthetic,
            price_evidence_path=tmp_path / "must-not-open-price.csv",
            liquidity_evidence_path=tmp_path / "must-not-open.csv",
        )

    class ForgedDataset(family42.Family42Dataset):
        pass

    subclass = ForgedDataset(
        synthetic.sessions,
        family42.PRICE_CSV_SHA256,
        "forged-snapshot",
    )
    object.__setattr__(subclass, "_source_token", object())
    with pytest.raises(TypeError, match="unexpected keyword argument 'dataset'"):
        family42.evaluate_family42(
            dataset=subclass,
            price_evidence_path=tmp_path / "must-not-open-price.csv",
            liquidity_evidence_path=tmp_path / "must-not-open.csv",
        )


def test_formal_evaluation_descriptor_captures_price_path_before_liquidity(
    tmp_path,
) -> None:
    source = tmp_path / "price.csv"
    _write_csv(source)
    with pytest.raises(family42.Family42Error, match="source CSV SHA-256 changed"):
        family42.evaluate_family42(
            price_evidence_path=source,
            liquidity_evidence_path=tmp_path / "must-not-open.csv",
        )


def test_missing_holdout_month_zero_variance_and_bad_capacity_fail_closed() -> None:
    dataset = _dataset(
        [
            (date(2023, 12, 29), _closes()),
            (
                date(2024, 1, 2),
                _closes(**{symbol: 100.0 / 0.995 for symbol in family42.SYMBOLS}),
            ),
            (
                date(2024, 2, 2),
                _closes(**{symbol: 100.0 / 0.995 for symbol in family42.SYMBOLS}),
            ),
        ]
    )
    flat = family42.run_strategy(dataset, offset_month=12, cost_bps=50)
    with pytest.raises(family42.Family42Error, match="24 complete"):
        family42.monthly_returns(flat)
    zero_row = lambda session: family42.LedgerRow(  # noqa: E731
        session,
        family42.TARGET_WEIGHTS,
        1.0,
        family42.TARGET_WEIGHTS,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        family42.TARGET_WEIGHTS,
        1.0,
        1.0,
        False,
    )
    exactly_flat = family42.SimulationResult(
        12,
        50,
        family42.TARGET_WEIGHTS,
        (zero_row(date(2024, 1, 2)), zero_row(date(2024, 2, 2))),
    )
    with pytest.raises(family42.Family42Error, match="variance"):
        family42.split_metrics(exactly_flat, "holdout_2024_2025")
    with pytest.raises(family42.Family42Error, match="exactly three"):
        family42._evaluate_family42(
            _long_synthetic_dataset(),
            defensive_median_amounts_cny={"511010.SH": 1.0},
        )
