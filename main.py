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

API_URL = "https://esports-api.lolesports.com/persisted/gw/getSchedule"
API_KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"

HEADERS = {"x-api-key": API_KEY}
PARAMS = {"hl": "fr-FR"}

LPL_TEAMS = [
    "JDG", "TES", "BLG", "EDG", "WBG", "RNG", "LNG", "IG",
    "OMG", "AL", "FPX", "TT", "UP", "RA", "NIP", "LGD"
]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def get_schedule():
    response = requests.get(API_URL, headers=HEADERS, params=PARAMS)
    if response.status_code == 200:
        return response.json()['data']['schedule']['events']
    else:
        print(f"❌ Erreur API: {response.status_code}")
        return []

def filter_lpl_matches(events):
    planning = []
    now = datetime.now(timezone.utc)

    # ✅ Fin de la semaine (dimanche 23:59)
    days_until_sunday = 6 - now.weekday()
    end_date = now + timedelta(days=days_until_sunday)
    end_date = end_date.replace(hour=23, minute=59, second=59)

    for match in events:
        if not match.get('match'):
            continue

        start_time = datetime.fromisoformat(match['startTime'].replace('Z', '+00:00'))
        if not (now <= start_time <= end_date):
            continue

        team_names = [team['code'] for team in match['match']['teams']]
        if any(team in LPL_TEAMS for team in team_names):
            game_info = {
                "date": start_time.strftime("%A %d %B %Y"),
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

    planning.sort(key=lambda x: x['date'] + x['heure'])
    result = "🇨🇳 **Planning des Équipes LPL (jusqu'à dimanche)** 🇨🇳\n\n"
    current_day = ""

    for match in planning:
        if match['date'] != current_day:
            current_day = match['date']
            result += f"\n📅 **{current_day}**\n"

        result += f" - {match['heure']} : {match['team1']} vs {match['team2']} _(Compétition : {match['league']})_\n"

    return result

async def send_weekly_planning():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        events = get_schedule()
        lpl_matches = filter_lpl_matches(events)
        planning_text = generate_planning_text(lpl_matches)
        await channel.send("@everyone\n" + planning_text)
    else:
        print("❌ Salon introuvable.")

@bot.event
async def on_ready():
    print(f'✅ {bot.user} est connecté et prêt à l’action !')
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_weekly_planning, 'interval', minutes=1) # Chaque lundi à 7h
    scheduler.start()

# === LANCEMENT DU BOT ===
bot.run(TOKEN)
