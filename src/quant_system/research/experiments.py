"""Immutable append-only experiment receipts without a control plane."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Literal

_SHA256 = re.compile(r"[0-9a-f]{64}")
_EVENT_TOKEN = object()
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
    parameters_json: str
    multiplicity_family_id: str
    preregistered_at: datetime
    external_anchor_sha256: str
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
        ):
            _sha(getattr(self, name), name)
        _sha(self.prior_event_sha256, "prior_event_sha256")
        _text(self.multiplicity_family_id, "multiplicity_family_id")
        _timestamp(self.preregistered_at, "preregistered_at")
        _sha(self.external_anchor_sha256, "external_anchor_sha256")
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
                )
            ):
                raise ValueError("preregistration cannot contain result fields")
        elif self.kind == "HOLDOUT_RESULT":
            if self.holdout_access_at is None:
                raise ValueError("holdout result requires access time")
            _timestamp(self.holdout_access_at, "holdout_access_at")
            _sha(self.result_sha256 or "", "result_sha256")
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
    parameters: Mapping[str, object],
    multiplicity_family_id: str,
    preregistered_at: datetime,
    external_anchor_sha256: str,
    alpha: float,
    family_size: int,
) -> tuple[ExperimentEvent, ...]:
    _validate_chain(events)
    if any(event.trial_id == trial_id for event in events):
        raise ValueError("trial_id is already present in the append-only chain")
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
        or event.external_anchor_sha256 != external_anchor_sha256
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
            parameters_json=parameters_json,
            multiplicity_family_id=_text(
                multiplicity_family_id,
                "multiplicity_family_id",
            ),
            preregistered_at=_timestamp(preregistered_at, "preregistered_at"),
            external_anchor_sha256=_sha(
                external_anchor_sha256,
                "external_anchor_sha256",
            ),
            alpha=alpha,
            family_size=family_size,
            prior_event_sha256=prior,
            holdout_access_at=None,
            result_sha256=None,
            result_status=None,
            multiplicity_method=None,
            adjusted_pvalue=None,
            raw_pvalue=None,
        ),
    )


def record_holdout_result(
    events: tuple[ExperimentEvent, ...],
    *,
    trial_id: str,
    holdout_access_at: datetime,
    result_sha256: str,
    result_status: ResultStatus,
    multiplicity_method: str,
    raw_pvalue: float,
    adjusted_pvalue: float,
) -> tuple[ExperimentEvent, ...]:
    _validate_chain(events)
    if any(
        event.kind == "HOLDOUT_RESULT" and event.trial_id == trial_id
        for event in events
    ):
        raise ValueError("trial holdout has already been recorded")
    preregistrations = tuple(
        event
        for event in events
        if event.kind == "PREREGISTERED" and event.trial_id == trial_id
    )
    if len(preregistrations) != 1:
        raise ValueError("holdout result requires one matching preregistration")
    trial = preregistrations[0]
    return events + (
        _event(
            event_index=len(events),
            kind="HOLDOUT_RESULT",
            trial_id=trial.trial_id,
            definition_sha256=trial.definition_sha256,
            dataset_sha256=trial.dataset_sha256,
            split_sha256=trial.split_sha256,
            stage_plan_sha256=trial.stage_plan_sha256,
            parameters_json=trial.parameters_json,
            multiplicity_family_id=trial.multiplicity_family_id,
            preregistered_at=trial.preregistered_at,
            external_anchor_sha256=trial.external_anchor_sha256,
            alpha=trial.alpha,
            family_size=trial.family_size,
            prior_event_sha256=events[-1].event_sha256,
            holdout_access_at=_timestamp(holdout_access_at, "holdout_access_at"),
            result_sha256=_sha(result_sha256, "result_sha256"),
            result_status=result_status,
            multiplicity_method=_text(multiplicity_method, "multiplicity_method"),
            adjusted_pvalue=adjusted_pvalue,
            raw_pvalue=raw_pvalue,
        ),
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
    manifest: ExperimentManifest,
    events: tuple[ExperimentEvent, ...],
) -> None:
    verify_experiment_manifest(manifest, events)
    if not isinstance(event, ExperimentEvent) or event.kind != "HOLDOUT_RESULT":
        raise ValueError("candidate evidence requires a holdout result event")
    if event not in events:
        raise ValueError("candidate holdout event is absent from the frozen manifest")
    if event.result_status != "PASSED":
        raise ValueError("candidate evidence requires a PASSED holdout result")
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
    event_count: int
    head_sha256: str
    bytes_sha256: str
    _token: object | None = field(default=None, repr=False, compare=False)

    def verify_current_bytes(self) -> None:
        if self._token is not _LEDGER_TOKEN:
            raise ValueError("experiment ledger receipt must come from persist entrypoint")
        payload = self.path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != self.bytes_sha256:
            raise ValueError("persistent experiment ledger bytes changed")


_LEDGER_TOKEN = object()


def persist_experiment_ledger(
    path: Path,
    events: tuple[ExperimentEvent, ...],
) -> ExperimentLedgerReceipt:
    """Append new event hashes to a durable ledger without rewriting its prefix."""

    _validate_chain(events)
    if not events:
        raise ValueError("persistent experiment ledger requires at least one event")
    candidate = path.expanduser().resolve()
    candidate.parent.mkdir(parents=True, exist_ok=True)
    existing = candidate.read_bytes() if candidate.exists() else b""
    expected_lines = tuple(
        json.dumps(
            {"event_index": event.event_index, "event_sha256": event.event_sha256},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        + b"\n"
        for event in events
    )
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
        len(events),
        events[-1].event_sha256,
        hashlib.sha256(payload).hexdigest(),
        _LEDGER_TOKEN,
    )
