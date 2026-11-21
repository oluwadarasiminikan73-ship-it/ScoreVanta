import html
from datetime import datetime, timezone
import requests

# ESPN public endpoints (no API key required)
LEAGUES = {
    "EPL": {
        "scoreboard": "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
        "summary": "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary",
    },
    "La Liga": {
        "scoreboard": "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard",
        "summary": "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/summary",
    },
    "UCL": {
        "scoreboard": "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard",
        "summary": "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/summary",
    },
}


def _to_int(val, default: int = 0) -> int:
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return default


def _fetch_events(date_str: str | None = None) -> list[dict]:
    events: list[dict] = []
    params = {"dates": date_str.replace("-", "")} if date_str else {}

    for league_name, urls in LEAGUES.items():
        try:
            resp = requests.get(urls["scoreboard"], params=params, timeout=10)
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
        "h_score": _to_int(home.get("score", 0)),
        "a_score": _to_int(away.get("score", 0)),
        "home_form": home.get("form", ""),
        "away_form": away.get("form", ""),
        "state": state,
        "detail": detail,
        "date": ev.get("date", ""),
    }


def get_match_lineups(event_id: str, league_name: str | None = None) -> dict | None:
    """Fetches starting lineups from ESPN's summary endpoint rosters."""
    candidate_urls = (
        [LEAGUES[league_name]["summary"]]
        if league_name in LEAGUES
        else [cfg["summary"] for cfg in LEAGUES.values()]
    )

    for url in candidate_urls:
        try:
            resp = requests.get(url, params={"event": event_id}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            rosters = data.get("rosters") or []
            if len(rosters) < 2:
                continue

            parsed_teams = []
            for roster in rosters[:2]:
                team_name = roster.get("team", {}).get("displayName", "Team")
                formation = roster.get("formation", "")
                starters = []
                for entry in roster.get("roster", []):
                    if entry.get("starter") is True:
                        athlete = entry.get("athlete", {})
                        name = athlete.get("shortName") or athlete.get("displayName")
                        jersey = entry.get("jersey")
                        if name:
                            starters.append(f"#{jersey} {name}" if jersey else name)

                if starters:
                    parsed_teams.append(
                        {
                            "team": team_name,
                            "formation": formation,
                            "starters": starters[:11],
                        }
                    )

            if len(parsed_teams) == 2:
                return {"home": parsed_teams[0], "away": parsed_teams[1]}
        except Exception:
            continue

    return None


def format_lineup_message(match: dict, lineups: dict) -> str:
    home = lineups["home"]
    away = lineups["away"]

    h_form_str = f" ({html.escape(home['formation'])})" if home.get("formation") else ""
    a_form_str = f" ({html.escape(away['formation'])})" if away.get("formation") else ""

    h_players = "\n".join(f"  {i + 1}. {html.escape(p)}" for i, p in enumerate(home["starters"]))
    a_players = "\n".join(f"  {i + 1}. {html.escape(p)}" for i, p in enumerate(away["starters"]))

    return (
        f"📋 <b>STARTING LINEUPS</b> [{html.escape(match['league'])}]\n"
        f"<b>{html.escape(match['home'])}</b> vs <b>{html.escape(match['away'])}</b>\n\n"
        f"🏠 <b>{html.escape(home['team'])}</b>{h_form_str}:\n{h_players}\n\n"
        f"✈️ <b>{html.escape(away['team'])}</b>{a_form_str}:\n{a_players}"
    )


def get_lineup_text(event_id: str) -> str:
    if not event_id.isdigit():
        return "Invalid Match ID. Example: <code>/lineup 701234</code>"

    match_info = {"id": event_id, "league": "", "home": "Home", "away": "Away"}
    for ev in _fetch_events():
        parsed = _parse_match(ev)
        if parsed and parsed["id"] == event_id:
            match_info = parsed
            break

    lineups = get_match_lineups(event_id, match_info.get("league"))
    if not lineups:
        return "Lineups are not published yet for this match. Try closer to kickoff."

    return format_lineup_message(match_info, lineups)


def get_live_match_items() -> list[dict]:
    items = []
    for ev in _fetch_events():
        m = _parse_match(ev)
        if m and m["state"] in ("pre", "in", "post"):
            items.append(m)
    return items


def get_live_scores(limit: int = 10) -> str:
    live_matches = [m for m in get_live_match_items() if m["state"] == "in"]
    if not live_matches:
        return "No live matches right now."

    lines = ["🔴 <b>LIVE SCORES</b>\n"]
    for m in live_matches[:limit]:
        lines.append(
            f"• [{html.escape(m['league'])}] <b>{html.escape(m['home'])}</b> "
            f"{m['h_score']} - {m['a_score']} <b>{html.escape(m['away'])}</b> "
            f"({html.escape(m['detail'])}) — ID: <code>{html.escape(m['id'])}</code>"
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
        kickoff = m["date"][11:16] + " UTC" if len(m["date"]) >= 16 else m["detail"]
        lines.append(
            f"• {html.escape(kickoff)} | <b>{html.escape(m['home'])}</b> vs "
            f"<b>{html.escape(m['away'])}</b> — ID: <code>{html.escape(m['id'])}</code>"
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
                f"• <b>Score:</b> {m['h_score']} — {m['a_score']}\n"
                f"• <b>League:</b> {html.escape(m['league'])}"
            )

    return "Match not found in current feeds. Check IDs via /live or /fixtures."


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
                edge = f"Evenly matched
