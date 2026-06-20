import discord
import datetime
import platform
import psutil
import asyncio
from typing import Optional
from discord.ext import commands
from utils import Utils
from config import config

class Utility(commands.Cog, name='Utility'):
    """🔧 Useful utility commands for server management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name='userinfo', aliases=['ui', 'whois'],
                            description='Get detailed information about a user')
    @commands.bot_has_permissions(embed_links=True)
    async def userinfo(self, ctx, member: discord.Member = None):
        """Display detailed information about a user"""
        member = member or ctx.author
        
        # Get user data
        roles = [role.mention for role in reversed(member.roles[1:])]  # Exclude @everyone, reverse for hierarchy
        roles_str = ' '.join(roles) if roles else 'No roles'
        
        # Calculate account and server join dates
        created_at = member.created_at
        joined_at = member.joined_at
        
        # Calculate permissions
        key_permissions = []
        if member.guild_permissions.administrator:
            key_permissions.append('Administrator')
        if member.guild_permissions.manage_guild:
            key_permissions.append('Manage Server')
        if member.guild_permissions.manage_messages:
            key_permissions.append('Manage Messages')
        if member.guild_permissions.kick_members:
            key_permissions.append('Kick Members')
        if member.guild_permissions.ban_members:
            key_permissions.append('Ban Members')
        if member.guild_permissions.manage_roles:
            key_permissions.append('Manage Roles')
        if member.guild_permissions.manage_channels:
            key_permissions.append('Manage Channels')
        
        # Create embed
        embed = discord.Embed(
            title=f'👤 User Information - {member}',
            color=member.color if member.color != discord.Color.default() else config.BOT_COLOR,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        
        # Basic Info
        embed.add_field(
            name='📋 Basic Information',
            value=f'**Username:** {member.name}\n'
                  f'**Display Name:** {member.display_name}\n'
                  f'**ID:** `{member.id}`\n'
                  f'**Bot:** {"Yes 🤖" if member.bot else "No 👤"}\n'
                  f'**System User:** {member.system}\n'
                  f'**Top Role:** {member.top_role.mention if member.top_role != ctx.guild.default_role else "None"}',
            inline=False
        )
        
        # Dates
        embed.add_field(
            name='📅 Dates',
            value=f'**Created:** <t:{int(created_at.timestamp())}:F> (<t:{int(created_at.timestamp())}:R>)\n'
                  f'**Joined:** <t:{int(joined_at.timestamp())}:F> (<t:{int(joined_at.timestamp())}:R>)' if joined_at else '**Joined:** Unknown',
            inline=False
        )
        
        # Server-specific info
        if member != ctx.author:
            # Get their warning count
            from database import Database
            warnings = await Database.get_warnings(member.id, ctx.guild.id, active_only=True)
            
            embed.add_field(
                name=f'🛡️ Server Moderation',
                value=f'**Warnings:** {len(warnings)}\n'
                      f'**Join Position:** #{sorted(ctx.guild.members, key=lambda m: m.joined_at).index(member) + 1 if joined_at else "Unknown"}\n'
                      f'**Boosting Since:** <t:{int(member.premium_since.timestamp())}:R>' if member.premium_since else '**Boosting:** Not boosting',
                inline=False
            )
        
        # Roles
        embed.add_field(
            name=f'🎨 Roles [{len(member.roles) - 1}]',
            value=roles_str[:1024] if roles_str else 'No roles',
            inline=False
        )
        
        # Key Permissions
        if key_permissions:
            embed.add_field(
                name='🔑 Key Permissions',
                value='\n'.join([f'• {perm}' for perm in key_permissions]),
                inline=False
            )
        
        # Activity
        if member.activities:
            activities = []
            for activity in member.activities:
                if isinstance(activity, discord.Game):
                    activities.append(f'🎮 Playing **{activity.name}**')
                elif isinstance(activity, discord.Streaming):
                    activities.append(f'📺 Streaming **{activity.name}**')
                elif isinstance(activity, discord.Spotify):
                    activities.append(f'🎵 Listening to **{activity.title}** by {activity.artist}')
                elif isinstance(activity, discord.CustomActivity):
                    activities.append(f'💬 {activity.name}')
                else:
                    activities.append(f'🔍 {activity.type.name}: {activity.name}')
            
            if activities:
                embed.add_field(
                    name='📱 Activity',
                    value='\n'.join(activities),
                    inline=False
                )
        
        # Status
        status_emoji = {
            discord.Status.online: '🟢',
            discord.Status.idle: '🟡',
            discord.Status.dnd: '🔴',
            discord.Status.offline: '⚫'
        }
        status = status_emoji.get(member.status, '❓')
        
        embed.add_field(
            name='📊 Status',
            value=f'{status} {str(member.status).title()}\n'
                  f'📱 {"Mobile" if member.is_on_mobile() else "Desktop/Web"}',
            inline=True
        )
        
        embed.set_footer(text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='serverinfo', aliases=['si', 'guildinfo'],
                            description='Get detailed information about the server')
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def serverinfo(self, ctx):
        """Display detailed information about the server"""
        guild = ctx.guild
        
        # Get guild info
        total_members = guild.member_count
        online_members = sum(1 for m in guild.members if m.status != discord.Status.offline)
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles = len(guild.roles)
        emojis = len(guild.emojis)
        stickers = len(guild.stickers)
        boosts = guild.premium_subscription_count
        
        # Create embed
        embed = discord.Embed(
            title=f'📊 Server Information - {guild.name}',
            color=config.BOT_COLOR,
            timestamp=datetime.datetime.utcnow()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Basic Info
        embed.add_field(
            name='📋 Basic Information',
            value=f'**Name:** {guild.name}\n'
                  f'**ID:** `{guild.id}`\n'
                  f'**Owner:** {guild.owner.mention if guild.owner else "Unknown"}\n'
                  f'**Created:** <t:{int(guild.created_at.timestamp())}:F>\n'
                  f'**Created:** <t:{int(guild.created_at.timestamp())}:R>\n'
                  f'**Region:** {str(guild.preferred_locale).title()}\n'
                  f'**Verification Level:** {str(guild.verification_level).title()}',
            inline=False
        )
        
        # Member Info
        embed.add_field(
            name='👥 Members',
            value=f'**Total:** {total_members}\n'
                  f'**Online:** {online_members}\n'
                  f'**Offline:** {total_members - online_members}\n'
                  f'**Humans:** {sum(1 for m in guild.members if not m.bot)}\n'
                  f'**Bots:** {sum(1 for m in guild.members if m.bot)}\n'
                  f'**Boosters:** {guild.premium_subscription_count}',
            inline=True
        )
        
        # Channel Info
        embed.add_field(
            name='💬 Channels',
            value=f'**Categories:** {categories}\n'
                  f'**Text:** {text_channels}\n'
                  f'**Voice:** {voice_channels}\n'
                  f'**Total:** {text_channels + voice_channels}\n'
                  f'**AFK Channel:** {guild.afk_channel.mention if guild.afk_channel else "None"}\n'
                  f'**System Channel:** {guild.system_channel.mention if guild.system_channel else "None"}',
            inline=True
        )
        
        # Other Info
        embed.add_field(
            name='🎨 Other',
            value=f'**Roles:** {roles}\n'
                  f'**Emojis:** {emojis}/{guild.emoji_limit}\n'
                  f'**Stickers:** {stickers}/{guild.sticker_limit}\n'
                  f'**Boost Level:** {guild.premium_tier}\n'
                  f'**Max Upload:** {guild.filesize_limit // 1048576}MB\n'
                  f'**Bitrate:** {guild.bitrate_limit // 1000}kbps',
            inline=True
        )
        
        # Features
        if guild.features:
            features = '\n'.join([f'• {feature.replace("_", " ").title()}' for feature in guild.features[:10]])
            embed.add_field(
                name=f'✨ Features ({len(guild.features)})',
                value=features,
                inline=False
            )
        
        # Server Banner
        if guild.banner:
            embed.set_image(url=guild.banner.url)
        
        embed.set_footer(text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='avatar', aliases=['av', 'pfp'],
                            description='Get the avatar of a user')
    @commands.bot_has_permissions(embed_links=True)
    async def avatar(self, ctx, member: discord.Member = None):
        """Display a user's avatar in different formats"""
        member = member or ctx.author
        
        # Get avatars
        global_avatar = member.avatar.url if member.avatar else member.default_avatar.url
        server_avatar = member.display_avatar.url
        
        embed = discord.Embed(
            title=f'🖼️ Avatar - {member}',
            color=member.color if member.color != discord.Color.default() else config.BOT_COLOR,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_image(url=server_avatar)
        
        # Add links for different formats
        formats = []
        if member.avatar:
            formats.append(f'[PNG]({member.avatar.with_format("png").url})')
            formats.append(f'[JPG]({member.avatar.with_format("jpg").url})')
            formats.append(f'[WebP]({member.avatar.with_format("webp").url})')
            if member.avatar.is_animated():
                formats.append(f'[GIF]({member.avatar.with_format("gif").url})')
        else:
            formats.append(f'[Default]({member.default_avatar.url})')
        
        embed.add_field(
            name='🔗 Formats',
            value=' • '.join(formats),
            inline=False
        )
        
        # Add server-specific avatar if different
        if member.guild_avatar and member.guild_avatar != member.avatar:
            embed.add_field(
                name='🔄 Server Avatar',
                value=f'This user has a custom server avatar.\n'
                      f'[View Server Avatar]({member.display_avatar.url})',
                inline=False
            )
        
        embed.set_footer(text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='ping', description='Check the bot\'s latency')
    async def ping(self, ctx):
        """Check bot's response time"""
        # Get websocket latency
        ws_latency = round(self.bot.latency * 1000, 2)
        
        # Measure API latency
        start = datetime.datetime.utcnow()
        msg = await ctx.send('🏓 Pong!')
        end = datetime.datetime.utcnow()
        api_latency = round((end - start).total_seconds() * 1000, 2)
        
        # Database latency
        try:
            from database import Database
            db = await Database.get_connection()
            start = datetime.datetime.utcnow()
            await db.execute('SELECT 1')
            end = datetime.datetime.utcnow()
            db_latency = round((end - start).total_seconds() * 1000, 2)
            await db.close()
        except:
            db_latency = 'N/A'
        
        # Determine status
        if ws_latency < 100:
            status = '🟢 Excellent'
            color = discord.Color.green()
        elif ws_latency < 200:
            status = '🟡 Good'
            color = discord.Color.gold()
        else:
            status = '🔴 Poor'
            color = discord.Color.red()
        
        embed = discord.Embed(
            title='🏓 Pong!',
            description=f'**Status:** {status}',
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name='WebSocket Latency', value=f'`{ws_latency}ms`', inline=True)
        embed.add_field(name='API Latency', value=f'`{api_latency}ms`', inline=True)
        embed.add_field(name='Database Latency', value=f'`{db_latency}ms`', inline=True)
        
        await msg.edit(content=None, embed=embed)
    
    @commands.hybrid_command(name='botinfo', aliases=['bi', 'stats'],
                            description='Get information about the bot')
    @commands.bot_has_permissions(embed_links=True)
    async def botinfo(self, ctx):
        """Display bot statistics and information"""
        # Calculate uptime
        if self.bot.start_time:
            uptime = datetime.datetime.utcnow() - self.bot.start_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f'{days}d {hours}h {minutes}m {seconds}s'
        else:
            uptime_str = 'Unknown'
        
        # System info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_used = memory.used / (1024 ** 3)  # GB
        memory_total = memory.total / (1024 ** 3)  # GB
        
        # Count commands
        total_commands = len(self.bot.commands)
        slash_commands = len([cmd for cmd in self.bot.commands if hasattr(cmd, 'slash_command')])
        
        embed = discord.Embed(
            title=f'🤖 {config.BOT_NAME} Statistics',
            color=config.BOT_COLOR,
            timestamp=datetime.datetime.utcnow()
        )
        
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        # Bot Info
        embed.add_field(
            name='📋 Bot Information',
            value=f'**Name:** {self.bot.user.name}\n'
                  f'**ID:** `{self.bot.user.id}`\n'
                  f'**Version:** {config.BOT_VERSION}\n'
                  f'**Library:** discord.py {discord.__version__}\n'
                  f'**Python:** {platform.python_version()}\n'
                  f'**Uptime:** {uptime_str}',
            inline=False
        )
        
        # Statistics
        embed.add_field(
            name='📊 Statistics',
            value=f'**Servers:** {len(self.bot.guilds)}\n'
                  f'**Users:** {len(self.bot.users)}\n'
                  f'**Channels:** {sum(1 for _ in self.bot.get_all_channels())}\n'
                  f'**Commands:** {total_commands}\n'
                  f'**Cogs:** {len(self.bot.cogs)}\n'
                  f'**Emojis:** {len(self.bot.emojis)}',
            inline=True
        )
        
        # System
        embed.add_field(
            name='💻 System',
            value=f'**CPU Usage:** {cpu_percent}%\n'
                  f'**Memory:** {memory_used:.1f}GB / {memory_total:.1f}GB\n'
                  f'**OS:** {platform.system()} {platform.release()}\n'
                  f'**Processor:** {platform.processor()[:50]}',
            inline=True
        )
        
        # Links
        embed.add_field(
            name='🔗 Links',
            value=f'[Invite Me]({config.BOT_INVITE.format(self.bot.user.id)})\n'
                  f'[Support Server](https://discord.gg/example)\n',
            inline=True
        )
        
        embed.set_footer(text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='invite', description='Get the bot invite link')
    async def invite(self, ctx):
        """Get the invite link for the bot"""
        embed = Utils.create_embed(
            title='🔗 Bot Invite Links',
            description='Invite me to your server!',
            color=config.BOT_COLOR,
            fields=[
                {
                    'name': 'Administrator',
                    'value': f'[Invite with Admin]({config.BOT_INVITE.format(self.bot.user.id)})',
                    'inline': True
                },
                {
                    'name': 'Recommended Permissions',
                    'value': f'[Invite with Required Perms]({config.BOT_INVITE.format(self.bot.user.id).replace("8", "268561430")})',
                    'inline': True
                }
            ]
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='roleinfo', description='Get information about a role')
    @commands.bot_has_permissions(embed_links=True)
    async def roleinfo(self, ctx, *, role: discord.Role):
        """Display detailed information about a role"""
        # Get role members count
        member_count = len(role.members)
        
        # Get permissions
        permissions = [perm.replace('_', ' ').title() for perm, value in role.permissions if value]
        
        embed = discord.Embed(
            title=f'🎨 Role Information - {role.name}',
            color=role.color if role.color != discord.Color.default() else config.BOT_COLOR,
            timestamp=datetime.datetime.utcnow()
        )
        
        # Basic Info
        embed.add_field(
            name='📋 Basic Information',
            value=f'**Name:** {role.name}\n'
                  f'**ID:** `{role.id}`\n'
                  f'**Color:** {role.color}\n'
                  f'**Created:** <t:{int(role.created_at.timestamp())}:R>\n'
                  f'**Position:** {role.position}\n'
                  f'**Members:** {member_count}\n'
                  f'**Hoisted:** {"Yes" if role.hoist else "No"}\n'
                  f'**Mentionable:** {"Yes" if role.mentionable else "No"}\n'
                  f'**Managed:** {"Yes" if role.managed else "No"}',
            inline=False
        )
        
        # Permissions
        if permissions:
            embed.add_field(
                name=f'🔑 Permissions ({len(permissions)})',
                value='\n'.join([f'{"✅" if value else "❌"} {perm}' for perm, value in list(role.permissions)[:25]]),
                inline=False
            )
        
        embed.set_footer(text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='channelinfo', aliases=['ci'],
                            description='Get information about a channel')
    @commands.bot_has_permissions(embed_links=True)
    async def channelinfo(self, ctx, channel: discord.TextChannel = None):
        """Display information about a channel"""
        channel = channel or ctx.channel
        
        embed = discord.Embed(
            title=f'💬 Channel Information - #{channel.name}',
            color=config.BOT_COLOR,
            timestamp=datetime.datetime.utcnow()
        )
        
        # Basic Info
        embed.add_field(
            name='📋 Basic Information',
            value=f'**Name:** {channel.name}\n'
                  f'**ID:** `{channel.id}`\n'
                  f'**Type:** {str(channel.type).title()}\n'
                  f'**Category:** {channel.category.name if channel.category else "None"}\n'
                  f'**Created:** <t:{int(channel.created_at.timestamp())}:R>\n'
                  f'**Position:** {channel.position}\n'
                  f'**NSFW:** {"Yes" if channel.is_nsfw() else "No"}',
            inline=False
        )
        
        # Channel-specific info
        if isinstance(channel, discord.TextChannel):
            embed.add_field(
                name='📝 Text Channel Info',
                value=f'**Topic:** {channel.topic or "None"}\n'
                      f'**Slowmode:** {channel.slowmode_delay}s\n'
                      f'**Default Auto-Archive:** {channel.default_auto_archive_duration} min\n'
                      f'**News:** {"Yes" if channel.is_news() else "No"}',
                inline=False
            )
        
        if isinstance(channel, discord.VoiceChannel):
            embed.add_field(
                name='🔊 Voice Channel Info',
                value=f'**Bitrate:** {channel.bitrate // 1000}kbps\n'
                      f'**User Limit:** {channel.user_limit or "Unlimited"}\n'
                      f'**Region:** {channel.rtc_region or "Auto"}',
                inline=False
            )
        
        embed.set_footer(text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))
