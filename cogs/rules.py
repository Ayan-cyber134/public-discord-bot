import discord
import datetime
from typing import Optional
from discord.ext import commands
from database import Database
from utils import Utils
from config import config

class Rules(commands.Cog, name='Rules'):
    """📜 Complete server rules management system"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_group(name='rules', fallback='list',
                          description='View and manage server rules')
    async def rules(self, ctx):
        """View server rules"""
        if ctx.invoked_subcommand is None:
            await self.list_rules(ctx)
    
    async def list_rules(self, ctx, page: int = 1):
        """List all server rules"""
        rules = await Database.get_rules(ctx.guild.id)
        
        if not rules:
            embed = Utils.create_embed(
                title=f'{config.EMOJIS["rules"]} Server Rules',
                description='No rules have been set for this server yet.',
                color=discord.Color.blue(),
                footer=f'Use {config.PREFIX}rules add <rule> to add a rule'
            )
            return await ctx.send(embed=embed)
        
        # Group rules by category
        categories = {}
        for rule in rules:
            cat = rule.get('category', 'General')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(rule)
        
        # Create embed
        embed = discord.Embed(
            title=f'{config.EMOJIS["rules"]} {ctx.guild.name} Rules',
            description=f'Please follow these rules to maintain a positive community.\n\n'
                       f'*Total rules: {len(rules)}*',
            color=config.BOT_COLOR,
            timestamp=datetime.datetime.utcnow()
        )
        
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        
        for category, category_rules in categories.items():
            rules_text = []
            for rule in category_rules:
                rules_text.append(f'**{rule["rule_number"]}.** {rule["rule_text"]}')
            
            # Split if too long
            text = '\n'.join(rules_text)
            if len(text) > 1024:
                text = text[:1020] + '...'
            
            embed.add_field(
                name=f'📌 {category}',
                value=text,
                inline=False
            )
        
        embed.set_footer(
            text=f'Use {config.PREFIX}rules add/remove to manage rules',
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )
        
        await ctx.send(embed=embed)
    
    @rules.command(name='add', description='Add a new rule')
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def add_rule(self, ctx, category: str = 'General', *, rule_text: str):
        """Add a new rule to the server"""
        # Get current rules
        rules = await Database.get_rules(ctx.guild.id)
        
        if len(rules) >= config.MAX_RULES_PER_GUILD:
            return await ctx.send(
                f'{config.EMOJIS["error"]} Maximum of {config.MAX_RULES_PER_GUILD} rules reached.'
            )
        
        if len(rule_text) > config.RULE_MAX_LENGTH:
            return await ctx.send(
                f'{config.EMOJIS["error"]} Rule text must be under {config.RULE_MAX_LENGTH} characters.'
            )
        
        # Get next rule number
        next_number = max([r['rule_number'] for r in rules] + [0]) + 1
        
        # Add rule
        await Database.add_rule(
            ctx.guild.id,
            next_number,
            rule_text,
            category,
            ctx.author.id
        )
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["success"]} Rule Added',
            description=f'**Rule #{next_number}** has been added.',
            color=discord.Color.green(),
            fields=[
                {'name': 'Category', 'value': category, 'inline': True},
                {'name': 'Rule', 'value': rule_text, 'inline': False}
            ],
            footer=f'Added by {ctx.author}'
        )
        
        await ctx.send(embed=embed)
    
    @rules.command(name='remove', aliases=['delete', 'del'],
                  description='Remove a rule')
    @commands.has_permissions(administrator=True)
    async def remove_rule(self, ctx, rule_number: int):
        """Remove a rule by its number"""
        rules = await Database.get_rules(ctx.guild.id)
        
        if not any(r['rule_number'] == rule_number for r in rules):
            return await ctx.send(
                f'{config.EMOJIS["error"]} Rule #{rule_number} not found.'
            )
        
        # Get the rule text before removing
        rule_text = next(r['rule_text'] for r in rules if r['rule_number'] == rule_number)
        
        confirm = await Utils.confirm_action(
            ctx,
            f'Are you sure you want to remove Rule #{rule_number}?\n\n> {rule_text}'
        )
        
        if not confirm:
            return await ctx.send(f'{config.EMOJIS["info"]} Removal cancelled.')
        
        await Database.remove_rule(ctx.guild.id, rule_number)
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["success"]} Rule Removed',
            description=f'**Rule #{rule_number}** has been removed.',
            color=discord.Color.orange(),
            fields=[
                {'name': 'Removed Rule', 'value': rule_text, 'inline': False}
            ],
            footer=f'Removed by {ctx.author}'
        )
        
        await ctx.send(embed=embed)
    
    @rules.command(name='edit', description='Edit an existing rule')
    @commands.has_permissions(administrator=True)
    async def edit_rule(self, ctx, rule_number: int, *, new_text: str):
        """Edit an existing rule"""
        rules = await Database.get_rules(ctx.guild.id)
        
        if not any(r['rule_number'] == rule_number for r in rules):
            return await ctx.send(
                f'{config.EMOJIS["error"]} Rule #{rule_number} not found.'
            )
        
        if len(new_text) > config.RULE_MAX_LENGTH:
            return await ctx.send(
                f'{config.EMOJIS["error"]} Rule text must be under {config.RULE_MAX_LENGTH} characters.'
            )
        
        old_rule = next(r for r in rules if r['rule_number'] == rule_number)
        
        # Update the rule
        await Database.add_rule(
            ctx.guild.id,
            rule_number,
            new_text,
            old_rule.get('category', 'General'),
            ctx.author.id
        )
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["success"]} Rule Edited',
            description=f'**Rule #{rule_number}** has been updated.',
            color=discord.Color.blue(),
            fields=[
                {'name': 'Old Rule', 'value': old_rule['rule_text'], 'inline': False},
                {'name': 'New Rule', 'value': new_text, 'inline': False}
            ],
            footer=f'Edited by {ctx.author}'
        )
        
        await ctx.send(embed=embed)
    
    @rules.command(name='category', description='Change a rule\'s category')
    @commands.has_permissions(administrator=True)
    async def change_category(self, ctx, rule_number: int, *, new_category: str):
        """Change the category of a rule"""
        rules = await Database.get_rules(ctx.guild.id)
        
        if not any(r['rule_number'] == rule_number for r in rules):
            return await ctx.send(
                f'{config.EMOJIS["error"]} Rule #{rule_number} not found.'
            )
        
        rule = next(r for r in rules if r['rule_number'] == rule_number)
        
        await Database.add_rule(
            ctx.guild.id,
            rule_number,
            rule['rule_text'],
            new_category,
            ctx.author.id
        )
        
        await ctx.send(
            f'{config.EMOJIS["success"]} Rule #{rule_number} moved to **{new_category}** category.'
        )
    
    @rules.command(name='channel', description='Set the rules channel')
    @commands.has_permissions(administrator=True)
    async def set_rules_channel(self, ctx, channel: discord.TextChannel):
        """Set the channel where rules will be displayed"""
        await Database.update_guild_settings(
            ctx.guild.id,
            rules_channel_id=channel.id
        )
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["success"]} Rules Channel Set',
            description=f'Rules will be displayed in {channel.mention}.',
            color=discord.Color.green(),
            footer=f'Set by {ctx.author}'
        )
        
        await ctx.send(embed=embed)
    
    @rules.command(name='send', description='Send the rules to the rules channel')
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def send_rules(self, ctx):
        """Send the rules embed to the designated channel"""
        settings = await Database.get_guild_settings(ctx.guild.id)
        channel_id = settings.get('rules_channel_id')
        
        if not channel_id:
            return await ctx.send(
                f'{config.EMOJIS["error"]} No rules channel set. Use `{config.PREFIX}rules channel #channel`.'
            )
        
        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send(
                f'{config.EMOJIS["error"]} Rules channel not found. It may have been deleted.'
            )
        
        rules = await Database.get_rules(ctx.guild.id)
        
        if not rules:
            return await ctx.send(
                f'{config.EMOJIS["error"]} No rules to send. Add some first!'
            )
        
        # Group by category
        categories = {}
        for rule in rules:
            cat = rule.get('category', 'General')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(rule)
        
        # Create beautiful rules embed
        embed = discord.Embed(
            title=f'📜 {ctx.guild.name} - Server Rules',
            description='Please read and follow these rules to maintain a positive community.\n\n'
                       '**Failure to follow these rules may result in moderation actions.**\n'
                       '────────────────────────────────────────',
            color=config.BOT_COLOR,
            timestamp=datetime.datetime.utcnow()
        )
        
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        
        for category, category_rules in categories.items():
            rules_text = []
            for rule in category_rules:
                rules_text.append(f'**{rule["rule_number"]}.** {rule["rule_text"]}')
            
            text = '\n'.join(rules_text)
            if len(text) > 1024:
                # Split into multiple fields if too long
                chunks = [category_rules[i:i+5] for i in range(0, len(category_rules), 5)]
                for i, chunk in enumerate(chunks):
                    chunk_text = '\n'.join([f'**{r["rule_number"]}.** {r["rule_text"]}' for r in chunk])
                    embed.add_field(
                        name=f'📌 {category} (Part {i+1})' if i > 0 else f'📌 {category}',
                        value=chunk_text,
                        inline=False
                    )
            else:
                embed.add_field(
                    name=f'📌 {category}',
                    value=text,
                    inline=False
                )
        
        embed.add_field(
            name='\u200b',
            value='────────────────────────────────────────\n'
                  '*These rules are subject to change at any time.*',
            inline=False
        )
        
        embed.set_footer(
            text=f'Last updated by {ctx.author}',
            icon_url=ctx.author.display_avatar.url
        )
        
        try:
            await channel.send(embed=embed)
            await ctx.send(f'{config.EMOJIS["success"]} Rules sent to {channel.mention}!')
        except discord.Forbidden:
            await ctx.send(f'{config.EMOJIS["error"]} I don\'t have permission to send messages in {channel.mention}.')
        except discord.HTTPException as e:
            await ctx.send(f'{config.EMOJIS["error"]} Failed to send rules: {e}')
    
    @rules.command(name='clear', description='Clear all rules')
    @commands.has_permissions(administrator=True)
    async def clear_rules(self, ctx):
        """Remove all rules from the server"""
        rules = await Database.get_rules(ctx.guild.id)
        
        if not rules:
            return await ctx.send(f'{config.EMOJIS["info"]} No rules to clear.')
        
        confirm = await Utils.confirm_action(
            ctx,
            f'Are you sure you want to delete ALL {len(rules)} rules? This cannot be undone!'
        )
        
        if not confirm:
            return await ctx.send(f'{config.EMOJIS["info"]} Clear cancelled.')
        
        # Delete all rules
        db = await Database.get_connection()
        await db.execute('DELETE FROM rules WHERE guild_id = ?', (ctx.guild.id,))
        await db.commit()
        await db.close()
        
        await ctx.send(f'{config.EMOJIS["success"]} All rules have been cleared.')
    
    @rules.command(name='import', description='Import rules from another server')
    @commands.has_permissions(administrator=True)
    async def import_rules(self, ctx, guild_id: int):
        """Import rules from another server (must be in both servers)"""
        source_guild = self.bot.get_guild(guild_id)
        if not source_guild:
            return await ctx.send(f'{config.EMOJIS["error"]} I\'m not in that server.')
        
        if not source_guild.get_member(ctx.author.id):
            return await ctx.send(f'{config.EMOJIS["error"]} You must be in the source server.')
        
        source_rules = await Database.get_rules(guild_id)
        
        if not source_rules:
            return await ctx.send(f'{config.EMOJIS["error"]} No rules found in the source server.')
        
        confirm = await Utils.confirm_action(
            ctx,
            f'Import {len(source_rules)} rules from **{source_guild.name}**? This will add to existing rules.'
        )
        
        if not confirm:
            return await ctx.send(f'{config.EMOJIS["info"]} Import cancelled.')
        
        # Get current max rule number
        current_rules = await Database.get_rules(ctx.guild.id)
        next_number = max([r['rule_number'] for r in current_rules] + [0]) + 1
        
        imported = 0
        for rule in source_rules:
            if len(current_rules) + imported >= config.MAX_RULES_PER_GUILD:
                break
            
            await Database.add_rule(
                ctx.guild.id,
                next_number + imported,
                rule['rule_text'],
                rule.get('category', 'Imported'),
                ctx.author.id
            )
            imported += 1
        
        await ctx.send(
            f'{config.EMOJIS["success"]} Imported {imported} rules from {source_guild.name}!'
        )

async def setup(bot):
    await bot.add_cog(Rules(bot))
