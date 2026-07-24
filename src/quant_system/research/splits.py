"""Small, explicit helpers for point-in-time research splits."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from datetime import date, datetime, timedelta
import hashlib
import json
import math
import random
import statistics
from typing import Literal, Sequence, TypeAlias


DateLike: TypeAlias = date | datetime
EvaluationMethod = Literal["non_overlapping", "hac", "block_bootstrap"]
EvaluationUnit = Literal["daily_portfolio"]
_EVALUATION_TOKEN = object()
_MANIFEST_TOKEN = object()
_PLAN_TOKEN = object()
_RETURN_ARTIFACT_TOKEN = object()


def _time_text(value: DateLike) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("split datetimes must be timezone-aware")
        return value.isoformat()
    if type(value) is date:
        return value.isoformat()
    raise TypeError("split times must be dates or datetimes")


@dataclass(frozen=True)
class SplitSample:
    sample_id: str
    entity_id: str
    observed_at: DateLike
    return_start_session: date
    label_end_at: DateLike
    fold_id: str
    overlap_group: str


@dataclass(frozen=True)
class SplitManifest:
    samples: tuple[SplitSample, ...]
    manifest_sha256: str
    _token: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _MANIFEST_TOKEN:
            raise ValueError("SplitManifest must come from a controlled builder or loader")
        if hashlib.sha256(_manifest_payload(self.samples)).hexdigest() != (
            self.manifest_sha256
        ):
            raise ValueError("split manifest hash mismatch")

    def verify(self) -> None:
        self.__post_init__()


@dataclass(frozen=True)
class SplitEvaluationPlan:
    holdout_id: str
    manifest_sha256: str
    selected_sample_ids: tuple[str, ...]
    evaluation_unit: EvaluationUnit
    method: EvaluationMethod
    hac_bandwidth: int | None
    block_length: int | None
    bootstrap_replicates: int | None
    preregistered_at: datetime
    plan_sha256: str
    _token: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _PLAN_TOKEN:
            raise ValueError("SplitEvaluationPlan must come from its controlled builder")
        if hashlib.sha256(_plan_payload(self)).hexdigest() != self.plan_sha256:
            raise ValueError("split evaluation plan hash mismatch")


@dataclass(frozen=True)
class ReturnObservation:
    signal_session: date
    session: date
    period_start_session: date
    period_end_session: date
    accepted_sessions: tuple[date, ...]
    contributors: tuple[str, ...]
    opening_exposure: tuple[tuple[str, float], ...]
    closing_exposure: tuple[tuple[str, float], ...]
    traded_symbols: tuple[str, ...]
    blocked_symbols: tuple[str, ...]
    exposure_sha256: str
    aggregate_receipt_sha256: str
    initial_nav: float
    final_nav: float
    net_external_cashflow: float
    net_return: float
    input_identity_sha256: str
    initial_portfolio_sha256: str
    final_portfolio_sha256: str
    execution_receipt_sha256s: tuple[str, ...]
    transaction_costs: float


@dataclass(frozen=True)
class ReturnArtifact:
    stage_plan_sha256: str
    final_run_receipt_sha256: str
    observations: tuple[ReturnObservation, ...]
    returns_sha256: str
    artifact_sha256: str
    _token: object | None = field(default=None, repr=False, compare=False)

    def verify(self) -> None:
        if self._token is not _RETURN_ARTIFACT_TOKEN:
            raise ValueError("ReturnArtifact must come from capture_return_artifact")
        if not self.observations:
            raise ValueError("return artifact must contain observations")
        if tuple(item.session for item in self.observations) != tuple(
            sorted({item.session for item in self.observations})
        ):
            raise ValueError("return artifact sessions must be unique and chronological")
        for index, observation in enumerate(self.observations):
            if observation.signal_session >= observation.session:
                raise ValueError(
                    "return artifact execution session must follow signal session"
                )
            if (
                observation.session != observation.period_end_session
                or observation.period_start_session >= observation.period_end_session
                or not observation.accepted_sessions
                or observation.accepted_sessions[-1]
                != observation.period_end_session
                or any(
                    session <= observation.period_start_session
                    or session > observation.period_end_session
                    for session in observation.accepted_sessions
                )
                or (
                    index > 0
                    and observation.period_start_session
                    != self.observations[index - 1].period_end_session
                )
            ):
                raise ValueError("return periods must be contiguous and fully covered")
            if (
                not observation.contributors
                or observation.contributors
                != tuple(sorted(set(observation.contributors)))
            ):
                raise ValueError("return contributors must be nonempty, sorted, and unique")
            actual_symbols = tuple(
                sorted(
                    {
                        *(symbol for symbol, _ in observation.opening_exposure),
                        *(symbol for symbol, _ in observation.closing_exposure),
                        *observation.traded_symbols,
                        *observation.blocked_symbols,
                    }
                )
            )
            exposure_payload = json.dumps(
                {
                    "accepted_sessions": tuple(
                        item.isoformat() for item in observation.accepted_sessions
                    ),
                    "blocked_symbols": observation.blocked_symbols,
                    "closing_exposure": observation.closing_exposure,
                    "execution_receipt_sha256s": (
                        observation.execution_receipt_sha256s
                    ),
                    "opening_exposure": observation.opening_exposure,
                    "period_end_session": observation.period_end_session.isoformat(),
                    "period_start_session": (
                        observation.period_start_session.isoformat()
                    ),
                    "traded_symbols": observation.traded_symbols,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            if (
                observation.contributors != actual_symbols
                or hashlib.sha256(exposure_payload).hexdigest()
                != observation.exposure_sha256
            ):
                raise ValueError("return exposure differs from actual portfolio economics")
            if (
                not isinstance(observation.aggregate_receipt_sha256, str)
                or len(observation.aggregate_receipt_sha256) != 64
            ):
                raise ValueError("return aggregate receipt SHA is invalid")
            for digest in (
                observation.input_identity_sha256,
                observation.initial_portfolio_sha256,
                observation.final_portfolio_sha256,
                *observation.execution_receipt_sha256s,
            ):
                if not isinstance(digest, str) or len(digest) != 64:
                    raise ValueError("return artifact contains an invalid SHA-256")
            if any(
                not math.isfinite(value)
                for value in (
                    observation.initial_nav,
                    observation.final_nav,
                    observation.net_external_cashflow,
                    observation.net_return,
                    observation.transaction_costs,
                )
            ):
                raise ValueError("return artifact contains nonfinite economics")
            denominator = observation.initial_nav + observation.net_external_cashflow
            if denominator <= 0:
                raise ValueError("return artifact NAV denominator must be positive")
            expected_return = observation.final_nav / denominator - 1
            if abs(observation.net_return - expected_return) > 1e-12:
                raise ValueError("return artifact net return is not derived from NAV")
        expected_returns_sha = hashlib.sha256(
            json.dumps(
                tuple(
                    (item.session.isoformat(), item.net_return)
                    for item in self.observations
                ),
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        if self.returns_sha256 != expected_returns_sha:
            raise ValueError("return artifact returns hash mismatch")
        if hashlib.sha256(_return_artifact_payload(self)).hexdigest() != self.artifact_sha256:
            raise ValueError("return artifact receipt hash mismatch")


def _return_artifact_payload(artifact: ReturnArtifact) -> bytes:
    return json.dumps(
        {
            "final_run_receipt_sha256": artifact.final_run_receipt_sha256,
            "observations": tuple(
                {
                    **observation.__dict__,
                    "signal_session": observation.signal_session.isoformat(),
                    "session": observation.session.isoformat(),
                    "period_start_session": (
                        observation.period_start_session.isoformat()
                    ),
                    "period_end_session": observation.period_end_session.isoformat(),
                    "accepted_sessions": tuple(
                        item.isoformat() for item in observation.accepted_sessions
                    ),
                }
                for observation in artifact.observations
            ),
            "returns_sha256": artifact.returns_sha256,
            "stage_plan_sha256": artifact.stage_plan_sha256,
            "version": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def capture_return_artifact(
    stage_plan: object,
    results: tuple[object, ...],
    final_run_receipt: object,
) -> ReturnArtifact:
    """Derive immutable daily net returns from a complete controlled result chain."""

    from quant_system.backtest.event_loop import (
        ControlledStageReceipt,
        StagePlan,
        _portfolio_nav_from_artifact,
        _replay_decode,
    )
    from quant_system.research.experiments import (
        FinalRunReceipt,
        capture_final_run_receipt,
    )

    if not isinstance(stage_plan, StagePlan):
        raise TypeError("return artifact stage_plan must be controlled")
    if (
        type(results) is not tuple
        or len(results) != len(stage_plan.sessions)
        or any(not isinstance(result, ControlledStageReceipt) for result in results)
    ):
        raise ValueError("return artifact requires every controlled stage result")
    if not isinstance(final_run_receipt, FinalRunReceipt):
        raise TypeError("return artifact requires a FinalRunReceipt")
    final_run_receipt.__post_init__()
    replayed_final = capture_final_run_receipt(stage_plan, results)
    if replayed_final.receipt_sha256 != final_run_receipt.receipt_sha256:
        raise ValueError("return artifact results do not match FinalRunReceipt")
    observations: list[ReturnObservation] = []
    for result in results:
        result.verify()
        signal_session = result.signal_session
        execution_session = result.execution_session
        if signal_session != result.stage_session:
            raise ValueError("return artifact stage must bind its signal session")
        if execution_session <= signal_session:
            raise ValueError(
                "return artifact execution session must follow signal session"
            )
        initial_nav = _portfolio_nav_from_artifact(result.initial_portfolio_json)
        final_nav = _portfolio_nav_from_artifact(result.final_portfolio_json)
        if abs(final_nav - float(result.final_nav)) > 1e-12:
            raise ValueError("return artifact final NAV differs from portfolio state")
        net_external_cashflow = 0.0
        denominator = initial_nav + net_external_cashflow
        if denominator <= 0:
            raise ValueError("return artifact initial NAV must be positive")
        initial_state = json.loads(result.initial_portfolio_json)
        final_state = json.loads(result.final_portfolio_json)
        try:
            period_start_session = date.fromisoformat(
                initial_state["current_session"]
            )
            opening_exposure = tuple(
                sorted(
                    (symbol, float(position["shares"]))
                    for symbol, position in initial_state["positions"].items()
                    if float(position["shares"]) != 0
                )
            )
            closing_exposure = tuple(
                sorted(
                    (symbol, float(position["shares"]))
                    for symbol, position in final_state["positions"].items()
                    if float(position["shares"]) != 0
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("return portfolio exposure artifact is invalid") from exc
        replay = json.loads(result.replay_artifact_json)
        calendar_sessions = _replay_decode(replay["calendar_sessions"])
        accepted_sessions = tuple(
            item.session_date
            for item in calendar_sessions
            if period_start_session < item.session_date <= execution_session
        )
        receipts = tuple(json.loads(payload) for payload in result.receipt_payloads)
        traded_symbols = tuple(
            sorted(
                {
                    str(receipt["symbol"])
                    for receipt in receipts
                    if float(receipt["filled_shares"]) != 0
                }
            )
        )
        blocked_symbols = tuple(
            sorted(
                {
                    str(receipt["symbol"])
                    for receipt in receipts
                    if float(receipt["requested_shares"]) != 0
                    and float(receipt["filled_shares"]) == 0
                }
            )
        )
        contributors = tuple(
            sorted(
                {
                    *(symbol for symbol, _ in opening_exposure),
                    *(symbol for symbol, _ in closing_exposure),
                    *traded_symbols,
                    *blocked_symbols,
                }
            )
        )
        exposure_payload = json.dumps(
            {
                "accepted_sessions": tuple(
                    item.isoformat() for item in accepted_sessions
                ),
                "blocked_symbols": blocked_symbols,
                "closing_exposure": closing_exposure,
                "execution_receipt_sha256s": result.receipt_hashes,
                "opening_exposure": opening_exposure,
                "period_end_session": execution_session.isoformat(),
                "period_start_session": period_start_session.isoformat(),
                "traded_symbols": traded_symbols,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        observations.append(
            ReturnObservation(
                signal_session=signal_session,
                session=execution_session,
                period_start_session=period_start_session,
                period_end_session=execution_session,
                accepted_sessions=accepted_sessions,
                contributors=contributors,
                opening_exposure=opening_exposure,
                closing_exposure=closing_exposure,
                traded_symbols=traded_symbols,
                blocked_symbols=blocked_symbols,
                exposure_sha256=hashlib.sha256(exposure_payload).hexdigest(),
                aggregate_receipt_sha256=hashlib.sha256(
                    json.dumps(
                        {
                            "controlled_stage_receipt_sha256": (
                                result.receipt_sha256
                            ),
                            "execution_session": execution_session.isoformat(),
                            "exposure_sha256": hashlib.sha256(
                                exposure_payload
                            ).hexdigest(),
                            "signal_session": signal_session.isoformat(),
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest(),
                initial_nav=initial_nav,
                final_nav=final_nav,
                net_external_cashflow=net_external_cashflow,
                net_return=final_nav / denominator - 1,
                input_identity_sha256=result.input_identity_hash,
                initial_portfolio_sha256=result.initial_portfolio_sha256,
                final_portfolio_sha256=result.final_portfolio_sha256,
                execution_receipt_sha256s=result.receipt_hashes,
                transaction_costs=result.transaction_costs,
            )
        )
    frozen = tuple(observations)
    returns_sha = hashlib.sha256(
        json.dumps(
            tuple((item.session.isoformat(), item.net_return) for item in frozen),
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    values = {
        "stage_plan_sha256": stage_plan.plan_sha256,
        "final_run_receipt_sha256": final_run_receipt.receipt_sha256,
        "observations": frozen,
        "returns_sha256": returns_sha,
    }
    provisional = object.__new__(ReturnArtifact)
    for name, value in values.items():
        object.__setattr__(provisional, name, value)
    artifact = ReturnArtifact(
        **values,
        artifact_sha256=hashlib.sha256(
            _return_artifact_payload(provisional)
        ).hexdigest(),
        _token=_RETURN_ARTIFACT_TOKEN,
    )
    artifact.verify()
    return artifact


@dataclass(frozen=True)
class SplitEvaluation:
    plan_sha256: str
    method: EvaluationMethod
    selected_sample_ids: tuple[str, ...]
    evaluation_unit: EvaluationUnit
    nominal_n: int
    effective_n: float
    overlap_corrected: bool
    manifest_sha256: str
    return_artifact_sha256: str
    final_run_receipt_sha256: str
    returns_sha256: str
    estimator_sha256: str
    statistic: float
    raw_pvalue: float
    inference_distribution: str
    standard_error: float
    hac_bandwidth: int | None
    block_length: int | None
    bootstrap_replicates: int | None
    evaluation_sha256: str
    _token: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _EVALUATION_TOKEN:
            raise ValueError("SplitEvaluation must be created by evaluate_split")
        if hashlib.sha256(_evaluation_payload(self)).hexdigest() != self.evaluation_sha256:
            raise ValueError("split evaluation receipt hash mismatch")


def _evaluation_payload(evaluation: SplitEvaluation) -> bytes:
    return json.dumps(
        {
            name: value
            for name, value in evaluation.__dict__.items()
            if name not in {"evaluation_sha256", "_token"}
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _sample_payload(sample: SplitSample) -> dict[str, str]:
    return {
        "entity_id": sample.entity_id,
        "fold_id": sample.fold_id,
        "label_end_at": _time_text(sample.label_end_at),
        "label_time_type": type(sample.label_end_at).__name__,
        "observed_at": _time_text(sample.observed_at),
        "observed_time_type": type(sample.observed_at).__name__,
        "overlap_group": sample.overlap_group,
        "return_start_session": sample.return_start_session.isoformat(),
        "sample_id": sample.sample_id,
    }


def _manifest_payload(samples: tuple[SplitSample, ...]) -> bytes:
    return json.dumps(
        tuple(_sample_payload(sample) for sample in samples),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def serialize_split_manifest(manifest: SplitManifest) -> bytes:
    manifest.verify()
    return json.dumps(
        {
            "manifest_sha256": manifest.manifest_sha256,
            "samples": tuple(_sample_payload(sample) for sample in manifest.samples),
            "version": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def load_split_manifest(payload: bytes) -> SplitManifest:
    try:
        decoded = json.loads(payload)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("split manifest bytes must be valid JSON") from exc
    if (
        type(decoded) is not dict
        or set(decoded) != {"manifest_sha256", "samples", "version"}
        or decoded["version"] != 1
    ):
        raise ValueError("split manifest envelope is invalid")
    samples: list[SplitSample] = []
    for row in decoded["samples"]:
        if type(row) is not dict or set(row) != {
            "entity_id",
            "fold_id",
            "label_end_at",
            "label_time_type",
            "observed_at",
            "observed_time_type",
            "overlap_group",
            "return_start_session",
            "sample_id",
        }:
            raise ValueError("split manifest sample schema is invalid")

        def parse_time(value: str, value_type: str) -> DateLike:
            if value_type == "date":
                return date.fromisoformat(value)
            if value_type == "datetime":
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None or parsed.utcoffset() is None:
                    raise ValueError("split manifest datetime must be timezone-aware")
                return parsed
            raise ValueError("split manifest time type is invalid")

        samples.append(
            SplitSample(
                sample_id=row["sample_id"],
                entity_id=row["entity_id"],
                observed_at=parse_time(row["observed_at"], row["observed_time_type"]),
                return_start_session=date.fromisoformat(
                    row["return_start_session"]
                ),
                label_end_at=parse_time(row["label_end_at"], row["label_time_type"]),
                fold_id=row["fold_id"],
                overlap_group=row["overlap_group"],
            )
        )
    return SplitManifest(
        tuple(samples),
        str(decoded["manifest_sha256"]),
        _token=_MANIFEST_TOKEN,
    )


def build_split_manifest(
    *,
    entity_ids: Sequence[str],
    observed_at: Sequence[DateLike],
    label_end_at: Sequence[DateLike],
    fold_ids: Sequence[str],
    return_start_sessions: Sequence[date] | None = None,
) -> SplitManifest:
    """Build stable panel sample IDs and connected interval-overlap groups."""

    entities = tuple(entity_ids)
    observations = tuple(observed_at)
    labels = tuple(label_end_at)
    folds = tuple(fold_ids)
    starts = (
        tuple(return_start_sessions)
        if return_start_sessions is not None
        else tuple(
            item.date() if isinstance(item, datetime) else item
            for item in observations
        )
    )
    count = len(entities)
    if count == 0 or any(
        len(values) != count for values in (observations, labels, folds, starts)
    ):
        raise ValueError("split manifest columns must have one nonempty common length")
    expected_type = type(observations[0])
    if expected_type not in {date, datetime}:
        raise TypeError("observed_at must contain dates or datetimes")
    rows: list[dict[str, object]] = []
    seen_keys: set[tuple[str, DateLike]] = set()
    for entity, observed, label_end, fold, return_start in zip(
        entities,
        observations,
        labels,
        folds,
        starts,
        strict=True,
    ):
        if not isinstance(entity, str) or not entity.strip():
            raise ValueError("entity_id must be nonempty")
        if not isinstance(fold, str) or not fold.strip():
            raise ValueError("fold_id must be nonempty")
        if type(return_start) is not date:
            raise TypeError("return_start_session must contain dates")
        if type(observed) is not expected_type or type(label_end) is not expected_type:
            raise TypeError("split times must use one consistent temporal type")
        observed_text = _time_text(observed)
        label_text = _time_text(label_end)
        if label_end < observed:
            raise ValueError("label_end_at cannot precede observed_at")
        observed_date = observed.date() if isinstance(observed, datetime) else observed
        label_date = (
            label_end.date() if isinstance(label_end, datetime) else label_end
        )
        if not observed_date <= return_start <= label_date:
            raise ValueError(
                "return_start_session must follow observation and not exceed label end"
            )
        key = (entity, observed)
        if key in seen_keys:
            raise ValueError("entity_id and observed_at must identify one panel sample")
        seen_keys.add(key)
        sample_id = hashlib.sha256(
            (
                f"{entity}|{observed_text}|{return_start.isoformat()}|"
                f"{label_text}|{fold}"
            ).encode()
        ).hexdigest()
        rows.append(
            {
                "entity": entity,
                "observed": observed,
                "label_end": label_end,
                "fold": fold,
                "return_start": return_start,
                "sample_id": sample_id,
            }
        )
    overlap_by_sample: dict[str, str] = {}
    by_fold: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_fold[str(row["fold"])].append(row)
    for fold, fold_rows in sorted(by_fold.items()):
        ordered = sorted(
            fold_rows,
            key=lambda row: (row["observed"], row["label_end"], row["sample_id"]),
        )
        group_index = -1
        group_end: DateLike | None = None
        for row in ordered:
            observed = row["observed"]
            label_end = row["label_end"]
            assert isinstance(observed, (date, datetime))
            assert isinstance(label_end, (date, datetime))
            if group_end is None or observed > group_end:
                group_index += 1
                group_end = label_end
            elif label_end > group_end:
                group_end = label_end
            group = hashlib.sha256(f"{fold}|{group_index}".encode()).hexdigest()
            overlap_by_sample[str(row["sample_id"])] = group
    samples = tuple(
        SplitSample(
            sample_id=str(row["sample_id"]),
            entity_id=str(row["entity"]),
            observed_at=row["observed"],  # type: ignore[arg-type]
            return_start_session=row["return_start"],  # type: ignore[arg-type]
            label_end_at=row["label_end"],  # type: ignore[arg-type]
            fold_id=str(row["fold"]),
            overlap_group=overlap_by_sample[str(row["sample_id"])],
        )
        for row in sorted(rows, key=lambda item: str(item["sample_id"]))
    )
    digest = hashlib.sha256(_manifest_payload(samples)).hexdigest()
    return SplitManifest(samples, digest, _token=_MANIFEST_TOKEN)


def _plan_payload(plan: SplitEvaluationPlan) -> bytes:
    return json.dumps(
        {
            name: value.isoformat() if isinstance(value, datetime) else value
            for name, value in plan.__dict__.items()
            if name not in {"plan_sha256", "_token"}
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def build_split_evaluation_plan(
    manifest: SplitManifest,
    *,
    holdout_id: str,
    selected_sample_ids: Sequence[str],
    method: EvaluationMethod,
    preregistered_at: datetime,
    evaluation_unit: EvaluationUnit = "daily_portfolio",
    hac_bandwidth: int | None = None,
    block_length: int | None = None,
    bootstrap_replicates: int = 1000,
) -> SplitEvaluationPlan:
    manifest.verify()
    if not isinstance(holdout_id, str) or not holdout_id.strip():
        raise ValueError("holdout_id must be stable nonempty text")
    if preregistered_at.tzinfo is None or preregistered_at.utcoffset() is None:
        raise ValueError("preregistered_at must be timezone-aware")
    selected = tuple(selected_sample_ids)
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("selected_sample_ids must be nonempty and unique")
    by_id = {sample.sample_id: sample for sample in manifest.samples}
    if not set(selected) <= set(by_id):
        raise ValueError("selected sample is absent from split manifest")
    if evaluation_unit != "daily_portfolio":
        raise ValueError("only daily_portfolio evaluation is candidate-controlled")
    canonical_selected = tuple(
        sample.sample_id
        for sample in sorted(
            (by_id[sample_id] for sample_id in selected),
            key=lambda sample: (
                sample.observed_at,
                sample.entity_id,
                sample.label_end_at,
                sample.sample_id,
            ),
        )
    )
    values = {
        "holdout_id": holdout_id.strip(),
        "manifest_sha256": manifest.manifest_sha256,
        "selected_sample_ids": canonical_selected,
        "evaluation_unit": evaluation_unit,
        "method": method,
        "hac_bandwidth": hac_bandwidth,
        "block_length": block_length,
        "bootstrap_replicates": (
            bootstrap_replicates if method == "block_bootstrap" else None
        ),
        "preregistered_at": preregistered_at,
    }
    provisional = object.__new__(SplitEvaluationPlan)
    for name, value in values.items():
        object.__setattr__(provisional, name, value)
    return SplitEvaluationPlan(
        **values,
        plan_sha256=hashlib.sha256(_plan_payload(provisional)).hexdigest(),
        _token=_PLAN_TOKEN,
    )


def evaluate_split(
    manifest: SplitManifest,
    *,
    plan: SplitEvaluationPlan,
    return_artifact: ReturnArtifact,
) -> SplitEvaluation:
    if not isinstance(manifest, SplitManifest):
        raise TypeError("manifest must be a SplitManifest")
    manifest.verify()
    if not isinstance(plan, SplitEvaluationPlan):
        raise TypeError("plan must be a SplitEvaluationPlan")
    plan.__post_init__()
    if not isinstance(return_artifact, ReturnArtifact):
        raise TypeError("evaluate_split requires a controlled ReturnArtifact")
    return_artifact.verify()
    if plan.manifest_sha256 != manifest.manifest_sha256:
        raise ValueError("split evaluation plan does not bind this manifest")
    selected = plan.selected_sample_ids
    method = plan.method
    hac_bandwidth = plan.hac_bandwidth
    block_length = plan.block_length
    bootstrap_replicates = plan.bootstrap_replicates or 0
    by_id = {sample.sample_id: sample for sample in manifest.samples}
    if not set(selected) <= set(by_id):
        raise ValueError("selected sample is absent from split manifest")
    if method not in {"non_overlapping", "hac", "block_bootstrap"}:
        raise ValueError("unsupported split evaluation method")
    selected_samples = tuple(by_id[sample_id] for sample_id in selected)
    if len({sample.fold_id for sample in selected_samples}) != 1:
        raise ValueError("one split evaluation cannot mix fold IDs")
    overlapping = any(
        (
            left.return_start_session,
            _time_text(left.label_end_at),
        )
        != (
            right.return_start_session,
            _time_text(right.label_end_at),
        )
        and left.return_start_session
        < (
            right.label_end_at.date()
            if isinstance(right.label_end_at, datetime)
            else right.label_end_at
        )
        and right.return_start_session
        < (
            left.label_end_at.date()
            if isinstance(left.label_end_at, datetime)
            else left.label_end_at
        )
        for index, left in enumerate(selected_samples)
        for right in selected_samples[index + 1 :]
    )
    if method == "non_overlapping" and overlapping:
        raise ValueError("non-overlapping evaluation selected overlapping labels")
    intervals: dict[tuple[date, date], set[str]] = defaultdict(set)
    for sample in selected_samples:
        start = sample.return_start_session
        end = (
            sample.label_end_at.date()
            if isinstance(sample.label_end_at, datetime)
            else sample.label_end_at
        )
        intervals[(start, end)].add(sample.entity_id)
    temporal_returns = []
    for (start, end), contributors in sorted(intervals.items()):
        horizon = tuple(
            observation
            for observation in return_artifact.observations
            if observation.period_start_session >= start
            and observation.period_end_session <= end
        )
        if (
            not horizon
            or horizon[0].period_start_session != start
            or horizon[-1].period_end_session != end
            or any(
                right.period_start_session != left.period_end_session
                for left, right in zip(horizon, horizon[1:], strict=False)
            )
        ):
            raise ValueError(
                "ReturnArtifact does not cover the complete label horizon"
            )
        expected_contributors = tuple(sorted(contributors))
        if any(
            observation.contributors != expected_contributors
            for observation in horizon
        ):
            raise ValueError(
                "ReturnArtifact contributor set differs from selected samples"
            )
        compounded = math.prod(1 + observation.net_return for observation in horizon) - 1
        temporal_returns.append(
            {
                "aggregate_receipt_sha256s": tuple(
                    observation.aggregate_receipt_sha256 for observation in horizon
                ),
                "compound_net_return": compounded,
                "contributors": expected_contributors,
                "end_session": end.isoformat(),
                "start_session": start.isoformat(),
            }
        )
    values = tuple(item["compound_net_return"] for item in temporal_returns)
    minimum_n = {"non_overlapping": 5, "hac": 30, "block_bootstrap": 20}[method]
    if len(values) < minimum_n:
        raise ValueError(f"{method} requires at least {minimum_n} daily portfolio returns")
    mean = statistics.fmean(values)
    sample_variance = statistics.variance(values)
    estimator = {
        "method": method,
        "version": 2,
        "evaluation_unit": plan.evaluation_unit,
        "minimum_n": minimum_n,
        "hac_bandwidth": hac_bandwidth,
        "block_length": block_length,
        "bootstrap_replicates": (
            plan.bootstrap_replicates if method == "block_bootstrap" else None
        ),
        "plan_sha256": plan.plan_sha256,
    }
    if method == "non_overlapping":
        if hac_bandwidth is not None or block_length is not None:
            raise ValueError("non-overlapping evaluation does not accept correction parameters")
        standard_error = math.sqrt(sample_variance / len(values))
        effective_n = float(len(values))
        statistic = mean / standard_error
        raw_pvalue = _student_t_two_sided_pvalue(statistic, len(values) - 1)
        inference_distribution = f"student_t_df_{len(values) - 1}"
    elif method == "hac":
        if (
            type(hac_bandwidth) is not int
            or not 1 <= hac_bandwidth < len(values)
            or block_length is not None
        ):
            raise ValueError("HAC requires bandwidth in [1, nominal_n)")
        centered = tuple(value - mean for value in values)
        long_run_variance = math.fsum(value * value for value in centered) / len(values)
        for lag in range(1, hac_bandwidth + 1):
            covariance = math.fsum(
                centered[index] * centered[index - lag]
                for index in range(lag, len(values))
            ) / len(values)
            long_run_variance += 2 * (1 - lag / (hac_bandwidth + 1)) * covariance
        if long_run_variance <= 0 or not math.isfinite(long_run_variance):
            raise ValueError("HAC long-run variance must be positive and finite")
        standard_error = math.sqrt(long_run_variance / len(values))
        effective_n = min(
            float(len(values)),
            max(1.0, sample_variance / (standard_error * standard_error)),
        )
        statistic = mean / standard_error
        raw_pvalue = math.erfc(abs(statistic) / math.sqrt(2.0))
        inference_distribution = "hac_asymptotic_normal_min_n_30"
    else:
        if (
            type(block_length) is not int
            or not 2 <= block_length <= len(values)
            or hac_bandwidth is not None
            or type(bootstrap_replicates) is not int
            or bootstrap_replicates < 200
        ):
            raise ValueError(
                "block bootstrap requires block_length in [2, nominal_n] "
                "and at least 200 replicates"
            )
        centered_values = tuple(value - mean for value in values)
        seed_payload = json.dumps(
            {"returns": values, **estimator},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        generator = random.Random(int(hashlib.sha256(seed_payload).hexdigest(), 16))
        bootstrap_means: list[float] = []
        for _ in range(bootstrap_replicates):
            sample: list[float] = []
            while len(sample) < len(values):
                start = generator.randrange(len(values))
                sample.extend(
                    centered_values[(start + offset) % len(values)]
                    for offset in range(block_length)
                )
            bootstrap_means.append(statistics.fmean(sample[: len(values)]))
        standard_error = statistics.stdev(bootstrap_means)
        if standard_error <= 0 or not math.isfinite(standard_error):
            raise ValueError("block-bootstrap standard error must be positive and finite")
        effective_n = min(
            float(len(values)),
            max(1.0, sample_variance / (standard_error * standard_error)),
        )
        statistic = mean / standard_error
        exceedances = sum(
            abs(bootstrap_mean) >= abs(mean) for bootstrap_mean in bootstrap_means
        )
        raw_pvalue = (exceedances + 1) / (bootstrap_replicates + 1)
        inference_distribution = "centered_moving_block_empirical"
    if standard_error <= 0 or not math.isfinite(standard_error):
        raise ValueError("evaluation standard error must be positive and finite")
    returns_sha = hashlib.sha256(
        json.dumps(
            temporal_returns,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    estimator_sha = hashlib.sha256(
        json.dumps(estimator, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    values_by_field = {
        "plan_sha256": plan.plan_sha256,
        "method": method,
        "selected_sample_ids": selected,
        "evaluation_unit": plan.evaluation_unit,
        "nominal_n": len(values),
        "effective_n": float(effective_n),
        "overlap_corrected": method in {"hac", "block_bootstrap"} or not overlapping,
        "manifest_sha256": manifest.manifest_sha256,
        "return_artifact_sha256": return_artifact.artifact_sha256,
        "final_run_receipt_sha256": return_artifact.final_run_receipt_sha256,
        "returns_sha256": returns_sha,
        "estimator_sha256": estimator_sha,
        "statistic": statistic,
        "raw_pvalue": raw_pvalue,
        "inference_distribution": inference_distribution,
        "standard_error": standard_error,
        "hac_bandwidth": hac_bandwidth,
        "block_length": block_length,
        "bootstrap_replicates": (
            plan.bootstrap_replicates if method == "block_bootstrap" else None
        ),
    }
    provisional = object.__new__(SplitEvaluation)
    for name, value in values_by_field.items():
        object.__setattr__(provisional, name, value)
    digest = hashlib.sha256(_evaluation_payload(provisional)).hexdigest()
    return SplitEvaluation(
        **values_by_field,
        evaluation_sha256=digest,
        _token=_EVALUATION_TOKEN,
    )


def _regularized_incomplete_beta(x: float, a: float, b: float) -> float:
    """Numerically stable regularized incomplete beta for Student-t tails."""

    if not 0 <= x <= 1 or a <= 0 or b <= 0:
        raise ValueError("invalid incomplete beta arguments")
    if x in {0.0, 1.0}:
        return x

    def continued_fraction(aa: float, bb: float, xx: float) -> float:
        qab, qap, qam = aa + bb, aa + 1.0, aa - 1.0
        c, d = 1.0, 1.0 - qab * xx / qap
        d = 1.0 / max(abs(d), 1e-300) * (1 if d >= 0 else -1)
        result = d
        for index in range(1, 201):
            twice = 2 * index
            coefficient = index * (bb - index) * xx / (
                (qam + twice) * (aa + twice)
            )
            d = 1.0 + coefficient * d
            d = 1.0 / max(abs(d), 1e-300) * (1 if d >= 0 else -1)
            c = 1.0 + coefficient / c
            c = max(abs(c), 1e-300) * (1 if c >= 0 else -1)
            result *= d * c
            coefficient = -(aa + index) * (qab + index) * xx / (
                (aa + twice) * (qap + twice)
            )
            d = 1.0 + coefficient * d
            d = 1.0 / max(abs(d), 1e-300) * (1 if d >= 0 else -1)
            c = 1.0 + coefficient / c
            c = max(abs(c), 1e-300) * (1 if c >= 0 else -1)
            delta = d * c
            result *= delta
            if abs(delta - 1.0) < 3e-14:
                break
        return result

    factor = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return factor * continued_fraction(a, b, x) / a
    return 1.0 - factor * continued_fraction(b, a, 1.0 - x) / b


def _student_t_two_sided_pvalue(statistic: float, degrees_of_freedom: int) -> float:
    if degrees_of_freedom < 1:
        raise ValueError("Student-t inference requires positive degrees of freedom")
    x = degrees_of_freedom / (degrees_of_freedom + statistic * statistic)
    return min(
        1.0,
        max(
            0.0,
            _regularized_incomplete_beta(
                x,
                degrees_of_freedom / 2.0,
                0.5,
            ),
        ),
    )


def require_split_evaluation_for_candidate(evaluation: SplitEvaluation) -> None:
    if not isinstance(evaluation, SplitEvaluation) or not evaluation.overlap_corrected:
        raise ValueError("candidate significance requires overlap correction")


def _validate_time_axis(values: Sequence[DateLike], *, name: str) -> tuple[DateLike, ...]:
    frozen = tuple(values)
    if not frozen:
        raise ValueError(f"{name} must not be empty")
    expected_type = type(frozen[0])
    if expected_type not in (date, datetime):
        raise TypeError(f"{name} must contain only dates or only datetimes")
    if any(type(value) is not expected_type for value in frozen):
        raise TypeError(f"{name} must contain one consistent temporal type")
    if expected_type is datetime:
        for value in frozen:
            assert isinstance(value, datetime)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} datetimes must be timezone-aware")
    if frozen != tuple(sorted(frozen)) or len(frozen) != len(set(frozen)):
        raise ValueError(f"{name} must be strictly increasing and unique")
    return frozen


def purged_embargo_train_mask(
    observed_at: Sequence[DateLike],
    label_end_at: Sequence[DateLike],
    *,
    test_start: DateLike,
    test_end: DateLike,
    embargo: timedelta = timedelta(0),
) -> tuple[bool, ...]:
    """Return training eligibility without label overlap or post-test leakage.

    An observation is removed when its inclusive information/label interval
    intersects the inclusive test interval. Observations after the test are
    additionally removed through ``test_end + embargo``. This general helper
    supports both walk-forward (use only the pre-test ``True`` values) and
    symmetric cross-validation splits.
    """

    observations = _validate_time_axis(observed_at, name="observed_at")
    labels = tuple(label_end_at)
    if len(labels) != len(observations):
        raise ValueError("label_end_at must have the same length as observed_at")
    if not isinstance(embargo, timedelta):
        raise TypeError("embargo must be a timedelta")
    if timedelta(0) > embargo:
        raise ValueError("embargo must be nonnegative")

    expected_type = type(observations[0])
    if expected_type is date and (embargo.seconds != 0 or embargo.microseconds != 0):
        raise ValueError("date-based embargo must use a whole number of days")
    if type(test_start) is not expected_type or type(test_end) is not expected_type:
        raise TypeError("test bounds must use the same temporal type as observed_at")
    if expected_type is datetime:
        for bound in (test_start, test_end):
            assert isinstance(bound, datetime)
            if bound.tzinfo is None or bound.utcoffset() is None:
                raise ValueError("test bound datetimes must be timezone-aware")
    if test_start > test_end:
        raise ValueError("test_start must not be after test_end")

    for observation, label_end in zip(observations, labels, strict=True):
        if type(label_end) is not expected_type:
            raise TypeError("label_end_at must use the same temporal type as observed_at")
        if expected_type is datetime:
            assert isinstance(label_end, datetime)
            if label_end.tzinfo is None or label_end.utcoffset() is None:
                raise ValueError("label_end_at datetimes must be timezone-aware")
        if label_end < observation:
            raise ValueError("a label cannot end before its observation")

    embargo_end = test_end + embargo
    mask: list[bool] = []
    for observation, label_end in zip(observations, labels, strict=True):
        overlaps_test = observation <= test_end and label_end >= test_start
        inside_post_test_embargo = test_end < observation <= embargo_end
        mask.append(not overlaps_test and not inside_post_test_embargo)
    return tuple(mask)


def walk_forward_masks(
    observed_at: Sequence[DateLike],
    label_end_at: Sequence[DateLike],
    *,
    test_start: DateLike,
    test_end: DateLike,
) -> tuple[tuple[bool, ...], tuple[bool, ...]]:
    """Return strictly historical train and inclusive test masks.

    Future observations are never admitted to the training mask. Labels that
    reach the first test timestamp are purged in full.
    """

    observations = _validate_time_axis(observed_at, name="observed_at")
    labels = tuple(label_end_at)
    general_train = purged_embargo_train_mask(
        observations,
        labels,
        test_start=test_start,
        test_end=test_end,
    )
    train = tuple(keep and value < test_start for keep, value in zip(general_train, observations))
    test = tuple(
        test_start <= value <= test_end and label_end <= test_end
        for value, label_end in zip(observations, labels, strict=True)
    )
    if not any(train):
        raise ValueError("split contains no purged training observations")
    if not any(test):
        raise ValueError("split contains no test observations")
    return train, test
