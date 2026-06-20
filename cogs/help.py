import discord
from typing import Optional
from discord.ext import commands
from utils import Utils
from config import config

class HelpCommand(commands.Cog, name='Help'):
    """📚 Custom help command system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command('help')
    
    @commands.hybrid_command(name='help', aliases=['h', 'commands'],
                            description='Get help with the bot')
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def help(self, ctx, *, command_or_category: Optional[str] = None):
        """Display help for commands and categories"""
        
        if not command_or_category:
            # Show main help menu
            await self.send_main_help(ctx)
        else:
            # Check if it's a category
            cog = self.bot.get_cog(command_or_category.capitalize())
            if cog:
                await self.send_category_help(ctx, cog)
            else:
                # Check if it's a command
                cmd = self.bot.get_command(command_or_category.lower())
                if cmd:
                    await self.send_command_help(ctx, cmd)
                else:
                    # Try fuzzy matching
                    await self.send_fuzzy_help(ctx, command_or_category)
    
    async def send_main_help(self, ctx):
        """Send the main help menu"""
        embed = discord.Embed(
            title=f'{config.BOT_NAME} Help Menu',
            description=f'Use `{config.PREFIX}help <command>` for more info on a command.\n'
                       f'Use `{config.PREFIX}help <category>` to browse a category.',
            color=config.BOT_COLOR,
            timestamp=discord.utils.utcnow()
        )
        
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        # Add each category
        for cog_name, cog in sorted(self.bot.cogs.items()):
            if cog_name in ['ErrorHandler']:
                continue
            
            commands_list = cog.get_commands()
            if not commands_list:
                continue
            
            # Filter out hidden commands
            visible_commands = [cmd for cmd in commands_list if not cmd.hidden]
            if not visible_commands:
                continue
            
            # Get cog description
            description = cog.description or 'No description'
            
            # Format commands
            cmd_names = ', '.join([f'`{cmd.name}`' for cmd in visible_commands[:5]])
            if len(visible_commands) > 5:
                cmd_names += f' and {len(visible_commands) - 5} more...'
            
            embed.add_field(
                name=f'{description}',
                value=f'{cmd_names}\n'
                      f'*{len(visible_commands)} commands*',
                inline=False
            )
        
        # Add useful links
        embed.add_field(
            name='🔗 Useful Links',
            value=f'[Invite Bot]({config.BOT_INVITE.format(self.bot.user.id)})\n'
                  f'[Support Server](https://discord.gg/example)',
            inline=False
        )
        
        embed.set_footer(
            text=f'{len(self.bot.commands)} total commands | {config.PREFIX}help <command> for details',
            icon_url=ctx.author.display_avatar.url
        )
        
        await ctx.send(embed=embed)
    
    async def send_category_help(self, ctx, cog: commands.Cog):
        """Send help for a specific category"""
        commands_list = cog.get_commands()
        visible_commands = [cmd for cmd in commands_list if not cmd.hidden]
        
        if not visible_commands:
            return await ctx.send(f'{config.EMOJIS["error"]} No commands found in this category.')
        
        embed = discord.Embed(
            title=f'{cog.description or cog.qualified_name}',
            description=f'All commands in the {cog.qualified_name} category.',
            color=config.BOT_COLOR,
            timestamp=discord.utils.utcnow()
        )
        
        # Group commands
        for cmd in sorted(visible_commands, key=lambda c: c.name):
            # Get command signature
            if hasattr(cmd, 'commands') and cmd.commands:
                # This is a command group
                sub_commands = [f'`{sub.name}`' for sub in cmd.commands if not sub.hidden]
                if sub_commands:
                    embed.add_field(
                        name=f'📁 {cmd.qualified_name}',
                        value=f'{cmd.description}\n*Subcommands: {", ".join(sub_commands)}*',
                        inline=False
                    )
            else:
                embed.add_field(
                    name=f'`{cmd.qualified_name} {cmd.signature}`' if cmd.signature else f'`{cmd.qualified_name}`',
                    value=cmd.description or 'No description',
                    inline=False
                )
        
        embed.set_footer(
            text=f'{config.PREFIX}help <command> for detailed usage',
            icon_url=ctx.author.display_avatar.url
        )
        
        await ctx.send(embed=embed)
    
    async def send_command_help(self, ctx, cmd: commands.Command):
        """Send help for a specific command"""
        embed = discord.Embed(
            title=f'Command: {cmd.qualified_name}',
            color=config.BOT_COLOR,
            timestamp=discord.utils.utcnow()
        )
        
        # Description
        embed.add_field(
            name='📝 Description',
            value=cmd.description or 'No description available',
            inline=False
        )
        
        # Usage
        usage = f'`{config.PREFIX}{cmd.qualified_name} {cmd.signature}`' if cmd.signature else f'`{config.PREFIX}{cmd.qualified_name}`'
        embed.add_field(
            name='🔧 Usage',
            value=usage,
            inline=False
        )
        
        # Aliases
        if cmd.aliases:
            embed.add_field(
                name='🔄 Aliases',
                value=', '.join([f'`{alias}`' for alias in cmd.aliases]),
                inline=False
            )
        
        # Cooldown
        if cmd._buckets and hasattr(cmd, '_buckets'):
            try:
                cooldown = cmd._buckets._cooldown
                if cooldown:
                    embed.add_field(
                        name='⏱️ Cooldown',
                        value=f'{cooldown.per:.0f} seconds per {cooldown.type.name}',
                        inline=False
                    )
            except:
                pass
        
        # Permissions
        if hasattr(cmd, 'checks') and cmd.checks:
            try:
                # This is simplified; actual permission checking would be more complex
                pass
            except:
                pass
        
        # Subcommands
        if hasattr(cmd, 'commands') and cmd.commands:
            sub_commands = [f'`{sub.name}`' for sub in cmd.commands if not sub.hidden]
            if sub_commands:
                embed.add_field(
                    name='📁 Subcommands',
                    value=', '.join(sub_commands),
                    inline=False
                )
        
        embed.set_footer(
            text=f'Category: {cmd.cog_name}',
            icon_url=ctx.author.display_avatar.url
        )
        
        await ctx.send(embed=embed)
    
    async def send_fuzzy_help(self, ctx, query: str):
        """Try to find similar commands"""
        all_commands = [cmd.qualified_name for cmd in self.bot.commands if not cmd.hidden]
        
        # Simple fuzzy matching
        matches = []
        for cmd_name in all_commands:
            if query.lower() in cmd_name.lower():
                matches.append(cmd_name)
        
        if matches:
            embed = discord.Embed(
                title=f'🔍 Search Results for "{query}"',
                description='Did you mean one of these commands?',
                color=config.BOT_COLOR
            )
            
            for match in matches[:10]:
                cmd = self.bot.get_command(match)
                if cmd:
                    embed.add_field(
                        name=f'`{match}`',
                        value=cmd.description or 'No description',
                        inline=False
                    )
            
            if len(matches) > 10:
                embed.set_footer(text=f'Showing 10 of {len(matches)} results')
            
            await ctx.send(embed=embed)
        else:
            embed = Utils.create_embed(
                title=f'{config.EMOJIS["error"]} Not Found',
                description=f'No command or category found matching "{query}".',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
