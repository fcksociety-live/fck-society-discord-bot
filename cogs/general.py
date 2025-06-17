import discord
from discord.ext import commands
import platform
import time
from utils.config import config


class General(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @commands.hybrid_command(name="ping",
                             description="Check the bot's latency")
    async def ping(self, ctx):
        """Check the bot's response time"""
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"Pong! 🏓 Response time: {latency}ms")

    @commands.hybrid_command(name="botinfo",
                             description="Get information about the bot")
    async def botinfo(self, ctx):
        """Displays information about the bot"""
        uptime = int(time.time() - self.start_time)
        days, remainder = divmod(uptime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        embed = discord.Embed(
            title="Fck Society Bot Info",
            color=discord.Color.blue(),
            description=
            "A custom bot for managing the Fck Society Minecraft server")

        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="Discord.py Version",
                        value=discord.__version__,
                        inline=True)
        embed.add_field(name="Python Version",
                        value=platform.python_version(),
                        inline=True)

        embed.add_field(
            name="Commands",
            value=("`/serverstatus` - Check the Minecraft server status\n"
                   "`/serverip` - Get the Minecraft server IP\n"
                   "`/playerlist` - View online players\n"
                   "`/startserver` - Start the server (commands channel)\n"
                   "`/wakeserver` - Wake up the server (commands channel)\n"
                   "`/lock` - Lock your voice channel\n"
                   "`/unlock` - Unlock your voice channel\n"),
            inline=False)

        embed.set_footer(text="Made for Fck Society Minecraft Server")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="societyhelp",
                             description="Show bot commands")
    async def societyhelp(self, ctx):
        """Shows the help menu with all commands"""
        embed = discord.Embed(
            title="Fck Society Bot Commands",
            color=discord.Color.blue(),
            description="Here are the commands you can use with this bot:")

        minecraft_commands = (
            "`/serverstatus` - Check the Minecraft server status\n"
            "`/serverip` - Get the Minecraft server IP address\n"
            "`/playerlist` - See which players are online\n")

        public_server_commands = (
            "`/startserver` - Start the Minecraft server (🔹 commands channel only)\n"
            "`/wakeserver` - Wake up the Minecraft server (🔹 commands channel only)\n"
        )

        admin_commands = (
            "`/stopserver` - Stop the Minecraft server (🔸 cPanel channel, Admin/Mod only)\n"
            "`/sleepserver` - Hibernate the Minecraft server (🔸 cPanel channel, Admin/Mod only)\n"
        )

        voice_commands = (
            "`/lock` - Lock your voice channel to prevent others from joining\n"
            "`/unlock` - Unlock your voice channel to allow everyone to join\n"
            "`/invite @user` - Invite a specific user to your locked voice channel\n"
        )

        general_commands = ("`/ping` - Check bot latency\n"
                            "`/botinfo` - View information about the bot\n"
                            "`/societyhelp` - Show this help message\n")

        embed.add_field(name="📋 Minecraft Info Commands",
                        value=minecraft_commands,
                        inline=False)
        embed.add_field(name="🚀 Public Server Commands",
                        value=public_server_commands,
                        inline=False)
        embed.add_field(name="🔊 Voice Channel Commands",
                        value=voice_commands,
                        inline=False)
        embed.add_field(name="🤖 General Commands",
                        value=general_commands,
                        inline=False)
        embed.add_field(name="🛡️ Admin Commands",
                        value=admin_commands,
                        inline=False)

        embed.add_field(
            name="📟 Console Channel",
            value="**Owner Only**: Send commands directly to the server console in the console channel",
            inline=False
        )

        embed.set_footer(
            text="🔹 = Available to everyone | 🔸 = Admin/Mod only | 📟 = Owner only"
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(General(bot))
