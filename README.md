# 🔐 SphereMatchers Verification Bot

A highly configurable, multi-language Discord bot designed to secure your server. It forces users to prove they have read the rules by solving a math problem and copy-pasting the specific English rule text.

It features **Regex pattern matching**, **Anti-Raid account age checks**, and **Traffic Logging**.

## ✨ Key Features

### 🛡️ Security & Verification
*   **Regex Trigger:** Detects variations like *"I have read the rules"*, *"I've read the rules"*, *"Ive read the rules here"*, etc.
*   **Math Challenge:** Generates random integer-only equations (Addition, Subtraction, Multiplication, Division) using clear symbols (`×`, `÷`).
*   **Strict Rule Matching:** Users must copy-paste the **exact English rule text** corresponding to the math answer.
*   **Anti-Raid / Account Age:** Automatically places accounts created less than **7 days** ago (configurable) into a **1-week Timeout**.

### 🌍 Multi-Language Support
*   **Dynamic Dropdowns:** Users select their language from a dropdown menu.
*   **Auto-Scaling:** Automatically handles unlimited languages by creating multiple dropdown menus if the list exceeds Discord's limit (25 per menu).
*   **Localized Errors:** If a user fails, the error message and hint are shown in their selected language.

### ⚙️ Administration
*   **Slash Commands:** Fully managed via Discord UI (`/set_channel`, `/reload`, etc.).
*   **Logging:** Live updates in a staff channel showing who is verifying and editing the message upon success.
*   **Welcome System:** Sends a custom welcome message to a specific channel upon successful verification.
*   **Hot Reload:** Update text/rules in the config file and reload without restarting the bot.

---

## 📋 Prerequisites

*   **Python 3.8** or higher.
*   **Discord Bot Token** with **Message Content** and **Server Members** intents enabled.

---

## 🛠️ Installation

1.  **Install the library:**
    ```bash
    pip install discord.py
    ```

2.  **Create the bot file:**
    Create a file named `Bot.py` and paste the Python code into it.

3.  **Create the configuration file:**
    Create a file named `server_config.json` in the same folder. Paste the template below.

---

## 📝 Configuration (`server_config.json`)

You must create this file. The bot uses this to store your Token, Rules, and Translations.
Check the repo for the sample config file.

---

## 🎮 How to use (Admins)

1.  **Start the bot:** `python Bot.py`
2.  **Configure the Verification Channel:**
    Go to the channel where users verify and type:
    `/set_verification_channel`
3.  **Configure the Welcome Channel:**
    Go to the channel where you want "Welcome User!" messages to appear and type:
    `/set_welcome_channel`
4.  **Configure the Log Channel:**
    Go to your staff-only channel and type:
    `/set_log_channel`
5.  **Set the Verified Role:**
    Type `/set_role role:@Member` (select the actual role).
6.  **Verify Configuration:**
    Type `/check_config` to see an overview of all settings.
7.  **Hot Reload:**
    If you edit the JSON file (e.g., to add a language), type `/reload` to update the bot instantly.

---

## 👤 How it works (Users)

1.  **Trigger:** User types any variation of:
    > "I have read the rules"
    > "I've read the rules"
    > "Ive read the rules here!"
2.  **Logic:**
    *   **If Account < 7 days:** User is timed out for 1 week.
    *   **If Account > 7 days:** User sees a Dropdown Menu to select their language.
    *   **Staff Log:** The log channel receives: *"⏳ User is attempting verification..."*
3.  **Challenge:**
    *   User selects language.
    *   Bot sends a hidden math problem (e.g., `144 ÷ 12`).
    *   User calculates the answer (12).
    *   User copies the text of Rule #12 and pastes it into chat.
4.  **Success:**
    *   Bot gives the Role.
    *   Bot posts "Welcome!" in the Welcome Channel.
    *   Bot edits the Staff Log message to: *"✅ User **Verified!**"*

---

## 🐧 Hosting on Ubuntu (Systemd)

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
    ExecStart=/home/ubuntu/my-bot-folder/venv/bin/python bot.py
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