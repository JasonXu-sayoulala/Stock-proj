# Phase 2 Stable Daily Runbook

## Purpose

This runbook is the stable daily operating guide for Stock-proj Phase 2.

It documents the accepted daily validation, run, review, artifact export, compare, web check, and handoff flow.

This document is operational only. It must not be used to justify filling low-confidence numeric levels.

## Current accepted baseline

Latest locally confirmed main:

```text
0b32e4b
```

Reference trade date:

```text
2026-05-19
```

Current accepted baseline results:

```text
validate_imported_levels: valid, record_count=3, valid_record_count=3
validate_manual_levels: valid, record_count=5, valid_record_count=5
daily --date 2026-05-19: passed, watchlist=4
validate_consistency --date 2026-05-19: 9/9 passed
review_snapshot JSON: valid
review_snapshot Markdown: valid
export_daily_artifacts: passed
compare_daily_artifacts same-date: has_differences=false
dashboard: 200
rules: 200
web: http://127.0.0.1:8000
```

## Current truth-layer status

### Effective imported contributions

| Code | Name | Field | Value | Source |
|---|---|---|---|---|
| 002747 | 埃斯顿 | entry_zone | 20.69-21.16 | imported / Reviewed imported level snapshot MVP |
| 300024 | 机器人 | entry_zone | 14.8-15.19 | imported / Reviewed imported level snapshot MVP |
| 688017 | 绿的谐波 | entry_zone | 205.88-213.82 | imported / Reviewed imported level snapshot MVP |

### Paused pending item

| Code | Name | Field | Status | Reason |
|---|---|---|---|---|
| 002050 | 三花智控 | entry_zone | pending trusted source + paused | manual anchors span multiple trading days; no same-day clean low-high mapping approved; requires cleaner same-day structured source before entry_zone can be imported |

## Trust and precedence rules

The precedence order must remain:

```text
manual > rule > imported > workflow_seed
```

Rules:

- Manual trigger and invalidation values remain authoritative.
- Rule-generated reduce and take-profit references remain authoritative over imported values.
- Imported values may only fill trusted blank fields.
- Imported values must not silently override manual fields.
- Imported values must not silently override rule fields.
- `trading_level_source_summary.imported` must count only final effective imported contributions.
- `review_snapshot`, `export_daily_artifacts`, and `compare_daily_artifacts` are read-only review/export tools.
- Missing core fields must remain visible as `pending trusted source`.
- Optional downstream missing fields may remain `unavailable`.

## Standard daily execution order

Run these commands from the project root:

```powershell
python main.py validate_imported_levels
python main.py validate_manual_levels
python main.py daily --date 2026-05-19
python main.py validate_consistency --date 2026-05-19
python main.py review_snapshot --date 2026-05-19
python main.py review_snapshot --date 2026-05-19 --format markdown
python main.py export_daily_artifacts --date 2026-05-19
python main.py compare_daily_artifacts --base-date 2026-05-19 --target-date 2026-05-19
python main.py compare_daily_artifacts --base-date 2026-05-19 --target-date 2026-05-19 --format markdown
```

## Expected validation results

```text
validate_imported_levels:
  status=valid
  record_count=3
  valid_record_count=3
  warning=0
  blocking_error=0

validate_manual_levels:
  status=valid
  record_count=5
  valid_record_count=5
  warning=0
  blocking_error=0

daily:
  Daily completed. watchlist=4

validate_consistency:
  Consistency check complete: 9/9 passed.

compare_daily_artifacts same-date:
  has_differences=false
```

## Web startup

Start the web service:

```powershell
python main.py web
```

Expected server:

```text
Uvicorn running on http://127.0.0.1:8000
```

Expected page checks:

```text
GET /dashboard -> 200
GET /rules -> 200
```

Open:

```text
http://127.0.0.1:8000/dashboard
http://127.0.0.1:8000/rules
```

If available, also check the watchlist page from the UI navigation.

`/favicon.ico 404` is non-blocking.

## Review snapshot

JSON:

```powershell
python main.py review_snapshot --date 2026-05-19
```

Markdown:

```powershell
python main.py review_snapshot --date 2026-05-19 --format markdown
```

Expected key state:

```text
data_quality.status = valid
imported_effective_contribution_names = 002747, 300024, 688017
missing_entry_zone_codes = 002050
next_imported_contribution_candidates = []
paused_imported_contribution_candidates = 002050
```

## Artifact export

Run:

```powershell
python main.py export_daily_artifacts --date 2026-05-19
```

Expected output:

```text
outputs/2026-05-19/review_snapshot.json
outputs/2026-05-19/review_snapshot.md
outputs/2026-05-19/daily_close_brief.md
outputs/2026-05-19/manifest.json
outputs/latest_manifest.json
```

`outputs/latest_manifest.json` is the latest handoff pointer.

Use it as the first artifact entry point when resuming a new session.

## Artifact compare

Same-date smoke test:

```powershell
python main.py compare_daily_artifacts --base-date 2026-05-19 --target-date 2026-05-19
python main.py compare_daily_artifacts --base-date 2026-05-19 --target-date 2026-05-19 --format markdown
```

Expected:

```text
has_differences=false
watchlist added=[]
watchlist removed=[]
unchanged=002050, 002747, 300024, 688017
```

Cross-date compare pattern:

```powershell
python main.py compare_daily_artifacts --base-date <previous-date> --target-date <current-date>
```

Only compare dates that already have artifact directories. The compare command must not implicitly run `daily` or generate truth-layer data.

## Handling warnings and blocking issues

If blocking errors appear:

1. Stop treating the daily output as deliverable.
2. Do not patch numeric values just to make the run pass.
3. Inspect validation, daily preflight, review snapshot, and consistency output.
4. Fix the actual cause.

If warnings appear:

1. Keep the warning visible.
2. Determine whether it is a real truth-layer gap or a regression.
3. Do not hide the warning by weakening rules.
4. Do not fabricate numeric levels.

## 002050 gate rule

`002050.entry_zone` must remain:

```text
pending trusted source + paused
```

Do not fill it unless all conditions are true:

1. A same-trading-day structured source is available.
2. The low-high range has clean entry-zone semantics.
3. The source is traceable.
4. It does not override manual trigger or invalidation.
5. It does not override rule reduce or take-profit.
6. Notes explain why the mapping is safe.
7. Validators pass without warnings or blocking errors.
8. Review snapshot correctly removes 002050 from paused state.

If these conditions are not met, keep it paused.

## Forbidden actions

Do not:

- Add manual records without a dedicated review task.
- Add imported records just to increase coverage.
- Fill `002050.entry_zone` from cross-date anchors.
- Change precedence.
- Change scoring.
- Change risk gate behavior.
- Change validators to accept weak data.
- Change preflight rules to hide warnings.
- Generate numeric levels automatically.
- Modify dashboard/watchlist semantics just to hide missing data.
- Treat artifact compare output as a reason to fabricate values.

## Handoff checklist

When handing off a daily run, report:

- Current commit.
- Validation results.
- Daily result.
- Consistency result.
- Review snapshot summary.
- Exported artifact paths.
- Latest manifest path.
- Same-date or cross-date compare result.
- Dashboard / rules / watchlist page check result.
- Whether numeric records changed.
- Whether `002050` remains paused.
