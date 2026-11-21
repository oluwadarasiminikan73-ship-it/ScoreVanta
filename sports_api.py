import html
from datetime import datetime, timezone
import requests

# ESPN public scoreboard endpoints (no API key required)
LEAGUES = {
    "EPL": "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
    "La Liga": "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard",
    "UCL": "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard",
}


def _fetch_events(date_str: str | None = None) -> list[dict]:
    events: list[dict] = []
    params = {"dates": date_str.replace("-", "")} if date_str else {}

    for league_name, url in LEAGUES.items():
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            for ev in data.get("events", []):
                ev["_league"] = league_name
                events.append(ev)
        except Exception:
            continue

    return events


def _parse_match(ev: dict) -> dict | None:
    competitions = ev.get("competitions", [])
    if not competitions:
        return None
    comp = competitions[0]
    competitors = comp.get("competitors", [])
    if len(competitors) < 2:
        return None

    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

    status_obj = comp.get("status", {})
    status_type = status_obj.get("type", {})
    state = status_type.get("state", "pre")  # "pre", "in", "post"
    detail = status_type.get("shortDetail") or status_type.get("description") or ""

    return {
        "id": str(ev.get("id", "")),
        "league": ev.get("_league", ""),
        "home": home.get("team", {}).get("displayName", "Home"),
        "away": away.get("team", {}).get("displayName", "Away"),
        "h_score": home.get("score", "0"),
        "a_score": away.get("score", "0"),
        "home_form": home.get("form", ""),
        "away_form": away.get("form", ""),
        "state": state,
        "detail": detail,
        "date": ev.get("date", ""),
    }


def get_live_scores(limit: int = 10) -> str:
    live_matches = []
    for ev in _fetch_events():
        m = _parse_match(ev)
        if m and m["state"] == "in":
            live_matches.append(m)

    if not live_matches:
        return "No live matches right now."

    lines = ["🔴 <b>LIVE SCORES</b>\n"]
    for m in live_matches[:limit]:
        home = html.escape(m["home"])
        away = html.escape(m["away"])
        detail = html.escape(m["detail"])
        league = html.escape(m["league"])
        lines.append(
            f"• [{league}] <b>{home}</b> {m['h_score']} - {m['a_score']} <b>{away}</b> "
            f"({detail}) — ID: <code>{html.escape(m['id'])}</code>"
        )
    return "\n".join(lines)


def get_fixtures(date_str: str | None = None, limit: int = 10) -> str:
    target_date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    matches = []
    for ev in _fetch_events(target_date):
        m = _parse_match(ev)
        if m:
            matches.append(m)

    if not matches:
        return f"No fixtures found for <b>{html.escape(target_date)}</b>."

    lines = [f"📅 <b>FIXTURES ({html.escape(target_date)})</b>\n"]
    for m in matches[:limit]:
        home = html.escape(m["home"])
        away = html.escape(m["away"])
        kickoff = m["date"][11:16] + " UTC" if len(m["date"]) >= 16 else m["detail"]
        lines.append(
            f"• {html.escape(kickoff)} | <b>{home}</b> vs <b>{away}</b> "
            f"— ID: <code>{html.escape(m['id'])}</code>"
        )
    return "\n".join(lines)


def get_match_stats(fixture_id: str) -> str:
    if not fixture_id.isdigit():
        return "Invalid Match ID. Example: <code>/stats 701234</code>"

    for ev in _fetch_events():
        m = _parse_match(ev)
        if m and m["id"] == fixture_id:
            return (
                f"📈 <b>MATCH SNAPSHOT: {html.escape(m['home'])} vs {html.escape(m['away'])}</b>\n\n"
                f"• <b>Status:</b> {html.escape(m['detail'])}\n"
                f"• <b>Score:</b> {html.escape(str(m['h_score']))} — {html.escape(str(m['a_score']))}\n"
                f"• <b>League:</b> {html.escape(m['league'])}"
            )

    return "Match not found in current live/today feeds. Check IDs via /live or /fixtures."


def get_match_analysis(fixture_id: str) -> str:
    if not fixture_id.isdigit():
        return "Invalid Match ID. Example: <code>/analysis 701234</code>"

    for ev in _fetch_events():
        m = _parse_match(ev)
        if m and m["id"] == fixture_id:
            h_form = html.escape(m["home_form"] or "N/A")
            a_form = html.escape(m["away_form"] or "N/A")
            h_wins = m["home_form"].count("W")
            a_wins = m["away_form"].count("W")

            if h_wins > a_wins:
                edge = f"{m['home']} hold recent form edge ({h_form} vs {a_form})"
            elif a_wins > h_wins:
                edge = f"{m['away']} hold recent form edge ({a_form} vs {h_form})"
            else:
                edge = f"Evenly matched on recent form ({h_form} vs {a_form})"

            return (
                f"📊 <b>GAME ANALYSIS: {html.escape(m['home'])} vs {html.escape(m['away'])}</b>\n\n"
                f"• <b>Status:</b> {html.escape(m['detail'])}\n"
                f"• <b>Recent Form:</b> {h_form} vs {a_form}\n"
                f"• <b>Takeaway:</b> {html.escape(edge)}"
            )

    return "Analysis not available for this Match ID. Check IDs via /live or /fixtures."
