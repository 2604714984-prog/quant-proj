"""Test-only builders that exercise controlled receipt mechanics.

These fixtures do not establish real-data provenance or external evidence.
"""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
from types import SimpleNamespace

import quant_system.backtest.event_loop as event_loop_module
from quant_system.backtest.event_loop import ControlledStageResult, create_stage_plan
from quant_system.backtest.portfolio import Portfolio
from quant_system.research.experiments import (
    FinalRunReceipt,
    capture_final_run_receipt,
)
from quant_system.research.splits import ReturnArtifact, capture_return_artifact


def controlled_return_fixture(
    returns_by_session: dict[date, float],
) -> tuple[ReturnArtifact, FinalRunReceipt]:
    """Create a complete in-memory controlled chain for mechanism tests only."""

    sessions = tuple(sorted(returns_by_session))
    signal_sessions = tuple(session - timedelta(days=1) for session in sessions)
    stage_plan = create_stage_plan(signal_sessions)
    results: list[ControlledStageResult] = []
    prior_stage_hash = "0" * 64
    starting_cash = 100.0
    for index, (signal_session, session) in enumerate(
        zip(signal_sessions, sessions, strict=True)
    ):
        ending_cash = starting_cash * (1 + returns_by_session[session])
        initial_portfolio = Portfolio.us(starting_cash)
        final_portfolio = Portfolio.us(ending_cash)
        initial_json = event_loop_module._portfolio_state_json(initial_portfolio)
        final_json = event_loop_module._portfolio_state_json(final_portfolio)
        initial_sha = hashlib.sha256(initial_json.encode()).hexdigest()
        final_sha = hashlib.sha256(final_json.encode()).hexdigest()
        stage_hash = hashlib.sha256(
            (
                f"{stage_plan.plan_sha256}|{index}|{session.isoformat()}|"
                f"{prior_stage_hash}|{initial_sha}|{final_sha}"
            ).encode()
        ).hexdigest()
        result = object.__new__(ControlledStageResult)
        for name, value in {
            "portfolio": final_portfolio,
            "context": SimpleNamespace(
                signal_session=SimpleNamespace(session_date=signal_session),
                execution_session=SimpleNamespace(session_date=session)
            ),
            "receipts": (),
            "input_identity_hash": hashlib.sha256(
                f"fixture-input|{session.isoformat()}".encode()
            ).hexdigest(),
            "receipt_hashes": (),
            "stage_hash": stage_hash,
            "final_nav": ending_cash,
            "stage_plan_sha256": stage_plan.plan_sha256,
            "stage_index": index,
            "stage_session": signal_session,
            "prior_stage_hash": prior_stage_hash,
            "initial_portfolio_json": initial_json,
            "initial_portfolio_sha256": initial_sha,
            "final_portfolio_json": final_json,
            "final_portfolio_sha256": final_sha,
            "interface_grade": "CONTROLLED_STAGE",
            "_token": event_loop_module._CONTROLLED_STAGE_TOKEN,
        }.items():
            object.__setattr__(result, name, value)
        results.append(result)
        starting_cash = ending_cash
        prior_stage_hash = stage_hash
    final_run_receipt = capture_final_run_receipt(stage_plan, tuple(results))
    return (
        capture_return_artifact(
            stage_plan,
            tuple(results),
            final_run_receipt,
        ),
        final_run_receipt,
    )
