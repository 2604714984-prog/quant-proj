"""One-use secondary runner for the frozen DTS SPY/cash mechanism.

This disposable branch-only script reconstructs the exact accepted validation
decision in-process before it claims or reads the secondary market packet.  It
is intentionally not a reusable runner framework.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Any


RESEARCH_ID = "US_EQ_DTS_NONDEBT_FISCAL_IMPULSE_YOY_4W_SPY_CASH_V1"
WORKTREE = Path("/home/rongyu/workspace/.wt-us-dts-fiscal-impulse-20260724")
DEFINITION = (
    WORKTREE
    / "research/definitions/us_eq_dts_nondebt_fiscal_impulse_yoy_4w_spy_cash_v1.json"
)
ADAPTER = WORKTREE / "research/adapters/dts_nondebt_fiscal_impulse.py"
VALIDATION_RUNNER = WORKTREE / "research/runners/run_dts_validation_once.py"
ROOT = Path(
    "/home/rongyu/workspace/quant-data/staging/"
    "us_eq_dts_nondebt_fiscal_impulse_yoy_4w_v1"
)
FISCAL = ROOT / "input_qualification_20260724"
VALIDATION_MARKET = ROOT / "validation_market_input_20260724"
SECONDARY_MARKET = ROOT / "secondary_market_input_20260724_v2"
VALIDATION_CLAIM = ROOT / "validation_run_20260724_attempt2.claim.json"
VALIDATION_RESULT = ROOT / "validation_result_20260724_attempt2.json"
CLAIM = ROOT / "secondary_run_20260724.claim.json"
RESULT = ROOT / "secondary_result_20260724.json"
DB = Path("/home/rongyu/workspace/quant-data/quant_research.duckdb")

EXPECTED = {
    "definition": "4a300d35b7a212c2bdd615c8344ec5530612c7299089a3c523d65105358539cf",
    "adapter": "85e43599fdbb7017d268a889a28cc0f6b94f4f8859d824b872c8c75d86b1030e",
    "validation_runner": "45cbf3cf26c4dfeca419d1e6956c4b5743fabe1c41890b814fe68867358080a8",
    "validation_claim": "0a35ed4413ed9c335f55eff0b38e408e6c100ddd58fb149c1d67e73cf5fbd36f",
    "validation_result": "6e6cf8f990e33ded92fbd7981baa5518bc6c0b20d99c5eef8ea67091345bf640",
    "fiscal_receipt": "2f28e9a9b5504183cf6b18906b6b1b978bc3a5b33b7e5a6774e4fd170c6ad7aa",
    "fiscal_states": "1fe1e2de16262d448d9024ca1270357ef482dc6d865eb800b235bb1584b54353",
    "fiscal_inventory": "5f95c1e7a7dc2c8ee12906687d474886cc5c21733c4396fa525cfb01e40a656e",
    "validation_market_receipt": (
        "8293423b0168107e98b48bf39afda3e4b2b35f090b9a956bc098572cb5d1cf57"
    ),
    "validation_market_file": (
        "0db17510864b5edd02fdf35da89ecb85bd57e4d3631edd850b4b0b95b4329e6b"
    ),
    "validation_calendar_file": (
        "4f9b7cfe58f7cec14ef0daa6f1f641a435c8f1bec919f847aa7d50e02995186f"
    ),
    "validation_actions_file": (
        "470c7e09496307bb5414b7116defa308789ebfdd83c51a6703afd7854303970a"
    ),
    "validation_lifecycle_file": (
        "a804d76ea3614bface8aebead8886379c6a6b1fb42ed30228c86b21306f656ec"
    ),
    "validation_state_rows": (
        "3a1fc93bb369390ba251063c099fffc89c835e868a928345ca59282c5c79b237"
    ),
    "validation_market_rows": (
        "076e93c47e96759f957af3b415cff8c86520e1040ff6dac7ce1e9e6248a49549"
    ),
    "validation_calendar_rows": (
        "844e6eb001679cd96660cf86053e2e3d4991c4982b9083f08daf4ffb82ca6d84"
    ),
    "db": "7a0e6a40fe5a1f2fbb7e9d0cecfb7178efb988befe854124e923206c5897b213",
}

EXPECTED_SECONDARY = {
    "receipt": "0d0dee7c569a013eafb3763d0222ca241b6dc37e53319b4428f1edfb95f8b1ee",
    "market": "b0711263e567034a2ff03879e408cf959e2db4e40374c54a56b2e11577ade1de",
    "calendar": "688e35b2a8c18756b272a385b9e0f423a6075bc22915e4fab9bee3ccfb36f57f",
    "actions": "f911b51cdef4b5bc38caf5f7296f095904143b550df7a388e93f7ff6f91b2c80",
    "lifecycle": "c09a7c06e3c20948ac6bc249193ba76c2c7ebcabcd5f74fb5463a62482c2850b",
    "sha256sums": "fa0071d70ceaf5ec1f344058d008294aa1c717ee208ccd4d0158e0b4561d8061",
}

SOURCE_ROLES = {
    "calendar": "XNYS_SESSION_IDENTITY_ONLY",
    "tiingo_spy_prices": "UNADJUSTED_RAW_OPEN_CLOSE_ONLY",
    "ssga_distributions": "SPY_CASH_DISTRIBUTIONS_ONLY",
    "nport_2023_lifecycle": "SPY_2023_PRIMARY_DOCUMENT_LIFECYCLE_IDENTITY_ONLY",
    "sec_submissions": "SPY_2024_2026_FILING_INDEX_IDENTITY_ONLY",
    "sec_primary_documents_2024_2026": (
        "SPY_2024_2026_PRIMARY_DOCUMENT_LIFECYCLE_IDENTITY_ONLY"
    ),
    "splithistory_page": (
        "ZERO_SPLIT_STATEMENT_SECONDARY_RETROSPECTIVE_CORROBORATION_ONLY"
    ),
    "yahoo_chart_split_events": (
        "ZERO_SPLIT_EVENT_KEYS_SECONDARY_CORROBORATION_ONLY_"
        "PRICE_FIELDS_DECODED_BUT_NOT_SELECTED_USED_OUTPUT_OR_FUSED"
    ),
    "automatic_source_fusion": False,
}

EXPECTED_DISTRIBUTION_DATES = {
    "2023-09-15",
    "2023-12-15",
    "2024-03-15",
    "2024-06-21",
    "2024-09-20",
    "2024-12-20",
    "2025-03-21",
    "2025-06-20",
    "2025-09-19",
    "2025-12-19",
    "2026-03-20",
}

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class ContractError(RuntimeError):
    """Raised whenever a frozen input or one-use boundary drifts."""


@dataclass(frozen=True)
class SecondaryHashes:
    receipt: str
    market: str
    calendar: str
    actions: str
    lifecycle: str
    sha256sums: str


@dataclass(frozen=True)
class ValidationContext:
    module: Any
    decision: Any
    accepted_result: dict[str, object]
    fiscal_states_root: dict[str, object]
    reports: tuple[date, ...]


@dataclass(frozen=True)
class SecondaryPacket:
    receipt: dict[str, object]
    states: tuple[Any, ...]
    sessions: tuple[Any, ...]
    distributions: tuple[Any, ...]
    input_identity: Any
    source_hashes: dict[str, str]


def sha256_value(value: str) -> str:
    if not _SHA256_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("expected a lowercase 64-character SHA256")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-runner-sha256", required=True, type=sha256_value)
    parser.add_argument("--secondary-receipt-sha256", required=True, type=sha256_value)
    parser.add_argument("--secondary-market-sha256", required=True, type=sha256_value)
    parser.add_argument("--secondary-calendar-sha256", required=True, type=sha256_value)
    parser.add_argument("--secondary-actions-sha256", required=True, type=sha256_value)
    parser.add_argument("--secondary-lifecycle-sha256", required=True, type=sha256_value)
    parser.add_argument("--secondary-sha256sums-sha256", required=True, type=sha256_value)
    return parser.parse_args(argv)


def secondary_hashes(args: argparse.Namespace) -> SecondaryHashes:
    hashes = SecondaryHashes(
        args.secondary_receipt_sha256,
        args.secondary_market_sha256,
        args.secondary_calendar_sha256,
        args.secondary_actions_sha256,
        args.secondary_lifecycle_sha256,
        args.secondary_sha256sums_sha256,
    )
    if hashes != SecondaryHashes(**EXPECTED_SECONDARY):
        raise ContractError("secondary CLI hash binding drift")
    return hashes


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


def read_regular(path: Path, *, single_link: bool = False) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ContractError(f"not a regular file: {path}")
        if single_link and before.st_nlink != 1:
            raise ContractError(f"hard-linked input is forbidden: {path}")
        payload = bytearray()
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            payload.extend(block)
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_nlink,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_nlink,
        )
        if identity_before != identity_after:
            raise ContractError(f"file changed while read: {path}")
        return bytes(payload)
    finally:
        os.close(descriptor)


def exact_bytes(path: Path, expected: str, *, single_link: bool = False) -> bytes:
    payload = read_regular(path, single_link=single_link)
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
    return json.loads(
        payload,
        object_pairs_hook=pairs,
        parse_constant=reject_constant,
    )


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


def finite(value: object, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ContractError(f"{label} must be finite")
    return float(value)


def publish_atomic_no_replace(path: Path, payload: bytes) -> None:
    """Durably publish complete bytes, never replacing or linking an identity."""

    if os.path.lexists(path):
        raise ContractError(f"output already exists: {path}")
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
        published = os.lstat(path)
        if not stat.S_ISREG(published.st_mode) or published.st_nlink != 1:
            raise ContractError(f"published output is not a single-link file: {path}")
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if os.path.lexists(temporary):
            os.unlink(temporary)
        if linked and not os.path.lexists(path):
            raise ContractError(f"atomic publication disappeared: {path}")


def load_exact_module(path: Path, expected_sha256: str, name: str):
    payload = exact_bytes(path, expected_sha256)
    specification = importlib.util.spec_from_loader(
        name,
        loader=None,
        origin=str(path),
    )
    if specification is None:
        raise ContractError(f"cannot load exact module: {path}")
    module = importlib.util.module_from_spec(specification)
    module.__file__ = str(path)
    sys.modules[name] = module
    try:
        code = compile(payload, str(path), "exec", dont_inherit=True)
        exec(code, module.__dict__)
        # The module ran only captured accepted bytes.  A second descriptor-
        # bound check additionally makes any concurrent path replacement a
        # pre-claim terminal failure rather than an ignored filesystem event.
        exact_bytes(path, expected_sha256)
        return module
    except BaseException:
        sys.modules.pop(name, None)
        raise


def validate_validation_claim(claim: dict[str, object]) -> None:
    required = {
        "schema_version": "dts-validation-one-use-claim-v1",
        "research_id": RESEARCH_ID,
        "attempt": 2,
        "runner_sha256": EXPECTED["validation_runner"],
        "definition_sha256": EXPECTED["definition"],
        "adapter_sha256": EXPECTED["adapter"],
        "fiscal_receipt_sha256": EXPECTED["fiscal_receipt"],
        "fiscal_states_sha256": EXPECTED["fiscal_states"],
        "market_receipt_sha256": EXPECTED["validation_market_receipt"],
        "market_rows_file_sha256": EXPECTED["validation_market_file"],
        "secondary_opened": False,
        "rerun": False,
        "strategy_candidate_available": False,
    }
    if any(claim.get(key) != value for key, value in required.items()):
        raise ContractError("accepted validation claim semantic drift")
    if set(claim) != {
        *required,
        "claimed_at_utc",
        "recovery_of_claim_sha256",
        "recovery_reason",
    }:
        raise ContractError("accepted validation claim field drift")


def decision_aggregate(decision: Any) -> dict[str, object]:
    gates = {name: passed for name, passed in decision.gates}
    return {
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
    }


def validate_accepted_validation(
    module: Any,
    claim: dict[str, object],
    result: dict[str, object],
    decision: Any,
) -> None:
    validate_validation_claim(claim)
    required_result = {
        "schema_version": "dts-validation-result-v1",
        "research_id": RESEARCH_ID,
        "attempt": 2,
        "status": "VALIDATION_PASS_SECONDARY_ELIGIBLE",
        "classification": "RETROSPECTIVE_SECONDARY_REVISION_LIMITED",
        "gate_pass_count": 3,
        "all_gates_pass": True,
    }
    if any(result.get(key) != value for key, value in required_result.items()):
        raise ContractError("accepted validation result semantic drift")
    code = require_object(result.get("code"), "validation result code")
    if (
        code.get("runner_sha256") != EXPECTED["validation_runner"]
        or code.get("definition_sha256") != EXPECTED["definition"]
        or code.get("adapter_sha256") != EXPECTED["adapter"]
        or code.get("duckdb_version") != "1.5.4"
    ):
        raise ContractError("accepted validation code identity drift")
    inputs = require_object(result.get("inputs"), "validation result inputs")
    expected_inputs = {
        "fiscal_receipt_sha256": EXPECTED["fiscal_receipt"],
        "fiscal_states_file_sha256": EXPECTED["fiscal_states"],
        "fiscal_state_rows_sha256": EXPECTED["validation_state_rows"],
        "market_receipt_sha256": EXPECTED["validation_market_receipt"],
        "market_rows_file_sha256": EXPECTED["validation_market_file"],
        "market_rows_sha256": EXPECTED["validation_market_rows"],
        "calendar_rows_sha256": EXPECTED["validation_calendar_rows"],
    }
    if inputs != expected_inputs:
        raise ContractError("accepted validation input identity drift")
    database = require_object(result.get("central_database"), "validation database")
    if database != {
        "sha256_before": EXPECTED["db"],
        "sha256_after": EXPECTED["db"],
        "unchanged": True,
        "write_performed": False,
    }:
        raise ContractError("accepted validation database boundary drift")
    boundaries = require_object(result.get("boundaries"), "validation boundaries")
    expected_boundaries = {
        "secondary_market_input_opened",
        "secondary_result_opened",
        "rerun",
        "strategy_candidate_available",
        "shadow",
        "paper",
        "broker",
        "live",
    }
    if set(boundaries) != expected_boundaries or any(
        value is not False for value in boundaries.values()
    ):
        raise ContractError("accepted validation boundary drift")

    aggregate = decision_aggregate(decision)
    if tuple(aggregate["gates"]) != module.GATE_NAMES:
        raise ContractError("reconstructed validation gate order drift")
    if (
        result.get("support") != aggregate["support"]
        or result.get("performance") != aggregate["performance"]
        or result.get("gates") != aggregate["gates"]
        or result.get("gate_pass_count") != aggregate["gate_pass_count"]
        or result.get("all_gates_pass") is not aggregate["all_gates_pass"]
    ):
        raise ContractError("accepted validation aggregate does not reproduce exactly")


def reconstruct_accepted_validation() -> ValidationContext:
    validation_runner = load_exact_module(
        VALIDATION_RUNNER,
        EXPECTED["validation_runner"],
        "_dts_secondary_validation_runner_exact",
    )
    sys.path.insert(0, str(WORKTREE / "src"))
    module = load_exact_module(
        ADAPTER,
        EXPECTED["adapter"],
        "_dts_secondary_adapter_exact",
    )
    claim = require_object(
        strict_json(exact_bytes(VALIDATION_CLAIM, EXPECTED["validation_claim"])),
        "validation claim",
    )
    accepted_result = require_object(
        strict_json(exact_bytes(VALIDATION_RESULT, EXPECTED["validation_result"])),
        "validation result",
    )
    fiscal_receipt = require_object(
        strict_json(exact_bytes(FISCAL / "receipt.json", EXPECTED["fiscal_receipt"])),
        "fiscal receipt",
    )
    fiscal_states_root = require_object(
        strict_json(
            exact_bytes(FISCAL / "monthly_states.json", EXPECTED["fiscal_states"])
        ),
        "fiscal states",
    )
    inventory = require_object(
        strict_json(
            exact_bytes(FISCAL / "raw_inventory.json", EXPECTED["fiscal_inventory"])
        ),
        "fiscal inventory",
    )
    if (
        fiscal_receipt.get("status")
        != "INPUT_QUALIFIED_FOR_ONE_EXPLORATORY_VALIDATION"
        or fiscal_states_root.get("research_id") != RESEARCH_ID
    ):
        raise ContractError("accepted fiscal packet drift")
    validation_rows = fiscal_states_root.get("validation")
    if not isinstance(validation_rows, list) or len(validation_rows) != 28:
        raise ContractError("accepted validation fiscal state count drift")

    market_receipt = require_object(
        strict_json(
            exact_bytes(
                VALIDATION_MARKET / "receipt.json",
                EXPECTED["validation_market_receipt"],
            )
        ),
        "validation market receipt",
    )
    market_rows = validation_runner.strict_jsonl(
        validation_runner.exact_bytes(
            VALIDATION_MARKET / "validation_market.jsonl",
            EXPECTED["validation_market_file"],
        )
    )
    calendar_rows = validation_runner.strict_jsonl(
        validation_runner.exact_bytes(
            VALIDATION_MARKET / "calendar_identity.jsonl",
            EXPECTED["validation_calendar_file"],
        )
    )
    action_rows = validation_runner.strict_jsonl(
        validation_runner.exact_bytes(
            VALIDATION_MARKET / "corporate_actions.jsonl",
            EXPECTED["validation_actions_file"],
        )
    )
    lifecycle_rows = validation_runner.strict_jsonl(
        validation_runner.exact_bytes(
            VALIDATION_MARKET / "lifecycle_identity.jsonl",
            EXPECTED["validation_lifecycle_file"],
        )
    )
    if (
        market_receipt.get("status")
        != "VALIDATION_MARKET_INPUT_MATERIALIZED_RETROSPECTIVE_ONLY"
        or market_receipt.get("classification") != "RETROSPECTIVE_ONLY"
        or len(market_rows) != 589
        or len(calendar_rows) != 589
        or len(action_rows) != 9
        or len(lifecycle_rows) != 4
    ):
        raise ContractError("accepted validation market packet drift")
    if tuple(row.get("session_date") for row in market_rows) != tuple(
        row.get("session_date") for row in calendar_rows
    ):
        raise ContractError("accepted validation market/calendar dates differ")

    reports = validation_runner.source_report_dates(inventory)
    states = validation_runner.monthly_states(module, validation_rows, reports)
    sessions = validation_runner.market_sessions(module, market_rows)
    distributions = validation_runner.distributions(module, action_rows)
    state_digest = module.fiscal_states_sha256(states)
    market_digest = module.market_rows_sha256(sessions)
    calendar_digest = module.calendar_sha256(sessions)
    if (
        state_digest != EXPECTED["validation_state_rows"]
        or market_digest != EXPECTED["validation_market_rows"]
        or calendar_digest != EXPECTED["validation_calendar_rows"]
    ):
        raise ContractError("reconstructed validation input digest drift")
    identity = module.SegmentInputIdentity(
        "validation",
        EXPECTED["fiscal_receipt"],
        state_digest,
        EXPECTED["validation_market_receipt"],
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
        distributions=distributions,
        splits=(),
    )
    validate_accepted_validation(module, claim, accepted_result, decision)
    return ValidationContext(
        module,
        decision,
        accepted_result,
        fiscal_states_root,
        reports,
    )


def reverify_validation_artifacts() -> None:
    exact_bytes(VALIDATION_CLAIM, EXPECTED["validation_claim"])
    exact_bytes(VALIDATION_RESULT, EXPECTED["validation_result"])


def atomic_claim(runner_sha256: str, hashes: SecondaryHashes) -> None:
    if os.path.lexists(CLAIM) or os.path.lexists(RESULT):
        raise ContractError("secondary identity was already claimed or completed")
    payload = canonical(
        {
            "schema_version": "dts-secondary-one-use-claim-v1",
            "research_id": RESEARCH_ID,
            "claimed_at_utc": datetime.now(timezone.utc).isoformat(),
            "runner_sha256": runner_sha256,
            "definition_sha256": EXPECTED["definition"],
            "adapter_sha256": EXPECTED["adapter"],
            "validation_runner_sha256": EXPECTED["validation_runner"],
            "validation_claim_sha256": EXPECTED["validation_claim"],
            "validation_result_sha256": EXPECTED["validation_result"],
            "fiscal_receipt_sha256": EXPECTED["fiscal_receipt"],
            "fiscal_states_sha256": EXPECTED["fiscal_states"],
            "secondary_receipt_sha256": hashes.receipt,
            "secondary_market_sha256": hashes.market,
            "secondary_calendar_sha256": hashes.calendar,
            "secondary_actions_sha256": hashes.actions,
            "secondary_lifecycle_sha256": hashes.lifecycle,
            "secondary_sha256sums_sha256": hashes.sha256sums,
            "rerun": False,
            "strategy_candidate_available": False,
            "shadow": False,
            "paper": False,
            "broker": False,
            "live": False,
        }
    )
    publish_atomic_no_replace(CLAIM, payload)


def parse_sha256sums(payload: bytes) -> dict[str, str]:
    output: dict[str, str] = {}
    for number, raw in enumerate(payload.decode("ascii").splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", raw)
        if match is None:
            raise ContractError(f"malformed SHA256SUMS line {number}")
        digest, name = match.groups()
        if name in output:
            raise ContractError(f"duplicate SHA256SUMS name: {name}")
        output[name] = digest
    return output


def require_secondary_receipt(
    receipt: dict[str, object],
    hashes: SecondaryHashes,
) -> None:
    if (
        receipt.get("schema_version") != "dts-secondary-market-input-receipt-v1"
        or receipt.get("research_id") != RESEARCH_ID
        or receipt.get("status")
        != "SECONDARY_MARKET_INPUT_MATERIALIZED_RETROSPECTIVE_ONLY"
        or receipt.get("classification")
        != "RETROSPECTIVE_SECONDARY_REVISION_LIMITED"
        or receipt.get("source_roles") != SOURCE_ROLES
    ):
        raise ContractError("secondary receipt identity or source-role drift")
    coverage = require_object(receipt.get("coverage"), "secondary coverage")
    if coverage != {
        "first_session": "2023-07-31",
        "last_session": "2026-06-01",
        "calendar_session_count": 712,
        "market_row_count": 712,
        "distribution_row_count": 11,
        "split_row_count": 0,
        "lifecycle_row_count": 4,
    }:
        raise ContractError("secondary coverage drift")
    fiscal = require_object(receipt.get("fiscal_binding"), "secondary fiscal binding")
    if (
        fiscal.get("fiscal_receipt_sha256") != EXPECTED["fiscal_receipt"]
        or fiscal.get("fiscal_states_sha256") != EXPECTED["fiscal_states"]
        or fiscal.get("secondary_row_count") != 34
        or fiscal.get("terminal_month_start") != "2026-06-01"
        or fiscal.get("validation_rows_used") != 0
        or fiscal.get("accepted_validation_result_sha256")
        != EXPECTED["validation_result"]
        or not _SHA256_RE.fullmatch(str(fiscal.get("secondary_schedule_sha256", "")))
    ):
        raise ContractError("secondary fiscal binding drift")
    boundaries = require_object(receipt.get("boundaries"), "secondary boundaries")
    required_false = {
        "validation_market_values_opened",
        "return_computed",
        "nav_computed",
        "strategy_computed",
        "central_database_write_performed",
        "strategy_candidate_available",
        "yahoo_price_fields_selected_used_output_or_fused",
    }
    if (
        boundaries.get("secondary_fiscal_rows_used") != 34
        or boundaries.get("yahoo_price_fields_decoded_by_strict_json_parser") is not True
        or any(boundaries.get(name) is not False for name in required_false)
    ):
        raise ContractError("secondary materialization boundary drift")
    database = require_object(receipt.get("database"), "secondary database")
    if (
        database.get("sha256_before") != EXPECTED["db"]
        or database.get("sha256_after") != EXPECTED["db"]
        or database.get("unchanged") is not True
        or database.get("write_performed") is not False
    ):
        raise ContractError("secondary materialization database drift")
    split = require_object(receipt.get("split_evidence"), "split evidence")
    if (
        split.get("classification")
        != "ZERO_EVENTS_DUAL_SECONDARY_CORROBORATED_RETROSPECTIVE_ONLY"
        or split.get("accepted_split_rows") != 0
        or split.get("automatic_row_fusion") is not False
    ):
        raise ContractError("secondary split evidence drift")
    split_history = require_object(split.get("splithistory_page"), "SplitHistory evidence")
    if (
        not _SHA256_RE.fullmatch(str(split_history.get("page_sha256", "")))
        or not _SHA256_RE.fullmatch(
            str(split_history.get("fetch_receipt_sha256", ""))
        )
        or split_history.get("url") != "https://www.splithistory.com/spy/"
        or split_history.get("http_status") != 200
        or split_history.get("response_bytes") != 49496
        or split_history.get("redirect_count") != 0
        or split_history.get("retry_count") != 0
        or split_history.get("accepted_event_rows") != 0
        or split_history.get("source_role")
        != "SECONDARY_RETROSPECTIVE_CORROBORATION_ONLY"
    ):
        raise ContractError("SplitHistory zero-event evidence drift")
    for source_name in ("yahoo_chart",):
        source = require_object(split.get(source_name), f"split evidence {source_name}")
        if source.get("accepted_event_rows") != 0:
            raise ContractError("secondary split evidence is not zero-event")
        for key, value in source.items():
            if key.endswith("sha256") and not _SHA256_RE.fullmatch(str(value)):
                raise ContractError(f"invalid split source hash: {source_name}.{key}")

    outputs = require_object(receipt.get("outputs"), "secondary outputs")
    expected_outputs = {
        "secondary_market.jsonl": hashes.market,
        "calendar_identity.jsonl": hashes.calendar,
        "corporate_actions.jsonl": hashes.actions,
        "lifecycle_identity.jsonl": hashes.lifecycle,
    }
    if set(outputs) != set(expected_outputs):
        raise ContractError("secondary receipt output set drift")
    for name, digest in expected_outputs.items():
        item = require_object(outputs.get(name), f"secondary output {name}")
        if (
            item.get("path") != str(SECONDARY_MARKET / name)
            or item.get("sha256") != digest
            or type(item.get("bytes")) is not int
            or int(item["bytes"]) <= 0
        ):
            raise ContractError(f"secondary output identity drift: {name}")


def validate_secondary_rows(
    market_rows: list[dict[str, object]],
    calendar_rows: list[dict[str, object]],
    action_rows: list[dict[str, object]],
    lifecycle_rows: list[dict[str, object]],
) -> None:
    if (
        len(market_rows) != 712
        or len(calendar_rows) != 712
        or len(action_rows) != 11
        or len(lifecycle_rows) != 4
    ):
        raise ContractError("secondary row counts are not frozen")
    market_dates = tuple(str(row.get("session_date")) for row in market_rows)
    calendar_dates = tuple(str(row.get("session_date")) for row in calendar_rows)
    if (
        market_dates != calendar_dates
        or market_dates != tuple(sorted(market_dates))
        or len(set(market_dates)) != 712
        or market_dates[0] != "2023-07-31"
        or market_dates[-1] != "2026-06-01"
    ):
        raise ContractError("secondary market/calendar coverage is not exact")
    if any(
        row.get("symbol") != "SPY"
        or row.get("price_basis") != "UNADJUSTED_RAW_OPEN_CLOSE_ONLY"
        for row in market_rows
    ):
        raise ContractError("secondary market price identity drift")
    action_dates = {str(row.get("ex_date")) for row in action_rows}
    if action_dates != EXPECTED_DISTRIBUTION_DATES or any(
        row.get("symbol") != "SPY"
        or row.get("action_type") != "cash_distribution"
        for row in action_rows
    ):
        raise ContractError("secondary phase-only distributions drift")
    lifecycle_years = {row.get("year") for row in lifecycle_rows}
    if lifecycle_years != {2023, 2024, 2025, 2026} or any(
        row.get("symbol") != "SPY"
        or row.get("exchange_identity") != "NYSE_ARCA"
        or row.get("trust_identity") != "SPDR_S&P_500_ETF_TRUST"
        or row.get("ticker_present") is not True
        or row.get("primary_document_bytes_bound") is not True
        for row in lifecycle_rows
    ):
        raise ContractError("secondary lifecycle identity drift")


def collect_source_hashes(receipt: dict[str, object]) -> dict[str, str]:
    output: dict[str, str] = {}

    def visit(value: object, prefix: str) -> None:
        if isinstance(value, dict):
            for key in sorted(value):
                child = f"{prefix}.{key}" if prefix else key
                item = value[key]
                if key.endswith("sha256") and isinstance(item, str):
                    if not _SHA256_RE.fullmatch(item):
                        raise ContractError(f"invalid source SHA256: {child}")
                    output[child] = item
                else:
                    visit(item, child)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{prefix}[{index}]")

    for root_name in ("inputs", "split_evidence", "fiscal_binding", "materializer"):
        if root_name in receipt:
            visit(receipt[root_name], root_name)
    return output


def load_secondary_packet(
    hashes: SecondaryHashes,
    context: ValidationContext,
) -> SecondaryPacket:
    receipt_payload = exact_bytes(
        SECONDARY_MARKET / "receipt.json",
        hashes.receipt,
        single_link=True,
    )
    market_payload = exact_bytes(
        SECONDARY_MARKET / "secondary_market.jsonl",
        hashes.market,
        single_link=True,
    )
    calendar_payload = exact_bytes(
        SECONDARY_MARKET / "calendar_identity.jsonl",
        hashes.calendar,
        single_link=True,
    )
    actions_payload = exact_bytes(
        SECONDARY_MARKET / "corporate_actions.jsonl",
        hashes.actions,
        single_link=True,
    )
    lifecycle_payload = exact_bytes(
        SECONDARY_MARKET / "lifecycle_identity.jsonl",
        hashes.lifecycle,
        single_link=True,
    )
    sums_payload = exact_bytes(
        SECONDARY_MARKET / "SHA256SUMS",
        hashes.sha256sums,
        single_link=True,
    )
    manifest = parse_sha256sums(sums_payload)
    if manifest != {
        "receipt.json": hashes.receipt,
        "secondary_market.jsonl": hashes.market,
        "calendar_identity.jsonl": hashes.calendar,
        "corporate_actions.jsonl": hashes.actions,
        "lifecycle_identity.jsonl": hashes.lifecycle,
    }:
        raise ContractError("secondary SHA256SUMS scope or identity drift")

    receipt = require_object(strict_json(receipt_payload), "secondary receipt")
    require_secondary_receipt(receipt, hashes)
    market_rows = strict_jsonl(market_payload)
    calendar_rows = strict_jsonl(calendar_payload)
    action_rows = strict_jsonl(actions_payload)
    lifecycle_rows = strict_jsonl(lifecycle_payload)
    validate_secondary_rows(
        market_rows,
        calendar_rows,
        action_rows,
        lifecycle_rows,
    )
    secondary_rows = context.fiscal_states_root.get("secondary_counts_only")
    if not isinstance(secondary_rows, list) or len(secondary_rows) != 34:
        raise ContractError("secondary fiscal state count is not frozen")
    module = context.module
    validation_runner = sys.modules["_dts_secondary_validation_runner_exact"]
    states = validation_runner.monthly_states(
        module,
        secondary_rows,
        context.reports,
    )
    if (
        len(states) != 34
        or states[0].month != date(2023, 8, 1)
        or states[-1].month != date(2026, 5, 1)
    ):
        raise ContractError("secondary fiscal month coverage drift")
    sessions = tuple(
        module.MarketSession(
            date.fromisoformat(str(row["session_date"])),
            float(row["raw_open"]),
            float(row["raw_close"]),
        )
        for row in market_rows
    )
    if (
        len(sessions) != 712
        or sessions[0].session_date != date(2023, 7, 31)
        or sessions[-1].session_date != date(2026, 6, 1)
    ):
        raise ContractError("secondary market session coverage drift")
    distributions = tuple(
        module.Distribution(
            str(row["symbol"]),
            str(row["event_id"]),
            date.fromisoformat(str(row["ex_date"])),
            date.fromisoformat(str(row["pay_date"])),
            float(row["amount_per_share"]),
        )
        for row in action_rows
    )
    state_digest = module.fiscal_states_sha256(states)
    market_digest = module.market_rows_sha256(sessions)
    calendar_digest = module.calendar_sha256(sessions)
    if (
        hashes.receipt == EXPECTED["validation_market_receipt"]
        or hashes.market == EXPECTED["validation_market_file"]
        or market_digest == EXPECTED["validation_market_rows"]
        or calendar_digest == EXPECTED["validation_calendar_rows"]
        or sessions[0].session_date <= date(2023, 6, 1)
    ):
        raise ContractError("secondary market segment is not independent")
    identity = module.SegmentInputIdentity(
        "secondary",
        EXPECTED["fiscal_receipt"],
        state_digest,
        hashes.receipt,
        market_digest,
        calendar_digest,
        EXPECTED["definition"],
        EXPECTED["adapter"],
    )
    return SecondaryPacket(
        receipt,
        states,
        sessions,
        distributions,
        identity,
        collect_source_hashes(receipt),
    )


def result_status(decision: Any) -> str:
    return (
        "RETROSPECTIVE_SECONDARY_PASS_PENDING_USER_REVIEW"
        if decision.all_gates_pass
        else "HOLDOUT_FAIL_CLOSED"
    )


def build_result(
    *,
    runner_sha256: str,
    duckdb_version: str,
    hashes: SecondaryHashes,
    claim_sha256: str,
    packet: SecondaryPacket,
    decision: Any,
    db_before: str,
    db_after: str,
) -> dict[str, object]:
    aggregate = decision_aggregate(decision)
    return {
        "schema_version": "dts-secondary-result-v1",
        "research_id": RESEARCH_ID,
        "status": result_status(decision),
        "classification": "RETROSPECTIVE_SECONDARY_REVISION_LIMITED",
        "code": {
            "runner_sha256": runner_sha256,
            "definition_sha256": EXPECTED["definition"],
            "adapter_sha256": EXPECTED["adapter"],
            "validation_runner_sha256": EXPECTED["validation_runner"],
            "python_executable": sys.executable,
            "duckdb_version": duckdb_version,
        },
        "validation": {
            "claim_sha256": EXPECTED["validation_claim"],
            "result_sha256": EXPECTED["validation_result"],
            "accepted_status": "VALIDATION_PASS_SECONDARY_ELIGIBLE",
            "reconstructed_in_process": True,
            "exact_aggregate_match": True,
        },
        "inputs": {
            "fiscal_receipt_sha256": EXPECTED["fiscal_receipt"],
            "fiscal_states_file_sha256": EXPECTED["fiscal_states"],
            "secondary_state_rows_sha256": packet.input_identity.fiscal_states_sha256,
            "secondary_receipt_sha256": hashes.receipt,
            "secondary_market_file_sha256": hashes.market,
            "secondary_market_rows_sha256": packet.input_identity.market_rows_sha256,
            "secondary_calendar_file_sha256": hashes.calendar,
            "secondary_calendar_rows_sha256": packet.input_identity.calendar_sha256,
            "secondary_actions_file_sha256": hashes.actions,
            "secondary_lifecycle_file_sha256": hashes.lifecycle,
            "secondary_sha256sums_sha256": hashes.sha256sums,
            "secondary_claim_sha256": claim_sha256,
            "source_identity_hashes": packet.source_hashes,
        },
        **aggregate,
        "central_database": {
            "sha256_before": db_before,
            "sha256_after": db_after,
            "unchanged": db_before == db_after == EXPECTED["db"],
            "write_performed": False,
        },
        "boundaries": {
            "rerun": False,
            "validation_rerun": False,
            "parameter_or_source_change": False,
            "strategy_candidate_available": False,
            "shadow": False,
            "paper": False,
            "broker": False,
            "live": False,
        },
    }


def execute_claimed_secondary(
    runner_sha256: str,
    duckdb_version: str,
    hashes: SecondaryHashes,
    context: ValidationContext,
) -> dict[str, object]:
    db_before = hash_large(DB)
    if db_before != EXPECTED["db"]:
        raise ContractError("central DB identity drift")
    packet = load_secondary_packet(hashes, context)
    decision = context.module.run_secondary(
        packet.states,
        packet.sessions,
        terminal_month=date(2026, 6, 1),
        validation=context.decision,
        input_identity=packet.input_identity,
        distributions=packet.distributions,
        splits=(),
    )
    gates = {name: passed for name, passed in decision.gates}
    if tuple(gates) != context.module.GATE_NAMES or any(
        type(value) is not bool for value in gates.values()
    ):
        raise ContractError("secondary gates are malformed")
    db_after = hash_large(DB)
    if db_after != db_before:
        raise ContractError("central DB changed during secondary execution")
    claim_sha = sha256_bytes(read_regular(CLAIM, single_link=True))
    result = build_result(
        runner_sha256=runner_sha256,
        duckdb_version=duckdb_version,
        hashes=hashes,
        claim_sha256=claim_sha,
        packet=packet,
        decision=decision,
        db_before=db_before,
        db_after=db_after,
    )
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
    return result


def run(args: argparse.Namespace) -> dict[str, object]:
    runner_sha = sha256_bytes(read_regular(Path(__file__)))
    if args.expected_runner_sha256 != runner_sha:
        raise ContractError("runner hash mismatch")
    hashes = secondary_hashes(args)
    exact_bytes(DEFINITION, EXPECTED["definition"])
    exact_bytes(ADAPTER, EXPECTED["adapter"])
    exact_bytes(VALIDATION_RUNNER, EXPECTED["validation_runner"])
    exact_bytes(VALIDATION_CLAIM, EXPECTED["validation_claim"])
    exact_bytes(VALIDATION_RESULT, EXPECTED["validation_result"])
    if os.path.lexists(CLAIM) or os.path.lexists(RESULT):
        raise ContractError("secondary identity was already claimed or completed")
    try:
        import duckdb
    except ImportError as exc:
        raise ContractError("the frozen runtime requires duckdb") from exc
    if duckdb.__version__ != "1.5.4":
        raise ContractError("duckdb runtime version drift")

    # No file under SECONDARY_MARKET is touched above this point.
    context = reconstruct_accepted_validation()
    reverify_validation_artifacts()
    atomic_claim(runner_sha, hashes)
    return execute_claimed_secondary(
        runner_sha,
        duckdb.__version__,
        hashes,
        context,
    )


def main(argv: list[str] | None = None) -> int:
    result = run(parse_args(argv))
    result_sha256 = sha256_bytes(read_regular(RESULT, single_link=True))
    print(
        json.dumps(
            {
                "status": result["status"],
                "gate_pass_count": result["gate_pass_count"],
                "result_sha256": result_sha256,
                "candidate": False,
                "db_unchanged": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
