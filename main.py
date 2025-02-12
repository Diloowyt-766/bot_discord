import discord
import os
import yt_dlp as youtube_dl
import asyncio
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

# Configuration du bot avec les intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# File d'attente pour gérer plusieurs musiques
queues = {}

def check_queue(ctx):
    """Joue la musique suivante si la file d'attente n'est pas vide."""
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        next_url = queues[ctx.guild.id].pop(0)
        asyncio.create_task(play_music(ctx, next_url))

async def play_music(ctx, url):
    """Se connecte au salon vocal et joue une musique YouTube en streaming."""
    try:
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send("❌ Tu dois être dans un salon vocal pour utiliser cette commande !")
            return

        voice_channel = ctx.author.voice.channel
        voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

        if not voice_client or not voice_client.is_connected():
            try:
                voice_client = await voice_channel.connect()
                await ctx.send(f"✅ Connecté au salon vocal : {voice_channel.name}")
            except discord.errors.ClientException:
                await ctx.send("❌ Impossible de rejoindre le salon vocal. Vérifie mes permissions !")
                return
        elif voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)
            await ctx.send(f"🔄 Déplacement dans : {voice_channel.name}")

        # Télécharge les informations sur la vidéo sans télécharger l'audio
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'extractaudio': True,
            'forcejson': True,
        }
        yt-dlp --cookies ./youtube.com_cookies.txt url

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            song_title = info.get('title', 'Musique inconnue')
            audio_url = info['url']

        # Lecture de la musique en streaming avec FFmpeg
        ffmpeg_options = {
            'options': '-vn',
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
        }
        source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        source = discord.PCMVolumeTransformer(source)

        voice_client.play(source, after=lambda e: check_queue(ctx))

        if voice_client.is_playing():
            await ctx.send(f"🎶 Lecture en cours : **{song_title}**")
        else:
            await ctx.send("❌ Impossible de lire la musique. Vérifie les logs.")

    except Exception as e:
        await ctx.send(f"❌ Une erreur s'est produite : {str(e)}")

@bot.command()
async def play(ctx, url: str):
    """Commande pour jouer une musique YouTube."""
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []

    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client:
        if voice_client.is_playing():  # Si une musique est en cours, on ajoute à la file d'attente
            queues[ctx.guild.id].append(url)
            await ctx.send("✅ Musique ajoutée à la file d'attente")
        else:  # Si aucune musique n'est en cours, on commence à jouer
            await play_music(ctx, url)
    else:
        # Si le bot n'est pas dans un salon vocal, on rejoint le salon et commence la musique
        if ctx.author.voice:
            voice_channel = ctx.author.voice.channel
            voice_client = await voice_channel.connect()
            await play_music(ctx, url)
        else:
            await ctx.send("❌ Tu dois être dans un salon vocal pour utiliser cette commande !")

@bot.command()
async def stop(ctx):
    """Arrête la musique et vide la file d'attente."""
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client and voice_client.is_playing():
        voice_client.stop()  # Arrêter la musique en cours
        queues[ctx.guild.id] = []  # Vider la file d'attente
        await ctx.send("⏹️ Musique arrêtée et file d'attente vidée.")
    else:
        await ctx.send("❌ Aucune musique en cours de lecture.")

@bot.command()
async def skip(ctx):
    """Passe à la musique suivante dans la file d'attente."""
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client and voice_client.is_playing():
        voice_client.stop()  # Stoppe la musique actuelle pour déclencher check_queue
        await ctx.send("⏭️ Musique suivante...")
    else:
        await ctx.send("❌ Aucune musique en cours de lecture.")

bot.run(os.getenv('DISCORD_TOKEN'))
