"""Bounded PIT profitability data smoke using the pinned repository endpoint."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import requests

import run_us_top50_strategy_followups_v1 as core


REPO_COMMIT = "d52a8a0013363577bceb28ca876c88fe6c1a5aeb"
CONTRACT_SHA = "137a489a4722a9fac6ec7fbf9eeb2bd0918f14c1c2032c37fe6d9661d9a42982"
RESIDUAL_RESULT_SHA = ""
URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SEC_UA = "quant-proj-research/2.0 (+https://github.com/2604714984-prog/quant-proj)"
SEC_PREFLIGHT_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
SMOKE = {
    "technology": "AAPL.O",
    "retailer": "WMT.N",
    "financial": "JPM.N",
    "multi_class": "GOOGL.O",
    "duplicate_revision_probe": "MSFT.O",
}
REPORTS = {
    "income": "RPT_USF10_FN_INCOME",
    "balance": "RPT_USF10_FN_BALANCE",
}


class Blocked(RuntimeError):
    pass


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def dump(path: Path, value: Any) -> None:
    core.dump(path, value)


def timestamp_fields(rows: list[dict[str, Any]]) -> list[str]:
    tokens = ("NOTICE", "ANNOUN", "PUBLISH", "ACCEPT", "DISCLOS", "DECLARE")
    return sorted(
        key
        for key in {key for row in rows for key in row}
        if any(token in key.upper() for token in tokens)
        and any(row.get(key) not in (None, "") for row in rows)
    )


def item_matches(rows: list[dict[str, Any]], tokens: tuple[str, ...]) -> list[str]:
    matches = set()
    for row in rows:
        item = str(row.get("ITEM_NAME") or row.get("STD_ITEM_NAME") or "")
        if any(token.lower() in item.lower() for token in tokens):
            matches.add(item)
    return sorted(matches)


def analyze(company_rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    income, balance = company_rows["income"], company_rows["balance"]
    all_rows = income + balance
    periods = sorted({str(row.get("REPORT_DATE")) for row in all_rows if row.get("REPORT_DATE")})
    timestamp = timestamp_fields(all_rows)
    gross = item_matches(income, ("gross profit", "毛利"))
    revenue = item_matches(income, ("revenue", "营业收入", "营收"))
    cost = item_matches(income, ("cost of revenue", "营业成本", "销售成本"))
    assets = item_matches(balance, ("total assets", "资产总计", "总资产"))
    currencies = sorted({str(row.get("CURRENCY")) for row in all_rows if row.get("CURRENCY")})
    report_groups: dict[tuple[str, str, str], int] = {}
    for row in all_rows:
        key = (str(row.get("REPORT_DATE")), str(row.get("REPORT_TYPE")), str(row.get("STD_ITEM_CODE")))
        report_groups[key] = report_groups.get(key, 0) + 1
    return {
        "row_counts": {"income": len(income), "balance": len(balance)},
        "period_count": len(periods),
        "timestamp_fields": timestamp,
        "gross_profit_items": gross,
        "revenue_items": revenue,
        "cost_items": cost,
        "total_assets_items": assets,
        "currencies": currencies,
        "duplicate_report_item_groups": sum(count > 1 for count in report_groups.values()),
        "gates": {
            "four_periods": len(periods) >= 4,
            "public_timestamp": bool(timestamp),
            "gross_profit_constructible": bool(gross) or (bool(revenue) and bool(cost)),
            "total_assets": bool(assets),
            "currency": bool(currencies),
        },
    }


def fetch(secucode: str, kind: str, raw_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params = {
        "reportName": REPORTS[kind],
        "columns": "ALL",
        "filter": f'(SECUCODE="{secucode}")',
        "pageNumber": "1",
        "pageSize": "500",
        "sortColumns": "REPORT_DATE",
        "sortTypes": "-1",
        "source": "WEB",
        "client": "WEB",
    }
    retrieved_at = datetime.now(timezone.utc).isoformat()
    response = requests.get(URL, params=params, headers={"User-Agent": UA}, timeout=20)
    name = f"{secucode.replace('.', '_')}_{kind}.json"
    path = raw_dir / name
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(response.content)
    temporary.replace(path)
    metadata = {
        "secucode": secucode,
        "kind": kind,
        "url": response.url,
        "retrieved_at": retrieved_at,
        "http_status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "bytes": len(response.content),
        "sha256": sha(path),
        "raw_path": str(path),
    }
    if response.status_code != 200:
        raise Blocked(f"eastmoney_http:{secucode}:{kind}:{response.status_code}")
    payload = response.json()
    rows = (payload.get("result") or {}).get("data") or []
    if not rows:
        raise Blocked(f"eastmoney_empty:{secucode}:{kind}")
    return rows, metadata


def smoke(repo: Path, pinned_repo: Path, root: Path) -> dict[str, Any]:
    residual = root.parent / "us_top50_residual_profitability_v1/residual_result.json"
    if sha(repo / "research/definitions/us_top50_residual_profitability_v1.json") != CONTRACT_SHA:
        raise Blocked("contract_changed")
    if not residual.exists() or json.loads(residual.read_text()).get("result") != "DISCOVERY_FAIL":
        raise Blocked("residual_failure_not_frozen")
    import subprocess

    commit = subprocess.check_output(["git", "-C", str(pinned_repo), "rev-parse", "HEAD"], text=True).strip()
    if commit != REPO_COMMIT:
        raise Blocked("pinned_repo_commit_changed")
    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest, analyses = [], {}
    for role, secucode in SMOKE.items():
        rows = {}
        for kind in REPORTS:
            rows[kind], metadata = fetch(secucode, kind, raw_dir)
            manifest.append(metadata)
        analyses[role] = {"secucode": secucode, **analyze(rows)}
    gates = {
        "five_company_roles": len(analyses) == 5,
        "all_responses": len(manifest) == 10,
        "all_four_periods": all(row["gates"]["four_periods"] for row in analyses.values()),
        "all_public_timestamp": all(row["gates"]["public_timestamp"] for row in analyses.values()),
        "all_gross_profit_constructible": all(row["gates"]["gross_profit_constructible"] for row in analyses.values()),
        "all_total_assets": all(row["gates"]["total_assets"] for row in analyses.values()),
        "all_currency": all(row["gates"]["currency"] for row in analyses.values()),
    }
    result = {
        "identity": "US_TOP50_GROSS_PROFITABILITY_V1",
        "phase": "PIT_DATA_SMOKE",
        "result": "PROFITABILITY_DATA_SMOKE_PASS" if all(gates.values()) else "PROFITABILITY_DATA_INPUT_BLOCKED",
        "provider": "Eastmoney via pinned global-stock-data",
        "repository_commit": commit,
        "analyses": analyses,
        "manifest": manifest,
        "gates": gates,
        "strategy_outcomes_accessed": False,
        "strategy_candidate_available": False,
    }
    dump(root / "profitability_smoke_result.json", result)
    return result


def sec_preflight(root: Path) -> dict[str, Any]:
    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    response = requests.get(
        SEC_PREFLIGHT_URL,
        headers={"User-Agent": SEC_UA, "Accept": "application/json"},
        timeout=20,
    )
    path = raw_dir / "sec_companyfacts_preflight.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(response.content)
    temporary.replace(path)
    metadata = {
        "url": response.url,
        "retrieved_at": retrieved_at,
        "http_status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "bytes": len(response.content),
        "sha256": sha(path),
        "raw_path": str(path),
        "user_agent": SEC_UA,
        "retry_count": 0,
    }
    valid = False
    if response.status_code == 200:
        payload = response.json()
        valid = bool(payload.get("facts", {}).get("us-gaap"))
    result = {
        "identity": "US_TOP50_GROSS_PROFITABILITY_V1",
        "phase": "SEC_COMPANYFACTS_PREFLIGHT",
        "result": "SEC_ROUTE_SMOKE_PASS" if valid else "PROFITABILITY_DATA_INPUT_BLOCKED",
        "metadata": metadata,
        "reason": None if valid else "SEC companyfacts unavailable from the single compliant preflight; no retry or identity change",
        "strategy_outcomes_accessed": False,
        "strategy_candidate_available": False,
    }
    dump(root / "sec_preflight_result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("eastmoney", "sec-preflight"), default="eastmoney")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--pinned-repo", type=Path, required=True)
    parser.add_argument("--staging", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = sec_preflight(args.staging) if args.phase == "sec-preflight" else smoke(args.repo, args.pinned_repo, args.staging)
    except (Blocked, OSError, ValueError, requests.RequestException, json.JSONDecodeError) as exc:
        args.staging.mkdir(parents=True, exist_ok=True)
        result = {"result": "PROFITABILITY_DATA_INPUT_BLOCKED", "failure": f"{type(exc).__name__}:{exc}", "strategy_outcomes_accessed": False, "strategy_candidate_available": False}
        dump(args.staging / "profitability_smoke_result.json", result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["result"] in {"PROFITABILITY_DATA_SMOKE_PASS", "SEC_ROUTE_SMOKE_PASS"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
