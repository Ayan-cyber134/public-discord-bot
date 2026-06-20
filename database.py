import aiosqlite
import logging
from typing import Optional, List, Dict, Any
from config import config

log = logging.getLogger(__name__)

class Database:
    """Async database manager for the bot"""
    
    @staticmethod
    async def get_connection() -> aiosqlite.Connection:
        """Get a database connection"""
        db = await aiosqlite.connect(config.DB_PATH)
        db.row_factory = aiosqlite.Row
        await db.execute('PRAGMA journal_mode=WAL')
        await db.execute('PRAGMA foreign_keys=ON')
        return db
    
    @staticmethod
    async def initialize():
        """Initialize all database tables"""
        db = await Database.get_connection()
        
        try:
            # Guild settings
            await db.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    prefix TEXT DEFAULT '!',
                    log_channel_id INTEGER,
                    welcome_channel_id INTEGER,
                    leave_channel_id INTEGER,
                    welcome_message TEXT DEFAULT 'Welcome {user} to {server}!',
                    leave_message TEXT DEFAULT '{user} has left {server}.',
                    mute_role_id INTEGER,
                    admin_role_id INTEGER,
                    mod_role_id INTEGER,
                    auto_role_id INTEGER,
                    rules_channel_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Warnings system
            await db.execute('''
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    reason TEXT DEFAULT 'No reason provided',
                    type TEXT DEFAULT 'warning',
                    active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Mutes
            await db.execute('''
                CREATE TABLE IF NOT EXISTS mutes (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    moderator_id INTEGER,
                    reason TEXT DEFAULT 'No reason provided',
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    active INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, guild_id, start_time)
                )
            ''')
            
            # Bans history
            await db.execute('''
                CREATE TABLE IF NOT EXISTS ban_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    reason TEXT DEFAULT 'No reason provided',
                    action_type TEXT DEFAULT 'ban', -- 'ban', 'unban', 'softban'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Rules
            await db.execute('''
                CREATE TABLE IF NOT EXISTS rules (
                    guild_id INTEGER NOT NULL,
                    rule_number INTEGER NOT NULL,
                    rule_text TEXT NOT NULL,
                    category TEXT DEFAULT 'General',
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (guild_id, rule_number)
                )
            ''')
            
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS automod_config (
                    guild_id INTEGER PRIMARY KEY,
                    anti_spam_enabled INTEGER DEFAULT 1,
                    anti_spam_threshold INTEGER DEFAULT 5,
                    anti_spam_interval INTEGER DEFAULT 10,
                    anti_spam_action TEXT DEFAULT 'mute',
                    anti_spam_action_duration INTEGER DEFAULT 300,
                    
                    anti_link_enabled INTEGER DEFAULT 1,
                    anti_link_whitelist_roles TEXT DEFAULT '[]',
                    anti_link_whitelist_channels TEXT DEFAULT '[]',
                    anti_link_whitelist_links TEXT DEFAULT '[]',
                    anti_link_action TEXT DEFAULT 'delete',
                    
                    anti_swear_enabled INTEGER DEFAULT 1,
                    anti_swear_words TEXT DEFAULT '[]',
                    anti_swear_action TEXT DEFAULT 'delete',
                    
                    anti_mention_enabled INTEGER DEFAULT 1,
                    anti_mention_limit INTEGER DEFAULT 5,
                    anti_mention_action TEXT DEFAULT 'warn',
                    
                    anti_invite_enabled INTEGER DEFAULT 0,
                    anti_invite_whitelist_channels TEXT DEFAULT '[]',
                    
                    anti_mass_emoji_enabled INTEGER DEFAULT 0,
                    anti_mass_emoji_limit INTEGER DEFAULT 10,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS infractions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    type TEXT NOT NULL, -- 'warn', 'mute', 'kick', 'ban', 'softban', 'unmute', 'unban'
                    reason TEXT DEFAULT 'No reason provided',
                    duration TEXT, -- For temporary actions
                    active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP
                )
            ''')
            
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_by INTEGER NOT NULL,
                    uses INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, name)
                )
            ''')
            
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS reaction_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    emoji TEXT NOT NULL,
                    role_id INTEGER NOT NULL,
                    UNIQUE(message_id, emoji)
                )
            ''')
            
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'open', -- 'open', 'closed', 'archived'
                    category TEXT DEFAULT 'support',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP
                )
            ''')
            
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS levels (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 0,
                    messages INTEGER DEFAULT 0,
                    last_message TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, guild_id)
                )
            ''')
            
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS economy (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    wallet INTEGER DEFAULT 0,
                    bank INTEGER DEFAULT 100,
                    total_earned INTEGER DEFAULT 0,
                    last_daily TIMESTAMP,
                    last_work TIMESTAMP,
                    PRIMARY KEY (user_id, guild_id)
                )
            ''')
            
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS custom_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    command_name TEXT NOT NULL,
                    response TEXT NOT NULL,
                    created_by INTEGER NOT NULL,
                    uses INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, command_name)
                )
            ''')
            
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS premium (
                    guild_id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    tier TEXT DEFAULT 'free', -- 'free', 'premium', 'ultimate'
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.commit()
            log.info('Database tables initialized successfully')
            
        except Exception as e:
            log.error(f'Database initialization error: {e}')
            raise
        finally:
            await db.close()
    
    
    @staticmethod
    async def get_guild_settings(guild_id: int) -> Dict[str, Any]:
        """Get all settings for a guild"""
        db = await Database.get_connection()
        try:
            cursor = await db.execute('SELECT * FROM guild_settings WHERE guild_id = ?', (guild_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            
            await db.execute('INSERT INTO guild_settings (guild_id) VALUES (?)', (guild_id,))
            await db.commit()
            return {'guild_id': guild_id, 'prefix': '!', 'welcome_message': 'Welcome {user} to {server}!',
                    'leave_message': '{user} has left {server}.'}
        finally:
            await db.close()
    
    @staticmethod
    async def update_guild_settings(guild_id: int, **kwargs):
        """Update guild settings"""
        db = await Database.get_connection()
        try:
            set_clause = ', '.join([f'{key} = ?' for key in kwargs.keys()])
            values = list(kwargs.values()) + [guild_id]
            await db.execute(
                f'UPDATE guild_settings SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE guild_id = ?',
                values
            )
            await db.commit()
        finally:
            await db.close()
    
    
    @staticmethod
    async def add_warning(user_id: int, guild_id: int, moderator_id: int, reason: str = None) -> int:
        """Add a warning to a user"""
        db = await Database.get_connection()
        try:
            cursor = await db.execute(
                'INSERT INTO warnings (user_id, guild_id, moderator_id, reason) VALUES (?, ?, ?, ?)',
                (user_id, guild_id, moderator_id, reason or 'No reason provided')
            )
            
            await db.execute(
                'INSERT INTO infractions (user_id, guild_id, moderator_id, type, reason) VALUES (?, ?, ?, ?, ?)',
                (user_id, guild_id, moderator_id, 'warn', reason or 'No reason provided')
            )
            await db.commit()
            return cursor.lastrowid
        finally:
            await db.close()
    
    @staticmethod
    async def get_warnings(user_id: int, guild_id: int, active_only: bool = True) -> List[Dict]:
        """Get all warnings for a user"""
        db = await Database.get_connection()
        try:
            query = 'SELECT * FROM warnings WHERE user_id = ? AND guild_id = ?'
            if active_only:
                query += ' AND active = 1'
            query += ' ORDER BY created_at DESC'
            cursor = await db.execute(query, (user_id, guild_id))
            return [dict(row) for row in await cursor.fetchall()]
        finally:
            await db.close()
    
    @staticmethod
    async def clear_warnings(user_id: int, guild_id: int):
        """Clear all warnings for a user"""
        db = await Database.get_connection()
        try:
            await db.execute(
                'UPDATE warnings SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND guild_id = ?',
                (user_id, guild_id)
            )
            await db.commit()
        finally:
            await db.close()
    
    
    @staticmethod
    async def add_mute(user_id: int, guild_id: int, moderator_id: int, 
                       duration: Optional[int] = None, reason: str = None):
        """Add a mute record"""
        db = await Database.get_connection()
        try:
            from datetime import datetime, timedelta
            end_time = None
            if duration:
                end_time = datetime.utcnow() + timedelta(seconds=duration)
            
            await db.execute(
                'INSERT INTO mutes (user_id, guild_id, moderator_id, reason, end_time) VALUES (?, ?, ?, ?, ?)',
                (user_id, guild_id, moderator_id, reason or 'No reason provided', end_time)
            )
            
            await db.execute(
                'INSERT INTO infractions (user_id, guild_id, moderator_id, type, reason, duration) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, guild_id, moderator_id, 'mute', reason or 'No reason provided', 
                 f'{duration}s' if duration else 'permanent')
            )
            await db.commit()
        finally:
            await db.close()
    
    @staticmethod
    async def remove_mute(user_id: int, guild_id: int):
        """Remove a mute record"""
        db = await Database.get_connection()
        try:
            await db.execute(
                'UPDATE mutes SET active = 0 WHERE user_id = ? AND guild_id = ? AND active = 1',
                (user_id, guild_id)
            )
            await db.execute(
                'INSERT INTO infractions (user_id, guild_id, moderator_id, type, reason) VALUES (?, ?, ?, ?, ?)',
                (user_id, guild_id, 0, 'unmute', 'Automatic unmute')
            )
            await db.commit()
        finally:
            await db.close()
    
    @staticmethod
    async def get_active_mutes() -> List[Dict]:
        """Get all active mutes"""
        db = await Database.get_connection()
        try:
            cursor = await db.execute(
                'SELECT * FROM mutes WHERE active = 1 AND (end_time IS NULL OR end_time > CURRENT_TIMESTAMP)'
            )
            return [dict(row) for row in await cursor.fetchall()]
        finally:
            await db.close()
    
    
    @staticmethod
    async def add_rule(guild_id: int, rule_number: int, rule_text: str, 
                       category: str = 'General', creator_id: int = None):
        """Add a rule"""
        db = await Database.get_connection()
        try:
            await db.execute(
                'INSERT OR REPLACE INTO rules (guild_id, rule_number, rule_text, category, created_by) VALUES (?, ?, ?, ?, ?)',
                (guild_id, rule_number, rule_text, category, creator_id)
            )
            await db.commit()
        finally:
            await db.close()
    
    @staticmethod
    async def get_rules(guild_id: int) -> List[Dict]:
        """Get all rules for a guild"""
        db = await Database.get_connection()
        try:
            cursor = await db.execute(
                'SELECT * FROM rules WHERE guild_id = ? ORDER BY rule_number',
                (guild_id,)
            )
            return [dict(row) for row in await cursor.fetchall()]
        finally:
            await db.close()
    
    @staticmethod
    async def remove_rule(guild_id: int, rule_number: int):
        """Remove a rule"""
        db = await Database.get_connection()
        try:
            await db.execute(
                'DELETE FROM rules WHERE guild_id = ? AND rule_number = ?',
                (guild_id, rule_number)
            )
            
            rules = await Database.get_rules(guild_id)
            for idx, rule in enumerate(rules, 1):
                await db.execute(
                    'UPDATE rules SET rule_number = ? WHERE guild_id = ? AND rule_number = ?',
                    (idx, guild_id, rule['rule_number'])
                )
            await db.commit()
        finally:
            await db.close()
    
    
    @staticmethod
    async def get_automod_config(guild_id: int) -> Dict[str, Any]:
        """Get auto-mod configuration"""
        db = await Database.get_connection()
        try:
            cursor = await db.execute('SELECT * FROM automod_config WHERE guild_id = ?', (guild_id,))
            row = await cursor.fetchone()
            if row:
                config = dict(row)
                
                for key in ['anti_link_whitelist_roles', 'anti_link_whitelist_channels', 
                           'anti_link_whitelist_links', 'anti_swear_words',
                           'anti_invite_whitelist_channels']:
                    if config.get(key):
                        import json
                        config[key] = json.loads(config[key])
                    else:
                        config[key] = []
                return config
            
            await db.execute('INSERT INTO automod_config (guild_id) VALUES (?)', (guild_id,))
            await db.commit()
            return await Database.get_automod_config(guild_id)
        finally:
            await db.close()
    
    @staticmethod
    async def update_automod_config(guild_id: int, **kwargs):
        """Update auto-mod configuration"""
        db = await Database.get_connection()
        try:
            set_clause = ', '.join([f'{key} = ?' for key in kwargs.keys()])
            values = list(kwargs.values()) + [guild_id]
            await db.execute(
                f'UPDATE automod_config SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE guild_id = ?',
                values
            )
            await db.commit()
        finally:
            await db.close()
    
    
    @staticmethod
    async def get_user_infractions(user_id: int, guild_id: int, 
                                   infraction_type: str = None, 
                                   limit: int = 10) -> List[Dict]:
        """Get infractions for a user"""
        db = await Database.get_connection()
        try:
            query = 'SELECT * FROM infractions WHERE user_id = ? AND guild_id = ?'
            params = [user_id, guild_id]
            
            if infraction_type:
                query += ' AND type = ?'
                params.append(infraction_type)
            
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor = await db.execute(query, params)
            return [dict(row) for row in await cursor.fetchall()]
        finally:
            await db.close()
    
    
    @staticmethod
    async def create_tag(guild_id: int, name: str, content: str, creator_id: int):
        """Create a tag"""
        db = await Database.get_connection()
        try:
            await db.execute(
                'INSERT INTO tags (guild_id, name, content, created_by) VALUES (?, ?, ?, ?)',
                (guild_id, name.lower(), content, creator_id)
            )
            await db.commit()
        finally:
            await db.close()
    
    @staticmethod
    async def get_tag(guild_id: int, name: str) -> Optional[Dict]:
        """Get a tag by name"""
        db = await Database.get_connection()
        try:
            cursor = await db.execute(
                'SELECT * FROM tags WHERE guild_id = ? AND name = ?',
                (guild_id, name.lower())
            )
            row = await cursor.fetchone()
            if row:
                
                await db.execute('UPDATE tags SET uses = uses + 1 WHERE id = ?', (row['id'],))
                await db.commit()
                return dict(row)
            return None
        finally:
            await db.close()
    
    @staticmethod
    async def get_all_tags(guild_id: int) -> List[Dict]:
        """Get all tags for a guild"""
        db = await Database.get_connection()
        try:
            cursor = await db.execute(
                'SELECT name, uses FROM tags WHERE guild_id = ? ORDER BY name',
                (guild_id,)
            )
            return [dict(row) for row in await cursor.fetchall()]
        finally:
            await db.close()
    
    @staticmethod
    async def delete_tag(guild_id: int, name: str):
        """Delete a tag"""
        db = await Database.get_connection()
        try:
            await db.execute(
                'DELETE FROM tags WHERE guild_id = ? AND name = ?',
                (guild_id, name.lower())
            )
            await db.commit()
        finally:
            await db.close()
