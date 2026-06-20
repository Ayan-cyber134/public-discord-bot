import discord
import asyncio
import os
import sys
import io
import textwrap
import traceback
from contextlib import redirect_stdout
from discord.ext import commands
from utils import Utils
from config import config

class Owner(commands.Cog, name='Owner'):
    """👑 Owner-only commands for bot management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_check(self, ctx):
        """Check if user is bot owner"""
        if not await self.bot.is_owner(ctx.author):
            raise commands.NotOwner()
        return True
    
    @commands.command(name='sync', hidden=True)
    async def sync(self, ctx, guild_id: int = None):
        """Sync application commands globally or to a specific guild"""
        await ctx.defer()
        
        if guild_id:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return await ctx.send(f'{config.EMOJIS["error"]} Guild not found.')
            
            synced = await self.bot.tree.sync(guild=guild)
            await ctx.send(f'{config.EMOJIS["success"]} Synced {len(synced)} commands to {guild.name}.')
        else:
            synced = await self.bot.tree.sync()
            await ctx.send(f'{config.EMOJIS["success"]} Synced {len(synced)} commands globally.')
    
    @commands.command(name='reload', aliases=['r'], hidden=True)
    async def reload(self, ctx, *, cog: str):
        """Reload a cog"""
        try:
            await self.bot.reload_extension(f'cogs.{cog}')
            await ctx.send(f'{config.EMOJIS["success"]} Reloaded `{cog}` cog.')
        except Exception as e:
            await ctx.send(f'{config.EMOJIS["error"]} Failed to reload `{cog}`: {e}')
    
    @commands.command(name='load', hidden=True)
    async def load(self, ctx, *, cog: str):
        """Load a cog"""
        try:
            await self.bot.load_extension(f'cogs.{cog}')
            await ctx.send(f'{config.EMOJIS["success"]} Loaded `{cog}` cog.')
        except Exception as e:
            await ctx.send(f'{config.EMOJIS["error"]} Failed to load `{cog}`: {e}')
    
    @commands.command(name='unload', hidden=True)
    async def unload(self, ctx, *, cog: str):
        """Unload a cog"""
        try:
            await self.bot.unload_extension(f'cogs.{cog}')
            await ctx.send(f'{config.EMOJIS["success"]} Unloaded `{cog}` cog.')
        except Exception as e:
            await ctx.send(f'{config.EMOJIS["error"]} Failed to unload `{cog}`: {e}')
    
    @commands.command(name='shutdown', aliases=['die', 'kill'], hidden=True)
    async def shutdown(self, ctx):
        """Shut down the bot"""
        confirm = await Utils.confirm_action(
            ctx,
            'Are you sure you want to shut down the bot?'
        )
        
        if not confirm:
            return await ctx.send(f'{config.EMOJIS["info"]} Shutdown cancelled.')
        
        await ctx.send(f'{config.EMOJIS["success"]} Shutting down...')
        await self.bot.close()
    
    @commands.command(name='restart', hidden=True)
    async def restart(self, ctx):
        """Restart the bot"""
        confirm = await Utils.confirm_action(
            ctx,
            'Are you sure you want to restart the bot?'
        )
        
        if not confirm:
            return await ctx.send(f'{config.EMOJIS["info"]} Restart cancelled.')
        
        await ctx.send(f'{config.EMOJIS["loading"]} Restarting...')
        os.execv(sys.executable, ['python'] + sys.argv)
    
    @commands.command(name='servers', aliases=['guilds'], hidden=True)
    async def servers(self, ctx):
        """List all servers the bot is in"""
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        
        embeds = []
        for i, guild in enumerate(guilds):
            embed = discord.Embed(
                title=f'🌐 Server List ({i+1}/{len(guilds)})',
                color=config.BOT_COLOR
            )
            embed.add_field(name='Name', value=guild.name, inline=True)
            embed.add_field(name='ID', value=guild.id, inline=True)
            embed.add_field(name='Members', value=guild.member_count, inline=True)
            embed.add_field(name='Owner', value=str(guild.owner), inline=True)
            
            embeds.append(embed)
        
        await Utils.paginate(ctx, embeds)
    
    @commands.command(name='leave', hidden=True)
    async def leave_guild(self, ctx, guild_id: int):
        """Leave a guild by ID"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.send(f'{config.EMOJIS["error"]} Guild not found.')
        
        confirm = await Utils.confirm_action(
            ctx,
            f'Are you sure you want me to leave **{guild.name}**?'
        )
        
        if not confirm:
            return await ctx.send(f'{config.EMOJIS["info"]} Cancelled.')
        
        await guild.leave()
        await ctx.send(f'{config.EMOJIS["success"]} Left **{guild.name}**.')
    
    @commands.command(name='eval', hidden=True)
    async def eval_code(self, ctx, *, code: str):
        """Evaluate Python code"""
        
        if code.startswith('```') and code.endswith('```'):
            code = '\n'.join(code.split('\n')[1:-1])
        else:
            code = code.strip('` \n')
        
        # Create environment
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            'discord': discord,
            'commands': commands,
            'asyncio': asyncio,
            'config': config
        }
        
        env.update(globals())
        
        stdout = io.StringIO()
        
        try:
            with redirect_stdout(stdout):
                exec(
                    f'async def func():\n{textwrap.indent(code, "  ")}',
                    env
                )
                
                result = await env['func']()
                
                value = stdout.getvalue()
                
                if result is not None:
                    value += str(result)
                
                if not value:
                    value = 'No output'
                
                if len(value) > 2000:
                    value = value[:1990] + '\n... (truncated)'
                
                embed = Utils.create_embed(
                    title='✅ Eval Result',
                    description=f'```py\n{value}\n```',
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                
        except Exception as e:
            embed = Utils.create_embed(
                title='❌ Eval Error',
                description=f'```py\n{traceback.format_exc()[:1000]}\n```',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='sql', hidden=True)
    async def execute_sql(self, ctx, *, query: str):
        """Execute SQL query on the database"""
        from database import Database
        
        try:
            db = await Database.get_connection()
            
            if query.lower().startswith('select'):
                cursor = await db.execute(query)
                rows = await cursor.fetchall()
                
                if not rows:
                    result = 'No results.'
                else:
                    
                    columns = rows[0].keys()
                    result = ' | '.join(columns) + '\n' + '-' * 50 + '\n'
                    for row in rows[:25]:
                        result += ' | '.join(str(val)[:50] for val in row) + '\n'
                    
                    if len(rows) > 25:
                        result += f'\n... and {len(rows) - 25} more rows'
            else:
                await db.execute(query)
                await db.commit()
                result = 'Query executed successfully.'
            
            await db.close()
            
            if len(result) > 2000:
                result = result[:1990] + '\n... (truncated)'
            
            embed = Utils.create_embed(
                title='🗄️ SQL Result',
                description=f'```\n{result}\n```',
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f'{config.EMOJIS["error"]} SQL Error: {e}')
    
    @commands.command(name='presence', hidden=True)
    async def change_presence(self, ctx, activity_type: str, *, name: str):
        """Change the bot's presence"""
        activity_types = {
            'playing': discord.ActivityType.playing,
            'streaming': discord.ActivityType.streaming,
            'listening': discord.ActivityType.listening,
            'watching': discord.ActivityType.watching,
            'competing': discord.ActivityType.competing
        }
        
        if activity_type.lower() not in activity_types:
            return await ctx.send(f'{config.EMOJIS["error"]} Invalid activity type. Use: {", ".join(activity_types.keys())}')
        
        activity = discord.Activity(
            type=activity_types[activity_type.lower()],
            name=name
        )
        
        await self.bot.change_presence(activity=activity)
        await ctx.send(f'{config.EMOJIS["success"]} Presence changed to {activity_type} **{name}**')
    
    @commands.command(name='announce', hidden=True)
    async def announce(self, ctx, *, message: str):
        """Send an announcement to all server owners"""
        confirm = await Utils.confirm_action(
            ctx,
            f'Are you sure you want to send this announcement to {len(self.bot.guilds)} servers?\n\n{message[:200]}'
        )
        
        if not confirm:
            return await ctx.send(f'{config.EMOJIS["info"]} Cancelled.')
        
        success = 0
        failed = 0
        
        embed = discord.Embed(
            title='📢 Announcement from Bot Owner',
            description=message,
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f'From: {ctx.author}')
        
        for guild in self.bot.guilds:
            try:
                if guild.system_channel:
                    await guild.system_channel.send(embed=embed)
                    success += 1
                else:
                    
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            await channel.send(embed=embed)
                            success += 1
                            break
            except:
                failed += 1
            
            await asyncio.sleep(0.5)
        
        await ctx.send(f'{config.EMOJIS["success"]} Announcement sent! Success: {success}, Failed: {failed}')

async def setup(bot):
    await bot.add_cog(Owner(bot))
