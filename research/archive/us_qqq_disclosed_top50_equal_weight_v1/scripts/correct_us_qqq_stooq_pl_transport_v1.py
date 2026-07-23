"""Run the frozen Stooq continuation with only the host corrected to stooq.pl."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import continue_us_qqq_top50_mapping_v1 as mapping
import continue_us_qqq_top50_prices_v1 as continuation
import acquire_us_qqq_top50_prices_v1 as prices
import smoke_us_qqq_disclosed_top50_v1 as smoke


FAILED_STOOQ_SHA256 = (
    "c7a4c240e5f016b423ae9d77ed9bc8316350fba69b09c338e9c61c1b5274659a"
)
STOOQ_PL = "https://stooq.pl/q/d/l/"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--staging-root",
        type=Path,
        default=Path(
            "/home/rongyu/workspace/quant-data/staging/"
            "us_qqq_disclosed_top50_equal_weight_v1/stooq_pl_transport"
        ),
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("/home/rongyu/workspace/quant-data/quant_research.duckdb"),
    )
    parser.add_argument(
        "--result",
        type=Path,
        default=Path(
            "research/results/"
            "us_qqq_disclosed_top50_equal_weight_v1_stooq_pl_transport_20260723.json"
        ),
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    failed = (
        repo_root
        / "research/results/"
        "us_qqq_disclosed_top50_equal_weight_v1_price_continuation_20260723.json"
    )
    if mapping._sha256_file(failed) != FAILED_STOOQ_SHA256:
        raise SystemExit("preserved Stooq .com failure result changed")
    result_path = (
        (repo_root / args.result).resolve()
        if not args.result.is_absolute()
        else args.result.resolve()
    )
    prices.STOOQ_BASE = STOOQ_PL
    result = continuation.run(
        repo_root,
        args.staging_root.resolve(),
        args.database.resolve(),
        result_path,
    )
    contract = (
        repo_root
        / "research/definitions/"
        "us_qqq_disclosed_top50_equal_weight_v1_stooq_pl_transport.json"
    )
    result.update(
        {
            "execution_id": (
                "US_QQQ_DISCLOSED_TOP50_EQUAL_WEIGHT_V1_STOOQ_PL_TRANSPORT"
            ),
            "phase": "PRICE_INPUT_TRANSPORT_CORRECTION",
            "contract": {
                "path": str(contract),
                "sha256": mapping._sha256_file(contract),
            },
            "preserved_stooq_com_failure": {
                "path": str(failed),
                "sha256": mapping._sha256_file(failed),
            },
        }
    )
    smoke._write_json_atomic(result_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"].startswith("PRICE_INPUTS_QUALIFIED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
