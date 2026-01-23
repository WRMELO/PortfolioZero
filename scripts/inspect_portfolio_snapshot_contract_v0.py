from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def try_git(cmd: List[str]) -> Optional[str]:
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return None


def grep_consumers(repo_root: Path) -> Dict[str, List[str]]:
    patterns = [
        "PORTFOLIO_SNAPSHOT_V0.json",
        "PORTFOLIO_SNAPSHOT",
        "portfolio_snapshot",
        "data/portfolio/",
    ]

    hits: List[str] = []
    for pat in patterns:
        try:
            out = subprocess.check_output(
                ["grep", "-RIn", pat, "scripts", "modules", "config"],
                cwd=str(repo_root),
                text=True,
                stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                if not line.strip():
                    continue
                file_path = line.split(":", 1)[0]
                hits.append(file_path)
        except Exception:
            pass

    unique = sorted(set(hits))
    return {"patterns": patterns, "files": unique}


def summarize_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    keys_top = sorted(list(snapshot.keys()))

    positions = snapshot.get("positions")
    positions_type = type(positions).__name__

    pos_len = None
    pos_keys_union: List[str] = []
    pos_keys_sample: List[List[str]] = []
    pos_first_sample: Optional[Dict[str, Any]] = None

    if isinstance(positions, list):
        pos_len = len(positions)
        union = set()
        for i, p in enumerate(positions[:20]):
            if isinstance(p, dict):
                k = sorted(list(p.keys()))
                pos_keys_sample.append(k)
                union |= set(k)
                if i == 0:
                    pos_first_sample = p
        pos_keys_union = sorted(list(union))

    return {
        "top_level_keys": keys_top,
        "positions_type": positions_type,
        "positions_len": pos_len,
        "positions_keys_union": pos_keys_union,
        "positions_keys_sample_first_5": pos_keys_sample[:5],
        "positions_first_item_sample": pos_first_sample,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--report-dir", required=True)
    args = ap.parse_args()

    repo_root = Path.cwd()
    snapshot_path = Path(args.snapshot)
    run_dir = Path(args.run_dir)
    report_dir = Path(args.report_dir)

    run_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    if not snapshot_path.exists():
        errors.append({"code": "SNAPSHOT_NOT_FOUND", "file": str(snapshot_path)})
        report = {
            "repo": str(repo_root),
            "head": try_git(["git", "rev-parse", "HEAD"]) or "UNKNOWN",
            "created_at_utc": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "snapshot_path": str(snapshot_path),
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings,
        }
        out_run = run_dir / "REPORT_PORTFOLIO_SNAPSHOT_CONTRACT_V0.json"
        out_rep = report_dir / "REPORT_PORTFOLIO_SNAPSHOT_CONTRACT_V0.json"
        out_run.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        out_rep.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("STATUS=FAIL (snapshot not found)")
        return 2

    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if not isinstance(snapshot, dict):
            errors.append({"code": "SNAPSHOT_NOT_DICT", "type": type(snapshot).__name__})
            snapshot = {}
    except Exception as e:
        errors.append({"code": "SNAPSHOT_INVALID_JSON", "error": str(e)})
        snapshot = {}

    consumer_map = grep_consumers(repo_root)
    snapshot_summary = summarize_snapshot(snapshot) if isinstance(snapshot, dict) else {}

    created_at_utc = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    git_head = try_git(["git", "rev-parse", "HEAD"]) or "UNKNOWN"
    git_branch = try_git(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "UNKNOWN"

    report: Dict[str, Any] = {
        "repo": str(repo_root),
        "head": git_head,
        "head_meta": {
            "git_branch": git_branch,
            "created_at_utc": created_at_utc,
            "task_id": "TASK_A_015",
        },
        "snapshot_path": str(snapshot_path),
        "snapshot_contract_v0": snapshot_summary,
        "consumers_scan": consumer_map,
        "warnings": warnings,
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
    }

    out_run = run_dir / "REPORT_PORTFOLIO_SNAPSHOT_CONTRACT_V0.json"
    out_rep = report_dir / "REPORT_PORTFOLIO_SNAPSHOT_CONTRACT_V0.json"
    out_run.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_rep.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("STATUS=", report["status"])
    print("snapshot_path=", report["snapshot_path"])
    print("top_level_keys=", report["snapshot_contract_v0"].get("top_level_keys"))
    print("positions_type=", report["snapshot_contract_v0"].get("positions_type"))
    print("positions_len=", report["snapshot_contract_v0"].get("positions_len"))
    print("consumers_files_count=", len(report["consumers_scan"].get("files", [])))
    print("report_run_path=", str(out_run))
    print("report_report_path=", str(out_rep))

    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
