import html
import os
import requests

API_KEY = os.environ.get("SPORTS_API_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}


def _api_get(endpoint: str, params: dict | None = None) -> tuple[list, str | None]:
    if not API_KEY:
        return [], "⚠️ <b>SPORTS_API_KEY</b> is missing in Railway variables."
    try:
        resp = requests.get(
            f"{BASE_URL}/{endpoint.lstrip('/')}",
            headers=HEADERS,
            params=params or {},
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
        errors = payload.get("errors")
        if errors:
            return [], f"⚠️ API error: <code>{html.escape(str(errors))}</code>"
        return payload.get("response", []), None
    except Exception as exc:
        return [], f"⚠️ Request failed: <code>{html.escape(str(exc))}</code>"


def get_live_scores(limit: int = 10) -> str:
    matches, err = _api_get("fixtures", {"live": "all"})
    if err:
        return err
    if not matches:
        return "No live matches right now."

    lines = ["🔴 <b>LIVE SCORES</b>\n"]
    for m in matches[:limit]:
        fixture_id = m["fixture"]["id"]
        home = html.escape(m["teams"]["home"]["name"])
        away = html.escape(m["teams"]["away"]["name"])
        h_goals = m["goals"]["home"] if m["goals"]["home"] is not None else 0
        a_goals = m["goals"]["away"] if m["goals"]["away"] is not None else 0
        elapsed = m["fixture"]["status"].get("elapsed") or 0
        lines.append(
            f"• <b>{home}</b> {h_goals} - {a_goals} <b>{away}</b> ({elapsed}') "
            f"— ID: <code>{fixture_id}</code>"
        )
    return "\n".join(lines)


def get_fixtures(date_str: str, limit: int = 10) -> str:
    matches, err = _api_get("fixtures", {"date": date_str})
    if err:
        return err
    if not matches:
        return f"No fixtures found for <b>{html.escape(date_str)}</b>."

    lines = [f"📅 <b>FIXTURES ({html.escape(date_str)})</b>\n"]
    for m in matches[:limit]:
        fixture_id = m["fixture"]["id"]
        home = html.escape(m["teams"]["home"]["name"])
        away = html.escape(m["teams"]["away"]["name"])
        kickoff = m["fixture"]["date"][11:16]
        lines.append(
            f"• {kickoff} UTC | <b>{home}</b> vs <b>{away}</b> "
            f"— ID: <code>{fixture_id}</code>"
        )
    return "\n".join(lines)


def get_match_stats(fixture_id: str) -> str:
    if not fixture_id.isdigit():
        return "Invalid Match ID. Use digits only, e.g. <code>/stats 123456</code>"

    data, err = _api_get("fixtures/statistics", {"fixture": fixture_id})
    if err:
        return err
    if len(data) < 2:
        return "Match statistics are not available yet for this ID."

    home_team = html.escape(data[0]["team"]["name"])
    away_team = html.escape(data[1]["team"]["name"])

    home_stats = {item["type"]: item["value"] for item in data[0].get("statistics", [])}
    away_stats = {item["type"]: item["value"] for item in data[1].get("statistics", [])}

    tracked = [
        "Ball Possession",
        "Total Shots",
        "Shots on Goal",
        "Corner Kicks",
        "Yellow Cards",
        "Red Cards",
    ]

    lines = [f"📈 <b>MATCH STATS: {home_team} vs {away_team}</b>\n"]
    for stat in tracked:
        h_val = html.escape(str(home_stats.get(stat) if home_stats.get(stat) is not None else "-"))
        a_val = html.escape(str(away_stats.get(stat) if away_stats.get(stat) is not None else "-"))
        lines.append(f"• <b>{html.escape(stat)}:</b> {h_val} — {a_val}")

    return "\n".join(lines)


def get_match_analysis(fixture_id: str) -> str:
    if not fixture_id.isdigit():
        return "Invalid Match ID. Use digits only, e.g. <code>/analysis 123456</code>"

    data, err = _api_get("predictions", {"fixture": fixture_id})
    if err:
        return err
    if not data:
        return "Analysis not available for this Match ID. Check IDs via /live or /fixtures."

    pred = data[0].get("predictions", {})
    teams = data[0].get("teams", {})
    home_name = html.escape(teams.get("home", {}).get("name", "Home"))
    away_name = html.escape(teams.get("away", {}).get("name", "Away"))
    advice = html.escape(pred.get("advice") or "N/A")
    pct = pred.get("percent", {})
    home_pct = html.escape(str(pct.get("home") or "N/A"))
    draw_pct = html.escape(str(pct.get("draw") or "N/A"))
    away_pct = html.escape(str(pct.get("away") or "N/A"))
    home_form = html.escape(teams.get("home", {}).get("last_5", {}).get("form") or "N/A")
    away_form = html.escape(teams.get("away", {}).get("last_5", {}).get("form") or "N/A")

    return (
        f"📊 <b>GAME ANALYSIS: {home_name} vs {away_name}</b>\n\n"
        f"• <b>Advice:</b> {advice}\n"
        f"• <b>Win Probability:</b> Home {home_pct} | Draw {draw_pct} | Away {away_pct}\n"
        f"• <b>Form (Last 5):</b> {home_form} vs {away_form}"
    )
