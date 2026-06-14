# Sphere Matchers Verification & Utility Discord Bot

A highly configurable, multi-language Discord bot designed to secure your server. It forces users to prove they have read the rules by solving a math problem and copy-pasting the specific English rule text.

It mainly features **Regex pattern matching**, **Anti-Raid account age checks**, **Traffic Logging**, **Fuzzy Text Matching**, **Perceptual hashing (dHash) based image recognisation ban**, **Time Zone based timestamp generator**, and **Birthday announcements**.

## Key Features

### Security & Verification
*   **Smart Regex Trigger:** Detects flexible variations like *"I have read the rules"*, *"I've read the rules"*, *"Ive read the rules"*, and allows optional punctuation or "here" at the end.
*   **Math Challenge:** Generates random integer-only equations (Addition, Subtraction, Multiplication, Division) using clear symbols (`×`, `÷`).
*   **Fuzzy Rule Matching:** Users must copy-paste the English rule text, but the bot is forgiving of **punctuation, capitalization, and extra spaces**.
*   **Anti-Raid / Account Age:** Automatically places accounts created less than **7 days** ago (configurable) into a **1-week Timeout**.
*   **Perceptual Image Scan for ban**: Scans file attachments in real-time using Perceptual Difference Hashing (dHash). If a compromised account uploads a known scam image layout, the bot immediately deletes the message, bans the user, and posts a detailed match report in your logging channel. Thanks a lot MrBreast.

### Multi-Language Support
*   **Dynamic Dropdowns:** Users select their language from a dropdown menu.
*   **Auto-Scaling:** Automatically handles unlimited languages by creating multiple dropdown menus if the list exceeds Discord's limit (25 per menu).
*   **Contextual Messages:** Messages can dynamically link to your rules channel using the `{rules_channel}` placeholder.

### Administration & Hygiene
*   **Chat Hygiene:** The bot **auto-deletes** user triggers, wrong answers, and verification menus to keep your channel clean.
*   **Detailed Logging:** Live updates in a staff channel:
    *   *On Trigger:* "⏳ User is attempting verification..."
    *   *On Selection:* "⏳ User is verifying in **English**..."
    *   *On Success:* "✅ User **Verified!** (English)"
    *   *On Failure:* "❌ User **Timed Out** (English)"
*   **Slash Commands:** Fully managed via Discord UI (`/set_channel`, `/reload`, etc.).
*   **Welcome System:** Sends a custom welcome message to a specific channel upon successful verification.
    *   **Custom Extras:** Admins can append extra text or links (like channel mentions) to the welcome message.

### Time Zones Analysis
* Users can send chats with date and time present in it and based on the user's timezone set by `/my_timezone`, the bot will convert it into the timestamp format.

---

## Prerequisites

*   **Python 3.8** or higher.
*   **Discord Bot Token** with **Message Content** and **Server Members** intents enabled.
*   **Manage Messages Permission** (Required for the bot to auto-delete user messages).

---

## Installation

1.  **Install the library:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Create the bot file:**
    Create a file named `Bot.py` and paste the Python code into it.

3.  **Create the configuration file:**
    Create a file named `server_config.json` in the same folder. Template in repo.

---

## Configuration (`server_config.json`)

You must create this file. The bot uses this to store your Token, Rules, and Translations.
**Note:** Use `{equation}` for the math problem and `{rules_channel}` to link to your rules channel in the translation strings.

---

## How to use (Admins)

1.  **Start the bot:** `python Bot.py`
2.  **Configure the Verification Channel:**
    Go to the channel where users verify and type:
    `/set_verification_channel`
3.  **Configure the Rules Channel:**
    Tell the bot where your rules are listed (used for the `{rules_channel}` link):
    `/set_rules_channel #rules`
4.  **Configure the Welcome Channel:**
    Go to the channel where you want "Welcome User!" messages to appear and type:
    `/set_welcome_channel`
5.  **Add Extra Welcome Text (Optional):**
    Add extra instructions or links after the standard welcome message:
    `/set_welcome_extra Check out #general to chat!`
    *(Leave empty to clear it).*
6.  **Configure the Log Channel:**
    Go to your staff-only channel and type:
    `/set_log_channel`
7.  **Configure the Birthday Channel:**
    Go to the channel you want to announce birthdays and type:
    `/set_birthday_channel`
8.  **Set the Verified Role:**
    Type `/set_role role:@Member` (select the actual role).
9.  **Verify Configuration:**
    Type `/check_config` to see an overview of all settings.
10.  **Hot Reload:**
    If you edit the JSON file (e.g., to add a language), type `/reload` to update the bot instantly.
11. **Register a Scam Image Layout (Anti-Scam):**
    Upload a scam screenshot variant and type:
    `/add_scam_template image_file:[file] label:MrBeast X Post Variant`
12. **List Scam Templates:**
    Check your active template layout database:
    `/list_scam_templates`
13. **Remove a Scam Layout:**
    Delete a layout signature from tracking using its 16-character hex hash:
    `/remove_scam_template scam_hash:1bd1593bebb3f298`

---

## How it works (Users)

1.  **Trigger:** User types variations of "I have read the rules".
    *   *Log:* Staff channel updates to "⏳ User is attempting verification..."
2.  **Logic:**
    *   **If Account < 7 days:** User is timed out for 1 week.
    *   **If Account > 7 days:** User sees a Dropdown Menu to select their language.
3.  **Challenge:**
    *   User selects language.
    *   *Log:* Staff channel updates to include the selected language.
    *   Bot sends a hidden (ephemeral) math problem (e.g., `144 ÷ 12`).
    *   User calculates the answer (12).
    *   User copies the text of Rule #12 and pastes it into chat.
4.  **Verification:**
    *   **Success:** Bot gives the Role, posts "Welcome!" in the Welcome Channel, and edits the Log to "✅ Verified!".
    *   **Failure (Wrong Text):** Bot pings user with an error (auto-deletes after 30s).
    *   **Timeout (6 mins):** If user abandons the process, the bot pings them to retry and updates the Log to "❌ Timed Out".

---

## Hosting on Ubuntu (Systemd)

To run the bot 24/7 in the background:

1.  **Create Service File:**
    `sudo nano /etc/systemd/system/discordbot.service`

2.  **Paste Configuration:**
    ```ini
    [Unit]
    Description=Discord Verification Bot
    After=network.target

    [Service]
    User=ubuntu
    WorkingDirectory=/home/ubuntu/my-bot-folder
    ExecStart=/home/ubuntu/my-bot-folder/venv/bin/python Bot.py
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

3.  **Start:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable discordbot
    sudo systemctl start discordbot
    ```
