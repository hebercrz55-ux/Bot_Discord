import discord
from discord.ext import commands
#librerias para utilizar GEMINI
import google.generativeai as genai
import os
from dotenv import load_dotenv

import yt_dlp
import asyncio

#librerias para el sistema de niveles
import random
import json


#carga de variables de entorno
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Configurar Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Intents
intents = discord.Intents.default()
intents.message_content = True  # Necesario para leer los mensajes
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

#archivo de datos
DATA_FILE = "xp_data.json"
#id del canal para notificar subidas de nivel
LEVEL_UP_CHANNEL_ID = 1427358050951368848

def cargar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    else:
        return{}

def guardar_datos(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4,ensure_ascii=False)
    
xp_data = cargar_datos()

#función para calcular el xp necesario
def xp_para_siguiente_nivel(nivel):
    return 5*(nivel**2)+50*nivel+100


FFMPEG_OPTIONS = {'options': '-vn'}

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')

#Evento cuando alguien manda un mensaje
@bot.event
async def on_message(message):
    if message.author.bot:
        return #ignora otros bot:
    user_id = str(message.author.id)

    #si el usuario no existe, se inicializa
    if user_id not in xp_data:
        xp_data[user_id]={"xp":0,"nivel":0}
    
    #se agrega xp aleatoria
    xp_ganada = random.randint(5,15)
    xp_data[user_id]["xp"]+=xp_ganada

    #reisar si sube de nivel
    nivel_actual = xp_data[user_id]["nivel"]
    xp_necesario = xp_para_siguiente_nivel(nivel_actual)

    if xp_data[user_id]["xp"] >= xp_necesario:
        xp_data[user_id]["nivel"] += 1
        xp_data[user_id]["xp"] -= xp_necesario

        #se envía el mensaje en el canal de niveles
        canal_niveles = bot.get_channel(LEVEL_UP_CHANNEL_ID)
        if canal_niveles:
            await canal_niveles.send(f"!{message.author.mention} ha subido al **nivel {xp_data[user_id]['nivel']}**!")
    guardar_datos(xp_data)
    await bot.process_commands(message) #permite seguir usando comandos

# Configurar opciones de descarga de yt-dlp
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'extract_flat': True,
    'allow_unplayable_formats': True
    
}



#comando de pregunta a la IA
@bot.command(name="pregunta")
async def pregunta(ctx, *, mensaje):
    """Comando para hablar con Elma"""
    await ctx.channel.typing()
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(f"{mensaje}. Responde en menos de 1500 caracteres.")
        #response = model.generate_content(mensaje)
        # Gemini puede devolver varios bloques, unimos el texto
        respuesta = response.text or "🤖 No se recibió respuesta del modelo."
        await ctx.reply(respuesta)
    except Exception as e:
        await ctx.reply(f"⚠️ Error: {e}")

#COMANDOS DE NIVEL
@bot.command(name="nivel")
async def nivel(ctx,miembro:discord.Member = None):
    miembro = miembro or ctx.author
    user_id = str(miembro.id)

    if user_id in xp_data:
        xp = xp_data[user_id]["xp"]
        nivel = xp_data[user_id]["nivel"]
        xp_necesario = xp_para_siguiente_nivel(nivel)
        await ctx.reply(f"{miembro.display_name} está en **nivel {nivel}** con **{xp}/{xp_necesario} XP**.")
    else:
        await ctx.reply(f"{miembro.display_name} aún no tiene XP.")


#comandos de musica
@bot.command(name='join')
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("🎧 Me he unido al canal de voz.")
    else:
        await ctx.send("❌ No estás en un canal de voz.")

@bot.command(name='leave')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Me he salido del canal de voz.")
    else:
        await ctx.send("❌ No estoy en ningún canal de voz.")

@bot.command(name='play')
async def play(ctx, *, url):
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("❌ No estás en un canal de voz.")
            return

    voice_client = ctx.voice_client

    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url,download=False)
        #file_path = ydl.prepare_filename(info)
        audio_url = info['url']
        title = info.get('title', 'Audio')

    voice_client.stop()
    #voice_client.play(discord.FFmpegPCMAudio(file_path, **FFMPEG_OPTIONS))
    #voice_client.play(discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS))
    voice_client.play(discord.FFmpegOpusAudio(audio_url, **FFMPEG_OPTIONS))

    await ctx.send(f"🎶 Reproduciendo: **{title}**")

@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏹️ Reproducción detenida.")
    else:
        await ctx.send("❌ No se está reproduciendo nada.")

# ⚠️ Reemplaza con tu token real del bot
bot.run(DISCORD_TOKEN)
