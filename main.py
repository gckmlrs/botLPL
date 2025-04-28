import discord
from discord.ext import commands
import requests
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import os

# === CONFIGURATION ===
TOKEN = os.getenv('TOKEN')
CHANNEL_ID = 1366089873559392309
NOTIF_ROLE_ID = 1366444786382409759  # ID du rôle "Notifications"

API_URL = "https://esports-api.lolesports.com/persisted/gw/getSchedule"
API_KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
HEADERS = {"x-api-key": API_KEY}
PARAMS = {"hl": "fr-FR"}

LPL_TEAMS = [
    "JDG", "TES", "BLG", "EDG", "WBG", "RNG", "LNG", "IG",
    "OMG", "AL", "FPX", "TT", "UP", "RA", "NIP", "LGD"
]

JOURS_FR = {
    "Monday": "Lundi",
    "Tuesday": "Mardi",
    "Wednesday": "Mercredi",
    "Thursday": "Jeudi",
    "Friday": "Vendredi",
    "Saturday": "Samedi",
    "Sunday": "Dimanche"
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def get_full_schedule():
    events = []
    page_token = None
    while True:
        params = PARAMS.copy()
        if page_token:
            params['pageToken'] = page_token

        response = requests.get(API_URL, headers=HEADERS, params=params)
        if response.status_code != 200:
            break
        data = response.json()['data']['schedule']
        events.extend(data['events'])

        if not data.get('pages') or not data['pages'].get('newer'):
            break
        page_token = data['pages']['newer']
    return events

def filter_lpl_matches(events):
    planning = []
    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=7)

    for match in events:
        if not match.get('match'):
            continue
        start_time = datetime.fromisoformat(match['startTime'].replace('Z', '+00:00'))
        if not (now <= start_time <= end_date):
            continue

        team_names = [team['code'] for team in match['match']['teams']]
        if any(team in LPL_TEAMS for team in team_names):
            game_info = {
                "datetime": start_time,
                "date_str": start_time.strftime("%A %d %B %Y"),
                "heure": start_time.strftime("%H:%M"),
                "team1": team_names[0],
                "team2": team_names[1],
                "league": match['league']['name']
            }
            planning.append(game_info)
    return planning

def generate_planning_text(planning):
    if not planning:
        return "❌ Aucun match prévu pour les équipes LPL cette semaine."

    planning.sort(key=lambda x: x['datetime'])

    result = "🇨🇳 **Planning des Équipes LPL (7 jours à venir)** 🇨🇳\n\n"
    current_day = ""

    for match in planning:
        day_eng = match['datetime'].strftime("%A")
        jour_fr = JOURS_FR.get(day_eng, day_eng)
        date_fr = match['datetime'].strftime(f"{jour_fr} %d %B %Y")

        if date_fr != current_day:
            current_day =
