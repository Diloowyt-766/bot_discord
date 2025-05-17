import discord
import os
import yt_dlp as youtube_dl
import asyncio
from dotenv import load_dotenv
from discord.ext import commands
from flask import Flask
import threading

# Lancer un serveur Flask pour garder l'app active (utile pour Render)
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Le bot Discord est actif."

def run_flask():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_flask, daemon=True).start()

# Charger les variables d'environnement
load_dotenv()

# Configuration du bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# File d'attente
queues = {}

def check_queue(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        next_url = queues[ctx.guild.id].pop(0)
        bot.loop.create_task(play_music(ctx, next_url))

async def play_music(ctx, url):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ Tu dois être dans un salon vocal pour utiliser cette commande !")
            return

        voice_channel = ctx.author.voice.channel
        voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

        if not voice_client or not voice_client.is_connected():
            voice_client = await voice_channel.connect()
            await ctx.send(f"✅ Connecté au salon : {voice_channel.name}")
        elif voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)
            await ctx.send(f"🔄 Déplacé vers : {voice_channel.name}")

        ydl_opts = {
            
            'format': 'bestaudio/best',
            'noplaylist': True,
            'cookiefile': './cookies.txt',
            'quiet': True,
            # Nouveaux paramètres pour contourner le problème de format :
            'postprocessor_args': ['-ar', '16000'], # Optionnel : fixe le sample rate
            'outtmpl': '-', # Nécessaire pour certains streams
            'restrictfilenames': True,
            
            # Remplacement des options extractor_args :
            'extract_flat': 'in_playlist',
            
            # Format de secours si le premier échoue :
            'audio-format': 'best',
            
            # Configuration FFmpeg :
            'ffmpeg_location': '/path/to/ffmpeg' # Si nécessaire
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info.get('url')
            title = info.get('title', 'Musique inconnue')

        ffmpeg_opts = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(audio_url, **ffmpeg_opts))
        voice_client.play(source, after=lambda e: check_queue(ctx))

        await ctx.send(f"🎶 Lecture en cours : **{title}**")

    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}")

@bot.command()
async def play(ctx, url: str):
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []

    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client and voice_client.is_playing():
        queues[ctx.guild.id].append(url)
        await ctx.send("✅ Ajouté à la file d'attente.")
    else:
        await play_music(ctx, url)

@bot.command()
async def skip(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send("⏭️ Musique suivante...")
        check_queue(ctx)
    else:
        await ctx.send("❌ Aucune musique en cours.")

@bot.command()
async def stop(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client:
        await voice_client.disconnect()
        queues[ctx.guild.id] = []
        await ctx.send("🛑 Déconnecté et file d'attente vidée.")
    else:
        await ctx.send("❌ Pas connecté à un salon vocal.")

@bot.command()
async def queue(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        q_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(queues[ctx.guild.id])])
        await ctx.send(f"🎧 File d'attente :\n{q_list}")
    else:
        await ctx.send("🎵 La file d'attente est vide.")

# Lancer le bot
bot.run(os.getenv("DISCORD_TOKEN"))
