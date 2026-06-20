import discord
import asyncio
import datetime
from typing import Optional
from discord.ext import commands, tasks
from database import Database
from utils import Utils
from config import config

class Moderation(commands.Cog, name='Moderation'):
    """🛡️ Advanced moderation commands for server management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.check_mutes.start()
        self.check_tempbans.start()
    
    def cog_unload(self):
        self.check_mutes.cancel()
        self.check_tempbans.cancel()
    
    @tasks.loop(seconds=30)
    async def check_mutes(self):
        """Check for expired mutes"""
        await self.bot.wait_until_ready()
        active_mutes = await Database.get_active_mutes()
        current_time = datetime.datetime.utcnow()
        
        for mute in active_mutes:
            if mute['end_time']:
                end_time = datetime.datetime.fromisoformat(mute['end_time'])
                if current_time >= end_time:
                    guild = self.bot.get_guild(mute['guild_id'])
                    if guild:
                        member = guild.get_member(mute['user_id'])
                        if member:
                            mute_role = await self.get_mute_role(guild)
                            if mute_role and mute_role in member.roles:
                                try:
                                    await member.remove_roles(mute_role, reason='Mute expired')
                                    await Database.remove_mute(mute['user_id'], mute['guild_id'])
                                except discord.Forbidden:
                                    pass
    
    @tasks.loop(minutes=5)
    async def check_tempbans(self):
        """Check for expired temporary bans"""
        await self.bot.wait_until_ready()
        pass
    
    async def get_mute_role(self, guild: discord.Guild) -> Optional[discord.Role]:
        """Get or create a mute role"""
        settings = await Database.get_guild_settings(guild.id)
        mute_role_id = settings.get('mute_role_id')
        
        if mute_role_id:
            mute_role = guild.get_role(mute_role_id)
            if mute_role:
                return mute_role
        
       
        mute_role = discord.utils.get(guild.roles, name='Muted')
        if not mute_role:
            try:
                # Create role with appropriate perms
                mute_role = await guild.create_role(
                    name='Muted',
                    reason='Mute role creation for moderation',
                    permissions=discord.Permissions(
                        send_messages=False,
                        speak=False,
                        add_reactions=False,
                        create_public_threads=False,
                        create_private_threads=False
                    ),
                    hoist=False,
                    mentionable=False
                )
                
                # Set perms
                for channel in guild.channels:
                    try:
                        await channel.set_permissions(mute_role, 
                            send_messages=False,
                            speak=False,
                            add_reactions=False,
                            create_public_threads=False,
                            create_private_threads=False
                        )
                    except discord.Forbidden:
                        continue
                
            except discord.Forbidden:
                raise commands.BotMissingPermissions(['manage_roles', 'manage_channels'])
        
        
        await Database.update_guild_settings(guild.id, mute_role_id=mute_role.id)
        return mute_role
    
    async def log_mod_action(self, guild: discord.Guild, embed: discord.Embed):
        """Log moderation action to log channel"""
        settings = await Database.get_guild_settings(guild.id)
        log_channel_id = settings.get('log_channel_id')
        
        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    await log_channel.send(embed=embed)
                except discord.Forbidden:
                    pass
    
    @commands.hybrid_command(name='warn', aliases=['w'], 
                            description='Warn a member for breaking rules')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def warn(self, ctx, member: discord.Member, *, reason: str = 'No reason provided'):
        """Warn a member for breaking rules"""
        # Permission checks
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send(f'{config.EMOJIS["error"]} You cannot warn this member due to role hierarchy.')
        
        if member.bot:
            return await ctx.send(f'{config.EMOJIS["error"]} You cannot warn bots.')
        
        # Add warning to database
        warn_id = await Database.add_warning(member.id, ctx.guild.id, ctx.author.id, reason)
        warnings = await Database.get_warnings(member.id, ctx.guild.id)
        warning_count = len(warnings)
        
        # Create embed
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["warn"]} Member Warned',
            color=discord.Color.orange(),
            fields=[
                {'name': 'Member', 'value': member.mention, 'inline': True},
                {'name': 'Moderator', 'value': ctx.author.mention, 'inline': True},
                {'name': 'Warning Count', 'value': str(warning_count), 'inline': True},
                {'name': 'Reason', 'value': reason, 'inline': False},
                {'name': 'Warning ID', 'value': f'#{warn_id}', 'inline': True}
            ],
            footer=f'Guild: {ctx.guild.name}'
        )
        
        await ctx.send(embed=embed)
        
        # Log the action
        await self.log_mod_action(ctx.guild, embed)
        
        # Check if action should be taken
        if warning_count >= config.MAX_WARNINGS_BEFORE_ACTION:
            action_embed = Utils.create_embed(
                title=f'{config.EMOJIS["warning"]} Warning Threshold Reached',
                description=f'{member.mention} has reached {warning_count} warnings.',
                color=discord.Color.red()
            )
            await ctx.send(embed=action_embed)
        
        # Try to DM the user
        try:
            dm_embed = discord.Embed(
                title=f'⚠️ Warning in {ctx.guild.name}',
                description=f'You have been warned by {ctx.author.name}',
                color=discord.Color.orange()
            )
            dm_embed.add_field(name='Reason', value=reason)
            dm_embed.add_field(name='Warning Count', value=f'{warning_count} of {config.MAX_WARNINGS_BEFORE_ACTION}')
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass
    
    @commands.hybrid_command(name='warnings', aliases=['warns'],
                            description='View warnings for a member')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def view_warnings(self, ctx, member: discord.Member):
        """View all warnings for a member"""
        warnings = await Database.get_warnings(member.id, ctx.guild.id)
        
        if not warnings:
            return await ctx.send(f'{config.EMOJIS["success"]} {member.mention} has no warnings!')
        
        embed = discord.Embed(
            title=f'📋 Warnings for {member}',
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        active_warnings = [w for w in warnings if w['active'] == 1]
        embed.add_field(name='Total Warnings', value=str(len(warnings)), inline=True)
        embed.add_field(name='Active Warnings', value=str(len(active_warnings)), inline=True)
        embed.add_field(name='Threshold', value=f'{config.MAX_WARNINGS_BEFORE_ACTION} for action', inline=True)
        
        # Add recent warnings
        if active_warnings:
            warning_list = []
            for warn in active_warnings[:5]:
                moderator = ctx.guild.get_member(warn['moderator_id'])
                mod_name = moderator.mention if moderator else f'Moderator ID: {warn["moderator_id"]}'
                date = warn['created_at'][:10] if warn['created_at'] else 'Unknown'
                warning_list.append(f'**#{warn["id"]}** - {mod_name}\n📝 {warn["reason"][:100]}\n📅 {date}')
            
            embed.add_field(
                name='Recent Warnings',
                value='\n\n'.join(warning_list) if warning_list else 'No active warnings',
                inline=False
            )
        
        embed.set_footer(text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar.url)
        
        # Create pagination if many warnings
        if len(warnings) > 5:
            pages = []
            for i in range(0, len(warnings), 5):
                page_embed = discord.Embed(
                    title=f'📋 Warnings for {member} (Page {i//5 + 1})',
                    color=discord.Color.orange()
                )
                for warn in warnings[i:i+5]:
                    moderator = ctx.guild.get_member(warn['moderator_id'])
                    mod_name = moderator.name if moderator else f'Unknown'
                    page_embed.add_field(
                        name=f'Warning #{warn["id"]} - {mod_name}',
                        value=f'**Reason:** {warn["reason"]}\n**Date:** {warn["created_at"][:19]}\n**Status:** {"Active" if warn["active"] else "Resolved"}',
                        inline=False
                    )
                pages.append(page_embed)
            await Utils.paginate(ctx, pages)
        else:
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='clearwarnings', aliases=['cw', 'delwarns'],
                            description='Clear all warnings for a member')
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(send_messages=True)
    async def clear_warnings(self, ctx, member: discord.Member):
        """Clear all warnings for a member"""
        confirm = await Utils.confirm_action(
            ctx, 
            f'Are you sure you want to clear all warnings for {member.mention}?'
        )
        
        if not confirm:
            return await ctx.send(f'{config.EMOJIS["info"]} Action cancelled.')
        
        await Database.clear_warnings(member.id, ctx.guild.id)
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["success"]} Warnings Cleared',
            description=f'All warnings have been cleared for {member.mention}.',
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
        await self.log_mod_action(ctx.guild, embed)
    
    @commands.hybrid_command(name='mute', aliases=['m'],
                            description='Mute a member')
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(manage_roles=True, moderate_members=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def mute(self, ctx, member: discord.Member, duration: str = '1h', *, reason: str = 'No reason provided'):
        """Mute a member for a specified duration"""
        # Parse duration
        seconds = Utils.parse_duration(duration)
        if seconds is None and duration.lower() not in ['perm', 'permanent', 'forever']:
            return await ctx.send(f'{config.EMOJIS["error"]} Invalid duration format. Use like: `1h30m`, `2d`, `perm`')
        
        is_permanent = duration.lower() in ['perm', 'permanent', 'forever']
        
        # Permission checks
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send(f'{config.EMOJIS["error"]} You cannot mute this member due to role hierarchy.')
        
        if member.bot:
            return await ctx.send(f'{config.EMOJIS["error"]} You cannot mute bots.')
        
        # Get mute role
        mute_role = await self.get_mute_role(ctx.guild)
        
        # Check if already muted
        if mute_role in member.roles:
            return await ctx.send(f'{config.EMOJIS["info"]} {member.mention} is already muted.')
        
        # Apply mute
        try:
            await member.add_roles(mute_role, reason=f'Muted by {ctx.author}: {reason}')
        except discord.Forbidden:
            return await ctx.send(f'{config.EMOJIS["error"]} Failed to mute {member.mention}. Check permissions.')
        
        # Add to database
        await Database.add_mute(
            member.id, 
            ctx.guild.id, 
            ctx.author.id, 
            seconds if not is_permanent else None, 
            reason
        )
        
        # Create embed
        duration_text = Utils.format_duration(seconds) if not is_permanent else 'Permanent'
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["mute"]} Member Muted',
            color=discord.Color.red(),
            fields=[
                {'name': 'Member', 'value': member.mention, 'inline': True},
                {'name': 'Moderator', 'value': ctx.author.mention, 'inline': True},
                {'name': 'Duration', 'value': duration_text, 'inline': True},
                {'name': 'Expires', 'value': f'<t:{int(datetime.datetime.utcnow().timestamp() + seconds)}:R>' if not is_permanent else 'Never', 'inline': True},
                {'name': 'Reason', 'value': reason, 'inline': False}
            ],
            footer=f'Mute ID: {ctx.guild.id}-{member.id}'
        )
        
        await ctx.send(embed=embed)
        await self.log_mod_action(ctx.guild, embed)
        
        # DM the user
        try:
            dm_embed = discord.Embed(
                title=f'🔇 Muted in {ctx.guild.name}',
                color=discord.Color.red(),
                description=f'You have been muted by {ctx.author.name}.'
            )
            dm_embed.add_field(name='Duration', value=duration_text)
            dm_embed.add_field(name='Reason', value=reason)
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass
    
    @commands.hybrid_command(name='unmute', aliases=['um'],
                            description='Unmute a member')
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member, *, reason: str = 'No reason provided'):
        """Unmute a member"""
        mute_role = await self.get_mute_role(ctx.guild)
        
        if mute_role not in member.roles:
            return await ctx.send(f'{config.EMOJIS["info"]} {member.mention} is not muted.')
        
        try:
            await member.remove_roles(mute_role, reason=f'Unmuted by {ctx.author}: {reason}')
        except discord.Forbidden:
            return await ctx.send(f'{config.EMOJIS["error"]} Failed to unmute {member.mention}.')
        
        await Database.remove_mute(member.id, ctx.guild.id)
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["success"]} Member Unmuted',
            description=f'{member.mention} has been unmuted.',
            color=discord.Color.green(),
            fields=[
                {'name': 'Moderator', 'value': ctx.author.mention, 'inline': True},
                {'name': 'Reason', 'value': reason, 'inline': False}
            ]
        )
        
        await ctx.send(embed=embed)
        await self.log_mod_action(ctx.guild, embed)
    
    @commands.hybrid_command(name='kick', aliases=['k'],
                            description='Kick a member from the server')
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def kick(self, ctx, member: discord.Member, *, reason: str = 'No reason provided'):
        """Kick a member from the server"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send(f'{config.EMOJIS["error"]} You cannot kick this member.')
        
        if member.bot:
            return await ctx.send(f'{config.EMOJIS["error"]} You cannot kick bots.')
        
        confirm = await Utils.confirm_action(
            ctx,
            f'Are you sure you want to kick {member.mention}?\n\nReason: {reason}'
        )
        
        if not confirm:
            return await ctx.send(f'{config.EMOJIS["info"]} Kick cancelled.')
        
        # DM the user
        try:
            dm_embed = discord.Embed(
                title=f'👢 Kicked from {ctx.guild.name}',
                color=discord.Color.red(),
                description=f'You have been kicked by {ctx.author.name}.'
            )
            dm_embed.add_field(name='Reason', value=reason)
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass
        
        await member.kick(reason=f'Kicked by {ctx.author}: {reason}')
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["kick"]} Member Kicked',
            color=discord.Color.red(),
            fields=[
                {'name': 'Member', 'value': f'{member} ({member.id})', 'inline': True},
                {'name': 'Moderator', 'value': ctx.author.mention, 'inline': True},
                {'name': 'Reason', 'value': reason, 'inline': False}
            ],
            footer=f'Guild: {ctx.guild.name}'
        )
        
        await ctx.send(embed=embed)
        await self.log_mod_action(ctx.guild, embed)
    
    @commands.hybrid_command(name='ban', aliases=['b'],
                            description='Ban a member from the server')
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def ban(self, ctx, member: discord.Member, delete_days: int = 0, *, reason: str = 'No reason provided'):
        """Ban a member from the server"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send(f'{config.EMOJIS["error"]} You cannot ban this member.')
        
        if member.bot:
            return await ctx.send(f'{config.EMOJIS["error"]} You cannot ban bots.')
        
        if delete_days < 0 or delete_days > 7:
            return await ctx.send(f'{config.EMOJIS["error"]} Delete days must be between 0 and 7.')
        
        confirm = await Utils.confirm_action(
            ctx,
            f'Are you sure you want to ban {member.mention}?\n\nReason: {reason}\nMessage delete days: {delete_days}'
        )
        
        if not confirm:
            return await ctx.send(f'{config.EMOJIS["info"]} Ban cancelled.')
        
        # DM the user
        try:
            dm_embed = discord.Embed(
                title=f'🔨 Banned from {ctx.guild.name}',
                color=discord.Color.red(),
                description=f'You have been banned by {ctx.author.name}.'
            )
            dm_embed.add_field(name='Reason', value=reason)
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass
        
        await member.ban(reason=f'Banned by {ctx.author}: {reason}', delete_message_days=delete_days)
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["ban"]} Member Banned',
            color=discord.Color.dark_red(),
            fields=[
                {'name': 'Member', 'value': f'{member} ({member.id})', 'inline': True},
                {'name': 'Moderator', 'value': ctx.author.mention, 'inline': True},
                {'name': 'Reason', 'value': reason, 'inline': False},
                {'name': 'Messages Deleted', 'value': f'Last {delete_days} days' if delete_days > 0 else 'None', 'inline': True}
            ],
            footer=f'Guild: {ctx.guild.name}'
        )
        
        await ctx.send(embed=embed)
        await self.log_mod_action(ctx.guild, embed)
    
    @commands.hybrid_command(name='unban', aliases=['ub'],
                            description='Unban a user from the server')
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int, *, reason: str = 'No reason provided'):
        """Unban a user by their ID"""
        try:
            user = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            return await ctx.send(f'{config.EMOJIS["error"]} User not found.')
        
        try:
            await ctx.guild.unban(user, reason=f'Unbanned by {ctx.author}: {reason}')
        except discord.NotFound:
            return await ctx.send(f'{config.EMOJIS["error"]} This user is not banned.')
        except discord.Forbidden:
            return await ctx.send(f'{config.EMOJIS["error"]} I don\'t have permission to unban members.')
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["success"]} User Unbanned',
            description=f'{user.mention} has been unbanned.',
            color=discord.Color.green(),
            fields=[
                {'name': 'User', 'value': f'{user} ({user.id})', 'inline': True},
                {'name': 'Moderator', 'value': ctx.author.mention, 'inline': True},
                {'name': 'Reason', 'value': reason, 'inline': False}
            ]
        )
        
        await ctx.send(embed=embed)
        await self.log_mod_action(ctx.guild, embed)
    
    @commands.hybrid_command(name='softban', aliases=['sb'],
                            description='Ban and immediately unban to clear messages')
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def softban(self, ctx, member: discord.Member, *, reason: str = 'No reason provided'):
        """Softban a member (ban and unban to clear messages)"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send(f'{config.EMOJIS["error"]} You cannot softban this member.')
        
        confirm = await Utils.confirm_action(
            ctx,
            f'Are you sure you want to softban {member.mention}?\nThis will clear all their messages from the last 7 days.\n\nReason: {reason}'
        )
        
        if not confirm:
            return await ctx.send(f'{config.EMOJIS["info"]} Softban cancelled.')
        
        await member.ban(reason=f'Softbanned by {ctx.author}: {reason}', delete_message_days=7)
        await member.unban(reason=f'Softban complete - {reason}')
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["purge"]} Member Softbanned',
            description=f'{member.mention} has been softbanned (messages cleared).',
            color=discord.Color.orange(),
            fields=[
                {'name': 'Member', 'value': f'{member}', 'inline': True},
                {'name': 'Moderator', 'value': ctx.author.mention, 'inline': True},
                {'name': 'Reason', 'value': reason, 'inline': False}
            ]
        )
        
        await ctx.send(embed=embed)
        await self.log_mod_action(ctx.guild, embed)
    
    @commands.hybrid_command(name='purge', aliases=['clear', 'prune'],
                            description='Purge messages from the channel')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.cooldown(1, 3, commands.BucketType.channel)
    async def purge(self, ctx, amount: int, member: discord.Member = None):
        """Purge messages from the channel"""
        if amount < 1 or amount > 1000:
            return await ctx.send(f'{config.EMOJIS["error"]} Amount must be between 1 and 1000.')
        
        await ctx.defer()  # For large purges
        
        if member:
            def check(msg):
                return msg.author == member
            
            deleted = await ctx.channel.purge(limit=amount, check=check)
        else:
            deleted = await ctx.channel.purge(limit=amount)
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["purge"]} Messages Purged',
            description=f'Successfully deleted {len(deleted)} messages.',
            color=discord.Color.blue(),
            fields=[
                {'name': 'Channel', 'value': ctx.channel.mention, 'inline': True},
                {'name': 'Moderator', 'value': ctx.author.mention, 'inline': True}
            ]
        )
        
        if member:
            embed.add_field(name='Filtered User', value=member.mention, inline=True)
        
        await ctx.send(embed=embed, delete_after=5)
        await self.log_mod_action(ctx.guild, embed)
    
    @commands.hybrid_command(name='slowmode', aliases=['sm'],
                            description='Set slowmode for the channel')
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int):
        """Set slowmode for the current channel"""
        if seconds < 0 or seconds > 21600:  # 6 hours max
            return await ctx.send(f'{config.EMOJIS["error"]} Slowmode must be between 0 and 21600 seconds (6 hours).')
        
        await ctx.channel.edit(slowmode_delay=seconds)
        
        if seconds == 0:
            await ctx.send(f'{config.EMOJIS["success"]} Slowmode has been disabled in {ctx.channel.mention}.')
        else:
            await ctx.send(f'{config.EMOJIS["success"]} Slowmode set to {seconds} seconds in {ctx.channel.mention}.')
    
    @commands.hybrid_command(name='lock', aliases=['lockdown'],
                            description='Lock the channel')
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        """Lock a channel from sending messages"""
        channel = channel or ctx.channel
        
        # Get the default role
        default_role = ctx.guild.default_role
        
        # Override permissions
        overwrite = channel.overwrites_for(default_role)
        overwrite.send_messages = False
        
        await channel.set_permissions(default_role, overwrite=overwrite)
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["warning"]} Channel Locked',
            description=f'{channel.mention} has been locked.',
            color=discord.Color.red(),
            fields=[{'name': 'Moderator', 'value': ctx.author.mention, 'inline': True}]
        )
        
        await ctx.send(embed=embed)
        await self.log_mod_action(ctx.guild, embed)
    
    @commands.hybrid_command(name='unlock',
                            description='Unlock the channel')
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """Unlock a previously locked channel"""
        channel = channel or ctx.channel
        
        default_role = ctx.guild.default_role
        overwrite = channel.overwrites_for(default_role)
        overwrite.send_messages = None  # Reset to default
        
        await channel.set_permissions(default_role, overwrite=overwrite)
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["success"]} Channel Unlocked',
            description=f'{channel.mention} has been unlocked.',
            color=discord.Color.green(),
            fields=[{'name': 'Moderator', 'value': ctx.author.mention, 'inline': True}]
        )
        
        await ctx.send(embed=embed)
        await self.log_mod_action(ctx.guild, embed)
    
    @commands.hybrid_command(name='infractions', aliases=['inf'],
                            description='View infractions for a member')
    @commands.has_permissions(manage_messages=True)
    async def infractions(self, ctx, member: discord.Member, infraction_type: str = None):
        """View all infractions for a member"""
        if infraction_type and infraction_type not in ['warn', 'mute', 'kick', 'ban', 'softban']:
            return await ctx.send(f'{config.EMOJIS["error"]} Invalid infraction type.')
        
        infractions = await Database.get_user_infractions(
            member.id, 
            ctx.guild.id, 
            infraction_type
        )
        
        if not infractions:
            return await ctx.send(f'{config.EMOJIS["info"]} No infractions found for {member.mention}.')
        
        embed = discord.Embed(
            title=f'📋 Infractions for {member}',
            color=discord.Color.purple(),
            timestamp=datetime.datetime.utcnow()
        )
        
        # Summarize
        types_count = {}
        for inf in infractions:
            inf_type = inf['type'].capitalize()
            types_count[inf_type] = types_count.get(inf_type, 0) + 1
        
        summary = '\n'.join([f'{t}: {c}' for t, c in types_count.items()])
        embed.add_field(name='Summary', value=summary, inline=False)
        
        # Recent infractions
        recent_list = []
        for inf in infractions[:10]:
            moderator = ctx.guild.get_member(inf['moderator_id'])
            mod_name = moderator.name if moderator else 'Unknown'
            emoji = {'warn': '⚠️', 'mute': '🔇', 'kick': '👢', 'ban': '🔨', 'softban': '🧹'}.get(inf['type'], '❓')
            recent_list.append(f'{emoji} **{inf["type"].capitalize()}** - {mod_name}\n📝 {inf["reason"][:100]}')
        
        embed.add_field(
            name='Recent Infractions',
            value='\n'.join(recent_list) if recent_list else 'None',
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
