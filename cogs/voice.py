import discord
from discord.ext import commands
import asyncio
from utils.config import config

class VoiceChannels(commands.Cog):
    """
    Voice channel management cog
    Note: This implementation only manages voice channels and doesn't use audio streaming functionality
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = {}  # track temp channels: {channel_id: owner_id}
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state changes for temp channel creation/deletion"""
        # Skip if the member is a bot
        if member.bot:
            return
        
        # Check if member joined the "create VC" channel
        if after.channel and after.channel.id == config.create_vc_channel_id:
            await self.create_temp_voice_channel(member)
            return
        
        # Check if member left a temp channel they own
        if before.channel and before.channel.id in self.temp_channels:
            if self.temp_channels[before.channel.id] == member.id:
                # Only delete if the channel is empty
                if not before.channel.members:
                    await self.delete_temp_voice_channel(before.channel)
                    return
        
        # Check if a temp channel is empty (fallback cleanup)
        for channel_id, owner_id in list(self.temp_channels.items()):
            channel = self.bot.get_channel(channel_id)
            if channel and not channel.members:
                await self.delete_temp_voice_channel(channel)
    
    async def create_temp_voice_channel(self, member):
        """Create a temporary voice channel for the member"""
        # Get the temp VC category
        category = self.bot.get_channel(config.temp_vc_category_id)
        if not category:
            # Fallback to the category of the "create VC" channel
            create_channel = self.bot.get_channel(config.create_vc_channel_id)
            category = create_channel.category if create_channel else None
        
        if not category:
            return
        
        # Create the new voice channel
        channel_name = f"🔊 {member.display_name}'s Channel"
        try:
            # Set default permissions - everyone can join but only owner can manage
            overwrites = {
                member.guild.default_role: discord.PermissionOverwrite(
                    connect=True,
                    speak=True
                ),
                member: discord.PermissionOverwrite(
                    connect=True,
                    speak=True,
                    move_members=True,
                    mute_members=True,
                    deafen_members=True,
                    manage_channels=True  # Allows changing name, etc.
                )
            }
            
            new_channel = await category.create_voice_channel(
                name=channel_name,
                overwrites=overwrites
            )
            
            # Store channel ownership
            self.temp_channels[new_channel.id] = member.id
            
            # Move the member to the new channel
            await member.move_to(new_channel)
            
            # Send instructions as a DM
            try:
                embed = discord.Embed(
                    title="Temporary Voice Channel Created",
                    description=(
                        f"Your voice channel **{channel_name}** has been created!\n\n"
                        "**You can:**\n"
                        "• Rename the channel\n"
                        "• Control who can join\n"
                        "• Mute/deafen others\n\n"
                        "The channel will be deleted when everyone leaves."
                    ),
                    color=discord.Color.green()
                )
                await member.send(embed=embed)
            except discord.Forbidden:
                # If DM fails, send a message in the channel instead (visible only to them)
                pass
                
        except discord.Forbidden:
            # Missing permissions
            try:
                await member.send("I don't have permission to create voice channels. Please contact a server administrator.")
            except:
                pass
        except Exception as e:
            print(f"Error creating temp channel: {e}")
    
    async def delete_temp_voice_channel(self, channel):
        """Delete a temporary voice channel if it's empty"""
        try:
            # Small delay to prevent instant deletion if someone is rejoining
            await asyncio.sleep(2)
            
            # Recheck if the channel is still empty
            if not channel.members:
                await channel.delete(reason="Temporary voice channel is empty")
                # Remove from tracking dict
                if channel.id in self.temp_channels:
                    del self.temp_channels[channel.id]
        except Exception as e:
            print(f"Error deleting temp channel: {e}")
    
    @commands.hybrid_command(name="lock", description="Lock your voice channel to prevent others from joining")
    async def lock_voice_channel(self, ctx):
        """Lock your temporary voice channel"""
        # Check if user is in a voice channel they own
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("You need to be in a voice channel to use this command.", ephemeral=True)
            return
            
        channel = ctx.author.voice.channel
        if channel.id not in self.temp_channels or self.temp_channels[channel.id] != ctx.author.id:
            await ctx.send("You can only lock voice channels you created.", ephemeral=True)
            return
        
        # Lock the channel
        try:
            await channel.set_permissions(ctx.guild.default_role, connect=False)
            await ctx.send(f"🔒 Voice channel locked! Only you can add people now.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"Failed to lock channel: {e}", ephemeral=True)
    
    @commands.hybrid_command(name="unlock", description="Unlock your voice channel to allow others to join")
    async def unlock_voice_channel(self, ctx):
        """Unlock your temporary voice channel"""
        # Check if user is in a voice channel they own
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("You need to be in a voice channel to use this command.", ephemeral=True)
            return
            
        channel = ctx.author.voice.channel
        if channel.id not in self.temp_channels or self.temp_channels[channel.id] != ctx.author.id:
            await ctx.send("You can only unlock voice channels you created.", ephemeral=True)
            return
        
        # Unlock the channel
        try:
            await channel.set_permissions(ctx.guild.default_role, connect=True)
            await ctx.send(f"🔓 Voice channel unlocked! Anyone can join now.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"Failed to unlock channel: {e}", ephemeral=True)
    
    @commands.hybrid_command(name="invite", description="Invite a user to your locked voice channel")
    async def invite_to_voice_channel(self, ctx, member: discord.Member):
        """Invite a specific user to your locked voice channel"""
        # Check if user is in a voice channel they own
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("You need to be in a voice channel to use this command.", ephemeral=True)
            return
            
        channel = ctx.author.voice.channel
        if channel.id not in self.temp_channels or self.temp_channels[channel.id] != ctx.author.id:
            await ctx.send("You can only invite users to voice channels you created.", ephemeral=True)
            return
        
        # Add permission for the member
        try:
            await channel.set_permissions(member, connect=True)
            await ctx.send(f"✅ {member.mention} can now join your voice channel.", ephemeral=True)
            
            # Notify the invited user
            try:
                embed = discord.Embed(
                    title="Voice Channel Invitation",
                    description=f"**{ctx.author.display_name}** has invited you to their voice channel: **{channel.name}**",
                    color=discord.Color.blue()
                )
                await member.send(embed=embed)
            except discord.Forbidden:
                await ctx.send(f"I couldn't DM {member.mention}, but they have been granted access to join.", ephemeral=True)
                
        except Exception as e:
            await ctx.send(f"Failed to invite user: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(VoiceChannels(bot))