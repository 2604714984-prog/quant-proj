"""One-use validation runner for the frozen DTS SPY/cash mechanism.

This disposable script is intentionally not a framework. It is bound to one
definition, one adapter, one accepted fiscal packet, and one accepted validation
market packet. The one-use claim is created before any market value is read.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import sys
import tempfile
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


RESEARCH_ID = "US_EQ_DTS_NONDEBT_FISCAL_IMPULSE_YOY_4W_SPY_CASH_V1"
WORKTREE = Path("/home/rongyu/workspace/.wt-us-dts-fiscal-impulse-20260724")
DEFINITION = (
    WORKTREE / "research/definitions/us_eq_dts_nondebt_fiscal_impulse_yoy_4w_spy_cash_v1.json"
)
ADAPTER = WORKTREE / "research/adapters/dts_nondebt_fiscal_impulse.py"
FISCAL = Path(
    "/home/rongyu/workspace/quant-data/staging/"
    "us_eq_dts_nondebt_fiscal_impulse_yoy_4w_v1/"
    "input_qualification_20260724"
)
MARKET = Path(
    "/home/rongyu/workspace/quant-data/staging/"
    "us_eq_dts_nondebt_fiscal_impulse_yoy_4w_v1/"
    "validation_market_input_20260724"
)
DB = Path("/home/rongyu/workspace/quant-data/quant_research.duckdb")
PRIOR_CLAIM = MARKET.parent / "validation_run_20260724.claim.json"
PRIOR_RESULT = MARKET.parent / "validation_result_20260724.json"
CLAIM = MARKET.parent / "validation_run_20260724_attempt2.claim.json"
RESULT = MARKET.parent / "validation_result_20260724_attempt2.json"
NY = ZoneInfo("America/New_York")

EXPECTED = {
    "definition": "4a300d35b7a212c2bdd615c8344ec5530612c7299089a3c523d65105358539cf",
    "adapter": "85e43599fdbb7017d268a889a28cc0f6b94f4f8859d824b872c8c75d86b1030e",
    "fiscal_receipt": "2f28e9a9b5504183cf6b18906b6b1b978bc3a5b33b7e5a6774e4fd170c6ad7aa",
    "fiscal_states": "1fe1e2de16262d448d9024ca1270357ef482dc6d865eb800b235bb1584b54353",
    "fiscal_inventory": "5f95c1e7a7dc2c8ee12906687d474886cc5c21733c4396fa525cfb01e40a656e",
    "market_receipt": "8293423b0168107e98b48bf39afda3e4b2b35f090b9a956bc098572cb5d1cf57",
    "market_rows": "0db17510864b5edd02fdf35da89ecb85bd57e4d3631edd850b4b0b95b4329e6b",
    "calendar_rows": "4f9b7cfe58f7cec14ef0daa6f1f641a435c8f1bec919f847aa7d50e02995186f",
    "actions": "470c7e09496307bb5414b7116defa308789ebfdd83c51a6703afd7854303970a",
    "lifecycle": "a804d76ea3614bface8aebead8886379c6a6b1fb42ed30228c86b21306f656ec",
    "prior_claim": "5a31c190fc15a723291fb49a9cdec6838bd808a6f227a9cbe4febd42c1b117bd",
    "db": "7a0e6a40fe5a1f2fbb7e9d0cecfb7178efb988befe854124e923206c5897b213",
}


class ContractError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-runner-sha256", required=True)
    return parser.parse_args()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        + b"\n"
    )


def read_regular(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ContractError(f"not a regular file: {path}")
        payload = bytearray()
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            payload.extend(block)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ContractError(f"file changed while read: {path}")
        return bytes(payload)
    finally:
        os.close(descriptor)


def exact_bytes(path: Path, expected: str) -> bytes:
    payload = read_regular(path)
    actual = sha256_bytes(payload)
    if actual != expected:
        raise ContractError(f"hash mismatch {path}: {actual} != {expected}")
    return payload


def hash_large(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    digest = hashlib.sha256()
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ContractError(f"not a regular file: {path}")
        while True:
            block = os.read(descriptor, 8 * 1024 * 1024)
            if not block:
                break
            digest.update(block)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ContractError(f"file changed while hashed: {path}")
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def reject_constant(token: str) -> None:
    raise ContractError(f"nonfinite JSON token: {token}")


def pairs(pairs_: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs_:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(payload: bytes) -> object:
    value = json.loads(
        payload,
        object_pairs_hook=pairs,
        parse_constant=reject_constant,
    )
    return value


def strict_jsonl(payload: bytes) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for number, raw in enumerate(payload.splitlines(), 1):
        if not raw.strip():
            raise ContractError(f"blank JSONL row {number}")
        value = strict_json(raw)
        if not isinstance(value, dict):
            raise ContractError(f"JSONL row {number} is not an object")
        rows.append(value)
    return rows


def require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def publish_atomic_no_replace(path: Path, payload: bytes) -> None:
    """Durably publish complete bytes without replacing an existing name."""

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    linked = False
    try:
        os.fchmod(descriptor, 0o600)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise ContractError(f"short write while publishing {path}")
            offset += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.link(temporary, path, follow_symlinks=False)
        linked = True
        os.unlink(temporary)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists() or temporary.is_symlink():
            os.unlink(temporary)
        if linked and not path.exists():
            raise ContractError(f"atomic publication disappeared: {path}")


def atomic_claim(runner_sha256: str) -> None:
    if CLAIM.exists() or CLAIM.is_symlink() or RESULT.exists() or RESULT.is_symlink():
        raise ContractError("validation identity was already claimed or completed")
    payload = canonical(
        {
            "schema_version": "dts-validation-one-use-claim-v1",
            "research_id": RESEARCH_ID,
            "attempt": 2,
            "recovery_of_claim_sha256": EXPECTED["prior_claim"],
            "recovery_reason": ("ATTEMPT_1_BLOCKED_BEFORE_ADAPTER_IMPORT_MISSING_DUCKDB_RUNTIME"),
            "claimed_at_utc": datetime.now(timezone.utc).isoformat(),
            "runner_sha256": runner_sha256,
            "definition_sha256": EXPECTED["definition"],
            "adapter_sha256": EXPECTED["adapter"],
            "fiscal_receipt_sha256": EXPECTED["fiscal_receipt"],
            "fiscal_states_sha256": EXPECTED["fiscal_states"],
            "market_receipt_sha256": EXPECTED["market_receipt"],
            "market_rows_file_sha256": EXPECTED["market_rows"],
            "secondary_opened": False,
            "rerun": False,
            "strategy_candidate_available": False,
        }
    )
    publish_atomic_no_replace(CLAIM, payload)


def verify_prior_attempt() -> None:
    exact_bytes(PRIOR_CLAIM, EXPECTED["prior_claim"])
    if PRIOR_RESULT.exists() or PRIOR_RESULT.is_symlink():
        raise ContractError("attempt 1 unexpectedly produced a result")


def load_module():
    sys.path.insert(0, str(WORKTREE / "src"))
    name = "_dts_validation_adapter_exact"
    spec = importlib.util.spec_from_file_location(name, ADAPTER)
    if spec is None or spec.loader is None:
        raise ContractError("cannot load adapter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_report_dates(inventory: dict[str, object]) -> tuple[date, ...]:
    api = require_object(inventory.get("api"), "inventory.api")
    observed_hashes = {
        key: require_object(value, f"inventory.api.{key}").get("sha256")
        for key, value in api.items()
    }
    dates: set[date] = set()
    for path in sorted((FISCAL / "raw_api").glob("*.json")):
        key = path.stem
        expected = observed_hashes.get(key)
        if not isinstance(expected, str):
            raise ContractError(f"unbound fiscal API file: {path}")
        payload = exact_bytes(path, expected)
        root = require_object(strict_json(payload), f"api.{key}")
        data = root.get("data")
        if not isinstance(data, list):
            raise ContractError(f"api.{key}.data must be a list")
        for row in data:
            item = require_object(row, f"api.{key}.row")
            dates.add(date.fromisoformat(str(item["record_date"])))
    ordered = tuple(sorted(dates))
    if len(ordered) != 1630:
        raise ContractError(f"expected 1630 report dates, got {len(ordered)}")
    return ordered


def monthly_states(module, fiscal_rows: list[dict[str, object]], reports: tuple[date, ...]):
    report_index = {value: index for index, value in enumerate(reports)}
    states = []
    for row in fiscal_rows:
        anchor = date.fromisoformat(str(row["anchor_report_date"]))
        index = report_index.get(anchor)
        if index is None or index + 1 >= len(reports):
            raise ContractError("state anchor has no following observed report")
        available_at = datetime.combine(reports[index + 1], time(16), tzinfo=NY)
        states.append(
            module.MonthlyState(
                date.fromisoformat(str(row["month_start"])),
                str(row["state"]),
                datetime.fromisoformat(str(row["decision_at"])),
                available_at,
                sha256_bytes(canonical(row)),
            )
        )
    return tuple(states)


def market_sessions(module, rows: list[dict[str, object]]):
    sessions = tuple(
        module.MarketSession(
            date.fromisoformat(str(row["session_date"])),
            float(row["raw_open"]),
            float(row["raw_close"]),
        )
        for row in rows
    )
    if (
        len(sessions) != 589
        or sessions[0].session_date != date(2021, 1, 29)
        or sessions[-1].session_date != date(2023, 6, 1)
    ):
        raise ContractError("validation market coverage is not exact")
    return sessions


def distributions(module, rows: list[dict[str, object]]):
    result = []
    for row in rows:
        if row.get("action_type") != "cash_distribution":
            raise ContractError("unexpected validation corporate action")
        result.append(
            module.Distribution(
                str(row["symbol"]),
                str(row["event_id"]),
                date.fromisoformat(str(row["ex_date"])),
                date.fromisoformat(str(row["pay_date"])),
                float(row["amount_per_share"]),
            )
        )
    if len(result) != 9:
        raise ContractError("expected exactly nine validation distributions")
    return tuple(result)


def finite(value: object, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ContractError(f"{label} must be finite")
    return float(value)


def main() -> int:
    args = parse_args()
    runner_sha = sha256_bytes(read_regular(Path(__file__)))
    if args.expected_runner_sha256 != runner_sha:
        raise ContractError("runner hash mismatch")
    exact_bytes(DEFINITION, EXPECTED["definition"])
    exact_bytes(ADAPTER, EXPECTED["adapter"])
    verify_prior_attempt()
    try:
        import duckdb
    except ImportError as exc:
        raise ContractError("the frozen runtime requires duckdb") from exc
    if duckdb.__version__ != "1.5.4":
        raise ContractError("duckdb runtime version drift")
    module = load_module()
    verify_prior_attempt()
    atomic_claim(runner_sha)

    db_before = hash_large(DB)
    if db_before != EXPECTED["db"]:
        raise ContractError("central DB identity drift")

    definition = require_object(
        strict_json(exact_bytes(DEFINITION, EXPECTED["definition"])),
        "definition",
    )
    if (
        definition.get("research_id") != RESEARCH_ID
        or require_object(definition.get("boundaries"), "definition.boundaries").get(
            "strategy_candidate_available"
        )
        is not False
    ):
        raise ContractError("definition boundary drift")

    fiscal_receipt = require_object(
        strict_json(exact_bytes(FISCAL / "receipt.json", EXPECTED["fiscal_receipt"])),
        "fiscal receipt",
    )
    fiscal_states_root = require_object(
        strict_json(exact_bytes(FISCAL / "monthly_states.json", EXPECTED["fiscal_states"])),
        "fiscal states",
    )
    inventory = require_object(
        strict_json(exact_bytes(FISCAL / "raw_inventory.json", EXPECTED["fiscal_inventory"])),
        "fiscal inventory",
    )
    if (
        fiscal_receipt.get("status") != "INPUT_QUALIFIED_FOR_ONE_EXPLORATORY_VALIDATION"
        or fiscal_states_root.get("research_id") != RESEARCH_ID
    ):
        raise ContractError("fiscal input is not accepted for validation")
    fiscal_rows = fiscal_states_root.get("validation")
    if not isinstance(fiscal_rows, list) or len(fiscal_rows) != 28:
        raise ContractError("validation fiscal state count is not frozen")

    market_receipt = require_object(
        strict_json(exact_bytes(MARKET / "receipt.json", EXPECTED["market_receipt"])),
        "market receipt",
    )
    market_rows = strict_jsonl(
        exact_bytes(MARKET / "validation_market.jsonl", EXPECTED["market_rows"])
    )
    calendar_rows = strict_jsonl(
        exact_bytes(MARKET / "calendar_identity.jsonl", EXPECTED["calendar_rows"])
    )
    action_rows = strict_jsonl(exact_bytes(MARKET / "corporate_actions.jsonl", EXPECTED["actions"]))
    lifecycle_rows = strict_jsonl(
        exact_bytes(MARKET / "lifecycle_identity.jsonl", EXPECTED["lifecycle"])
    )
    if (
        market_receipt.get("status") != "VALIDATION_MARKET_INPUT_MATERIALIZED_RETROSPECTIVE_ONLY"
        or market_receipt.get("classification") != "RETROSPECTIVE_ONLY"
        or require_object(market_receipt.get("boundaries"), "market boundaries").get(
            "secondary_fiscal_rows_used"
        )
        != 0
        or len(calendar_rows) != 589
        or len(lifecycle_rows) != 4
    ):
        raise ContractError("validation market receipt boundary drift")
    market_dates = tuple(str(row["session_date"]) for row in market_rows)
    calendar_dates = tuple(str(row["session_date"]) for row in calendar_rows)
    if market_dates != calendar_dates:
        raise ContractError("market/calendar dates differ")

    reports = source_report_dates(inventory)
    states = monthly_states(module, fiscal_rows, reports)
    sessions = market_sessions(module, market_rows)
    action_objects = distributions(module, action_rows)
    state_digest = module.fiscal_states_sha256(states)
    market_digest = module.market_rows_sha256(sessions)
    calendar_digest = module.calendar_sha256(sessions)
    identity = module.SegmentInputIdentity(
        "validation",
        EXPECTED["fiscal_receipt"],
        state_digest,
        EXPECTED["market_receipt"],
        market_digest,
        calendar_digest,
        EXPECTED["definition"],
        EXPECTED["adapter"],
    )

    decision = module.run_validation(
        states,
        sessions,
        terminal_month=date(2023, 6, 1),
        input_identity=identity,
        distributions=action_objects,
        splits=(),
    )
    gates = {name: passed for name, passed in decision.gates}
    if tuple(gates) != module.GATE_NAMES or any(
        type(value) is not bool for value in gates.values()
    ):
        raise ContractError("validation gates are malformed")

    db_after = hash_large(DB)
    if db_after != db_before:
        raise ContractError("central DB changed during validation")
    result = {
        "schema_version": "dts-validation-result-v1",
        "research_id": RESEARCH_ID,
        "attempt": 2,
        "recovery_of_claim_sha256": EXPECTED["prior_claim"],
        "attempt_1_result_opened": False,
        "status": (
            "VALIDATION_PASS_SECONDARY_ELIGIBLE"
            if decision.all_gates_pass
            else "VALIDATION_FAIL_TERMINAL"
        ),
        "classification": "RETROSPECTIVE_SECONDARY_REVISION_LIMITED",
        "code": {
            "runner_sha256": runner_sha,
            "definition_sha256": EXPECTED["definition"],
            "adapter_sha256": EXPECTED["adapter"],
            "python_executable": sys.executable,
            "duckdb_version": duckdb.__version__,
        },
        "inputs": {
            "fiscal_receipt_sha256": EXPECTED["fiscal_receipt"],
            "fiscal_states_file_sha256": EXPECTED["fiscal_states"],
            "fiscal_state_rows_sha256": state_digest,
            "market_receipt_sha256": EXPECTED["market_receipt"],
            "market_rows_file_sha256": EXPECTED["market_rows"],
            "market_rows_sha256": market_digest,
            "calendar_rows_sha256": calendar_digest,
        },
        "support": {
            "intervals": decision.observed_intervals,
            "spy_intervals": decision.spy_intervals,
            "cash_intervals": decision.cash_intervals,
            "spy_to_cash_transitions": decision.spy_to_cash_transitions,
            "cash_to_spy_transitions": decision.cash_to_spy_transitions,
        },
        "performance": {
            "strategy_terminal_wealth": finite(
                decision.strategy.terminal_wealth, "strategy terminal wealth"
            ),
            "fifty_fifty_terminal_wealth": finite(
                decision.fifty_fifty.terminal_wealth, "comparator terminal wealth"
            ),
            "paired_mean_active_return": finite(
                decision.paired_mean_active_return, "paired mean active return"
            ),
            "strategy_maximum_drawdown": finite(
                decision.strategy.maximum_drawdown, "strategy maximum drawdown"
            ),
            "spy_buyhold_maximum_drawdown": finite(
                decision.spy_buyhold.maximum_drawdown, "SPY maximum drawdown"
            ),
            "strategy_trade_count": len(decision.strategy.trades),
        },
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "all_gates_pass": decision.all_gates_pass,
        "central_database": {
            "sha256_before": db_before,
            "sha256_after": db_after,
            "unchanged": True,
            "write_performed": False,
        },
        "boundaries": {
            "secondary_market_input_opened": False,
            "secondary_result_opened": False,
            "rerun": False,
            "strategy_candidate_available": False,
            "shadow": False,
            "paper": False,
            "broker": False,
            "live": False,
        },
    }
    payload = (
        json.dumps(
            result,
            indent=2,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
        ).encode("ascii")
        + b"\n"
    )
    publish_atomic_no_replace(RESULT, payload)
    print(
        json.dumps(
            {
                "status": result["status"],
                "gate_pass_count": result["gate_pass_count"],
                "result_sha256": sha256_bytes(payload),
                "secondary_opened": False,
                "db_unchanged": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
