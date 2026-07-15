#!/usr/bin/env python3
"""Run the bounded synthetic P4 system-conformance fixture.

Status: FROZEN_ONE_OFF_EVIDENCE / NO_GENERALIZATION. This is a frozen one-off
evidence reproducer, not a general backtest runner. Do not import or generalize
it into the runtime API.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any
from zoneinfo import ZoneInfo

from quant_system.backtest import (
    Portfolio,
    TerminalAction,
    TransactionCostModel,
    advance_blocked_exit,
    blocked_exit_from_receipt,
    execute_ready_blocked_exit,
    run_static_rebalance,
)
from quant_system.backtest.event_loop import ExecutionInput
from quant_system.data import (
    AcceptedSession,
    AcceptedSessionCalendar,
    CorporateActionIdentity,
    SourceIdentity,
)
from quant_system.markets.common import FillDecision
from quant_system.markets.universe import StatusEvidence

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "research/definitions/p4_v2_engine_golden_static_allocation_v1.json"
FIXTURE = ROOT / "research/fixtures/p4_v2_engine_golden_static_allocation_v1.json"
RESULT = ROOT / "research/reports/p4_v2_engine_golden_static_allocation_v1_result.json"
VALIDATION_ID = "P4_V2_ENGINE_GOLDEN_STATIC_ALLOCATION_V1"
GATES = (
    "definition_and_fixture_hashes_exact",
    "clean_committed_runtime_identity",
    "synthetic_only_boundary",
    "calendar_and_source_cutoffs",
    "initial_allocation_and_costs_exact",
    "split_value_and_once_only",
    "distribution_entitlement_and_pay_date_once_only",
    "blocked_exit_retries_and_delay_exact",
    "terminal_value_and_nonrepurchase_exact",
    "settlement_cash_timing_exact",
    "nav_accounting_identity_exact",
    "receipt_and_stage_hash_chain_exact",
    "deterministic_replay_and_mutation_sensitivity",
)
SCOPE = (
    "research/definitions/p4_v2_engine_golden_static_allocation_v1.json",
    "research/fixtures/p4_v2_engine_golden_static_allocation_v1.json",
    "scripts/run_p4_system_validation.py",
    "tests/test_p4_system_validation.py",
)
NINE_PLACES = Decimal("0.000000001")
UTC = timezone.utc


class ValidationError(ValueError):
    """Raised when the frozen packet is malformed or no longer exact."""


def _pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ValidationError(f"nonfinite JSON constant: {value}")


def strict_load(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_pairs,
        parse_constant=_nonfinite,
    )
    if type(value) is not dict:
        raise ValidationError("top-level JSON value must be an object")
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _keys(value: dict[str, Any], required: set[str], optional: set[str] | None = None) -> None:
    optional = optional or set()
    actual = set(value)
    if not required <= actual or actual - required - optional:
        raise ValidationError(
            f"object keys changed: missing={sorted(required - actual)}, "
            f"extra={sorted(actual - required - optional)}"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValidationError("timestamps must be timezone-aware")
    return parsed.astimezone(UTC)


def _day(value: str) -> date:
    return date.fromisoformat(value)


def _decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValidationError("booleans are not numeric values")
    parsed = Decimal(str(value))
    if not parsed.is_finite():
        raise ValidationError("numeric values must be finite")
    return parsed


def _number(value: Any) -> str:
    return format(_decimal(value).quantize(NINE_PLACES, rounding=ROUND_HALF_EVEN), "f")


def _source(label: str, available_at: datetime, payload: Any) -> SourceIdentity:
    return SourceIdentity(
        f"https://p4-synthetic.invalid/{label}",
        hashlib.sha256(_canonical(payload)).hexdigest(),
        available_at,
        available_at + timedelta(seconds=1),
        label,
    )


def _calendar(fixture: dict[str, Any]) -> AcceptedSessionCalendar:
    zone = ZoneInfo(fixture["exchange_timezone"])
    available = datetime(2000, 1, 1, tzinfo=UTC)
    sessions = []
    for value in fixture["calendar_dates"]:
        day = _day(value)
        payload = {"date": value, "timezone": fixture["exchange_timezone"]}
        sessions.append(
            AcceptedSession(
                day,
                datetime.combine(day, time(9, 30), zone),
                datetime.combine(day, time(16), zone),
                _source(f"calendar/{value}", available, payload),
                fixture["exchange_timezone"],
            )
        )
    return AcceptedSessionCalendar(tuple(sessions))


def _statuses(stage_id: str, row: dict[str, Any], timezone_name: str) -> tuple[StatusEvidence, ...]:
    symbol = row["symbol"]
    values = {
        "listed": True,
        "delisted": row.get("delisted", False),
        "st": False,
        "suspended": row.get("suspended", False),
    }
    available = datetime(2000, 1, 1, tzinfo=UTC)
    return tuple(
        StatusEvidence(
            f"{stage_id}:{symbol}:{kind}",
            symbol,
            kind,  # type: ignore[arg-type]
            value,
            date(1990, 1, 1),
            None,
            timezone_name,
            _source(f"status/{stage_id}/{symbol}/{kind}", available, values),
        )
        for kind, value in values.items()
    )


def _action(stage_id: str, symbol: str, value: dict[str, Any], timezone_name: str):
    common = {
        "subject_id": symbol,
        "action_id": value["action_id"],
        "action_type": value["action_type"],
        "effective_at": _dt(value["effective_at"]),
        "source": _source(
            f"action/{stage_id}/{value['action_id']}", _dt(value["available_at"]), value
        ),
        "exchange_timezone": timezone_name,
        "ex_date": _day(value["ex_date"]),
    }
    if value["action_type"] in {"split", "reverse_split"}:
        return CorporateActionIdentity(**common, split_ratio=_decimal(value["split_ratio"]))
    return CorporateActionIdentity(
        **common,
        record_date=_day(value["record_date"]),
        pay_date=_day(value["pay_date"]),
        cash_amount=_decimal(value["cash_amount"]),
        currency="USD",
        unit="per_share",
    )


def _row(stage: dict[str, Any], value: dict[str, Any], timezone_name: str) -> ExecutionInput:
    stage_id, symbol = stage["stage_id"], value["symbol"]
    actions = tuple(
        _action(stage_id, symbol, action, timezone_name)
        for action in value.get("corporate_actions", [])
    )
    terminal_value = value.get("terminal_action")
    terminal = None
    if terminal_value is not None:
        terminal = TerminalAction(
            terminal_value["event_id"],
            terminal_value["action_type"],
            _dt(terminal_value["effective_at"]),
            float(_decimal(terminal_value["recovery_per_share"])),
            _source(
                f"terminal/{stage_id}/{terminal_value['event_id']}",
                _dt(terminal_value["available_at"]),
                terminal_value,
            ),
        )
    price = value["open_price"]
    return ExecutionInput(
        symbol=symbol,
        market="us",
        open_price=None if price is None else float(_decimal(price)),
        currency="USD",
        source=_source(
            f"bar/{stage_id}/{symbol}", _dt(value["source_available_at"]), value
        ),
        status_records=_statuses(stage_id, value, timezone_name),
        action_types=tuple(value.get("action_types", [])),
        corporate_actions=actions,
        terminal_action=terminal,
    )


def _runtime_identity(repo: Path, require_clean: bool) -> dict[str, Any]:
    def git(*arguments: str) -> str:
        result = subprocess.run(
            ("git", "-C", str(repo), *arguments),
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    dirty = git("status", "--porcelain=v1")
    if require_clean and dirty:
        raise ValidationError("--execute requires a clean committed worktree")
    if require_clean:
        for path in SCOPE:
            git("ls-files", "--error-unmatch", path)
    return {
        "clean_committed": not dirty,
        "commit": git("rev-parse", "HEAD^{commit}"),
        "tree": git("rev-parse", "HEAD^{tree}"),
    }


def _simulate(fixture: dict[str, Any]) -> dict[str, Any]:
    calendar = _calendar(fixture)
    costs = TransactionCostModel(
        commission_rate=float(_decimal(fixture["commission_bps"]) / 10_000),
        sell_tax_rate=float(_decimal(fixture["sell_tax_bps"]) / 10_000),
    )
    portfolio = Portfolio.us(float(_decimal(fixture["initial_cash"])), costs=costs)
    stage_hash, blocked = "0" * 64, None
    ledger, receipts, receipt_hashes, receipt_stages, stage_hashes = [], [], [], [], []
    timezone_name = fixture["exchange_timezone"]
    for stage in fixture["stages"]:
        rows = tuple(_row(stage, value, timezone_name) for value in stage["rows"])
        before = deepcopy(portfolio)
        result = run_static_rebalance(
            portfolio,
            calendar,
            signal_session=_day(stage["signal_date"]),
            decision_at=_dt(stage["decision_at"]),
            execution_inputs=rows,
            target_weights=lambda _, weights=stage["target_weights"]: {
                symbol: float(_decimal(weight)) for symbol, weight in weights.items()
            },
            slippage_bps=float(_decimal(fixture["slippage_bps"])),
            prior_stage_hash=stage_hash,
        )
        stage_hash = result.stage_hash
        stage_hashes.append(stage_hash)
        receipts.extend(result.receipts)
        receipt_hashes.extend(result.receipt_hashes)
        receipt_stages.extend([stage["stage_id"]] * len(result.receipts))
        blocked_receipts = [item for item in result.receipts if item.reason == "confirmed_halt"]
        if stage["stage_id"] == "terminal_and_blocked_exit_1":
            blocked = blocked_exit_from_receipt(blocked_receipts[0], result.context, calendar)
        elif stage["stage_id"] == "blocked_exit_2":
            assert blocked is not None
            blocked = advance_blocked_exit(
                blocked,
                session=result.context.execution_session.session_date,
                decision_at=result.context.decision_at,
                decision=FillDecision(False, None, blocked_receipts[0].reason),
            )
        elif stage["stage_id"] == "blocked_exit_filled":
            assert blocked is not None
            fill = next(item for item in result.receipts if item.side == "sell")
            probe = deepcopy(before)
            probe.start_session(result.context.execution_session.session_date)
            blocked, trade = execute_ready_blocked_exit(
                blocked,
                portfolio=probe,
                session=result.context.execution_session.session_date,
                decision_at=result.context.decision_at,
                decision=FillDecision(True, fill.price, "filled"),
            )
            if _number(trade.cash_change) != _number(fill.cash_change):
                raise ValidationError("blocked-order and event-loop sale disagree")
        delay = None
        if blocked is not None:
            delay = blocked.delay_sessions if not blocked.pending else len(blocked.attempts)
        portfolio = result.portfolio
        ledger.append(
            {
                "blocked_delay": delay,
                "final_nav": _number(result.final_nav),
                "pending_cash": _number(portfolio.pending_cash_total),
                "positions": {
                    symbol: _number(position.shares)
                    for symbol, position in sorted(portfolio.positions.items())
                },
                "receipt_reasons": [item.reason for item in result.receipts],
                "settled_cash": _number(portfolio.available_cash),
                "stage_id": stage["stage_id"],
            }
        )
    commission = sum(Decimal(str(item.commission)) for item in receipts)
    slippage = Decimal("0")
    raw_prices = {
        stage["stage_id"]: {row["symbol"]: row["open_price"] for row in stage["rows"]}
        for stage in fixture["stages"]
    }
    for stage_id, receipt in zip(receipt_stages, receipts, strict=True):
        if receipt.side not in {"buy", "sell"} or not receipt.filled_shares:
            continue
        raw = _decimal(raw_prices[stage_id][receipt.symbol])
        fill = _decimal(receipt.price)
        delta = fill - raw if receipt.side == "buy" else raw - fill
        slippage += delta * _decimal(receipt.filled_shares)
    final_nav = _decimal(ledger[-1]["final_nav"])
    residual = final_nav - (
        _decimal(fixture["initial_cash"]) + Decimal("550") - commission - slippage
    )
    return {
        "accounting_residual": _number(residual),
        "blocked_attempt_count": sum(item.reason == "confirmed_halt" for item in receipts),
        "commission_total": _number(commission),
        "corporate_action_receipt_count": sum(
            item.side in {"distribution", "split", "terminal"} for item in receipts
        ),
        "final_nav": ledger[-1]["final_nav"],
        "receipt_count": len(receipts),
        "receipt_hashes": receipt_hashes,
        "slippage_total": _number(slippage),
        "stage_hashes": stage_hashes,
        "stages": ledger,
        "trade_fill_count": sum(
            item.side in {"buy", "sell"} and item.filled_shares > 0 for item in receipts
        ),
    }


def _contract(definition: dict[str, Any], fixture: dict[str, Any], fixture_path: Path) -> None:
    _keys(
        definition,
        {
            "date", "evidence_class", "family_number", "fixture_path", "fixture_sha256",
            "forbidden_interpretations", "golden_ledger", "market", "phase",
            "real_market_data_used", "research_id", "runtime_contract", "schema_version",
            "strategy_candidate_available", "strategy_evidence_eligible",
            "strategy_gate_counts", "strict_gates",
        },
    )
    _keys(
        fixture,
        {
            "calendar_dates", "commission_bps", "exchange_timezone", "fixture_id",
            "initial_cash", "market", "schema_version", "sell_tax_bps", "slippage_bps",
            "source_host", "stages", "symbols", "synthetic_only",
        },
    )
    stage_ids = (
        "entry", "actions", "distribution_pending", "distribution_paid",
        "terminal_and_blocked_exit_1", "blocked_exit_2", "blocked_exit_filled",
        "sale_settled",
    )
    if tuple(stage.get("stage_id") for stage in fixture.get("stages", ())) != stage_ids:
        raise ValidationError("fixture stage names or order changed")
    for stage in fixture["stages"]:
        _keys(
            stage,
            {"decision_at", "execution_date", "rows", "signal_date", "stage_id", "target_weights"},
        )
        for row in stage["rows"]:
            _keys(
                row,
                {"open_price", "source_available_at", "symbol"},
                {"action_types", "corporate_actions", "delisted", "suspended", "terminal_action"},
            )
            for action in row.get("corporate_actions", []):
                common = {"action_id", "action_type", "available_at", "effective_at", "ex_date"}
                if action.get("action_type") in {"split", "reverse_split"}:
                    _keys(action, common | {"split_ratio"})
                else:
                    _keys(action, common | {"cash_amount", "record_date", "pay_date"})
            terminal = row.get("terminal_action")
            if terminal is not None:
                _keys(
                    terminal,
                    {"action_type", "available_at", "effective_at", "event_id", "recovery_per_share"},
                )
    if definition.get("research_id") != VALIDATION_ID:
        raise ValidationError("unexpected validation identity")
    if definition.get("fixture_path") != str(FIXTURE.relative_to(ROOT)):
        raise ValidationError("fixture path changed")
    if tuple(definition.get("strict_gates", ())) != GATES:
        raise ValidationError("strict gate names or order changed")
    if definition.get("strategy_candidate_available") is not False:
        raise ValidationError("strategy_candidate_available must remain false")
    if definition.get("strategy_evidence_eligible") is not False:
        raise ValidationError("synthetic validation cannot be strategy evidence")
    if definition.get("strategy_gate_counts") is not None:
        raise ValidationError("strategy gate counts must remain null")
    if definition.get("real_market_data_used") is not False:
        raise ValidationError("real market data is forbidden")
    if definition.get("fixture_sha256") != sha256_file(fixture_path):
        raise ValidationError("fixture SHA-256 does not match the frozen definition")
    if (
        fixture.get("synthetic_only") is not True
        or fixture.get("source_host") != "p4-synthetic.invalid"
        or fixture.get("market") != "synthetic_us"
    ):
        raise ValidationError("fixture must use only the reserved synthetic host")
    if len(fixture.get("stages", ())) != 8 or fixture.get("symbols") != ["SYN_A", "SYN_B"]:
        raise ValidationError("fixture shape changed")
    dates = fixture["calendar_dates"]
    for stage in fixture["stages"]:
        position = dates.index(stage["signal_date"])
        if position + 1 >= len(dates) or dates[position + 1] != stage["execution_date"]:
            raise ValidationError("execution_date must be the next frozen calendar session")


def build_report(
    definition_path: Path,
    fixture_path: Path,
    *,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    definition, fixture = strict_load(definition_path), strict_load(fixture_path)
    _contract(definition, fixture, fixture_path)
    observed = _simulate(fixture)
    replay = _simulate(deepcopy(fixture))
    mutation = deepcopy(fixture)
    mutation["stages"][0]["rows"][0]["source_available_at"] = "2026-01-05T14:29:59+00:00"
    changed = _simulate(mutation)
    golden = definition["golden_ledger"]
    stages = observed["stages"]
    gates = {
        "definition_and_fixture_hashes_exact": True,
        "clean_committed_runtime_identity": runtime["clean_committed"],
        "synthetic_only_boundary": definition["real_market_data_used"] is False,
        "calendar_and_source_cutoffs": len(stages) == 8,
        "initial_allocation_and_costs_exact": stages[0] == golden["stages"][0],
        "split_value_and_once_only": stages[1]["positions"].get("SYN_A") == "1000.000000000",
        "distribution_entitlement_and_pay_date_once_only": (
            stages[1]["pending_cash"] == "500.000000000"
            and stages[3]["pending_cash"] == "0.000000000"
        ),
        "blocked_exit_retries_and_delay_exact": [
            stages[index]["blocked_delay"] for index in (4, 5, 6)
        ] == [1, 2, 2],
        "terminal_value_and_nonrepurchase_exact": (
            "SYN_A" not in stages[4]["positions"]
            and stages[4]["settled_cash"] == "50450.075025000"
        ),
        "settlement_cash_timing_exact": (
            stages[6]["pending_cash"] == "49950.012500000"
            and stages[7]["settled_cash"] == "100400.087525000"
        ),
        "nav_accounting_identity_exact": (
            observed["accounting_residual"] == "0.000000000"
            and observed["final_nav"] == "100400.087525000"
        ),
        "receipt_and_stage_hash_chain_exact": (
            len(observed["stage_hashes"]) == 8
            and len(set(observed["stage_hashes"])) == 8
            and len(observed["receipt_hashes"]) == 8
            and len(set(observed["receipt_hashes"])) == 8
            and all(len(value) == 64 for value in observed["stage_hashes"])
        ),
        "deterministic_replay_and_mutation_sensitivity": (
            observed == replay and observed["stage_hashes"] != changed["stage_hashes"]
        ),
    }
    comparable = {key: value for key, value in observed.items() if key not in {"stage_hashes", "receipt_hashes"}}
    if comparable != golden:
        gates["initial_allocation_and_costs_exact"] = False
    failed = [name for name in GATES if gates.get(name) is not True]
    runner_path = Path(__file__).resolve()
    identities = {
        "definition_sha256": sha256_file(definition_path),
        "fixture_sha256": sha256_file(fixture_path),
        "runner_sha256": sha256_file(runner_path),
        "git_commit": runtime["commit"],
        "git_tree": runtime["tree"],
    }
    run_identity = hashlib.sha256(
        _canonical({"identities": identities, "stage_hashes": observed["stage_hashes"]})
    ).hexdigest()
    return {
        "boundary_result": "PASS_SYNTHETIC_SYSTEM_ONLY" if not failed else "FAIL_CLOSED",
        "evidence_class": "SYNTHETIC_SYSTEM_EVIDENCE_ONLY",
        "gate_results": gates,
        "identities": identities,
        "observed_ledger": observed,
        "phase": "FORMAL_SYSTEM_CONFORMANCE_VALIDATION",
        "research_id": VALIDATION_ID,
        "run_identity_sha256": run_identity,
        "schema_version": "p4-system-validation-result-v1",
        "strategy_candidate_available": False,
        "strategy_evidence_eligible": False,
        "strategy_gate_counts": None,
        "system_gate_counts": {"passed": len(GATES) - len(failed), "total": len(GATES)},
        "system_validation_status": (
            "FORMAL_SYSTEM_VALIDATION_PASS" if not failed else "FORMAL_SYSTEM_VALIDATION_FAIL"
        ),
    }


def _publish(report: dict[str, Any], output: Path) -> None:
    sidecar = output.with_suffix(output.suffix + ".sha256")
    if output != RESULT or output.exists() or sidecar.exists():
        raise ValidationError("result path is fixed and neither result file may already exist")
    parent_existed = output.parent.exists()
    output.parent.mkdir(parents=True, exist_ok=True)
    claim = output.with_suffix(output.suffix + ".claim")
    data = json.dumps(report, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    digest = hashlib.sha256(data).hexdigest()
    sidecar_data = f"{digest}  {output.name}\n".encode()
    claimed, linked = False, []
    temporary: list[Path] = []
    try:
        try:
            claim_descriptor = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise ValidationError("another publisher already owns the result claim") from exc
        claimed = True
        with os.fdopen(claim_descriptor, "wb") as handle:
            handle.write(f"{digest}\n".encode())
            handle.flush()
            os.fsync(handle.fileno())
        if output.exists() or sidecar.exists():
            raise ValidationError("result appeared after the exclusive claim was acquired")
        for final_path, payload in ((output, data), (sidecar, sidecar_data)):
            handle = tempfile.NamedTemporaryFile(
                dir=output.parent,
                prefix=f".{output.name}.",
                suffix=".tmp",
                delete=False,
            )
            temp_path = Path(handle.name)
            temporary.append(temp_path)
            with handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.link(temp_path, final_path)
            linked.append(final_path)
            temp_path.unlink()
            temporary.remove(temp_path)
        claim.unlink()
        claimed = False
    except BaseException:
        for path in reversed(linked):
            path.unlink(missing_ok=True)
        for path in temporary:
            path.unlink(missing_ok=True)
        if claimed:
            try:
                claim.unlink(missing_ok=True)
            except OSError:
                pass
        if not parent_existed:
            try:
                output.parent.rmdir()
            except OSError:
                pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--definition", type=Path, default=DEFINITION)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--output", type=Path, default=RESULT)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.execute and (
        args.definition.resolve() != DEFINITION
        or args.fixture.resolve() != FIXTURE
        or args.output.resolve() != RESULT
    ):
        raise ValidationError("--execute requires the exact frozen definition, fixture, and output")
    runtime = _runtime_identity(ROOT, require_clean=args.execute)
    report = build_report(args.definition.resolve(), args.fixture.resolve(), runtime=runtime)
    if not args.execute:
        semantic_failures = [
            name for name, passed in report["gate_results"].items()
            if name != "clean_committed_runtime_identity" and passed is not True
        ]
        if semantic_failures:
            raise ValidationError(f"precommit semantic gates failed: {semantic_failures}")
        print("PRECOMMIT_READY_AFTER_COMMIT")
        return 0
    if report["system_validation_status"] != "FORMAL_SYSTEM_VALIDATION_PASS":
        raise ValidationError("formal system gates failed")
    _publish(report, args.output.resolve())
    print("FORMAL_SYSTEM_VALIDATION_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
