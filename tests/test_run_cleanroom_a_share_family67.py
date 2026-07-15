from __future__ import annotations

import csv
from datetime import date, timedelta
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace

import pytest

from quant_system.backtest.dual_momentum import MonthlyTarget, OpenCloseBar


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_cleanroom_a_share_family67.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("run_cleanroom_a_share_family67", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_frozen_definition_is_hash_bound_outcome_blind_and_exact_family67() -> None:
    module = _load_script()
    definition, digest = module._load_definition()
    assert digest == module.DEFINITION_SHA256
    assert definition["family_number"] == 67
    assert definition["classification"] == "RETROSPECTIVE_CLEANROOM_MIGRATION_REPLAY"
    assert definition["gates"]["expected_count"] == 23
    assert definition["lineage_controls"] == {
        "legacy_python_permitted_as_implementation_input": False,
        "legacy_result_values_permitted_as_test_oracle": False,
        "status_mutation_allowed": False,
        "eligible_for_new_strategy_evidence": False,
        "strict_pit": False,
        "strategy_candidate_available": False,
        "promotion_allowed": False,
    }


def test_definition_freezes_mapping_signal_costs_and_label_only_supplement() -> None:
    module = _load_script()
    definition, _ = module._load_definition()
    assert {
        item["asset_class"]: item["symbol"] for item in definition["asset_classes"]
    } == {
        "domestic_large_cap_equity": "510300.SH",
        "domestic_mid_cap_equity": "510500.SH",
        "overseas_broad_equity": "513500.SH",
        "overseas_growth_equity": "513100.SH",
        "gold": "518880.SH",
        "treasury_bond": "511010.SH",
        "cash_like": "511880.SH",
    }
    assert definition["signal"]["momentum_formula"] == "close[d-21] / close[d-252] - 1"
    assert definition["signal"]["volatility_sessions"] == 60
    assert definition["execution_accounting"]["gate_cost_bps"] == 50
    supplement = definition["evaluation_contract_supplement"]
    assert supplement["sha256"] == (
        "20c7b1a289f6c7130f035b8d720ee2ba62b6881245c8378f1871fddc852e0d9f"
    )
    assert "observed values" in supplement["permitted_use"]
    assert definition["inference"]["seed"] == 20260710


def test_default_path_opens_no_source_socket_or_output(monkeypatch, capsys) -> None:
    module = _load_script()
    monkeypatch.setattr(module, "_load_source", lambda *args: pytest.fail("source opened"))
    monkeypatch.setattr(module, "_publish", lambda *args: pytest.fail("output written"))
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: pytest.fail("socket opened"))
    assert module.main([]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "definition_sha256": module.DEFINITION_SHA256,
        "network_used": False,
        "output_written": False,
        "source_data_opened": False,
        "status": "VALIDATE_DEFINITION_ONLY",
    }


def _write_fixture_csv(module, path: Path) -> dict:
    definition, _ = module._load_definition()
    source = definition["source_data"]
    columns = source["expected_columns"]
    symbols = [item["symbol"] for item in definition["asset_classes"]]
    rows = []
    for offset, session in enumerate(("20260102", "20260105")):
        for index, symbol in enumerate(symbols):
            price = 100 + offset + index / 10
            rows.append(
                {
                    "snapshot_id": source["snapshot_id"],
                    "ts_code": symbol,
                    "trade_date": session,
                    "open": str(price),
                    "close": str(price + 0.5),
                    "high": str(price + 1),
                    "low": str(price - 1),
                    "volume": "100",
                    "amount": "200",
                    "provider_source": source["provider_source"],
                    "adjustment": source["adjustment"],
                    "nav_available": "False",
                }
            )
    rows.append({**rows[0], "trade_date": "20260106"})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    definition["source_data"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return definition


def test_source_loader_hashes_sorted_selected_and_common_slices(tmp_path) -> None:
    module = _load_script()
    path = tmp_path / "fixture.csv"
    definition = _write_fixture_csv(module, path)
    loaded = module._load_source(path, definition)
    assert loaded.selected_row_count == 15
    assert loaded.common_session_count == 2
    assert loaded.common_row_count == 14
    assert loaded.excluded_non_common_rows == 1
    assert loaded.per_symbol_row_counts == (3, 2, 2, 2, 2, 2, 2)
    assert len(loaded.rows) == 14
    assert loaded.first_common_date == date(2026, 1, 2)
    assert loaded.last_common_date == date(2026, 1, 5)


def test_source_loader_rejects_hash_header_provenance_duplicate_and_bad_price(tmp_path) -> None:
    module = _load_script()
    path = tmp_path / "fixture.csv"
    definition = _write_fixture_csv(module, path)
    definition["source_data"]["sha256"] = "0" * 64
    with pytest.raises(module.Family67ReplayError, match="SHA-256 changed"):
        module._load_source(path, definition)

    definition = _write_fixture_csv(module, path)
    payload = path.read_text(encoding="utf-8").replace(",qfq,", ",hfq,", 1)
    path.write_text(payload, encoding="utf-8")
    definition["source_data"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(module.Family67ReplayError, match="provenance changed"):
        module._load_source(path, definition)

    definition = _write_fixture_csv(module, path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(path.read_text(encoding="utf-8").splitlines()[1] + "\n")
    definition["source_data"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(module.Family67ReplayError, match="duplicate"):
        module._load_source(path, definition)

    definition = _write_fixture_csv(module, path)
    payload = path.read_text(encoding="utf-8").replace(",100.0,100.5,", ",nan,100.5,", 1)
    path.write_text(payload, encoding="utf-8")
    definition["source_data"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(module.Family67ReplayError, match="finite and positive"):
        module._load_source(path, definition)


def test_source_capture_rejects_path_replacement_after_descriptor_read(
    monkeypatch,
    tmp_path,
) -> None:
    module = _load_script()
    path = tmp_path / "fixture.csv"
    definition = _write_fixture_csv(module, path)
    replacement = tmp_path / "replacement.csv"
    replacement.write_bytes(path.read_bytes())
    real_read = module.os.read
    replaced = False

    def replacing_read(descriptor, count):
        nonlocal replaced
        chunk = real_read(descriptor, count)
        if chunk and not replaced:
            os.replace(replacement, path)
            replaced = True
        return chunk

    monkeypatch.setattr(module.os, "read", replacing_read)
    with pytest.raises(module.Family67ReplayError, match="replaced during descriptor capture"):
        module._load_source(path, definition)
    assert replaced is True


def test_source_capture_rejects_symlink(tmp_path) -> None:
    module = _load_script()
    target = tmp_path / "fixture.csv"
    definition = _write_fixture_csv(module, target)
    link = tmp_path / "fixture-link.csv"
    link.symlink_to(target)
    with pytest.raises(module.Family67ReplayError, match="cannot safely open"):
        module._load_source(link, definition)


def test_bh_adjustment_is_exact_three_test_step_up_with_stable_ties() -> None:
    module = _load_script()
    assert module._bh_adjusted([0.01, 0.02, 0.9]) == pytest.approx([0.03, 0.03, 0.9])
    assert module._bh_adjusted([0.02, 0.02, 0.02]) == pytest.approx([0.02, 0.02, 0.02])
    with pytest.raises(module.Family67ReplayError, match="exactly three"):
        module._bh_adjusted([0.01, 0.02])


def test_pre_anchor_targets_are_filtered_after_history_and_cash_carries_to_first_target() -> None:
    module = _load_script()
    pre_anchor = MonthlyTarget(
        decision_date=date(2018, 12, 30),
        execution_date=date(2018, 12, 31),
        weights=(("AAA", 0.5), ("CASH", 0.5)),
        selected_symbols=("AAA",),
        momentum_by_symbol=(),
        volatility_by_symbol=(),
    )
    post_anchor = MonthlyTarget(
        decision_date=date(2019, 1, 31),
        execution_date=date(2019, 2, 1),
        weights=(("AAA", 0.5), ("CASH", 0.5)),
        selected_symbols=("AAA",),
        momentum_by_symbol=(),
        volatility_by_symbol=(),
    )
    generated = (pre_anchor, post_anchor)
    retained = module._targets_after_anchor(generated, date(2019, 1, 1))
    assert generated[0] is pre_anchor
    assert retained == (post_anchor,)

    rows = []
    session = date(2018, 12, 30)
    while session <= date(2019, 2, 2):
        offset = (session - date(2018, 12, 30)).days
        rows.extend(
            (
                OpenCloseBar(session, "AAA", 100.0, 100.0),
                OpenCloseBar(session, "CASH", 100.0 + offset, 100.0 + offset),
            )
        )
        session += timedelta(days=1)
    result = module.run_monthly_open_close_backtest(
        tuple(rows),
        retained,
        cash_like_symbol="CASH",
        cost_bps_per_turnover_side=0.0,
        initial_close_date=date(2019, 1, 1),
    )
    assert result.sessions[0].session_date == date(2019, 1, 2)
    assert result.sessions[0].rebalanced is False
    first_rebalance = next(item for item in result.sessions if item.rebalanced)
    assert first_rebalance.session_date == date(2019, 2, 1)
    assert first_rebalance.decision_date == date(2019, 1, 31)


def _synthetic_loaded(module):
    definition, _ = module._load_definition()
    assets = sorted(item["symbol"] for item in definition["asset_classes"])
    start = date(2021, 1, 1)
    end = date(2026, 7, 7)
    drifts = {symbol: 0.0002 + 0.00005 * index for index, symbol in enumerate(assets)}
    rows = []
    session = start
    offset = 0
    while session <= end:
        for index, symbol in enumerate(assets):
            close = 100.0 * math.exp(
                drifts[symbol] * offset + 0.003 * math.sin(offset * (index + 1) / 7.0)
            )
            rows.append(OpenCloseBar(session, symbol, close * 0.999, close))
        offset += 1
        session += timedelta(days=1)
    return module.LoadedSource(
        rows=tuple(rows),
        source_sha256="a" * 64,
        selected_slice_sha256="b" * 64,
        common_slice_sha256="c" * 64,
        selected_row_count=len(rows),
        common_session_count=offset,
        common_row_count=len(rows),
        excluded_non_common_rows=0,
        per_symbol_row_counts=(offset,) * 7,
        first_common_date=start,
        last_common_date=end,
    )


def test_synthetic_report_derives_exact_23_gates_without_promoting(monkeypatch) -> None:
    module = _load_script()
    definition, digest = module._load_definition()
    definition["inference"]["bootstrap_draws"] = 32
    definition["execution_accounting"]["cost_bps_per_turnover_side"] = [50]
    report = module.build_report(
        definition,
        digest,
        _synthetic_loaded(module),
        source_commit="a" * 40,
    )
    assert report["gate_results"]["total_count"] == 23
    expected_gate_ids = {
        f"{split}.{suffix}"
        for split in (
            "validation_2022_2023",
            "holdout_2024_2025",
            "forward_2026h1",
        )
        for suffix in (
            "minimum_complete_months",
            "positive_net_annualized_return",
            "annualized_above_static",
        )
    }
    expected_gate_ids.update(
        f"{split}.drawdown_no_worse_than_static"
        for split in ("validation_2022_2023", "holdout_2024_2025")
    )
    expected_gate_ids.update(
        f"{split}.{gate}.{comparator}"
        for split in ("validation_2022_2023", "holdout_2024_2025")
        for gate in ("lower_bound", "bh_significant")
        for comparator in (
            "static_diversified",
            "equal_weight_six_risky",
            "cash_like",
        )
    )
    assert {item["gate_id"] for item in report["gate_results"]["checks"]} == (
        expected_gate_ids
    )
    assert report["classification"] == "RETROSPECTIVE_CLEANROOM_MIGRATION_REPLAY"
    assert report["source_data"]["strict_pit"] is False
    assert report["lineage"]["strategy_candidate_available"] is False


def test_git_identity_accepts_sha1_or_sha256_and_rejects_dirty(monkeypatch) -> None:
    module = _load_script()

    def fake_run(args, **kwargs):
        del kwargs
        if args[-2:] == ["status", "--porcelain=v1"]:
            return SimpleNamespace(stdout="")
        if args[-2:] == ["rev-parse", "HEAD"]:
            return SimpleNamespace(stdout="a" * fake_run.length + "\n")
        raise AssertionError(args)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    for length in (40, 64):
        fake_run.length = length
        assert module._git_identity() == "a" * length
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="?? untracked\n"),
    )
    with pytest.raises(module.Family67ReplayError, match="clean committed"):
        module._git_identity()


def test_publish_is_atomic_non_overwriting_and_strict_json(tmp_path) -> None:
    module = _load_script()
    output = tmp_path / "result.json"
    digest, sidecar = module._publish({"value": 1.0}, output)
    assert hashlib.sha256(output.read_bytes()).hexdigest() == digest
    assert json.loads(output.read_text(encoding="utf-8")) == {"value": 1.0}
    assert sidecar.read_text(encoding="ascii") == f"{digest}  result.json\n"
    with pytest.raises(module.Family67ReplayError, match="already exists"):
        module._publish({"value": 2.0}, output)
