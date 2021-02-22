import discord, youtube_dl, os, random, time, asyncio
from discord.ext import commands
from discord.utils import get
from datetime import datetime as d
from discord.voice_client import VoiceClient

folder = os.path.dirname(os.path.abspath(__file__))
token = os.path.join(folder, 'token.txt')

def read_pass(x):
    with open(token, "r") as f:
        lines = f.readlines()
        return lines[x].strip()

def prefix(client, message):
    prefixes = ['!']
    if not message.guild:
        prefixes = ['']
    return commands.when_mentioned_or(*prefixes)(client, message)

client = commands.Bot(
    command_prefix = prefix,
    # owner_id is the Discord ID from the owner.
    owner_id = read_pass(1),
    case_insensitive = True,
    description = "PAPAPA"
)

cogs = ['cogs.music', 'cogs.web']

@client.event
async def on_ready():
    print('Okaeri ' + str(client.user.name) + '-sama.')
    for cog in cogs:
        client.load_extension(cog)
    return

async def status():
    await client.wait_until_ready()
    choices = ["World of Warcraft", "NBA2k20", "Sleeping", "Waiting for new commands", "Coding", "Scraping"]

    while not client.is_closed():
        status = random.choice(choices)
        await client.change_presence(activity=discord.Game(status))
        await asyncio.sleep(600)

client.loop.create_task(status())
# Bot's Secret Token here visit: https://discord.com/developers/applications
client.run(read_pass(0), bot = True, reconnect = True)