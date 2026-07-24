# US SEC company-facts PIT data V1

This is a data-only capability. It does not define, rank, backtest, or promote a
strategy.

- Universe: distinct mapped symbols that appeared in the disclosed QQQ top 50
  under holdings snapshot `qqq_nport_pit_20260723_a10cf2fcdafa4dd8`.
- Mapping snapshot: `qqq_identity_complete_20260723_767fbc6dbfa92cb9`.
- Source: SEC `company_tickers.json` and per-CIK `companyfacts` JSON.
- Availability: SEC `filed` date; fiscal period end is never used as the
  availability date.
- Forms: `10-K`, `20-F`, and `40-F`.
- Concepts: US GAAP `NetIncomeLoss` and `Assets`, plus IFRS `ProfitLoss` and
  `Assets`.
- Raw responses and normalized rows stay under `QUANT_DATA_ROOT`.
- Central target: `us_equity_research.us_sec_companyfacts_pit_research`.
- Natural key: `(snapshot_id, row_sha256)`.
- Qualification: at least 80 percent of mapped historical symbols must have
  both an annual income concept and annual assets from 2017 onward.

The loader is append-only and idempotent. It must complete a dry-run
qualification before `--execute --input-run <qualified-run>` is allowed. The
execute phase reuses the exact captured `rows.json` bytes and performs no
provider requests. No current rankings, portfolio
weights, paper trading, broker integration, live trading, or automation are
part of this capability.
