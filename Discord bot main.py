import discord
import logging
import json
import asyncio
import time
import os
from datetime import datetime, timedelta

# ✅ Securely Load Bot Token from Environment Variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN") # Set this in your system environment variables

# ✅ Define Server IDs
SOURCE_SERVER_ID = 
TARGET_SERVER_ID = 

# ✅ Ensure Log and Checkpoint Folder Exists
BASE_DIR = os.path.join(os.path.expanduser("~"), "discord_bot")
os.makedirs(BASE_DIR, exist_ok=True)

CHECKPOINT_FILE = r"checkpoint.json" # Change the text inside the r"" to the directory where the bot should output checkpoint.json!
LOG_FILE = r"bot_log.txt" # Change the text inside the r"" to the directory where the bot should output bot_log.txt!

# ✅ Enable Logging to File and Console
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # Save logs to file
        logging.StreamHandler()  # Also print logs to console
    ]
)

# ✅ Set Up Bot Intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.members = True

bot = discord.Client(intents=intents)

# ✅ Initialize Operation Log
operation_log = []

def load_checkpoints():
    """Loads saved checkpoints from file."""
    try:
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_checkpoint(channel_id, message_id):
    """Saves the last processed message ID for a channel."""
    checkpoints = load_checkpoints()
    checkpoints[str(channel_id)] = message_id
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoints, f)

@bot.event
async def on_ready():
    """Executes when the bot starts up."""
    try:
        logging.info(f'✅ Logged in as {bot.user}')
        
        # 🔹 Check for missing permissions
        missing_perms = []
        guild = bot.get_guild(SOURCE_SERVER_ID)
        if guild:
            me = guild.me
            if not me.guild_permissions.read_message_history:
                missing_perms.append("Read Message History")
            if not me.guild_permissions.manage_channels:
                missing_perms.append("Manage Channels")

        if missing_perms:
            logging.warning(f"⚠ Missing permissions: {', '.join(missing_perms)}")

        # 🔹 Start copying messages
        channel_to_copy = '' #Specify channel here
        logging.info(f"Attempting to copy messages from channel: {channel_to_copy}")
        await copy_past_messages(channel_name=channel_to_copy)

    except Exception as e:
        logging.error(f"❌ on_ready() crashed: {e}")

async def copy_past_messages(channel_name: str):
    """Copies past messages from a specific channel in source server to target server, resuming if needed."""
    logging.info(f"Attempting to copy past messages from '{channel_name}'")

    source_guild = bot.get_guild(SOURCE_SERVER_ID)
    target_guild = bot.get_guild(TARGET_SERVER_ID)

    if not source_guild or not target_guild:
        logging.error("❌ Server not found. Check server IDs!")
        return

    source_channel = discord.utils.get(source_guild.text_channels, name=channel_name)
    if not source_channel:
        logging.error(f"❌ Channel {channel_name} not found in source server.")
        return

    target_channel = discord.utils.get(target_guild.channels, name=source_channel.name)
    
    if not target_channel:
        logging.info(f"🔹 Creating channel: {source_channel.name}")
        target_channel = await target_guild.create_text_channel(name=source_channel.name)

    checkpoints = load_checkpoints()
    last_message_id = checkpoints.get(str(source_channel.id), None)

    messages = []
    async for message in source_channel.history(limit=1000, after=discord.Object(id=last_message_id) if last_message_id else None):
        messages.append(message)

    for message in reversed(messages):
        await process_message(message, target_channel)
        save_checkpoint(source_channel.id, message.id)  # Save progress after each message

async def process_message(message, target_channel):
    """Handles processing and sending messages correctly."""
    try:
        start_time = time.time()
        operation_log.append(f"Processing message {message.id} from {message.author.name}")

        member = message.guild.get_member(message.author.id)
        color = member.color if member and member.color != discord.Color.default() else discord.Color.default()

        # ✅ Convert timestamp to UTC+1
        utc_plus_1_time = message.created_at + timedelta(hours=1)
        formatted_time = utc_plus_1_time.strftime('%Y-%m-%d %H:%M:%S')

        # ✅ Handle normal text messages (excluding Tenor links)
        if message.content:
            # Check if the message contains Tenor links
            tenor_links = [word for word in message.content.split() if "https://tenor.com" in word]
            if tenor_links:
                for link in tenor_links:
                    await target_channel.send(link)  # Send the Tenor link
                # Remove Tenor links from the message content
                message.content = " ".join([word for word in message.content.split() if "https://tenor.com" not in word])

            # Handle non-Tenor text messages
            if message.content.strip():  # Only send if content is not empty
                embed = discord.Embed(
                    description=message.content,
                    color=color
                )
                embed.set_author(
                    name=f"{message.author.name}",
                    icon_url=message.author.avatar.url if message.author.avatar else None
                )
                embed.set_footer(text=f"Sent on {formatted_time} UTC+1")
                await target_channel.send(embed=embed)

        # ✅ Handle attachments (images, videos, etc.)
        if message.attachments:
            attachment_links = []
            for attachment in message.attachments:
                try:
                    # Try sending the file
                    await target_channel.send(file=await attachment.to_file())
                except discord.HTTPException as e:
                    if e.code == 40005:  # "Request entity too large"
                        logging.warning(f"⚠ File too large: {attachment.url}")
                        attachment_links.append(attachment.url)

            # Send links for oversized files
            if attachment_links:
                await target_channel.send("\n".join(attachment_links))

        # ✅ Log Last 10 Operations if Process Takes Too Long
        if time.time() - start_time > 120:
            logging.warning("⚠ Process taking too long! Last 10 operations:")
            for op in operation_log[-10:]:
                logging.warning(op)

    except Exception as e:
        logging.error(f"❌ Error processing message: {e}")

@bot.event
async def on_message(message):
    """Copies new messages in real-time."""
    if message.author == bot.user:
        return

    if message.guild and message.guild.id == SOURCE_SERVER_ID:
        try:
            target_guild = bot.get_guild(TARGET_SERVER_ID)
            target_channel = discord.utils.get(target_guild.channels, name=message.channel.name)

            if not target_channel:
                logging.info(f"🔹 Creating missing channel: {message.channel.name}")
                target_channel = await target_guild.create_text_channel(name=message.channel.name)

            await process_message(message, target_channel)

        except Exception as e:
            logging.error(f"❌ Error handling new message: {e}")

bot.run(TOKEN)
