import voice_patch

import discord
from discord.ext import commands
import asyncio
import os
import logging
from utils.config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('bot')

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True  # Required for voice channel features

# Create bot instance
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Called when the bot is ready to start working"""
    logger.info(f'Bot logged in as {bot.user.name} ({bot.user.id})')
    
    # Set activity status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="Fck Society Minecraft"
        )
    )
    
    # Sync app commands with Discord
    try:
        logger.info("Syncing application commands...")
        await bot.tree.sync()
        logger.info("Application commands synced successfully!")
    except Exception as e:
        logger.error(f"Failed to sync application commands: {e}")
    
    logger.info("Bot is ready!")

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Bad argument: {error}")
    elif isinstance(error, commands.MissingPermissions) or isinstance(error, commands.MissingRole):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds.")
    else:
        logger.error(f"Command error in {ctx.command}: {error}")
        await ctx.send("An error occurred while processing this command.")

async def load_extensions():
    """Load all cogs"""
    cogs_dir = "cogs"
    for filename in os.listdir(cogs_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f"{cogs_dir}.{filename[:-3]}")
                logger.info(f"Loaded extension {filename[:-3]}")
            except Exception as e:
                logger.error(f"Failed to load extension {filename[:-3]}: {e}")

async def main():
    """Main entry point for the bot"""
    # First load all cogs
    await load_extensions()
    
    # Then start the bot
    token = config.token
    if not token:
        logger.error("No Discord token provided. Please set DISCORD_TOKEN environment variable.")
        return
    
    # Check if Minefort credentials are set
    if not config.minefort_email or not config.minefort_password:
        logger.warning("Minefort credentials are not set. Server management features will not work.")
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("Invalid Discord token. Please check your DISCORD_TOKEN environment variable.")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())