import discord
from discord.ext import commands
import requests
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import os

# === CONFIGURATION ===
TOKEN = os.getenv('TOKEN')  # Récupération sécurisée du token
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

# Fonction pour récupérer toutes les pages de l'API
def get_full_schedule():
    print("📡 Récupération complète du planning depuis l'API...")
    events = []
    page_token = None

    while True:
        params = PARAMS.copy()
        if page_token:
            params['pageToken'] = page_token

        response = requests.get(API_URL, headers=HEADERS, params=params)
        if response.status_code != 200:
            print(f"❌ Erreur API: {response.status_code}")
            break

        data = response.json()['data']['schedule']
        events.extend(data['events'])

        if not data.get('pages') or not data['pages'].get('newer'):
            break
        page_token = data['pages']['newer']

    print(f"✅ {len(events)} événements récupérés.")
    return events

def filter_lpl_matches(events):
    print("🔎 Filtrage des matchs des équipes LPL...")
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
                "date": start_time.strftime("%A %d %B %Y"),
                "heure": start_time.strftime("%H:%M"),
                "team1": team_names[0],
                "team2": team_names[1],
                "league": match['league']['name']
            }
            planning.append(game_info)
    print(f"✅ {len(planning)} match(s) trouvé(s).")
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
            result += f"\n📅 **{current_day}**\n"

        result += f" - {match['heure']} : {match['team1']} vs {match['team2']} _(Compétition : {match['league']})_\n"

    return result

async def send_weekly_planning():
    print("⏰ Envoi automatique déclenché !")
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        print("📨 Envoi du planning...")
        events = get_full_schedule()
        lpl_matches = filter_lpl_matches(events)
        planning_text = generate_planning_text(lpl_matches)
        await channel.send(f"@everyone\n{planning_text}")
        print("✅ Planning envoyé.")
    else:
        print("❌ Salon introuvable.")

@bot.event
async def on_ready():
    print(f'✅ {bot.user} est connecté et prêt à l’action !')
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("✅ **LPL FRANCE BOT est en ligne !** Prêt à partager le planning des matchs ! 🏆")
    scheduler = AsyncIOScheduler()
   # scheduler.add_job(send_weekly_planning, 'cron', day_of_week='mon', hour=7, minute=0)
    scheduler.add_job(send_weekly_planning, 'interval', minutes=1)
    scheduler.start()
    print("🕒 Scheduler lancé, en attente de l'envoi hebdomadaire...")

# === LANCEMENT DU BOT ===
bot.run(TOKEN)
