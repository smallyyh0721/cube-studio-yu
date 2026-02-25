from __future__ import annotations

import html
import json


def render_html_report(report: dict[str, object]) -> str:
    scenario = report.get("scenario", {})
    timeline = report.get("timeline", [])
    score = report.get("resilience_score", {})
    failed = [item for item in timeline if item.get("status") != "success" and item.get("event_type") != "monitor"]

    timeline_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(str(item.get('timestamp', '')))}</td>"
            f"<td>{html.escape(str(item.get('event_type', '')))}</td>"
            f"<td>{html.escape(str(item.get('host', '')))}</td>"
            f"<td>{html.escape(str(item.get('status', '')))}</td>"
            f"<td><pre>{html.escape(json.dumps(item.get('details', {}), ensure_ascii=False))}</pre></td>"
            "</tr>"
        )
        for item in timeline
    )

    failed_items = "".join(
        f"<li>{html.escape(item.get('host', ''))}: {html.escape(item.get('title', ''))}</li>" for item in failed
    ) or "<li>None</li>"

    score_list = "".join(
        f"<li>{html.escape(str(k))}: <strong>{html.escape(str(v))}</strong></li>" for k, v in score.items()
    )

    return f"""<!doctype html>
<html lang=\"zh\">
<head>
  <meta charset=\"utf-8\" />
  <title>Fault Injection Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 24px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ background: #f4f4f4; text-align: left; }}
    pre {{ margin: 0; white-space: pre-wrap; word-break: break-word; }}
  </style>
</head>
<body>
  <h1>Fault Injection Report</h1>
  <h2>Scenario</h2>
  <pre>{html.escape(json.dumps(scenario, ensure_ascii=False, indent=2))}</pre>
  <h2>Resilience Score</h2>
  <ul>{score_list}</ul>
  <h2>Timeline</h2>
  <table>
    <thead><tr><th>Timestamp</th><th>Type</th><th>Host</th><th>Status</th><th>Details</th></tr></thead>
    <tbody>{timeline_rows}</tbody>
  </table>
  <h2>Failure Details</h2>
  <ul>{failed_items}</ul>
</body>
</html>
"""
