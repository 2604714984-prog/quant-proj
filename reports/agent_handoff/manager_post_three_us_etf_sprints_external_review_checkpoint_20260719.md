# Manager checkpoint after three US ETF result sprints

Date: 2026-07-19
Repository: `2604714984-prog/quant-proj`
Controlling main commit: `c56db93b4df2d9b7006c03676708a9de7232ab4b`
Status: `EXTERNAL_REVIEW_REQUIRED_BEFORE_NEXT_STRATEGY`

## Purpose

The three result sprints authorized by the accepted post-PR-94 program are now
terminal. This checkpoint asks the external reviewer to verify the combined
interpretation before the Manager opens a fourth strategy lineage. It is not a
request to retune, rerun, promote, shadow, paper trade, or trade any strategy.

## Exact terminal evidence

| Sprint | Merged PR | Result status | Gates | Result SHA-256 | Decisive failures |
|---|---:|---|---:|---|---|
| SPY/QQQ/GLD dual momentum with cash | #96 | `RETROSPECTIVE_DUAL_MOMENTUM_FAIL` | 7/8 | `9c22a877c13e783b73a164f49569c7a3ddb9739721af7ad973bb7f4a94337f65` | Combined validation-plus-holdout Calmar did not exceed the static equal-weight comparator. |
| SPY/QQQ/GLD inverse volatility | #98 | `RETROSPECTIVE_INVERSE_VOLATILITY_FAIL` | 6/10 | `42772cd61d660e7fab1359bfeeae71d92e656d96fcdf58463b2b54a1f5cab541` | Holdout and combined Calmar, 30-bps robustness, and the four-test adjusted inference family failed. |
| SPY/GLD stress safe-haven sleeve | #100 | `RETROSPECTIVE_STRESS_SAFE_HAVEN_FAIL` | 7/10 | `92cecfef384d243797b1783532a190009c3cff1cdd692751b208569f7dca4ba4` | Holdout Calmar versus the identically timed SPY stress sleeve, 30-bps robustness/concentration, and all four adjusted inference tests failed. |

All three results were produced from committed and remotely pinned code, used
one frozen variant, passed input qualification before result consumption, and
received independent result acceptance. Their exact historical runs are
consumed and must not be reopened or repaired.

## What the third result actually showed

The safe-haven sleeve was not an input failure. It used 5,436 exact common
SPY/GLD sessions through 2026-06-30 and passed the sample, identity, positive
CAGR, drawdown and positive-active-interval gates.

At 15 bps one way, its GLD/cash sleeve reported:

- validation CAGR `0.3392%`;
- retrospective-holdout CAGR `1.8131%`;
- combined CAGR `1.0952%` and cumulative net return `19.6656%`;
- combined positive active-interval fraction `54.8673%`.

Those positive numbers are insufficient for acceptance. In the holdout, the
GLD sleeve Calmar was `0.09284`, below the identically timed SPY stress sleeve
at `0.12671`. At 30 bps, GLD-sleeve combined maximum drawdown was `-28.08%`
versus `-22.61%` for the SPY stress sleeve, and its largest positive-year
contribution was `51.37%`, above the frozen `40%` ceiling. All four Holm-family
tests had negative simultaneous lower bounds.

## Program-level conclusion

The lightweight engine is producing reproducible numerical decisions. The
current bottleneck is not another architecture rewrite. The three tested ETF
mechanisms did not meet their own frozen comparison and inference standards.

Therefore:

- `strategy_candidate_available=false`;
- no exact mechanism or parameter from these three sprints may be rerun;
- rejected legacy `US31`, `US36`, `US41` and `US46` remain closed;
- no prospective-forward, shadow, paper, broker, live, or automatic path is
  authorized;
- infrastructure improvements may support a genuinely new lineage but cannot
  rescue these results.

## Manager proposal for the next phase

Do not start another code-writing strategy before this checkpoint is reviewed.
After acceptance, use a narrow two-step program:

1. Produce one outcome-free feasibility shortlist of at most three genuinely
   distinct US economic mechanisms. Each entry must name its primary economic
   prior, exact data already available or one bounded missing-data action, and
   its duplicate/failure-memory screen. No return values or parameter grid may
   be opened in this step.
2. Select exactly one feasible mechanism, freeze one variant, and run one
   result sprint under the existing lightweight engine. A result PASS again
   stops before merge for exact-head external review; an ordinary correct FAIL
   is preserved and closed without retuning.

The preferred search order is:

1. a genuinely new US mechanism executable on already qualified daily ETF
   inputs;
2. a stock-level mechanism only if survivor-aware membership, delisting,
   corporate-action and availability identities are already sufficient;
3. no new formal result if neither condition is met.

Do not build a data platform, agent framework, regime router, or broker path as
part of this decision.

## Questions for external review

1. Are PRs #96, #98 and #100 correctly interpreted as three terminal ordinary
   retrospective failures rather than architecture or input failures?
2. Is the prohibition on rerunning the exact mechanisms and legacy US lines
   sufficiently explicit?
3. Is the proposed `at most three feasibility entries -> exactly one frozen
   result` sequence narrow enough to prevent broad result mining while still
   prioritizing actual numerical output?
4. Should any shared semantic or result-calculation issue be fixed before that
   next shortlist? If none, please explicitly say that no architecture rework
   is required.

## Validation and boundaries

- PR #100 exact-head CI: green, run `29689742353`.
- Local exact committed-code suite: `821 passed`.
- Safe-haven result and receipt independent acceptance: `VALID`.
- Central database SHA-256 before/after:
  `e636bb80e300f89e46831e91275c6f2167e370e81a00b21b300e253f6107bee0`.
- Database write: false; provider/network use: false; prospective-forward
  access: false; candidate promotion: false; trading activation: false.

External review should bind its verdict to the exact PR HEAD containing this
file. Any later commit requires a fresh incremental review.
