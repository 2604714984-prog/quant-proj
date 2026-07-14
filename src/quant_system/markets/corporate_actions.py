"""Strict corporate-action identities and point-in-time revision selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import math
from typing import Literal
from urllib.parse import urlsplit

from .common import (
    MarketDataError,
    is_finite_number,
    require_aware_datetime,
    require_date,
    require_nonempty_text,
    require_sha256,
)

ActionType = Literal["split", "cash_dividend", "symbol_change"]
ACTION_TYPES = frozenset({"split", "cash_dividend", "symbol_change"})


@dataclass(frozen=True)
class CorporateAction:
    action_id: str
    action_type: ActionType
    symbol: str
    source_url: str
    source_sha256: str
    revision: int
    supersedes_sha256: str | None
    available_at: datetime
    effective_at: datetime
    ex_date: date | None = None
    record_date: date | None = None
    pay_date: date | None = None
    split_ratio: float | None = None
    cash_amount: float | None = None
    currency: str | None = None
    new_symbol: str | None = None

    def __post_init__(self) -> None:
        require_nonempty_text(self.action_id, "action_id")
        require_nonempty_text(self.symbol, "symbol")
        if self.action_type not in ACTION_TYPES:
            raise MarketDataError(f"unsupported corporate-action type: {self.action_type!r}")
        parsed = urlsplit(require_nonempty_text(self.source_url, "source_url"))
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise MarketDataError("source_url must be an uncredentialed HTTPS URL")
        require_sha256(self.source_sha256)
        if type(self.revision) is not int or self.revision < 1:
            raise MarketDataError("revision must be a positive integer")
        if self.revision == 1 and self.supersedes_sha256 is not None:
            raise MarketDataError("first revision cannot supersede another source")
        if self.revision > 1:
            require_sha256(self.supersedes_sha256, "supersedes_sha256")
            if self.supersedes_sha256 == self.source_sha256:
                raise MarketDataError("a revision cannot supersede itself")
        require_aware_datetime(self.available_at, "available_at")
        require_aware_datetime(self.effective_at, "effective_at")
        for name, value in (
            ("ex_date", self.ex_date),
            ("record_date", self.record_date),
            ("pay_date", self.pay_date),
        ):
            if value is not None:
                require_date(value, name)
        if self.action_type == "split":
            self._validate_split()
        elif self.action_type == "cash_dividend":
            self._validate_cash_dividend()
        else:
            self._validate_symbol_change()

    def _validate_split(self) -> None:
        if (
            not is_finite_number(self.split_ratio)
            or self.split_ratio <= 0.0
            or math.isclose(float(self.split_ratio), 1.0, rel_tol=0.0, abs_tol=0.0)
        ):
            raise MarketDataError("split_ratio must be finite, positive, and not one")
        if self.ex_date is None or self.effective_at.date() != self.ex_date:
            raise MarketDataError("split effective_at date must equal ex_date")
        if (self.record_date is None) != (self.pay_date is None):
            raise MarketDataError("split record_date and pay_date must be both present or absent")
        if self.record_date is not None:
            assert self.pay_date is not None
            if not self.ex_date <= self.record_date <= self.pay_date:
                raise MarketDataError(
                    "split dates must satisfy ex_date <= record_date <= pay_date"
                )
        if any(
            value is not None for value in (self.cash_amount, self.currency, self.new_symbol)
        ):
            raise MarketDataError("split cannot contain dividend or symbol-change fields")

    def _validate_cash_dividend(self) -> None:
        if not is_finite_number(self.cash_amount) or self.cash_amount <= 0.0:
            raise MarketDataError("cash_amount must be finite and positive")
        if (
            not isinstance(self.currency, str)
            or len(self.currency) != 3
            or not self.currency.isalpha()
            or self.currency != self.currency.upper()
        ):
            raise MarketDataError("currency must be a three-letter uppercase code")
        if self.ex_date is None or self.record_date is None or self.pay_date is None:
            raise MarketDataError("cash dividend requires ex, record, and pay dates")
        if not self.ex_date <= self.record_date <= self.pay_date:
            raise MarketDataError("dividend dates must satisfy ex_date <= record_date <= pay_date")
        if self.effective_at.date() != self.ex_date:
            raise MarketDataError("dividend effective_at date must equal ex_date")
        if self.split_ratio is not None or self.new_symbol is not None:
            raise MarketDataError("cash dividend cannot contain split or symbol-change fields")

    def _validate_symbol_change(self) -> None:
        new_symbol = require_nonempty_text(self.new_symbol, "new_symbol")
        if new_symbol == self.symbol:
            raise MarketDataError("new_symbol must differ from symbol")
        if any(
            value is not None
            for value in (
                self.ex_date,
                self.record_date,
                self.pay_date,
                self.split_ratio,
                self.cash_amount,
                self.currency,
            )
        ):
            raise MarketDataError("symbol change cannot contain split or distribution fields")


def select_action_revision(
    actions: tuple[CorporateAction, ...] | list[CorporateAction],
    available_at_cutoff: datetime,
) -> CorporateAction:
    """Return the newest complete revision available at a point in time."""

    cutoff = require_aware_datetime(available_at_cutoff, "available_at_cutoff")
    frozen = tuple(actions)
    if not frozen:
        raise MarketDataError("corporate-action revision chain is empty")
    identity = (frozen[0].action_id, frozen[0].action_type, frozen[0].symbol)
    if any((item.action_id, item.action_type, item.symbol) != identity for item in frozen):
        raise MarketDataError("corporate-action revisions must share one identity")
    ordered = tuple(sorted(frozen, key=lambda item: item.revision))
    if tuple(item.revision for item in ordered) != tuple(range(1, len(ordered) + 1)):
        raise MarketDataError("corporate-action revisions must be contiguous from one")
    hashes = tuple(item.source_sha256 for item in ordered)
    if len(hashes) != len(set(hashes)):
        raise MarketDataError("corporate-action revision hashes must be unique")
    for previous, current in zip(ordered, ordered[1:]):
        if current.supersedes_sha256 != previous.source_sha256:
            raise MarketDataError("corporate-action revision chain is broken")
        if current.available_at < previous.available_at:
            raise MarketDataError("corporate-action revision availability must be monotonic")
    available = tuple(item for item in ordered if item.available_at <= cutoff)
    if not available:
        raise MarketDataError("no corporate-action revision was available by the cutoff")
    return available[-1]
