import discord
import datetime
import asyncio
from typing import Optional
from discord.ext import commands
from database import Database
from utils import Utils
from config import config

class ModLog(commands.Cog, name='ModLog'):
    """📋 Moderation logging and audit system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.message_cache = {}
    
    async def get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Get the configured log channel"""
        settings = await Database.get_guild_settings(guild.id)
        channel_id = settings.get('log_channel_id')
        if channel_id:
            return guild.get_channel(channel_id)
        return None
    
    async def log_action(self, guild: discord.Guild, embed: discord.Embed):
        """Log a moderation action"""
        channel = await self.get_log_channel(guild)
        if channel:
            try:
                await channel.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                pass
    
    @commands.hybrid_group(name='log', description='Configure moderation logging')
    @commands.has_permissions(administrator=True)
    async def log(self, ctx):
        """Moderation log configuration"""
        if ctx.invoked_subcommand is None:
            settings = await Database.get_guild_settings(ctx.guild.id)
            channel_id = settings.get('log_channel_id')
            channel = ctx.guild.get_channel(channel_id) if channel_id else None
            
            embed = Utils.create_embed(
                title=f'{config.EMOJIS["settings"]} Log Settings',
                color=config.BOT_COLOR,
                fields=[
                    {
                        'name': 'Log Channel',
                        'value': channel.mention if channel else 'Not set',
                        'inline': True
                    }
                ],
                footer=f'Use {config.PREFIX}log channel #channel to configure'
            )
            await ctx.send(embed=embed)
    
    @log.command(name='channel', description='Set the moderation log channel')
    async def set_log_channel(self, ctx, channel: discord.TextChannel):
        """Set the channel for moderation logs"""
        await Database.update_guild_settings(ctx.guild.id, log_channel_id=channel.id)
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["success"]} Log Channel Set',
            description=f'Moderation logs will now be sent to {channel.mention}',
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @log.command(name='test', description='Test the logging system')
    async def test_log(self, ctx):
        """Send a test log message"""
        channel = await self.get_log_channel(ctx.guild)
        if not channel:
            return await ctx.send(f'{config.EMOJIS["error"]} No log channel set. Use `{config.PREFIX}log channel #channel`')
        
        test_embed = Utils.create_embed(
            title=f'{config.EMOJIS["info"]} Log System Test',
            description='This is a test of the moderation logging system.',
            color=discord.Color.blue(),
            fields=[
                {'name': 'Tested By', 'value': ctx.author.mention, 'inline': True},
                {'name': 'Timestamp', 'value': discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'), 'inline': True}
            ]
        )
        
        try:
            await channel.send(embed=test_embed)
            await ctx.send(f'{config.EMOJIS["success"]} Test log sent to {channel.mention}')
        except discord.Forbidden:
            await ctx.send(f'{config.EMOJIS["error"]} Cannot send messages to {channel.mention}')
    
    # Event listeners for automatic logging
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Log deleted messages"""
        if message.author.bot or not message.guild:
            return
        
        # Ignore empty messages and very long messages
        if not message.content and not message.attachments:
            return
        
        channel = await self.get_log_channel(message.guild)
        if not channel or channel == message.channel:
            return
        
        embed = discord.Embed(
            title='🗑️ Message Deleted',
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        embed.add_field(name='Channel', value=message.channel.mention, inline=True)
        embed.add_field(name='Author', value=message.author.mention, inline=True)
        
        if message.content:
            content = message.content[:1024] if len(message.content) > 1024 else message.content
            embed.add_field(name='Content', value=content, inline=False)
        
        if message.attachments:
            attachments = '\n'.join([a.filename for a in message.attachments])
            embed.add_field(name='Attachments', value=attachments, inline=False)
        
        embed.set_footer(text=f'Message ID: {message.id}')
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Log edited messages"""
        if before.author.bot or not before.guild:
            return
        
        if before.content == after.content:
            return  # Only content changes matter (ignore embed updates)
        
        channel = await self.get_log_channel(before.guild)
        if not channel or channel == before.channel:
            return
        
        embed = discord.Embed(
            title='✏️ Message Edited',
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
        embed.add_field(name='Channel', value=before.channel.mention, inline=True)
        embed.add_field(name='Author', value=before.author.mention, inline=True)
        embed.add_field(name='Jump To', value=f'[Click Here]({after.jump_url})', inline=True)
        
        # Before content
        before_content = before.content[:512] if len(before.content) > 512 else before.content or '*Empty*'
        embed.add_field(name='Before', value=before_content, inline=False)
        
        # After content
        after_content = after.content[:512] if len(after.content) > 512 else after.content or '*Empty*'
        embed.add_field(name='After', value=after_content, inline=False)
        
        embed.set_footer(text=f'Message ID: {after.id}')
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Log member joins"""
        channel = await self.get_log_channel(member.guild)
        if not channel:
            return
        
        account_age = (discord.utils.utcnow() - member.created_at).days
        
        embed = discord.Embed(
            title='📥 Member Joined',
            description=f'{member.mention} has joined the server.',
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name='Account Created', value=f'<t:{int(member.created_at.timestamp())}:R>', inline=True)
        embed.add_field(name='Account Age', value=f'{account_age} days', inline=True)
        embed.add_field(name='Member Count', value=str(member.guild.member_count), inline=True)
        embed.set_footer(text=f'User ID: {member.id}')
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Log member leaves"""
        channel = await self.get_log_channel(member.guild)
        if not channel:
            return
        
        # Get their roles
        roles = [role.mention for role in member.roles[1:]]  # Exclude @everyone
        roles_str = ', '.join(roles) if roles else 'No roles'
        
        embed = discord.Embed(
            title='📤 Member Left',
            description=f'{member.mention} has left the server.',
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name='Roles', value=roles_str[:1024], inline=False)
        embed.add_field(name='Joined', value=f'<t:{int(member.joined_at.timestamp())}:R>' if member.joined_at else 'Unknown', inline=True)
        embed.add_field(name='Member Count', value=str(member.guild.member_count), inline=True)
        embed.set_footer(text=f'User ID: {member.id}')
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Log member updates (nickname changes, role changes)"""
        channel = await self.get_log_channel(before.guild)
        if not channel:
            return
        
        # Nickname change
        if before.nick != after.nick:
            embed = discord.Embed(
                title='📝 Nickname Changed',
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            embed.add_field(name='Before', value=before.nick or '*None*', inline=True)
            embed.add_field(name='After', value=after.nick or '*None*', inline=True)
            embed.set_footer(text=f'User ID: {after.id}')
            
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass
        
        # Role changes
        if before.roles != after.roles:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            if added_roles or removed_roles:
                embed = discord.Embed(
                    title='🔧 Roles Updated',
                    color=discord.Color.purple(),
                    timestamp=discord.utils.utcnow()
                )
                embed.set_author(name=str(after), icon_url=after.display_avatar.url)
                
                if added_roles:
                    embed.add_field(
                        name='✅ Added',
                        value=' '.join([role.mention for role in added_roles]),
                        inline=False
                    )
                
                if removed_roles:
                    embed.add_field(
                        name='❌ Removed',
                        value=' '.join([role.mention for role in removed_roles]),
                        inline=False
                    )
                
                embed.set_footer(text=f'User ID: {after.id}')
                
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Log member bans"""
        channel = await self.get_log_channel(guild)
        if not channel:
            return
        
        embed = discord.Embed(
            title='🔨 Member Banned',
            description=f'{user.mention} has been banned.',
            color=discord.Color.dark_red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        embed.add_field(name='User', value=f'{user} ({user.id})', inline=True)
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Log member unbans"""
        channel = await self.get_log_channel(guild)
        if not channel:
            return
        
        embed = discord.Embed(
            title='✅ Member Unbanned',
            description=f'{user.mention} has been unbanned.',
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        embed.add_field(name='User', value=f'{user} ({user.id})', inline=True)
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Log channel creation"""
        log_channel = await self.get_log_channel(channel.guild)
        if not log_channel or log_channel == channel:
            return
        
        embed = discord.Embed(
            title='📝 Channel Created',
            description=f'{channel.mention} was created.',
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name='Name', value=channel.name, inline=True)
        embed.add_field(name='Type', value=str(channel.type).title(), inline=True)
        embed.set_footer(text=f'Channel ID: {channel.id}')
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Log channel deletion"""
        log_channel = await self.get_log_channel(channel.guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title='🗑️ Channel Deleted',
            description=f'Channel #{channel.name} was deleted.',
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name='Name', value=channel.name, inline=True)
        embed.add_field(name='Type', value=str(channel.type).title(), inline=True)
        embed.set_footer(text=f'Channel ID: {channel.id}')
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Log role creation"""
        channel = await self.get_log_channel(role.guild)
        if not channel:
            return
        
        permissions = [perm for perm, value in role.permissions if value]
        
        embed = discord.Embed(
            title='📝 Role Created',
            description=f'Role {role.mention} was created.',
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name='Name', value=role.name, inline=True)
        embed.add_field(name='Color', value=str(role.color), inline=True)
        embed.add_field(name='Hoisted', value=str(role.hoist), inline=True)
        embed.add_field(name='Mentionable', value=str(role.mentionable), inline=True)
        if permissions:
            embed.add_field(
                name=f'Permissions ({len(permissions)})',
                value='\n'.join(permissions[:10]) + ('...' if len(permissions) > 10 else ''),
                inline=False
            )
        embed.set_footer(text=f'Role ID: {role.id}')
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Log role deletion"""
        channel = await self.get_log_channel(role.guild)
        if not channel:
            return
        
        embed = discord.Embed(
            title='🗑️ Role Deleted',
            description=f'Role {role.name} was deleted.',
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name='Name', value=role.name, inline=True)
        embed.add_field(name='Color', value=str(role.color), inline=True)
        embed.set_footer(text=f'Role ID: {role.id}')
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

async def setup(bot):
    await bot.add_cog(ModLog(bot))
