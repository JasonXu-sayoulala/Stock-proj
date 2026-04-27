from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_PY = PROJECT_ROOT / "main.py"
EXPECTED_IMPORTED_CODES = ["002747", "300024", "688017"]
EXPECTED_PAUSED_CODES = ["002050"]


@dataclass
class CommandResult:
    name: str
    command: list[str]
    required: bool
    returncode: int
    duration_seconds: float
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_process(command: list[str], *, name: str, required: bool = True, timeout: int = 180) -> CommandResult:
    start = time.time()
    try:
        proc = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return CommandResult(
            name=name,
            command=command,
            required=required,
            returncode=proc.returncode,
            duration_seconds=round(time.time() - start, 3),
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
        )
    except subprocess.TimeoutExpired:
        return CommandResult(
            name=name,
            command=command,
            required=required,
            returncode=124,
            duration_seconds=round(time.time() - start, 3),
            stdout="",
            stderr=f"timeout after {timeout}s",
        )


def project_command(args: list[str]) -> list[str]:
    return [sys.executable, str(MAIN_PY), *args]


def parse_json(text: str) -> Any | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def code_list(value: Any) -> list[str]:
    if not value:
        return []
    result: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict) and item.get("code"):
                result.append(str(item["code"]))
    return sorted(set(result))


def command_summary(result: CommandResult) -> dict[str, Any]:
    parsed = parse_json(result.stdout)
    summary: dict[str, Any] = {
        "name": result.name,
        "required": result.required,
        "passed": result.passed,
        "returncode": result.returncode,
        "duration_seconds": result.duration_seconds,
    }
    if isinstance(parsed, dict):
        for key in [
            "status",
            "record_count",
            "valid_record_count",
            "issue_counts",
            "all_passed",
            "summary",
            "trade_date",
            "has_differences",
        ]:
            if key in parsed:
                summary[key] = parsed[key]
        if isinstance(parsed.get("data_quality"), dict):
            dq = parsed["data_quality"]
            summary["data_quality"] = {
                "status": dq.get("status"),
                "summary_text": dq.get("summary_text"),
                "issue_counts": dq.get("issue_counts"),
            }
        if isinstance(parsed.get("source_summary"), dict):
            summary["source_summary"] = parsed["source_summary"]
    elif result.stdout:
        summary["stdout_preview"] = result.stdout[:800]
    if result.stderr:
        summary["stderr_preview"] = result.stderr[:1200]
    return summary


def git_snapshot() -> dict[str, Any]:
    head = run_process(["git", "log", "-1", "--oneline"], name="git_head", required=False, timeout=30)
    branch = run_process(["git", "branch", "--show-current"], name="git_branch", required=False, timeout=30)
    status = run_process(["git", "status", "--short"], name="git_status", required=False, timeout=30)
    changed = [line.strip() for line in status.stdout.splitlines() if line.strip()]
    return {
        "branch": branch.stdout or None,
        "head": head.stdout or None,
        "is_clean": status.passed and not changed,
        "changed_files": changed,
        "git_available": head.passed and status.passed,
    }


def http_check(web_url: str | None) -> dict[str, Any] | None:
    if not web_url:
        return None
    base = web_url.rstrip("/")
    checks = []
    for path in ["/dashboard", "/rules"]:
        url = base + path
        start = time.time()
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                status = int(getattr(response, "status", 0) or 0)
                checks.append({"url": url, "ok": 200 <= status < 400, "status": status, "duration_seconds": round(time.time() - start, 3)})
        except urllib.error.HTTPError as exc:
            checks.append({"url": url, "ok": False, "status": exc.code, "error": str(exc), "duration_seconds": round(time.time() - start, 3)})
        except Exception as exc:
            checks.append({"url": url, "ok": False, "status": None, "error": str(exc), "duration_seconds": round(time.time() - start, 3)})
    return {"base_url": base, "all_ok": all(item["ok"] for item in checks), "checks": checks}


def artifact_paths(trade_date: str) -> dict[str, Path]:
    output_dir = PROJECT_ROOT / "outputs" / trade_date
    return {
        "review_snapshot_json": output_dir / "review_snapshot.json",
        "review_snapshot_markdown": output_dir / "review_snapshot.md",
        "daily_close_brief_markdown": output_dir / "daily_close_brief.md",
        "manifest_json": output_dir / "manifest.json",
        "latest_manifest_json": PROJECT_ROOT / "outputs" / "latest_manifest.json",
    }


def artifact_snapshot(trade_date: str) -> dict[str, Any]:
    paths = artifact_paths(trade_date)
    return {
        "output_dir": f"outputs/{trade_date}",
        "expected_files": {name: path.exists() for name, path in paths.items()},
        "review_snapshot": read_json(paths["review_snapshot_json"]),
        "manifest": read_json(paths["manifest_json"]),
        "latest_manifest": read_json(paths["latest_manifest_json"]),
    }


def review_summary_from_payload(review: Any) -> dict[str, Any]:
    if not isinstance(review, dict):
        return {"exists": False, "readable": False}
    data_quality = review.get("data_quality") or {}
    source_summary = review.get("source_summary") or {}
    missing = review.get("missing_trusted_fields") or {}
    watchlist = review.get("watchlist") or []
    return {
        "exists": True,
        "readable": True,
        "data_quality_status": data_quality.get("status"),
        "data_quality_summary": data_quality.get("summary_text"),
        "watchlist_count": len(watchlist) if isinstance(watchlist, list) else None,
        "manual_names": source_summary.get("manual_names") or [],
        "rule_names": source_summary.get("rule_names") or [],
        "imported_effective_contribution_names": code_list(source_summary.get("imported_effective_contribution_names")),
        "missing_entry_zone_codes": code_list(missing.get("missing_entry_zone_codes")),
        "next_imported_contribution_candidates": review.get("next_imported_contribution_candidates") or [],
        "paused_imported_contribution_candidates": review.get("paused_imported_contribution_candidates") or [],
    }


def load_review_summary(trade_date: str) -> dict[str, Any]:
    return review_summary_from_payload(read_json(PROJECT_ROOT / "outputs" / trade_date / "review_snapshot.json"))


def write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
