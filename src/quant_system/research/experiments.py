"""Immutable append-only experiment receipts without a control plane."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import fcntl
import json
import math
import os
from pathlib import Path
import re
from typing import Iterator, Literal

from quant_system.data import (
    SourceIdentity,
    TypedObservationReceipt,
    require_trusted_source,
    require_typed_observation,
)
from quant_system.paths import AppPaths
from quant_system.research.splits import SplitEvaluation, SplitEvaluationPlan

_SHA256 = re.compile(r"[0-9a-f]{64}")
_EVENT_TOKEN = object()
_HOLDOUT_RESULT_TOKEN = object()
_ANCHOR_TOKEN = object()
_FINAL_RUN_TOKEN = object()
EventKind = Literal["PREREGISTERED", "HOLDOUT_RESULT"]
ResultStatus = Literal["PASSED", "FAILED"]


def _sha(value: str, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(
        ord(character) < 32 for character in value
    ):
        raise ValueError(f"{field} must be stable nonempty text")
    return value.strip()


def _timestamp(value: datetime, field: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class ExperimentEvent:
    event_index: int
    kind: EventKind
    trial_id: str
    definition_sha256: str
    dataset_sha256: str
    split_sha256: str
    stage_plan_sha256: str
    split_evaluation_plan_sha256: str
    candidate_run_config_sha256: str
    parameters_json: str
    multiplicity_family_id: str
    holdout_id: str
    preregistered_at: datetime
    external_anchor_sha256: str
    external_anchor_capture_level: str
    alpha: float
    family_size: int
    prior_event_sha256: str
    event_sha256: str
    holdout_access_at: datetime | None = None
    result_sha256: str | None = None
    result_status: ResultStatus | None = None
    multiplicity_method: str | None = None
    adjusted_pvalue: float | None = None
    raw_pvalue: float | None = None
    split_evaluation_sha256: str | None = None
    final_stage_hash: str | None = None
    holdout_result_receipt_sha256: str | None = None
    _token: object | None = None

    def __post_init__(self) -> None:
        if self._token is not _EVENT_TOKEN:
            raise ValueError("experiment events must come from append entrypoints")
        if type(self.event_index) is not int or self.event_index < 0:
            raise ValueError("event_index must be nonnegative")
        _text(self.trial_id, "trial_id")
        for name in (
            "definition_sha256",
            "dataset_sha256",
            "split_sha256",
            "stage_plan_sha256",
            "split_evaluation_plan_sha256",
            "candidate_run_config_sha256",
        ):
            _sha(getattr(self, name), name)
        _sha(self.prior_event_sha256, "prior_event_sha256")
        _text(self.multiplicity_family_id, "multiplicity_family_id")
        _text(self.holdout_id, "holdout_id")
        _timestamp(self.preregistered_at, "preregistered_at")
        _sha(self.external_anchor_sha256, "external_anchor_sha256")
        if self.external_anchor_capture_level not in {
            "UNANCHORED",
            "GENERIC_CAPTURE",
            "TRANSPORT_CAPTURE",
            "PROVIDER_QUALIFIED_CAPTURE",
        }:
            raise ValueError("external anchor must be a trusted capture")
        if (
            not isinstance(self.alpha, (int, float))
            or isinstance(self.alpha, bool)
            or not 0 < float(self.alpha) < 1
        ):
            raise ValueError("alpha must be in (0, 1)")
        if type(self.family_size) is not int or self.family_size < 1:
            raise ValueError("family_size must be a positive integer")
        try:
            parameters = json.loads(self.parameters_json)
        except json.JSONDecodeError as exc:
            raise ValueError("parameters_json must be canonical JSON") from exc
        if not isinstance(parameters, dict) or json.dumps(
            parameters,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) != self.parameters_json:
            raise ValueError("parameters_json must be a canonical JSON object")
        if self.kind == "PREREGISTERED":
            if any(
                value is not None
                for value in (
                    self.holdout_access_at,
                    self.result_sha256,
                    self.result_status,
                    self.multiplicity_method,
                    self.adjusted_pvalue,
                    self.raw_pvalue,
                    self.split_evaluation_sha256,
                    self.final_stage_hash,
                    self.holdout_result_receipt_sha256,
                )
            ):
                raise ValueError("preregistration cannot contain result fields")
        elif self.kind == "HOLDOUT_RESULT":
            if self.holdout_access_at is None:
                raise ValueError("holdout result requires access time")
            _timestamp(self.holdout_access_at, "holdout_access_at")
            _sha(self.result_sha256 or "", "result_sha256")
            _sha(self.split_evaluation_sha256 or "", "split_evaluation_sha256")
            _sha(self.final_stage_hash or "", "final_stage_hash")
            _sha(
                self.holdout_result_receipt_sha256 or "",
                "holdout_result_receipt_sha256",
            )
            if self.result_status not in {"PASSED", "FAILED"}:
                raise ValueError("result_status must be PASSED or FAILED")
            _text(self.multiplicity_method or "", "multiplicity_method")
            if self.multiplicity_method not in {"holm", "bonferroni"}:
                raise ValueError("unsupported multiplicity_method")
            if (
                not isinstance(self.adjusted_pvalue, (int, float))
                or isinstance(self.adjusted_pvalue, bool)
                or not 0 <= float(self.adjusted_pvalue) <= 1
            ):
                raise ValueError("adjusted_pvalue must be in [0, 1]")
            if (
                not isinstance(self.raw_pvalue, (int, float))
                or isinstance(self.raw_pvalue, bool)
                or not 0 <= float(self.raw_pvalue) <= 1
            ):
                raise ValueError("raw_pvalue must be in [0, 1]")
            expected_status = (
                "PASSED" if float(self.adjusted_pvalue) <= float(self.alpha) else "FAILED"
            )
            if self.result_status != expected_status:
                raise ValueError("result_status must be derived from adjusted_pvalue and alpha")
            if _timestamp(self.holdout_access_at, "holdout_access_at") <= (
                self.preregistered_at
            ):
                raise ValueError("holdout access must follow preregistration")
        else:
            raise ValueError("unsupported experiment event kind")
        if hashlib.sha256(_event_payload(self)).hexdigest() != self.event_sha256:
            raise ValueError("experiment event hash mismatch")


@dataclass(frozen=True)
class HoldoutResultReceipt:
    trial_id: str
    holdout_id: str
    final_stage_hash: str
    final_run_receipt_sha256: str
    split_evaluation_sha256: str
    split_evaluation_plan_sha256: str
    return_artifact_sha256: str
    returns_sha256: str
    raw_pvalue: float
    holdout_access_at: datetime
    result_sha256: str
    receipt_sha256: str
    _token: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _HOLDOUT_RESULT_TOKEN:
            raise ValueError(
                "HoldoutResultReceipt must come from capture_holdout_result"
            )
        _text(self.trial_id, "trial_id")
        _text(self.holdout_id, "holdout_id")
        for name in (
            "final_stage_hash",
            "final_run_receipt_sha256",
            "split_evaluation_sha256",
            "split_evaluation_plan_sha256",
            "return_artifact_sha256",
            "returns_sha256",
            "result_sha256",
        ):
            _sha(getattr(self, name), name)
        _timestamp(self.holdout_access_at, "holdout_access_at")
        expected_result = hashlib.sha256(
            json.dumps(
                {
                    "final_stage_hash": self.final_stage_hash,
                    "final_run_receipt_sha256": self.final_run_receipt_sha256,
                    "return_artifact_sha256": self.return_artifact_sha256,
                    "returns_sha256": self.returns_sha256,
                    "split_evaluation_sha256": self.split_evaluation_sha256,
                    "trial_id": self.trial_id,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        if self.result_sha256 != expected_result:
            raise ValueError("holdout result identity is not derived from final artifacts")
        if hashlib.sha256(_holdout_receipt_payload(self)).hexdigest() != (
            self.receipt_sha256
        ):
            raise ValueError("holdout result receipt hash mismatch")


@dataclass(frozen=True)
class FinalRunReceipt:
    stage_plan_sha256: str
    stage_count: int
    ordered_stage_hashes: tuple[str, ...]
    ordered_portfolio_transitions: tuple[tuple[str, str], ...]
    final_stage_hash: str
    initial_portfolio_sha256: str
    final_portfolio_sha256: str
    final_nav: float
    receipt_sha256: str
    _token: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _FINAL_RUN_TOKEN:
            raise ValueError("FinalRunReceipt must come from capture_final_run_receipt")
        _sha(self.stage_plan_sha256, "stage_plan_sha256")
        if (
            type(self.stage_count) is not int
            or self.stage_count < 1
            or len(self.ordered_stage_hashes) != self.stage_count
            or len(self.ordered_portfolio_transitions) != self.stage_count
        ):
            raise ValueError("final run receipt stage count is invalid")
        for stage_hash in self.ordered_stage_hashes:
            _sha(stage_hash, "ordered_stage_hash")
        for initial_sha, final_sha in self.ordered_portfolio_transitions:
            _sha(initial_sha, "initial_portfolio_sha256")
            _sha(final_sha, "final_portfolio_sha256")
        if any(
            current[0] != previous[1]
            for previous, current in zip(
                self.ordered_portfolio_transitions,
                self.ordered_portfolio_transitions[1:],
                strict=False,
            )
        ):
            raise ValueError("final run portfolio state is discontinuous between stages")
        if self.final_stage_hash != self.ordered_stage_hashes[-1]:
            raise ValueError("final run receipt does not end at its final stage")
        if (
            self.initial_portfolio_sha256 != self.ordered_portfolio_transitions[0][0]
            or self.final_portfolio_sha256 != self.ordered_portfolio_transitions[-1][1]
        ):
            raise ValueError("final run portfolio boundary hashes are invalid")
        if (
            not isinstance(self.final_nav, (int, float))
            or isinstance(self.final_nav, bool)
            or not math.isfinite(float(self.final_nav))
        ):
            raise ValueError("final run NAV must be finite")
        if hashlib.sha256(_final_run_payload(self)).hexdigest() != self.receipt_sha256:
            raise ValueError("final run receipt hash mismatch")


def _final_run_payload(receipt: FinalRunReceipt) -> bytes:
    return json.dumps(
        {
            name: value
            for name, value in receipt.__dict__.items()
            if name not in {"receipt_sha256", "_token"}
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def capture_final_run_receipt(stage_plan: object, results: tuple[object, ...]) -> FinalRunReceipt:
    """Freeze the complete, ordered result chain for an executed StagePlan."""

    from quant_system.backtest.event_loop import ControlledStageReceipt, StagePlan

    if not isinstance(stage_plan, StagePlan):
        raise TypeError("stage_plan must be a controlled StagePlan")
    if (
        type(results) is not tuple
        or len(results) != len(stage_plan.sessions)
        or any(not isinstance(result, ControlledStageReceipt) for result in results)
    ):
        raise ValueError("final run requires one actual result for every planned stage")
    prior = "0" * 64
    for index, (session, result) in enumerate(
        zip(stage_plan.sessions, results, strict=True)
    ):
        result.verify()
        if (
            result.stage_plan_sha256 != stage_plan.plan_sha256
            or result.stage_index != index
            or result.stage_session != session
            or result.prior_stage_hash != prior
        ):
            raise ValueError("final run results are skipped, reordered, or replaced")
        if index and result.initial_portfolio_sha256 != results[index - 1].final_portfolio_sha256:
            raise ValueError("final run portfolio state is discontinuous between stages")
        prior = result.stage_hash
    values = {
        "stage_plan_sha256": stage_plan.plan_sha256,
        "stage_count": len(results),
        "ordered_stage_hashes": tuple(result.stage_hash for result in results),
        "ordered_portfolio_transitions": tuple(
            (result.initial_portfolio_sha256, result.final_portfolio_sha256)
            for result in results
        ),
        "final_stage_hash": results[-1].stage_hash,
        "initial_portfolio_sha256": results[0].initial_portfolio_sha256,
        "final_portfolio_sha256": results[-1].final_portfolio_sha256,
        "final_nav": results[-1].final_nav,
    }
    provisional = object.__new__(FinalRunReceipt)
    for name, value in values.items():
        object.__setattr__(provisional, name, value)
    return FinalRunReceipt(
        **values,
        receipt_sha256=hashlib.sha256(_final_run_payload(provisional)).hexdigest(),
        _token=_FINAL_RUN_TOKEN,
    )


@dataclass(frozen=True)
class ExperimentAnchorReceipt:
    holdout_id: str
    multiplicity_family_id: str
    family_size: int
    parameter_summary_sha256: str
    ledger_head_sha256: str
    ledger_event_count: int
    frozen_at: datetime
    source: SourceIdentity
    observation_receipt: TypedObservationReceipt
    receipt_sha256: str
    _token: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _ANCHOR_TOKEN:
            raise ValueError("experiment anchor must come from capture_family_anchor")
        _text(self.holdout_id, "holdout_id")
        _text(self.multiplicity_family_id, "multiplicity_family_id")
        if type(self.family_size) is not int or self.family_size < 1:
            raise ValueError("anchor family_size must be positive")
        _sha(self.parameter_summary_sha256, "parameter_summary_sha256")
        _sha(self.ledger_head_sha256, "ledger_head_sha256")
        if type(self.ledger_event_count) is not int or self.ledger_event_count < 1:
            raise ValueError("anchor ledger_event_count must be positive")
        frozen_at = _timestamp(self.frozen_at, "frozen_at")
        require_trusted_source(self.source)
        require_typed_observation(
            self.observation_receipt,
            source=self.source,
            observation_kind="experiment_anchor",
            subject_id=self.holdout_id,
            expected_values={
                "created_at": self.source.available_at,
                "family_size": self.family_size,
                "frozen_at": frozen_at,
                "holdout_id": self.holdout_id,
                "ledger_event_count": self.ledger_event_count,
                "ledger_head_sha256": self.ledger_head_sha256,
                "multiplicity_family_id": self.multiplicity_family_id,
                "parameter_summary_sha256": self.parameter_summary_sha256,
            },
        )
        if self.source.available_at <= frozen_at:
            raise ValueError("anchor must be published after the family freeze")
        payload = json.dumps(
            {
                "holdout_id": self.holdout_id,
                "ledger_head_sha256": self.ledger_head_sha256,
                "observation_receipt_sha256": self.observation_receipt.receipt_sha256,
                "source_capture_receipt_sha256": self.source.capture_receipt_sha256,
                "version": 1,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        if hashlib.sha256(payload).hexdigest() != self.receipt_sha256:
            raise ValueError("experiment anchor receipt hash mismatch")


def _holdout_receipt_payload(receipt: HoldoutResultReceipt) -> bytes:
    return json.dumps(
        {
            name: value.isoformat() if isinstance(value, datetime) else value
            for name, value in receipt.__dict__.items()
            if name not in {"receipt_sha256", "_token"}
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def capture_holdout_result(
    *,
    trial_id: str,
    holdout_id: str,
    final_run_receipt: FinalRunReceipt,
    split_evaluation: SplitEvaluation,
    holdout_access_at: datetime,
) -> HoldoutResultReceipt:
    if not isinstance(split_evaluation, SplitEvaluation):
        raise TypeError("split_evaluation must be a SplitEvaluation")
    split_evaluation.__post_init__()
    if not isinstance(final_run_receipt, FinalRunReceipt):
        raise TypeError("final_run_receipt must be a FinalRunReceipt")
    final_run_receipt.__post_init__()
    if (
        split_evaluation.final_run_receipt_sha256
        != final_run_receipt.receipt_sha256
    ):
        raise ValueError(
            "split evaluation returns must derive from this FinalRunReceipt"
        )
    final_stage_hash = final_run_receipt.final_stage_hash
    raw_pvalue = split_evaluation.raw_pvalue
    result_sha = hashlib.sha256(
        json.dumps(
            {
                "final_stage_hash": _sha(final_stage_hash, "final_stage_hash"),
                "final_run_receipt_sha256": final_run_receipt.receipt_sha256,
                "return_artifact_sha256": split_evaluation.return_artifact_sha256,
                "returns_sha256": split_evaluation.returns_sha256,
                "split_evaluation_sha256": split_evaluation.evaluation_sha256,
                "trial_id": _text(trial_id, "trial_id"),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    values = {
        "trial_id": trial_id,
        "holdout_id": holdout_id,
        "final_stage_hash": final_stage_hash,
        "final_run_receipt_sha256": final_run_receipt.receipt_sha256,
        "split_evaluation_sha256": split_evaluation.evaluation_sha256,
        "split_evaluation_plan_sha256": split_evaluation.plan_sha256,
        "return_artifact_sha256": split_evaluation.return_artifact_sha256,
        "returns_sha256": split_evaluation.returns_sha256,
        "raw_pvalue": raw_pvalue,
        "holdout_access_at": _timestamp(holdout_access_at, "holdout_access_at"),
        "result_sha256": result_sha,
    }
    provisional = object.__new__(HoldoutResultReceipt)
    for name, value in values.items():
        object.__setattr__(provisional, name, value)
    return HoldoutResultReceipt(
        **values,
        receipt_sha256=hashlib.sha256(_holdout_receipt_payload(provisional)).hexdigest(),
        _token=_HOLDOUT_RESULT_TOKEN,
    )


def _event_payload(event: ExperimentEvent) -> bytes:
    payload = {
        name: value.astimezone(timezone.utc).isoformat()
        if isinstance(value, datetime)
        else value
        for name, value in event.__dict__.items()
        if name not in {"event_sha256", "_token"}
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _event(**values: object) -> ExperimentEvent:
    provisional = object.__new__(ExperimentEvent)
    for name, value in values.items():
        object.__setattr__(provisional, name, value)
    digest = hashlib.sha256(_event_payload(provisional)).hexdigest()
    return ExperimentEvent(**values, event_sha256=digest, _token=_EVENT_TOKEN)


def _validate_chain(events: tuple[ExperimentEvent, ...]) -> None:
    prior = "0" * 64
    for index, event in enumerate(events):
        if not isinstance(event, ExperimentEvent):
            raise ValueError("experiment chain contains an invalid event")
        if event.event_index != index or event.prior_event_sha256 != prior:
            raise ValueError("experiment event chain is incomplete or reordered")
        prior = event.event_sha256


def preregister_trial(
    events: tuple[ExperimentEvent, ...],
    *,
    trial_id: str,
    definition_sha256: str,
    dataset_sha256: str,
    split_sha256: str,
    stage_plan_sha256: str,
    split_evaluation_plan: SplitEvaluationPlan,
    candidate_run_config_sha256: str,
    parameters: Mapping[str, object],
    multiplicity_family_id: str,
    holdout_id: str,
    preregistered_at: datetime,
    alpha: float,
    family_size: int,
) -> tuple[ExperimentEvent, ...]:
    _validate_chain(events)
    preregistered = _timestamp(preregistered_at, "preregistered_at")
    if not isinstance(split_evaluation_plan, SplitEvaluationPlan):
        raise TypeError("split_evaluation_plan must be a controlled plan")
    split_evaluation_plan.__post_init__()
    if (
        split_evaluation_plan.preregistered_at.astimezone(timezone.utc)
        != preregistered
        or split_evaluation_plan.holdout_id != holdout_id
        or split_evaluation_plan.manifest_sha256 != split_sha256
    ):
        raise ValueError(
            "split evaluation plan must be frozen for this holdout before access"
        )
    if any(event.trial_id == trial_id for event in events):
        raise ValueError("trial_id is already present in the append-only chain")
    holdout_events = tuple(event for event in events if event.holdout_id == holdout_id)
    if any(event.kind == "HOLDOUT_RESULT" for event in holdout_events):
        raise ValueError("holdout family cannot be extended after holdout access")
    if any(
        event.multiplicity_family_id != multiplicity_family_id
        for event in holdout_events
    ):
        raise ValueError("one holdout_id must use one frozen multiplicity family")
    split_scope = tuple(
        event
        for event in events
        if event.kind == "PREREGISTERED"
        and event.dataset_sha256 == dataset_sha256
        and event.split_sha256 == split_sha256
    )
    if any(
        event.holdout_id != holdout_id
        or event.multiplicity_family_id != multiplicity_family_id
        for event in split_scope
    ):
        raise ValueError("one frozen dataset split must use one holdout family")
    family = tuple(
        event
        for event in events
        if event.kind == "PREREGISTERED"
        and event.multiplicity_family_id == multiplicity_family_id
    )
    if len(family) >= family_size:
        raise ValueError("multiplicity family already contains its preregistered size")
    if family and any(
        event.family_size != family_size
        or event.alpha != alpha
        or event.holdout_id != holdout_id
        or event.split_evaluation_plan_sha256 != split_evaluation_plan.plan_sha256
        or event.candidate_run_config_sha256 != candidate_run_config_sha256
        for event in family
    ):
        raise ValueError("multiplicity family preregistration contract changed")
    try:
        parameters_json = json.dumps(
            dict(parameters),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("parameters must be canonically serializable") from exc
    prior = events[-1].event_sha256 if events else "0" * 64
    return events + (
        _event(
            event_index=len(events),
            kind="PREREGISTERED",
            trial_id=_text(trial_id, "trial_id"),
            definition_sha256=_sha(definition_sha256, "definition_sha256"),
            dataset_sha256=_sha(dataset_sha256, "dataset_sha256"),
            split_sha256=_sha(split_sha256, "split_sha256"),
            stage_plan_sha256=_sha(stage_plan_sha256, "stage_plan_sha256"),
            split_evaluation_plan_sha256=_sha(
                split_evaluation_plan.plan_sha256,
                "split_evaluation_plan_sha256",
            ),
            candidate_run_config_sha256=_sha(
                candidate_run_config_sha256,
                "candidate_run_config_sha256",
            ),
            parameters_json=parameters_json,
            multiplicity_family_id=_text(
                multiplicity_family_id,
                "multiplicity_family_id",
            ),
            holdout_id=_text(holdout_id, "holdout_id"),
            preregistered_at=preregistered,
            external_anchor_sha256="0" * 64,
            external_anchor_capture_level="UNANCHORED",
            alpha=alpha,
            family_size=family_size,
            prior_event_sha256=prior,
            holdout_access_at=None,
            result_sha256=None,
            result_status=None,
            multiplicity_method=None,
            adjusted_pvalue=None,
            raw_pvalue=None,
            split_evaluation_sha256=None,
            final_stage_hash=None,
            holdout_result_receipt_sha256=None,
        ),
    )


def _family_parameter_summary(events: tuple[ExperimentEvent, ...]) -> str:
    return hashlib.sha256(
        json.dumps(
            tuple(
                {
                    "definition_sha256": event.definition_sha256,
                    "parameters_json": event.parameters_json,
                    "trial_id": event.trial_id,
                }
                for event in sorted(events, key=lambda item: item.trial_id)
            ),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def record_holdout_family_results(
    events: tuple[ExperimentEvent, ...],
    *,
    receipts: tuple[HoldoutResultReceipt, ...],
    multiplicity_method: str,
    anchor: ExperimentAnchorReceipt,
) -> tuple[ExperimentEvent, ...]:
    _validate_chain(events)
    if multiplicity_method not in {"holm", "bonferroni"}:
        raise ValueError("unsupported multiplicity_method")
    if not receipts or any(
        not isinstance(receipt, HoldoutResultReceipt) for receipt in receipts
    ):
        raise ValueError("holdout receipts must be a nonempty immutable tuple")
    for receipt in receipts:
        receipt.__post_init__()
    holdout_ids = {receipt.holdout_id for receipt in receipts}
    if len(holdout_ids) != 1:
        raise ValueError("one result batch must cover one holdout_id")
    holdout_id = next(iter(holdout_ids))
    if not isinstance(anchor, ExperimentAnchorReceipt):
        raise ValueError("holdout results require a typed family anchor")
    anchor.__post_init__()
    if anchor.holdout_id != holdout_id:
        raise ValueError("family anchor does not bind this holdout")
    preregistrations = tuple(
        event
        for event in events
        if event.kind == "PREREGISTERED" and event.holdout_id == holdout_id
    )
    if not preregistrations:
        raise ValueError("holdout result requires a preregistered family")
    family_size = preregistrations[0].family_size
    if (
        len(preregistrations) != family_size
        or len(receipts) != family_size
        or {event.trial_id for event in preregistrations}
        != {receipt.trial_id for receipt in receipts}
    ):
        raise ValueError("holdout result batch must cover the complete frozen family")
    if (
        anchor.family_size != family_size
        or anchor.multiplicity_family_id
        != preregistrations[0].multiplicity_family_id
        or anchor.ledger_head_sha256 != preregistrations[-1].event_sha256
        or anchor.ledger_event_count != len(events)
        or anchor.parameter_summary_sha256
        != _family_parameter_summary(preregistrations)
        or any(receipt.holdout_access_at <= anchor.source.available_at for receipt in receipts)
    ):
        raise ValueError("family anchor does not commit the frozen preregistration head")
    if any(
        event.kind == "HOLDOUT_RESULT" and event.holdout_id == holdout_id
        for event in events
    ):
        raise ValueError("holdout family has already been recorded")
    trials = {event.trial_id: event for event in preregistrations}
    raw = {receipt.trial_id: receipt.raw_pvalue for receipt in receipts}
    if multiplicity_method == "bonferroni":
        adjusted = {
            trial_id: min(1.0, pvalue * family_size)
            for trial_id, pvalue in raw.items()
        }
    else:
        adjusted = {}
        running = 0.0
        for index, (trial_id, pvalue) in enumerate(
            sorted(raw.items(), key=lambda item: (item[1], item[0]))
        ):
            running = max(running, (family_size - index) * pvalue)
            adjusted[trial_id] = min(1.0, running)
    chain = events
    for receipt in sorted(receipts, key=lambda item: item.trial_id):
        trial = trials[receipt.trial_id]
        if (
            receipt.split_evaluation_plan_sha256
            != trial.split_evaluation_plan_sha256
            or receipt.holdout_access_at <= trial.preregistered_at
        ):
            raise ValueError("holdout receipt violates the preregistered plan or time")
        adjusted_pvalue = adjusted[receipt.trial_id]
        chain = chain + (
            _event(
            event_index=len(chain),
            kind="HOLDOUT_RESULT",
            trial_id=trial.trial_id,
            definition_sha256=trial.definition_sha256,
            dataset_sha256=trial.dataset_sha256,
            split_sha256=trial.split_sha256,
            stage_plan_sha256=trial.stage_plan_sha256,
            split_evaluation_plan_sha256=trial.split_evaluation_plan_sha256,
            candidate_run_config_sha256=trial.candidate_run_config_sha256,
            parameters_json=trial.parameters_json,
            multiplicity_family_id=trial.multiplicity_family_id,
            holdout_id=trial.holdout_id,
            preregistered_at=trial.preregistered_at,
            external_anchor_sha256=anchor.receipt_sha256,
            external_anchor_capture_level=anchor.source.capture_level,
            alpha=trial.alpha,
            family_size=trial.family_size,
            prior_event_sha256=chain[-1].event_sha256,
            holdout_access_at=receipt.holdout_access_at,
            result_sha256=receipt.result_sha256,
            result_status=(
                "PASSED" if adjusted_pvalue <= float(trial.alpha) else "FAILED"
            ),
            multiplicity_method=_text(multiplicity_method, "multiplicity_method"),
            adjusted_pvalue=adjusted_pvalue,
            raw_pvalue=receipt.raw_pvalue,
            split_evaluation_sha256=receipt.split_evaluation_sha256,
            final_stage_hash=receipt.final_stage_hash,
            holdout_result_receipt_sha256=receipt.receipt_sha256,
            ),
        )
    return chain


def record_holdout_result(
    events: tuple[ExperimentEvent, ...],
    *,
    receipt: HoldoutResultReceipt,
    multiplicity_method: str,
    anchor: ExperimentAnchorReceipt,
) -> tuple[ExperimentEvent, ...]:
    """Record a single-member family; multi-trial families use the batch entrypoint."""

    return record_holdout_family_results(
        events,
        receipts=(receipt,),
        multiplicity_method=multiplicity_method,
        anchor=anchor,
    )


@dataclass(frozen=True)
class ExperimentManifest:
    event_count: int
    ordered_event_sha256s: tuple[str, ...]
    head_sha256: str


def freeze_experiment_manifest(events: tuple[ExperimentEvent, ...]) -> ExperimentManifest:
    _validate_chain(events)
    hashes = tuple(event.event_sha256 for event in events)
    return ExperimentManifest(len(events), hashes, hashes[-1] if hashes else "0" * 64)


def verify_experiment_manifest(
    manifest: ExperimentManifest,
    events: tuple[ExperimentEvent, ...],
) -> None:
    _validate_chain(events)
    observed = freeze_experiment_manifest(events)
    if observed != manifest:
        raise ValueError("experiment manifest is incomplete, deleted, or reordered")


def require_adjusted_holdout_for_candidate(
    event: ExperimentEvent,
    *,
    receipt: HoldoutResultReceipt,
    manifest: ExperimentManifest,
    events: tuple[ExperimentEvent, ...],
    anchor: ExperimentAnchorReceipt,
) -> None:
    verify_experiment_manifest(manifest, events)
    if not isinstance(event, ExperimentEvent) or event.kind != "HOLDOUT_RESULT":
        raise ValueError("candidate evidence requires a holdout result event")
    if event not in events:
        raise ValueError("candidate holdout event is absent from the frozen manifest")
    if event.result_status != "PASSED":
        raise ValueError("candidate evidence requires a PASSED holdout result")
    if not isinstance(receipt, HoldoutResultReceipt):
        raise ValueError("candidate evidence requires a typed holdout result receipt")
    receipt.__post_init__()
    if not isinstance(anchor, ExperimentAnchorReceipt):
        raise ValueError("candidate evidence requires the typed family anchor")
    anchor.__post_init__()
    if (
        anchor.receipt_sha256 != event.external_anchor_sha256
        or anchor.source.capture_level != event.external_anchor_capture_level
        or anchor.source.available_at >= receipt.holdout_access_at
    ):
        raise ValueError("candidate holdout event does not bind its family anchor")
    if (
        receipt.trial_id != event.trial_id
        or receipt.holdout_id != event.holdout_id
        or receipt.receipt_sha256 != event.holdout_result_receipt_sha256
        or receipt.result_sha256 != event.result_sha256
        or receipt.raw_pvalue != event.raw_pvalue
        or receipt.split_evaluation_sha256 != event.split_evaluation_sha256
        or receipt.final_stage_hash != event.final_stage_hash
    ):
        raise ValueError("holdout result event does not bind its typed receipt")
    if (
        event.multiplicity_method not in {"holm", "bonferroni"}
        or event.adjusted_pvalue is None
        or event.adjusted_pvalue > event.alpha
    ):
        raise ValueError("candidate evidence requires multiplicity adjustment")
    preregistrations = tuple(
        item
        for item in events
        if item.kind == "PREREGISTERED"
        and item.multiplicity_family_id == event.multiplicity_family_id
    )
    results = tuple(
        item
        for item in events
        if item.kind == "HOLDOUT_RESULT"
        and item.multiplicity_family_id == event.multiplicity_family_id
    )
    if (
        len(preregistrations) != event.family_size
        or len(results) != event.family_size
        or {item.trial_id for item in preregistrations}
        != {item.trial_id for item in results}
        or any(item.multiplicity_method != event.multiplicity_method for item in results)
    ):
        raise ValueError("candidate evidence requires a complete multiplicity family")
    raw = {item.trial_id: float(item.raw_pvalue) for item in results}
    if event.multiplicity_method == "bonferroni":
        expected = {
            trial_id: min(1.0, pvalue * event.family_size)
            for trial_id, pvalue in raw.items()
        }
    else:
        expected = {}
        running = 0.0
        for index, (trial_id, pvalue) in enumerate(
            sorted(raw.items(), key=lambda item: (item[1], item[0]))
        ):
            running = max(running, (event.family_size - index) * pvalue)
            expected[trial_id] = min(1.0, running)
    if any(
        abs(float(item.adjusted_pvalue) - expected[item.trial_id]) > 1e-12
        for item in results
    ):
        raise ValueError("candidate multiplicity adjustment is not recomputable")


@dataclass(frozen=True)
class ExperimentLedgerReceipt:
    path: Path
    data_root_sha256: str
    event_count: int
    head_sha256: str
    bytes_sha256: str
    _token: object | None = field(default=None, repr=False, compare=False)

    def verify_current_bytes(self) -> None:
        if self._token is not _LEDGER_TOKEN:
            raise ValueError("experiment ledger receipt must come from persist entrypoint")
        paths = AppPaths.discover()
        if not paths.data_root_bound:
            raise ValueError("experiment ledger requires an explicit QUANT_DATA_ROOT")
        expected_path = paths.data_root / "research" / "experiment_ledger.ndjson"
        if (
            self.path != expected_path
            or self.data_root_sha256
            != hashlib.sha256(str(paths.data_root).encode()).hexdigest()
        ):
            raise ValueError("experiment ledger is not bound to the configured AppPaths")
        payload = self.path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != self.bytes_sha256:
            raise ValueError("persistent experiment ledger bytes changed")


_LEDGER_TOKEN = object()


@contextmanager
def _canonical_ledger_lock(path: Path) -> Iterator[None]:
    lock_path = path.with_suffix(path.suffix + ".lock")
    descriptor = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0),
        0o600,
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def persist_experiment_ledger(
    events: tuple[ExperimentEvent, ...],
) -> ExperimentLedgerReceipt:
    """Append to the one canonical ledger beneath the configured data root."""

    _validate_chain(events)
    if not events:
        raise ValueError("persistent experiment ledger requires at least one event")
    paths = AppPaths.discover()
    if not paths.data_root_bound:
        raise ValueError("experiment ledger requires an explicit QUANT_DATA_ROOT")
    candidate = paths.data_root / "research" / "experiment_ledger.ndjson"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    expected_lines = tuple(
        json.dumps(
            {"event_index": event.event_index, "event_sha256": event.event_sha256},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        + b"\n"
        for event in events
    )
    with _canonical_ledger_lock(candidate):
        existing = candidate.read_bytes() if candidate.exists() else b""
        existing_lines = tuple(existing.splitlines(keepends=True))
        if existing_lines != expected_lines[: len(existing_lines)]:
            raise ValueError("persistent experiment ledger prefix is missing or changed")
        if len(existing_lines) > len(expected_lines):
            raise ValueError("persistent experiment ledger is ahead of supplied chain")
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(candidate, flags, 0o600)
        try:
            for line in expected_lines[len(existing_lines) :]:
                os.write(descriptor, line)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        payload = candidate.read_bytes()
    return ExperimentLedgerReceipt(
        candidate,
        hashlib.sha256(str(paths.data_root).encode()).hexdigest(),
        len(events),
        events[-1].event_sha256,
        hashlib.sha256(payload).hexdigest(),
        _LEDGER_TOKEN,
    )


def capture_family_anchor(
    events: tuple[ExperimentEvent, ...],
    *,
    holdout_id: str,
    ledger_receipt: ExperimentLedgerReceipt,
    observation_receipt: TypedObservationReceipt,
) -> ExperimentAnchorReceipt:
    """Verify a post-freeze external commitment to the canonical ledger head."""

    _validate_chain(events)
    if not isinstance(ledger_receipt, ExperimentLedgerReceipt):
        raise ValueError("family anchor requires the canonical ledger receipt")
    ledger_receipt.verify_current_bytes()
    if (
        ledger_receipt.path.name != "experiment_ledger.ndjson"
        or ledger_receipt.path.parent.name != "research"
        or ledger_receipt.event_count != len(events)
        or ledger_receipt.head_sha256 != events[-1].event_sha256
    ):
        raise ValueError("family anchor ledger is not the canonical frozen head")
    family = tuple(
        event
        for event in events
        if event.kind == "PREREGISTERED" and event.holdout_id == holdout_id
    )
    if not family or len(family) != family[0].family_size:
        raise ValueError("family must be complete before it can be anchored")
    if not isinstance(observation_receipt, TypedObservationReceipt):
        raise ValueError("family anchor requires a typed observation")
    frozen_at = max(event.preregistered_at for event in family)
    source = observation_receipt.source
    values = {
        "holdout_id": _text(holdout_id, "holdout_id"),
        "multiplicity_family_id": family[0].multiplicity_family_id,
        "family_size": len(family),
        "parameter_summary_sha256": _family_parameter_summary(family),
        "ledger_head_sha256": ledger_receipt.head_sha256,
        "ledger_event_count": ledger_receipt.event_count,
        "frozen_at": frozen_at,
        "source": source,
        "observation_receipt": observation_receipt,
    }
    payload = json.dumps(
        {
            "holdout_id": holdout_id,
            "ledger_head_sha256": ledger_receipt.head_sha256,
            "observation_receipt_sha256": observation_receipt.receipt_sha256,
            "source_capture_receipt_sha256": source.capture_receipt_sha256,
            "version": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return ExperimentAnchorReceipt(
        **values,
        receipt_sha256=hashlib.sha256(payload).hexdigest(),
        _token=_ANCHOR_TOKEN,
    )
