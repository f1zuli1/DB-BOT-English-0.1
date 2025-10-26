# DB-ChatBot 🤖

**DB-ChatBot** is a versatile Discord bot that brings productivity, games, and AI chat into your server.  
Manage projects, show your profile, play Pokémon, duel in chess, or just chat — all in one bot!

---

## Features

### 🧱 Project Commands
Organize your projects directly on Discord:
!new_project → Add a new project
!projects → Show all your projects
!update_projects → Update project information
!skills → Add a skill to a project
!delete → Delete a project

shell
Kodu kopyala

### 👤 Profile Commands
Create and manage your personal profile:
!createprofil → Create a new profile
!profil → Show your profile
!deleteprofil → Delete your profile

kotlin
Kodu kopyala

### 🎮 Game & Pokémon Commands
Have fun with games and quizzes:
!go → Create a Pokémon card
!feed → Increase Pokémon HP
!attack → Battle opponent Pokémon
!startquiz → Start a quiz
$duel @user → Challenge to a chess duel
$move [piece] [target] → Move chess piece
$castle, $draw, $accept, $refuse → Chess moves

shell
Kodu kopyala

### 💬 Other Commands
Additional features for chat and creativity:
!stats → Introduce the bot
!translate → Translate your text to English
!photo → Take your photo
!video → Record a short video
!photoshow → Display your photo
!videoshow → Display your video
!chat <msg> → Chat directly with DB-ChatBot

yaml
Kodu kopyala

---

## ⚠️ Rules
**Do NOT send messages starting with "http"!**  
DB-ChatBot automatically bans users sending suspicious links.

---

## 📌 Bot Info
- **Prefix:** `!`  
- **Language:** Turkish  
- **Invite Link:** [Invite Bot](https://discord.com/oauth2/authorize?client_id=1431682128554360872&permissions=8&scope=bot%20applications.commands)  
- **Tags:** Utility, Fun, Games, Turkish

---

## 📸 Screenshots
![Project Commands](https://i.imgur.com/example2.png)  
![Profile Commands](https://i.imgur.com/example3.png)  
![Game Screenshot](https://i.imgur.com/example4.png)  

---

## 💡 How to Run Locally
1. Clone the repository:
```bash
git clone [https://github.com/yourusername/db-chatbot.git](https://github.com/f1zuli1/DB-BOT-English-0.1.git
Install dependencies:

bash
Kodu kopyala
pip install -r requirements.txt
or manually:

bash
Kodu kopyala
pip install discord.py
pip install opencv-python
pip install Pillow
pip install python-dotenv
pip install genai
Create a .env file with your bot token:

env
Kodu kopyala
DISCORD_TOKEN=your_token_here
Run the bot:

bash
Kodu kopyala
python bot.py
🌐 Deployment on Railway
Push your repository to GitHub.

Connect your GitHub repo to Railway as a new project.

Add an Environment Variable on Railway:

ini
Kodu kopyala
DISCORD_TOKEN=your_token_here
Deploy → bot is now online 24/7.

🌐 Contribution
Feel free to contribute! Fork the repo, make changes, and submit a pull request.

