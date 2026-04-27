from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from phase2_operator_common import PROJECT_ROOT, command_summary, now_iso, project_command, run_process, write_json, write_markdown


def build_commands(trade_date: str, base_date: str | None, skip_markdown_compare: bool):
    commands = [
        ("validate_imported_levels", ["validate_imported_levels"], True, 120),
        ("validate_manual_levels", ["validate_manual_levels"], True, 120),
        ("daily", ["daily", "--date", trade_date], True, 240),
        ("validate_consistency", ["validate_consistency", "--date", trade_date], True, 180),
        ("review_snapshot_json", ["review_snapshot", "--date", trade_date], True, 180),
        ("review_snapshot_markdown", ["review_snapshot", "--date", trade_date, "--format", "markdown"], True, 180),
        ("export_daily_artifacts", ["export_daily_artifacts", "--date", trade_date], True, 180),
    ]
    if base_date:
        commands.append(("compare_daily_artifacts_json", ["compare_daily_artifacts", "--base-date", base_date, "--target-date", trade_date], False, 180))
        if not skip_markdown_compare:
            commands.append(("compare_daily_artifacts_markdown", ["compare_daily_artifacts", "--base-date", base_date, "--target-date", trade_date, "--format", "markdown"], False, 180))
    return commands


def render_markdown(payload: dict) -> list[str]:
    lines = [
        "# Phase 2 Daily Dry-run Summary",
        "",
        f"- Trade date: {payload['trade_date']}",
        f"- Base date: {payload.get('base_date') or '-'}",
        f"- Generated at: {payload['generated_at']}",
        f"- Overall status: {payload['overall_status']}",
        "",
        "## Commands",
    ]
    for item in payload["command_summaries"]:
        icon = "✅" if item["passed"] else ("⚠️" if not item["required"] else "❌")
        lines.append(f"- {icon} `{item['name']}`")
        for key in ["status", "record_count", "valid_record_count", "all_passed", "summary", "has_differences"]:
            if key in item:
                lines.append(f"  - {key}: {item[key]}")
        if "data_quality" in item:
            dq = item["data_quality"]
            lines.append(f"  - data_quality: {dq.get('status')} | {dq.get('summary_text')}")
        if "stdout_preview" in item:
            lines.append(f"  - output: {item['stdout_preview']}")
        if "stderr_preview" in item:
            lines.append(f"  - stderr: {item['stderr_preview']}")
    lines += [
        "",
        "## Guardrails",
        "- This dry-run does not edit manual/imported truth sources.",
        "- This dry-run does not generate numeric levels.",
        "- `002050.entry_zone` remains paused unless a cleaner same-day structured source is approved.",
    ]
    return lines


def run_dry_run(trade_date: str, base_date: str | None, skip_markdown_compare: bool) -> dict:
    results = []
    for name, args, required, timeout in build_commands(trade_date, base_date, skip_markdown_compare):
        result = run_process(project_command(args), name=name, required=required, timeout=timeout)
        results.append(result)
        if required and not result.passed:
            break
    required_failures = [r for r in results if r.required and not r.passed]
    optional_failures = [r for r in results if (not r.required) and not r.passed]
    status = "failed" if required_failures else ("warning" if optional_failures else "passed")
    payload = {
        "trade_date": trade_date,
        "base_date": base_date,
        "generated_at": now_iso(),
        "overall_status": status,
        "required_failure_count": len(required_failures),
        "optional_failure_count": len(optional_failures),
        "command_summaries": [command_summary(r) for r in results],
        "commands": [asdict(r) for r in results],
    }
    out = PROJECT_ROOT / "outputs" / trade_date
    write_json(out / "dry_run_summary.json", payload)
    write_markdown(out / "dry_run_summary.md", render_markdown(payload))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Stock-proj Phase 2 daily dry-run workflow.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--base-date")
    parser.add_argument("--skip-markdown-compare", action="store_true")
    args = parser.parse_args()
    payload = run_dry_run(args.date, args.base_date, args.skip_markdown_compare)
    print(json.dumps({k: v for k, v in payload.items() if k != "commands"}, ensure_ascii=False, indent=2))
    return 0 if payload["overall_status"] in {"passed", "warning"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
