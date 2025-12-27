import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import json
import os
import sys
import re
import asyncio
from datetime import datetime, timedelta, timezone

# --- FILE PATH ---
CONFIG_FILE = 'server_config.json'

# --- CONFIG LOADER ---
config_data = {}
TOKEN = ""
MIN_AGE = 7
RULES = {}
LANGUAGES_CONFIG = {}

def load_config():
    global config_data, TOKEN, MIN_AGE, RULES, LANGUAGES_CONFIG
    
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ CRITICAL ERROR: '{CONFIG_FILE}' not found.")
        return False
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON ERROR: {e}")
        return False

    if not config_data.get("bot_token") or config_data["bot_token"] == "PASTE_YOUR_BOT_TOKEN_HERE":
        print("❌ Invalid Token.")
        return False
        
    if "languages" not in config_data:
        print("❌ Missing 'languages' section.")
        return False

    TOKEN = config_data['bot_token']
    MIN_AGE = config_data.get('min_account_age_days', 7)
    RULES = config_data.get('rules', {})
    LANGUAGES_CONFIG = config_data.get('languages', {})
    
    print(f"✅ Configuration loaded: {len(RULES)} rules, {len(LANGUAGES_CONFIG)} languages.")
    return True

if not load_config():
    sys.exit(1)

# Data Storage
pending_verifications = {}

# Regex
VERIFY_PATTERN = re.compile(r"i( ha|'|)?ve read the rules( here)?(\.|!)?", re.IGNORECASE)

# --- HELPER FUNCTIONS ---

def normalize_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_lang_label(code):
    """Returns the pretty label (e.g. English 🇺🇸) for a code."""
    return LANGUAGES_CONFIG.get(code, {}).get("label", code)

def generate_complicated_math():
    if not RULES: return "1 + 0", 1 
    rule_keys = [int(k) for k in RULES.keys() if k.isdigit()]
    max_rule = max(rule_keys) if rule_keys else 12
    target = random.randint(1, max_rule)
    
    operation = random.choice(['-', '-', '-', '/', '/', '/', '*', '+']) 
    
    if operation == '-':
        b = random.randint(100, 999)
        a = target + b
        equation = f"{a} - {b}"
    elif operation == '/':
        divisor = random.randint(6, 60)
        dividend = target * divisor
        equation = f"{dividend} ÷ {divisor}"
    elif operation == '*':
        factors = []
        for i in range(1, target + 1):
            if target % i == 0: factors.append((i, target // i))
        a, b = random.choice(factors) if factors else (1, target)
        equation = f"{a} × {b}"
    else:
        if target == 1: equation = "0 + 1"
        else:
            a = random.randint(1, target - 1)
            b = target - a
            equation = f"{a} + {b}"

    return equation, target

# --- DYNAMIC MULTI-DROPDOWN LOGIC ---

class LanguageSelect(discord.ui.Select):
    def __init__(self, parent_view, options_chunk, part_number):
        super().__init__(
            placeholder=f"Select Language (Part {part_number})...",
            min_values=1,
            max_values=1,
            options=options_chunk
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        lang_code = self.values[0]
        await self.parent_view.send_challenge(interaction, lang_code)

class LanguageView(discord.ui.View):
    def __init__(self, log_msg_id=None):
        super().__init__(timeout=300) # 5 Minutes UI Timeout
        self.log_msg_id = log_msg_id
        self.message = None 
        self.create_dropdowns()

    def create_dropdowns(self):
        all_options = []
        for code, details in LANGUAGES_CONFIG.items():
            label = details.get("label", code)
            all_options.append(discord.SelectOption(label=label[:100], value=code))

        chunk_size = 25
        chunks = [all_options[i:i + chunk_size] for i in range(0, len(all_options), chunk_size)]

        for index, chunk in enumerate(chunks):
            select_menu = LanguageSelect(self, chunk, index + 1)
            self.add_item(select_menu)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except: pass

    async def send_challenge(self, interaction: discord.Interaction, lang_code: str):
        equation_str, answer_num = generate_complicated_math()
        
        rule_key = str(answer_num)
        if rule_key in RULES:
            # UPDATE existing entry
            if interaction.user.id in pending_verifications:
                pending_verifications[interaction.user.id].update({
                    "answer": RULES[rule_key],
                    "lang": lang_code,
                    "timestamp": datetime.now() 
                })
            else:
                # Fallback if entry missing
                pending_verifications[interaction.user.id] = {
                    "answer": RULES[rule_key],
                    "lang": lang_code,
                    "log_msg_id": self.log_msg_id,
                    "timestamp": datetime.now(),
                    "guild_id": interaction.guild_id
                }
            
            # --- UPDATE STAFF LOG TO SHOW LANGUAGE SELECTION ---
            if self.log_msg_id:
                gid = str(interaction.guild_id)
                g_settings = config_data.get('guild_settings', {}).get(gid, {})
                log_channel_id = g_settings.get('log_channel_id')
                if log_channel_id:
                    chan = interaction.guild.get_channel(log_channel_id)
                    if chan:
                        try:
                            msg = await chan.fetch_message(self.log_msg_id)
                            lang_label = get_lang_label(lang_code)
                            await msg.edit(content=f"⏳ {interaction.user.mention} is verifying in **{lang_label}**...")
                        except: pass
            # ---------------------------------------------------

            lang_data = LANGUAGES_CONFIG.get(lang_code, {})
            msg_template = lang_data.get("message", "Error: Message missing.")
            hint_template = lang_data.get("hint", "\n\n*(Copy and paste the rule text)*")
            
            message_text = msg_template.format(equation=equation_str)
            
            await interaction.response.send_message(message_text + hint_template, ephemeral=True)
            try:
                await interaction.message.delete()
            except: pass
        else:
            await interaction.response.send_message("System Error: Rule config missing.", ephemeral=True)

# Setup Bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# --- BACKGROUND TASK (CLEANUP) ---

@tasks.loop(minutes=1) 
async def cleanup_pending():
    now = datetime.now()
    to_remove = []
    
    # 1. Identify expired users (> 6 mins)
    for user_id, data in pending_verifications.items():
        if "timestamp" in data:
            if (now - data["timestamp"]).total_seconds() > 360:
                to_remove.append((user_id, data))
    
    # 2. Process removals
    for user_id, data in to_remove:
        guild_id = data.get("guild_id")
        log_msg_id = data.get("log_msg_id")
        lang_code = data.get("lang") # Get the language they were using

        if guild_id:
            g_settings = config_data.get('guild_settings', {}).get(str(guild_id), {})
            channel_id = g_settings.get('channel_id')
            log_channel_id = g_settings.get('log_channel_id')
            
            # A. Notify User
            if channel_id:
                channel = bot.get_channel(channel_id)
                if channel:
                    try:
                        user = await bot.fetch_user(user_id)
                        await channel.send(
                            f"⏰ {user.mention}, verification timed out. Type **'I have read the rules'** to retry.",
                            delete_after=30
                        )
                    except: pass
            
            # B. Update Log Message
            if log_channel_id and log_msg_id:
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    try:
                        log_msg_obj = await log_channel.fetch_message(log_msg_id)
                        
                        try:
                            user = await bot.fetch_user(user_id)
                            user_text = user.mention
                        except:
                            user_text = f"User {user_id}"
                        
                        # Show which language they failed on
                        lang_label = get_lang_label(lang_code) if lang_code else "No Selection"
                        await log_msg_obj.edit(content=f"❌ {user_text} **Timed Out** (Lang: {lang_label})")
                    except discord.NotFound:
                        pass 
                    except Exception as e:
                        print(f"Log update failed: {e}")

        del pending_verifications[user_id]
    
    if to_remove:
        print(f"🧹 Cleaned up {len(to_remove)} expired verifications.")

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        if not cleanup_pending.is_running():
            cleanup_pending.start()
        print(f"Synced commands.")
    except Exception as e:
        print(f"Failed sync: {e}")
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

def save_config():
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

# --- ADMIN COMMANDS ---

@bot.tree.command(name="reload", description="Reloads config file.")
@app_commands.default_permissions(administrator=True)
async def reload(interaction: discord.Interaction):
    if load_config():
        await interaction.response.send_message(f"✅ Configuration Reloaded!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Reload Failed.", ephemeral=True)

@bot.tree.command(name="set_verification_channel", description="Where users type commands.")
@app_commands.default_permissions(administrator=True)
async def set_verification_channel(interaction: discord.Interaction):
    gid = str(interaction.guild_id)
    if "guild_settings" not in config_data: config_data["guild_settings"] = {}
    if gid not in config_data['guild_settings']: config_data['guild_settings'][gid] = {}
    config_data['guild_settings'][gid]['channel_id'] = interaction.channel.id
    save_config()
    await interaction.response.send_message(f"✅ Verification Channel set to: {interaction.channel.mention}", ephemeral=True)

@bot.tree.command(name="set_welcome_channel", description="Where welcome messages appear.")
@app_commands.default_permissions(administrator=True)
async def set_welcome_channel(interaction: discord.Interaction):
    gid = str(interaction.guild_id)
    if "guild_settings" not in config_data: config_data["guild_settings"] = {}
    if gid not in config_data['guild_settings']: config_data['guild_settings'][gid] = {}
    config_data['guild_settings'][gid]['welcome_channel_id'] = interaction.channel.id
    save_config()
    await interaction.response.send_message(f"✅ Welcome Channel set to: {interaction.channel.mention}", ephemeral=True)

@bot.tree.command(name="set_log_channel", description="Where staff see verification progress.")
@app_commands.default_permissions(administrator=True)
async def set_log_channel(interaction: discord.Interaction):
    gid = str(interaction.guild_id)
    if "guild_settings" not in config_data: config_data["guild_settings"] = {}
    if gid not in config_data['guild_settings']: config_data['guild_settings'][gid] = {}
    config_data['guild_settings'][gid]['log_channel_id'] = interaction.channel.id
    save_config()
    await interaction.response.send_message(f"✅ Log/Progress Channel set to: {interaction.channel.mention}", ephemeral=True)

@bot.tree.command(name="set_role", description="Set verified role.")
@app_commands.default_permissions(administrator=True)
async def set_role(interaction: discord.Interaction, role: discord.Role):
    if role.permissions.administrator:
        await interaction.response.send_message("⚠️ Unsafe: Cannot use Admin role.", ephemeral=True)
        return
    gid = str(interaction.guild_id)
    if "guild_settings" not in config_data: config_data["guild_settings"] = {}
    if gid not in config_data['guild_settings']: config_data['guild_settings'][gid] = {}
    config_data['guild_settings'][gid]['role_id'] = role.id
    save_config()
    await interaction.response.send_message(f"✅ Role set: **{role.name}**", ephemeral=True)

@bot.tree.command(name="check_config", description="View current config.")
@app_commands.default_permissions(administrator=True)
async def check_config(interaction: discord.Interaction):
    gid = str(interaction.guild_id)
    settings = config_data.get('guild_settings', {}).get(gid, {})
    
    def get_status(obj_id, type_func):
        if not obj_id: return "❌ Not Set"
        obj = type_func(obj_id)
        return f"✅ {obj.mention}" if obj else f"⚠️ ID `{obj_id}` (Deleted)"

    v_chan = get_status(settings.get('channel_id'), interaction.guild.get_channel)
    w_chan = get_status(settings.get('welcome_channel_id'), interaction.guild.get_channel)
    l_chan = get_status(settings.get('log_channel_id'), interaction.guild.get_channel)
    role_s = get_status(settings.get('role_id'), interaction.guild.get_role)

    embed = discord.Embed(title="🔐 Verification Configuration", color=discord.Color.blue())
    embed.add_field(name="Verification Channel", value=v_chan, inline=True)
    embed.add_field(name="Welcome Channel", value=w_chan, inline=True)
    embed.add_field(name="Log Channel", value=l_chan, inline=True)
    embed.add_field(name="Verified Role", value=role_s, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- MAIN LOGIC ---

@bot.event
async def on_message(message):
    if message.author.bot: return

    g_settings = config_data.get('guild_settings', {}).get(str(message.guild.id), {})
    allowed_channel_id = g_settings.get('channel_id')
    welcome_channel_id = g_settings.get('welcome_channel_id')
    log_channel_id = g_settings.get('log_channel_id')
    verified_role_id = g_settings.get('role_id')

    # 1. TRIGGER
    if VERIFY_PATTERN.fullmatch(message.content.strip()):
        if not allowed_channel_id or message.channel.id != allowed_channel_id: return
        try: await message.delete()
        except: pass

        age_delta = datetime.now(timezone.utc) - message.author.created_at
        if age_delta.days < MIN_AGE:
            try:
                await message.author.timeout(timedelta(days=7), reason="Account too new")
                warn = await message.channel.send(f"🚫 {message.author.mention}, account < {MIN_AGE} days old. Timeout 7 days.")
                await asyncio.sleep(10)
                await warn.delete()
            except discord.Forbidden:
                await message.channel.send("Account too new (Permission Error).", delete_after=5)
            return

        log_msg_id = None
        if log_channel_id:
            log_channel = message.guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    log_msg = await log_channel.send(f"⏳ {message.author.mention} is attempting verification...")
                    log_msg_id = log_msg.id
                except: pass

        # Store immediately (default lang is None)
        pending_verifications[message.author.id] = {
            "answer": None, 
            "lang": None,
            "log_msg_id": log_msg_id,
            "timestamp": datetime.now(),
            "guild_id": message.guild.id
        }

        view = LanguageView(log_msg_id)
        prompt_msg = await message.channel.send(f"Hello {message.author.mention}, please select your language:", view=view)
        view.message = prompt_msg
        return

    # 2. ANSWER CHECK
    if message.author.id in pending_verifications:
        if not allowed_channel_id or message.channel.id != allowed_channel_id: return
        try: await message.delete()
        except: pass

        user_data = pending_verifications[message.author.id]
        
        # Ignore if math hasn't been generated yet (user skipped buttons)
        if user_data["answer"] is None:
            return

        expected_text = user_data["answer"]
        lang_code = user_data["lang"]
        stored_log_id = user_data.get("log_msg_id")
        
        if normalize_text(message.content) == normalize_text(expected_text):
            if not verified_role_id:
                await message.channel.send("⚠️ Error: Role not set.", delete_after=10)
                return

            role = message.guild.get_role(verified_role_id)
            if role:
                try:
                    await message.author.add_roles(role)
                    # Temp success msg
                    await message.channel.send(f"✅ {message.author.mention} has been verified.", delete_after=5)
                    
                    welcome_msg = f"Welcome to the server, {message.author.mention}! Please remember: **English Only**."
                    if welcome_channel_id:
                        w_channel = message.guild.get_channel(welcome_channel_id)
                        if w_channel: await w_channel.send(welcome_msg)
                    else:
                        await message.channel.send(welcome_msg)

                    # Update Log to VERIFIED with Language info
                    if log_channel_id and stored_log_id:
                        l_channel = message.guild.get_channel(log_channel_id)
                        if l_channel:
                            try:
                                log_msg_obj = await l_channel.fetch_message(stored_log_id)
                                lang_label = get_lang_label(lang_code)
                                await log_msg_obj.edit(content=f"✅ {message.author.mention} **Verified!** ({lang_label})")
                            except: pass

                    del pending_verifications[message.author.id]

                except discord.Forbidden:
                    await message.channel.send("Correct, but I lack permissions to give the role.", delete_after=10)
            else:
                await message.channel.send("Error: Role deleted.", delete_after=10)
        else:
            lang_data = LANGUAGES_CONFIG.get(lang_code, LANGUAGES_CONFIG['en'])
            error_msg = lang_data.get("error", "Incorrect rule text.")
            await message.channel.send(
                f"❌ {message.author.mention} {error_msg}\n*(Check punctuation and ensure it is English)*", 
                delete_after=30
            )

    await bot.process_commands(message)

bot.run(TOKEN)