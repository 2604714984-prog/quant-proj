"""Immutable append-only experiment receipts without a control plane."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
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
    parameters_json: str
    multiplicity_family_id: str
    prior_event_sha256: str
    event_sha256: str
    holdout_access_at: datetime | None = None
    result_sha256: str | None = None
    result_status: ResultStatus | None = None
    multiplicity_method: str | None = None
    adjusted_pvalue: float | None = None
    _token: object | None = None

    def __post_init__(self) -> None:
        if self._token is not _EVENT_TOKEN:
            raise ValueError("experiment events must come from append entrypoints")
        if type(self.event_index) is not int or self.event_index < 0:
            raise ValueError("event_index must be nonnegative")
        _text(self.trial_id, "trial_id")
        for name in ("definition_sha256", "dataset_sha256", "split_sha256"):
            _sha(getattr(self, name), name)
        _sha(self.prior_event_sha256, "prior_event_sha256")
        _text(self.multiplicity_family_id, "multiplicity_family_id")
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
            if (
                not isinstance(self.adjusted_pvalue, (int, float))
                or isinstance(self.adjusted_pvalue, bool)
                or not 0 <= float(self.adjusted_pvalue) <= 1
            ):
                raise ValueError("adjusted_pvalue must be in [0, 1]")
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
    parameters: Mapping[str, object],
    multiplicity_family_id: str,
) -> tuple[ExperimentEvent, ...]:
    _validate_chain(events)
    if any(event.trial_id == trial_id for event in events):
        raise ValueError("trial_id is already present in the append-only chain")
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
            parameters_json=parameters_json,
            multiplicity_family_id=_text(
                multiplicity_family_id,
                "multiplicity_family_id",
            ),
            prior_event_sha256=prior,
            holdout_access_at=None,
            result_sha256=None,
            result_status=None,
            multiplicity_method=None,
            adjusted_pvalue=None,
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
    adjusted_pvalue: float,
) -> tuple[ExperimentEvent, ...]:
    _validate_chain(events)
    if any(event.kind == "HOLDOUT_RESULT" for event in events):
        raise ValueError("final holdout has already been unlocked")
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
            parameters_json=trial.parameters_json,
            multiplicity_family_id=trial.multiplicity_family_id,
            prior_event_sha256=events[-1].event_sha256,
            holdout_access_at=_timestamp(holdout_access_at, "holdout_access_at"),
            result_sha256=_sha(result_sha256, "result_sha256"),
            result_status=result_status,
            multiplicity_method=_text(multiplicity_method, "multiplicity_method"),
            adjusted_pvalue=adjusted_pvalue,
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


def require_adjusted_holdout_for_candidate(event: ExperimentEvent) -> None:
    if not isinstance(event, ExperimentEvent) or event.kind != "HOLDOUT_RESULT":
        raise ValueError("candidate evidence requires a holdout result event")
    if not event.multiplicity_method or event.adjusted_pvalue is None:
        raise ValueError("candidate evidence requires multiplicity adjustment")
