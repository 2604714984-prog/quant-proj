"""One-use retrospective runner for the frozen Cycle 6 VIX-change strategy."""
# ruff: noqa: E402

from __future__ import annotations
import hashlib
import json
import math
import os
import stat
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / 'src', ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
from quant_system.backtest import ExecutionInput, Portfolio, run_static_rebalance
from quant_system.data import AcceptedSession, AcceptedSessionCalendar, CalendarIdentity, CorporateActionIdentity, SourceIdentity
from quant_system.markets.universe import StatusEvidence, UniverseSnapshotIdentity, validate_universe_snapshot
from research.adapters.c6_cboe_vix_weekly_change_spy_cash import HOLDOUT_INTERVALS, INITIAL_CAPITAL, PROGRAM_ALPHA, RESEARCH_ID, VALIDATION_INTERVALS, WeeklyState, derive_weekly_state, holdout_decision, split_support, validation_decision
DEFINITION = ROOT / 'research/definitions/c6_cboe_vix_weekly_change_spy_cash_v1.json'
ADAPTER = ROOT / 'research/adapters/c6_cboe_vix_weekly_change_spy_cash.py'
RUNNER = Path(__file__).resolve()
DEFINITION_SHA256 = '38834937bb2dbb662d3bd1ddea16bc48d7eefcbb187327acbfb72c4760f5502d'
ADAPTER_SHA256 = '8be3db4b0bf24f55f3c93ef38c844563f8b2e1f8310aaec07dbae28cad022f52'
STATE_INPUT_SHA256 = '3a221b43b625634f456a4e29a010b7eb8746508933aaeba1b29e3540911a4491'
STATE_RECEIPT_SHA256 = 'e5ba49693658d2deabf53d3df4c6c6fcb51e0c506c9b3ce367246f1b4bf75812'
CALENDAR_INPUT_SHA256 = '08b1722c675012d89e0b4f92ed51f51160adbd1d54961c093c52101c067fc553'
VALIDATION_BUNDLE_SHA256 = '51c402ef95ab93a235dd38c862be517f9f0ed06fa47c3bb91becc33e914aa2d6'
HOLDOUT_BUNDLE_SHA256 = '120eeeacd724af31125c7209985621d90d1edd1c95cfe068098fc3bf903a8db1'
CORE_SOURCE_FILE_COUNT = 23
CORE_SOURCE_SHA256 = '46ae2fe342a40034b9caacb6cc48a182947a49da9d874de31a1fdb60be0b9a80'
INCLUSION_RULE_SHA256 = '89483ee34a4b87fcdb728889dc31c7dc7222f85b3071ff7a97c65148e1b6402e'
STATE_INPUT = Path('/home/rongyu/workspace/quant-data/staging/c6_vix_weekly_change_impulse_spy_cash_v1/vix_weekly_change_input.json')
VALIDATION_BUNDLE = STATE_INPUT.with_name('spy_validation_runtime_bundle.json')
HOLDOUT_BUNDLE = STATE_INPUT.with_name('spy_holdout_runtime_bundle.json')
PRIVATE_ROOT = Path('/home/rongyu/workspace/quant-data/private_results')
TECHNICAL_CONTINUATION_ID = 'PREOUTCOME_TECHNICAL_CONTINUATION_1'
PRIOR_VALIDATION_CLAIM = PRIVATE_ROOT / 'c6_vix_weekly_change_spy_cash_v1_validation/claim.json'
PRIOR_VALIDATION_RESULT = PRIOR_VALIDATION_CLAIM.with_name('result.json')
PRIOR_VALIDATION_CLAIM_SHA256 = 'b238f671e9c1f5f71106da5ca31dc54fc8389f6e61b138dc1f911710d9bd2d03'
PRIOR_VALIDATION_RESULT_SHA256 = '72b76ad796245c031a83bc42afd6277248ab18c6fb0a883eb0610862de715494'
VALIDATION_CLAIM = PRIVATE_ROOT / 'c6_vix_weekly_change_spy_cash_v1_technical_continuation_1_validation/claim.json'
VALIDATION_RESULT = VALIDATION_CLAIM.with_name('result.json')
HOLDOUT_CLAIM = PRIVATE_ROOT / 'c6_vix_weekly_change_spy_cash_v1_technical_continuation_1_holdout/claim.json'
HOLDOUT_RESULT = HOLDOUT_CLAIM.with_name('result.json')
ONE_WAY_SLIPPAGE_BPS = 10.0
_SOURCE_FIELDS = {'source_url', 'content_sha256', 'available_at', 'retrieved_at', 'revision_id', 'supersedes_revision_id'}
_SESSION_FIELDS = {'session_date', 'open_at', 'close_at', 'is_early_close', 'exchange_id', 'exchange_timezone', 'row_sha256', 'source'}
_CALENDAR_IDENTITY_FIELDS = {'exchange_id', 'exchange_timezone', 'coverage_start', 'coverage_end', 'session_count', 'session_dates_sha256', 'session_rows_sha256', 'source_identity'}
_STATUS_FIELDS = {'status_id', 'symbol', 'kind', 'value', 'effective_from', 'effective_to', 'exchange_timezone', 'source'}
_SNAPSHOT_FIELDS = {'market', 'exchange_id', 'effective_session', 'member_count', 'ordered_members_sha256', 'lifecycle_coverage_sha256', 'inclusion_rule_sha256', 'calendar_identity_sha256', 'source_identity'}
_ACTION_FIELDS = {'subject_id', 'action_id', 'action_type', 'effective_at', 'source', 'exchange_timezone', 'ex_date', 'record_date', 'pay_date', 'split_ratio', 'cash_amount', 'currency', 'unit', 'new_subject_id'}
_EXECUTION_FIELDS = {'symbol', 'market', 'session_date', 'raw_open', 'currency', 'source', 'decision_price', 'decision_price_session', 'decision_price_effective_at', 'decision_price_source', 'decision_price_basis', 'execution_price_effective_at', 'execution_price_basis', 'corporate_action_ids'}
_BUNDLE_FIELDS = {'schema_version', 'research_id', 'stage', 'symbol', 'state_input_sha256', 'calendar_input_sha256', 'reconstruction_calendar', 'calendar_epochs', 'execution_points', 'daily_sessions', 'corporate_actions'}
_POINT_FIELDS = {'signal_session', 'decision_at', 'execution_session', 'decision_calendar_epoch_id', 'execution_calendar_revision_id', 'terminal_exit', 'state_row_sha256', 'status_evidence', 'universe_snapshot', 'execution'}
_STATE_TOP_FIELDS = {'availability_basis', 'calendar', 'missing_anchor_count', 'missing_next_count', 'rows', 'source_class', 'terminal_no_next_session_count'}
_STATE_CALENDAR_FIELDS = {'end', 'mode', 'nlink', 'path', 'rows', 'sha256', 'start', 'uid'}
_STATE_ROW_FIELDS = {'availability_basis', 'available_at', 'current_close', 'execution_date', 'observation_date', 'prior_close', 'prior_observation_date', 'row_sha256', 'source_class', 'state'}
STATE_TOP_SOURCE_CLASS = 'RETROSPECTIVE_SECONDARY_NOT_STRICT_HISTORICAL_PIT'
STATE_ROW_SOURCE_CLASS = 'CBOE_CURRENT_SNAPSHOT_RETROSPECTIVE_SECONDARY_NOT_STRICT_HISTORICAL_PIT'

class InputBlockedError(ValueError):
    """Fail-closed identity, schema, chronology, or one-use error."""

@dataclass(frozen=True)
class Point:
    signal_session: date
    decision_at: datetime
    execution_session: date
    calendar: AcceptedSessionCalendar
    execution_calendar_revision: AcceptedSessionCalendar | None
    execution_input: ExecutionInput
    universe_snapshot: UniverseSnapshotIdentity
    weekly_state: WeeklyState
    terminal_exit: bool

@dataclass(frozen=True)
class Bundle:
    stage: str
    reconstruction_calendar: AcceptedSessionCalendar
    points: tuple[Point, ...]
    daily_sessions: tuple[date, ...]
    actions: tuple[CorporateActionIdentity, ...]

def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()

def _sha256(value: object, field: str) -> str:
    if type(value) is not str or len(value) != 64 or any((character not in '0123456789abcdef' for character in value)):
        raise InputBlockedError(f'{field} must be a lowercase SHA-256')
    return value

def _runtime_sha(value: str, field: str) -> str:
    if value.startswith('__PATCH_C6_'):
        raise InputBlockedError(f'{field} is not materialized and patched')
    return _sha256(value, field)

def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())

def _core_identity() -> tuple[int, str]:
    rows: list[dict[str, str]] = []
    for path in sorted((ROOT / 'src/quant_system').rglob('*.py')):
        if path.is_symlink() or not path.is_file():
            raise InputBlockedError('shared-core source must contain regular files')
        rows.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': _file_sha256(path)})
    payload = json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()
    return (len(rows), _sha256_bytes(payload))

def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    record: dict[str, Any] = {}
    for key, value in pairs:
        if key in record:
            raise InputBlockedError(f'duplicate JSON key: {key}')
        record[key] = value
    return record

def _json(payload: bytes, field: str) -> dict[str, Any]:
    try:
        record = json.loads(payload.decode('utf-8', errors='strict'), object_pairs_hook=_strict_object, parse_constant=lambda value: (_ for _ in ()).throw(InputBlockedError(f'nonfinite JSON constant: {value}')))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputBlockedError(f'{field} is not strict UTF-8 JSON') from exc
    if type(record) is not dict:
        raise InputBlockedError(f'{field} must be a JSON object')
    return record

def _capture(path: Path, expected_sha256: str | None, *, max_bytes: int, private: bool=True) -> bytes:
    flags = os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NOFOLLOW', 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise InputBlockedError(f'cannot open protected input: {path}') from exc
    try:
        before = os.fstat(fd)
        mode = stat.S_IMODE(before.st_mode)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
            raise InputBlockedError('input must be an owner-controlled regular file')
        if private and mode & ~384 or (not private and mode & 18):
            raise InputBlockedError('input mode is outside the frozen bound')
        if not 0 < before.st_size <= max_bytes:
            raise InputBlockedError('input size is outside the frozen bound')
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(fd, min(1024 * 1024, max_bytes + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > max_bytes:
                raise InputBlockedError('input exceeds the frozen size bound')
        after = os.fstat(fd)
    finally:
        os.close(fd)
    try:
        current = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise InputBlockedError('input path changed during capture') from exc
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if any((getattr(before, field) != getattr(after, field) or getattr(after, field) != getattr(current, field) for field in fields)):
        raise InputBlockedError('input changed during descriptor-bound capture')
    payload = b''.join(chunks)
    if expected_sha256 is not None and _sha256_bytes(payload) != _sha256(expected_sha256, 'expected input SHA-256'):
        raise InputBlockedError('input SHA-256 mismatch')
    return payload

def _date(value: object, field: str) -> date:
    if type(value) is not str:
        raise InputBlockedError(f'{field} must be an ISO date')
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise InputBlockedError(f'{field} must be an ISO date') from exc
    if parsed.isoformat() != value:
        raise InputBlockedError(f'{field} must use canonical ISO format')
    return parsed

def _datetime(value: object, field: str) -> datetime:
    if type(value) is not str:
        raise InputBlockedError(f'{field} must be an ISO timestamp')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InputBlockedError(f'{field} must be an ISO timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InputBlockedError(f'{field} must be timezone-aware')
    return parsed

def _decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool):
        raise InputBlockedError(f'{field} must be finite')
    try:
        number = Decimal(str(value))
    except Exception as exc:
        raise InputBlockedError(f'{field} must be finite') from exc
    if not number.is_finite():
        raise InputBlockedError(f'{field} must be finite')
    return number

def _keys(row: object, expected: set[str], field: str) -> dict[str, Any]:
    if type(row) is not dict or set(row) != expected:
        raise InputBlockedError(f'{field} schema mismatch')
    return row

def _state_label_matches(declared: object, derived: str) -> bool:
    return (declared == 'SPY' and derived == 'spy') or (
        declared == 'cash' and derived == 'cash'
    )

def _load_states(payload: bytes) -> dict[str, tuple[WeeklyState, ...]]:
    record = _json(payload, 'weekly VIX state input')
    _keys(record, _STATE_TOP_FIELDS, 'weekly VIX state input')
    if record['availability_basis'] != 'METHOD_BASED_CONSERVATIVE_AVAILABILITY' or record['source_class'] != STATE_TOP_SOURCE_CLASS or record['missing_anchor_count'] != 0 or (record['missing_next_count'] != 0) or (record['terminal_no_next_session_count'] != 1):
        raise InputBlockedError('weekly state top-level qualification mismatch')
    calendar = _keys(record['calendar'], _STATE_CALENDAR_FIELDS, 'state calendar')
    if calendar['sha256'] != CALENDAR_INPUT_SHA256 or calendar['start'] != '2018-01-02' or calendar['end'] != '2026-06-30' or (calendar['mode'] != '0600') or (calendar['nlink'] != 1):
        raise InputBlockedError('weekly state calendar identity mismatch')
    rows = record['rows']
    if type(rows) is not list or len(rows) != 435:
        raise InputBlockedError('weekly state requires exactly 435 boundary rows')
    states: list[WeeklyState] = []
    for raw in rows:
        row = _keys(raw, _STATE_ROW_FIELDS, 'weekly state row')
        if row['availability_basis'] != 'METHOD_BASED_CONSERVATIVE_AVAILABILITY' or row['source_class'] != STATE_ROW_SOURCE_CLASS:
            raise InputBlockedError('weekly state row qualification mismatch')
        state = derive_weekly_state(prior_observation_date=_date(row['prior_observation_date'], 'prior_observation_date'), observation_date=_date(row['observation_date'], 'observation_date'), execution_date=_date(row['execution_date'], 'execution_date'), prior_close=row['prior_close'], current_close=row['current_close'], available_at=_datetime(row['available_at'], 'available_at'), row_sha256=_sha256(row['row_sha256'], 'state row SHA-256'))
        if not _state_label_matches(row['state'], state.state):
            raise InputBlockedError('declared state differs from frozen sign rule')
        states.append(state)
    frozen = tuple(states)
    execution_dates = tuple((state.execution_date for state in frozen))
    if execution_dates != tuple(sorted(execution_dates)) or len(execution_dates) != len(set(execution_dates)):
        raise InputBlockedError('weekly state execution dates are duplicated or reordered')
    groups = {'development': tuple((state for state in frozen if date(2018, 3, 1) <= state.execution_date <= date(2020, 12, 31))), 'validation': tuple((state for state in frozen if date(2021, 1, 1) <= state.execution_date <= date(2023, 6, 30))), 'holdout': tuple((state for state in frozen if date(2023, 7, 1) <= state.execution_date <= date(2026, 6, 30)))}
    expected_boundaries = {'development': 148, 'validation': 130, 'holdout': 157}
    if {key: len(value) for key, value in groups.items()} != expected_boundaries:
        raise InputBlockedError('weekly state split boundary counts mismatch')
    if sum(map(len, groups.values())) != len(frozen):
        raise InputBlockedError('weekly state contains a boundary outside frozen splits')
    for split_id, group in groups.items():
        if not split_support(group[:-1], split_id=split_id).all_gates_pass:
            raise InputBlockedError(f'{split_id} state-support gates failed')
    return groups

def _source(row: object) -> SourceIdentity:
    item = _keys(row, _SOURCE_FIELDS, 'source identity')
    return SourceIdentity(item['source_url'], item['content_sha256'], _datetime(item['available_at'], 'source available_at'), _datetime(item['retrieved_at'], 'source retrieved_at'), item['revision_id'], item['supersedes_revision_id'])

def _calendar(row: object) -> AcceptedSessionCalendar:
    item = _keys(row, {'calendar_identity', 'session_rows'}, 'calendar')
    if type(item['session_rows']) is not list:
        raise InputBlockedError('calendar session_rows must be a list')
    sessions = tuple((AcceptedSession(_date(session['session_date'], 'session_date'), _datetime(session['open_at'], 'open_at'), _datetime(session['close_at'], 'close_at'), _source(session['source']), session['exchange_timezone'], session['is_early_close'], session['exchange_id']) for raw in item['session_rows'] for session in (_keys(raw, _SESSION_FIELDS, 'calendar session'),)))
    identity = _keys(item['calendar_identity'], _CALENDAR_IDENTITY_FIELDS, 'calendar identity')
    if identity['exchange_id'] != 'XNYS' or identity['exchange_timezone'] != 'America/New_York' or any((session.exchange_id != 'XNYS' or session.exchange_timezone != 'America/New_York' for session in sessions)):
        raise InputBlockedError('runtime calendars must be XNYS America/New_York')
    frozen = CalendarIdentity(identity['exchange_id'], identity['exchange_timezone'], _date(identity['coverage_start'], 'coverage_start'), _date(identity['coverage_end'], 'coverage_end'), identity['session_count'], identity['session_dates_sha256'], identity['session_rows_sha256'], _source(identity['source_identity']))
    return AcceptedSessionCalendar(sessions, identity=frozen)

def _calendar_epochs(rows: object) -> dict[str, AcceptedSessionCalendar]:
    if type(rows) is not dict or not rows or any((type(key) is not str or not key for key in rows)):
        raise InputBlockedError('calendar epochs are required')
    digests = [_sha256_bytes(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()) for value in rows.values()]
    if len(set(digests)) != len(digests):
        raise InputBlockedError('calendar epoch identities must not duplicate bytes')
    return {key: _calendar(value) for key, value in rows.items()}

def _status(row: object) -> StatusEvidence:
    item = _keys(row, _STATUS_FIELDS, 'status evidence')
    if item['symbol'] != 'SPY' or item['exchange_timezone'] != 'America/New_York':
        raise InputBlockedError('status evidence must identify SPY in America/New_York')
    ending = None if item['effective_to'] is None else _date(item['effective_to'], 'effective_to')
    return StatusEvidence(item['status_id'], item['symbol'], item['kind'], item['value'], _date(item['effective_from'], 'effective_from'), ending, item['exchange_timezone'], _source(item['source']))

def _snapshot(row: object) -> UniverseSnapshotIdentity:
    item = _keys(row, _SNAPSHOT_FIELDS, 'universe snapshot')
    if item['market'] != 'us' or item['exchange_id'] != 'XNYS':
        raise InputBlockedError('universe snapshot must identify the US XNYS venue')
    snapshot = UniverseSnapshotIdentity(item['market'], item['exchange_id'], _date(item['effective_session'], 'effective_session'), item['member_count'], item['ordered_members_sha256'], item['lifecycle_coverage_sha256'], item['inclusion_rule_sha256'], item['calendar_identity_sha256'], _source(item['source_identity']))
    if snapshot.inclusion_rule_sha256 != INCLUSION_RULE_SHA256:
        raise InputBlockedError('universe inclusion rule mismatch')
    return snapshot

def _action(row: object) -> CorporateActionIdentity:
    item = _keys(row, _ACTION_FIELDS, 'corporate action')
    if item['subject_id'] != 'SPY' or item['exchange_timezone'] != 'America/New_York':
        raise InputBlockedError('corporate action must identify SPY in America/New_York')

    def optional_date(key: str) -> date | None:
        return None if item[key] is None else _date(item[key], key)
    return CorporateActionIdentity(item['subject_id'], item['action_id'], item['action_type'], _datetime(item['effective_at'], 'action effective_at'), _source(item['source']), item['exchange_timezone'], ex_date=optional_date('ex_date'), record_date=optional_date('record_date'), pay_date=optional_date('pay_date'), split_ratio=None if item['split_ratio'] is None else _decimal(item['split_ratio'], 'split_ratio'), cash_amount=None if item['cash_amount'] is None else _decimal(item['cash_amount'], 'cash_amount'), currency=item['currency'], unit=item['unit'], new_subject_id=item['new_subject_id'])

def _execution_actions(actions: tuple[CorporateActionIdentity, ...], session: date, supplied_ids: object) -> tuple[CorporateActionIdentity, ...]:
    expected = tuple((action for action in actions if action.effective_date == session))
    if supplied_ids != [action.action_id for action in expected]:
        raise InputBlockedError('execution action coverage is incomplete or reordered')
    return expected

def _require_action_sessions(
    actions: tuple[CorporateActionIdentity, ...],
    daily_sessions: tuple[date, ...],
) -> None:
    accepted = set(daily_sessions)
    if any(action.effective_date not in accepted for action in actions):
        raise InputBlockedError(
            'corporate action effective date must be an accepted split session'
        )

def _execution(row: object, statuses: tuple[StatusEvidence, ...], actions: tuple[CorporateActionIdentity, ...], *, signal_session: date, decision_at: datetime, calendar: AcceptedSessionCalendar) -> ExecutionInput:
    item = _keys(row, _EXECUTION_FIELDS, 'execution input')
    if item['symbol'] != 'SPY' or item['market'] != 'us' or item['currency'] != 'USD':
        raise InputBlockedError('only the frozen US SPY execution input is allowed')
    action_ids = tuple((action.action_id for action in actions))
    if item['corporate_action_ids'] != list(action_ids):
        raise InputBlockedError('execution corporate-action mapping mismatch')
    ordinary = {'cash_dividend', 'special_dividend', 'split', 'reverse_split'}
    if any((action.action_type not in ordinary for action in actions)):
        raise InputBlockedError('unsupported execution-day corporate action')
    expected_basis = 'raw_pre_action_per_old_share' if actions else 'raw_execution_units'
    decision_source = _source(item['decision_price_source'])
    accepted_signal = calendar.session_on(signal_session, as_of=decision_at)
    execution_date = _date(item['session_date'], 'session_date')
    accepted_execution = calendar.session_on(execution_date, as_of=decision_at)
    execution_effective_at = _datetime(item['execution_price_effective_at'], 'execution_price_effective_at')
    price = item['decision_price']
    raw_open = item['raw_open']
    valid_prices = not isinstance(price, bool) and isinstance(price, (int, float)) and math.isfinite(price) and (price > 0.0) and (not isinstance(raw_open, bool)) and isinstance(raw_open, (int, float)) and math.isfinite(raw_open) and (raw_open > 0.0)
    if item['decision_price_basis'] != expected_basis or item['execution_price_basis'] != 'retrospective_daily_bar_open_fill' or _date(item['decision_price_session'], 'decision_price_session') != signal_session or (_datetime(item['decision_price_effective_at'], 'decision_price_effective_at') != accepted_signal.close_at) or (execution_effective_at != accepted_execution.open_at) or (decision_source.available_at > decision_at) or (not valid_prices):
        raise InputBlockedError('execution price basis or calendar identity mismatch')
    return ExecutionInput(item['symbol'], item['market'], raw_open, item['currency'], _source(item['source']), statuses, corporate_actions=actions, decision_price=price, decision_price_source=decision_source, decision_price_basis=item['decision_price_basis'], execution_price_effective_at=execution_effective_at, execution_price_basis=item['execution_price_basis'])

def _load_bundle(payload: bytes, *, stage: str, official_states: dict[str, tuple[WeeklyState, ...]]) -> Bundle:
    expected_boundaries = 130 if stage == 'validation' else 157
    record = _json(payload, 'runtime bundle')
    _keys(record, _BUNDLE_FIELDS, 'runtime bundle')
    if record['schema_version'] != 'c6-vix-weekly-change-runtime-v1' or record['research_id'] != RESEARCH_ID or record['stage'] != stage or (record['symbol'] != 'SPY') or (record['state_input_sha256'] != STATE_INPUT_SHA256) or (_sha256(record['calendar_input_sha256'], 'runtime calendar input SHA-256') != CALENDAR_INPUT_SHA256):
        raise InputBlockedError('runtime bundle frozen identity mismatch')
    reconstruction = _calendar(record['reconstruction_calendar'])
    epoch_rows = record['calendar_epochs']
    epochs = _calendar_epochs(epoch_rows)
    raw_actions = record['corporate_actions']
    if type(raw_actions) is not list:
        raise InputBlockedError('corporate_actions must be a list')
    actions = tuple((_action(row) for row in raw_actions))
    if len({action.action_id for action in actions}) != len(actions):
        raise InputBlockedError('corporate actions must have unique identities')
    raw_points = record['execution_points']
    if type(raw_points) is not list or len(raw_points) != expected_boundaries:
        raise InputBlockedError(f'{stage} requires exactly {expected_boundaries} boundaries')
    points: list[Point] = []
    for raw, official in zip(raw_points, official_states[stage], strict=True):
        item = _keys(raw, _POINT_FIELDS, 'execution point')
        decision_at = _datetime(item['decision_at'], 'decision_at')
        execution_session = _date(item['execution_session'], 'execution_session')
        signal_session = _date(item['signal_session'], 'signal_session')
        if item['state_row_sha256'] != official.row_sha256 or execution_session != official.execution_date or signal_session != official.observation_date or (official.available_at > decision_at):
            raise InputBlockedError('runtime weekly state differs from official state input')
        revision_id = item['execution_calendar_revision_id']
        try:
            calendar = epochs[item['decision_calendar_epoch_id']]
            revision = None if revision_id is None else epochs[revision_id]
        except KeyError as exc:
            raise InputBlockedError('unknown calendar epoch identity') from exc
        if calendar.next_session(signal_session, as_of=decision_at).session_date != execution_session:
            raise InputBlockedError('execution must be the next accepted XNYS session')
        local = decision_at.astimezone(ZoneInfo('America/New_York'))
        if local.date() != execution_session or local.time().isoformat() != '09:00:00':
            raise InputBlockedError('decision must be 09:00 ET on execution session')
        point_actions = _execution_actions(actions, execution_session, item['execution']['corporate_action_ids'])
        statuses = tuple((_status(value) for value in item['status_evidence']))
        execution = _execution(item['execution'], statuses, point_actions, signal_session=signal_session, decision_at=decision_at, calendar=calendar)
        snapshot = _snapshot(item['universe_snapshot'])
        if snapshot.effective_session != execution_session:
            raise InputBlockedError('universe snapshot session mismatch')
        validate_universe_snapshot(
            snapshot,
            market='us',
            calendar_identity=calendar.identity,
            session=calendar.session_on(execution_session, as_of=decision_at),
            decision_at=decision_at,
            members=('SPY',),
            records_by_symbol={'SPY': statuses},
        )
        points.append(Point(signal_session, decision_at, execution_session, calendar, revision, execution, snapshot, official, item['terminal_exit']))
    frozen = tuple(points)
    dates = tuple((point.execution_session for point in frozen))
    if dates != tuple(sorted(dates)) or len(dates) != len(set(dates)):
        raise InputBlockedError('execution sessions must be unique and chronological')
    if sum((point.terminal_exit is True for point in frozen)) != 1 or not frozen[-1].terminal_exit:
        raise InputBlockedError('only the final boundary may be the terminal exit')
    if any((point.terminal_exit for point in frozen[:-1])):
        raise InputBlockedError('entry boundaries cannot be terminal exits')
    if not split_support(tuple((point.weekly_state for point in frozen[:-1])), split_id=stage).all_gates_pass:
        raise InputBlockedError(f'{stage} state-support gates failed')
    raw_daily = record['daily_sessions']
    if type(raw_daily) is not list:
        raise InputBlockedError('daily_sessions must be a list')
    daily = tuple((_date(value, 'daily session') for value in raw_daily))
    expected_daily = tuple((session for session in reconstruction.session_dates if frozen[0].execution_session <= session <= frozen[-1].execution_session))
    if daily != expected_daily:
        raise InputBlockedError('daily session coverage is incomplete or reordered')
    _require_action_sessions(actions, daily)
    return Bundle(stage, reconstruction, frozen, daily, actions)

def _apply_actions(portfolio: Portfolio, session_date: date, actions: tuple[CorporateActionIdentity, ...]) -> None:
    portfolio.start_session(session_date)
    for action in actions:
        if action.effective_date != session_date:
            continue
        if action.action_type in {'cash_dividend', 'special_dividend'}:
            assert action.cash_amount is not None and action.ex_date and action.pay_date
            portfolio.apply_cash_distribution('SPY', event_id=action.action_id, amount_per_share=float(action.cash_amount), ex_date=action.ex_date, pay_date=action.pay_date)
        elif action.action_type in {'split', 'reverse_split'}:
            assert action.split_ratio is not None
            portfolio.apply_split('SPY', float(action.split_ratio), event_id=action.action_id)
        else:
            raise InputBlockedError('unsupported nonterminal SPY corporate action')

def _rebalance(portfolio: Portfolio, point: Point, target: float | None, prior_stage_hash: str):
    return run_static_rebalance(portfolio, point.calendar, signal_session=point.signal_session, decision_at=point.decision_at, execution_inputs=(point.execution_input,), execution_calendar_revision=point.execution_calendar_revision, universe_members=('SPY',), universe_snapshot=point.universe_snapshot, target_weights=lambda context: {} if target is None else {'SPY': target}, strategy_definition_sha256=DEFINITION_SHA256, strategy_adapter_sha256=ADAPTER_SHA256, slippage_bps=ONE_WAY_SLIPPAGE_BPS, prior_stage_hash=prior_stage_hash)

def _simulate(bundle: Bundle) -> tuple[tuple[float, ...], tuple[float, ...], tuple[str, ...]]:
    point_by_date = {point.execution_session: point for point in bundle.points}
    actions_by_date = {day: tuple((action for action in bundle.actions if action.effective_date == day)) for day in bundle.daily_sessions}
    strategy = Portfolio.us(INITIAL_CAPITAL)
    benchmark = Portfolio.us(INITIAL_CAPITAL)
    strategy_navs = [INITIAL_CAPITAL]
    benchmark_navs = [INITIAL_CAPITAL]
    strategy_stage = '0' * 64
    benchmark_stage = '0' * 64
    stage_hashes: list[str] = []
    for session_date in bundle.daily_sessions:
        point = point_by_date.get(session_date)
        daily_actions = actions_by_date[session_date]
        if point is None:
            _apply_actions(strategy, session_date, daily_actions)
            _apply_actions(benchmark, session_date, daily_actions)
            continue
        if point.terminal_exit:
            strategy_result = _rebalance(strategy, point, None, strategy_stage)
            benchmark_result = _rebalance(benchmark, point, None, benchmark_stage)
            strategy, benchmark = (strategy_result.portfolio, benchmark_result.portfolio)
            strategy_navs.append(strategy_result.final_nav)
            benchmark_navs.append(benchmark_result.final_nav)
            stage_hashes.extend((strategy_result.stage_hash, benchmark_result.stage_hash))
            continue
        strategy_result = _rebalance(strategy, point, point.weekly_state.spy_target_weight, strategy_stage)
        strategy, strategy_stage = (strategy_result.portfolio, strategy_result.stage_hash)
        stage_hashes.append(strategy_stage)
        if point is bundle.points[0]:
            benchmark_result = _rebalance(benchmark, point, 1.0, benchmark_stage)
            benchmark, benchmark_stage = (benchmark_result.portfolio, benchmark_result.stage_hash)
            stage_hashes.append(benchmark_stage)
            continue
        _apply_actions(benchmark, session_date, daily_actions)
        raw_open = point.execution_input.open_price
        if isinstance(raw_open, bool) or raw_open is None or (not math.isfinite(raw_open)) or (raw_open <= 0.0):
            raise InputBlockedError('benchmark boundary requires a positive raw open')
        strategy_navs.append(strategy_result.final_nav)
        benchmark_navs.append(benchmark.nav({'SPY': float(raw_open)}))
    expected = (VALIDATION_INTERVALS if bundle.stage == 'validation' else HOLDOUT_INTERVALS) + 1
    if len(strategy_navs) != expected or len(benchmark_navs) != expected:
        raise InputBlockedError('split boundary path is incomplete')
    return (tuple((right / left - 1.0 for left, right in zip(strategy_navs, strategy_navs[1:]))), tuple((right / left - 1.0 for left, right in zip(benchmark_navs, benchmark_navs[1:]))), tuple(stage_hashes))

def _decision(stage: str, strategy: tuple[float, ...], spy: tuple[float, ...]) -> dict[str, Any]:
    decision = validation_decision(strategy, spy) if stage == 'validation' else holdout_decision(strategy, spy)
    extra = {'arithmetic_mean_active_return': decision.arithmetic_mean_active_return} if stage == 'validation' else {'inference': asdict(decision.inference)}
    return {'stage': stage, 'observed_intervals': decision.observed_intervals, 'strategy': asdict(decision.strategy), 'spy': asdict(decision.spy), 'gates': {name: passed for name, passed in decision.gates}, 'all_gates_pass': decision.all_gates_pass, **extra}

def _private_parent(path: Path) -> None:
    path.parent.mkdir(mode=448, parents=True, exist_ok=True)
    parent = path.parent.lstat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) & ~448 or path.exists() or path.is_symlink():
        raise InputBlockedError('one-use target must be absent under an owner-private directory')

def _publish(path: Path, record: dict[str, Any]) -> str:
    _private_parent(path)
    payload = json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    try:
        fd = os.open(temporary, flags, 384)
        try:
            written = 0
            while written < len(payload):
                count = os.write(fd, payload[written:])
                if count <= 0:
                    raise InputBlockedError('private publication was incomplete')
                written += count
            os.fsync(fd)
        finally:
            os.close(fd)
        os.link(temporary, path, follow_symlinks=False)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)
    if stat.S_IMODE(path.stat().st_mode) != 384:
        raise InputBlockedError('private publication mode is not 0600')
    return _sha256_bytes(payload)

def _claim_record(stage: str, runner_sha256: str, state_sha256: str, expected_bundle_sha256: str) -> dict[str, Any]:
    return {'schema_version': 'c6-vix-weekly-change-claim-v1', 'research_id': RESEARCH_ID, 'stage': stage, 'claimed_at': datetime.now(timezone.utc).isoformat(), 'technical_continuation_id': TECHNICAL_CONTINUATION_ID, 'prior_claim_sha256': PRIOR_VALIDATION_CLAIM_SHA256, 'prior_result_sha256': PRIOR_VALIDATION_RESULT_SHA256, 'definition_sha256': DEFINITION_SHA256, 'adapter_sha256': ADAPTER_SHA256, 'runner_sha256': runner_sha256, 'weekly_state_input_sha256': state_sha256, 'accepted_xnys_calendar_sha256': CALENDAR_INPUT_SHA256, 'expected_runtime_bundle_sha256': _sha256(expected_bundle_sha256, 'expected runtime bundle SHA-256'), 'one_use_execution_consumed': True, 'rerun_authorized': False}

def _result_record(stage: str, classification: str, *, claim_sha256: str, bundle_sha256: str | None, decision: dict[str, Any] | None, stage_hashes: tuple[str, ...]=(), error: Exception | None=None) -> dict[str, Any]:
    return {'schema_version': 'c6-vix-weekly-change-result-v1', 'research_id': RESEARCH_ID, 'stage': stage, 'classification': classification, 'program_alpha': PROGRAM_ALPHA, 'technical_continuation_id': TECHNICAL_CONTINUATION_ID, 'prior_claim_sha256': PRIOR_VALIDATION_CLAIM_SHA256, 'prior_result_sha256': PRIOR_VALIDATION_RESULT_SHA256, 'claim_sha256': claim_sha256, 'runtime_bundle_sha256': bundle_sha256, 'decision': decision, 'stage_hashes': list(stage_hashes), 'error_type': None if error is None else type(error).__name__, 'error_message': None if error is None else str(error), 'strategy_candidate_available': False, 'rerun_authorized': False, 'shadow': False, 'paper': False, 'broker': False, 'live': False}

def _stage(stage: str, bundle_path: Path, claim_path: Path, result_path: Path, *, runner_sha256: str, state_sha256: str, expected_bundle_sha256: str, official_states: dict[str, tuple[WeeklyState, ...]]) -> dict[str, Any]:
    payload = _capture(bundle_path, expected_bundle_sha256, max_bytes=64 * 1024 * 1024)
    bundle_sha = _sha256_bytes(payload)
    bundle = _load_bundle(payload, stage=stage, official_states=official_states)
    claim_sha = _publish(claim_path, _claim_record(stage, runner_sha256, state_sha256, expected_bundle_sha256))
    try:
        strategy, spy, stage_hashes = _simulate(bundle)
        decision = _decision(stage, strategy, spy)
        classification = 'RETROSPECTIVE_SECONDARY_VALIDATION_PASS_HOLDOUT_UNLOCKED' if stage == 'validation' and decision['all_gates_pass'] else 'RETROSPECTIVE_SECONDARY_VALIDATION_FAIL' if stage == 'validation' else 'RETROSPECTIVE_SECONDARY_PASS_PENDING_REVIEW' if decision['all_gates_pass'] else 'RETROSPECTIVE_SECONDARY_HOLDOUT_FAIL'
        record = _result_record(stage, classification, claim_sha256=claim_sha, bundle_sha256=bundle_sha, decision=decision, stage_hashes=stage_hashes)
    except Exception as exc:
        record = _result_record(stage, 'INPUT_BLOCKED_CLAIM_CONSUMED', claim_sha256=claim_sha, bundle_sha256=bundle_sha, decision=None, error=exc)
    _publish(result_path, record)
    return record

def _validate_technical_continuation() -> None:
    prior_paths = {PRIOR_VALIDATION_CLAIM, PRIOR_VALIDATION_RESULT}
    target_paths = {VALIDATION_CLAIM, VALIDATION_RESULT, HOLDOUT_CLAIM, HOLDOUT_RESULT}
    if len(target_paths) != 4 or prior_paths & target_paths:
        raise InputBlockedError('technical continuation must use distinct one-use targets')
    if any(path.exists() or path.is_symlink() for path in target_paths):
        raise InputBlockedError('technical continuation target already exists')
    _capture(PRIOR_VALIDATION_CLAIM, PRIOR_VALIDATION_CLAIM_SHA256, max_bytes=8 * 1024)
    _capture(PRIOR_VALIDATION_RESULT, PRIOR_VALIDATION_RESULT_SHA256, max_bytes=8 * 1024)

def _validate_definition(payload: bytes) -> None:
    definition = _json(payload, 'definition')
    identities = definition.get('input_identities')
    runtime = definition.get('runtime_bundle_contract')
    continuation = definition.get('one_use')
    if type(identities) is not dict or type(runtime) is not dict or type(continuation) is not dict:
        raise InputBlockedError('definition identity sections are missing')
    if definition.get('research_id') != RESEARCH_ID or identities.get('weekly_state_input_sha256') != STATE_INPUT_SHA256 or identities.get('weekly_state_receipt_sha256') != STATE_RECEIPT_SHA256 or (identities.get('accepted_xnys_calendar_sha256') != CALENDAR_INPUT_SHA256) or (identities.get('adapter_sha256') != ADAPTER_SHA256) or (identities.get('shared_core_source_file_count') != CORE_SOURCE_FILE_COUNT) or (identities.get('shared_core_source_sha256') != CORE_SOURCE_SHA256) or (identities.get('universe_inclusion_rule_sha256') != INCLUSION_RULE_SHA256) or (runtime.get('expected_inclusion_rule_sha256') != INCLUSION_RULE_SHA256) or (identities.get('validation_bundle_sha256') != VALIDATION_BUNDLE_SHA256) or (identities.get('holdout_bundle_sha256') != HOLDOUT_BUNDLE_SHA256) or (identities.get('prior_validation_claim_sha256') != PRIOR_VALIDATION_CLAIM_SHA256) or (identities.get('prior_validation_result_sha256') != PRIOR_VALIDATION_RESULT_SHA256) or (continuation.get('technical_continuation_id') != TECHNICAL_CONTINUATION_ID) or (continuation.get('validation_claim') != str(VALIDATION_CLAIM)) or (continuation.get('validation_result') != str(VALIDATION_RESULT)) or (continuation.get('holdout_claim') != str(HOLDOUT_CLAIM)) or (continuation.get('holdout_result') != str(HOLDOUT_RESULT)) or continuation.get('runtime_bundle_preflight_before_claim') is not True or continuation.get('claim_before_strategy_simulation') is not True:
        raise InputBlockedError('definition does not bind exact frozen identities')

def execute_once() -> dict[str, Any]:
    validation_sha = _runtime_sha(VALIDATION_BUNDLE_SHA256, 'validation runtime bundle SHA-256')
    holdout_sha = _runtime_sha(HOLDOUT_BUNDLE_SHA256, 'holdout runtime bundle SHA-256')
    _validate_technical_continuation()
    definition_payload = _capture(DEFINITION, DEFINITION_SHA256, max_bytes=256 * 1024, private=False)
    _validate_definition(definition_payload)
    if _file_sha256(ADAPTER) != ADAPTER_SHA256:
        raise InputBlockedError('adapter bytes differ from the frozen identity')
    if _core_identity() != (CORE_SOURCE_FILE_COUNT, CORE_SOURCE_SHA256):
        raise InputBlockedError('shared-core bytes differ from the frozen identity')
    runner_sha = _file_sha256(RUNNER)
    state_payload = _capture(STATE_INPUT, STATE_INPUT_SHA256, max_bytes=8 * 1024 * 1024)
    state_sha = _sha256_bytes(state_payload)
    official_states = _load_states(state_payload)
    validation = _stage('validation', VALIDATION_BUNDLE, VALIDATION_CLAIM, VALIDATION_RESULT, runner_sha256=runner_sha, state_sha256=state_sha, expected_bundle_sha256=validation_sha, official_states=official_states)
    if validation['classification'] != 'RETROSPECTIVE_SECONDARY_VALIDATION_PASS_HOLDOUT_UNLOCKED':
        return validation
    return _stage('holdout', HOLDOUT_BUNDLE, HOLDOUT_CLAIM, HOLDOUT_RESULT, runner_sha256=runner_sha, state_sha256=state_sha, expected_bundle_sha256=holdout_sha, official_states=official_states)

def main() -> int:
    record = execute_once()
    print(json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False))
    return 0 if record['classification'] != 'INPUT_BLOCKED_CLAIM_CONSUMED' else 2
if __name__ == '__main__':
    raise SystemExit(main())
