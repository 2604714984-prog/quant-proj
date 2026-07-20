# US mechanism falsification evidence scout week

Date: 2026-07-21
Batch: `US_MECHANISM_FALSIFICATION_SCOUT_WEEK_20260720`
Control HEAD: `037827f85becec1c706c679402a313fcf23922fc`
Task SHA256: `9317cbb98ed7c5d3d23c20b9cb32f70a524b71b448f8f23371eaebf3d5e83f0f`

## Scope and reading rule

This is an outcome-blind literature falsification pass over exactly ten frozen Atlas mechanisms. It does not read local prices or returns, fit a model, choose parameters, modify Atlas, create a mechanism, or authorize an outcome run. A classification describes prior-evidence strength and implementation risk; it is not a strategy recommendation or promotion decision.

Counts: `PRIOR_REMAINS_STRONG=0`, `PRIOR_MIXED=2`, `PRIOR_WEAK_AFTER_COSTS=3`, `PRIOR_REPLICATION_SENSITIVE=3`, `PRIOR_DATA_CONTRACT_DOMINATES=2`.

## 1. USDEM-004 — macroeconomic announcement premium

- Classification: `PRIOR_REPLICATION_SENSITIVE`.
- Support: Savor and Wilson report high average US equity returns on scheduled macro announcement days over 1958–2007; their event taxonomy is Employment Situation, scheduled FOMC decisions, and CPI through January 1971 followed by PPI. [Savor–Wilson manuscript](https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2014/04/0906.pdf) Wachter and Zhu find large announcement-day premia and a stronger beta-return relation. [NBER w24432](https://www.nber.org/papers/w24432)
- Contrary/limit: a later reassessment attributes much of the average to monetary-policy surprises and small-sample components and finds volatility patterns inconsistent with a large general premium. [Management Science, 2026](https://pubsonline.informs.org/doi/10.1287/mnsc.2024.06960)
- Microcap/period: not primarily a microcap result, but inference is concentrated in a small number of event days and therefore period-sensitive.
- Short leg: no; the published aggregate-market claim does not require one.
- Long-only preservation: possible only after reproducing the exact event taxonomy and window; the frozen six-family union is not the original taxonomy.
- Costs: low turnover may leave room after costs, but the claimed daily mean is small and cannot absorb event-time slippage without measurement.
- PIT observability: official release calendars and timestamps are observable, but revisions, rescheduling, unscheduled FOMC actions, timezone, and collision handling require immutable identities.
- Post-publication: evidence is mixed rather than uniformly durable.
- ETF/cash benchmark: an SPY-versus-cash implementation may express the aggregate claim, but may also absorb most of the economic effect; it cannot validate the broader six-family union.
- Shadow evidence speed: medium; official calendars are compact, but historical timestamp and revision qualification is the bottleneck.
- Implementation risk: taxonomy drift is decisive. PCE, advance GDP, and ISM cannot be silently added under the Savor–Wilson label, while GDP/ISM belong to a distinct mostly-overnight literature.
- Local falsifier: reject the local formulation if its exact frozen event set and timing cannot be matched to a pre-specified primary paper before any return join.

## 2. USDEM-006 — pre-holiday premium

- Classification: `PRIOR_MIXED`; this does not reopen the separately parked input-blocked lane.
- Support: Ariel finds eight pre-holiday days per year account for more than one-third of 1963–1982 market returns. [Journal of Finance DOI](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1990.tb03731.x) Robins and Smith report persistence in value-weighted and low-size CRSP portfolios through 2016, while also noting sample dependence. [SSRN 3298365](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3298365)
- Contrary/limit: Keef and Roush find the S&P 500 effect greatly diminished after 1987. [Applied Financial Economics DOI](https://doi.org/10.1080/0960310042000293164) A further out-of-sample study finds the effect largely becomes a small-firm effect, with large-firm differences insignificant, especially after 1990. [Critical Finance Review](https://ideas.repec.org/a/now/jnlcfr/104.00000111.html)
- Microcap/period: yes, later evidence is materially size- and subperiod-sensitive.
- Short leg: no; the basic claim is long market on pre-holidays versus cash otherwise.
- Long-only preservation: economically possible, but only with a complete historical XNYS calendar and unchanged holiday definition.
- Costs: infrequent trading helps, but a weak large-cap effect can be absorbed by spreads and close/open implementation differences.
- PIT observability: scheduled holidays are observable; unscheduled closures, delayed openings, and historical early-close rules remain the hard identity problem.
- Post-publication: materially weakened in some post-1987/post-1990 samples.
- ETF/cash benchmark: likely absorbs the intended aggregate exposure and is the correct simple comparator; it does not solve the calendar contract.
- Shadow evidence speed: slow under the frozen 2010–2026H1 XNYS contract because missing official historical exceptions, not computation, blocks the lane.
- Implementation risk: replacing XNYS with Nasdaq or shortening the period changes the frozen claim.
- Local falsifier: keep the mechanism parked if any session classification depends on inferred or cross-market calendar evidence.

## 3. USDEM-012 — session decomposition V2

- Classification: `PRIOR_WEAK_AFTER_COSTS`.
- Support: Cliff, Cooper, and Gulen document positive close-to-open and near-zero or negative open-to-close returns across US stocks, indexes, and futures. [SSRN 1004081](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1004081)
- Contrary/limit: Lachance shows ETF overnight returns can be mechanically inflated by order imbalances and widening overnight bid-ask spreads. [Journal of Financial Markets DOI](https://doi.org/10.1016/j.finmar.2020.100563) Nasdaq's SPY reconstruction reports that roughly 0.004% daily total cost nearly removes the historical gain and that consistency weakens after 2001. [Nasdaq, Night and Day](https://www.nasdaq.com/articles/night-and-day)
- Microcap/period: not only microcaps, but ETF evidence is venue-, quote-, and period-sensitive.
- Short leg: no for the long overnight sleeve; shorting the daytime sleeve would add borrow and leverage risks not required by the frozen design.
- Long-only preservation: weak; a long overnight/cash daytime rule is implementable, but the net edge is close to the execution-cost boundary.
- Costs: yes, plausible spreads, crossing, and twice-daily turnover can exceed the effect.
- PIT observability: timestamps are observable, but executable open/close prices, auction participation, stale quotes, distributions, and overnight corporate actions need strict identities.
- Post-publication: the effect is inconsistent in later samples and at least one dedicated product implementation closed.
- ETF/cash benchmark: directly absorbs the economic claim; the question is net executable excess versus buy-and-hold/cash, not raw session arithmetic.
- Shadow evidence speed: fast with qualified auction/quote data; current daily bars alone are insufficient.
- Implementation risk: midpoint or unadjusted closes can manufacture the spread.
- Local falsifier: reject if a conservative executable-price and cost reconstruction removes the overnight-minus-daytime advantage.

## 4. STK_01 — 52-week-high proximity

- Classification: `PRIOR_WEAK_AFTER_COSTS`.
- Support: George and Hwang show proximity to the 52-week high predicts cross-sectional returns. [Journal of Finance DOI](https://doi.org/10.1111/j.1540-6261.2004.00695.x) An international study finds positive spreads in 18 of 20 markets. [Journal of International Money and Finance](https://www.sciencedirect.com/science/article/abs/pii/S0261560610001099)
- Contrary/limit: the international paper also finds significance after transaction costs in only a minority of markets. A liquid-stock replication reports positive raw results but no significant dollar profit after short-sale, liquidity, and trading-cost constraints. [Australian Journal of Management DOI](https://doi.org/10.1177/0312896210385282)
- Microcap/period: not exclusively microcap, but raw spreads and significance are stronger outside the most investable implementations.
- Short leg: much of the published test is a winner-minus-loser spread; omitting the short leg weakens identification.
- Long-only preservation: uncertain; top-proximity selection may collapse toward ordinary momentum or market beta.
- Costs: likely material because monthly cross-sectional replacement and small-name exposure can consume the spread.
- PIT observability: adjusted historical highs, split timing, delistings, security type, and eligible-universe history are required.
- Post-publication: cross-market evidence exists, but net implementability is weak.
- ETF/cash benchmark: a broad ETF may absorb market exposure but cannot establish stock-selection alpha; cash does not address momentum overlap.
- Shadow evidence speed: medium with survivor-complete adjusted daily bars; slow otherwise.
- Implementation risk: using a current universe or retroactively adjusted highs creates survivorship or corporate-action leakage.
- Local falsifier: reject if the long-only top bucket fails to beat an equal-risk total-momentum comparator after conservative costs.

## 5. STK_04 — short-term residual reversal

- Classification: `PRIOR_MIXED`.
- Support: Blitz and coauthors report residual reversal after controlling for common factors, including net-of-cost results in large caps after 1990. [SSRN 1911449](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1911449)
- Contrary/limit: Chiang, Kirby, and Nie find no monthly reversal in the highest-turnover quintile; high-turnover, news-driven moves can continue instead. [SSRN 3369648](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3369648) Recent evidence likewise finds reversal declines with turnover and proximity to the 52-week high, sometimes becoming momentum. [Journal of Empirical Finance](https://www.sciencedirect.com/science/article/abs/pii/S0927539824000902)
- Microcap/period: not limited to microcaps, but liquidity and information environment change the sign.
- Short leg: classical residual-reversal evidence is strongest as a long-short spread; frozen long-only losers omit half of it.
- Long-only preservation: possible but conditional; it risks loading on distressed, low-liquidity, or news-continuation names.
- Costs: five-day turnover makes spreads and impact first-order even where gross reversal exists.
- PIT observability: factor residuals, split-adjusted returns, tradability, news/ex-event exclusions, and survivor-complete universe must be contemporaneous.
- Post-publication: mixed; credible large-cap evidence exists, but state dependence and sign reversals are substantial.
- ETF/cash benchmark: neither absorbs cross-sectional residual selection; an ordinary short-term reversal comparator is necessary to isolate residualization.
- Shadow evidence speed: medium; daily data suffice mechanically, but qualified factor and event identities do not.
- Implementation risk: choosing turnover or 52-week-high filters after seeing results would turn limitations into parameter search.
- Local falsifier: reject if the fixed long-only residual-loser portfolio does not exceed plain reversal after costs without ex-post conditioning.

## 6. FND_01 — post-earnings-announcement drift

- Classification: `PRIOR_WEAK_AFTER_COSTS`.
- Support: Bernard and Thomas document predictable post-announcement returns related to standardized unexpected earnings. [Journal of Accounting and Economics manuscript](https://deepblue.lib.umich.edu/bitstream/handle/2027.42/28288/0000041.pdf)
- Contrary/limit: Chordia and coauthors find only 0.04% monthly drift in the most liquid stocks versus 2.43% in illiquid stocks and estimate costs consume 70–100% of profits. [Financial Analysts Journal DOI](https://doi.org/10.2469/faj.v65.n4.3) Martineau reports disappearance in large stocks after 2006 and recently in microcaps. [SSRN 3111607](https://ssrn.com/abstract=3111607)
- Microcap/period: yes, the remaining gross effect is concentrated in illiquid names and earlier periods.
- Short leg: conventional evidence uses positive-minus-negative surprise; a long-positive-only sleeve gives up half the spread.
- Long-only preservation: possible as a directional signal, but likely much smaller in liquid, executable stocks.
- Costs: likely exceed the modern liquid-stock effect once event-time spreads and turnover are included.
- PIT observability: original as-filed earnings, analyst expectations or frozen seasonal model, announcement timestamp, revision chain, splits, and next executable open are mandatory.
- Post-publication: materially weakened or disappeared in several modern samples.
- ETF/cash benchmark: neither isolates PEAD; sector/size/earnings-event controls are needed, but must be frozen before outcomes.
- Shadow evidence speed: slow because surprise identity and announcement-time PIT qualification dominate.
- Implementation risk: restated fundamentals or date-only announcements introduce lookahead and mistimed entry.
- Local falsifier: reject if the fixed liquid long-only positive-surprise sleeve has no conservative net excess over its pre-specified event control.

## 7. FND_07 — filing delay

- Classification: `PRIOR_DATA_CONTRACT_DOMINATES`.
- Support: Chambers and Penman establish that reporting timeliness contains price-relevant information. [Journal of Accounting Research record](https://ideas.repec.org/a/bla/joares/v22y1984i1p21-47.html) Penman's related 1971–1976 strategy study finds roughly 1% pre-cost abnormal returns over 20 days from shorting late reporters and about 1% from long early reporters with good news. [Columbia summary and citation](https://business.columbia.edu/faculty/research/abnormal-returns-investment-strategies-based-timing-earnings-reports)
- Contrary/limit: the original effect is larger in small firms and relies heavily on the short-late leg. A later Russell 3000 study still finds negative late-filer returns but warns that event-study returns are difficult to capture and that late filers tilt small and distressed. [S&P Global study](https://www.spglobal.com/content/dam/spglobal/mi/en/documents/general/sp-capital-iq-quantamental-late-to-file-the-costs-of-delayed-10-q-and-10-k-company-filings.pdf)
- Microcap/period: materially small-firm and old-sample sensitive.
- Short leg: central to the strongest original claim; long-only avoidance/cash is a different and likely weaker payoff.
- Long-only preservation: not established by the original short-late result.
- Costs: event timing, small-name liquidity, and borrow can exceed a roughly 1% gross 20-day effect.
- PIT observability: requires filer-status-specific statutory deadlines, form type, fiscal year-end, EDGAR acceptance time, Form 12b-25, extension/grace rules, amendments, and issuer-specific seasonal cadence.
- Post-publication: later evidence supports a distress signal but not a clean, low-cost long-only premium.
- ETF/cash benchmark: cash is the natural result of avoidance, making incremental value depend on correctly identifying a tradable foregone loss.
- Shadow evidence speed: slow; EDGAR is public, but historical deadline and cadence reconstruction is labor-intensive.
- Implementation risk: a seasonal-date shortcut can label lawful deadline changes or fiscal-calendar shifts as delays.
- Local falsifier: reject before outcomes if the system cannot reproduce each issuer's legally applicable deadline and public acceptance timestamp.

## 8. FND_16 — cluster insider purchases

- Classification: `PRIOR_REPLICATION_SENSITIVE`.
- Support: Lakonishok and Lee find insider purchases informative, particularly in smaller firms. [NBER w6656](https://www.nber.org/papers/w6656) Alldredge and Blank report more than 2% next-month abnormal returns after clustered purchases. [Journal of Financial Research DOI](https://doi.org/10.1111/jfir.12172)
- Contrary/limit: a 2026 working paper using PIT S&P 500 membership and 2015–2024 Form 4 data finds overlapping observations can inflate cluster-buy significance; it is recent, non-peer-reviewed falsification evidence. [SSRN 6883638](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6883638) The SEC's 2022 rule amended Forms 4/5 to identify Rule 10b5-1 plan transactions, creating a reporting-regime break from 2023. [SEC final rule](https://www.sec.gov/rules-regulations/2022/12/insider-trading-arrangements-related-disclosures)
- Microcap/period: purchase informativeness is stronger in small firms; modern large-cap evidence is sensitive to sampling and overlap.
- Short leg: no for a purchase-only signal.
- Long-only preservation: plausible, but only after deduplicating overlapping event windows and excluding non-discretionary or planned transactions consistently.
- Costs: one-month holding helps, but small-name spreads and clustered entries remain material.
- PIT observability: Form 4 acceptance time is observable; transaction code, owner identity, amendment chain, direct/indirect ownership, plan status, and duplicate filings must be frozen.
- Post-publication: not decisively gone, but inference is replication-sensitive and disclosure fields changed.
- ETF/cash benchmark: a market ETF absorbs beta but not issuer-level information; size/liquidity controls matter.
- Shadow evidence speed: medium for recent EDGAR XML, slow for comparable pre-2023 plan classification.
- Implementation risk: treating multiple filings or overlapping windows as independent trials inflates effective sample size.
- Local falsifier: reject if significance disappears after issuer-level non-overlapping event clustering and the pre-specified disclosure-regime split.

## 9. FND_22 — asset growth

- Classification: `PRIOR_REPLICATION_SENSITIVE`.
- Support: Cooper, Gulen, and Schill report total asset growth as a strong cross-sectional predictor and state that the relation survives large-cap restrictions. [SSRN 760967](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=760967)
- Contrary/limit: O'Donovan finds earnings-management-related growth components no longer predict returns and links disappearance to Sarbanes–Oxley. [SSRN 3886280](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3886280) Fu finds the anomaly is almost fully driven by delisting and external-financing observations. [SMU paper](https://ink.library.smu.edu.sg/cgi/viewcontent.cgi?article=5493&context=lkcsb_research)
- Microcap/period: not claimed to be only microcap, but delisting, financing events, and regulatory period materially affect results.
- Short leg: the original low-minus-high growth spread relies on high-growth underperformance; a low-growth long-only sleeve is weaker identification.
- Long-only preservation: uncertain after controlling value, quality, financing, and delisting effects.
- Costs: quarterly turnover is moderate, but distressed/delisting and small-name execution can dominate realized returns.
- PIT observability: first-as-filed total assets, filing acceptance time, fiscal-period identity, amendments, mergers, IPOs, delistings, and security history are required.
- Post-publication: evidence indicates weakening after SOX and sensitivity to special observations.
- ETF/cash benchmark: a broad ETF may absorb much of low-growth firms' factor exposure; cash does not isolate an asset-growth effect.
- Shadow evidence speed: slow because as-filed XBRL revision lineage and survivor-complete returns dominate.
- Implementation risk: using later-restated Compustat-style values or dropping delistings can create a different result in either direction.
- Local falsifier: reject if the fixed first-as-filed long-only low-growth sleeve loses excess return after pre-specified delisting and external-financing treatment.

## 10. USIOT-008 — variance risk premium

- Classification: `PRIOR_DATA_CONTRACT_DOMINATES`.
- Support: Bollerslev, Tauchen, and Zhou show that a model-free implied-variance measure less expected realized variation predicts aggregate stock returns. [Review of Financial Studies](https://ideas.repec.org/a/oup/rfinst/v22y2009i11p4463-4492.html) Federal Reserve evidence finds the US variance risk premium predicts US and foreign equity returns. [IFDP 1035](https://www.federalreserve.gov/pubs/ifdp/2011/1035/ifdp1035.htm)
- Contrary/limit: Federal Reserve measurement guidance describes VRP as model-free option-implied variance minus a conditional expectation of realized variance and explains why high-frequency realized variance is used; substituting subsequent realized variance directly in the signal creates lookahead. [Federal Reserve FEDS 2010-14](https://www.federalreserve.gov/pubs/FEDS/2010/201014/) The predictive evidence does not imply a simple long-only variance trade, and direct short-variance exposure carries crash and margin risk.
- Microcap/period: aggregate-market rather than microcap, but option-market regime and crisis periods dominate the distribution.
- Short leg: no for using VRP to time equity exposure; yes for directly harvesting option variance premium, which is outside the frozen long-only mechanism.
- Long-only preservation: possible only as pre-specified equity timing; it is not equivalent to selling variance.
- Costs: equity timing costs may be modest, while option implementation costs, spreads, collateral, and tail losses are first-order.
- PIT observability: full option surface, exact quotes, rates, dividends, maturity interpolation, high-frequency realized-variance history, and an ex-ante physical forecast are required at decision time.
- Post-publication: cross-country predictability supports the prior, but measurement choices and crisis concentration make replication fragile.
- ETF/cash benchmark: ETF/cash directly absorbs the equity-timing expression and is the appropriate simple baseline; it cannot validate a variance-swap payoff.
- Shadow evidence speed: slow; no shortcut from VIX minus future realized variance is admissible.
- Implementation risk: fixed-maturity interpolation, stale option quotes, and an ex-post realized-variance subtraction can manufacture the predictor.
- Local falsifier: reject before outcomes if the signal cannot be reconstructed entirely from decision-time option and realized-variance information with no future window.

## Cross-mechanism conclusion

No mechanism receives `PRIOR_REMAINS_STRONG`. Three are plausibly real but weak after executable costs, three are replication-sensitive, two have mixed evidence, and two are dominated by PIT data-contract feasibility. This pass narrows evidentiary expectations; it does not select a mechanism or authorize data/outcome access.

```text
BATCH=US_MECHANISM_FALSIFICATION_SCOUT_WEEK_20260720
STATUS=COMPLETE_PRIORS_WEAKENED_NO_OUTCOME
MECHANISMS_REVIEWED=10
STRONG_PRIOR_COUNT=0
MIXED_PRIOR_COUNT=2
WEAK_AFTER_COSTS_COUNT=3
REPLICATION_SENSITIVE_COUNT=3
DATA_CONTRACT_DOMINATES_COUNT=2
REPORT_URL=https://github.com/2604714984-prog/quant-proj/blob/evidence/week-f-mechanism-falsification-20260721/reports/validation/us_mechanism_falsification_scout_week_20260721.md
ATLAS_MODIFIED=false
PRICE_ACCESS=false
OUTCOME_ACCESS=false
DATABASE_WRITE=false
```
