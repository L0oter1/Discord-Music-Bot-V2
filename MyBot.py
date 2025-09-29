# Importing libraries and modules
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import yt_dlp 
from collections import deque 
import asyncio 
import re


# Environment variables for tokens and other sensitive data
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Create the structure for queueing songs - Dictionary of queues
SONG_QUEUES = {}

async def search_ytdlp_async(query, ydl_opts):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _extract(query, ydl_opts))

def _extract(query, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(query, download=False)


# Setup of intents. Intents are permissions the bot has on the server
intents = discord.Intents.default()
intents.message_content = True

# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)

# Bot ready-up code
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} is online!")


@bot.tree.command(name="skip", description="Skips the current playing song")
async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client and (interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused()):
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("Skipped the current song.")
    else:
        await interaction.response.send_message("Not playing anything to skip.")


@bot.tree.command(name="pause", description="Pause the currently playing song.")
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if voice_client is None:
        return await interaction.response.send_message("I'm not in a voice channel.")

    # Check if something is actually playing
    if not voice_client.is_playing():
        return await interaction.response.send_message("Nothing is currently playing.")
    
    # Pause the track
    voice_client.pause()
    await interaction.response.send_message("Playback paused!")


@bot.tree.command(name="resume", description="Resume the currently paused song.")
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if voice_client is None:
        return await interaction.response.send_message("I'm not in a voice channel.")

    # Check if it's actually paused
    if not voice_client.is_paused():
        return await interaction.response.send_message("I’m not paused right now.")
    
    # Resume playback
    voice_client.resume()
    await interaction.response.send_message("Playback resumed!")


@bot.tree.command(name="stop", description="Stop playback and clear the queue.")
async def stop(interaction: discord.Interaction):
    await interaction.response.defer()
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if not voice_client or not voice_client.is_connected():
        return await interaction.followup.send("I'm not connected to any voice channel.")

    # Clear the guild's queue
    guild_id_str = str(interaction.guild_id)
    if guild_id_str in SONG_QUEUES:
        SONG_QUEUES[guild_id_str].clear()

    # If something is playing or paused, stop it
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()

    await interaction.followup.send("Stopped playback and disconnected!")

    # (Optional) Disconnect from the channel
    await voice_client.disconnect()


@bot.tree.command(name="queue", description="Shows you what the queue is.")
async def queue(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)

    if SONG_QUEUES.get(guild_id) is None:
        await interaction.response.send_message("There is nothing queued up!")
    else:
        queue = SONG_QUEUES[guild_id] 
        message = "\n".join([f"{idx}. {song[1]}" for idx, song in enumerate(queue, start=1)])
        await interaction.response.send_message(f"**Song Queue:**\n{message}")


@bot.tree.command(name="play", description="Play a song or add it to the queue.")
@app_commands.describe(song_query="Search query")
async def play(interaction: discord.Interaction, song_query: str):
    await interaction.response.defer()

    voice_channel = interaction.user.voice.channel

    if voice_channel is None:
        await interaction.followup.send("You must be in a voice channel.")
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None:
        voice_client = await voice_channel.connect()
    elif voice_channel != voice_client.channel:
        await voice_client.move_to(voice_channel)

    ydl_options = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "youtube_include_dash_manifest": False,
        "youtube_include_hls_manifest": False,
    }

    query = build_query(song_query)
    results = await search_ytdlp_async(query, ydl_options)


    # Case 1: Playlist or search → dict with "entries"
    if "entries" in results:
        tracks = results["entries"]
    else:
    # Case 2: Direct video → yt-dlp returns a single dict
        tracks = [results]

    if tracks is None:
        await interaction.followup.send("No results found.")
        return

    first_track = tracks[0]
    audio_url = first_track["url"]
    title = first_track.get("title", "Untitled")
    duration_seconds = first_track.get("duration", 0)  # duration in seconds
    

    guild_id = str(interaction.guild_id)
    if SONG_QUEUES.get(guild_id) is None:
        SONG_QUEUES[guild_id] = deque()

    SONG_QUEUES[guild_id].append((audio_url, title, duration_seconds))

    if voice_client.is_playing() or voice_client.is_paused():
        await interaction.followup.send(f"Added to queue: **{title}**")
    else:
        msg = await interaction.followup.send("✅", ephemeral=True)
        await interaction.delete_original_response()
        await play_next_song(voice_client, interaction, voice_channel, guild_id, interaction.channel)


async def play_next_song(voice_client, interaction, voice_channel, guild_id, channel):
    if SONG_QUEUES[guild_id]:
        audio_url, title, duration_seconds = SONG_QUEUES[guild_id].popleft()
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60

        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn -c:a libopus -b:a 96k",
            # Remove executable if FFmpeg is in PATH
        }

        source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options, executable="bin\\ffmpeg\\ffmpeg.exe")

        def after_play(error):
            if error:
                print(f"Error playing {title}: {error}")
            asyncio.run_coroutine_threadsafe(play_next_song(voice_client, interaction, voice_channel, guild_id, channel), bot.loop)

        voice_client = interaction.guild.voice_client

        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_channel != voice_client.channel:
            await voice_client.move_to(voice_channel)


        voice_client.play(source, after=after_play)
        asyncio.create_task(channel.send(f"Now playing: **{title}** [{minutes}:{seconds:02d}]"))
    else:
        await voice_client.disconnect()
        SONG_QUEUES[guild_id] = deque()

# Method to return search query based on if the input was a youtube link or just text
def build_query(song_query: str) -> str:
    # Simple check: does it look like a URL?
    if re.match(r'https?://', song_query):
        return song_query  # use link directly
    else:
        return f"ytsearch1:{song_query}"  # fallback to search

# Run the bot
bot.run(TOKEN)

# notes:
# added time feature to tell how much time each song is
# added in ability to detect if you put in a link so it can play directly from links
# Added a queue feature to view what songs you have coming up