import discord
from discord.ext import commands
import requests
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import os
from flask import Flask
from threading import Thread

# === CONFIGURATION ===
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1366089873559392309

if not TOKEN:
    print("❌ ERREUR : Le TOKEN n'a pas été chargé depuis les variables d'environnement.")
    exit()

API_URL = "https://esports-api.lolesports.com/persisted/gw/getSchedule"
API_KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"

HEADERS = {"x-api-key": API_KEY}
PARAMS = {"hl": "fr-FR"}

LPL_TEAMS = [
    "JDG", "TES", "BLG", "EDG", "WBG", "RNG", "LNG", "IG",
    "OMG", "AL", "FPX", "TT", "UP", "RA", "NIP", "LGD"
]

# === BOT SETUP ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# === FUNCTIONS ===
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
    end_date = now + timedelta(days=7)

    for match in events:
        if not match.get('match'):
            continue
        start_time = datetime.fromisoformat(match['startTime'].replace('Z', '+00:00'))
        if not (now <= start_time <= end_date):
            continue
        team_names = [team['code'] for team in match['match']['teams']]
        if any(team in LPL_TEAMS for team in team_names):
            planning.append({
                "date": start_time.strftime("%A %d %B %Y"),
                "heure": start_time.strftime("%H:%M"),
                "team1": team_names[0],
                "team2": team_names[1],
                "league": match['league']['name']
            })
    return planning

def generate_planning_text(planning):
    if not planning:
        return "❌ Aucun match prévu pour les équipes LPL cette semaine."
    planning.sort(key=lambda x: x['date'] + x['heure'])
    result = "🇨🇳 **Planning des Équipes LPL (7 jours à venir)** 🇨🇳\n\n"
    current_day = ""
    for match in planning:
        if match['date'] != current_day:
            current_day = match['date']
            result += f"\n🗓️ **{current_day}**\n"
        result += f" - {match['heure']} : {match['team1']} vs {match['team2']} _(Compétition : {match['league']})_\n"
    return result

async def send_weekly_planning():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        events = get_schedule()
        lpl_matches = filter_lpl_matches(events)
        planning_text = generate_planning_text(lpl_matches)
        await channel.send(f"@everyone\n{planning_text}")
    else:
        print("❌ Salon introuvable.")

# === BOT EVENTS ===
@bot.event
async def on_ready():
    print(f'✅ {bot.user} est connecté et prêt à l’action !')
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("✅ **LPL FRANCE BOT est en ligne !** Prêt à partager le planning des matchs ! 🏆")
    else:
        print("❌ Salon introuvable.")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_weekly_planning, 'cron', day_of_week='mon', hour=5, minute=52)
    scheduler.start()
    print("🕒 Scheduler activé : Envoi tous les lundis à 7h !")

# === KEEP ALIVE ===
app = Flask('')

@app.route('/')
def home():
    return "Bot LPL actif."

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# === LANCEMENT DU BOT ===
bot.run(TOKEN)
