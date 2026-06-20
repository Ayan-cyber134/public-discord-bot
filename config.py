import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Config:
    """Central configuration class for the bot"""
    
    TOKEN: str = os.getenv('DISCORD_TOKEN', '')
    PREFIX: str = os.getenv('PREFIX', '!')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    
    OWNER_IDS: List[int] = [
        int(id.strip()) 
        for id in os.getenv('OWNER_IDS', '').split(',') 
        if id.strip().isdigit()
    ]
    
    # Bot settings
    BOT_NAME = "Advanced Discord Bot"
    BOT_VERSION = "1.0.0"
    BOT_COLOR = 0x5865F2  # Discord blurple
    BOT_INVITE = "https://discord.com/api/oauth2/authorize?client_id=BOT_ID_HERE&permissions=8&scope=bot%20applications.commands"
    
    # Database
    DB_PATH = "database.db"
    
    # Moderation defaults
    DEFAULT_MUTE_DURATION = 3600  # 1 hour in seconds
    MAX_WARNINGS_BEFORE_ACTION = 3
    WARNING_EXPIRY_DAYS = 30  # Warnings expire after 30 days
    
    # Auto mod defaults
    ANTI_SPAM_THRESHOLD = 5
    ANTI_SPAM_INTERVAL = 10 
    ANTI_MENTION_LIMIT = 5
    ANTI_LINK_WHITELIST = ['discord.gg', 'discord.com']
    
    # Rules system
    MAX_RULES_PER_GUILD = 25
    RULE_MAX_LENGTH = 500
    
    # Cooldowns (in seconds)
    COMMAND_COOLDOWN = 3
    FUN_COMMAND_COOLDOWN = 5
    
    # Emojis (customize these)
    EMOJIS = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️',
        'loading': '🔄',
        'mod': '🛡️',
        'ban': '🔨',
        'kick': '👢',
        'mute': '🔇',
        'warn': '⚠️',
        'purge': '🧹',
        'rules': '📜',
        'settings': '⚙️',
        'stats': '📊',
        'fun': '🎮',
        'utility': '🔧',
        'owner': '👑',
        'automod': '🤖',
    }

config = Config()
