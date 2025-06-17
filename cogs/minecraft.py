import discord
from discord.ext import commands, tasks
from utils.config import config
from utils.minefort_api import MinefortAPI
import asyncio
from typing import Optional
import time

class MinecraftCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = MinefortAPI(config.minefort_email, config.minefort_password)
        self.servers_cache = []
        self.last_update = 0
        self.last_status_message_id = None
        self.last_console_message_id = None
        self.last_console_content = ""
        
        # Start background tasks
        self.status_updater.start()
        self.console_updater.start()
    
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        self.status_updater.cancel()
        self.console_updater.cancel()
    
    async def get_servers(self, force_refresh=False):
        """Get servers with caching to avoid repeated API calls"""
        current_time = asyncio.get_event_loop().time()
        
        # Refresh cache if it's empty, forced, or older than 30 seconds
        if not self.servers_cache or force_refresh or (current_time - self.last_update) > 30:
            loop = asyncio.get_event_loop()
            try:
                self.servers_cache = await loop.run_in_executor(None, self.api.get_servers)
                self.last_update = current_time
            except Exception as e:
                print(f"❌ Error refreshing servers cache: {e}")
                
        return self.servers_cache
    
    def has_admin_role(self, member):
        """Check if member has admin or moderator role"""
        admin_role = discord.utils.get(member.roles, id=config.admin_role_id)
        mod_role = discord.utils.get(member.roles, id=config.mod_role_id)
        return admin_role is not None or mod_role is not None
    
    def is_owner(self, user):
        """Check if user is the bot owner"""
        return user.id == config.owner_id
    
    @tasks.loop(minutes=1)  # Every 1 minute
    async def status_updater(self):
        """Update server status message every minute"""
        try:
            servers = await self.get_servers(force_refresh=True)
            
            if not servers:
                return
                
            # Format status message
            status_lines = ["# 🖥️ Fck Society Server Status", ""]
            
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
                
                # Add player count if server is running
                player_info = ""
                if server.get('state') == 4:  # Running
                    player_count = server.get('playerCount', 0)
                    max_players = server.get('maxPlayers', 0)
                    player_info = f" | Players: {player_count}/{max_players}"
                
                status_lines.append(f"{emoji} **{server.get('serverName')}**: {status_text}{player_info}")
            
            status_lines.append("")
            status_lines.append(f"**IP Address**: `{config.server_ip}`")
            status_lines.append(f"_Last updated: <t:{int(time.time())}:R>_")
            
            status_message = "\n".join(status_lines)
            
            # Find the STATUS channel (not cPanel)
            channel = self.bot.get_channel(config.status_channel_id)
            if not channel:
                return
            
            # Try to find and edit the last status message
            message_updated = False
            if self.last_status_message_id:
                try:
                    message = await channel.fetch_message(self.last_status_message_id)
                    await message.edit(content=status_message)
                    message_updated = True
                except discord.NotFound:
                    self.last_status_message_id = None
                except Exception:
                    pass
            
            # If no previous message found or edit failed, send a new one
            if not message_updated:
                try:
                    message = await channel.send(status_message)
                    self.last_status_message_id = message.id
                except Exception:
                    pass
            
        except Exception:
            pass  # Silent fail
    
    @tasks.loop(seconds=30)  # Update console every 30 seconds
    async def console_updater(self):
        """Update console logs every 30 seconds"""
        try:
            servers = await self.get_servers()
            if not servers:
                return
            
            # Get the first server's ID
            server_id = servers[0].get('serverId')
            if not server_id:
                return
            
            # Only update console if server is running
            if servers[0].get('state') != 4:  # Not running
                return
            
            # Get console logs
            loop = asyncio.get_event_loop()
            success, logs = await loop.run_in_executor(
                None, lambda: self.api.get_console_logs(server_id)
            )
            
            if not success:
                return
            
            # If logs haven't changed, don't update
            if logs == self.last_console_content:
                return
                
            self.last_console_content = logs
            
            # Format console message
            console_lines = ["# 📟 Server Console", "```"]
            
            # Limit logs to last 20 lines to avoid message size limits
            if isinstance(logs, str):
                log_lines = logs.split('\n')[-20:] if logs else ["No recent logs available"]
            else:
                log_lines = ["No recent logs available"]
                
            console_lines.extend(log_lines)
            console_lines.append("```")
            console_lines.append(f"_Last updated: <t:{int(time.time())}:R>_")
            console_lines.append("\n**Owner only**: Type commands directly in this channel")
            
            console_message = "\n".join(console_lines)
            
            # Find the console channel
            channel = self.bot.get_channel(config.console_channel_id)
            if channel:
                # Try to find and edit the last console message
                if self.last_console_message_id:
                    try:
                        message = await channel.fetch_message(self.last_console_message_id)
                        await message.edit(content=console_message)
                        return
                    except discord.NotFound:
                        self.last_console_message_id = None
                
                # If no previous message found, send a new one
                message = await channel.send(console_message)
                self.last_console_message_id = message.id
            
        except Exception:
            pass  # Silent fail
    
    @status_updater.before_loop
    async def before_status_updater(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
    
    @console_updater.before_loop
    async def before_console_updater(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle console commands sent in the console channel"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Only process messages in the console channel
        if message.channel.id != config.console_channel_id:
            return
        
        # Only allow owner to send commands
        if not self.is_owner(message.author):
            await message.reply("❌ Only the server owner can send console commands.", delete_after=5)
            await message.delete(delay=5)
            return
        
        # Get the command from the message
        command = message.content.strip()
        if not command:
            return
        
        # Get server info
        servers = await self.get_servers()
        if not servers:
            await message.reply("❌ Failed to get server information.", delete_after=5)
            return
        
        server_id = servers[0].get('serverId')
        if servers[0].get('state') != 4:  # Not running
            await message.reply("❌ Server is not running. Console commands are only available when the server is online.", delete_after=10)
            return
        
        # Send the command
        loop = asyncio.get_event_loop()
        success, response = await loop.run_in_executor(
            None, lambda: self.api.send_console_command(server_id, command)
        )
        
        if success:
            await message.add_reaction("✅")
            # Force update console logs after command
            await asyncio.sleep(2)
            await self.console_updater()
        else:
            await message.reply(f"❌ Failed to send command: {response}", delete_after=10)
    
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
            
            # Add player count if available
            player_info = ""
            if server.get('state') == 4:  # Running
                player_count = server.get('playerCount', 0)
                max_players = server.get('maxPlayers', 0)
                player_info = f"\nPlayers: {player_count}/{max_players}"
            
            embed.add_field(
                name=f"{status_emoji} {server.get('serverName', 'Unknown Server')}",
                value=f"Status: **{status_text}**\nID: `{server.get('serverId', 'N/A')}`{player_info}",
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
        
        embed = discord.Embed(
            title="Online Players",
            description=f"**{player_count}/{max_players}** players currently online",
            color=discord.Color.green() if player_count > 0 else discord.Color.light_gray()
        )
        
        # If there's player data available, add it
        if player_count > 0 and hasattr(server, 'players') and server.players:
            player_names = [player.get('name', 'Unknown') for player in server.players]
            embed.add_field(name="Players", value="\n".join(player_names), inline=False)
        
        embed.set_footer(text=f"Server: {server.get('serverName')} | Last Updated: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="startserver", description="Start the Minecraft server")
    async def start_server(self, ctx):
        """Starts the Minecraft server - Available to everyone in commands channel"""
        # Check channel restriction
        if ctx.channel.id != config.commands_channel_id:
            await ctx.send("❌ This command can only be used in the commands channel.", ephemeral=True)
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

    @commands.hybrid_command(name="wakeserver", description="Wake up the hibernating Minecraft server")
    async def wake_server(self, ctx):
        """Wakes up the hibernating Minecraft server - Available to everyone in commands channel"""
        # Check channel restriction
        if ctx.channel.id != config.commands_channel_id:
            await ctx.send("❌ This command can only be used in the commands channel.", ephemeral=True)
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

    @commands.hybrid_command(name="stopserver", description="Stop the Minecraft server")
    @commands.has_any_role("Admin", "Moderator")
    async def stop_server(self, ctx):
        """Stops the Minecraft server - Admin/Mod only in cPanel channel"""
        # Check channel restriction
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
        """Hibernates the Minecraft server - Admin/Mod only in cPanel channel"""
        # Check channel restriction
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

async def setup(bot):
    await bot.add_cog(MinecraftCommands(bot))
