# Discord-server-message-cloning-bot
A Python bot using discord.py to copy messages, media, and links from one Discord server to another. It supports resuming from the last processed message, converts timestamps to UTC+1, handles Tenor links, and manages large file attachments by sending links instead of skipping them.

This Python-based bot uses the discord.py library to copy messages from one Discord server to another, including handling text messages, media files, and links. It is designed to ensure that all important content from a specific source channel in one server is replicated in a target channel of another server, with support for resuming from the last processed message.

Features:
  
Message Copying: Automatically copies text messages, media (images, videos), and links from a source channel to a target channel.

Time Zone Handling: Converts and formats timestamps to UTC+1 before sending them to the target server.

Handling Tenor Links: Special handling for Tenor GIF links. Links are extracted from the message content and sent as standalone messages.

Resumable Process: If the bot is interrupted, it can resume from the last processed message using checkpointing. Checkpoints are stored in a JSON file to maintain progress.

File Size Handling: If attachments are too large to send (exceeding Discord’s file size limit), the bot will send the link to the file instead of skipping the message.

Logging and Debugging: The bot logs important actions and errors, allowing you to debug issues and monitor its progress. The last 10 operations are logged if the process takes longer than expected.

(!) Setup:
1. Clone or download the repository.

2. Install dependencies using pip install discord.py.

3. Set your bot's token as an environment variable (DISCORD_BOT_TOKEN).

4. Update the SOURCE_SERVER_ID, TARGET_SERVER_ID, the paths for the log and checkpoint and the name of channel_to_copy, inside the main file. 

5. Run the bot script.

6. Make a file called checkpoint.json and another file called bot_log.txt

Use Cases:

Archiving: Archive messages from one server to another for backup or storage purposes.
Content Migration: Migrate content from one server to another while maintaining the structure of channels and messages.
Media Backup: Copy messages containing media (images, videos) to ensure you have a backup of media shared in a Discord server.

Contributions:

Feel free to contribute to this project by forking the repository and submitting pull requests. If you encounter any issues or have feature requests, please open an issue on GitHub.

