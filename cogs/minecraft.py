import discord
from discord.ext import commands, tasks
from utils.config import config
from utils.minefort_api import MinefortAPI
import asyncio
from typing import Optional

class MinecraftCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = MinefortAPI(config.minefort_email, config.minefort_password)
        self.servers_cache = []
        self.last_update = 0
        
        # Start background tasks
        self.status_updater.start()
    
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        self.status_updater.cancel()
    
    async def get_servers(self, force_refresh=False):
        """Get servers with caching to avoid repeated API calls"""
        current_time = asyncio.get_event_loop().time()
        
        # Refresh cache if it's empty, forced, or older than 60 seconds
        if not self.servers_cache or force_refresh or (current_time - self.last_update) > 60:
            loop = asyncio.get_event_loop()
            self.servers_cache = await loop.run_in_executor(None, self.api.get_servers)
            self.last_update = current_time
            
        return self.servers_cache
    
    @tasks.loop(minutes=5)
    async def status_updater(self):
        """Update server status message every 5 minutes"""
        try:
            servers = await self.get_servers(force_refresh=True)
            
            if not servers:
                return
                
            # Format status message
            status_lines = ["# Fck Society Server Status", ""]
            
            for server in servers:
                status_text = "UNKNOWN"
                emoji = "❓"
                
                # Map state codes to status messages and emojis
                if 'state' in server:
                    state_map = {
                        0: ("HIBERNATING", "💤"),
                        1: ("PROCESSING", "🔄"),
                        3: ("STARTING", "🔄"),
                        4: ("RUNNING", "✅"),
                        5: ("OFFLINE", "❌"),
                        8: ("STOPPING", "🔄")
                    }
                    
                    status_text, emoji = state_map.get(
                        server['state'], 
                        (f"UNKNOWN (State {server['state']})", "❓")
                    )
                
                status_lines.append(f"{emoji} **{server.get('serverName')}**: {status_text}")
            
            status_lines.append("")
            status_lines.append(f"**IP Address**: `{config.server_ip}`")
            status_lines.append(f"_Last updated: <t:{int(self.last_update)}:R>_")
            
            status_message = "\n".join(status_lines)
            
            # Find the server status channel
            channel = self.bot.get_channel(config.cpanel_channel_id)
            if channel:
                # Try to find and edit the last bot message
                async for message in channel.history(limit=10):
                    if message.author == self.bot.user and "Server Status" in message.content:
                        await message.edit(content=status_message)
                        return
                
                # If no message found, send a new one
                await channel.send(status_message)
            
        except Exception as e:
            print(f"Error updating server status: {e}")
    
    @status_updater.before_loop
    async def before_status_updater(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
    
    @commands.hybrid_command(name="serverstatus", description="Check the Minecraft server status")
    async def server_status(self, ctx):
        """Shows the current server status"""
        await ctx.defer()
        
        servers = await self.get_servers(force_refresh=True)
        
        if not servers:
            await ctx.send("❌ Failed to fetch server status. Please try again later.")
            return
            
        embed = discord.Embed(
            title="Fck Society Server Status",
            color=discord.Color.blue(),
            description=f"**IP Address**: `{config.server_ip}`"
        )
        
        for server in servers:
            status_text = "UNKNOWN"
            status_emoji = "❓"
            
            # Map state codes to status messages and emojis
            if 'state' in server:
                state_map = {
                    0: ("HIBERNATING", "💤"),
                    1: ("PROCESSING", "🔄"),
                    3: ("STARTING", "🔄"),
                    4: ("RUNNING", "✅"),
                    5: ("OFFLINE", "❌"),
                    8: ("STOPPING", "🔄")
                }
                
                status_text, status_emoji = state_map.get(
                    server['state'], 
                    (f"UNKNOWN (State {server['state']})", "❓")
                )
            
            embed.add_field(
                name=f"{status_emoji} {server.get('serverName', 'Unknown Server')}",
                value=f"Status: **{status_text}**\nID: `{server.get('serverId', 'N/A')}`",
                inline=False
            )
        
        embed.set_footer(text=f"Last Updated: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="serverip", description="Get the Minecraft server IP address")
    async def server_ip(self, ctx):
        """Shows the Minecraft server IP address"""
        embed = discord.Embed(
            title="Fck Society Minecraft Server",
            description=f"**Server IP:** `{config.server_ip}`",
            color=discord.Color.green()
        )
        embed.set_footer(text="Copy the IP address and paste it in your Minecraft client")
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="playerlist", description="Check which players are online")
    async def player_list(self, ctx):
        """Shows the list of online players"""
        await ctx.defer()
        
        servers = await self.get_servers()
        if not servers:
            await ctx.send("❌ Failed to fetch server information. Please try again later.")
            return
        
        # Assuming the first server in the list
        server = servers[0]
        server_id = server.get('serverId')
        
        if server.get('state') != 4:  # 4 = RUNNING
            status_text = "UNKNOWN"
            if 'state' in server:
                state_map = {0: "HIBERNATING", 1: "PROCESSING", 3: "STARTING", 
                            4: "RUNNING", 5: "OFFLINE", 8: "STOPPING"}
                status_text = state_map.get(server['state'], f"UNKNOWN (State {server['state']})")
            
            await ctx.send(f"❌ Server is not running. Current status: **{status_text}**")
            return
        
        # Get player count from server info
        player_count = server.get('playerCount', 0)
        max_players = server.get('maxPlayers', 0)
        
        # Unfortunately, your cli.py doesn't include player names fetching
        # Typically we would call something like await self.api.get_player_list(server_id)
        # Instead, we'll just show the count based on server info
        
        embed = discord.Embed(
            title="Online Players",
            description=f"**{player_count}/{max_players}** players currently online",
            color=discord.Color.green() if player_count > 0 else discord.Color.light_gray()
        )
        
        # If there's player data available, add it
        # This is a placeholder as the actual implementation depends on the API
        if player_count > 0 and hasattr(server, 'players') and server.players:
            player_names = [player.get('name', 'Unknown') for player in server.players]
            embed.add_field(name="Players", value="\n".join(player_names), inline=False)
        
        embed.set_footer(text=f"Server: {server.get('serverName')} | Last Updated: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="startserver", description="Start the Minecraft server")
    @commands.has_any_role("Admin", "Moderator")
    async def start_server(self, ctx):
        """Starts the Minecraft server"""
        # Only allow in cPanel channel
        if ctx.channel.id != config.cpanel_channel_id:
            await ctx.send("❌ This command can only be used in the cPanel channel.", ephemeral=True)
            return
        
        await ctx.defer()
        
        servers = await self.get_servers()
        if not servers:
            await ctx.send("❌ Failed to fetch server information. Please try again later.")
            return
        
        # For simplicity, using the first server
        server = servers[0]
        server_id = server.get('serverId')
        server_name = server.get('serverName', 'Unknown Server')
        
        loop = asyncio.get_event_loop()
        success, message = await loop.run_in_executor(
            None, lambda: self.api.perform_server_action(server_id, 'start')
        )
        
        if success:
            await ctx.send(f"✅ Starting server **{server_name}**!\n{message}")
            # Force refresh status
            await asyncio.sleep(5)
            await self.status_updater()
        else:
            await ctx.send(f"❌ Failed to start server: {message}")

    @commands.hybrid_command(name="stopserver", description="Stop the Minecraft server")
    @commands.has_any_role("Admin", "Moderator")
    async def stop_server(self, ctx):
        """Stops the Minecraft server"""
        # Only allow in cPanel channel
        if ctx.channel.id != config.cpanel_channel_id:
            await ctx.send("❌ This command can only be used in the cPanel channel.", ephemeral=True)
            return
            
        await ctx.defer()
        
        servers = await self.get_servers()
        if not servers:
            await ctx.send("❌ Failed to fetch server information. Please try again later.")
            return
        
        # For simplicity, using the first server
        server = servers[0]
        server_id = server.get('serverId')
        server_name = server.get('serverName', 'Unknown Server')
        
        loop = asyncio.get_event_loop()
        success, message = await loop.run_in_executor(
            None, lambda: self.api.perform_server_action(server_id, 'kill')
        )
        
        if success:
            await ctx.send(f"✅ Stopping server **{server_name}**!\n{message}")
            # Force refresh status
            await asyncio.sleep(5)
            await self.status_updater()
        else:
            await ctx.send(f"❌ Failed to stop server: {message}")

    @commands.hybrid_command(name="sleepserver", description="Hibernate the Minecraft server")
    @commands.has_any_role("Admin", "Moderator")
    async def sleep_server(self, ctx):
        """Hibernates the Minecraft server"""
        # Only allow in cPanel channel
        if ctx.channel.id != config.cpanel_channel_id:
            await ctx.send("❌ This command can only be used in the cPanel channel.", ephemeral=True)
            return
            
        await ctx.defer()
        
        servers = await self.get_servers()
        if not servers:
            await ctx.send("❌ Failed to fetch server information. Please try again later.")
            return
        
        # For simplicity, using the first server
        server = servers[0]
        server_id = server.get('serverId')
        server_name = server.get('serverName', 'Unknown Server')
        
        loop = asyncio.get_event_loop()
        success, message = await loop.run_in_executor(
            None, lambda: self.api.perform_server_action(server_id, 'sleep')
        )
        
        if success:
            await ctx.send(f"✅ Hibernating server **{server_name}**!\n{message}")
            # Force refresh status
            await asyncio.sleep(5)
            await self.status_updater()
        else:
            await ctx.send(f"❌ Failed to hibernate server: {message}")

    @commands.hybrid_command(name="wakeserver", description="Wake up the hibernating Minecraft server")
    @commands.has_any_role("Admin", "Moderator")
    async def wake_server(self, ctx):
        """Wakes up the hibernating Minecraft server"""
        # Only allow in cPanel channel
        if ctx.channel.id != config.cpanel_channel_id:
            await ctx.send("❌ This command can only be used in the cPanel channel.", ephemeral=True)
            return
            
        await ctx.defer()
        
        servers = await self.get_servers()
        if not servers:
            await ctx.send("❌ Failed to fetch server information. Please try again later.")
            return
        
        # For simplicity, using the first server
        server = servers[0]
        server_id = server.get('serverId')
        server_name = server.get('serverName', 'Unknown Server')
        
        loop = asyncio.get_event_loop()
        success, message = await loop.run_in_executor(
            None, lambda: self.api.perform_server_action(server_id, 'wakeup')
        )
        
        if success:
            await ctx.send(f"✅ Waking up server **{server_name}**!\n{message}")
            # Force refresh status
            await asyncio.sleep(5)
            await self.status_updater()
        else:
            await ctx.send(f"❌ Failed to wake up server: {message}")

async def setup(bot):
    await bot.add_cog(MinecraftCommands(bot))