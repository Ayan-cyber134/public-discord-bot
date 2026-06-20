import discord
import re
import json
import time
import asyncio
from typing import Dict, List, Set, Optional
from collections import defaultdict
from discord.ext import commands
from database import Database
from utils import Utils
from config import config

class SpamChecker:
    """Efficient spam tracking system"""
    
    def __init__(self):
        # Structure: {guild_id: {user_id: [(timestamp, message_content), ...]}}
        self.messages: Dict[int, Dict[int, List[tuple]]] = defaultdict(lambda: defaultdict(list))
        # Structure: {guild_id: {user_id: last_warning_time}}
        self.last_warning: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
    
    def add_message(self, guild_id: int, user_id: int, content: str) -> int:
        """Add a message and return count in interval window"""
        now = time.time()
        user_messages = self.messages[guild_id][user_id]
        user_messages.append((now, content))
        return len(user_messages)
    
    def clean_old_messages(self, guild_id: int, user_id: int, interval: float):
        """Remove messages older than the interval"""
        now = time.time()
        user_messages = self.messages[guild_id][user_id]
        self.messages[guild_id][user_id] = [
            (ts, content) for ts, content in user_messages 
            if now - ts < interval
        ]
    
    def get_spam_count(self, guild_id: int, user_id: int, interval: float) -> int:
        """Get spam count for a user in given interval"""
        self.clean_old_messages(guild_id, user_id, interval)
        return len(self.messages[guild_id][user_id])
    
    def get_duplicate_count(self, guild_id: int, user_id: int, interval: float) -> int:
        """Count duplicate messages"""
        self.clean_old_messages(guild_id, user_id, interval)
        messages = [content for _, content in self.messages[guild_id][user_id]]
        if not messages:
            return 0
        # Count most frequent message occurrences
        from collections import Counter
        return Counter(messages).most_common(1)[0][1] if messages else 0
    
    def can_warn(self, guild_id: int, user_id: int, cooldown: float = 30) -> bool:
        """Check if we can send another warning to this user"""
        now = time.time()
        if now - self.last_warning[guild_id][user_id] > cooldown:
            self.last_warning[guild_id][user_id] = now
            return True
        return False
    
    def clear_user(self, guild_id: int, user_id: int):
        """Clear all data for a user"""
        if guild_id in self.messages and user_id in self.messages[guild_id]:
            del self.messages[guild_id][user_id]
        if guild_id in self.last_warning and user_id in self.last_warning[guild_id]:
            del self.last_warning[guild_id][user_id]

class AutoMod(commands.Cog, name='AutoMod'):
    """🤖 Advanced auto-moderation system with real-time protection"""
    
    def __init__(self, bot):
        self.bot = bot
        self.spam_checker = SpamChecker()
        
        # Pre-compiled regex patterns
        self.url_pattern = re.compile(
            r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*|'
            r'discord\.gg/[^\s]+|'
            r'discord(?:app)?\.com/invite/[^\s]+'
        )
        self.mention_pattern = re.compile(r'<@!?(\d+)>')
        self.emoji_pattern = re.compile(r'<a?:[^:]+:\d+>')
        
        # Cached automod configs
        self.config_cache: Dict[int, Dict] = {}
        self.cache_expiry: Dict[int, float] = {}
    
    def cog_unload(self):
        self.spam_checker.messages.clear()
        self.config_cache.clear()
    
    async def get_config(self, guild_id: int) -> Dict:
        """Get automod config with caching"""
        now = time.time()
        
        # Return cached config if still valid (cache for 60 seconds)
        if guild_id in self.config_cache and now - self.cache_expiry.get(guild_id, 0) < 60:
            return self.config_cache[guild_id]
        
        config = await Database.get_automod_config(guild_id)
        self.config_cache[guild_id] = config
        self.cache_expiry[guild_id] = now
        return config
    
    def invalidate_cache(self, guild_id: int):
        """Invalidate cache for a guild"""
        self.config_cache.pop(guild_id, None)
        self.cache_expiry.pop(guild_id, None)
    
    async def punish_user(self, message: discord.Message, automod_config: Dict, 
                          violation_type: str, reason: str):
        """Apply punishment based on automod config"""
        action = automod_config.get(f'anti_{violation_type}_action', 'delete')
        
        # Always try to delete the message first
        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass
        
        if action == 'delete':
            # Just delete, no further action
            try:
                warning_msg = await message.channel.send(
                    f'{config.EMOJIS["warning"]} {message.author.mention}, {reason}',
                    delete_after=5
                )
            except discord.Forbidden:
                pass
        
        elif action == 'warn':
            await Database.add_warning(
                message.author.id,
                message.guild.id,
                self.bot.user.id,
                f'AutoMod: {reason}'
            )
            try:
                embed = Utils.create_embed(
                    title=f'{config.EMOJIS["warn"]} Auto-Mod Warning',
                    description=f'{message.author.mention}, {reason}',
                    color=discord.Color.orange()
                )
                await message.channel.send(embed=embed, delete_after=5)
            except discord.Forbidden:
                pass
        
        elif action == 'mute':
            moderation_cog = self.bot.get_cog('Moderation')
            if moderation_cog:
                mute_role = await moderation_cog.get_mute_role(message.guild)
                if mute_role:
                    try:
                        duration = automod_config.get('anti_spam_action_duration', 300)
                        await message.author.add_roles(mute_role, reason=f'AutoMod: {reason}')
                        await Database.add_mute(
                            message.author.id,
                            message.guild.id,
                            self.bot.user.id,
                            duration,
                            f'AutoMod: {reason}'
                        )
                        
                        # Schedule unmute
                        async def unmute_later():
                            await asyncio.sleep(duration)
                            try:
                                await message.author.remove_roles(
                                    mute_role, 
                                    reason='AutoMod mute expired'
                                )
                                await Database.remove_mute(
                                    message.author.id,
                                    message.guild.id
                                )
                            except discord.Forbidden:
                                pass
                        
                        self.bot.loop.create_task(unmute_later())
                        
                        embed = Utils.create_embed(
                            title=f'{config.EMOJIS["mute"]} Auto-Mod Mute',
                            description=f'{message.author.mention} has been muted for {Utils.format_duration(duration)}.',
                            color=discord.Color.red(),
                            fields=[
                                {'name': 'Reason', 'value': reason, 'inline': False}
                            ]
                        )
                        await message.channel.send(embed=embed, delete_after=10)
                    except discord.Forbidden:
                        pass
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Main auto-mod message handler"""
        # Ignore bots, DMs, and members with manage_messages permission
        if message.author.bot or not message.guild:
            return
        
        if message.author.guild_permissions.manage_messages:
            return
        
        # Get automod config
        am_config = await self.get_config(message.guild.id)
        
        # Run all checks concurrently
        tasks = []
        
        if am_config.get('anti_spam_enabled'):
            tasks.append(self.check_spam(message, am_config))
        
        if am_config.get('anti_link_enabled'):
            tasks.append(self.check_links(message, am_config))
        
        if am_config.get('anti_swear_enabled'):
            tasks.append(self.check_swear(message, am_config))
        
        if am_config.get('anti_mention_enabled'):
            tasks.append(self.check_mentions(message, am_config))
        
        if am_config.get('anti_invite_enabled'):
            tasks.append(self.check_invites(message, am_config))
        
        if am_config.get('anti_mass_emoji_enabled'):
            tasks.append(self.check_emojis(message, am_config))
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def check_spam(self, message: discord.Message, config: Dict):
        """Anti-spam check"""
        threshold = config.get('anti_spam_threshold', 5)
        interval = config.get('anti_spam_interval', 10)
        
        # Add message to tracker
        count = self.spam_checker.add_message(
            message.guild.id,
            message.author.id,
            message.content
        )
        
        # Get actual spam count within interval
        spam_count = self.spam_checker.get_spam_count(
            message.guild.id,
            message.author.id,
            interval
        )
        
        # Check for spam
        if spam_count > threshold:
            # Check for duplicate spam
            duplicate_count = self.spam_checker.get_duplicate_count(
                message.guild.id,
                message.author.id,
                interval
            )
            
            if duplicate_count > threshold // 2:
                reason = f"Spam detected: {spam_count} messages in {interval}s (including {duplicate_count} duplicates)"
            else:
                reason = f"Spam detected: {spam_count} messages in {interval}s"
            
            await self.punish_user(message, config, 'spam', reason)
            
            # Clear their message history to prevent immediate re-trigger
            self.spam_checker.clear_user(message.guild.id, message.author.id)
    
    async def check_links(self, message: discord.Message, config: Dict):
        """Anti-link check"""
        content = message.content
        
        # Check for URLs
        if self.url_pattern.search(content):
            # Check whitelist
            whitelist_channels = config.get('anti_link_whitelist_channels', [])
            whitelist_roles = config.get('anti_link_whitelist_roles', [])
            whitelist_links = config.get('anti_link_whitelist_links', [])
            
            # Check channel whitelist
            if message.channel.id in whitelist_channels:
                return
            
            # Check role whitelist
            author_role_ids = [role.id for role in message.author.roles]
            if any(role_id in whitelist_roles for role_id in author_role_ids):
                return
            
            # Check link whitelist
            if whitelist_links:
                for allowed_link in whitelist_links:
                    if allowed_link.lower() in content.lower():
                        return
            
            # If we get here, link is not whitelisted
            await self.punish_user(
                message,
                config,
                'link',
                'Links are not allowed in this server.'
            )
    
    async def check_swear(self, message: discord.Message, config: Dict):
        """Anti-swear check"""
        bad_words = config.get('anti_swear_words', [])
        if not bad_words:
            return
        
        content = message.content.lower()
        
        # Check for exact words and word boundaries
        for word in bad_words:
            pattern = re.compile(r'\b' + re.escape(word.lower()) + r'\b', re.IGNORECASE)
            if pattern.search(content):
                await self.punish_user(
                    message,
                    config,
                    'swear',
                    'Inappropriate language detected.'
                )
                return
    
    async def check_mentions(self, message: discord.Message, config: Dict):
        """Anti-mass mention check"""
        mention_limit = config.get('anti_mention_limit', 5)
        
        # Count mentions
        mentions = self.mention_pattern.findall(message.content)
        # Also count role mentions
        role_mentions = len(message.role_mentions)
        total_mentions = len(mentions) + role_mentions + len(message.mentions)
        
        if total_mentions > mention_limit:
            await self.punish_user(
                message,
                config,
                'mention',
                f'Mass mentions detected ({total_mentions} mentions).'
            )
    
    async def check_invites(self, message: discord.Message, config: Dict):
        """Anti-invite link check"""
        invite_pattern = re.compile(
            r'(?:discord\.gg|discord(?:app)?\.com/invite)/[a-zA-Z0-9]+'
        )
        
        if invite_pattern.search(message.content):
            # Check whitelist
            whitelist_channels = config.get('anti_invite_whitelist_channels', [])
            if message.channel.id in whitelist_channels:
                return
            
            await self.punish_user(
                message,
                config,
                'invite',
                'Discord invites are not allowed here.'
            )
    
    async def check_emojis(self, message: discord.Message, config: Dict):
        """Anti-mass emoji check"""
        emoji_limit = config.get('anti_mass_emoji_limit', 10)
        
        # Count custom emojis
        custom_emojis = self.emoji_pattern.findall(message.content)
        # Count unicode emojis (rough check)
        unicode_emojis = sum(1 for char in message.content if ord(char) > 0x1F600)
        
        total_emojis = len(custom_emojis) + unicode_emojis
        
        if total_emojis > emoji_limit:
            await self.punish_user(
                message,
                config,
                'mass_emoji',
                f'Too many emojis detected ({total_emojis} emojis).'
            )
    
    @commands.hybrid_group(name='automod', aliases=['am'],
                          description='Configure auto-moderation settings')
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx):
        """Auto-mod configuration commands"""
        if ctx.invoked_subcommand is None:
            await self.show_settings(ctx)
    
    async def show_settings(self, ctx):
        """Show current auto-mod settings"""
        am_config = await self.get_config(ctx.guild.id)
        
        # Create main settings embed
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["automod"]} Auto-Mod Settings',
            description='Current auto-moderation configuration for this server.',
            color=config.BOT_COLOR,
            fields=[
                {
                    'name': 'Anti-Spam',
                    'value': f'**Status:** {"✅ Enabled" if am_config.get("anti_spam_enabled") else "❌ Disabled"}\n'
                            f'**Threshold:** {am_config.get("anti_spam_threshold", 5)} msgs\n'
                            f'**Interval:** {am_config.get("anti_spam_interval", 10)}s\n'
                            f'**Action:** {am_config.get("anti_spam_action", "mute")}',
                    'inline': True
                },
                {
                    'name': 'Anti-Link',
                    'value': f'**Status:** {"✅ Enabled" if am_config.get("anti_link_enabled") else "❌ Disabled"}\n'
                            f'**Action:** {am_config.get("anti_link_action", "delete")}\n'
                            f'**Whitelist Roles:** {len(am_config.get("anti_link_whitelist_roles", []))}\n'
                            f'**Whitelist Channels:** {len(am_config.get("anti_link_whitelist_channels", []))}',
                    'inline': True
                },
                {
                    'name': 'Anti-Swear',
                    'value': f'**Status:** {"✅ Enabled" if am_config.get("anti_swear_enabled") else "❌ Disabled"}\n'
                            f'**Words:** {len(am_config.get("anti_swear_words", []))}\n'
                            f'**Action:** {am_config.get("anti_swear_action", "delete")}',
                    'inline': True
                },
                {
                    'name': 'Anti-Mention',
                    'value': f'**Status:** {"✅ Enabled" if am_config.get("anti_mention_enabled") else "❌ Disabled"}\n'
                            f'**Limit:** {am_config.get("anti_mention_limit", 5)}\n'
                            f'**Action:** {am_config.get("anti_mention_action", "warn")}',
                    'inline': True
                },
                {
                    'name': 'Anti-Invite',
                    'value': f'**Status:** {"✅ Enabled" if am_config.get("anti_invite_enabled") else "❌ Disabled"}\n'
                            f'**Whitelist Channels:** {len(am_config.get("anti_invite_whitelist_channels", []))}',
                    'inline': True
                },
                {
                    'name': 'Anti-Mass Emoji',
                    'value': f'**Status:** {"✅ Enabled" if am_config.get("anti_mass_emoji_enabled") else "❌ Disabled"}\n'
                            f'**Limit:** {am_config.get("anti_mass_emoji_limit", 10)}',
                    'inline': True
                }
            ],
            footer=f'Use {config.PREFIX}automod <setting> to configure'
        )
        
        await ctx.send(embed=embed)
    
    @automod.command(name='antispam', description='Configure anti-spam settings')
    async def antispam_set(self, ctx, enabled: bool = None, threshold: int = None, 
                          interval: int = None, action: str = None):
        """Configure anti-spam settings"""
        updates = {}
        
        if enabled is not None:
            updates['anti_spam_enabled'] = int(enabled)
        
        if threshold is not None:
            if threshold < 3 or threshold > 20:
                return await ctx.send(f'{config.EMOJIS["error"]} Threshold must be between 3 and 20.')
            updates['anti_spam_threshold'] = threshold
        
        if interval is not None:
            if interval < 5 or interval > 60:
                return await ctx.send(f'{config.EMOJIS["error"]} Interval must be between 5 and 60 seconds.')
            updates['anti_spam_interval'] = interval
        
        if action is not None:
            valid_actions = ['delete', 'warn', 'mute']
            if action.lower() not in valid_actions:
                return await ctx.send(f'{config.EMOJIS["error"]} Action must be one of: {", ".join(valid_actions)}')
            updates['anti_spam_action'] = action.lower()
        
        if not updates:
            return await ctx.send(f'{config.EMOJIS["error"]} No settings provided to update.')
        
        await Database.update_automod_config(ctx.guild.id, **updates)
        self.invalidate_cache(ctx.guild.id)
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["success"]} Anti-Spam Updated',
            description='Anti-spam settings have been updated.',
            color=discord.Color.green(),
            fields=[
                {'name': key.replace('anti_spam_', '').replace('_', ' ').title(), 
                 'value': str(value), 'inline': True}
                for key, value in updates.items()
            ]
        )
        await ctx.send(embed=embed)
    
    @automod.command(name='antilink', description='Configure anti-link settings')
    async def antilink_set(self, ctx, enabled: bool = None, action: str = None):
        """Configure anti-link settings"""
        updates = {}
        
        if enabled is not None:
            updates['anti_link_enabled'] = int(enabled)
        
        if action is not None:
            valid_actions = ['delete', 'warn', 'mute']
            if action.lower() not in valid_actions:
                return await ctx.send(f'{config.EMOJIS["error"]} Action must be one of: {", ".join(valid_actions)}')
            updates['anti_link_action'] = action.lower()
        
        if not updates:
            return await ctx.send(f'{config.EMOJIS["error"]} No settings provided to update.')
        
        await Database.update_automod_config(ctx.guild.id, **updates)
        self.invalidate_cache(ctx.guild.id)
        
        await ctx.send(f'{config.EMOJIS["success"]} Anti-link settings updated.')
    
    @automod.command(name='antiswear', description='Configure anti-swear settings')
    async def antiswear_set(self, ctx, enabled: bool = None, action: str = None):
        """Configure anti-swear settings"""
        updates = {}
        
        if enabled is not None:
            updates['anti_swear_enabled'] = int(enabled)
        
        if action is not None:
            valid_actions = ['delete', 'warn', 'mute']
            if action.lower() not in valid_actions:
                return await ctx.send(f'{config.EMOJIS["error"]} Action must be one of: {", ".join(valid_actions)}')
            updates['anti_swear_action'] = action.lower()
        
        if not updates:
            return await ctx.send(f'{config.EMOJIS["error"]} No settings provided to update.')
        
        await Database.update_automod_config(ctx.guild.id, **updates)
        self.invalidate_cache(ctx.guild.id)
        
        await ctx.send(f'{config.EMOJIS["success"]} Anti-swear settings updated.')
    
    @automod.command(name='swearwords', description='Manage banned words list')
    async def swearwords_manage(self, ctx, action: str = 'list', *, word: str = None):
        """Add, remove, or list banned words"""
        am_config = await self.get_config(ctx.guild.id)
        words = am_config.get('anti_swear_words', [])
        
        if action.lower() == 'list':
            if not words:
                return await ctx.send(f'{config.EMOJIS["info"]} No banned words configured.')
            
            # Paginate if many words
            word_chunks = [words[i:i+20] for i in range(0, len(words), 20)]
            for i, chunk in enumerate(word_chunks):
                embed = Utils.create_embed(
                    title=f'📝 Banned Words (Page {i+1}/{len(word_chunks)})',
                    description='\n'.join([f'{j+1}. `{w}`' for j, w in enumerate(chunk, i*20)]),
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
            return
        
        if not word:
            return await ctx.send(f'{config.EMOJIS["error"]} Please provide a word to {action}.')
        
        if action.lower() == 'add':
            if word.lower() in [w.lower() for w in words]:
                return await ctx.send(f'{config.EMOJIS["info"]} This word is already banned.')
            words.append(word.lower())
            await Database.update_automod_config(
                ctx.guild.id,
                anti_swear_words=json.dumps(words)
            )
            self.invalidate_cache(ctx.guild.id)
            await ctx.send(f'{config.EMOJIS["success"]} Added `{word}` to banned words.')
        
        elif action.lower() == 'remove':
            if word.lower() not in [w.lower() for w in words]:
                return await ctx.send(f'{config.EMOJIS["info"]} This word is not in the banned list.')
            words = [w for w in words if w.lower() != word.lower()]
            await Database.update_automod_config(
                ctx.guild.id,
                anti_swear_words=json.dumps(words)
            )
            self.invalidate_cache(ctx.guild.id)
            await ctx.send(f'{config.EMOJIS["success"]} Removed `{word}` from banned words.')
        
        else:
            await ctx.send(f'{config.EMOJIS["error"]} Invalid action. Use: list, add, remove')
    
    @automod.command(name='antimention', description='Configure anti-mention settings')
    async def antimention_set(self, ctx, enabled: bool = None, limit: int = None, action: str = None):
        """Configure anti-mass mention settings"""
        updates = {}
        
        if enabled is not None:
            updates['anti_mention_enabled'] = int(enabled)
        
        if limit is not None:
            if limit < 2 or limit > 50:
                return await ctx.send(f'{config.EMOJIS["error"]} Limit must be between 2 and 50.')
            updates['anti_mention_limit'] = limit
        
        if action is not None:
            valid_actions = ['delete', 'warn', 'mute']
            if action.lower() not in valid_actions:
                return await ctx.send(f'{config.EMOJIS["error"]} Action must be one of: {", ".join(valid_actions)}')
            updates['anti_mention_action'] = action.lower()
        
        if not updates:
            return await ctx.send(f'{config.EMOJIS["error"]} No settings provided to update.')
        
        await Database.update_automod_config(ctx.guild.id, **updates)
        self.invalidate_cache(ctx.guild.id)
        
        await ctx.send(f'{config.EMOJIS["success"]} Anti-mention settings updated.')
    
    @automod.command(name='linkwhitelist', description='Manage link whitelist')
    async def linkwhitelist_manage(self, ctx, target_type: str, action: str, target: str = None):
        """Add or remove channels/roles/links from whitelist"""
        if target_type not in ['channel', 'role', 'link']:
            return await ctx.send(f'{config.EMOJIS["error"]} Target type must be: channel, role, or link.')
        
        if action not in ['add', 'remove', 'list']:
            return await ctx.send(f'{config.EMOJIS["error"]} Action must be: add, remove, or list.')
        
        am_config = await self.get_config(ctx.guild.id)
        
        if target_type == 'channel':
            field = 'anti_link_whitelist_channels'
            whitelist = am_config.get(field, [])
            
            if action == 'list':
                channels = [ctx.guild.get_channel(cid) for cid in whitelist]
                channels = [c.mention if c else f'Deleted Channel ({cid})' for cid, c in zip(whitelist, channels)]
                if not channels:
                    return await ctx.send(f'{config.EMOJIS["info"]} No whitelisted channels.')
                embed = Utils.create_embed(
                    title='📋 Whitelisted Channels',
                    description='\n'.join(channels),
                    color=discord.Color.blue()
                )
                return await ctx.send(embed=embed)
            
            if not target:
                return await ctx.send(f'{config.EMOJIS["error"]} Please mention a channel.')
            
            channel = await commands.TextChannelConverter().convert(ctx, target)
            
            if action == 'add':
                if channel.id in whitelist:
                    return await ctx.send(f'{config.EMOJIS["info"]} Channel already whitelisted.')
                whitelist.append(channel.id)
            else:
                if channel.id not in whitelist:
                    return await ctx.send(f'{config.EMOJIS["info"]} Channel not in whitelist.')
                whitelist.remove(channel.id)
        
        elif target_type == 'role':
            field = 'anti_link_whitelist_roles'
            whitelist = am_config.get(field, [])
            
            if action == 'list':
                roles = [ctx.guild.get_role(rid) for rid in whitelist]
                roles = [r.mention if r else f'Deleted Role ({rid})' for rid, r in zip(whitelist, roles)]
                if not roles:
                    return await ctx.send(f'{config.EMOJIS["info"]} No whitelisted roles.')
                embed = Utils.create_embed(
                    title='📋 Whitelisted Roles',
                    description='\n'.join(roles),
                    color=discord.Color.blue()
                )
                return await ctx.send(embed=embed)
            
            if not target:
                return await ctx.send(f'{config.EMOJIS["error"]} Please mention a role.')
            
            role = await commands.RoleConverter().convert(ctx, target)
            
            if action == 'add':
                if role.id in whitelist:
                    return await ctx.send(f'{config.EMOJIS["info"]} Role already whitelisted.')
                whitelist.append(role.id)
            else:
                if role.id not in whitelist:
                    return await ctx.send(f'{config.EMOJIS["info"]} Role not in whitelist.')
                whitelist.remove(role.id)
        
        elif target_type == 'link':
            field = 'anti_link_whitelist_links'
            whitelist = am_config.get(field, [])
            
            if action == 'list':
                if not whitelist:
                    return await ctx.send(f'{config.EMOJIS["info"]} No whitelisted links.')
                embed = Utils.create_embed(
                    title='📋 Whitelisted Links',
                    description='\n'.join([f'`{link}`' for link in whitelist]),
                    color=discord.Color.blue()
                )
                return await ctx.send(embed=embed)
            
            if not target:
                return await ctx.send(f'{config.EMOJIS["error"]} Please provide a link domain.')
            
            domain = target.lower().replace('https://', '').replace('http://', '').split('/')[0]
            
            if action == 'add':
                if domain in whitelist:
                    return await ctx.send(f'{config.EMOJIS["info"]} Link already whitelisted.')
                whitelist.append(domain)
            else:
                if domain not in whitelist:
                    return await ctx.send(f'{config.EMOJIS["info"]} Link not in whitelist.')
                whitelist.remove(domain)
        
        await Database.update_automod_config(ctx.guild.id, **{field: json.dumps(whitelist)})
        self.invalidate_cache(ctx.guild.id)
        await ctx.send(f'{config.EMOJIS["success"]} {target_type.capitalize()} {action}ed to/from link whitelist.')
    
    @automod.command(name='reset', description='Reset all auto-mod settings to default')
    async def automod_reset(self, ctx):
        """Reset auto-mod configuration to defaults"""
        confirm = await Utils.confirm_action(
            ctx,
            'Are you sure you want to reset ALL auto-mod settings to default? This cannot be undone!'
        )
        
        if not confirm:
            return await ctx.send(f'{config.EMOJIS["info"]} Reset cancelled.')
        
        # Delete and recreate default config
        db = await Database.get_connection()
        await db.execute('DELETE FROM automod_config WHERE guild_id = ?', (ctx.guild.id,))
        await db.commit()
        await db.close()
        
        self.invalidate_cache(ctx.guild.id)
        
        # Recreate with defaults
        await self.get_config(ctx.guild.id)
        
        await ctx.send(f'{config.EMOJIS["success"]} Auto-mod settings have been reset to defaults.')

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
