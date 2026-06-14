import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import json
import os
import sys
import re
import asyncio
import difflib
import io
from PIL import Image
from datetime import datetime, timedelta, timezone
import dateparser
import pytz

# --- FILE PATHS ---
CONFIG_FILE = 'server_config.json'
USER_DATA_FILE = 'user_data.json'

# --- CONFIG LOADER ---
config_data = {}
TOKEN = ""
MIN_AGE = 7
RULES = {}
LANGUAGES_CONFIG = {}
user_profiles = {}
msg_translation_map = {} # Maps user_message_id -> bot_reply_message_id

def save_config():
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

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
    
    # Initialize default template dictionary
    default_signatures = {
        "1bd1593bebb3f298": "MrBeast X post",
        "1958cb09292b4b67": "Bonuses screen",
        "0ceee5a474c0c1d0": "Withdrawal success modal",
        "cacac75c785ccd98": "Smartphone transaction success"
    }

    if "scam_hashes" not in config_data:
        config_data["scam_hashes"] = default_signatures
        save_config()
    
    print(f"✅ Configuration loaded: {len(RULES)} rules, {len(LANGUAGES_CONFIG)} languages.")
    return True

def load_user_data():
    global user_profiles
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                user_profiles = json.load(f)
            print(f"✅ Loaded {len(user_profiles)} user profiles from '{USER_DATA_FILE}'.")
        except Exception as e:
            print(f"❌ Error loading '{USER_DATA_FILE}': {e}")
            user_profiles = {}
    else:
        user_profiles = {}

def save_user_data():
    try:
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_profiles, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Error saving '{USER_DATA_FILE}': {e}")

# Load configurations
if not load_config():
    sys.exit(1)
load_user_data()

# Data Storage
pending_verifications = {}

# --- REGEXES ---
VERIFY_PATTERN = re.compile(r"i( ha|'|)?ve read the rules( here)?(\.|!)?", re.IGNORECASE)

TIME_RE = re.compile(
    r'\b(?:1[0-2]|0?[1-9])(?::[0-5][0-9])?\s*[aApP][mM]\b|' # Matches "10:30 AM", "10am", "3 pm"
    r'\b(?:[01]?[0-9]|2[0-3]):[0-5][0-9]\b|'               # Matches "14:00", "22:30"
    r'\b(?:noon|midnight)\b',                              # Matches "noon", "midnight"
    re.IGNORECASE
)

DATE_RE = re.compile(
    r'\b(?:today|tomorrow|yesterday)\b|'
    r'\b(?:(?:this|next)\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat)\b|'
    r'(?<!\bthe\s)(?<!\ba\s)\b(?:(?:this|next)\s+)?sun\b|' # Matches "sun" but ignores "the sun" or "a sun"
    r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)(?:\s+\d{4})?\b|'
    r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}(?:\s+\d{4})?\b',
    re.IGNORECASE
)

NATURAL_TIME_RE = re.compile(
    r'\b(?:half|quarter|\d{1,2}(?:\s*mins?)?)\s+(?:past|to)\s+(?:noon|midnight|\d{1,2}(?::\d{2})?\s*(?:[ap]m)?)\b',
    re.IGNORECASE
)

# --- HELPER FUNCTIONS ---

def normalize_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_close_match(user_input, expected, threshold=0.85):
    norm_user = normalize_text(user_input)
    norm_expected = normalize_text(expected)
    matcher = difflib.SequenceMatcher(None, norm_user, norm_expected)
    return matcher.ratio() >= threshold

def get_lang_label(code):
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

def classify_segment(text):
    has_time = TIME_RE.search(text) is not None or NATURAL_TIME_RE.search(text) is not None
    has_date = DATE_RE.search(text) is not None
    if has_time and has_date:
        return "F"
    elif has_time:
        return "t"
    else:
        return "D"

def preprocess_natural_time(text):
    text = text.lower().strip()
    
    text = re.sub(r'\bhalf\s+past\s+midnight\b', '12:30 am', text)
    text = re.sub(r'\bquarter\s+past\s+midnight\b', '12:15 am', text)
    text = re.sub(r'\bquarter\s+to\s+midnight\b', '11:45 pm', text)
    text = re.sub(r'\bhalf\s+past\s+noon\b', '12:30 pm', text)
    text = re.sub(r'\bquarter\s+past\s+noon\b', '12:15 pm', text)
    text = re.sub(r'\bquarter\s+to\s+noon\b', '11:45 am', text)
    
    def half_past_repl(match):
        hour = int(match.group(1))
        suffix = match.group(2) or ""
        if 1 <= hour <= 12:
            return f"{hour}:30 {suffix}"
        return match.group(0)
    
    text = re.sub(r'\bhalf\s+past\s+(\d{1,2})\s*([ap]m)?\b', half_past_repl, text)
    
    def quarter_past_repl(match):
        hour = int(match.group(1))
        suffix = match.group(2) or ""
        if 1 <= hour <= 12:
            return f"{hour}:15 {suffix}"
        return match.group(0)
        
    text = re.sub(r'\bquarter\s+past\s+(\d{1,2})\s*([ap]m)?\b', quarter_past_repl, text)
    
    def quarter_to_repl(match):
        hour = int(match.group(1))
        suffix = match.group(2) or ""
        if 1 <= hour <= 12:
            prev_hour = 12 if hour == 1 else hour - 1
            return f"{prev_hour}:45 {suffix}"
        return match.group(0)
        
    text = re.sub(r'\bquarter\s+to\s+(\d{1,2})\s*([ap]m)?\b', quarter_to_repl, text)
    
    return text

def extract_and_parse_all(text):
    spans = []
    for r in [NATURAL_TIME_RE, TIME_RE, DATE_RE]:
        for m in r.finditer(text):
            spans.append(list(m.span()))
            
    if not spans:
        return []
        
    spans.sort(key=lambda x: x[0])
    
    merged = []
    for span in spans:
        if not merged:
            merged.append(span)
        else:
            prev_start, prev_end = merged[-1]
            curr_start, curr_end = span
            
            gap = text[prev_end:curr_start].strip().lower()

            prev_text = text[prev_start:prev_end]
            curr_text = text[curr_start:curr_end]
            
            prev_type = "time" if (TIME_RE.search(prev_text) or NATURAL_TIME_RE.search(prev_text)) else "date"
            curr_type = "time" if (TIME_RE.search(curr_text) or NATURAL_TIME_RE.search(curr_text)) else "date"
            
            is_different_type = (prev_type != curr_type)
            
            if curr_start <= prev_end:
                merged[-1][1] = max(prev_end, curr_end)
            elif is_different_type and gap in ["", "at", "on", "around", "at about", "in", "the"]:
                merged[-1][1] = max(prev_end, curr_end)
            else:
                merged.append(span)

    final_spans = []
    for span in merged:
        if not final_spans:
            final_spans.append(span)
        else:
            prev_start, prev_end = final_spans[-1]
            curr_start, curr_end = span
            if curr_start < prev_end:
                final_spans[-1][1] = max(prev_end, curr_end)
            else:
                final_spans.append(span)
                
    results = []
    for start, end in final_spans:
        segment_text = text[start:end]
        results.append((segment_text, classify_segment(segment_text)))
        
    return results

def add_to_translation_map(user_msg_id, bot_reply_id):
    if len(msg_translation_map) >= 1000:
        oldest_key = next(iter(msg_translation_map))
        msg_translation_map.pop(oldest_key, None)
    msg_translation_map[user_msg_id] = bot_reply_id

# --- DYNAMIC IMAGE DHASH MODERATION ---

def bytes_dhash(img_bytes, hash_size=8):
    try:
        with Image.open(io.BytesIO(img_bytes)) as img:
            img = img.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            pixels = list(img.getdata())
            
            difference = []
            for row in range(hash_size):
                for col in range(hash_size):
                    left = pixels[row * (hash_size + 1) + col]
                    right = pixels[row * (hash_size + 1) + col + 1]
                    difference.append(left > right)
            
            decimal_value = 0
            hex_string = []
            for index, value in enumerate(difference):
                if value:
                    decimal_value += 2 ** (index % 8)
                if (index % 8) == 7:
                    hex_string.append(hex(decimal_value)[2:].rjust(2, '0'))
                    decimal_value = 0
            return ''.join(hex_string)
    except Exception:
        return None

def hamming_distance(hash1, hash2):
    if len(hash1) != len(hash2):
        return 999
    return bin(int(hash1, 16) ^ int(hash2, 16)).count('1')

async def handle_scam_match(message, attachment, matched_hash, distance, label):
    try:
        await message.delete()
    except: pass

    author = message.author
    guild = message.guild
    gid = str(guild.id)
    g_settings = config_data.get('guild_settings', {}).get(gid, {})
    log_channel_id = g_settings.get('log_channel_id')
    
    ban_success = False
    try:
        await guild.ban(author, reason=f"Automated Ban: Compromised account posting scam layout ({label}).")
        ban_success = True
    except discord.Forbidden:
        pass

    if log_channel_id:
        log_channel = guild.get_channel(log_channel_id)
        if log_channel:
            embed = discord.Embed(
                description=f"User {author.mention} was automatically banned for uploading a verified malicious scam image template.",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name="Compromised Account Handled", icon_url=author.display_avatar.url)
            embed.add_field(name="Username", value=f"`{author}`", inline=True)
            embed.add_field(name="User ID", value=f"`{author.id}`", inline=True)
            embed.add_field(name="Detected Layout", value=f"**{label}**", inline=True)
            embed.add_field(name="Action Taken", value="⛔ **Banned**" if ban_success else "⚠️ **Failed to Ban (Missing Permissions)**", inline=False)
            embed.add_field(name="Filename Detected", value=f"`{attachment.filename}`", inline=True)
            embed.add_field(name="Match Confidence", value=f"**{(1 - distance/64)*100:.1f}%** (Dist: `{distance}/64`)", inline=True)
            
            try:
                await log_channel.send(embed=embed)
            except: pass

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
        super().__init__(timeout=300) 
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
            if interaction.user.id in pending_verifications:
                pending_verifications[interaction.user.id].update({
                    "answer": RULES[rule_key],
                    "lang": lang_code,
                    "timestamp": datetime.now() 
                })
            else:
                pending_verifications[interaction.user.id] = {
                    "answer": RULES[rule_key],
                    "lang": lang_code,
                    "log_msg_id": self.log_msg_id,
                    "timestamp": datetime.now(),
                    "guild_id": interaction.guild_id
                }
            
            # Update Staff Log
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

            lang_data = LANGUAGES_CONFIG.get(lang_code, {})
            msg_template = lang_data.get("message", "Error: Message missing.")
            hint_template = lang_data.get("hint", "\n\n*(Copy and paste the rule text)*")
            
            gid = str(interaction.guild_id)
            rules_channel_id = config_data.get('guild_settings', {}).get(gid, {}).get('rules_channel_id')
            rules_mention = f"<#{rules_channel_id}>" if rules_channel_id else "the rules channel"

            try:
                message_text = msg_template.format(equation=equation_str, rules_channel=rules_mention)
            except KeyError:
                message_text = msg_template.replace("{equation}", equation_str).replace("{rules_channel}", rules_mention)

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

# --- BACKGROUND TASKS ---

@tasks.loop(minutes=1) 
async def cleanup_pending():
    now = datetime.now()
    to_remove = []
    
    for user_id, data in pending_verifications.items():
        if "timestamp" in data:
            if (now - data["timestamp"]).total_seconds() > 360:
                to_remove.append((user_id, data))
    
    for user_id, data in to_remove:
        guild_id = data.get("guild_id")
        log_msg_id = data.get("log_msg_id")
        lang_code = data.get("lang")

        if guild_id:
            g_settings = config_data.get('guild_settings', {}).get(str(guild_id), {})
            channel_id = g_settings.get('channel_id')
            log_channel_id = g_settings.get('log_channel_id')
            
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
                        
                        lang_label = get_lang_label(lang_code) if lang_code else "No Selection"
                        await log_msg_obj.edit(content=f"❌ {user_text} **Timed Out** (Lang: {lang_label})")
                    except: pass

        del pending_verifications[user_id]
    
    if to_remove:
        print(f"🧹 Cleaned up {len(to_remove)} expired verifications.")

@tasks.loop(minutes=15)
async def check_birthdays():
    for user_id_str, profile in list(user_profiles.items()):
        bday_info = profile.get("birthday")
        if not bday_info:
            continue
            
        month = bday_info.get("month")
        day = bday_info.get("day")
        last_announced = bday_info.get("last_announced", 0)
        
        tz_name = profile.get("timezone")
        if not tz_name:
            continue
            
        try:
            tz = pytz.timezone(tz_name)
            now_user = datetime.now(tz)
        except Exception:
            continue
            
        if now_user.month == month and now_user.day == day:
            if last_announced != now_user.year:
                announced_somewhere = False
                user_id = int(user_id_str)
                
                for guild in bot.guilds:
                    member = guild.get_member(user_id)
                    if member:
                        gid = str(guild.id)
                        g_settings = config_data.get('guild_settings', {}).get(gid, {})
                        bday_channel_id = g_settings.get('birthday_channel_id')
                        
                        if bday_channel_id:
                            channel = guild.get_channel(bday_channel_id)
                            if channel:
                                try:
                                    await channel.send(f"🎉 **Happy Birthday** to {member.mention}! Wishing you an amazing day! 🎂🎈")
                                    announced_somewhere = True
                                except Exception as e:
                                    print(f"❌ Failed sending birthday in guild {guild.name}: {e}")
                
                if announced_somewhere:
                    user_profiles[user_id_str]["birthday"]["last_announced"] = now_user.year
                    save_user_data()

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        if not cleanup_pending.is_running():
            cleanup_pending.start()
        if not check_birthdays.is_running():
            check_birthdays.start()
        print(f"Synced commands.")
    except Exception as e:
        print(f"Failed sync: {e}")
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

# --- USER COMMANDS ---

@bot.tree.command(name="my_timezone", description="Set your personal timezone for automatic time translation.")
@app_commands.describe(timezone="Select or type your timezone (e.g. America/New_York, UTC, CET)")
async def mytimezone(interaction: discord.Interaction, timezone: str):
    try:
        pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        await interaction.response.send_message(
            f"❌ Unknown timezone: `{timezone}`. Please use a valid standard timezone name.",
            ephemeral=True
        )
        return
    
    user_id_str = str(interaction.user.id)
    if user_id_str not in user_profiles:
        user_profiles[user_id_str] = {}
        
    user_profiles[user_id_str]["timezone"] = timezone
    save_user_data()
    await interaction.response.send_message(f"✅ Your timezone has been saved as: **{timezone}**", ephemeral=True)

@mytimezone.autocomplete('timezone')
async def mytimezone_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    try:
        all_tzs = pytz.common_timezones
    except Exception:
        all_tzs = [
            "UTC", "US/Eastern", "US/Central", "US/Mountain", "US/Pacific",
            "Europe/London", "Europe/Paris", "Europe/Berlin", "Asia/Tokyo",
            "Asia/Kolkata", "Asia/Singapore", "Australia/Sydney", "America/Sao_Paulo"
        ]
    
    choices = [
        app_commands.Choice(name=tz, value=tz)
        for tz in all_tzs if current.lower() in tz.lower()
    ][:25]
    
    return choices

@bot.tree.command(name="my_birthday", description="Register your birthday to be celebrated.")
@app_commands.describe(month="Your birthday month", day="Your birthday day (1-31)")
@app_commands.choices(month=[
    app_commands.Choice(name="January", value=1),
    app_commands.Choice(name="February", value=2),
    app_commands.Choice(name="March", value=3),
    app_commands.Choice(name="April", value=4),
    app_commands.Choice(name="May", value=5),
    app_commands.Choice(name="June", value=6),
    app_commands.Choice(name="July", value=7),
    app_commands.Choice(name="August", value=8),
    app_commands.Choice(name="September", value=9),
    app_commands.Choice(name="October", value=10),
    app_commands.Choice(name="November", value=11),
    app_commands.Choice(name="December", value=12)
])
async def my_birthday(interaction: discord.Interaction, month: app_commands.Choice[int], day: int):
    user_id_str = str(interaction.user.id)
    
    if user_id_str not in user_profiles or "timezone" not in user_profiles[user_id_str]:
        await interaction.response.send_message(
            "⚠️ You must set your timezone using `/my_timezone` first before configuring your birthday.",
            ephemeral=True
        )
        return

    try:
        datetime(2000, month.value, day)
    except ValueError:
        await interaction.response.send_message(
            f"❌ Invalid date: **{month.name} {day}** does not exist.",
            ephemeral=True
        )
        return

    user_profiles[user_id_str]["birthday"] = {
        "month": month.value,
        "day": day,
        "last_announced": 0 
    }
    save_user_data()
    await interaction.response.send_message(f"🎉 Saved! Your birthday is set to **{month.name} {day}**.", ephemeral=True)

# --- ADMIN COMMANDS ---

@bot.tree.command(name="add_scam_template", description="Register an image as a malicious scam template layout.")
@app_commands.describe(
    image_file="Upload the target scam image",
    label="A descriptive label for this layout (e.g., 'X Post', 'Success screen variant')"
)
@app_commands.default_permissions(administrator=True)
async def add_scam_template(interaction: discord.Interaction, image_file: discord.Attachment, label: str):
    if not any(image_file.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
        await interaction.response.send_message("❌ Uploaded file must be an image format (.png, .jpg, .jpeg, .webp).", ephemeral=True)
        return
        
    await interaction.response.defer(ephemeral=True)
    try:
        img_bytes = await image_file.read()
        h = bytes_dhash(img_bytes)
        if h:
            if "scam_hashes" not in config_data or isinstance(config_data["scam_hashes"], list):
                config_data["scam_hashes"] = {}
                
            if h in config_data["scam_hashes"]:
                await interaction.followup.send(f"⚠️ This exact layout is already registered as: **{config_data['scam_hashes'][h]}**", ephemeral=True)
                return
                
            config_data["scam_hashes"][h] = label
            save_config()
            await interaction.followup.send(f"✅ Successfully registered scam layout template!\n\n• **Label**: {label}\n• **Hash**: `{h}`", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to resolve image properties.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="remove_scam_template", description="Remove a scam template layout hash from the tracking list.")
@app_commands.describe(scam_hash="The exact 16-character hex hash of the template")
@app_commands.default_permissions(administrator=True)
async def remove_scam_template(interaction: discord.Interaction, scam_hash: str):
    if "scam_hashes" in config_data and scam_hash in config_data["scam_hashes"]:
        label = config_data["scam_hashes"].pop(scam_hash)
        save_config()
        await interaction.response.send_message(f"✅ Removed scam template: **{label}** (`{scam_hash}`)", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Hash not found in the config database.", ephemeral=True)

@bot.tree.command(name="list_scam_templates", description="List all registered scam template layout hashes.")
@app_commands.default_permissions(administrator=True)
async def list_scam_templates(interaction: discord.Interaction):
    scam_hashes = config_data.get("scam_hashes", {})
    if not scam_hashes:
        await interaction.response.send_message("ℹ️ No scam templates are registered yet.", ephemeral=True)
        return
        
    hash_list = "\n".join(f"• `{h}`: **{label}**" for h, label in scam_hashes.items())
    await interaction.response.send_message(f"🔐 **Registered Scam Layout Templates ({len(scam_hashes)}):**\n{hash_list}", ephemeral=True)

@bot.tree.command(name="set_birthday_channel", description="Set the channel where birthday announcements will be posted.")
@app_commands.default_permissions(administrator=True)
async def set_birthday_channel(interaction: discord.Interaction):
    gid = str(interaction.guild_id)
    if "guild_settings" not in config_data: config_data["guild_settings"] = {}
    if gid not in config_data['guild_settings']: config_data['guild_settings'][gid] = {}
    
    config_data['guild_settings'][gid]['birthday_channel_id'] = interaction.channel.id
    save_config()
    await interaction.response.send_message(f"✅ Birthday channel set to: {interaction.channel.mention}", ephemeral=True)

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

@bot.tree.command(name="set_welcome_extra", description="Add extra text/links after the default welcome message.")
@app_commands.describe(text="The text to append (leave empty to clear). Supports channel links like #general.")
@app_commands.default_permissions(administrator=True)
async def set_welcome_extra(interaction: discord.Interaction, text: str = None):
    gid = str(interaction.guild_id)
    if "guild_settings" not in config_data: config_data["guild_settings"] = {}
    if gid not in config_data['guild_settings']: config_data['guild_settings'][gid] = {}
    
    if text:
        config_data['guild_settings'][gid]['welcome_extra'] = text
        save_config()
        await interaction.response.send_message(f"✅ Welcome message extra text updated:\n\n*...English Only.*\n**{text}**", ephemeral=True)
    else:
        config_data['guild_settings'][gid]['welcome_extra'] = ""
        save_config()
        await interaction.response.send_message(f"✅ Welcome message extra text **removed**.", ephemeral=True)

@bot.tree.command(name="set_log_channel", description="Where staff see verification progress.")
@app_commands.default_permissions(administrator=True)
async def set_log_channel(interaction: discord.Interaction):
    gid = str(interaction.guild_id)
    if "guild_settings" not in config_data: config_data["guild_settings"] = {}
    if gid not in config_data['guild_settings']: config_data['guild_settings'][gid] = {}
    config_data['guild_settings'][gid]['log_channel_id'] = interaction.channel.id
    save_config()
    await interaction.response.send_message(f"✅ Log/Progress Channel set to: {interaction.channel.mention}", ephemeral=True)

@bot.tree.command(name="set_rules_channel", description="The channel containing the rules list.")
@app_commands.default_permissions(administrator=True)
async def set_rules_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    gid = str(interaction.guild_id)
    if "guild_settings" not in config_data: config_data["guild_settings"] = {}
    if gid not in config_data['guild_settings']: config_data['guild_settings'][gid] = {}
    
    config_data['guild_settings'][gid]['rules_channel_id'] = channel.id
    save_config()
    await interaction.response.send_message(f"✅ Rules Channel set to: {channel.mention}", ephemeral=True)

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
    r_chan = get_status(settings.get('rules_channel_id'), interaction.guild.get_channel)
    b_chan = get_status(settings.get('birthday_channel_id'), interaction.guild.get_channel)
    role_s = get_status(settings.get('role_id'), interaction.guild.get_role)
    
    extra_txt = settings.get('welcome_extra')
    extra_status = f"📝 **Set:** \"{extra_txt[:50]}...\"" if extra_txt else "❌ Not Set"

    embed = discord.Embed(title="🔐 Verification Configuration", color=discord.Color.blue())
    embed.add_field(name="Verification Channel", value=v_chan, inline=True)
    embed.add_field(name="Welcome Channel", value=w_chan, inline=True)
    embed.add_field(name="Log Channel", value=l_chan, inline=True)
    embed.add_field(name="Rules Channel", value=r_chan, inline=True)
    embed.add_field(name="Birthday Channel", value=b_chan, inline=True)
    embed.add_field(name="Verified Role", value=role_s, inline=True)
    embed.add_field(name="Welcome Extra Text", value=extra_status, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- MAIN LOGIC ---

@bot.event
async def on_message_edit(before, after):
    if after.author.bot: return
    if before.content == after.content: return

    g_settings = config_data.get('guild_settings', {}).get(str(after.guild.id), {})
    allowed_channel_id = g_settings.get('channel_id')
    is_verification_channel = (allowed_channel_id is not None) and (after.channel.id == allowed_channel_id)
    if is_verification_channel: return

    user_id_str = str(after.author.id)
    user_tz_name = user_profiles.get(user_id_str, {}).get("timezone")
    
    bot_reply_id = msg_translation_map.get(after.id)

    parsed_segments = []
    if user_tz_name:
        parsed_segments = extract_and_parse_all(after.content)

    epochs = []
    if parsed_segments:
        try:
            user_tz = pytz.timezone(user_tz_name)
            now_user_time = datetime.now(user_tz)
            
            for segment_text, format_type in parsed_segments:
                preprocessed_text = preprocess_natural_time(segment_text)
                settings = {
                    'PREFER_DATES_FROM': 'future',
                    'RELATIVE_BASE': now_user_time.replace(tzinfo=None),
                    'TIMEZONE': user_tz_name,
                    'RETURN_AS_TIMEZONE_AWARE': True
                }
                parsed_dt = dateparser.parse(preprocessed_text, settings=settings)
                if parsed_dt:
                    epoch = int(parsed_dt.timestamp())
                    epochs.append((epoch, format_type))
        except Exception:
            pass

    if epochs:
        formatted_times = [f"<t:{epoch}:{fmt}>" for epoch, fmt in epochs]
        if len(formatted_times) == 1:
            reply_text = f"The user means {formatted_times[0]}"
        elif len(formatted_times) == 2:
            reply_text = f"The user means {formatted_times[0]} or {formatted_times[1]}"
        else:
            reply_text = f"The user means {', '.join(formatted_times[:-1])}, or {formatted_times[-1]}"

        if bot_reply_id:
            try:
                msg = await after.channel.fetch_message(bot_reply_id)
                await msg.edit(content=reply_text)
            except discord.NotFound:
                try:
                    reply = await after.reply(reply_text, mention_author=False)
                    msg_translation_map[after.id] = reply.id
                except: pass
            except: pass
        else:
            try:
                reply = await after.reply(reply_text, mention_author=False)
                add_to_translation_map(after.id, reply.id)
            except: pass
    else:
        if bot_reply_id:
            try:
                msg = await after.channel.fetch_message(bot_reply_id)
                await msg.delete()
            except: pass
            msg_translation_map.pop(after.id, None)

@bot.event
async def on_message(message):
    if message.author.bot: return

    # 1. SCAN FOR MALICIOUS SCAM ATTACHMENTS
    if message.attachments:
        scam_hashes = config_data.get("scam_hashes", {})
        if scam_hashes:
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                    try:
                        img_bytes = await attachment.read()
                        h = bytes_dhash(img_bytes)
                        if h:
                            for template_hash, label in scam_hashes.items():
                                dist = hamming_distance(h, template_hash)
                                if dist <= 12: 
                                    await handle_scam_match(message, attachment, h, dist, label)
                                    return
                    except Exception as e:
                        print(f"❌ Error scanning attachment: {e}")

    g_settings = config_data.get('guild_settings', {}).get(str(message.guild.id), {})
    allowed_channel_id = g_settings.get('channel_id')
    welcome_channel_id = g_settings.get('welcome_channel_id')
    log_channel_id = g_settings.get('log_channel_id')
    verified_role_id = g_settings.get('role_id')
    welcome_extra = g_settings.get('welcome_extra', "")

    # 2. TRIGGER
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

    # 3. ANSWER CHECK
    if message.author.id in pending_verifications:
        if not allowed_channel_id or message.channel.id != allowed_channel_id: return
        try: await message.delete()
        except: pass

        user_data = pending_verifications[message.author.id]
        if user_data["answer"] is None: return

        expected_text = user_data["answer"]
        lang_code = user_data["lang"]
        stored_log_id = user_data.get("log_msg_id")
        
        if is_close_match(message.content, expected_text):
            if not verified_role_id:
                await message.channel.send("⚠️ Error: Role not set.", delete_after=10)
                return

            role = message.guild.get_role(verified_role_id)
            if role:
                try:
                    await message.author.add_roles(role)
                    await message.channel.send(f"✅ {message.author.mention} has been verified.", delete_after=5)
                    
                    base_welcome = f"Welcome to the server, {message.author.mention}! Please remember: **English Only**."
                    
                    if welcome_extra:
                        final_welcome = f"{base_welcome}\n{welcome_extra}"
                    else:
                        final_welcome = base_welcome

                    if welcome_channel_id:
                        w_channel = message.guild.get_channel(welcome_channel_id)
                        if w_channel: await w_channel.send(final_welcome)
                    else:
                        await message.channel.send(final_welcome)

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
            return
        else:
            lang_data = LANGUAGES_CONFIG.get(lang_code, LANGUAGES_CONFIG['en'])
            error_msg = lang_data.get("error", "Incorrect rule text.")
            
            rules_channel_id = config_data.get('guild_settings', {}).get(str(message.guild.id), {}).get('rules_channel_id')
            rules_mention = f"<#{rules_channel_id}>" if rules_channel_id else "the rules channel"
            
            try: error_msg = error_msg.format(rules_channel=rules_mention)
            except: pass

            await message.channel.send(
                f"❌ {message.author.mention} {error_msg}", 
                delete_after=30
            )
            return

    # 4. TIMEZONE TRANSLATION SYSTEM
    is_verification_channel = (allowed_channel_id is not None) and (message.channel.id == allowed_channel_id)
    if not is_verification_channel:
        user_id_str = str(message.author.id)
        user_tz_name = user_profiles.get(user_id_str, {}).get("timezone")
        
        if user_tz_name:
            parsed_segments = extract_and_parse_all(message.content)
            epochs = []
            
            if parsed_segments:
                try:
                    user_tz = pytz.timezone(user_tz_name)
                    now_user_time = datetime.now(user_tz)
                    
                    for segment_text, format_type in parsed_segments:
                        preprocessed_text = preprocess_natural_time(segment_text)
                        settings = {
                            'PREFER_DATES_FROM': 'future',
                            'RELATIVE_BASE': now_user_time.replace(tzinfo=None),
                            'TIMEZONE': user_tz_name,
                            'RETURN_AS_TIMEZONE_AWARE': True
                        }
                        
                        parsed_dt = dateparser.parse(preprocessed_text, settings=settings)
                        if parsed_dt:
                            epoch = int(parsed_dt.timestamp())
                            epochs.append((epoch, format_type))
                except Exception:
                    pass
            
            if epochs:
                formatted_times = [f"<t:{epoch}:{fmt}>" for epoch, fmt in epochs]
                if len(formatted_times) == 1:
                    reply_text = f"The user means {formatted_times[0]}"
                elif len(formatted_times) == 2:
                    reply_text = f"The user means {formatted_times[0]} or {formatted_times[1]}"
                else:
                    reply_text = f"The user means {', '.join(formatted_times[:-1])}, or {formatted_times[-1]}"
                    
                try:
                    reply = await message.reply(reply_text, mention_author=False)
                    add_to_translation_map(message.id, reply.id)
                except Exception:
                    pass

    await bot.process_commands(message)

bot.run(TOKEN)