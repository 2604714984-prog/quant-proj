"""One deterministic, point-in-time next-session rebalance."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass, field, fields, is_dataclass, replace
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from quant_system.data import (
    AcceptedSession, AcceptedSessionCalendar, CalendarIdentityError,
    CorporateActionIdentity, SourceIdentity, TypedObservationReceipt, capture_file_bytes,
    capture_file_digest, require_trusted_source, require_typed_observation,
)
from quant_system.markets.a_share import (
    AShareAdjustmentReceipt,
    AShareBar,
    decide_fill as a_share_fill,
    stamp_tax_rate,
)
from quant_system.markets.common import (
    FillDecision, MarketDataError, is_finite_number, is_positive_price,
    require_aware_datetime, require_nonempty_text,
)
from quant_system.markets.universe import (
    StatusEvidence,
    UniverseDecision,
    UniverseMaterialization,
    UniverseSnapshotIdentity,
    evaluate_universe,
    ordered_members_sha256,
    validate_universe_snapshot,
)
from quant_system.markets.us import (
    CorporateActionValuationError, KNOWN_ACTION_TYPES, TERMINAL_ACTION_TYPES,
    cash_settlement_lag_sessions,
    decide_fill as us_fill, resolve_mark,
)
from quant_system.research.identity import DatasetManifest
from quant_system.research.experiments import (
    ExperimentEvent,
    ExperimentAnchorReceipt,
    ExperimentLedgerReceipt,
    ExperimentManifest,
    FinalRunReceipt,
    HoldoutResultReceipt,
    require_adjusted_holdout_for_candidate,
)
from quant_system.research.splits import (
    SplitEvaluation,
    require_split_evaluation_for_candidate,
)
from .blocked_orders import (
    BLOCKED_EXIT_REASONS,
    BlockedExitOrder,
    NoFillEvent,
    RetryInstruction,
    advance_blocked_exit,
)
from .capacity import CapacityObservation, CapacityPolicy, assess_capacity
from .costs import ExecutionCostAssumptions
from .portfolio import Portfolio, Position, Trade

Market = Literal["a_share", "us"]
DecisionPriceBasis = Literal[
    "raw_pre_action_per_old_share",
    "raw_execution_units",
    "adjusted_qfq",
    "adjusted_hfq",
    "adjusted_total_return",
]
ExecutionPriceBasis = Literal[
    "timestamped_session_open",
    "retrospective_daily_bar_open_fill",
    "confirmed_no_open_event",
]
LimitRegime = Literal["applies", "no_limit"]
TargetWeightCallback = Callable[["DecisionContext"], Mapping[str, float]]
_RAW_ACTIONS = {"split", "reverse_split", "dividend", "special_dividend"}
_DECISION_PRICE_BASES = {
    "raw_pre_action_per_old_share",
    "raw_execution_units",
    "adjusted_qfq",
    "adjusted_hfq",
    "adjusted_total_return",
}
_EXECUTION_PRICE_BASES = {
    "timestamped_session_open",
    "retrospective_daily_bar_open_fill",
}
_NO_OPEN_EVENT_BASIS = "confirmed_no_open_event"
_DECISION_ARTIFACT_TOKEN = object()
_STAGE_CONTEXT_TOKEN = object()
_CANDIDATE_RUN_CONFIG_TOKEN = object()
_RESULT_TOKEN = object()


@dataclass(frozen=True)
class StagePlan:
    sessions: tuple[date, ...]
    plan_sha256: str
    _token: object | None = field(default=None, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if self._token is not _STAGE_CONTEXT_TOKEN:
            raise ValueError("StagePlan must be created by create_stage_plan")


@dataclass(frozen=True)
class StageContext:
    plan_sha256: str
    stage_index: int
    stage_session: date
    prior_stage_hash: str
    _token: object | None = field(default=None, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        _sha256(self.plan_sha256, "plan_sha256")
        _sha256(self.prior_stage_hash, "prior_stage_hash")
        if type(self.stage_index) is not int or self.stage_index < 0:
            raise ValueError("stage_index must be a nonnegative integer")
        if type(self.stage_session) is not date:
            raise TypeError("stage_session must be a date")
        if self._token is not _STAGE_CONTEXT_TOKEN:
            raise ValueError("StageContext must be created by genesis_stage or next_stage")


@dataclass(frozen=True)
class CandidateRunConfig:
    decision_artifact_sha256: str
    dataset_identity_sha256: str
    split_identity_sha256: str
    split_evaluation_plan_sha256: str
    stage_plan_sha256: str
    final_stage_index: int
    cost_assumptions_sha256: str
    signal_session: date
    decision_at: datetime
    max_positions: int | None
    parameters_json: str
    config_sha256: str
    _token: object | None = field(default=None, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if self._token is not _CANDIDATE_RUN_CONFIG_TOKEN:
            raise ValueError(
                "CandidateRunConfig must come from capture_candidate_run_config"
            )
        for name in (
            "decision_artifact_sha256",
            "dataset_identity_sha256",
            "split_identity_sha256",
            "split_evaluation_plan_sha256",
            "stage_plan_sha256",
            "cost_assumptions_sha256",
        ):
            _sha256(getattr(self, name), name)
        if type(self.final_stage_index) is not int or self.final_stage_index < 0:
            raise ValueError("final_stage_index must be nonnegative")
        if type(self.signal_session) is not date:
            raise TypeError("signal_session must be a date")
        require_aware_datetime(self.decision_at, "decision_at")
        if self.max_positions is not None and (
            type(self.max_positions) is not int or self.max_positions < 1
        ):
            raise ValueError("max_positions must be a positive integer")
        try:
            parameters = json.loads(self.parameters_json)
        except json.JSONDecodeError as exc:
            raise ValueError("candidate parameters_json is invalid") from exc
        if json.dumps(
            parameters,
            sort_keys=True,
            separators=(",", ":"),
        ) != self.parameters_json:
            raise ValueError("candidate parameters_json must be canonical")
        if hashlib.sha256(_candidate_run_config_payload(self)).hexdigest() != (
            self.config_sha256
        ):
            raise ValueError("candidate run config hash mismatch")


def _candidate_run_config_payload(config: CandidateRunConfig) -> bytes:
    return json.dumps(
        {
            name: value.isoformat() if isinstance(value, (date, datetime)) else value
            for name, value in config.__dict__.items()
            if name not in {"config_sha256", "_token"}
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def capture_candidate_run_config(
    *,
    decision_artifact_sha256: str,
    dataset_identity_sha256: str,
    split_identity_sha256: str,
    split_evaluation_plan_sha256: str,
    stage_plan_sha256: str,
    final_stage_index: int,
    cost_assumptions_sha256: str,
    signal_session: date,
    decision_at: datetime,
    max_positions: int | None,
) -> CandidateRunConfig:
    parameters = {
        "decision_at": require_aware_datetime(decision_at, "decision_at").isoformat(),
        "final_stage_index": final_stage_index,
        "max_positions": max_positions,
        "signal_session": signal_session.isoformat(),
    }
    values = {
        "decision_artifact_sha256": decision_artifact_sha256,
        "dataset_identity_sha256": dataset_identity_sha256,
        "split_identity_sha256": split_identity_sha256,
        "split_evaluation_plan_sha256": split_evaluation_plan_sha256,
        "stage_plan_sha256": stage_plan_sha256,
        "final_stage_index": final_stage_index,
        "cost_assumptions_sha256": cost_assumptions_sha256,
        "signal_session": signal_session,
        "decision_at": decision_at,
        "max_positions": max_positions,
        "parameters_json": json.dumps(
            parameters,
            sort_keys=True,
            separators=(",", ":"),
        ),
    }
    provisional = object.__new__(CandidateRunConfig)
    for name, value in values.items():
        object.__setattr__(provisional, name, value)
    return CandidateRunConfig(
        **values,
        config_sha256=hashlib.sha256(
            _candidate_run_config_payload(provisional)
        ).hexdigest(),
        _token=_CANDIDATE_RUN_CONFIG_TOKEN,
    )


@dataclass(frozen=True)
class TerminalAction:
    event_id: str
    action_type: str
    effective_at: datetime
    recovery_per_share: float
    source: SourceIdentity
    payment_date: date
    accepted_settlement_sessions: tuple[AcceptedSession, ...]
    successor_symbol: str | None = None
    successor_shares_per_share: float | None = None
    observation_receipt: TypedObservationReceipt | None = None

    def __post_init__(self) -> None:
        require_nonempty_text(self.event_id, "event_id")
        require_aware_datetime(self.effective_at, "effective_at")
        if self.action_type not in TERMINAL_ACTION_TYPES:
            raise MarketDataError("unsupported terminal action_type")
        if not is_finite_number(self.recovery_per_share) or self.recovery_per_share < 0:
            raise MarketDataError("recovery_per_share must be finite and nonnegative")
        if not isinstance(self.source, SourceIdentity):
            raise MarketDataError("terminal action requires a SourceIdentity")
        if type(self.payment_date) is not date:
            raise MarketDataError("terminal action payment_date must be a date")
        if type(self.accepted_settlement_sessions) is not tuple or any(
            not isinstance(item, AcceptedSession)
            for item in self.accepted_settlement_sessions
        ):
            raise MarketDataError(
                "terminal action settlement sessions must be an immutable accepted tuple"
            )
        effective_date = self.effective_at.astimezone(timezone.utc).date()
        if self.payment_date < effective_date:
            raise MarketDataError("terminal action payment_date cannot precede effective date")


@dataclass(frozen=True)
class ExecutionInput:
    """One row separating causal sizing inputs from the realized execution event."""

    symbol: str
    market: Market
    open_price: float | None
    currency: str
    source: SourceIdentity
    status_records: tuple[StatusEvidence, ...]
    action_types: tuple[str, ...] = ()
    corporate_actions: tuple[CorporateActionIdentity, ...] = ()
    is_suspended: bool = False
    up_limit: float | None = None
    down_limit: float | None = None
    capacity: CapacityObservation | None = None
    terminal_action: TerminalAction | None = None
    decision_price: float | None = None
    decision_price_source: SourceIdentity | None = None
    decision_price_basis: DecisionPriceBasis | None = None
    execution_price_effective_at: datetime | None = None
    execution_price_basis: ExecutionPriceBasis | None = None
    limit_regime: LimitRegime | None = None
    adjustment_receipt: AShareAdjustmentReceipt | None = None
    execution_observation_receipt: TypedObservationReceipt | None = None
    execution_constraints_observation_receipt: TypedObservationReceipt | None = None
    no_open_observation_receipt: TypedObservationReceipt | None = None
    no_open_observed_at: datetime | None = None
    decision_observation_receipt: TypedObservationReceipt | None = None


@dataclass(frozen=True)
class DecisionContext:
    signal_session: AcceptedSession
    execution_session: AcceptedSession
    decision_at: datetime
    eligible_symbols: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionReceipt:
    sequence: int
    symbol: str
    side: str
    requested_shares: float
    filled_shares: float
    price: float | None
    commission: float
    sell_tax: float
    cash_change: float
    cash_after: float
    reason: str


@dataclass(frozen=True)
class CandidateRunBundle:
    decision_artifact_sha256: str
    dataset_identity_sha256: str
    split_evaluation_sha256: str
    experiment_manifest_sha256: str
    candidate_run_config_sha256: str
    cost_assumptions_sha256: str
    universe_materialization_sha256: str
    source_receipt_sha256s: tuple[str, ...]
    stage_plan_sha256: str
    stage_index: int
    stage_session: date
    prior_stage_hash: str
    base_input_identity_hash: str
    base_receipt_payloads: tuple[str, ...]
    base_receipt_hashes: tuple[str, ...]
    base_stage_hash: str
    adverse_input_identity_hash: str
    adverse_receipt_payloads: tuple[str, ...]
    adverse_stage_hash: str
    bundle_sha256: str

    def verify(self) -> None:
        for name in (
            "decision_artifact_sha256",
            "dataset_identity_sha256",
            "split_evaluation_sha256",
            "experiment_manifest_sha256",
            "candidate_run_config_sha256",
            "cost_assumptions_sha256",
            "universe_materialization_sha256",
            "stage_plan_sha256",
            "prior_stage_hash",
            "base_input_identity_hash",
            "base_stage_hash",
            "adverse_input_identity_hash",
            "adverse_stage_hash",
            "bundle_sha256",
        ):
            _sha256(getattr(self, name), name)
        if (
            not self.source_receipt_sha256s
            or self.source_receipt_sha256s
            != tuple(sorted(set(self.source_receipt_sha256s)))
        ):
            raise ValueError("run bundle source receipts must be sorted and unique")
        for digest in self.source_receipt_sha256s:
            _sha256(digest, "source_receipt_sha256")
        if type(self.stage_index) is not int or self.stage_index < 0:
            raise ValueError("run bundle stage_index must be nonnegative")
        if type(self.stage_session) is not date:
            raise TypeError("run bundle stage_session must be a date")
        base_hashes, base_stage = _bundle_hashes(
            self.base_receipt_payloads,
            identity=self.base_input_identity_hash,
            plan_sha256=self.stage_plan_sha256,
            stage_index=self.stage_index,
            stage_session=self.stage_session,
            prior_stage_hash=self.prior_stage_hash,
        )
        if base_hashes != self.base_receipt_hashes or base_stage != self.base_stage_hash:
            raise ValueError("run bundle base stage hash cannot be replayed")
        _, adverse_stage = _bundle_hashes(
            self.adverse_receipt_payloads,
            identity=self.adverse_input_identity_hash,
            plan_sha256=self.stage_plan_sha256,
            stage_index=self.stage_index,
            stage_session=self.stage_session,
            prior_stage_hash=self.prior_stage_hash,
        )
        if adverse_stage != self.adverse_stage_hash:
            raise ValueError("run bundle adverse stage hash cannot be replayed")
        if hashlib.sha256(_candidate_run_bundle_payload(self)).hexdigest() != (
            self.bundle_sha256
        ):
            raise ValueError("run bundle envelope hash mismatch")


def _bundle_hashes(
    receipt_payloads: tuple[str, ...],
    *,
    identity: str,
    plan_sha256: str,
    stage_index: int,
    stage_session: date,
    prior_stage_hash: str,
) -> tuple[tuple[str, ...], str]:
    for payload in receipt_payloads:
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("run bundle receipt payload is invalid JSON") from exc
        if json.dumps(decoded, sort_keys=True, separators=(",", ":")) != payload:
            raise ValueError("run bundle receipt payload is not canonical")
    prefix = (
        f"{plan_sha256}|{stage_index}|{stage_session.isoformat()}|"
        f"{prior_stage_hash}|{identity}"
    )
    current = hashlib.sha256(prefix.encode()).hexdigest()
    hashes: list[str] = []
    for payload in receipt_payloads:
        current = hashlib.sha256(f"{current}|{payload}".encode()).hexdigest()
        hashes.append(current)
    return tuple(hashes), current


def _candidate_run_bundle_payload(bundle: CandidateRunBundle) -> bytes:
    return json.dumps(
        {
            name: value.isoformat() if isinstance(value, date) else value
            for name, value in bundle.__dict__.items()
            if name != "bundle_sha256"
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def serialize_candidate_run_bundle(bundle: CandidateRunBundle) -> bytes:
    bundle.verify()
    return json.dumps(
        {
            **json.loads(_candidate_run_bundle_payload(bundle)),
            "bundle_sha256": bundle.bundle_sha256,
            "version": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def load_candidate_run_bundle(payload: bytes) -> CandidateRunBundle:
    try:
        values = json.loads(payload)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("candidate run bundle must be valid UTF-8 JSON") from exc
    if type(values) is not dict or values.pop("version", None) != 1:
        raise ValueError("candidate run bundle version is invalid")
    tuple_fields = (
        "source_receipt_sha256s",
        "base_receipt_payloads",
        "base_receipt_hashes",
        "adverse_receipt_payloads",
    )
    for name in tuple_fields:
        if type(values.get(name)) is not list:
            raise ValueError(f"candidate run bundle {name} must be an array")
        values[name] = tuple(values[name])
    try:
        values["stage_session"] = date.fromisoformat(values["stage_session"])
        bundle = CandidateRunBundle(**values)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("candidate run bundle fields are invalid") from exc
    bundle.verify()
    return bundle


@dataclass(frozen=True)
class StaticRebalanceResult:
    portfolio: Portfolio
    context: DecisionContext
    target_weights: tuple[tuple[str, float], ...]
    receipts: tuple[ExecutionReceipt, ...]
    input_identity_hash: str
    receipt_hashes: tuple[str, ...]
    stage_hash: str
    final_nav: float
    strategy_definition_sha256: str
    strategy_adapter_sha256: str
    stage_plan_sha256: str
    stage_index: int
    stage_session: date
    prior_stage_hash: str
    execution_evidence_grade: str = "UNCLASSIFIED"
    interface_grade: str = "UNTRUSTED_EXPERIMENT"
    decision_artifact_sha256: str | None = None
    dataset_identity_sha256: str | None = None
    split_identity_sha256: str | None = None
    experiment_manifest_sha256: str | None = None
    split_evaluation_sha256: str | None = None
    candidate_run_config_sha256: str | None = None
    run_bundle_sha256: str | None = None
    run_bundle: CandidateRunBundle | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    cost_assumptions_sha256: str | None = None
    adverse_input_identity_hash: str | None = None
    adverse_stage_hash: str | None = None
    adverse_final_nav: float | None = None
    base_fx_adjusted_final_nav: float | None = None
    adverse_fx_adjusted_final_nav: float | None = None
    strategy_candidate_available: bool = False
    _token: object | None = field(default=None, repr=False, compare=False)

    def verify_controlled_result(self) -> None:
        if self._token is not _RESULT_TOKEN:
            raise ValueError("stage result must come from the event-loop runner")
        _sha256(self.stage_hash, "stage_hash")
        _sha256(self.prior_stage_hash, "prior_stage_hash")
        if not math.isfinite(self.final_nav):
            raise ValueError("stage result final NAV must be finite")


def create_stage_plan(sessions: tuple[date, ...]) -> StagePlan:
    if not sessions or any(type(session) is not date for session in sessions):
        raise ValueError("stage plan sessions must be a nonempty tuple of dates")
    if sessions != tuple(sorted(sessions)) or len(sessions) != len(set(sessions)):
        raise ValueError("stage plan sessions must be unique and chronological")
    payload = json.dumps(
        {"sessions": tuple(session.isoformat() for session in sessions), "version": 1},
        sort_keys=True,
        separators=(",", ":"),
    )
    return StagePlan(
        sessions,
        hashlib.sha256(payload.encode()).hexdigest(),
        _STAGE_CONTEXT_TOKEN,
    )


def genesis_stage(plan: StagePlan) -> StageContext:
    if not isinstance(plan, StagePlan):
        raise TypeError("plan must be a StagePlan")
    return StageContext(
        plan.plan_sha256,
        0,
        plan.sessions[0],
        "0" * 64,
        _STAGE_CONTEXT_TOKEN,
    )


def next_stage(plan: StagePlan, previous: StaticRebalanceResult) -> StageContext:
    if not isinstance(plan, StagePlan) or not isinstance(previous, StaticRebalanceResult):
        raise TypeError("next_stage requires a StagePlan and previous result")
    if previous.stage_plan_sha256 != plan.plan_sha256:
        raise ValueError("previous result belongs to a different stage plan")
    next_index = previous.stage_index + 1
    if next_index >= len(plan.sessions):
        raise ValueError("stage plan is already complete")
    if previous.stage_session != plan.sessions[previous.stage_index]:
        raise ValueError("previous result stage session is out of plan order")
    return StageContext(
        plan.plan_sha256,
        next_index,
        plan.sessions[next_index],
        previous.stage_hash,
        _STAGE_CONTEXT_TOKEN,
    )


@dataclass(frozen=True)
class DecisionArtifact:
    """Frozen weights and actual strategy/data bytes for the controlled interface."""

    weights: tuple[tuple[str, float], ...]
    feature_snapshot_sha256: str
    strategy_definition_sha256: str
    strategy_adapter_sha256: str
    feature_source: SourceIdentity
    strategy_definition_source: SourceIdentity
    strategy_adapter_source: SourceIdentity
    decision_at: datetime
    dataset_identity_sha256: str
    split_identity_sha256: str
    artifact_sha256: str
    _feature_snapshot_path: Path = field(repr=False, compare=False, hash=False)
    _strategy_definition_path: Path = field(repr=False, compare=False, hash=False)
    _strategy_adapter_path: Path = field(repr=False, compare=False, hash=False)
    _artifact_token: object | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        symbols = tuple(symbol for symbol, _ in self.weights)
        frozen = _weights(dict(self.weights), symbols)
        if frozen != self.weights or len(symbols) != len(set(symbols)):
            raise MarketDataError("decision artifact weights must be sorted and unique")
        for field_name in (
            "feature_snapshot_sha256",
            "strategy_definition_sha256",
            "strategy_adapter_sha256",
            "dataset_identity_sha256",
            "split_identity_sha256",
        ):
            object.__setattr__(self, field_name, _sha256(getattr(self, field_name), field_name))
        for field_name in (
            "feature_source",
            "strategy_definition_source",
            "strategy_adapter_source",
        ):
            try:
                require_trusted_source(getattr(self, field_name))
            except ValueError as exc:
                raise MarketDataError(
                    "decision artifact sources must be captured identities"
                ) from exc
        object.__setattr__(self, "decision_at", require_aware_datetime(self.decision_at, "decision_at"))
        expected = hashlib.sha256(_decision_artifact_payload(self)).hexdigest()
        if self._artifact_token is not _DECISION_ARTIFACT_TOKEN or self.artifact_sha256 != expected:
            raise MarketDataError(
                "DecisionArtifact must be created by capture_decision_artifact"
            )

    def verify_current_bytes(self) -> None:
        observed = {
            "feature_snapshot_sha256": capture_file_digest(self._feature_snapshot_path)[0],
            "strategy_definition_sha256": capture_file_digest(
                self._strategy_definition_path
            )[0],
            "strategy_adapter_sha256": capture_file_digest(self._strategy_adapter_path)[0],
        }
        for field_name, digest in observed.items():
            if digest != getattr(self, field_name):
                raise MarketDataError(f"{field_name} no longer matches captured bytes")


def _decision_artifact_payload(artifact: DecisionArtifact) -> bytes:
    payload = {
        "dataset_identity_sha256": artifact.dataset_identity_sha256,
        "decision_at": require_aware_datetime(
            artifact.decision_at,
            "decision_at",
        ).isoformat(),
        "feature_snapshot_sha256": artifact.feature_snapshot_sha256,
        "feature_source_receipt_sha256": artifact.feature_source.capture_receipt_sha256,
        "split_identity_sha256": artifact.split_identity_sha256,
        "strategy_adapter_sha256": artifact.strategy_adapter_sha256,
        "strategy_adapter_source_receipt_sha256": (
            artifact.strategy_adapter_source.capture_receipt_sha256
        ),
        "strategy_definition_sha256": artifact.strategy_definition_sha256,
        "strategy_definition_source_receipt_sha256": (
            artifact.strategy_definition_source.capture_receipt_sha256
        ),
        "version": 1,
        "weights": artifact.weights,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def capture_decision_artifact(
    *,
    feature_snapshot_path: Path,
    strategy_definition_path: Path,
    strategy_adapter_path: Path,
    feature_source: SourceIdentity,
    strategy_definition_source: SourceIdentity,
    strategy_adapter_source: SourceIdentity,
    decision_at: datetime,
    dataset_identity_sha256: str,
    split_identity_sha256: str,
) -> DecisionArtifact:
    """Execute frozen declarative strategy bytes and capture their derived weights."""

    feature_bytes = capture_file_bytes(feature_snapshot_path)
    definition_bytes = capture_file_bytes(strategy_definition_path)
    adapter_bytes = capture_file_bytes(strategy_adapter_path)
    computed = _execute_frozen_adapter(
        feature_bytes=feature_bytes,
        definition_bytes=definition_bytes,
        adapter_bytes=adapter_bytes,
    )
    symbols = tuple(sorted(computed))
    frozen = _weights(computed, symbols)
    feature_sha = hashlib.sha256(feature_bytes).hexdigest()
    definition_sha = hashlib.sha256(definition_bytes).hexdigest()
    adapter_sha = hashlib.sha256(adapter_bytes).hexdigest()
    sources_and_hashes = (
        (feature_source, feature_sha),
        (strategy_definition_source, definition_sha),
        (strategy_adapter_source, adapter_sha),
    )
    for source, digest in sources_and_hashes:
        try:
            require_trusted_source(source)
        except ValueError as exc:
            raise MarketDataError("strategy artifact source is not captured") from exc
        if source.content_sha256 != digest:
            raise MarketDataError("strategy artifact bytes do not match source receipt")
        if source.available_at > decision_at:
            raise MarketDataError("strategy artifact was unavailable at decision_at")
    provisional = object.__new__(DecisionArtifact)
    values = {
        "weights": frozen,
        "feature_snapshot_sha256": feature_sha,
        "strategy_definition_sha256": definition_sha,
        "strategy_adapter_sha256": adapter_sha,
        "feature_source": feature_source,
        "strategy_definition_source": strategy_definition_source,
        "strategy_adapter_source": strategy_adapter_source,
        "decision_at": require_aware_datetime(decision_at, "decision_at"),
        "dataset_identity_sha256": _sha256(dataset_identity_sha256, "dataset_identity_sha256"),
        "split_identity_sha256": _sha256(split_identity_sha256, "split_identity_sha256"),
        "_feature_snapshot_path": feature_snapshot_path,
        "_strategy_definition_path": strategy_definition_path,
        "_strategy_adapter_path": strategy_adapter_path,
    }
    for name, value in values.items():
        object.__setattr__(provisional, name, value)
    artifact_sha = hashlib.sha256(_decision_artifact_payload(provisional)).hexdigest()
    return DecisionArtifact(
        **values,
        artifact_sha256=artifact_sha,
        _artifact_token=_DECISION_ARTIFACT_TOKEN,
    )


def _execute_frozen_adapter(
    *,
    feature_bytes: bytes,
    definition_bytes: bytes,
    adapter_bytes: bytes,
) -> dict[str, float]:
    """Execute the sole controlled, declarative score-to-weight contract."""

    try:
        feature = json.loads(feature_bytes.decode("utf-8"))
        definition = json.loads(definition_bytes.decode("utf-8"))
        adapter = json.loads(adapter_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MarketDataError("controlled strategy artifacts must be UTF-8 JSON") from exc
    if adapter != {
        "feature_field": "scores",
        "normalization": "positive_sum",
        "transform": "threshold",
        "version": 1,
    }:
        raise MarketDataError("unsupported controlled strategy adapter contract")
    if not isinstance(definition, dict) or set(definition) != {
        "minimum_score",
        "version",
    } or definition["version"] != 1:
        raise MarketDataError("controlled strategy definition has an invalid schema")
    threshold = definition["minimum_score"]
    if not is_finite_number(threshold) or float(threshold) < 0:
        raise MarketDataError("minimum_score must be finite and nonnegative")
    if not isinstance(feature, dict) or set(feature) != {"scores", "version"} \
            or feature["version"] != 1 or not isinstance(feature["scores"], dict):
        raise MarketDataError("controlled feature snapshot has an invalid schema")
    scores: dict[str, float] = {}
    for symbol, score in feature["scores"].items():
        if not isinstance(symbol, str) or not symbol.strip():
            raise MarketDataError("feature symbols must be nonempty strings")
        if not is_finite_number(score):
            raise MarketDataError("feature scores must be finite numbers")
        normalized = float(score)
        if normalized > float(threshold):
            scores[symbol] = normalized
    total = math.fsum(scores.values())
    if not scores or not math.isfinite(total) or total <= 0:
        raise MarketDataError("controlled strategy produced no positive eligible scores")
    return {symbol: score / total for symbol, score in scores.items()}


def run_static_rebalance(
    portfolio: Portfolio,
    calendar: AcceptedSessionCalendar,
    *,
    signal_session: date,
    decision_at: datetime,
    execution_inputs: tuple[ExecutionInput, ...],
    execution_calendar_revision: AcceptedSessionCalendar | None = None,
    universe_members: tuple[str, ...],
    universe_snapshot: UniverseSnapshotIdentity,
    target_weights: TargetWeightCallback,
    strategy_definition_sha256: str,
    strategy_adapter_sha256: str,
    stage_context: StageContext,
    capacity_policy: CapacityPolicy | None = None,
    max_positions: int | None = None,
    slippage_bps: float = 0.0,
) -> StaticRebalanceResult:
    """Run an experimental callable-based rebalance on a copy.

    The returned interface grade is always ``UNTRUSTED_EXPERIMENT``. Use
    ``run_candidate_rebalance`` for a controlled, non-callable decision input.
    """
    if not isinstance(portfolio, Portfolio) or not isinstance(calendar, AcceptedSessionCalendar):
        raise TypeError("portfolio and calendar have invalid types")
    if not isinstance(stage_context, StageContext):
        raise TypeError("stage_context must come from genesis_stage or next_stage")
    if stage_context.stage_session != signal_session:
        raise ValueError("stage_context session must match signal_session")
    definition_sha = _sha256(strategy_definition_sha256, "strategy_definition_sha256")
    adapter_sha = _sha256(strategy_adapter_sha256, "strategy_adapter_sha256")
    cutoff = require_aware_datetime(decision_at, "decision_at")
    signal = calendar.session_on(signal_session, as_of=cutoff)
    execution = calendar.next_session(signal_session, as_of=cutoff)
    if cutoff < signal.close_at or cutoff >= execution.open_at:
        raise MarketDataError(
            "decision_at must be between signal close and strictly before next-session open"
        )
    (
        settlement_calendar,
        settlement_as_of,
        execution_calendar_revision_rows,
    ) = _execution_calendar(
        calendar,
        execution_calendar_revision,
        execution,
        cutoff,
        portfolio,
    )
    if not is_finite_number(slippage_bps) or not 0 <= float(slippage_bps) < 10_000:
        raise ValueError("slippage_bps must be finite and in [0, 10000)")
    if max_positions is not None and (
        type(max_positions) is not int or max_positions < 1
    ):
        raise ValueError("max_positions must be a positive integer or None")
    ordered_members_sha256(universe_members)
    rows = _inputs(execution_inputs, portfolio, execution, cutoff)
    working = deepcopy(portfolio)
    working.start_session(execution.session_date)
    if set(working.positions) - rows.keys():
        raise MarketDataError("every held symbol requires an execution input")
    member_set = set(universe_members)
    if member_set - rows.keys():
        raise MarketDataError("every universe member requires an execution input")
    terminal_successors = {
        row.terminal_action.successor_symbol
        for row in rows.values()
        if row.terminal_action is not None and row.terminal_action.successor_symbol
    }
    unexplained_rows = set(rows) - member_set - set(working.positions) - terminal_successors
    if unexplained_rows:
        raise MarketDataError(
            "nonmember execution inputs are limited to held or terminal-maintenance symbols"
        )
    market: Market = "us" if portfolio.us_cash_settlement else "a_share"
    validate_universe_snapshot(
        universe_snapshot,
        market=market,
        calendar_identity=calendar.identity,
        session=execution,
        decision_at=cutoff,
        members=universe_members,
        records_by_symbol={symbol: row.status_records for symbol, row in rows.items()},
    )
    decisions = {
        symbol: evaluate_universe(
            symbol,
            execution,
            cutoff,
            row.status_records,
            market=market,
        )
        for symbol, row in rows.items()
    }
    _require_matching_suspension(rows, decisions)
    _terminal_checks(rows, decisions, calendar, execution, cutoff)
    receipts: list[ExecutionReceipt] = []
    _actions(working, rows, execution, cutoff, receipts)
    eligible = tuple(symbol for symbol in universe_members if decisions[symbol].eligible)
    _require_decision_prices(eligible, working, rows, cutoff)
    context = DecisionContext(signal, execution, cutoff, eligible)
    weights = _weights(target_weights(context), eligible)
    nav = working.nav(_decision_marks(working, rows))
    desired = {
        symbol: _lot(
            nav * dict(weights).get(symbol, 0) / _decision_price(rows[symbol]),
            working.lot_size,
        )
        for symbol in eligible
    }
    desired.update({symbol: 0.0 for symbol in working.positions if symbol not in desired})
    for side in ("sell", "buy"):
        for symbol in sorted(desired):
            current = working.positions.get(symbol, Position()).shares
            delta = desired[symbol] - current
            if (side == "sell" and delta >= -1e-9) or (side == "buy" and delta <= 1e-9):
                continue
            requested = -delta if side == "sell" else delta
            requested = current if side == "sell" and math.isclose(
                requested, current, abs_tol=1e-9
            ) else _lot(requested, working.lot_size)
            if requested:
                if (
                    side == "buy"
                    and max_positions is not None
                    and symbol not in working.positions
                    and len(working.positions) >= max_positions
                ):
                    _receipt(
                        receipts,
                        symbol,
                        side,
                        requested,
                        0,
                        None,
                        0,
                        0,
                        0,
                        working.available_cash,
                        "max_positions_after_blocked_exit",
                    )
                    continue
                _order(
                    working,
                    calendar,
                    settlement_calendar,
                    settlement_as_of,
                    execution,
                    cutoff,
                    rows[symbol],
                    side,
                    requested,
                    capacity_policy,
                    slippage_bps,
                    receipts,
                )
    final_nav = working.nav(_marks(working, rows))
    identity = _identity(
        context,
        calendar,
        rows,
        portfolio,
        weights,
        capacity_policy,
        max_positions,
        slippage_bps,
        cutoff,
        universe_members,
        universe_snapshot,
        definition_sha,
        adapter_sha,
        execution_calendar_revision,
        execution_calendar_revision_rows,
    )
    receipt_hashes, stage_hash = _hashes(tuple(receipts), identity, stage_context)
    return StaticRebalanceResult(
        working,
        context,
        weights,
        tuple(receipts),
        identity,
        receipt_hashes,
        stage_hash,
        final_nav,
        definition_sha,
        adapter_sha,
        stage_context.plan_sha256,
        stage_context.stage_index,
        stage_context.stage_session,
        stage_context.prior_stage_hash,
        execution_evidence_grade=_execution_evidence_grade(rows),
        _token=_RESULT_TOKEN,
    )


def run_candidate_rebalance(
    portfolio: Portfolio,
    calendar: AcceptedSessionCalendar,
    *,
    signal_session: date,
    decision_at: datetime,
    execution_inputs: tuple[ExecutionInput, ...],
    universe_materialization: UniverseMaterialization,
    dataset_manifest: DatasetManifest,
    decision_artifact: DecisionArtifact,
    candidate_run_config: CandidateRunConfig,
    experiment_events: tuple[ExperimentEvent, ...],
    experiment_manifest: ExperimentManifest,
    experiment_ledger: ExperimentLedgerReceipt,
    experiment_anchor: ExperimentAnchorReceipt,
    holdout_event: ExperimentEvent,
    holdout_result_receipt: HoldoutResultReceipt,
    final_run_receipt: FinalRunReceipt,
    split_evaluation: SplitEvaluation,
    cost_assumptions: ExecutionCostAssumptions,
    stage_context: StageContext,
    execution_calendar_revision: AcceptedSessionCalendar | None = None,
    max_positions: int | None = None,
) -> StaticRebalanceResult:
    """Run the controlled interface from weights computed from frozen bytes only."""

    if not isinstance(decision_artifact, DecisionArtifact):
        raise TypeError("decision_artifact must be a captured DecisionArtifact")
    if not isinstance(universe_materialization, UniverseMaterialization):
        raise TypeError(
            "universe_materialization must come from materialize_universe_partition"
        )
    if not isinstance(dataset_manifest, DatasetManifest):
        raise TypeError("dataset_manifest must be a DatasetManifest")
    try:
        dataset_manifest.verify_identity()
    except ValueError as exc:
        raise MarketDataError("dataset manifest semantic identity mismatch") from exc
    if decision_artifact.dataset_identity_sha256 != dataset_manifest.identity_sha256:
        raise MarketDataError(
            "decision artifact dataset identity must match the dataset manifest"
        )
    if decision_artifact.split_identity_sha256 != dataset_manifest.split_manifest_sha256:
        raise MarketDataError("decision artifact split identity must match the dataset manifest")
    if not isinstance(cost_assumptions, ExecutionCostAssumptions):
        raise TypeError("cost_assumptions must be ExecutionCostAssumptions")
    if not isinstance(candidate_run_config, CandidateRunConfig):
        raise TypeError("candidate_run_config must be a captured CandidateRunConfig")
    candidate_run_config.__post_init__()
    if not isinstance(experiment_ledger, ExperimentLedgerReceipt):
        raise TypeError("experiment_ledger must be a persistent ledger receipt")
    experiment_ledger.verify_current_bytes()
    require_adjusted_holdout_for_candidate(
        holdout_event,
        receipt=holdout_result_receipt,
        manifest=experiment_manifest,
        events=experiment_events,
        anchor=experiment_anchor,
    )
    require_split_evaluation_for_candidate(split_evaluation)
    if (
        holdout_result_receipt.split_evaluation_sha256
        != split_evaluation.evaluation_sha256
        or holdout_event.split_evaluation_plan_sha256
        != split_evaluation.plan_sha256
    ):
        raise MarketDataError(
            "holdout result must bind the evaluated preregistered split plan"
        )
    expected_parameters = json.dumps(
        {
            "decision_at": require_aware_datetime(
                decision_at,
                "decision_at",
            ).isoformat(),
            "final_stage_index": stage_context.stage_index,
            "max_positions": max_positions,
            "signal_session": signal_session.isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    if (
        candidate_run_config.decision_artifact_sha256
        != decision_artifact.artifact_sha256
        or candidate_run_config.dataset_identity_sha256
        != dataset_manifest.identity_sha256
        or candidate_run_config.split_identity_sha256
        != dataset_manifest.split_manifest_sha256
        or candidate_run_config.split_evaluation_plan_sha256
        != split_evaluation.plan_sha256
        or candidate_run_config.stage_plan_sha256 != stage_context.plan_sha256
        or candidate_run_config.final_stage_index != stage_context.stage_index
        or candidate_run_config.cost_assumptions_sha256
        != cost_assumptions.identity_sha256
        or candidate_run_config.signal_session != signal_session
        or candidate_run_config.decision_at
        != require_aware_datetime(decision_at, "decision_at")
        or candidate_run_config.max_positions != max_positions
        or candidate_run_config.parameters_json != expected_parameters
        or holdout_event.candidate_run_config_sha256
        != candidate_run_config.config_sha256
        or holdout_event.parameters_json != candidate_run_config.parameters_json
    ):
        raise MarketDataError(
            "candidate run parameters or final-stage completion differ from preregistration"
        )
    if (
        experiment_ledger.event_count != experiment_manifest.event_count
        or experiment_ledger.head_sha256 != experiment_manifest.head_sha256
    ):
        raise MarketDataError("persistent experiment ledger does not match manifest")
    if holdout_event.stage_plan_sha256 != stage_context.plan_sha256:
        raise MarketDataError("holdout evidence does not bind the complete stage plan")
    if (
        not isinstance(final_run_receipt, FinalRunReceipt)
        or final_run_receipt.stage_plan_sha256 != stage_context.plan_sha256
        or final_run_receipt.stage_count != stage_context.stage_index + 1
        or final_run_receipt.final_stage_hash != holdout_result_receipt.final_stage_hash
        or holdout_result_receipt.final_run_receipt_sha256
        != final_run_receipt.receipt_sha256
    ):
        raise MarketDataError("holdout evidence does not bind the actual final run")
    final_run_receipt.__post_init__()
    if any(row.capacity is None for row in execution_inputs):
        raise MarketDataError("candidate execution requires capacity evidence for every input")
    if any(row.currency != cost_assumptions.currency for row in execution_inputs):
        raise MarketDataError("execution and cost assumption currencies must match")
    cutoff = require_aware_datetime(decision_at, "decision_at")
    execution_for_costs = calendar.next_session(signal_session, as_of=cutoff)
    _require_cost_model(portfolio, cost_assumptions, execution_for_costs.session_date)
    if decision_artifact.decision_at != cutoff:
        raise MarketDataError("decision artifact decision_at mismatch")
    decision_artifact.verify_current_bytes()
    universe_materialization.verify_current_bytes()
    universe_members = universe_materialization.members
    universe_snapshot = universe_materialization.snapshot
    if dataset_manifest.universe_snapshot_sha256 != universe_materialization.materialization_sha256:
        raise MarketDataError("dataset manifest must bind the frozen universe partition")
    if decision_artifact.dataset_identity_sha256 != dataset_manifest.identity_sha256:
        raise MarketDataError(
            "decision artifact dataset identity must match the dataset manifest"
        )
    if decision_artifact.split_identity_sha256 != dataset_manifest.split_manifest_sha256:
        raise MarketDataError("decision artifact split identity must match the dataset manifest")
    if split_evaluation.manifest_sha256 != dataset_manifest.split_manifest_sha256:
        raise MarketDataError("split evaluation must match the dataset split manifest")
    if dataset_manifest.cost_policy_sha256 != cost_assumptions.identity_sha256:
        raise MarketDataError("dataset cost policy must match execution cost assumptions")
    if (
        holdout_event.definition_sha256 != decision_artifact.strategy_definition_sha256
        or holdout_event.dataset_sha256 != dataset_manifest.identity_sha256
        or holdout_event.split_sha256 != dataset_manifest.split_manifest_sha256
    ):
        raise MarketDataError("holdout evidence does not bind candidate strategy/data/split")
    provider_qualified = _require_candidate_sources(
        calendar,
        execution_inputs,
        universe_snapshot,
        cutoff,
        execution_calendar_revision,
    )
    provider_qualified = provider_qualified and all(
        source.is_provider_qualified_capture
        for source in (
            decision_artifact.feature_source,
            decision_artifact.strategy_definition_source,
            decision_artifact.strategy_adapter_source,
        )
    )
    provider_qualified = (
        provider_qualified
        and dataset_manifest.has_captured_semantics
        and dataset_manifest.has_pit_partitions
        and dataset_manifest.has_verified_split_manifest
        and holdout_event.external_anchor_capture_level
        == "PROVIDER_QUALIFIED_CAPTURE"
    )
    common = {
        "signal_session": signal_session,
        "decision_at": cutoff,
        "execution_inputs": execution_inputs,
        "execution_calendar_revision": execution_calendar_revision,
        "universe_members": universe_members,
        "universe_snapshot": universe_snapshot,
        "target_weights": lambda _: dict(decision_artifact.weights),
        "strategy_definition_sha256": decision_artifact.strategy_definition_sha256,
        "strategy_adapter_sha256": decision_artifact.strategy_adapter_sha256,
        "capacity_policy": cost_assumptions.capacity_policy,
        "max_positions": max_positions,
        "stage_context": stage_context,
    }
    base_portfolio = deepcopy(portfolio)
    base_portfolio.costs = cost_assumptions.base.transaction_cost_model()
    base_portfolio.a_share_stamp_tax_schedule = False
    result = run_static_rebalance(
        base_portfolio,
        calendar,
        slippage_bps=cost_assumptions.base.slippage_bps,
        **common,
    )
    if (
        result.stage_hash != final_run_receipt.final_stage_hash
        or abs(result.final_nav - final_run_receipt.final_nav) > 1e-12
    ):
        raise MarketDataError("candidate replay differs from the frozen final run")
    adverse_portfolio = deepcopy(base_portfolio)
    adverse_portfolio.costs = cost_assumptions.adverse.transaction_cost_model()
    adverse_portfolio.a_share_stamp_tax_schedule = False
    adverse = run_static_rebalance(
        adverse_portfolio,
        calendar,
        slippage_bps=cost_assumptions.adverse.slippage_bps,
        **common,
    )
    assumption_sha = cost_assumptions.identity_sha256
    candidate_identity = hashlib.sha256(
        (
            f"{result.input_identity_hash}|{decision_artifact.artifact_sha256}|"
            f"{dataset_manifest.identity_sha256}|{dataset_manifest.split_manifest_sha256}|"
            f"{split_evaluation.evaluation_sha256}|"
            f"{experiment_manifest.head_sha256}|{candidate_run_config.config_sha256}|"
            f"{assumption_sha}|base"
        ).encode()
    ).hexdigest()
    receipt_hashes, stage_hash = _hashes(
        result.receipts,
        candidate_identity,
        stage_context,
    )
    adverse_identity = hashlib.sha256(
        (
            f"{adverse.input_identity_hash}|{decision_artifact.artifact_sha256}|"
            f"{dataset_manifest.identity_sha256}|{dataset_manifest.split_manifest_sha256}|"
            f"{split_evaluation.evaluation_sha256}|"
            f"{experiment_manifest.head_sha256}|{candidate_run_config.config_sha256}|"
            f"{assumption_sha}|adverse"
        ).encode()
    ).hexdigest()
    _, adverse_stage_hash = _hashes(
        adverse.receipts,
        adverse_identity,
        stage_context,
    )
    source_receipts = tuple(
        sorted(
            {
                *_source_receipt_hashes(
                    calendar,
                    execution_calendar_revision,
                    execution_inputs,
                    universe_snapshot,
                    decision_artifact,
                    dataset_manifest.partition_sources,
                ),
                holdout_event.external_anchor_sha256,
            }
        )
    )
    run_bundle = _build_candidate_run_bundle(
        result=result,
        adverse=adverse,
        decision_artifact=decision_artifact,
        dataset_manifest=dataset_manifest,
        split_evaluation=split_evaluation,
        experiment_manifest=experiment_manifest,
        candidate_run_config=candidate_run_config,
        cost_assumptions=cost_assumptions,
        universe_materialization=universe_materialization,
        source_receipt_sha256s=source_receipts,
        base_input_identity_hash=candidate_identity,
        base_receipt_hashes=receipt_hashes,
        base_stage_hash=stage_hash,
        adverse_input_identity_hash=adverse_identity,
        adverse_stage_hash=adverse_stage_hash,
        stage_context=stage_context,
    )
    return replace(
        result,
        input_identity_hash=candidate_identity,
        receipt_hashes=receipt_hashes,
        stage_hash=stage_hash,
        interface_grade=(
            "GROSS_ONLY_EXPERIMENT"
            if cost_assumptions.gross_only
            else "RETROSPECTIVE_RESEARCH_ONLY"
            if "RETROSPECTIVE" in result.execution_evidence_grade
            else "GENERIC_CAPTURE_EXPERIMENT"
            if not provider_qualified
            else "CONTROLLED_CANDIDATE_INPUT"
        ),
        decision_artifact_sha256=decision_artifact.artifact_sha256,
        dataset_identity_sha256=decision_artifact.dataset_identity_sha256,
        split_identity_sha256=decision_artifact.split_identity_sha256,
        experiment_manifest_sha256=experiment_manifest.head_sha256,
        split_evaluation_sha256=split_evaluation.evaluation_sha256,
        candidate_run_config_sha256=candidate_run_config.config_sha256,
        run_bundle_sha256=run_bundle.bundle_sha256,
        run_bundle=run_bundle,
        cost_assumptions_sha256=assumption_sha,
        adverse_input_identity_hash=adverse_identity,
        adverse_stage_hash=adverse_stage_hash,
        adverse_final_nav=adverse.final_nav,
        base_fx_adjusted_final_nav=result.final_nav * cost_assumptions.base.fx_to_base,
        adverse_fx_adjusted_final_nav=(
            adverse.final_nav * cost_assumptions.adverse.fx_to_base
        ),
        strategy_candidate_available=False,
    )


def _require_cost_model(
    portfolio: Portfolio,
    assumptions: ExecutionCostAssumptions,
    execution_session: date,
) -> None:
    base = assumptions.base
    if (
        portfolio.costs.commission_rate != base.commission_rate
        or portfolio.costs.minimum_commission != base.minimum_commission
    ):
        raise MarketDataError("portfolio cost model must match base cost assumptions")
    if assumptions.gross_only:
        if portfolio.costs.sell_tax_rate != 0:
            raise MarketDataError("gross-only portfolio must have zero configured costs")
    elif portfolio.a_share_stamp_tax_schedule:
        if base.regulatory_fee_rate != stamp_tax_rate(execution_session):
            raise MarketDataError("A-share regulatory fee assumption must match its schedule")
    elif portfolio.costs.sell_tax_rate != base.regulatory_fee_rate:
        raise MarketDataError("portfolio regulatory fees must match base cost assumptions")


def _execution_evidence_grade(rows: Mapping[str, ExecutionInput]) -> str:
    bases = {row.execution_price_basis for row in rows.values()}
    if bases == {"timestamped_session_open"}:
        return "TIMESTAMPED_EXECUTION"
    if bases == {"retrospective_daily_bar_open_fill"}:
        return "RETROSPECTIVE_EXECUTION"
    if bases == {"confirmed_no_open_event"}:
        return "CONFIRMED_NO_OPEN"
    if "retrospective_daily_bar_open_fill" in bases:
        return "MIXED_RETROSPECTIVE"
    return "MIXED_CONFIRMED_NO_OPEN"


def _require_candidate_sources(
    calendar: AcceptedSessionCalendar,
    execution_inputs: tuple[ExecutionInput, ...],
    universe_snapshot: UniverseSnapshotIdentity,
    cutoff: datetime,
    execution_calendar_revision: AcceptedSessionCalendar | None,
) -> bool:
    sources: list[SourceIdentity] = []
    require_trusted_source(calendar.identity.source_identity)
    sources.append(calendar.identity.source_identity)
    for day in calendar.session_dates:
        source = calendar.session_on(day, as_of=cutoff).source
        require_trusted_source(source)
        sources.append(source)
    require_trusted_source(universe_snapshot.source_identity)
    sources.append(universe_snapshot.source_identity)
    if execution_calendar_revision is not None:
        require_trusted_source(execution_calendar_revision.identity.source_identity)
        sources.append(execution_calendar_revision.identity.source_identity)
        for session in execution_calendar_revision.sessions:
            require_trusted_source(session.source)
            sources.append(session.source)
    for row in execution_inputs:
        require_trusted_source(row.source)
        sources.append(row.source)
        if row.decision_price_source is not None:
            require_trusted_source(row.decision_price_source)
            sources.append(row.decision_price_source)
        for status in row.status_records:
            require_trusted_source(status.source)
            sources.append(status.source)
        for action in row.corporate_actions:
            require_trusted_source(action.source)
            sources.append(action.source)
        if row.capacity is not None:
            require_trusted_source(row.capacity.source)
            sources.append(row.capacity.source)
        if row.adjustment_receipt is not None:
            require_trusted_source(row.adjustment_receipt.factor_source)
            require_trusted_source(row.adjustment_receipt.action_completeness_source)
            sources.extend(
                (
                    row.adjustment_receipt.factor_source,
                    row.adjustment_receipt.action_completeness_source,
                )
            )
        if row.terminal_action is not None:
            require_trusted_source(row.terminal_action.source)
            sources.append(row.terminal_action.source)
    provider_qualified = bool(sources) and all(
        source.is_provider_qualified_capture for source in sources
    )
    if provider_qualified:
        try:
            _require_candidate_typed_values(
                calendar,
                execution_inputs,
                universe_snapshot,
                execution_calendar_revision,
            )
        except ValueError as exc:
            raise MarketDataError(
                "provider-qualified candidate values lack matching typed receipts"
            ) from exc
    return provider_qualified


def _require_session_observation(session: AcceptedSession) -> None:
    require_typed_observation(
        session.observation_receipt,
        source=session.source,
        observation_kind="calendar_session",
        subject_id=f"{session.exchange_id}:{session.session_date.isoformat()}",
        expected_values={
            "close_at": session.close_at,
            "exchange_id": session.exchange_id,
            "exchange_timezone": session.exchange_timezone,
            "is_early_close": session.is_early_close,
            "open_at": session.open_at,
            "session_date": session.session_date,
        },
    )


def _require_candidate_typed_values(
    calendar: AcceptedSessionCalendar,
    execution_inputs: tuple[ExecutionInput, ...],
    universe_snapshot: UniverseSnapshotIdentity,
    execution_calendar_revision: AcceptedSessionCalendar | None,
) -> None:
    for session in calendar.sessions:
        _require_session_observation(session)
    if execution_calendar_revision is not None:
        for session in execution_calendar_revision.sessions:
            _require_session_observation(session)
    require_typed_observation(
        universe_snapshot.observation_receipt,
        source=universe_snapshot.source_identity,
        observation_kind="universe_snapshot",
        subject_id=(
            f"{universe_snapshot.exchange_id}:"
            f"{universe_snapshot.effective_session.isoformat()}"
        ),
        expected_values={
            "calendar_identity_sha256": universe_snapshot.calendar_identity_sha256,
            "exchange_id": universe_snapshot.exchange_id,
            "lifecycle_coverage_sha256": universe_snapshot.lifecycle_coverage_sha256,
            "market": universe_snapshot.market,
            "member_count": universe_snapshot.member_count,
            "ordered_members_sha256": universe_snapshot.ordered_members_sha256,
        },
    )
    for row in execution_inputs:
        require_typed_observation(
            row.execution_observation_receipt,
            source=row.source,
            observation_kind="execution_price",
            subject_id=row.symbol,
            expected_values={
                "basis": row.execution_price_basis,
                "currency": row.currency,
                "effective_at": row.execution_price_effective_at,
                "open_price": row.open_price,
                "symbol": row.symbol,
            },
        )
        if row.market == "a_share":
            require_typed_observation(
                row.execution_constraints_observation_receipt,
                source=row.source,
                observation_kind="a_share_execution_constraints",
                subject_id=row.symbol,
                expected_values={
                    "down_limit": row.down_limit,
                    "effective_at": row.execution_price_effective_at,
                    "is_suspended": row.is_suspended,
                    "limit_regime": row.limit_regime,
                    "symbol": row.symbol,
                    "up_limit": row.up_limit,
                },
            )
        if row.execution_price_basis == _NO_OPEN_EVENT_BASIS:
            require_typed_observation(
                row.no_open_observation_receipt,
                source=row.source,
                observation_kind="market_no_open_event",
                subject_id=row.symbol,
                expected_values={
                    "effective_at": row.execution_price_effective_at,
                    "event_type": (
                        "terminal"
                        if row.terminal_action is not None
                        else "trading_halt"
                    ),
                    "observed_at": row.no_open_observed_at,
                    "symbol": row.symbol,
                },
            )
        if row.decision_price_source is not None:
            require_typed_observation(
                row.decision_observation_receipt,
                source=row.decision_price_source,
                observation_kind="decision_price",
                subject_id=row.symbol,
                expected_values={
                    "basis": row.decision_price_basis,
                    "currency": row.currency,
                    "price": row.decision_price,
                    "symbol": row.symbol,
                },
            )
        for status in row.status_records:
            require_typed_observation(
                status.observation_receipt,
                source=status.source,
                observation_kind="status",
                subject_id=status.symbol,
                expected_values={
                    "effective_from": status.effective_from,
                    "effective_to": status.effective_to,
                    "exchange_timezone": status.exchange_timezone,
                    "kind": status.kind,
                    "status_id": status.status_id,
                    "symbol": status.symbol,
                    "value": status.value,
                },
            )
        for action in row.corporate_actions:
            require_typed_observation(
                action.observation_receipt,
                source=action.source,
                observation_kind="corporate_action",
                subject_id=action.subject_id,
                expected_values={
                    "action_id": action.action_id,
                    "action_type": action.action_type,
                    "cash_amount": action.cash_amount,
                    "currency": action.currency,
                    "effective_at": action.effective_at,
                    "ex_date": action.ex_date,
                    "new_subject_id": action.new_subject_id,
                    "pay_date": action.pay_date,
                    "record_date": action.record_date,
                    "split_ratio": action.split_ratio,
                    "subject_id": action.subject_id,
                    "unit": action.unit,
                },
            )
        if row.capacity is not None:
            require_typed_observation(
                row.capacity.observation_receipt,
                source=row.capacity.source,
                observation_kind="capacity",
                subject_id=row.capacity.subject_id,
                expected_values={
                    "currency": row.capacity.currency,
                    "observed_session": row.capacity.observed_session.session_date,
                    "session_amount": row.capacity.session_amount,
                    "session_volume_shares": row.capacity.session_volume_shares,
                    "subject_id": row.capacity.subject_id,
                },
            )
        if row.adjustment_receipt is not None:
            adjustment = row.adjustment_receipt
            require_typed_observation(
                adjustment.factor_observation_receipt,
                source=adjustment.factor_source,
                observation_kind="a_share_adjustment_factor",
                subject_id=adjustment.subject_id,
                expected_values={
                    "adjustment_factor": adjustment.adjustment_factor,
                    "price_basis": adjustment.price_basis,
                    "session": adjustment.effective_session,
                    "symbol": adjustment.subject_id,
                },
            )
            require_typed_observation(
                adjustment.action_observation_receipt,
                source=adjustment.action_completeness_source,
                observation_kind="a_share_action_completeness",
                subject_id=adjustment.subject_id,
                expected_values={
                    "action_types": list(adjustment.action_types),
                    "session": adjustment.effective_session,
                    "symbol": adjustment.subject_id,
                },
            )
        if row.terminal_action is not None:
            action = row.terminal_action
            require_typed_observation(
                action.observation_receipt,
                source=action.source,
                observation_kind="terminal_action",
                subject_id=row.symbol,
                expected_values={
                    "action_type": action.action_type,
                    "effective_at": action.effective_at,
                    "event_id": action.event_id,
                    "payment_date": action.payment_date,
                    "recovery_per_share": action.recovery_per_share,
                    "successor_shares_per_share": action.successor_shares_per_share,
                    "successor_symbol": action.successor_symbol,
                    "symbol": row.symbol,
                },
            )


def _execution_calendar(
    decision_calendar: AcceptedSessionCalendar,
    revision: AcceptedSessionCalendar | None,
    execution: AcceptedSession,
    cutoff: datetime,
    portfolio: Portfolio,
) -> tuple[
    AcceptedSessionCalendar,
    datetime,
    tuple[AcceptedSession, ...] | None,
]:
    if revision is None:
        return decision_calendar, cutoff, None
    if not portfolio.us_cash_settlement:
        raise MarketDataError("execution calendar revisions are US-settlement-only")
    if not isinstance(revision, AcceptedSessionCalendar):
        raise TypeError("execution_calendar_revision must be an AcceptedSessionCalendar")
    original_identity = decision_calendar.identity
    revised_identity = revision.identity
    if (
        revised_identity.exchange_id != original_identity.exchange_id
        or revised_identity.exchange_timezone != original_identity.exchange_timezone
        or revised_identity.coverage_start != original_identity.coverage_start
        or revised_identity.coverage_end != original_identity.coverage_end
    ):
        raise MarketDataError(
            "execution calendar revision must preserve exchange, timezone, and coverage"
        )
    revised_source = revised_identity.source_identity
    if revised_source.supersedes_revision_id != original_identity.source_identity.revision_id:
        raise MarketDataError("execution calendar revision must supersede the decision calendar")
    if not cutoff < revised_source.available_at <= execution.open_at:
        raise MarketDataError(
            "execution calendar revision must become available after decision and by execution open"
        )
    try:
        revision_rows = tuple(
            revision.session_on(day, as_of=execution.open_at)
            for day in revision.session_dates
        )
    except CalendarIdentityError as exc:
        raise MarketDataError(
            "every execution calendar revision row must be available by execution open"
        ) from exc
    original_prefix = tuple(
        _session_semantics(decision_calendar.session_on(day, as_of=cutoff))
        for day in decision_calendar.session_dates
        if day <= execution.session_date
    )
    revised_prefix = tuple(
        _session_semantics(session)
        for session in revision_rows
        if session.session_date <= execution.session_date
    )
    if revised_prefix != original_prefix:
        raise MarketDataError(
            "execution calendar revision cannot change the execution session or earlier history"
        )
    after = execution.session_date
    for _ in range(cash_settlement_lag_sessions(after)):
        after = revision.next_session(after, as_of=execution.open_at).session_date
    return revision, execution.open_at, revision_rows


def _session_semantics(session: AcceptedSession) -> tuple[object, ...]:
    return (
        session.session_date,
        session.open_at,
        session.close_at,
        session.exchange_timezone,
        session.exchange_id,
        session.is_early_close,
    )


def blocked_exit_from_receipt(
    receipt: ExecutionReceipt,
    context: DecisionContext,
    calendar: AcceptedSessionCalendar,
    *,
    no_fill_event: NoFillEvent,
) -> BlockedExitOrder:
    """Bind a blocked receipt to separate pre-open intent and post-open evidence."""
    if receipt.side != "sell" or receipt.filled_shares or receipt.reason not in BLOCKED_EXIT_REASONS:
        raise ValueError("receipt is not a retryable market-blocked exit")
    order = BlockedExitOrder(receipt.symbol, receipt.requested_shares,
                             context.execution_session.session_date, calendar)
    return advance_blocked_exit(
        order,
        instruction=RetryInstruction(
            decision_at=context.decision_at,
            requested_session=context.execution_session.session_date,
        ),
        no_fill_event=no_fill_event,
    )


def _inputs(
    values: tuple[ExecutionInput, ...], portfolio: Portfolio, execution: AcceptedSession,
    cutoff: datetime,
) -> dict[str, ExecutionInput]:
    if type(values) is not tuple or not values or any(not isinstance(row, ExecutionInput) for row in values):
        raise TypeError("execution_inputs must be a nonempty immutable tuple")
    rows = {row.symbol: row for row in values}
    if len(rows) != len(values) or any(
        not isinstance(symbol, str) or not symbol.strip() for symbol in rows
    ):
        raise MarketDataError("execution symbols must be unique and nonempty")
    market, action_ids = ("us" if portfolio.us_cash_settlement else "a_share"), []
    for row in values:
        if not isinstance(row.source, SourceIdentity):
            raise MarketDataError("execution source must be a SourceIdentity")
        if row.market != market:
            raise MarketDataError("execution input market mismatch")
        if row.execution_price_effective_at is None or row.execution_price_basis is None:
            raise MarketDataError("execution price effective_at and basis are required")
        effective_at = require_aware_datetime(
            row.execution_price_effective_at,
            "execution_price_effective_at",
        )
        if effective_at != execution.open_at:
            raise MarketDataError(
                "execution price effective_at must equal the accepted-session open"
        )
        confirmed_no_open = row.execution_price_basis == _NO_OPEN_EVENT_BASIS
        if confirmed_no_open:
            if row.open_price is not None:
                raise MarketDataError(
                    "confirmed no-open event basis requires open_price=None"
                )
        else:
            if row.execution_price_basis not in _EXECUTION_PRICE_BASES:
                raise MarketDataError("execution price basis is unsupported")
            if row.market == "us" and not is_positive_price(row.open_price):
                raise MarketDataError(
                    "missing US execution open requires a confirmed no-open event"
                )
            if row.source.available_at < effective_at:
                raise MarketDataError(
                    "execution price source cannot be available before its market event"
                )
            if (
                row.execution_price_basis == "timestamped_session_open"
                and row.source.available_at != effective_at
            ):
                raise MarketDataError(
                    "timestamped session-open source must be available at the market event"
                )
        if not isinstance(row.currency, str) or len(row.currency) != 3 \
                or not row.currency.isalpha() or not row.currency.isupper():
            raise MarketDataError("currency must be a three-letter uppercase code")
        if type(row.status_records) is not tuple or any(
            not isinstance(item, StatusEvidence) or item.symbol != row.symbol
            for item in row.status_records
        ):
            raise MarketDataError(
                "status_records must be immutable identities for the execution symbol"
            )
        if any(item.source.available_at > cutoff for item in row.status_records):
            raise MarketDataError(
                "status_records include future evidence unavailable at decision_at"
            )
        decision_fields = (
            row.decision_price,
            row.decision_price_source,
            row.decision_price_basis,
        )
        supplied = tuple(value is not None for value in decision_fields)
        if any(supplied) and not all(supplied):
            raise MarketDataError(
                "decision price, source, and basis must be supplied together"
            )
        if row.decision_price is not None:
            if not is_positive_price(row.decision_price):
                raise MarketDataError("decision price must be finite and positive")
            if not isinstance(row.decision_price_source, SourceIdentity):
                raise MarketDataError("decision price requires a SourceIdentity")
            if row.decision_price_source.available_at > cutoff:
                raise MarketDataError("decision price was unavailable at decision_at")
            if row.decision_price_basis not in _DECISION_PRICE_BASES:
                raise MarketDataError("decision price basis is unsupported")
        if type(row.action_types) is not tuple or row.action_types != tuple(sorted(set(row.action_types))):
            raise MarketDataError("action_types must be sorted and unique")
        if set(row.action_types) - KNOWN_ACTION_TYPES:
            raise MarketDataError("action_types contains an unknown US action")
        if set(row.action_types) & _RAW_ACTIONS:
            raise CorporateActionValuationError("ordinary action requires a rich identity")
        if type(row.is_suspended) is not bool:
            raise MarketDataError("is_suspended must be boolean")
        if row.market == "a_share" and row.limit_regime not in {"applies", "no_limit"}:
            raise MarketDataError("A-share input requires an explicit limit_regime")
        if row.market == "a_share" and row.limit_regime == "applies" and (
            row.up_limit is None or row.down_limit is None
        ):
            raise MarketDataError("applicable limit regime requires both limit fields")
        if row.market == "a_share" and row.limit_regime == "no_limit" and (
            row.up_limit is not None or row.down_limit is not None
        ):
            raise MarketDataError("no-limit regime cannot carry limit fields")
        if confirmed_no_open:
            observed_at = row.no_open_observed_at
            if (
                not isinstance(observed_at, datetime)
                or observed_at.tzinfo is None
                or observed_at.utcoffset() is None
                or observed_at.astimezone(timezone.utc) < effective_at
                or observed_at.astimezone(timezone.utc) != row.source.available_at
            ):
                raise MarketDataError(
                    "confirmed no-open event requires its post-event observation time"
                )
        elif row.no_open_observed_at is not None or row.no_open_observation_receipt is not None:
            raise MarketDataError("no-open evidence is only valid for confirmed no-open events")
        if row.market == "us" and (
            row.is_suspended
            or row.up_limit is not None
            or row.down_limit is not None
            or row.limit_regime is not None
            or row.adjustment_receipt is not None
        ):
            raise MarketDataError("A-share fields cannot be used for US inputs")
        if type(row.corporate_actions) is not tuple or any(
            not isinstance(item, CorporateActionIdentity) or item.subject_id != row.symbol
            for item in row.corporate_actions
        ):
            raise MarketDataError("corporate_actions must be immutable identities for symbol")
        current_action_ids = tuple(item.action_id for item in row.corporate_actions)
        if len(current_action_ids) != len(set(current_action_ids)):
            raise MarketDataError("action IDs must be globally unique")
        if len(current_action_ids) > 1:
            raise CorporateActionValuationError(
                "multiple same-session ordinary actions require an explicit order and unit basis"
            )
        if (
            current_action_ids
            and row.decision_price_basis != "raw_pre_action_per_old_share"
        ):
            raise CorporateActionValuationError(
                "ordinary actions require raw_pre_action_per_old_share decision prices"
            )
        action_ids.extend(item.action_id for item in row.corporate_actions)
        if row.capacity is not None and (
            not isinstance(row.capacity, CapacityObservation) or row.capacity.subject_id != row.symbol
        ):
            raise MarketDataError("capacity observation must match symbol")
        if row.terminal_action is not None:
            if not isinstance(row.terminal_action, TerminalAction):
                raise MarketDataError("terminal_action has an invalid type")
            if row.terminal_action.action_type not in row.action_types:
                raise MarketDataError("terminal action must appear in action_types")
            action_ids.append(row.terminal_action.event_id)
        if row.market == "a_share":
            _require_a_share_adjustment_receipt(row, execution, cutoff)
        if confirmed_no_open and not (
            "trading_halt" in row.action_types
            or row.terminal_action is not None
        ):
            raise MarketDataError(
                "confirmed no-open event requires a halt or terminal action identity"
            )
    if len(action_ids) != len(set(action_ids)):
        raise MarketDataError("action IDs must be globally unique")
    return rows


def _require_a_share_adjustment_receipt(
    row: ExecutionInput,
    execution: AcceptedSession,
    cutoff: datetime,
) -> None:
    receipt = row.adjustment_receipt
    if not isinstance(receipt, AShareAdjustmentReceipt):
        raise MarketDataError("A-share input requires a captured adjustment receipt")
    if receipt.subject_id != row.symbol or receipt.effective_session != execution.session_date:
        raise MarketDataError("adjustment receipt symbol or session mismatch")
    if (
        receipt.factor_source.available_at > cutoff
        or receipt.action_completeness_source.available_at > cutoff
    ):
        raise MarketDataError("adjustment evidence was unavailable at decision_at")
    expected_actions = tuple(
        sorted(
            {
                *(item.action_type for item in row.corporate_actions),
                *(
                    (row.terminal_action.action_type,)
                    if row.terminal_action is not None
                    else ()
                ),
            }
        )
    )
    if receipt.action_types != expected_actions:
        raise MarketDataError(
            "adjustment receipt action_types must exactly match executable actions"
        )
    if receipt.price_basis != "raw":
        raise MarketDataError(
            "A-share execution and portfolio accounting require raw price units"
        )
    if row.decision_price_basis is None:
        return
    if row.decision_price_basis not in {
        "raw_pre_action_per_old_share",
        "raw_execution_units",
    }:
        raise MarketDataError("raw and adjusted price bases cannot be mixed")


def _require_matching_suspension(
    rows: Mapping[str, ExecutionInput],
    decisions: Mapping[str, UniverseDecision],
) -> None:
    for symbol, row in rows.items():
        if row.market != "a_share":
            continue
        decision = decisions[symbol]
        status_suspended = "suspended" in decision.reasons
        if status_suspended != row.is_suspended:
            raise MarketDataError(
                f"{symbol} suspension status conflicts with execution input"
            )


def _terminal_checks(
    rows: Mapping[str, ExecutionInput], decisions: Mapping[str, Any],
    calendar: AcceptedSessionCalendar, execution: AcceptedSession, cutoff: datetime,
) -> None:
    zone = ZoneInfo(execution.exchange_timezone)
    for symbol, row in rows.items():
        action = row.terminal_action
        if action is None:
            continue
        if action.source.available_at > cutoff:
            raise MarketDataError("terminal action unavailable at decision_at")
        if action.effective_at > execution.open_at:
            raise MarketDataError("terminal action effective_at follows execution open")
        if action.effective_at.astimezone(zone).date() != execution.session_date:
            raise MarketDataError("terminal action effective date is not the execution session")
        settlement_sessions = action.accepted_settlement_sessions
        if action.payment_date == execution.session_date:
            if settlement_sessions:
                raise MarketDataError("same-day terminal payment cannot carry settlement sessions")
        else:
            if not settlement_sessions or settlement_sessions[-1].session_date != action.payment_date:
                raise MarketDataError(
                    "terminal payment requires accepted sessions ending on payment_date"
                )
            previous = execution
            for settlement in settlement_sessions:
                accepted = calendar.next_session(previous.session_date, as_of=cutoff)
                if settlement != accepted:
                    raise MarketDataError(
                        "terminal settlement sessions must be consecutive accepted sessions"
                    )
                previous = settlement
        if decisions[symbol].eligible:
            raise MarketDataError("terminal-action symbol must be PIT ineligible")
        successor = action.successor_symbol
        if successor and (successor not in decisions or not decisions[successor].eligible):
            raise MarketDataError("terminal successor requires an explicit eligible input")


def _actions(
    portfolio: Portfolio, rows: Mapping[str, ExecutionInput], execution: AcceptedSession,
    cutoff: datetime, receipts: list[ExecutionReceipt],
) -> None:
    for symbol in sorted(rows):
        row = rows[symbol]
        for action in sorted(row.corporate_actions, key=lambda item: item.action_id):
            if action.source.available_at > cutoff or action.effective_at > execution.open_at:
                raise MarketDataError("corporate action is late or effective after execution open")
            if action.effective_date != execution.session_date:
                raise MarketDataError("corporate action is late or effective on another session")
            before = portfolio.positions.get(symbol, Position()).shares
            if action.action_type in {"cash_dividend", "special_dividend"}:
                if action.unit != "per_share" or action.currency != row.currency:
                    raise MarketDataError("cash action has incompatible unit or currency")
                assert action.ex_date is not None and action.pay_date is not None
                cash_before, amount = portfolio.available_cash, float(action.cash_amount)
                entitlement = portfolio.apply_cash_distribution(
                    symbol, event_id=action.action_id, amount_per_share=amount,
                    ex_date=action.ex_date, pay_date=action.pay_date,
                )
                _receipt(receipts, symbol, "distribution", before, before, amount, 0, 0,
                         portfolio.available_cash - cash_before, portfolio.available_cash,
                         f"entitlement:{entitlement:.12g}")
            elif action.action_type in {"split", "reverse_split"}:
                ratio = float(action.split_ratio)
                portfolio.apply_split(symbol, ratio, event_id=action.action_id)
                after = portfolio.positions.get(symbol, Position()).shares
                _receipt(receipts, symbol, "split", before, after, ratio, 0, 0, 0,
                         portfolio.available_cash, "split_applied")
            else:
                raise CorporateActionValuationError("symbol change lacks terminal economics")
        terminal = row.terminal_action
        if terminal is None or symbol not in portfolio.positions:
            continue
        before = portfolio.positions[symbol].shares
        cash_before = portfolio.available_cash
        recovery = portfolio.apply_terminal_action(
            symbol, event_id=terminal.event_id, action_type=terminal.action_type,
            recovery_per_share=terminal.recovery_per_share,
            payment_date=terminal.payment_date,
            accepted_settlement_sessions=tuple(
                item.session_date for item in terminal.accepted_settlement_sessions
            ),
            successor_symbol=terminal.successor_symbol,
            successor_shares_per_share=terminal.successor_shares_per_share,
        )
        cash_change = portfolio.available_cash - cash_before
        reason = f"terminal_{terminal.action_type}"
        if recovery and terminal.payment_date > execution.session_date:
            reason += f"_pending_until_{terminal.payment_date.isoformat()}"
        _receipt(receipts, symbol, "terminal", before, before, terminal.recovery_per_share,
                 0, 0, cash_change, portfolio.available_cash, reason)


def _order(
    portfolio: Portfolio,
    calendar: AcceptedSessionCalendar,
    settlement_calendar: AcceptedSessionCalendar,
    settlement_as_of: datetime,
    execution: AcceptedSession,
    cutoff: datetime,
    row: ExecutionInput,
    side: str,
    requested: float,
    policy: CapacityPolicy | None, slippage_bps: float, receipts: list[ExecutionReceipt],
) -> None:
    decision = _fill(row, side, slippage_bps)
    if not decision.filled:
        _receipt(receipts, row.symbol, side, requested, 0, None, 0, 0, 0,
                 portfolio.available_cash, decision.reason)
        return
    assert decision.price is not None
    if policy is not None:
        if row.capacity is None:
            raise MarketDataError("capacity policy requires an observation")
        observed = calendar.session_on(
            row.capacity.observed_session.session_date,
            as_of=cutoff,
        )
        if observed != row.capacity.observed_session:
            raise MarketDataError("capacity observation uses a different calendar identity")
        cap = assess_capacity(row.symbol, requested, decision.price, row.currency, row.capacity,
                              policy, decision_at=cutoff, execution_session=execution)
        if not cap.allowed:
            _receipt(receipts, row.symbol, side, requested, 0, None, 0, 0, 0,
                     portfolio.available_cash, f"capacity:{cap.reason}")
            return
    filled = requested if side == "sell" else _affordable(portfolio, requested, decision.price)
    if not filled:
        _receipt(receipts, row.symbol, side, requested, 0, None, 0, 0, 0,
                 portfolio.available_cash, "insufficient_cash")
        return
    if side == "buy":
        trade = portfolio.buy(row.symbol, filled, decision.price, execution.session_date)
        reason = "partial_cash" if filled < requested else "filled"
    else:
        trade = _sell(
            portfolio,
            settlement_calendar,
            row.symbol,
            filled,
            decision.price,
            execution,
            settlement_as_of,
        )
        reason = "filled"
    _receipt(receipts, trade.symbol, trade.side, requested, trade.shares, trade.price,
             trade.costs.commission, trade.costs.sell_tax, trade.cash_change,
             portfolio.available_cash, reason)


def _weights(raw: Mapping[str, float], eligible: tuple[str, ...]) -> tuple[tuple[str, float], ...]:
    if not isinstance(raw, Mapping):
        raise TypeError("callback must return a mapping")
    items = tuple(raw.items())
    if len({symbol for symbol, _ in items}) != len(items):
        raise ValueError("target symbols must be unique")
    if any(isinstance(weight, bool) or not is_finite_number(weight) for _, weight in items):
        raise ValueError("weights must be finite numeric values")
    frozen = tuple(sorted((symbol, float(weight)) for symbol, weight in items))
    if any(symbol not in eligible for symbol, _ in frozen):
        raise MarketDataError("target symbol is not PIT eligible")
    if any(not is_finite_number(weight) or not 0 <= weight <= 1 for _, weight in frozen):
        raise ValueError("weights must be finite and in [0, 1]")
    if math.fsum(weight for _, weight in frozen) > 1 + 1e-12:
        raise ValueError("target weights cannot exceed one")
    return frozen


def _marks(portfolio: Portfolio, rows: Mapping[str, ExecutionInput]) -> dict[str, float]:
    marks: dict[str, float] = {}
    for symbol, position in portfolio.positions.items():
        if symbol not in rows:
            raise MarketDataError("holding lacks an execution input")
        row = rows[symbol]
        if row.market == "us":
            marks[symbol] = resolve_mark(
                symbol=symbol, current_price=row.open_price,
                previous_accepted_price=position.last_accepted_mark,
                action_types=row.action_types, data_qualified=True,
            )
        elif row.is_suspended and is_positive_price(position.last_accepted_mark):
            marks[symbol] = float(position.last_accepted_mark)
        else:
            marks[symbol] = _open(row)
    return marks


def _require_decision_prices(
    eligible: tuple[str, ...],
    portfolio: Portfolio,
    rows: Mapping[str, ExecutionInput],
    cutoff: datetime,
) -> None:
    required = set(eligible) | set(portfolio.positions)
    for symbol in required:
        row = rows[symbol]
        if row.decision_price is None or row.decision_price_source is None:
            raise MarketDataError(f"{symbol} lacks a qualified decision-time sizing price")
        if row.decision_price_source.available_at > cutoff:
            raise MarketDataError(f"{symbol} decision-time sizing price is late")
        _decision_price(row)


def _decision_marks(
    portfolio: Portfolio,
    rows: Mapping[str, ExecutionInput],
) -> dict[str, float]:
    return {symbol: _decision_price(rows[symbol]) for symbol in portfolio.positions}


def _fill(row: ExecutionInput, side: str, slippage: float) -> FillDecision:
    if row.market == "us":
        return us_fill(side, row.open_price, action_types=row.action_types,
                       data_qualified=True, slippage_bps=slippage)
    return a_share_fill(
        side,
        AShareBar(
            row.open_price,
            row.is_suspended,
            row.up_limit,
            row.down_limit,
            True,
            row.limit_regime,
        ),
        slippage_bps=slippage,
    )


def _open(row: ExecutionInput) -> float:
    if not is_positive_price(row.open_price):
        raise MarketDataError(f"{row.symbol} lacks a qualified positive open")
    return float(row.open_price)


def _decision_price(row: ExecutionInput) -> float:
    if not is_positive_price(row.decision_price):
        raise MarketDataError(f"{row.symbol} lacks a qualified decision-time sizing price")
    if row.decision_price_basis not in _DECISION_PRICE_BASES:
        raise MarketDataError(f"{row.symbol} lacks a supported decision price basis")
    if (
        row.corporate_actions
        and row.decision_price_basis != "raw_pre_action_per_old_share"
    ):
        raise CorporateActionValuationError(
            "ordinary actions require raw_pre_action_per_old_share decision prices"
        )
    price = float(row.decision_price)
    if row.decision_price_basis == "raw_execution_units":
        return price
    for action in sorted(row.corporate_actions, key=lambda item: item.action_id):
        if action.action_type in {"split", "reverse_split"}:
            assert action.split_ratio is not None
            price /= float(action.split_ratio)
        elif action.action_type in {"cash_dividend", "special_dividend"}:
            if action.unit != "per_share" or action.currency != row.currency:
                raise MarketDataError("cash action has incompatible unit or currency")
            assert action.cash_amount is not None
            price -= float(action.cash_amount)
        else:
            raise CorporateActionValuationError(
                "decision-time sizing cannot adjust an unsupported corporate action"
            )
        if not is_positive_price(price):
            raise MarketDataError(
                f"{row.symbol} corporate actions make the sizing price nonpositive"
            )
    return price


def _lot(shares: float, size: int) -> float:
    return float(max(0, math.floor(shares / size)) * size)


def _affordable(portfolio: Portfolio, requested: float, price: float) -> float:
    gross = max(0.0, portfolio.available_cash - portfolio.costs.minimum_commission)
    return min(requested, _lot(gross / (1 + portfolio.costs.commission_rate) / price,
                               portfolio.lot_size))


def _sell(
    portfolio: Portfolio, calendar: AcceptedSessionCalendar, symbol: str, shares: float,
    price: float, execution: AcceptedSession, cutoff: datetime,
) -> Trade:
    sessions: list[date] = []
    after = execution.session_date
    if portfolio.us_cash_settlement:
        for _ in range(cash_settlement_lag_sessions(after)):
            accepted = calendar.next_session(after, as_of=cutoff)
            sessions.append(accepted.session_date)
            after = accepted.session_date
    return portfolio.sell(symbol, shares, price, execution.session_date,
                          settlement_date=sessions[-1] if sessions else None,
                          accepted_settlement_sessions=tuple(sessions) if sessions else None)


def _receipt(
    receipts: list[ExecutionReceipt], symbol: str, side: str, requested: float, filled: float,
    price: float | None, commission: float, sell_tax: float, cash_change: float,
    cash_after: float, reason: str,
) -> None:
    receipts.append(ExecutionReceipt(len(receipts) + 1, symbol, side, float(requested),
                                     float(filled), None if price is None else float(price),
                                     float(commission), float(sell_tax), float(cash_change),
                                     float(cash_after), reason))


def _identity(
    context: DecisionContext, calendar: AcceptedSessionCalendar,
    rows: Mapping[str, ExecutionInput], portfolio: Portfolio,
    weights: tuple[tuple[str, float], ...], policy: CapacityPolicy | None,
    max_positions: int | None, slippage: float, cutoff: datetime,
    universe_members: tuple[str, ...],
    universe_snapshot: UniverseSnapshotIdentity,
    strategy_definition_sha256: str,
    strategy_adapter_sha256: str,
    execution_calendar_revision: AcceptedSessionCalendar | None,
    execution_calendar_revision_rows: tuple[AcceptedSession, ...] | None,
) -> str:
    payload = {
        "context": context,
        "calendar_identity": calendar.identity,
        "calendar": tuple(calendar.session_on(day, as_of=cutoff) for day in calendar.session_dates),
        "inputs": tuple(rows[symbol] for symbol in sorted(rows)),
        "portfolio": portfolio.__dict__,
        "weights": weights,
        "universe_members": universe_members,
        "universe_snapshot": universe_snapshot,
        "strategy_definition_sha256": strategy_definition_sha256,
        "strategy_adapter_sha256": strategy_adapter_sha256,
        "capacity_policy": policy,
        "slippage_bps": slippage,
    }
    if execution_calendar_revision is not None:
        if execution_calendar_revision_rows is None:
            raise RuntimeError("execution calendar revision rows were not prevalidated")
        payload["execution_calendar_revision_identity"] = (
            execution_calendar_revision.identity
        )
        payload["execution_calendar_revision"] = execution_calendar_revision_rows
    elif execution_calendar_revision_rows is not None:
        raise RuntimeError("execution calendar revision rows lack a revision identity")
    if max_positions is not None:
        payload["max_positions"] = max_positions
    encoded = json.dumps(_normal(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _normal(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _normal(getattr(value, item.name))
            for item in fields(value)
            if not item.name.startswith("_")
        }
    if isinstance(value, Mapping):
        return {str(key): _normal(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_normal(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_normal(item) for item in value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("input identity cannot contain nonfinite values")
    return value


def _source_receipt_hashes(*values: object) -> tuple[str, ...]:
    receipts: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, SourceIdentity):
            if value.capture_receipt_sha256 is not None:
                receipts.add(value.capture_receipt_sha256)
            return
        if is_dataclass(value) and not isinstance(value, type):
            for item in fields(value):
                if not item.name.startswith("_"):
                    visit(getattr(value, item.name))
            return
        if isinstance(value, Mapping):
            for item in value.values():
                visit(item)
            return
        if isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                visit(item)

    for value in values:
        visit(value)
    return tuple(sorted(receipts))


def _build_candidate_run_bundle(
    *,
    result: StaticRebalanceResult,
    adverse: StaticRebalanceResult,
    decision_artifact: DecisionArtifact,
    dataset_manifest: DatasetManifest,
    split_evaluation: SplitEvaluation,
    experiment_manifest: ExperimentManifest,
    candidate_run_config: CandidateRunConfig,
    cost_assumptions: ExecutionCostAssumptions,
    universe_materialization: UniverseMaterialization,
    source_receipt_sha256s: tuple[str, ...],
    base_input_identity_hash: str,
    base_receipt_hashes: tuple[str, ...],
    base_stage_hash: str,
    adverse_input_identity_hash: str,
    adverse_stage_hash: str,
    stage_context: StageContext,
) -> CandidateRunBundle:
    values = {
        "decision_artifact_sha256": decision_artifact.artifact_sha256,
        "dataset_identity_sha256": dataset_manifest.identity_sha256,
        "split_evaluation_sha256": split_evaluation.evaluation_sha256,
        "experiment_manifest_sha256": experiment_manifest.head_sha256,
        "candidate_run_config_sha256": candidate_run_config.config_sha256,
        "cost_assumptions_sha256": cost_assumptions.identity_sha256,
        "universe_materialization_sha256": (
            universe_materialization.materialization_sha256
        ),
        "source_receipt_sha256s": source_receipt_sha256s,
        "stage_plan_sha256": stage_context.plan_sha256,
        "stage_index": stage_context.stage_index,
        "stage_session": stage_context.stage_session,
        "prior_stage_hash": stage_context.prior_stage_hash,
        "base_input_identity_hash": base_input_identity_hash,
        "base_receipt_payloads": tuple(
            json.dumps(asdict(receipt), sort_keys=True, separators=(",", ":"))
            for receipt in result.receipts
        ),
        "base_receipt_hashes": base_receipt_hashes,
        "base_stage_hash": base_stage_hash,
        "adverse_input_identity_hash": adverse_input_identity_hash,
        "adverse_receipt_payloads": tuple(
            json.dumps(asdict(receipt), sort_keys=True, separators=(",", ":"))
            for receipt in adverse.receipts
        ),
        "adverse_stage_hash": adverse_stage_hash,
    }
    provisional = object.__new__(CandidateRunBundle)
    for name, value in values.items():
        object.__setattr__(provisional, name, value)
    bundle = CandidateRunBundle(
        **values,
        bundle_sha256=hashlib.sha256(
            _candidate_run_bundle_payload(provisional)
        ).hexdigest(),
    )
    bundle.verify()
    return bundle


def _hashes(
    receipts: tuple[ExecutionReceipt, ...], identity: str, context: StageContext,
) -> tuple[tuple[str, ...], str]:
    if not isinstance(context, StageContext):
        raise TypeError("hash chain requires a StageContext")
    prefix = (
        f"{context.plan_sha256}|{context.stage_index}|"
        f"{context.stage_session.isoformat()}|{context.prior_stage_hash}|{identity}"
    )
    current, hashes = hashlib.sha256(prefix.encode()).hexdigest(), []
    for receipt in receipts:
        payload = json.dumps(asdict(receipt), sort_keys=True, separators=(",", ":"))
        current = hashlib.sha256(f"{current}|{payload}".encode()).hexdigest()
        hashes.append(current)
    return tuple(hashes), current


def _sha256(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
        char not in "0123456789abcdef" for char in value
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value
