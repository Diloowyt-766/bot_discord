import discord
import os
import yt_dlp as youtube_dl
import asyncio
from dotenv import load_dotenv
from discord.ext import commands
from flask import Flask
import threading
import subprocess

# Démarrer un serveur HTTP minimal pour Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Discord en cours d'exécution."

def run_flask():
    app.run(host='0.0.0.0', port=10000)

flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Charger les variables d'environnement
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
        bot.loop.create_task(play_music(ctx, next_url))
    else:
        bot.loop.create_task(ctx.send("🎶 La file d'attente est vide."))

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

        # Options pour yt-dlp avec gestion des cookies
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': False,  # Désactiver le mode silencieux pour voir les logs
            'noplaylist': True,
            'extractaudio': True,
            'forcejson': True,
            'cookiefile': './cookies.txt',  # Utilisation du fichier de cookies
            'verbose': True,  # Activer les logs détaillés
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                song_title = info.get('title', 'Musique inconnue')
                audio_url = info.get('url')

                if not audio_url:
                    await ctx.send("❌ Impossible de récupérer l'URL audio. Vérifiez l'URL ou les cookies.")
                    return

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

        except youtube_dl.utils.DownloadError as e:
            if "Sign in to confirm you’re not a bot" in str(e):
                await ctx.send("❌ Erreur d'authentification. Vérifiez le fichier `cookies.txt`.")
            else:
                await ctx.send(f"❌ Une erreur s'est produite lors du téléchargement : {str(e)}")

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
        voice_client.stop()  # Arrête la musique en cours
        await ctx.send("⏭️ Musique suivante...")
        check_queue(ctx)  # Déclenche la lecture de la musique suivante
    else:
        await ctx.send("❌ Aucune musique en cours de lecture.")

@bot.command()
async def queue(ctx):
    """Affiche la file d'attente des musiques."""
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        queue_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(queues[ctx.guild.id])])
        await ctx.send(f"🎶 File d'attente :\n{queue_list}")
    else:
        await ctx.send("❌ La file d'attente est vide.")

@bot.command()
async def update_cookies(ctx):
    """Met à jour le fichier cookies.txt."""
    await ctx.send("⏳ Mise à jour des cookies en cours...")

    try:
        # Vérifier si le fichier maj_cookies.py existe
        if not os.path.exists('maj_cookies.py'):
            await ctx.send("❌ Le fichier maj_cookies.py est introuvable.")
            return

        # Exécuter le script pour exporter les cookies
        subprocess.run(['python3', 'maj_cookies.py'], check=True)
        await ctx.send("✅ Cookies mis à jour avec succès !")
    except subprocess.CalledProcessError as e:
        await ctx.send(f"❌ Erreur lors de la mise à jour des cookies : {str(e)}")
    except Exception as e:
        await ctx.send(f"❌ Une erreur s'est produite : {str(e)}")

# Démarrer le bot
bot.run(os.getenv('DISCORD_TOKEN'))
