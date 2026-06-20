import os
import sys
import asyncio
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import Database
from config import config
import colorama
from colorama import Fore, Style

# Initialize colorama for colored console output
colorama.init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format=f'{Fore.CYAN}%(asctime)s{Style.RESET_ALL} {Fore.GREEN}[%(levelname)s]{Style.RESET_ALL} {Fore.WHITE}%(name)s{Style.RESET_ALL}: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

log = logging.getLogger(__name__)

class AdvancedBot(commands.Bot):
    """Advanced Discord Bot with multi-purpose functionality"""
    
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.PREFIX),
            intents=discord.Intents.all(),
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
            owner_ids=set(config.OWNER_IDS),
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name='over the server'
            ),
            status=discord.Status.online
        )
        self.start_time = None
    
    async def setup_hook(self):
        """Setup hook for loading cogs and initializing database"""
        log.info(f'{Fore.YELLOW}Initializing database...{Style.RESET_ALL}')
        await Database.initialize()
        
        # List of cogs to load
        cogs = [
            'cogs.error_handler',
            'cogs.modlog',
            'cogs.moderation',
            'cogs.automod',
            'cogs.rules',
            'cogs.utility',
            'cogs.fun',
            'cogs.help',
            'cogs.owner'
        ]
        
        # Load cogs
        for cog in cogs:
            try:
                await self.load_extension(cog)
                log.info(f'{Fore.GREEN}✓ Loaded cog:{Style.RESET_ALL} {cog}')
            except Exception as e:
                log.error(f'{Fore.RED}✗ Failed to load {cog}:{Style.RESET_ALL} {e}')
        
        # Sync application commands
        log.info(f'{Fore.YELLOW}Syncing application commands...{Style.RESET_ALL}')
        await self.tree.sync()
        log.info(f'{Fore.GREEN}Commands synced successfully!{Style.RESET_ALL}')
    
    async def on_ready(self):
        """Called when the bot is ready"""
        if not self.start_time:
            import datetime
            self.start_time = datetime.datetime.utcnow()
        
        log.info(f'{Fore.GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')
        log.info(f'{Fore.CYAN}Bot is ready!{Style.RESET_ALL}')
        log.info(f'{Fore.WHITE}Name:{Style.RESET_ALL} {self.user.name}')
        log.info(f'{Fore.WHITE}ID:{Style.RESET_ALL} {self.user.id}')
        log.info(f'{Fore.WHITE}Servers:{Style.RESET_ALL} {len(self.guilds)}')
        log.info(f'{Fore.WHITE}Users:{Style.RESET_ALL} {len(self.users)}')
        log.info(f'{Fore.WHITE}Commands:{Style.RESET_ALL} {len(self.commands)}')
        log.info(f'{Fore.GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')
        
        # Update presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f'{config.PREFIX}help | {len(self.guilds)} servers'
            )
        )
    
    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild"""
        log.info(f'{Fore.GREEN}Joined new guild:{Style.RESET_ALL} {guild.name} (ID: {guild.id})')
        
        # Create default guild settings
        await Database.get_guild_settings(guild.id)
        await Database.get_automod_config(guild.id)
        
        
        if guild.system_channel:
            embed = Utils.create_embed(
                title=f'👋 Thanks for adding {self.user.name}!',
                description=f'Use `{config.PREFIX}help` to see all commands.',
                color=config.BOT_COLOR,
                fields=[
                    {'name': '📜 Rules System', 'value': 'Set up server rules with ease', 'inline': True},
                    {'name': '🛡️ Moderation', 'value': 'Powerful moderation tools', 'inline': True},
                    {'name': '🤖 Auto-Mod', 'value': 'Automatic moderation features', 'inline': True},
                    {'name': '⚙️ Settings', 'value': f'Configure with `{config.PREFIX}settings`', 'inline': True}
                ]
            )
            try:
                await guild.system_channel.send(embed=embed)
            except discord.Forbidden:
                pass

if __name__ == '__main__':
    
    load_dotenv()
    
    
    if not config.TOKEN:
        log.critical(f'{Fore.RED}DISCORD_TOKEN not found in .env file!{Style.RESET_ALL}')
        sys.exit(1)
    
    
    bot = AdvancedBot()
    
    try:
        bot.run(config.TOKEN, log_handler=None)
    except discord.LoginFailure:
        log.critical(f'{Fore.RED}Invalid token provided!{Style.RESET_ALL}')
        sys.exit(1)
    except Exception as e:
        log.critical(f'{Fore.RED}Fatal error:{Style.RESET_ALL} {e}')
        sys.exit(1)
