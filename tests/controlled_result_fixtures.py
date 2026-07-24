"""Synthetic receipt fixtures for statistical mechanism tests only.

These values never enter the candidate happy path and do not establish execution,
real-data provenance, provider qualification, or external evidence.
"""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json

import quant_system.research.experiments as experiment_module
import quant_system.research.splits as split_module
from quant_system.backtest.event_loop import create_stage_plan
from quant_system.research.experiments import FinalRunReceipt
from quant_system.research.splits import ReturnArtifact, ReturnObservation


def controlled_return_fixture(
    returns_by_session: dict[date, float],
) -> tuple[ReturnArtifact, FinalRunReceipt]:
    """Build synthetic economics for split/estimator unit tests."""

    sessions = tuple(sorted(returns_by_session))
    stage_plan = create_stage_plan(
        tuple(session - timedelta(days=1) for session in sessions)
    )
    nav = 100.0
    observations = []
    transitions = []
    stage_hashes = []
    for index, session in enumerate(sessions):
        initial_nav = nav
        nav *= 1 + returns_by_session[session]
        initial_sha = hashlib.sha256(
            f"synthetic-initial|{index}|{initial_nav:.17g}".encode()
        ).hexdigest()
        final_sha = hashlib.sha256(
            f"synthetic-final|{index}|{nav:.17g}".encode()
        ).hexdigest()
        if transitions:
            initial_sha = transitions[-1][1]
        transitions.append((initial_sha, final_sha))
        stage_hashes.append(
            hashlib.sha256(
                f"synthetic-stage|{index}|{initial_sha}|{final_sha}".encode()
            ).hexdigest()
        )
        observations.append(
            ReturnObservation(
                signal_session=session - timedelta(days=1),
                session=session,
                initial_nav=initial_nav,
                final_nav=nav,
                net_external_cashflow=0.0,
                net_return=returns_by_session[session],
                input_identity_sha256=hashlib.sha256(
                    f"synthetic-input|{session.isoformat()}".encode()
                ).hexdigest(),
                initial_portfolio_sha256=initial_sha,
                final_portfolio_sha256=final_sha,
                execution_receipt_sha256s=(),
                transaction_costs=0.0,
            )
        )
    final_values = {
        "stage_plan_sha256": stage_plan.plan_sha256,
        "stage_count": len(sessions),
        "ordered_stage_receipt_sha256s": tuple(
            hashlib.sha256(
                f"synthetic-receipt|{index}".encode()
            ).hexdigest()
            for index in range(len(sessions))
        ),
        "ordered_stage_hashes": tuple(stage_hashes),
        "ordered_portfolio_transitions": tuple(transitions),
        "final_stage_hash": stage_hashes[-1],
        "initial_portfolio_sha256": transitions[0][0],
        "final_portfolio_sha256": transitions[-1][1],
        "final_nav": nav,
    }
    provisional_final = object.__new__(FinalRunReceipt)
    for name, value in final_values.items():
        object.__setattr__(provisional_final, name, value)
    final_receipt = FinalRunReceipt(
        **final_values,
        receipt_sha256=hashlib.sha256(
            experiment_module._final_run_payload(provisional_final)
        ).hexdigest(),
        _token=experiment_module._FINAL_RUN_TOKEN,
    )
    frozen = tuple(observations)
    returns_sha = hashlib.sha256(
        json.dumps(
            tuple((item.session.isoformat(), item.net_return) for item in frozen),
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    artifact_values = {
        "stage_plan_sha256": stage_plan.plan_sha256,
        "final_run_receipt_sha256": final_receipt.receipt_sha256,
        "observations": frozen,
        "returns_sha256": returns_sha,
    }
    provisional_artifact = object.__new__(ReturnArtifact)
    for name, value in artifact_values.items():
        object.__setattr__(provisional_artifact, name, value)
    artifact = ReturnArtifact(
        **artifact_values,
        artifact_sha256=hashlib.sha256(
            split_module._return_artifact_payload(provisional_artifact)
        ).hexdigest(),
        _token=split_module._RETURN_ARTIFACT_TOKEN,
    )
    artifact.verify()
    return artifact, final_receipt
