import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os

# === CONFIGURATION ===
TOKEN = os.getenv('TOKEN')
PLANNING_CHANNEL_ID = 1366089873559392309
CLASSEMENT_CHANNEL_ID = 1366478478475657246
NOTIF_ROLE_ID = 1366444786382409759

API_URL_SCHEDULE = "https://esports-api.lolesports.com/persisted/gw/getSchedule"
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

# === PLANNING ===
def get_full_schedule():
    events = []
    page_token = None
    while True:
        params = PARAMS.copy()
        if page_token:
            params['pageToken'] = page_token
        response = requests.get(API_URL_SCHEDULE, headers=HEADERS, params=params)
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
    result = "🇨🇳 **Planning des Équipes LPL (7 jours à venir)** 🇨🇳\n"
    current_day = ""
    for match in planning:
        day_eng = match['datetime'].strftime("%A")
        jour_fr = JOURS_FR.get(day_eng, day_eng)
        date_fr = match['datetime'].strftime(f"{jour_fr} %d %B %Y")
        if date_fr != current_day:
            current_day = date_fr
            result += f"\n📅 **{current_day}**\n"
        result += f" - {match['heure']} : {match['team1']} vs {match['team2']} _(Compétition : {match['league']})_\n"
    return result

async def send_weekly_planning():
    channel = bot.get_channel(PLANNING_CHANNEL_ID)
    if channel:
        events = get_full_schedule()
        lpl_matches = filter_lpl_matches(events)
        planning_text = generate_planning_text(lpl_matches)
        notif_role = channel.guild.get_role(NOTIF_ROLE_ID)
        if notif_role:
            await channel.send(f"{notif_role.mention}\n{planning_text}")

# === CLASSEMENT (Scraping Flashscore avec Debug) ===
FLASHSCORE_URL = "https://www.flashscore.fr/esports/league-of-legends/lpl/classement/"

def get_lpl_classement_from_flashscore():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9"
    }
    response = requests.get(FLASHSCORE_URL, headers=headers)
    if response.status_code != 200:
        print(f"Erreur HTTP: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    teams = soup.select('div.table__row')
    print(f"Nombre d'équipes trouvées : {len(teams)}")

    classement_text = "📊 **Classement LPL (Source: Flashscore)** 📊\n"
    rank = 1
    for team in teams:
        name_tag = team.select_one('div.table__cell--participant')
        stats_tag = team.select_one('div.table__cell--main')
        if name_tag and stats_tag:
            name = name_tag.get_text(strip=True)
            stats = stats_tag.get_text(strip=True)
            classement_text += f"{rank}️⃣ {name} | {stats}\n"
            rank += 1
        if rank > 10:
            break

    return classement_text if rank > 1 else None

async def update_classement():
    channel = bot.get_channel(CLASSEMENT_CHANNEL_ID)
    if not channel:
        return

    classement_text = get_lpl_classement_from_flashscore()
    if not classement_text:
        await channel.send("❌ Impossible de récupérer le classement depuis Flashscore.")
        return

    async for msg in channel.history(limit=10):
        if msg.author == bot.user and "📊 **Classement LPL" in msg.content:
            await msg.edit(content=classement_text)
            break
    else:
        await channel.send(classement_text)

# === EVENT PRINCIPAL ===
@bot.event
async def on_ready():
    print(f'✅ {bot.user} est connecté et prêt à l’action !')
    planning_channel = bot.get_channel(PLANNING_CHANNEL_ID)
    classement_channel = bot.get_channel(CLASSEMENT_CHANNEL_ID)
    if planning_channel:
        await planning_channel.send("✅ **LPL FRANCE BOT est en ligne !** Prêt à partager le planning des matchs ! 🏆")
    if classement_channel:
        await classement_channel.send("📊 **LPL FRANCE BOT est en ligne !** Prêt à mettre à jour le classement en temps réel !")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_weekly_planning, 'cron', day_of_week='mon', hour=7, minute=0)
    scheduler.add_job(update_classement, 'interval', minutes=1)  # Test rapide
    scheduler.start()

bot.run(TOKEN)
