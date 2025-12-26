import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os
import sys
import re  # Required for Regex
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

# --- REGEX PATTERN (UPDATED) ---
# Logic:
# 1. "i" = Starts with I
# 2. "( ha|'|)?" = Matches " ha" (I have), "'" (I've), or nothing (Ive)
# 3. "ve" = Must end with ve
# 4. "read the rules" = The core phrase
# 5. "( here)?" = Optional " here" at the end
# 6. "(\.|!)?" = Optional punctuation
VERIFY_PATTERN = re.compile(r"i( ha|'|)?ve read the rules( here)?(\.|!)?", re.IGNORECASE)

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
        super().__init__(timeout=60)
        self.log_msg_id = log_msg_id
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

    async def send_challenge(self, interaction: discord.Interaction, lang_code: str):
        equation_str, answer_num = generate_complicated_math()
        
        rule_key = str(answer_num)
        if rule_key in RULES:
            pending_verifications[interaction.user.id] = {
                "answer": RULES[rule_key],
                "lang": lang_code,
                "log_msg_id": self.log_msg_id
            }
            
            lang_data = LANGUAGES_CONFIG.get(lang_code, {})
            msg_template = lang_data.get("message", "Error: Message missing.")
            hint_template = lang_data.get("hint", "\n\n*(Copy and paste the rule text exactly as shown)*")
            
            message_text = msg_template.format(equation=equation_str)
            
            await interaction.response.send_message(message_text + hint_template, ephemeral=True)
        else:
            await interaction.response.send_message("System Error: Rule config missing.", ephemeral=True)

# Setup Bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
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
    success = load_config()
    if success:
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

@bot.tree.command(name="set_welcome_channel", description="Where welcome messages appear after success.")
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

    # 1. TRIGGER: REGEX CHECK
    # This now matches "i have", "i've", and "ive" (case insensitive)
    if VERIFY_PATTERN.fullmatch(message.content.strip()):
        
        if not allowed_channel_id or message.channel.id != allowed_channel_id: return

        age_delta = datetime.now(timezone.utc) - message.author.created_at
        if age_delta.days < MIN_AGE:
            try:
                await message.author.timeout(timedelta(days=7), reason="Account too new")
                await message.channel.send(f"🚫 {message.author.mention}, account < {MIN_AGE} days old. Timeout 7 days.")
            except discord.Forbidden:
                await message.channel.send("Account too new (Permission Error).")
            return

        # LOGGING
        log_msg_id = None
        if log_channel_id:
            log_channel = message.guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    log_msg = await log_channel.send(f"⏳ {message.author.mention} is attempting verification...")
                    log_msg_id = log_msg.id
                except Exception as e:
                    print(f"Log Error: {e}")

        await message.channel.send("Please select your language:", view=LanguageView(log_msg_id))
        return

    # 2. ANSWER CHECK
    if message.author.id in pending_verifications:
        if not allowed_channel_id or message.channel.id != allowed_channel_id: return

        user_data = pending_verifications[message.author.id]
        expected_text = user_data["answer"]
        lang_code = user_data["lang"]
        stored_log_id = user_data.get("log_msg_id")
        
        if message.content.strip() == expected_text.strip():
            if not verified_role_id:
                await message.channel.send("⚠️ Error: Role not set.")
                return

            role = message.guild.get_role(verified_role_id)
            if role:
                try:
                    await message.author.add_roles(role)
                    
                    await message.channel.send(f"Correct! You have been verified. ✅")
                    
                    welcome_msg = f"Welcome to the server, {message.author.mention}! Please remember: **English Only**."
                    if welcome_channel_id:
                        w_channel = message.guild.get_channel(welcome_channel_id)
                        if w_channel:
                            await w_channel.send(welcome_msg)
                    else:
                        await message.channel.send(welcome_msg)

                    if log_channel_id and stored_log_id:
                        l_channel = message.guild.get_channel(log_channel_id)
                        if l_channel:
                            try:
                                log_msg_obj = await l_channel.fetch_message(stored_log_id)
                                await log_msg_obj.edit(content=f"✅ {message.author.mention} **Verified!**")
                            except Exception:
                                pass

                    del pending_verifications[message.author.id]

                except discord.Forbidden:
                    await message.channel.send("Correct, but I lack permissions.")
            else:
                await message.channel.send("Error: Role deleted.")
        else:
            lang_data = LANGUAGES_CONFIG.get(lang_code, LANGUAGES_CONFIG['en'])
            error_msg = lang_data.get("error", "Incorrect rule text.")
            await message.channel.send(error_msg)

    await bot.process_commands(message)

bot.run(TOKEN)