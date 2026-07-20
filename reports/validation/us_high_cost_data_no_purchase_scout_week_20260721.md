# US High-Cost Data No-Purchase Scout — Terminal Report

Date: 2026-07-21
Batch: `US_HIGH_COST_DATA_NO_PURCHASE_SCOUT_WEEK_20260720`
Status: `COMPLETE_NO_PURCHASE_MARKET_MAP`
Control PR #111 HEAD: `037827f85becec1c706c679402a313fcf23922fc`
Task SHA256: `da5032f17007fa85e1b068d883eb2f4aeb01c20ab1ce4c799718cc004c422a76`
Repository base: `6751fa4f3acf30e41a06cb6f90c0d8c50abdc095`

## Decision

Current free official sources can solve event and filing identity, but not the historical intraday, option-chain, or earnings-call transcript contracts. No purchase, trial, account, sample download, SDK, API key, or integration is justified before a mechanism specialist proves that the exact frozen history and fields can change a research decision.

## Route matrix

| Route | Coverage and format observed on official page | Personal-use / redistribution / public price | Mechanisms and decisive gap | Recommendation |
|---|---|---|---|---|
| [NYSE Daily TAQ](https://beta.nyse.com/data-products/catalog/daily-taq) | Consolidated US equity trades, quotes, NBBO, master and admin files; historical 1993-present; flat files; sample link | Purchase and data agreement required; public price not shown; redistribution terms not established here | Only inspected route that visibly reaches a 1994-start intraday contract; execution evidence still needs exchange calendar, corrections and licensed storage terms | `CONSIDER_ONLY_AFTER_HISTORICAL_SPECIALIST_PASS` |
| [NYSE TAQ Order Imbalances](https://beta.nyse.com/market-data/historical/taq-order-imbalances) | Opening/closing imbalance messages; NYSE history from 2008-05-14, American from 2008-12-01, Arca from 2012-01-30 | Purchase required; public price not shown; exchange agreement applies | Useful for auction mechanisms, but cannot satisfy a 1994-start contract | `REJECT_COVERAGE_OR_LICENSE_MISMATCH` |
| [Cboe Option Quotes](https://datashop.cboe.com/option-quote-intervals) | Listed US stock/ETF/index options; 1-minute or N-minute NBBO, sizes, OHLCV; optional IV, Greeks and open interest; product page says 2012-present | Historical or subscription purchase; public sample offered; index underlier fields can require a separate license starting at USD 1,000/month | Large storage footprint; no futures options; product-page start conflicts with the FAQ's 2010 start and must be resolved before contracting | `CONSIDER_ONLY_AFTER_HISTORICAL_SPECIALIST_PASS` |
| [Cboe Volatility Surfaces](https://datashop.cboe.com/volatility-surfaces) | Four interpolated surface forms; daily zipped CSV; history from 2011-08 | Historical purchase or subscription; price generated after selections; model methodology is vendor-controlled | Could support skew/term-structure research, but starts too late for older contracts and is not a raw-chain substitute | `DEFER_NO_CLEAR_VALUE` |
| [Cboe Option Sentiment specification](https://datashop.cboe.com/Documents/Cboe_OptionSentiment_Specs.pdf) | Daily underlying-level call/put volume, trades, size, premium and related aggregates; FAQ states history from 2012 | Paid daily/historical product; redistribution terms not qualified | Aggregated sentiment may save engineering, but removes contract-level reconstruction and inherits vendor classifications | `DEFER_NO_CLEAR_VALUE` |
| [Massive Stocks](https://massive.com/docs/rest/stocks) | REST/flat-file stocks, minute aggregates, trades, quotes, reference, corporate actions and inactive tickers | [Public plans](https://massive.com/pricing?product=stocks): USD 0 with 2 years, USD 29 with 5 years, USD 79 with 10 years, USD 199 with 20+ years; account required; redistribution not qualified | Convenient recent research route, but visible plan history does not establish a 1994 start or terminal-value completeness | `REJECT_COVERAGE_OR_LICENSE_MISMATCH` |
| [Databento equities and futures](https://databento.com/) | Direct equities/SIP and futures datasets with tick schemas; historical and live APIs; dataset-specific history | Usage pricing or flat plans; USD 125 new-user credits require signup; no purchase made; exchange licensing varies | Potential raw intraday/futures route, but the exact venue/start/license matrix is not frozen on the overview | `CONSIDER_ONLY_AFTER_HISTORICAL_SPECIALIST_PASS` |
| [Databento security master](https://databento.com/security-master) and [corporate actions](https://databento.com/docs/schemas-and-data-formats/corporate-actions) | PIT security identity for listed/delisted securities and 60+ event types with record-change timestamps | Reference service requires account/plan; redistribution not qualified | Strong supporting identity layer, not execution-price evidence; 18-year security-master history cannot prove older completeness | `SAMPLE_REVIEW_WORTHWHILE_WITH_USER_APPROVAL` |
| [LSEG Event Transcripts and Briefs](https://www.lseg.com/content/dam/data-analytics/en_us/documents/brochures/lseg-harvesting-insights-from-text-unstructured-text-and-analytics-brochure.pdf) | History from 2001; about 36,000 transcripts/summaries yearly and about 1,500 live companies; event, speaker and document metadata | Contact/enterprise route; no public personal price; text redistribution is not qualified | Direct earnings-call text route, but coverage continuity, revisions, entitlement and reproducible export remain unknown | `CONSIDER_ONLY_AFTER_HISTORICAL_SPECIALIST_PASS` |
| [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Free public submissions and XBRL APIs plus nightly bulk archives; no authentication | Official free access subject to SEC fair-access policy; filings are public; project redistribution still limited to derived metadata/hashes | Preferred for filings and structured facts; does not provide proprietary earnings-call transcripts | `OFFICIAL_FREE_ROUTE_PREFERRED` |
| [Federal Reserve FOMC archive](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) | Official schedules, statements and meeting materials; statement pages can state release time | Official free public source | Preferred for event-time identity; supplies no market minute bars or execution prices | `OFFICIAL_FREE_ROUTE_PREFERRED` |
| [BLS release calendar and archives](https://www.bls.gov/schedule/) | Official schedules and release archives for BLS series | Official free public source | Preferred for event identity; mutable/rescheduled calendar lineage must still be proven and it supplies no market data | `OFFICIAL_FREE_ROUTE_PREFERRED` |

## Contract-field normalization

All rows have `source_last_checked=2026-07-21`. `UNKNOWN_NOT_PUBLIC` is a fail-closed observation, not an inference of absence.

| Product | Asset / frequency / history | Hours / timezone | Raw-adjusted, actions, symbols, delisted, PIT | Delivery / format | Personal license / redistribution / minimum visible price / no-account sample |
|---|---|---|---|---|---|
| NYSE Daily TAQ | US equities; tick/daily files; 1993-current | Exact regular/extended-hours inclusion and timestamp convention require specification-level qualification | Raw trades/quotes; master/admin messages; adjustments, full symbol history, delisted and PIT contract not qualified | Bulk flat files | Agreement required / not qualified / quote / yes |
| NYSE Order Imbalances | US equities auctions; intraday messages; 2008-current depending venue | Auction windows; ET | Raw imbalance feed; no adjustment or full lifecycle contract qualified | Bulk flat files | Agreement required / not qualified / quote / yes |
| Cboe Option Quotes | US listed options; 1/N-minute; 2012-current on product page | Regular and GTH coverage depends product; ET | Raw quotes/trade aggregates plus optional calculated IV/Greeks; action, symbol, expired-contract and PIT completeness unqualified | Bulk zipped CSV | Purchase required / not qualified / CGI from USD 1,000 monthly for some index fields / yes |
| Cboe Volatility Surfaces | US listed options analytics; daily; 2011-08-current | 16:00 and eligible 16:15 ET snapshots | Vendor-adjusted/model-derived; corporate-action and expired-contract lineage not qualified | Bulk zipped CSV | Purchase required / not qualified / selection-priced / no public file observed |
| Cboe Option Sentiment | US listed options aggregates; daily; 2012-current per FAQ | Daily ET files | Vendor-classified aggregates; no chain, action or contract-history reconstruction | Bulk zipped CSV | Purchase required / not qualified / quote or selection-priced / specification only |
| Massive Stocks | US equities; minute/tick/daily; visible plan windows 2, 5, 10, 20+ years | Pre/regular/post-market; ET | Raw/aggregate prices; corporate-action and inactive ticker endpoints; terminal values and immutable PIT revisions unqualified | REST, WebSocket, flat files | Individual plans / not qualified / USD 0, 29, 79, 199 monthly / account required |
| Databento equities/futures | US equities and global futures; tick to bars; dataset-specific history | Venue sessions; UTC normalized timestamps | Raw direct/SIP feeds; time-series action handling and symbol history need separate reference products | API and batch DBN/CSV | Usage/flat pricing plus venue fees / not qualified / dataset-specific / credits require signup |
| Databento reference | Global securities/actions; weekly master and multi-daily actions; about 18 years PIT master history | Not session-bound; UTC/local dates | PIT master and 60+ actions; listed/delisted coverage advertised; exact US terminal-value contract unqualified | Reference API, CSV/JSON/Parquet samples | Plan required / not qualified / quote or plan / one-click samples advertised |
| LSEG Event Transcripts | Global event text; event-driven; history from 2001 | Event timestamps; timezone contract not qualified | Edited transcript/brief content and PermID speaker metadata; revisions and immutable PIT export unqualified | Workspace/feed formats not qualified | Enterprise/contact / restrictive and unqualified / quote / no |
| SEC EDGAR | US filings/XBRL; real-time APIs and nightly bulk; API coverage by filing history | Filing timestamps in EDGAR conventions | Original filings, accessions and amendments; issuer CIK but no tradable-symbol lifecycle or price adjustments | JSON APIs and ZIP bulk | Official free fair access / public-source limits apply / USD 0 / yes |
| Federal Reserve FOMC | US macro events; meeting/statement schedule; archive-current | Published release times in ET | Official source and revision pages; no security actions, symbols or market data | HTML/PDF | Official free / public-source limits / USD 0 / yes |
| BLS schedule/archive | US macro events; monthly/periodic releases; archive-current | Published ET schedule | Official schedule/releases; reschedule-version PIT chain not automatically complete; no market data | HTML/ICS/PDF depending route | Official free / public-source limits / USD 0 / yes |

## Category findings

### Intraday and market structure

- Daily TAQ is the only reviewed product whose published history visibly spans the frozen 1994 start, but its purchase price and personal storage/redistribution terms are not public in the inspected material.
- NYSE imbalance history begins in 2008, Massive's visible maximum is 20+ years, and Databento requires a dataset-by-dataset history check. None can silently replace a 1994-start contract.
- Official Fed/BLS timestamps solve only event identity. A minute feed does not prove first-publication time, and an event archive does not prove an executable quote.

### Options

- Cboe exposes useful quote, IV/Greek, surface and sentiment products, but their visible histories begin in 2011-2012 and their calculated fields embed vendor models.
- The Cboe FAQ and current Option Quotes product page disagree on the start year. A purchase decision requires a dated written entitlement and coverage confirmation.
- Full option-chain reconstruction needs bid/ask, open interest, expirations, corporate-action handling, expired contracts and underlying identity; no single inspected summary page proves all of them.

### Text and transcripts

- LSEG is the direct transcript route but lacks public personal pricing and qualified redistribution/export terms.
- SEC EDGAR is the preferred free route for filings, amendments, accessions and XBRL facts. It is not a replacement for earnings-call audio or proprietary transcripts.

## User decision gate

No user decision is required now. Reopen procurement only after a frozen mechanism passes an outcome-blind specialist review that states exact dates, fields, venue coverage, acceptable license, expected storage size and a maximum budget. At that point, inspect a public sample or request a written quote; do not start a trial automatically.

## Callback

```text
BATCH=US_HIGH_COST_DATA_NO_PURCHASE_SCOUT_WEEK_20260720
STATUS=COMPLETE_NO_PURCHASE_MARKET_MAP
ROUTES_REVIEWED=12
INTRADAY_ROUTE_COUNT=4
OPTIONS_ROUTE_COUNT=3
TEXT_ROUTE_COUNT=2
FREE_OFFICIAL_ROUTES=3
PAID_ROUTES=9
SAMPLE_REVIEW_CANDIDATES=1
PURCHASES_MADE=0
TRIALS_STARTED=0
ACCOUNTS_CREATED=0
REPORT_URL=https://github.com/2604714984-prog/quant-proj/blob/evidence/week-e-high-cost-scout-20260721/reports/validation/us_high_cost_data_no_purchase_scout_week_20260721.md
STRATEGY_RESULT_ACCESS=false
DATABASE_WRITE=false
NEXT_USER_DECISION_REQUIRED=NONE_UNTIL_MECHANISM_SPECIALIST_PASS
```

## Boundary receipt

Only public official documentation was inspected. No account, trial, purchase, credential, sample, SDK, provider call, price/return result, strategy, database, candidate, Paper, Broker or Live path was accessed or created.
