import discord
import datetime
import pytz
import json
from typing import Optional, Union, List, Dict, Any
from discord.ext import commands
from config import config

class Utils:
    """Utility functions for the bot"""
    
    @staticmethod
    def create_embed(
        title: str = None,
        description: str = None,
        color: int = config.BOT_COLOR,
        timestamp: bool = True,
        author: discord.User = None,
        footer: str = None,
        fields: List[Dict[str, Any]] = None
    ) -> discord.Embed:
        """Create a professional embed with ease"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.datetime.now(pytz.UTC) if timestamp else None
        )
        
        if author:
            embed.set_author(name=str(author), icon_url=author.display_avatar.url)
        
        if footer:
            embed.set_footer(text=footer)
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get('name', '\u200b'),
                    value=field.get('value', '\u200b'),
                    inline=field.get('inline', True)
                )
        
        return embed
    
    @staticmethod
    def create_paginated_embeds(items: List[str], title: str, per_page: int = 10) -> List[discord.Embed]:
        """Create paginated embeds for long lists"""
        embeds = []
        for i in range(0, len(items), per_page):
            page_items = items[i:i + per_page]
            embed = discord.Embed(
                title=title,
                description='\n'.join(page_items),
                color=config.BOT_COLOR,
                timestamp=datetime.datetime.now(pytz.UTC)
            )
            embed.set_footer(text=f'Page {len(embeds) + 1}/{((len(items) - 1) // per_page) + 1}')
            embeds.append(embed)
        return embeds if embeds else [discord.Embed(title=title, description='No items found', color=config.BOT_COLOR)]
    
    @staticmethod
    async def paginate(ctx: commands.Context, embeds: List[discord.Embed], timeout: int = 60):
        """Paginate through multiple embeds"""
        if len(embeds) == 1:
            return await ctx.send(embed=embeds[0])
        
        current_page = 0
        message = await ctx.send(embed=embeds[current_page])
        
        
        await message.add_reaction('⬅️')
        await message.add_reaction('➡️')
        await message.add_reaction('❌')
        
        def check(reaction, user):
            return (
                user == ctx.author 
                and str(reaction.emoji) in ['⬅️', '➡️', '❌'] 
                and reaction.message.id == message.id
            )
        
        while True:
            try:
                reaction, user = await ctx.bot.wait_for('reaction_add', timeout=timeout, check=check)
                
                if str(reaction.emoji) == '➡️':
                    current_page = (current_page + 1) % len(embeds)
                    await message.edit(embed=embeds[current_page])
                    await message.remove_reaction(reaction, user)
                
                elif str(reaction.emoji) == '⬅️':
                    current_page = (current_page - 1) % len(embeds)
                    await message.edit(embed=embeds[current_page])
                    await message.remove_reaction(reaction, user)
                
                elif str(reaction.emoji) == '❌':
                    await message.delete()
                    break
                    
            except TimeoutError:
                await message.clear_reactions()
                break
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format seconds into human-readable duration"""
        if seconds <= 0:
            return "Permanent"
        
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    @staticmethod
    def parse_duration(duration_str: str) -> Optional[int]:
        """Parse duration string to seconds (e.g., '1h30m' -> 5400)"""
        import re
        
        pattern = r'(\d+)([dhms])'
        matches = re.findall(pattern, duration_str.lower())
        
        if not matches:
            return None
        
        total_seconds = 0
        multipliers = {'d': 86400, 'h': 3600, 'm': 60, 's': 1}
        
        for value, unit in matches:
            total_seconds += int(value) * multipliers[unit]
        
        return total_seconds
    
    @staticmethod
    def get_progress_bar(current: int, total: int, length: int = 10) -> str:
        """Create a visual progress bar"""
        filled = int(length * current // total)
        bar = '█' * filled + '░' * (length - filled)
        return f'[{bar}]'
    
    @staticmethod
    async def confirm_action(ctx: commands.Context, message: str, timeout: int = 30) -> bool:
        """Ask for user confirmation"""
        embed = Utils.create_embed(
            title='Confirmation Required',
            description=message,
            color=discord.Color.gold()
        )
        confirm_msg = await ctx.send(embed=embed)
        await confirm_msg.add_reaction('✅')
        await confirm_msg.add_reaction('❌')
        
        def check(reaction, user):
            return (
                user == ctx.author 
                and str(reaction.emoji) in ['✅', '❌'] 
                and reaction.message.id == confirm_msg.id
            )
        
        try:
            reaction, _ = await ctx.bot.wait_for('reaction_add', timeout=timeout, check=check)
            return str(reaction.emoji) == '✅'
        except:
            return False
        finally:
            await confirm_msg.delete()
