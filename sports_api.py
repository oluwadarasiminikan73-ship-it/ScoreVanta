import os
import requests

API_KEY = os.environ.get("SPORTS_API_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

def get_live_scores():
    res = requests.get(f"{BASE_URL}/fixtures?live=all", headers=HEADERS).json()
    matches = res.get("response", [])[:10] # Limit to top 10 live matches
    if not matches:
        return "No live matches right now."
    
    output = ["🔴 **LIVE SCORES**\n"]
    for m in matches:
        home = m["teams"]["home"]["name"]
        away = m["teams"]["away"]["name"]
        h_goals = m["goals"]["home"]
        a_goals = m["goals"]["away"]
        elapsed = m["fixture"]["status"]["elapsed"]
        output.append(f"• {home} {h_goals} - {a_goals} {away} ({elapsed}')")
    return "\n".join(output)

def get_fixtures(date_str):
    res = requests.get(f"{BASE_URL}/fixtures?date={date_str}", headers=HEADERS).json()
    matches = res.get("response", [])[:10]
    if not matches:
        return "No fixtures found for today."
    
    output = ["📅 **TODAY'S FIXTURES**\n"]
    for m in matches:
        home = m["teams"]["home"]["name"]
        away = m["teams"]["away"]["name"]
        time = m["fixture"]["date"][11:16]
        output.append(f"• {time} UTC | {home} vs {away}")
    return "\n".join(output)

def get_match_analysis(fixture_id):
    # Fetches predictions & stats for game analysis
    res = requests.get(f"{BASE_URL}/predictions?fixture={fixture_id}", headers=HEADERS).json()
    data = res.get("response", [])
    if not data:
        return "Analysis not available for this Match ID. Use /live to find valid IDs."
    
    pred = data[0]["predictions"]
    teams = data[0]["teams"]
    return (
        f"📊 **GAME ANALYSIS: {teams['home']['name']} vs {teams['away']['name']}**\n\n"
        f"• **Advice:** {pred.get('advice', 'N/A')}\n"
        f"• **Win Probability:** Home {pred['percent']['home']} | Draw {pred['percent']['draw']} | Away {pred['percent']['away']}\n"
        f"• **Form (Last 5):** {teams['home']['last_5']['form']} vs {teams['away']['last_5']['form']}"
    )
