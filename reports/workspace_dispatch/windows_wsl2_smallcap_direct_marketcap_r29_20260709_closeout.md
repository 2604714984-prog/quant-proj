# R29 Direct MarketCap Closeout

Batch: `WINDOWS_WSL2_SMALLCAP_DIRECT_MARKETCAP_R29_20260709`

Closeout status: `CLOSED_ACCEPTED_RESEARCH_ONLY_DIRECT_MARKET_CAP_UNAVAILABLE_NO_PROBE_ELIGIBLE`

R29 is closed as a narrow evidence-resolution batch. It did not materialize direct decision-date market-cap membership. SmallCap local-probe reconsideration remains stopped until new accepted direct market-cap source evidence exists.

Final counts:

- `local_research_probe_eligible_count=0`
- `wide_research_probe_eligible_count=0`
- `strategy_candidate_available=false`

Required carry-forward warning:

- Do not retry SmallCap local-probe reconsideration on a proxy-only market-cap premise.
- Direct total/float market-cap decision-date membership remains unavailable from accepted sources.
- Current-only quote fields are not sufficient for R28/R29 historical decision-date membership.

Boundary result: `PASS_RESEARCH_ONLY`.
