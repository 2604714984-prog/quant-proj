# PR #54 Relative-Strength V3 Terminal Checkpoint

Date: 2026-07-16
Market: A-share
Phase: execution and adjudication
Research ID: `A_SHARE_RELATIVE_STRENGTH_MEDIUM_TERM_MOMENTUM_V1_20260715`
Run ID: `A_SHARE_RELATIVE_STRENGTH_HISTORICAL_SECONDARY_SCREEN_V3_20260716`

## Terminal decision

`HISTORICAL_SCREENING_FAIL`. V3 is consumed and closed: no retry, retune, or candidate promotion is authorized. `strategy_candidate_available=false`. Any future work must start from a genuinely new economic hypothesis, a new lineage identity, and a new outcome-blind preregistration.

## Controlling lineage

- PR #54 preserved the accepted terminal V2 `INPUT_BLOCKED` evidence and closed that run without reuse: merge `c48e09604949519d8192fd6a6c46f9ea82a11e80`, tree `a2a5fbb113d1abf5e0ad3148f74cea1b5b697112`; V2 result SHA-256 `e1e34e1653a6ad8c35a21703ebb75af5bcfedfcfc1c15347ed13bc8bba963b13`; V2 receipt SHA-256 `8b2779a534a5d559397e3bba83b02cc7df5affc6ffbc323c00e934fb62f9bb97`.
- PR #55 implemented the narrow market fix: a buy whose theoretical slipped price crosses the up-limit is unfilled as `slippage_crosses_up_limit`; the symmetric sell case is `slippage_crosses_down_limit`; neither price is capped. Merge `470391da92f74086b797fc36ea5cc48ba322cd0e`, market module SHA-256 `ecb528e9de4b7422cb5c919d57237208b4039089e3e64c87352c4dd08a31872d`.
- PR #56 separated fresh run identity from consumed V1/V2 identities. V3 executed from source commit `33c6ab3c00a026842a5961cc4c00b3e495275d0f`, tree `da864acddd5e72b34122912bdaa1b8cfcd0fbe43`; runner SHA-256 `8ac3046de8a2fccc604cfbbbee5525b9b7a08bb215f5c326be3833c6224f5100`.

## Qualified input and preflight

- The V4 HALF_UP tick-rounding repair was append-published once. Central DuckDB SHA-256 is `ff493d9a85537fed85de3b98eb54f097ac1349475138bc076864385edec347ff`; publication receipt SHA-256 is `c83f8d49961802298e80c44a2b1339e8e105342d2103e2822150968c9e248985`; superseding consumer manifest SHA-256 is `88766149e1c9ec44aea656dce04f36a850bc736f303b284c07ffbb44f29dca96`. It binds 4,720,765 rows, 2,910 symbols, 2018-01-02 through 2026-06-30, 2,058 benchmark rows, ordered-row hash `6a2b4b18e9e5c7f27e2e69043f8bbe293ba711e5f03a61fdf8ec4503860c2be2`, and target digest `969c65ef944099ee916ed8699bdfa65432a6cb2e6ef28c65139b7922941e26be`.
- Outcome-free preflight-v2 script SHA-256 is `8ea1008f66f64388ccfb7f176b262dd28fe484ff9bc400f40cbfc73c1230b064`; result SHA-256 is `7af2d30c1c1c0ea59d4f9dc8af39979c637cc9d75b1900ccb8ad2b1448d18c3f`; independent acceptance SHA-256 is `c9e8a356775bb917065bc6848098964c1ebd1f7a9f402363be8c2b4ba5da7e6a`.
- Its exact aggregate counters were: `filled=6194`, `limit_up_buy_rejected=86`, `limit_down_sell_rejected=48`, `slippage_crosses_up_limit=21`, `slippage_crosses_down_limit=0`, `capacity_rejected=5739`, `insufficient_cash=0`, and `unexpected_exception_count=0`.

## Exactly-once V3 evidence

- V3 data manifest SHA-256: `b4cfe55963636872c35db2d8030ae697138efebe513d3ea0288071a8e768a0ad`.
- Wrapper SHA-256: `26d81e4300f86f6259dda558ae3f431eb33f353e3bf78e6448004bf34da3fe9d`.
- Permanent consumed-marker SHA-256: `fdba0339199ff25d1e59c7476df30f7db6758e77bafa35f2a178be3006a18c69`.
- Result SHA-256: `10293246fc3a6e5a408ee89c6fa1e4c47f2761a4474728e95ee98dfc70f5c14e`.
- Run-receipt SHA-256: `720c7a05276ee41244e6310a6000c6539cc2f8db782b45e286e63045b3734fb8`.
- Preregistration SHA-256: `84a0d0c80e2e072caf13474873e92de0a2ce7edc4878bcdad2006dfdd46a02ac`; amendment SHA-256: `72621319dcc24c67bb02f56eda2f972320026dd89c3d5bbb96de0962d7038a1e`; input qualification SHA-256: `d96e6e46babc5633f4e57e483d397c97f352f4b9f76bf02bc8882e24e20b945b`.
- Independent post-run review verdict: `VALID`, findings none.

## Mechanical adjudication

The frozen run produced 8 historical tests across validation and retrospective holdout only, with 208 complete 20-bps holding intervals. Validation samples were 23 intervals per variant and retrospective-holdout samples were 29 intervals per variant.

Gate count was 16/48. In every test, the two integrity/sample gates passed: `minimum_complete_holding_intervals` and `no_invalid_decision_or_missing_mark`. The four performance gates failed: positive mean monthly active return, positive Bonferroni one-sided lower bound, Bonferroni one-sided p-value threshold, and strategy annualized net return exceeding the benchmark. This is negative historical screening evidence, not strict strategy evidence.

## Boundary result

The V3 preflight and outcome run opened no prospective-forward outcomes, used no provider or network, and performed no database write. Results contain no security identifiers. No recommendation, ranking, candidate, readiness, product route, signal, or trading action was created. The accepted result cannot be repaired by retrying or retuning this lineage.
