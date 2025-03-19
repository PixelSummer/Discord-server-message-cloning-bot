import discord
import logging
import json
import asyncio
import time
import os
from datetime import datetime, timedelta

# ✅ Securely Load Bot Token from Environment Variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Set this in your system environment variables

# ✅ Define Server IDs
SOURCE_SERVER_ID = 
TARGET_SERVER_ID = 

# ✅ Specify Channels to Copy
CHANNELS_TO_COPY = [
    "",
    "",
    "",
    "",
    "",
    "",
    ""
]  # Update this list with channel names inside citation

# ✅ Store Log and Checkpoint Files in the Same Directory as the Script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get directory where script is located
CHECKPOINT_FILE = os.path.join(BASE_DIR, "last_checkpoint.json")
LOG_FILE = os.path.join(BASE_DIR, "bot_log.txt")


def ensure_file_exists(file_path, default_content="{}"):
    """Ensures the given file exists, creating it if necessary."""
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(default_content)


# ✅ Ensure the checkpoint and log files exist
ensure_file_exists(CHECKPOINT_FILE)
ensure_file_exists(LOG_FILE, default_content="")

# ✅ Enable Logging to File and Console
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),  # ✅ Logs saved in script directory
        logging.StreamHandler()  # ✅ Also print logs to console
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
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_checkpoint(channel_id, message_id):
    """Saves the last processed message ID for a channel."""
    checkpoints = load_checkpoints()
    checkpoints[str(channel_id)] = message_id
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoints, f)


async def copy_past_messages(channel_name: str):
    """Copies past messages from a specific channel in the source server to the target server."""
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

    logging.info(f"📌 Found {len(messages)} messages in {channel_name}")

    for message in reversed(messages):
        await process_message(message, target_channel)
        save_checkpoint(source_channel.id, message.id)  # Save progress after each message

    logging.info(f"✅ Finished copying messages from '{channel_name}'")


@bot.event
async def on_ready():
    """Executes when the bot starts up and begins copying channels."""
    try:
        logging.info(f'✅ Logged in as {bot.user}')

        # 🔹 Start copying messages for each specified channel sequentially
        for channel_name in CHANNELS_TO_COPY:
            logging.info(f"📌 Starting to copy messages from channel: {channel_name}")
            await copy_past_messages(channel_name)
            await asyncio.sleep(2)  # Small delay to prevent rate limits

        logging.info("✅ Finished copying all specified channels.")

    except Exception as e:
        logging.error(f"❌ on_ready() crashed: {e}")


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
        tenor_links = [word for word in message.content.split() if "https://tenor.com" in word]
        message_text = " ".join([word for word in message.content.split() if "https://tenor.com" not in word])

        if message_text.strip():
            embed = discord.Embed(description=message_text, color=color)
            embed.set_author(name=f"{message.author.name}", icon_url=message.author.avatar.url if message.author.avatar else None)
            embed.set_footer(text=f"Sent on {formatted_time} UTC+1")
            await target_channel.send(embed=embed)

        # ✅ Send Tenor links separately
        for link in tenor_links:
            await target_channel.send(link)

        # ✅ Handle images/videos separately
        media_files = [attachment for attachment in message.attachments if not attachment.filename.lower().endswith((".gif", ".gifv"))]

        if media_files:
            # 🔹 First, send an embed with the author info
            media_embed = discord.Embed(color=color)
            media_embed.set_author(name=f"{message.author.name}", icon_url=message.author.avatar.url if message.author.avatar else None)
            await target_channel.send(embed=media_embed)

            # 🔹 Then send all images/videos
            for attachment in media_files:
                try:
                    await target_channel.send(file=await attachment.to_file())
                except discord.HTTPException as e:
                    if e.code == 40005:  # "Request entity too large"
                        logging.warning(f"⚠ File too large: {attachment.url}")
                        await target_channel.send(f"📎 **Pic/Vid** {attachment.url}")  # ✅ Send link instead

        # ✅ Log Last 10 Operations if Process Takes Too Long
        if time.time() - start_time > 120:
            logging.warning("⚠ Process taking too long! Last 10 operations:")
            for op in operation_log[-10:]:
                logging.warning(op)

    except Exception as e:
        logging.error(f"❌ Error processing message: {e}")


bot.run(TOKEN)
