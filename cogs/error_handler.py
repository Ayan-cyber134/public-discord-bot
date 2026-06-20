import discord
import traceback
import sys
import logging
from typing import Union
from discord.ext import commands
from utils import Utils
from config import config

log = logging.getLogger(__name__)

class ErrorHandler(commands.Cog, name='ErrorHandler'):
    """🎯 Global error handler for the bot"""
    
    def __init__(self, bot):
        self.bot = bot
        self.error_count = 0
        self.cooldowns = {}
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Global error handler for all commands"""
        
        # Ignore these errors
        ignored_errors = (
            commands.CommandNotFound,
            commands.DisabledCommand,
        )
        
        if isinstance(error, ignored_errors):
            return
        
        # Get the error type and message
        error_type = type(error).__name__
        
        # Handle different error types
        if isinstance(error, commands.MissingRequiredArgument):
            await self.handle_missing_argument(ctx, error)
        
        elif isinstance(error, commands.BadArgument):
            await self.handle_bad_argument(ctx, error)
        
        elif isinstance(error, commands.MissingPermissions):
            await self.handle_missing_permissions(ctx, error)
        
        elif isinstance(error, commands.BotMissingPermissions):
            await self.handle_bot_missing_permissions(ctx, error)
        
        elif isinstance(error, commands.CommandOnCooldown):
            await self.handle_cooldown(ctx, error)
        
        elif isinstance(error, commands.MaxConcurrencyReached):
            await self.handle_max_concurrency(ctx, error)
        
        elif isinstance(error, commands.NoPrivateMessage):
            await self.handle_no_dm(ctx, error)
        
        elif isinstance(error, commands.PrivateMessageOnly):
            await self.handle_dm_only(ctx, error)
        
        elif isinstance(error, commands.NotOwner):
            await self.handle_not_owner(ctx, error)
        
        elif isinstance(error, commands.MemberNotFound):
            await self.handle_member_not_found(ctx, error)
        
        elif isinstance(error, commands.UserNotFound):
            await self.handle_user_not_found(ctx, error)
        
        elif isinstance(error, commands.ChannelNotFound):
            await self.handle_channel_not_found(ctx, error)
        
        elif isinstance(error, commands.RoleNotFound):
            await self.handle_role_not_found(ctx, error)
        
        elif isinstance(error, commands.EmojiNotFound):
            await self.handle_emoji_not_found(ctx, error)
        
        elif isinstance(error, commands.CheckFailure):
            await self.handle_check_failure(ctx, error)
        
        elif isinstance(error, discord.Forbidden):
            await self.handle_forbidden(ctx, error)
        
        elif isinstance(error, discord.HTTPException):
            await self.handle_http_exception(ctx, error)
        
        else:
            # Unhandled error - log it
            await self.handle_unexpected_error(ctx, error)
    
    async def handle_missing_argument(self, ctx: commands.Context, error: commands.MissingRequiredArgument):
        """Handle missing required arguments"""
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["error"]} Missing Argument',
            description=f'You missed the `{error.param.name}` argument.',
            color=discord.Color.red(),
            fields=[
                {
                    'name': 'Usage',
                    'value': f'`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`',
                    'inline': False
                }
            ]
        )
        await ctx.send(embed=embed, delete_after=30)
    
    async def handle_bad_argument(self, ctx: commands.Context, error: commands.BadArgument):
        """Handle bad argument conversion"""
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["error"]} Invalid Argument',
            description=f'Could not convert argument: {str(error)}',
            color=discord.Color.red(),
            fields=[
                {
                    'name': 'Correct Usage',
                    'value': f'`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`',
                    'inline': False
                }
            ]
        )
        await ctx.send(embed=embed, delete_after=30)
    
    async def handle_missing_permissions(self, ctx: commands.Context, error: commands.MissingPermissions):
        """Handle user missing permissions"""
        missing_perms = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["error"]} Insufficient Permissions',
            description='You don\'t have permission to use this command.',
            color=discord.Color.red(),
            fields=[
                {
                    'name': 'Required Permissions',
                    'value': '\n'.join([f'• {perm}' for perm in missing_perms]),
                    'inline': False
                }
            ]
        )
        await ctx.send(embed=embed, delete_after=30)
    
    async def handle_bot_missing_permissions(self, ctx: commands.Context, error: commands.BotMissingPermissions):
        """Handle bot missing permissions"""
        missing_perms = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["error"]} I Need Permissions',
            description='I don\'t have the required permissions to execute this command.',
            color=discord.Color.red(),
            fields=[
                {
                    'name': 'Missing Permissions',
                    'value': '\n'.join([f'• {perm}' for perm in missing_perms]),
                    'inline': False
                }
            ]
        )
        await ctx.send(embed=embed, delete_after=30)
    
    async def handle_cooldown(self, ctx: commands.Context, error: commands.CommandOnCooldown):
        """Handle command cooldown"""
        retry_after = error.retry_after
        
        if retry_after < 60:
            time_str = f'{retry_after:.1f} seconds'
        elif retry_after < 3600:
            time_str = f'{retry_after / 60:.1f} minutes'
        else:
            time_str = f'{retry_after / 3600:.1f} hours'
        
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["warning"]} Command on Cooldown',
            description=f'Please wait {time_str} before using this command again.',
            color=discord.Color.gold()
        )
        
        # Only send cooldown message every 5 seconds to prevent spam
        cooldown_key = f'{ctx.author.id}-{ctx.command.qualified_name}'
        import time
        now = time.time()
        
        if cooldown_key not in self.cooldowns or now - self.cooldowns[cooldown_key] > 5:
            self.cooldowns[cooldown_key] = now
            await ctx.send(embed=embed, delete_after=10)
    
    async def handle_max_concurrency(self, ctx: commands.Context, error: commands.MaxConcurrencyReached):
        """Handle max concurrency reached"""
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["warning"]} Command Busy',
            description=f'This command is already running. Please wait for it to finish.',
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed, delete_after=10)
    
    async def handle_no_dm(self, ctx: commands.Context, error: commands.NoPrivateMessage):
        """Handle commands that can't be used in DMs"""
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["info"]} Server Only',
            description='This command can only be used in a server.',
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, delete_after=15)
    
    async def handle_dm_only(self, ctx: commands.Context, error: commands.PrivateMessageOnly):
        """Handle commands that can only be used in DMs"""
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["info"]} DM Only',
            description='This command can only be used in DMs.',
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, delete_after=15)
    
    async def handle_not_owner(self, ctx: commands.Context, error: commands.NotOwner):
        """Handle owner-only commands"""
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["error"]} Owner Only',
            description='This command is reserved for the bot owner.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=15)
    
    async def handle_member_not_found(self, ctx: commands.Context, error: commands.MemberNotFound):
        """Handle member not found"""
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["error"]} Member Not Found',
            description=f'Could not find member: {error.argument}',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=15)
    
    async def handle_user_not_found(self, ctx: commands.Context, error: commands.UserNotFound):
        """Handle user not found"""
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["error"]} User Not Found',
            description=f'Could not find user: {error.argument}',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=15)
    
    async def handle_channel_not_found(self, ctx: commands.Context, error: commands.ChannelNotFound):
        """Handle channel not found"""
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["error"]} Channel Not Found',
            description=f'Could not find channel: {error.argument}',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=15)
    
    async def handle_role_not_found(self, ctx: commands.Context, error: commands.RoleNotFound):
        """Handle role not found"""
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["error"]} Role Not Found',
            description=f'Could not find role: {error.argument}',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=15)
    
    async def handle_emoji_not_found(self, ctx: commands.Context, error: commands.EmojiNotFound):
        """Handle emoji not found"""
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["error"]} Emoji Not Found',
            description=f'Could not find emoji: {error.argument}',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=15)
    
    async def handle_check_failure(self, ctx: commands.Context, error: commands.CheckFailure):
        """Handle check failures"""
        if isinstance(error, commands.MissingRole):
            embed = Utils.create_embed(
                title=f'{config.EMOJIS["error"]} Missing Role',
                description=f'You need the {error.missing_role} role to use this command.',
                color=discord.Color.red()
            )
        elif isinstance(error, commands.MissingAnyRole):
            roles = ', '.join(error.missing_roles)
            embed = Utils.create_embed(
                title=f'{config.EMOJIS["error"]} Missing Role',
                description=f'You need one of these roles: {roles}',
                color=discord.Color.red()
            )
        else:
            embed = Utils.create_embed(
                title=f'{config.EMOJIS["error"]} Check Failed',
                description='You don\'t meet the requirements for this command.',
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed, delete_after=15)
    
    async def handle_forbidden(self, ctx: commands.Context, error: discord.Forbidden):
        """Handle forbidden errors"""
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["error"]} Forbidden',
            description='I don\'t have permission to do that. Check my role permissions.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=15)
    
    async def handle_http_exception(self, ctx: commands.Context, error: discord.HTTPException):
        """Handle HTTP exceptions"""
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["error"]} API Error',
            description='An error occurred while communicating with Discord. Try again later.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=15)
    
    async def handle_unexpected_error(self, ctx: commands.Context, error: Exception):
        """Handle unexpected errors"""
        self.error_count += 1
        
        # Create error embed
        embed = Utils.create_embed(
            title=f'{config.EMOJIS["error"]} Unexpected Error',
            description='An unexpected error occurred. The error has been logged.',
            color=discord.Color.dark_red(),
            fields=[
                {
                    'name': 'Error',
                    'value': f'```py\n{str(error)[:500]}\n```',
                    'inline': False
                },
                {
                    'name': 'Command',
                    'value': ctx.command.qualified_name if ctx.command else 'Unknown',
                    'inline': True
                },
                {
                    'name': 'Error ID',
                    'value': f'#{self.error_count}',
                    'inline': True
                }
            ],
            footer='If this persists, please contact the bot owner.'
        )
        
        await ctx.send(embed=embed)
        
        # Log the full error
        log.error(
            f'Unexpected error in command {ctx.command}:',
            exc_info=(type(error), error, error.__traceback__)
        )
        
        # Print full traceback
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr
        )

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
