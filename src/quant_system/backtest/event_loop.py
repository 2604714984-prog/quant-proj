"""One deterministic, point-in-time next-session rebalance."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass, field, fields, is_dataclass, replace
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from quant_system.data import (
    AcceptedSession, AcceptedSessionCalendar, CalendarIdentityError,
    CorporateActionIdentity, SourceIdentity, capture_file_digest,
    require_trusted_source,
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
from .blocked_orders import (
    BLOCKED_EXIT_REASONS,
    BlockedExitOrder,
    RetryDecision,
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


@dataclass(frozen=True)
class TerminalAction:
    event_id: str
    action_type: str
    effective_at: datetime
    recovery_per_share: float
    source: SourceIdentity
    successor_symbol: str | None = None
    successor_shares_per_share: float | None = None

    def __post_init__(self) -> None:
        require_nonempty_text(self.event_id, "event_id")
        require_aware_datetime(self.effective_at, "effective_at")
        if self.action_type not in TERMINAL_ACTION_TYPES:
            raise MarketDataError("unsupported terminal action_type")
        if not is_finite_number(self.recovery_per_share) or self.recovery_per_share < 0:
            raise MarketDataError("recovery_per_share must be finite and nonnegative")
        if not isinstance(self.source, SourceIdentity):
            raise MarketDataError("terminal action requires a SourceIdentity")


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
    interface_grade: str = "UNTRUSTED_EXPERIMENT"
    decision_artifact_sha256: str | None = None
    dataset_identity_sha256: str | None = None
    split_identity_sha256: str | None = None
    cost_assumptions_sha256: str | None = None
    adverse_input_identity_hash: str | None = None
    adverse_stage_hash: str | None = None
    adverse_final_nav: float | None = None
    base_fx_adjusted_final_nav: float | None = None
    adverse_fx_adjusted_final_nav: float | None = None
    strategy_candidate_available: bool = False


@dataclass(frozen=True)
class DecisionArtifact:
    """Frozen weights and actual strategy/data bytes for the controlled interface."""

    weights: tuple[tuple[str, float], ...]
    feature_snapshot_sha256: str
    strategy_definition_sha256: str
    strategy_adapter_sha256: str
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
        "split_identity_sha256": artifact.split_identity_sha256,
        "strategy_adapter_sha256": artifact.strategy_adapter_sha256,
        "strategy_definition_sha256": artifact.strategy_definition_sha256,
        "version": 1,
        "weights": artifact.weights,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def capture_decision_artifact(
    *,
    weights: Mapping[str, float],
    feature_snapshot_path: Path,
    strategy_definition_path: Path,
    strategy_adapter_path: Path,
    decision_at: datetime,
    dataset_identity_sha256: str,
    split_identity_sha256: str,
) -> DecisionArtifact:
    """Capture actual feature, definition, and adapter bytes into one decision receipt."""

    symbols = tuple(sorted(weights))
    frozen = _weights(weights, symbols)
    feature_sha = capture_file_digest(feature_snapshot_path)[0]
    definition_sha = capture_file_digest(strategy_definition_path)[0]
    adapter_sha = capture_file_digest(strategy_adapter_path)[0]
    provisional = object.__new__(DecisionArtifact)
    values = {
        "weights": frozen,
        "feature_snapshot_sha256": feature_sha,
        "strategy_definition_sha256": definition_sha,
        "strategy_adapter_sha256": adapter_sha,
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
    capacity_policy: CapacityPolicy | None = None,
    max_positions: int | None = None,
    slippage_bps: float = 0.0,
    prior_stage_hash: str = "0" * 64,
) -> StaticRebalanceResult:
    """Run an experimental callable-based rebalance on a copy.

    The returned interface grade is always ``UNTRUSTED_EXPERIMENT``. Use
    ``run_candidate_rebalance`` for a controlled, non-callable decision input.
    """
    if not isinstance(portfolio, Portfolio) or not isinstance(calendar, AcceptedSessionCalendar):
        raise TypeError("portfolio and calendar have invalid types")
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
    _terminal_checks(rows, decisions, execution, cutoff)
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
    receipt_hashes, stage_hash = _hashes(tuple(receipts), identity, prior_stage_hash)
    return StaticRebalanceResult(working, context, weights, tuple(receipts), identity,
                                 receipt_hashes, stage_hash, final_nav,
                                 definition_sha, adapter_sha)


def run_candidate_rebalance(
    portfolio: Portfolio,
    calendar: AcceptedSessionCalendar,
    *,
    signal_session: date,
    decision_at: datetime,
    execution_inputs: tuple[ExecutionInput, ...],
    universe_materialization: UniverseMaterialization,
    decision_artifact: DecisionArtifact,
    cost_assumptions: ExecutionCostAssumptions,
    execution_calendar_revision: AcceptedSessionCalendar | None = None,
    max_positions: int | None = None,
    prior_stage_hash: str = "0" * 64,
) -> StaticRebalanceResult:
    """Run the controlled interface from frozen weights and captured bytes only."""

    if not isinstance(decision_artifact, DecisionArtifact):
        raise TypeError("decision_artifact must be a captured DecisionArtifact")
    if not isinstance(universe_materialization, UniverseMaterialization):
        raise TypeError(
            "universe_materialization must come from materialize_universe_partition"
        )
    if not isinstance(cost_assumptions, ExecutionCostAssumptions):
        raise TypeError("cost_assumptions must be ExecutionCostAssumptions")
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
    _require_candidate_sources(
        calendar,
        execution_inputs,
        universe_snapshot,
        cutoff,
        execution_calendar_revision,
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
        "prior_stage_hash": prior_stage_hash,
    }
    base_portfolio = portfolio
    if cost_assumptions.gross_only:
        base_portfolio = deepcopy(portfolio)
        base_portfolio.costs = cost_assumptions.base.transaction_cost_model()
        base_portfolio.a_share_stamp_tax_schedule = False
    result = run_static_rebalance(
        base_portfolio,
        calendar,
        slippage_bps=cost_assumptions.base.slippage_bps,
        **common,
    )
    adverse_portfolio = deepcopy(base_portfolio)
    adverse_portfolio.costs = cost_assumptions.adverse.transaction_cost_model()
    adverse = run_static_rebalance(
        adverse_portfolio,
        calendar,
        slippage_bps=cost_assumptions.adverse.slippage_bps,
        **common,
    )
    assumption_sha = cost_assumptions.identity_sha256
    candidate_identity = hashlib.sha256(
        f"{result.input_identity_hash}|{assumption_sha}|base".encode()
    ).hexdigest()
    receipt_hashes, stage_hash = _hashes(
        result.receipts,
        candidate_identity,
        prior_stage_hash,
    )
    adverse_identity = hashlib.sha256(
        f"{adverse.input_identity_hash}|{assumption_sha}|adverse".encode()
    ).hexdigest()
    _, adverse_stage_hash = _hashes(
        adverse.receipts,
        adverse_identity,
        prior_stage_hash,
    )
    return replace(
        result,
        input_identity_hash=candidate_identity,
        receipt_hashes=receipt_hashes,
        stage_hash=stage_hash,
        interface_grade=(
            "GROSS_ONLY_EXPERIMENT"
            if cost_assumptions.gross_only
            else "CONTROLLED_CANDIDATE_INPUT"
        ),
        decision_artifact_sha256=decision_artifact.artifact_sha256,
        dataset_identity_sha256=decision_artifact.dataset_identity_sha256,
        split_identity_sha256=decision_artifact.split_identity_sha256,
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


def _require_candidate_sources(
    calendar: AcceptedSessionCalendar,
    execution_inputs: tuple[ExecutionInput, ...],
    universe_snapshot: UniverseSnapshotIdentity,
    cutoff: datetime,
    execution_calendar_revision: AcceptedSessionCalendar | None,
) -> None:
    require_trusted_source(calendar.identity.source_identity)
    for day in calendar.session_dates:
        require_trusted_source(calendar.session_on(day, as_of=cutoff).source)
    require_trusted_source(universe_snapshot.source_identity)
    if execution_calendar_revision is not None:
        require_trusted_source(execution_calendar_revision.identity.source_identity)
    for row in execution_inputs:
        require_trusted_source(row.source)
        if row.decision_price_source is not None:
            require_trusted_source(row.decision_price_source)
        for status in row.status_records:
            require_trusted_source(status.source)
        for action in row.corporate_actions:
            require_trusted_source(action.source)
        if row.capacity is not None:
            require_trusted_source(row.capacity.source)
        if row.adjustment_receipt is not None:
            require_trusted_source(row.adjustment_receipt.factor_source)
            require_trusted_source(row.adjustment_receipt.action_completeness_source)
        if row.terminal_action is not None:
            require_trusted_source(row.terminal_action.source)


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
) -> BlockedExitOrder:
    """Turn a market-blocked sell into the existing multi-session retry object."""
    if receipt.side != "sell" or receipt.filled_shares or receipt.reason not in BLOCKED_EXIT_REASONS:
        raise ValueError("receipt is not a retryable market-blocked exit")
    order = BlockedExitOrder(receipt.symbol, receipt.requested_shares,
                             context.execution_session.session_date, calendar)
    return advance_blocked_exit(
        order,
        decision=RetryDecision(
            decision_at=context.decision_at,
            requested_session=context.execution_session.session_date,
            reason=receipt.reason,
        ),
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
            if row.market != "us":
                raise MarketDataError("confirmed no-open events are US-only")
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
        if row.market == "a_share":
            _require_a_share_adjustment_receipt(row, execution, cutoff)
        if row.market == "a_share" and (row.action_types or row.corporate_actions
                                        or row.terminal_action is not None):
            raise MarketDataError("US action fields cannot be used for A-share inputs")
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
    expected_basis = {
        "qfq": "adjusted_qfq",
        "hfq": "adjusted_hfq",
        "total_return": "adjusted_total_return",
    }.get(receipt.price_basis)
    if row.decision_price_basis is None:
        return
    if expected_basis is None:
        if row.decision_price_basis not in {
            "raw_pre_action_per_old_share",
            "raw_execution_units",
        }:
            raise MarketDataError("raw and adjusted price bases cannot be mixed")
    elif row.decision_price_basis != expected_basis:
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
    execution: AcceptedSession, cutoff: datetime,
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
        recovery = portfolio.apply_terminal_action(
            symbol, event_id=terminal.event_id, action_type=terminal.action_type,
            recovery_per_share=terminal.recovery_per_share,
            successor_symbol=terminal.successor_symbol,
            successor_shares_per_share=terminal.successor_shares_per_share,
        )
        _receipt(receipts, symbol, "terminal", before, before, terminal.recovery_per_share,
                 0, 0, recovery, portfolio.available_cash, f"terminal_{terminal.action_type}")


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


def _hashes(
    receipts: tuple[ExecutionReceipt, ...], identity: str, prior: str,
) -> tuple[tuple[str, ...], str]:
    if len(prior) != 64 or any(char not in "0123456789abcdef" for char in prior):
        raise ValueError("prior_stage_hash must be a lowercase SHA-256 digest")
    current, hashes = hashlib.sha256(f"{prior}|{identity}".encode()).hexdigest(), []
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
