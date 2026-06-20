import discord
import random
import asyncio
import aiohttp
from typing import Optional
from discord.ext import commands
from utils import Utils
from config import config

class Fun(commands.Cog, name='Fun'):
    """🎮 Fun and entertainment commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.session = None
    
    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def cog_unload(self):
        if self.session:
            asyncio.create_task(self.session.close())
    
    @commands.hybrid_command(name='8ball', aliases=['8b', 'ask'],
                            description='Ask the magic 8-ball a question')
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def eight_ball(self, ctx, *, question: str):
        """Ask the magic 8-ball a question"""
        responses = [
            # Positive responses
            '🎱 It is certain.',
            '🎱 It is decidedly so.',
            '🎱 Without a doubt.',
            '🎱 Yes - definitely.',
            '🎱 You may rely on it.',
            '🎱 As I see it, yes.',
            '🎱 Most likely.',
            '🎱 Outlook good.',
            '🎱 Yes.',
            '🎱 Signs point to yes.',
            # Uncertain responses
            '🎱 Reply hazy, try again.',
            '🎱 Ask again later.',
            '🎱 Better not tell you now.',
            '🎱 Cannot predict now.',
            '🎱 Concentrate and ask again.',
            # Negative responses
            '🎱 Don\'t count on it.',
            '🎱 My reply is no.',
            '🎱 My sources say no.',
            '🎱 Outlook not so good.',
            '🎱 Very doubtful.'
        ]
        
        response = random.choice(responses)
        
        embed = Utils.create_embed(
            title='🎱 Magic 8-Ball',
            color=discord.Color.purple(),
            fields=[
                {'name': 'Question', 'value': question, 'inline': False},
                {'name': 'Answer', 'value': response, 'inline': False}
            ],
            footer=f'Asked by {ctx.author}'
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='roll', aliases=['dice', 'r'],
                            description='Roll a dice')
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def roll(self, ctx, sides: int = 6):
        """Roll a dice with specified number of sides"""
        if sides < 2:
            return await ctx.send(f'{config.EMOJIS["error"]} Dice must have at least 2 sides.')
        if sides > 1000:
            return await ctx.send(f'{config.EMOJIS["error"]} Dice can have at most 1000 sides.')
        
        result = random.randint(1, sides)
        
        # Create a visual dice if standard
        if sides == 6:
            dice_faces = {
                1: '⚀',
                2: '⚁',
                3: '⚂',
                4: '⚃',
                5: '⚄',
                6: '⚅'
            }
            dice_visual = dice_faces[result]
        else:
            dice_visual = f'[ {result} ]'
        
        embed = Utils.create_embed(
            title='🎲 Dice Roll',
            description=f'You rolled a **d{sides}**!',
            color=discord.Color.blue(),
            fields=[
                {'name': 'Result', 'value': f'{dice_visual} **{result}**', 'inline': False}
            ],
            footer=f'Rolled by {ctx.author}'
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='coinflip', aliases=['cf', 'coin'],
                            description='Flip a coin')
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def coinflip(self, ctx):
        """Flip a coin"""
        result = random.choice(['Heads', 'Tails'])
        emoji = '🪙' if result == 'Heads' else '💿'
        
        # Animate the flip
        flip_msg = await ctx.send('🔄 Flipping...')
        await asyncio.sleep(1)
        
        embed = Utils.create_embed(
            title=f'{emoji} Coin Flip',
            description=f'The coin landed on **{result}**!',
            color=discord.Color.gold() if result == 'Heads' else discord.Color.light_gray(),
            footer=f'Flipped by {ctx.author}'
        )
        
        await flip_msg.edit(content=None, embed=embed)
    
    @commands.hybrid_command(name='meme', description='Get a random meme')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def meme(self, ctx):
        """Fetch a random meme from Reddit"""
        await ctx.defer()
        
        try:
            session = await self.get_session()
            
            async with session.get('https://meme-api.com/gimme') as response:
                if response.status == 200:
                    data = await response.json()
                    
                    embed = discord.Embed(
                        title=data['title'][:256],
                        color=discord.Color.random(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.set_image(url=data['url'])
                    embed.add_field(
                        name='Info',
                        value=f'👍 {data["ups"]} upvotes | 💬 r/{data["subreddit"]}',
                        inline=False
                    )
                    embed.set_footer(text=f'Requested by {ctx.author}')
                    
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f'{config.EMOJIS["error"]} Failed to fetch meme. Try again later.')
        
        except Exception as e:
            await ctx.send(f'{config.EMOJIS["error"]} Error fetching meme: {str(e)}')
    
    @commands.hybrid_command(name='rps', aliases=['rockpaperscissors'],
                            description='Play Rock Paper Scissors')
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def rps(self, ctx, choice: str):
        """Play Rock Paper Scissors against the bot"""
        choices = {
            'rock': '🪨',
            'paper': '📄',
            'scissors': '✂️',
            'r': '🪨',
            'p': '📄',
            's': '✂️'
        }
        
        choice = choice.lower()
        if choice not in choices:
            return await ctx.send(f'{config.EMOJIS["error"]} Please choose: rock, paper, or scissors (r/p/s)')
        
        user_choice = choices[choice]
        bot_choice = random.choice(['🪨', '📄', '✂️'])
        
        # Determine winner
        if user_choice == bot_choice:
            result = "It's a tie!"
            color = discord.Color.gold()
        elif (user_choice == '🪨' and bot_choice == '✂️') or \
             (user_choice == '📄' and bot_choice == '🪨') or \
             (user_choice == '✂️' and bot_choice == '📄'):
            result = 'You win!'
            color = discord.Color.green()
        else:
            result = 'You lose!'
            color = discord.Color.red()
        
        embed = Utils.create_embed(
            title='🎮 Rock Paper Scissors',
            color=color,
            fields=[
                {'name': 'You', 'value': user_choice, 'inline': True},
                {'name': 'Bot', 'value': bot_choice, 'inline': True},
                {'name': 'Result', 'value': result, 'inline': False}
            ],
            footer=f'Played by {ctx.author}'
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='joke', description='Get a random joke')
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def joke(self, ctx):
        """Fetch a random joke"""
        await ctx.defer()
        
        try:
            session = await self.get_session()
            
            async with session.get('https://official-joke-api.appspot.com/random_joke') as response:
                if response.status == 200:
                    data = await response.json()
                    
                    embed = Utils.create_embed(
                        title='😂 Random Joke',
                        description=f'**{data["setup"]}**\n\n*{data["punchline"]}*',
                        color=discord.Color.orange(),
                        footer=f'Requested by {ctx.author}'
                    )
                    
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f'{config.EMOJIS["error"]} Failed to fetch joke.')
        
        except Exception as e:
            await ctx.send(f'{config.EMOJIS["error"]} Error: {str(e)}')
    
    @commands.hybrid_command(name='choose', aliases=['pick'],
                            description='Let the bot choose between options')
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def choose(self, ctx, *, options: str):
        """Bot chooses between options separated by commas"""
        choices = [option.strip() for option in options.split(',')]
        
        if len(choices) < 2:
            return await ctx.send(f'{config.EMOJIS["error"]} Please provide at least 2 options separated by commas.')
        
        # Animate choice
        choose_msg = await ctx.send('🤔 Let me think...')
        await asyncio.sleep(1)
        
        for _ in range(3):
            await choose_msg.edit(content=f'🤔 {random.choice(choices)}...')
            await asyncio.sleep(0.5)
        
        final_choice = random.choice(choices)
        
        embed = Utils.create_embed(
            title='✅ I Choose...',
            description=f'**{final_choice}**',
            color=discord.Color.green(),
            fields=[
                {'name': 'Options', 'value': ', '.join(choices), 'inline': False}
            ],
            footer=f'Chosen by {ctx.author}'
        )
        
        await choose_msg.edit(content=None, embed=embed)
    
    @commands.hybrid_command(name='say', description='Make the bot say something')
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx, channel: Optional[discord.TextChannel] = None, *, message: str):
        """Make the bot say a message in a channel"""
        target_channel = channel or ctx.channel
        
        try:
            await target_channel.send(message)
            if channel and channel != ctx.channel:
                await ctx.send(f'{config.EMOJIS["success"]} Message sent to {channel.mention}')
            else:
                await ctx.message.delete()
        except discord.Forbidden:
            await ctx.send(f'{config.EMOJIS["error"]} Cannot send messages in that channel.')
    
    @commands.hybrid_command(name='embed', description='Create an embed message')
    @commands.has_permissions(manage_messages=True)
    async def create_embed(self, ctx, title: str, description: str, color: str = 'blue'):
        """Create a custom embed"""
        colors = {
            'red': discord.Color.red(),
            'blue': discord.Color.blue(),
            'green': discord.Color.green(),
            'orange': discord.Color.orange(),
            'purple': discord.Color.purple(),
            'gold': discord.Color.gold(),
            'random': discord.Color.random()
        }
        
        embed = Utils.create_embed(
            title=title,
            description=description,
            color=colors.get(color.lower(), discord.Color.blue()),
            footer=f'Created by {ctx.author}'
        )
        
        await ctx.send(embed=embed)
        await ctx.message.delete()
    
    @commands.hybrid_command(name='poll', description='Create a poll')
    @commands.has_permissions(manage_messages=True)
    async def poll(self, ctx, title: str, *, options: str):
        """Create a poll with reactions"""
        options_list = [opt.strip() for opt in options.split(',')]
        
        if len(options_list) < 2:
            return await ctx.send(f'{config.EMOJIS["error"]} Need at least 2 options.')
        if len(options_list) > 10:
            return await ctx.send(f'{config.EMOJIS["error"]} Maximum 10 options allowed.')
        
        # Reaction emojis
        emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        
        # Create poll embed
        description = '\n'.join([f'{emoji_list[i]} {opt}' for i, opt in enumerate(options_list)])
        
        embed = Utils.create_embed(
            title=f'📊 {title}',
            description=description,
            color=discord.Color.blue(),
            footer=f'Poll by {ctx.author}'
        )
        
        poll_msg = await ctx.send(embed=embed)
        
        # Add reactions
        for i in range(len(options_list)):
            await poll_msg.add_reaction(emoji_list[i])
        
        await ctx.message.delete()

async def setup(bot):
    await bot.add_cog(Fun(bot))
