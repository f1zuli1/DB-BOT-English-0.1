import discord
import random
import re
import os
import cv2
import asyncio
import time
import datetime
import subprocess
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from dotenv import load_dotenv
from ChessPieces import Pawn, Rook, Knight, Bishop, Queen, King
from discord.ext import commands, tasks
from discord import ui, ButtonStyle, TextStyle
from discord.ui import View, Button, Modal, TextInput
from collections import defaultdict
from logic import *
from logic import Pokemon
from logic import Wizard,Fighter
from logic import quiz_questions
from logic import DB_Manager
from logic import allowed_domains, warnings
from logic import init_db, save_file, get_user_files
from config import token, DATABASE
from datetime import datetime

# Bot için yetkileri/intents ayarlama
intents = discord.Intents.default()  # Varsayılan ayarların alınması
intents.messages = True              # Botun mesajları işlemesine izin verme
intents.message_content = True       # Botun mesaj içeriğini okumasına izin verme
intents.guilds = True                # Botun sunucularla çalışmasına izin verme

intents = discord.Intents.default()
intents.message_content = True
# Tanımlanmış bir komut önekine ve etkinleştirilmiş amaçlara sahip bir bot oluşturma
bot = commands.Bot(command_prefix=["!", "$"], intents=intents)

load_dotenv()
user_responses = {}
points = defaultdict(int)
manager = DB_Manager(DATABASE)
manager.create_tables()
bot.spectate_msgs = {}

@bot.event
async def on_ready():
    print(f'Logged in as:  {bot.user.name}')

@bot.command()
async def start(ctx):
    await ctx.send("Hello! I am a chat management bot!")

#-----------------TRANSLATE------------------------------------------------------------------------------------------------------------------------------

class PersistentView(discord.ui.View):
    def __init__(self, owner):
        super().__init__(timeout=None)
        self.owner = owner

    @discord.ui.button(label="Get Answer", style=discord.ButtonStyle.primary, custom_id="text_ans")
    async def text_ans_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        obj = TextAnalysis.memory[self.owner][-1]
        await interaction.response.send_message(obj.response, ephemeral=True)

    @discord.ui.button(label="Translate Message", style=discord.ButtonStyle.secondary, custom_id="text_translate")
    async def text_translate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        obj = TextAnalysis.memory[self.owner][-1]
        await interaction.response.send_message(obj.translation, ephemeral=True)

@bot.command(name="translate") # Command name changed for consistency
async def start(ctx, *, text: str):
    TextAnalysis(text, ctx.author.name)
    view = PersistentView(ctx.author.name)
    await ctx.send("I've received your message! What would you like to do with it?", view=view)

#------------------BAN---------------------------------------------------------------------------------------------------------------------------------
# Function to check if the message contains a forbidden link
def contains_unallowed_link(message_content):
    urls = re.findall(r'(https?://\S+)', message_content)
    for url in urls:
        if not any(domain in url for domain in allowed_domains):
            return True
    return False

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return # Ignore bot's own messages

    if contains_unallowed_link(message.content):
        user_id = message.author.id

        # If the user has already received a warning, ban them
        if warnings.get(user_id, 0) >= 1:
            try:
                await message.author.ban(reason="Shared a banned link for the second time")
                await message.channel.send(f"{message.author} was banned for sharing a banned link for the second time.")
                warnings.pop(user_id, None) # Remove user from dictionary
            except Exception as e:
                await message.channel.send(f"Unable to ban: {e}")
        else:
            # First warning
            warnings[user_id] = 1
            await message.channel.send(f"{message.author}, you shared a banned link! Next time you will be banned.")

    await bot.process_commands(message)

#--------------QUIZ-----------------------------------------------------------------------------------------------------------------------------------------

# Start quiz command
@bot.command(name="startquiz")
async def start_quiz(ctx):
    user_id = ctx.author.id
    if user_id in user_responses:
        await ctx.send("You have already started a quiz!")
        return

    user_responses[user_id] = 0 # Start of quiz for the user
    points[user_id] = 0 # Reset score
    await send_question(ctx, user_id)

async def send_question(ctx_or_interaction, user_id):
    question = quiz_questions[user_responses[user_id]]
    buttons = question.gen_buttons()
    view = discord.ui.View()
    for button in buttons:
        view.add_item(button)

    if isinstance(ctx_or_interaction, commands.Context):
        await ctx_or_interaction.send(question.text, view=view)
    else:
        await ctx_or_interaction.followup.send(question.text, view=view)
#question
@bot.event
async def on_interaction(interaction):
    user_id = interaction.user.id
    if user_id not in user_responses:
        # If the interaction was already responded to, send via followup
        if interaction.response.is_done():
            await interaction.followup.send("Please start the test by typing the !startquiz command", ephemeral=True)
        else:
            await interaction.response.send_message("Please start the test by typing the !startquiz command", ephemeral=True)
        return

    custom_id = interaction.data.get("custom_id")
    if not custom_id:
        return

    if custom_id.startswith("correct"):
        await interaction.response.send_message("Correct answer!", ephemeral=True)
        points[user_id] += 1
    elif custom_id.startswith("wrong"):
        await interaction.response.send_message("Wrong answer!", ephemeral=True)

    user_responses[user_id] += 1
    if user_responses[user_id] > len(quiz_questions) - 1:
        await interaction.followup.send(f"Congratulations, the quiz is over! Your Total Score: {points[user_id]}")
    else:
        await send_question(interaction, user_id)

#--------------POKEMON-----------------------------------------------------------------------------------------------------------------------------------------------

# '!go' command
@bot.command()
async def go(ctx):
    author = ctx.author.name # Gets the name of the user who called the command
    if author not in Pokemon.pokemons: # Check if a Pokémon already exists for this user
        chance = random.randint(1, 3)# Create a random number between 1 and 3
        # Create a Pokémon object based on the random number
        if chance == 1:
            pokemon = Pokemon(author) # Create a standard Pokémon
        elif chance == 2:
            pokemon = Wizard(author) # Create a Wizard type Pokémon
        elif chance == 3:
            pokemon = Fighter(author) # Create a Fighter type Pokémon
        await ctx.send(await pokemon.infopokemon())# Sending information about the Pokémon
        image_url = await pokemon.show_img() # Getting the Pokémon image URL
        if image_url:
            name=await pokemon.get_name()
            color=discord.Color.orange()
            embed = discord.Embed(color=color,title=name.upper())
            boy=pokemon.height/10
            kilo=pokemon.weight/10
            hp=pokemon.hp
            power=pokemon.power
            embed.add_field(name="Weight",value=kilo,inline=True) # Kilo -> Weight
            embed.add_field(name="Height",value=boy,inline=True) # Boy -> Height
            embed.add_field(name="",value="",inline=False) 
            embed.add_field(name="Hp",value=hp,inline=True)
            embed.add_field(name="Power",value=power,inline=True) # Creating the embedded message
            embed.set_image(url=image_url) # Setting the Pokémon's image
            await ctx.send(embed=embed) # Sending an embedded message with the image
        else:
            await ctx.send("The Pokémon image could not be loaded!") # Pokémonun görüntüsü yüklenemedi!
    else:
        await ctx.send("You have already created your own Pokémon!") # Zaten kendi Pokémonunuzu oluşturdunuz!



@bot.command()
async def attack(ctx):
    target = ctx.message.mentions[0] if ctx.message.mentions else None # Gets the mentioned user in the message
    if target: # Check if the user is mentioned
        # Check if both attacker and target have a Pokémon
        if target.name in Pokemon.pokemons and ctx.author.name in Pokemon.pokemons:
            enemy = Pokemon.pokemons[target.name] # Get the target's Pokémon
            attacker = Pokemon.pokemons[ctx.author.name] # Get the attacker's Pokémon
            result = await attacker.attack(enemy) # Perform the attack and get the result
            await ctx.send(result)  #Send the attack result
        else:
            await ctx.send("For battle, both sides must have a Pokémon!") # Savaş için her iki tarafın da Pokémon sahibi olması gerekir!
    else:
        await ctx.send("Mention the user you want to attack by tagging them.") # Saldırmak istediğiniz kullanıcıyı etiketleyerek belirtin.
# Botun çalıştırılması


@bot.command()
async def infopokemon(ctx):
    author = ctx.author.name
    if author in Pokemon.pokemons:
        pokemon = Pokemon.pokemons[author]
        await ctx.send(await pokemon.info())
    else:
        await ctx.send("You don't have a Pokémon!") # Pokémon'un yok!


@bot.command()
async def feed(ctx):
    author = ctx.author.name
    if author in Pokemon.pokemons:
        pokemon = Pokemon.pokemons[author]
        await ctx.send(await pokemon.feed())
    else:
        await ctx.send("You don't have a Pokémon!") # Pokémon'un yok!

#------------- MODAL ---------------------------------------------------------------------------------------------------------------------------------------

# Define Modal window
class TestModal(ui.Modal, title='Create Profile'): # Create Profil -> Create Profile
    field_1 = ui.TextInput(label='Name') # Ad -> Name
    field_2 = ui.TextInput(label='Surname', style=TextStyle.paragraph) # Soyad -> Surname
    field_3 = ui.TextInput(label='Date of Birth', placeholder="DD/MM/YY") # Dogum Tarixi -> Date of Birth

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        ad = self.field_1.value
        soyad = self.field_2.value
        dogum_tarixi = self.field_3.value

        manager.insert_profile(user_id, ad, soyad, dogum_tarixi)
        await interaction.response.send_message("Your profile has been saved!", ephemeral=True) # Profiliniz kaydedildi!

# Define Button
class TestButton(ui.Button):
    def __init__(self, label="Profile", style=ButtonStyle.blurple, row=0): # Profil -> Profile
        super().__init__(label=label, style=style, row=row)

    async def callback(self, interaction: discord.Interaction):
        # Only show the modal
        await interaction.response.send_modal(TestModal())

# View containing the button
class TestView(ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TestButton(label="Profile")) # Profil -> Profile
# --------------------- Modal ve Buton --------------------------
# --------------------- Komutlar ---------------------
import discord
from discord.ext import commands
import asyncio

@bot.command()
async def infocommand(ctx):
    # Typing effect
    msg = await ctx.send("📚 Commands are loading...") # Əmrlər yüklənir...
    await asyncio.sleep(1.5)

    # Embed message
    embed = discord.Embed(
        title="📜 Command List", # Əmrlər Siyahısı
        description="**You can use the following commands:**", # Aşağıdakı əmrlərdən istifadə edə bilərsiniz:
        color=discord.Color.blue()
    )

    embed.add_field(name="🧱 **Project Commands**", value="""
`!new_project` - Add a new project
`!projects` - Show all your projects
`!update_projects` - Update project information
`!skills` - Add a skill to a project
`!delete` - Delete a project 
""", inline=False)

    embed.add_field(name="👤 **Profile Commands**", value="""
`!createprofil` - Create a new profile 
`!profil` - Show your profile 
`!deleteprofil` - Delete your profile 
""", inline=False)

    embed.add_field(name="🎮 **Game and Pokémon Commands**", value="""
`!go` - Create a Pokémon card 
`!feed` - Increase Pokémon's HP 
`!attack` - Attack opponent's Pokémon 
`!startquiz` - Start a quiz
`$duel @user` - Challenge to a chess duel 
`$move [piece] [target]` - Move a piece 
`$castle` - Perform castling move 
`$draw` - Offer a draw 
`$accept / $refuse` - Accept or refuse the offer
""", inline=False)

    embed.add_field(name="💬 **Other Commands**", value="""
!stats - The bot introduces itself
!translate - Translates the sentence you wrote into English
!photo - Takes your photo 
!video - Shoots a 5 second video 
!videoshow - Shows the video 
!photoshow - Show the photo
!chat <message> - You can talk with DB-ChatBot
""", inline=False)

    embed.add_field(name="⚠️ **Rules**", value=""" 
**Sending messages starting with HTTP is forbidden!** 
Otherwise, the bot will automatically ban you. 🚫 
""", inline=False)

    embed.set_footer(text="💡 Type /help for more information!") # Daha çox məlumat üçün /help yaz!
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/4712/4712035.png")

    # Edit the previous message
    await msg.edit(content="✅ Commands loaded! All commands below:", embed=embed) # Komandalar yükləndi! Aşağıda bütün əmrlər:

    # Add a small reaction
    await ctx.message.add_reaction("👀")
    await ctx.send(f"**{ctx.author.display_name}** viewed the command list! 🔥") # komanda siyahısına baxdı! 🔥

#---------------------- Profile ----------------------------------------

#-----  !createprofile ---------
@bot.command()
async def createprofil(ctx):
    await ctx.send("You can create a profile by clicking this button:", view=TestView()) # Bu düğmeye basarak profil oluşturabilirsiniz:

#------- !profile ---------------
@bot.command()
async def profil(ctx):
    user_id = ctx.author.id
    profile = manager.get_profile(user_id)
    if profile:
        ad, soyad, dogum_tarixi = profile
        await ctx.send(f"ID: {user_id}\nName: {ad}\nSurname: {soyad}\nDate of Birth: {dogum_tarixi}") # Ad: -> Name:, Soyad: -> Surname:, Dogum Tarihi: -> Date of Birth:
    else:
        await ctx.send("You haven't created a profile yet. Use the !createprofil command.") # Henüz bir profil oluşturmadınız. !createprofil komutunu kullanın.

#------- !deleteprofile --------
@bot.command()
async def deleteprofil(ctx, user_id: int):
    profile = manager.get_profile(user_id)
    if profile:
        manager.delete_profile(user_id)
        await ctx.send(f"The profile with ID {user_id} was successfully deleted.") # ID’li profil başarıyla silindi.
    else:
        await ctx.send(f"Could not find the profile with ID {user_id}.") # ID’li profili bulamadım.
        
#--------- Project ----------------------------------------------------------------

@bot.command(name='new_project')
async def new_project(ctx):
    await ctx.send("Please enter the project name!") # Lütfen projenin adını girin!

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    name = await bot.wait_for('message', check=check)
    data = [ctx.author.id, name.content]
    await ctx.send("Please send the link for the project!") # Lütfen projeye ait bağlantıyı gönderin!
    link = await bot.wait_for('message', check=check)
    data.append(link.content)

    statuses = [x[0] for x in manager.get_statuses()]
    await ctx.send("Please enter the current status of the project!", delete_after=60.0) # Lütfen projenin mevcut durumunu girin!
    await ctx.send("\n".join(statuses), delete_after=60.0)
    
    status = await bot.wait_for('message', check=check)
    if status.content not in statuses:
        await ctx.send("The status you selected is not in the list. Please try again!", delete_after=60.0) # Seçtiğiniz durum listede bulunmuyor. Lütfen tekrar deneyin!
        return

    status_id = manager.get_status_id(status.content)
    data.append(status_id)
    manager.insert_project([tuple(data)])
    await ctx.send("Project saved") # Proje kaydedildi

@bot.command(name='projects')
async def get_projects(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        text = "\n".join([f"Project name: {x[2]} \nLink: {x[4]}\n" for x in projects])
        await ctx.send(text)
    else:
        await ctx.send("You don't have any projects yet!\nConsider adding one! You can use the !new_project command.") # Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.

@bot.command(name='skills')
async def skills(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        await ctx.send('Select the project you want to add a skill to') # Bir beceri eklemek istediğiniz projeyi seçin
        await ctx.send("\n".join(projects))

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        project_name = await bot.wait_for('message', check=check)
        if project_name.content not in projects:
            await ctx.send('You do not own this project, please try again! Select the project you want to add a skill to') # Bu projeye sahip değilsiniz, lütfen tekrar deneyin! Beceri eklemek istediğiniz projeyi seçin
            return

        skills = [x[1] for x in manager.get_skills()]
        await ctx.send('Select a skill') # Bir beceri seçin
        await ctx.send("\n".join(skills))

        skill = await bot.wait_for('message', check=check)
        if skill.content not in skills:
            await ctx.send('It seems the skill you selected is not in the list! Please try again! Select a skill') # Görünüşe göre seçtiğiniz beceri listede yok! Lütfen tekrar deneyin! Bir beceri seçin
            return

        manager.insert_skill(user_id, project_name.content, skill.content)
        await ctx.send(f'{skill.content} skill was added to the {project_name.content} project') # becerisi {project_name.content} projesine eklendi
    else:
        await ctx.send("You don't have any projects yet!\nConsider adding one! You can use the !new_project command.") # Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.

@bot.command(name='delete_project')
async def delete_project(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        await ctx.send("Select the project you want to delete") # Silmek istediğiniz projeyi seçin
        await ctx.send("\n".join(projects))

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        project_name = await bot.wait_for('message', check=check)
        if project_name.content not in projects:
            await ctx.send('You do not own this project, please try again!') # Bu projeye sahip değilsiniz, lütfen tekrar deneyin!
            return

        project_id = manager.get_project_id(project_name.content, user_id)
        manager.delete_project(user_id, project_id)
        await ctx.send(f'{project_name.content} project was deleted from the database!') # projesi veri tabanından silindi!
    else:
        await ctx.send("You don't have any projects yet!\nConsider adding one! You can use the !new_project command.") # Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.

@bot.command(name='update_projects')
async def update_projects(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        await ctx.send("Select the project you want to update") # Güncellemek istediğiniz projeyi seçin
        await ctx.send("\n".join(projects))

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        project_name = await bot.wait_for('message', check=check)
        if project_name.content not in projects:
            await ctx.send("An error occurred! Please select the project you want to update again:") # Bir hata oldu! Lütfen güncellemek istediğiniz projeyi tekrar seçin:
            return

        await ctx.send("What do you want to change in the project?") # Projede neyi değiştirmek istersiniz?
        # Translated attribute keys for display, values remain the same for database mapping
        attributes = {'Project name': 'project_name', 'Description': 'description', 'Project link': 'url', 'Project status': 'status_id'}
        await ctx.send("\n".join(attributes.keys()))

        attribute = await bot.wait_for('message', check=check)
        if attribute.content not in attributes:
            await ctx.send("An error occurred! Please try again!") # Hata oluştu! Lütfen tekrar deneyin!
            return

        # Note: 'Durum' was translated to 'Project status' for the user prompt, but the check for 'Durum' below must be updated to 'Project status' if the attributes list is used. 
        # Since I translated attributes keys to English, I will use 'Project status' here:
        if attribute.content == 'Project status': 
            statuses = manager.get_statuses()
            await ctx.send("Select a new status for your project") # Projeniz için yeni bir durum seçin
            await ctx.send("\n".join([x[0] for x in statuses]))
            update_info = await bot.wait_for('message', check=check)
            if update_info.content not in [x[0] for x in statuses]:
                await ctx.send("Wrong status selected, please try again!") # Yanlış durum seçildi, lütfen tekrar deneyin!
                return
            update_info = manager.get_status_id(update_info.content)
        else:
            await ctx.send(f"Enter a new value for {attribute.content}") # için yeni bir değer girin
            update_info = await bot.wait_for('message', check=check)
            update_info = update_info.content

        manager.update_projects(attributes[attribute.content], (update_info, project_name.content, user_id))
        await ctx.send("All operations completed! Project updated!") # Tüm işlemler tamamlandı! Proje güncellendi!
    else:
        await ctx.send("You don't have any projects yet!\nConsider adding one! You can use the !new_project command.") # Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.

#----------------------------- CHESS.BOT ----------------------------------------------------------------------------------------
intents = discord.Intents.default()
intents.members = True
bot.remove_command('help')

# =============================================================================
# Initialise some variables & global data at launch
# =============================================================================
@bot.event
async def on_ready():
	bot.startTime = time.time()
	bot.startDateTime = datetime.datetime.now()

	print(f"Online as {bot.user.name} at {bot.startDateTime}")
	bot.serv_dic = {}
	bot.duel_ids = {}
	bot.spectate_msgs = {}

	await bot.change_presence(activity = discord.Game("$duel @someone"))

	# A dictionnary of all the bot's custom emotes (correspondes to the pieces)
	# 0 for white, 1 for black pieces
	bot.emotes = {
		"pawn": ["<:pawn_white:798140768379863090>","<:pawn_black:798140768379863060>"],
		"rook": ["<:rook_white:798140768166084609>","<:rook_black:798140768438583296>"],
		"bishop": ["<:bishop_white:798140767801311243>","<:bishop_black:798140768102514699>"],
		"knight": ["<:knight_white:798140768383926272>","<:knight_black:798140768204095508>"],
		"queen": ["<:queen_white:798140768476725278>","<:queen_black:798140768442384404>"],
		"king": ["<:king_white:798140768165429278>","<:king_black:798140768187449395>"]
		}

# =============================================================================
# Displays a message when the bot joins a server
# =============================================================================
@bot.event
async def on_guild_join(guild):
	for channel in guild.text_channels:
		if channel.permissions_for(guild.me).send_messages:
			msg = "Thank you for adding me to this server!"

			# Checking for missing perms
			missing_perms = []
			if not channel.permissions_for(guild.me).manage_messages:
				missing_perms.append("-Manage Messages")

			if not channel.permissions_for(guild.me).attach_files:
				missing_perms.append("-Attach Files")

			if not channel.permissions_for(guild.me).manage_channels:
				missing_perms.append("-Manage Channels")

			if not channel.permissions_for(guild.me).manage_roles:
				missing_perms.append("-Manage Roles")

			if not channel.permissions_for(guild.me).external_emojis:
				missing_perms.append("-Using External Emojis")

			if not channel.permissions_for(guild.me).add_reactions:
				missing_perms.append("-Add Reactions")

			if len(missing_perms) != 0:
				to_add = '\n'.join(missing_perms)
				msg += f"\nI appear to be missing the following permissions, please add them before using the $duel command:\n{to_add}"
				msg += "\n\nYou can also have me rejoin through that link to ensure I get the proper permissions: https://discord.com/oauth2/authorize?bot_id=797085070422441984&scope=bot&permissions=268807248"
			await channel.send(msg)
			break


# =============================================================================
# The coroutine that runs the actual duel
# =============================================================================
async def game_on(ctx,duel_channel, duelist, victim, duel_msg):

	def command_check(message):
		return message.channel == duel_channel and message.author != bot.user

	async def endgame():
		await asyncio.sleep(60)
		await duel_channel.delete()

	async def get_piece(idt):
		if white == turnset:
			for piece in white_pieces:
				if piece.idt.lower() == idt.lower():
					return piece
			else:
				return None

		elif black == turnset:
			for piece in black_pieces:
				if piece.idt.lower() == idt.lower():
					return piece

			else:
				return None

	board = [[{"color": None, "piece": None} for i in range(8)] for i in range(8)]

	# Filling the board's color
	col = "W"
	for line in board:
		for cell in line:
			cell["color"] = col

			# Swap the next cell color
			if col == "W":
				col = "B"
			elif col == "B":
				col = "W"

	# Filling the board with pieces
	# White Pawns
	for x in range(len(board[1])):
		board[1][x]["piece"] = Pawn("W",x,1,f"P{x+1}")

	# Black Pawns
	for x in range(len(board[6])):
		board[6][x]["piece"] = Pawn("B",x,6,f"P{x+1}")

	# Rooks
	board[0][0]["piece"] = Rook("W",0,0,"R1")
	board[0][7]["piece"] = Rook("W",7,0,"R2")
	board[7][0]["piece"] = Rook("B",0,7,"R1")
	board[7][7]["piece"] = Rook("B",7,7,"R2")

	# Knights
	board[0][1]["piece"] = Knight("W",1,0,"K1")
	board[0][6]["piece"] = Knight("W",6,0,"K2")
	board[7][1]["piece"] = Knight("B",1,7,"K1")
	board[7][6]["piece"] = Knight("B",6,7,"K2")

	# Bishops
	board[0][2]["piece"] = Bishop("W",2,0,"B1")
	board[0][5]["piece"] = Bishop("W",5,0,"B2")
	board[7][2]["piece"] = Bishop("B",2,7,"B1")
	board[7][5]["piece"] = Bishop("B",5,7,"B2")

	# Queens
	board[0][3]["piece"] = Queen("W",3,0,"Q")
	board[7][3]["piece"] = Queen("B",3,7,"Q")

	# Kings
	board[0][4]["piece"] = King("W",4,0,"K")
	white_king = board[0][4]["piece"]
	board[7][4]["piece"] = King("B",4,7,"K")
	black_king = board[7][4]["piece"]

	# Randomly decides who is white and who is black
	if random.randint(0,1):
		white = duelist
		black = victim

	else:
		white = victim
		black = duelist

	# Initialising stuff
	turnset = white
	winner = None
	old_x = None
	old_y = None
	move_x = None
	move_y = None
	old_piece = None
	castled_rook = False
	white_queen_nb= 1
	black_queen_nb = 1
	white_taken = {"pawn":0,"rook":0,"bishop":0,"knight":0,"queen":0,"king":0}
	black_taken = {"pawn":0,"rook":0,"bishop":0,"knight":0,"queen":0,"king":0}


	msg = f"Here's how you play chess with {ctx.guild.me.mention}:\n```\n"
	msg += "When it's your turn, move your piece with:  $move [piece name] [destination coordinates]\n"
	msg += "For exemple, to move the 3rd Pawn (P3) to the f4 cell, use $move P3 f4\n(note that you can use $m instead of $move, and that the piece's names and positions aren't caps sensitive)\n\n"
	msg += "Castling is done with $castle [castling rook].\nFor exemple, to castle using the R1 rook, use $castle R1\n\n"
	msg += "You can concede anytime with $concede, even if it's not your turn. You can also ask your opponent to declare the game a draw with $draw (they will have to accept).\nTo win, you have to take the king (not just checkmate it)."
	msg += "\n\nWhile I will not register illegal moves, I also won't stop you from putting your king in danger :)\n\n"
	msg += "If someone doesn't take their turn within 10 minutes, the game times out, and the other player is declared winner.\n```"
	await duel_channel.send(msg)

	while True:  # Turns will continue until a King is taken

		if winner == None:

			# Constructing the list of taken pieces as emotes
			white_toadd = ""
			black_toadd = ""
			for taken_piece,nb in white_taken.items():
				if nb == 0:
					continue
				white_toadd += f"  {bot.emotes[taken_piece][1]}\\*{nb}"

			for taken_piece,nb in black_taken.items():
				if nb == 0:
					continue
				black_toadd += f"  {bot.emotes[taken_piece][0]}\\*{nb}"

			turn_msg = f"**White:** {white.name}  -{white_toadd}\n**Black:** {black.name}  -{black_toadd}"

			if old_x != None and old_y != None:
				turn_msg+=f"\nLast turn: **{old_piece.idt}** moved (*{chr(old_x+97)}{old_y+1}* → *{chr(move_x+97)}{move_y+1}*)"
				if castled_rook:
					castled_rook = False
					turn_msg+=" **-castling-**"

			turn_msg += f"\nWaiting for a play from: {turnset.mention}"
		else:
			turn_msg = f"**White:** {white.name}\n**Black:** {black.name}\n**{winner.name} WINS!**"

		# Checks if either king is in check
		if winner == None:
			white_check = white_king.is_in_check(board)
			black_check = black_king.is_in_check(board)

		if white_check[0]:
			turn_msg += "\n**⚠️---THE WHITE KING IS IN CHECK---⚠️**\n"
		if black_check[0]:
			turn_msg += "\n**⚠️---THE BLACK KING IS IN CHECK---⚠️**\n"

		# Initalising the list of pieces of both players
		white_pieces = []
		black_pieces = []

		# Using PIL to construct the chessboard
		board_img = Image.open("Ressources/ChessBoard.png")
		start_x = 22
		start_y = 1200
		cell_size = 162
		offset = cell_size//4

		# Loading the font for the pieces ID
		font = ImageFont.truetype("Ressources/F25_font.ttf", 31)
		draw = ImageDraw.Draw(board_img)

		for i in range(8):
			for j in range(8):

				# Calculating this cell's absolute coordinates (in px)
				point_coords = (start_x + j*cell_size+offset, start_y- i*cell_size-offset)
				piece = board[i][j]["piece"]

				# Skipping empty cells
				if piece == None:
					continue
				else:

					# putting the piece into the piece list
					if piece.color == "W":
						white_pieces.append(piece)
					elif piece.color == "B":
						black_pieces.append(piece)

					# Getting the corresponding piece file
					piece_filepath = "Ressources/Pieces/"+piece.file
					piece_img = Image.open(piece_filepath)


				# pasting the piece into the board
				board_img.paste(piece_img,point_coords,piece_img)
				piece_img.close()

				# Adding the text
				point_coords = list(point_coords)
				point_coords[0] = point_coords[0] - (offset//3)
				point_coords = tuple(point_coords)

				# The text is black, or red if the piece is threatening a king
				color = "black"
				if piece in white_check[1] or piece in black_check[1]:
					color = "red"

				draw.text(point_coords,piece.idt,font=font,fill=color)

		# If there was a move last turn, draw a line representing it
		if old_x != None and old_y != None:
			old_px = (start_x+old_x*cell_size+int(2.6*offset),start_y-old_y*cell_size+(offset//1.1))
			new_px = (start_x+move_x*cell_size+int(2.6*offset),start_y-move_y*cell_size+(offset//1.1))

			draw.line(old_px + new_px, fill = "red", width=5)

		# Saving the image
		randname = random.randint(100,9999999)
		board_img.save(str(randname)+".png")
		board_img.close()

		# Sending updated board & updated turn message, then deleting the image
		turn_sent = await duel_channel.send(content=turn_msg, file=discord.File(str(randname)+".png"))
		os.remove(str(randname)+".png")

		if winner != None:
			await duel_channel.send(f"{winner.name} wins the game!\n(This channel will be deleted in 1 minute)")
			await endgame()
			return

		end_turn = True
		while True and end_turn:

			try:
				reply = await bot.wait_for("message", check=command_check, timeout = 600)

			except asyncio.TimeoutError:
				await duel_channel.send(f"{turnset.mention} didn't play in time (10min). Game canceled.\n(This channel will be deleted in 1 minute)")
				await endgame()
				return


			from_player = reply.author == white or reply.author == black
			if "$concede" in reply.content and from_player:
				await duel_channel.send(f"**{reply.author.name} has conceded!**\n(This channel will be deleted in 1 minute)")
				await endgame()
				return

			exited_draw = False
			if "$draw" == reply.content and from_player:
				bot_msg = await duel_channel.send(f"{reply.author.name} wants to declare this game a draw.\nType $accept to accept\nType $refuse to refuse")

				# Waiting for an answer
				while True:
					try:
						reply_draw = await bot.wait_for("message", check=command_check, timeout = 180)

					except asyncio.TimeoutError:
						bot_reply = await duel_channel.send("No reply was given in time. Draw request canceled.")
						exited_draw = True
						break

					# The draw request was accepted. Ending the match
					if reply_draw.content == "$accept":
						await duel_channel.send("**This match has been declared a draw!**\n(This channel will be deleted in 1 minute)")
						await endgame()
						return

					elif reply_draw.content == "$refuse":
						bot_reply = await duel_channel.send("Draw request refused. The match continues!")
						exited_draw = True
						break

					else:
						tmp = await reply_draw.channel.fetch_message(reply_draw.id)
						await tmp.add_reaction("💬")
						await tmp.delete(delay = 15)

			# Returns at the start of the loop & cleans the draw message
			if exited_draw:
				await reply.delete(delay = 2)
				await reply_draw.delete(delay = 2)
				await bot_reply.add_reaction("❌")
				await bot_reply.delete(delay = 10)
				await bot_msg.delete(delay = 2)

				continue

			# If there is no commands, then this is a chat message (15sec lifespan)
			mv_cmd = "$move" not in reply.content and "$m " not in reply.content
			if mv_cmd and "$castle" not in reply.content and "$draw" not in reply.content:
				tmp = await reply.channel.fetch_message(reply.id)
				await tmp.add_reaction("💬")
				await tmp.delete(delay = 15)
				continue

			if reply.author == turnset:
				elements = reply.content.split(" ")

				# Easy way to avoid problems between commands argument number
				if len(elements)<3:
					elements.append(None)
					elements.append(None)

				# Finding the piece in question (if it exists)
				piece = await get_piece(elements[1])
				if piece == None:
					tmp = await reply.channel.fetch_message(reply.id)
					await tmp.add_reaction("👎")
					await tmp.delete(delay =2)
					continue

				if "$castle" in reply.content:

					# Only Rooks can castle
					if type(piece) == Rook:
						king = await get_piece("K")

						# Can't castle if K or R has moved
						if piece.can_castle and king.can_castle:
							castle_check = piece.castling(king.x, king.y, board)

							# Can't castle if there's anything in the path
							# Also can't castle if king is in check
							if castle_check[0] and not king.in_check:

								# Results depend on the type of castling
								if castle_check[1] == "big":
									k_mod = -2
									r_mod = 3

								elif castle_check[1] == "small":
									k_mod = 2
									r_mod = -2

								# Moving the Rook
								old_x = piece.x
								old_y = piece.y
								board[piece.y][piece.x+r_mod]["piece"] = piece
								board[old_y][old_x]["piece"] = None
								piece.x = piece.x + r_mod
								piece.can_castle = False

								# Moving the king
								old_x = king.x
								old_y = king.y
								board[king.y][king.x+k_mod]["piece"] = king
								board[old_y][old_x]["piece"] = None
								king.x = king.x + k_mod
								king.can_castle = False

								# Updates the move coords for the movement line
								move_x = king.x
								move_y = king.y
								old_piece = king
								castled_rook = True

								# This turn ends
								end_turn = False
								continue

					# Castling failed
					tmp = await reply.channel.fetch_message(reply.id)
					await tmp.add_reaction("👎")
					await tmp.delete(delay =2)
					continue


				try:
					move_x = ord(elements[2][0].lower())-97
					move_y = int(elements[2][1])-1

				except Exception as e:
					tmp = await reply.channel.fetch_message(reply.id)
					await tmp.add_reaction("👎")
					await tmp.delete(delay =2)
					continue

				old_x = piece.x
				old_y = piece.y

				# Attempts to move the piece
				if piece.move(move_x, move_y, board):

					old_piece = piece
					cur_piece = board[move_y][move_x]["piece"]

					if cur_piece != None:
						if turnset == white:
							white_taken[cur_piece.piece_type] += 1

						else:
							black_taken[cur_piece.piece_type] += 1


					# If a king is taken, the game ends
					if board[move_y][move_x]["piece"] != None and board[move_y][move_x]["piece"].idt == "K":
						winner = turnset

					board[move_y][move_x]["piece"] = piece
					board[old_y][old_x]["piece"] = None

					# If a pawn gets to the end of the board, it becomes a queen
					if "P" in piece.idt and ((piece.y == 0 and piece.color == "B") or (piece.y == 7 and piece.color == "W")):

						# Avoids new queens having the same id
						if turnset == white:
							to_add = white_queen_nb
							white_queen_nb +=1

						else:
							to_add = black_queen_nb
							black_queen_nb +=1

						board[move_y][move_x]["piece"] = Queen(piece.color,piece.x,piece.y,f"Q{to_add}")


					break

				else:
					tmp = await reply.channel.fetch_message(reply.id)
					await tmp.add_reaction("👎")
					await tmp.delete(delay =2)
					continue
			else:
				tmp = await reply.channel.fetch_message(reply.id)
				await tmp.add_reaction("🤨")
				await tmp.delete(delay =2)
				continue

		# Deleting the messages
		tmp = await reply.channel.fetch_message(reply.id)
		await tmp.delete()
		tmp = await turn_sent.channel.fetch_message(turn_sent.id)
		await tmp.delete()

		# next turn
		if turnset == white:
			turnset = black
		elif turnset == black:
			turnset = white

		end_turn = False



# =============================================================================
# The $duel command is used to start a game
# =============================================================================
@bot.command(pass_context=True, aliases = ["game","challenge"])
async def duel(ctx, victim_str=None, *args):

	# Called to verify if a message is a reply to a duel request
	def accept_check(message):
		return (message.content == "$accept" or message.content == "$refuse") and message.author == victim

	if ctx.guild == None:
		await ctx.send("You can only use the duel command in a server.")
		return

	if not victim_str:
		await ctx.send("You need to specify the user you wish to duel.")
		return

	if len(ctx.message.mentions) == 0:
		await ctx.send(f"Cannot find user \"{victim_str.strip('@')}\".")
		return

	# The User objects of the 2 participants
	duelist = ctx.author
	victim = ctx.message.mentions[0]

	if victim == ctx.author:
		await ctx.send("You can't challenge yourself...")
		return

	if victim == bot.user:
		await ctx.send("You cannot challenge me (for your own good).")
		return

	await ctx.send(f"{duelist.mention} has challenged you, {victim.mention}, in a game of chess. Will you accept the duel?\n\nType \"$accept\" to accept the duel.\nType \"$refuse\" to refuse the duel.")

	try:
		reply = await bot.wait_for("message", check=accept_check, timeout = 600)

	except asyncio.TimeoutError:
		await ctx.send(f"{duelist.mention}'s challenge request has expired. {victim.mention} didn't accept in time.")
		return

	if reply.content == "$refuse":
		await ctx.send(f"{victim.mention} has refused {duelist.mention}'s challenge.")
		return

	# If we're here, both parties are ready for the duel
	# Generating duel ID
	duel_id = random.randint(10000, 99999)
	while duel_id in bot.duel_ids.keys():
		duel_id = random.randint(10000, 99999)

	bot.duel_ids[duel_id] = ctx.guild.id

	# Creating duel channel
	overwrites = {
		ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
		duelist: discord.PermissionOverwrite(read_messages=True, send_messages=True),
		victim:  discord.PermissionOverwrite(read_messages=True, send_messages=True)

		}

	if "public" in args:
		overwrites[ctx.guild.default_role] = discord.PermissionOverwrite(send_messages=False)

	else:
		overwrites[ctx.guild.default_role] = discord.PermissionOverwrite(read_messages=False)

	duel_channel = await ctx.guild.create_text_channel(f"chess-{duel_id}", overwrites=overwrites, category=ctx.channel.category)

	# Adding duel entry
	if ctx.guild.id not in bot.serv_dic.keys():
		bot.serv_dic[ctx.guild.id] = {}

	bot.serv_dic[ctx.guild.id][duel_id] = {
		"duel_channel": duel_channel,
		"duelist": duelist,
		"victim": victim,
		"start_time": datetime.datetime.now()
		}

	# Sending the duel message
	msg = f"{victim.mention} has accepted {duelist.mention}'s duel!\nThe duel will take place in {duel_channel.mention}."
	if "private" not in args and "public" not in args:
		msg += "\n\n Everyone can react with 👁️ to this message to gain access to the duel channel as a spectateor."
	duel_msg = await ctx.send(msg)

	# If the game is private, no spectateing is allowed
	if "private" not in args and "public" not in args:
		await duel_msg.add_reaction("👁️")

		# Storing the message to allow spectateors to join
		bot.spectate_msgs[duel_msg.id] = duel_channel

	await game_on(ctx, duel_channel, duelist, victim, duel_msg)
	del bot.spectate_msgs[duel_msg.id]

# =============================================================================
# Fake commands (avoids raising useless errors)
# =============================================================================
@bot.command(pass_context=False)
async def accept(ctx):
	pass
@bot.command(pass_context=False)
async def refuse(ctx):
	pass
@bot.command(pass_context=False)
async def move(ctx):
	pass
@bot.command(pass_context=False)
async def m(ctx):
	pass
@bot.command(pass_context=False)
async def castle(ctx):
	pass
@bot.command(pass_context=False)
async def draw(ctx):
	pass
@bot.command(pass_context=False)
async def concede(ctx):
	pass

# =============================================================================
# Reads reaction for spectateor mode
# =============================================================================
@bot.event
async def on_raw_reaction_add(payload):

	if payload.message_id in bot.spectate_msgs.keys() and payload.emoji.name == "👁️" and payload.user_id != bot.user.id:
		await bot.spectate_msgs[payload.message_id].set_permissions(payload.member, read_messages=True, send_messages=False)

@bot.event
async def on_raw_reaction_remove(payload):

	pass  # Doesn't work currently. the payload of this function doesn't include the member.
# 	if payload.message_id in bot.spectate_msgs.keys() and payload.emoji.name == "👁️" and payload.user_id != bot.user.id:
# 		await bot.spectate_msgs[payload.message_id].set_permissions(message.auth, read_messages=False, send_messages=False)

#--------------------------------- Auction -----------------------------------------------------------------------------------------------------------
# Command for user registration
@bot.command()
async def auction(ctx): # acikartirma -> auction (command name not strictly translated but contextually relevant)
    user_id = ctx.author.id
    if user_id in manager.get_users():
        await ctx.send("You are already registered!") # Zaten kayıtlısınız!
    else:
        manager.add_user(user_id, ctx.author.name)
        await ctx.send("""Hello! Welcome! You have successfully registered! Every minute you will receive new images and have a chance to obtain them! To do this, you need to click the "Claim!" button! Only the first three users who click the "Claim!" button will get the image! ==""") 
        # Merhaba! Hoş geldiniz! Başarılı bir şekilde kaydoldunuz! Her dakika yeni resimler alacaksınız ve bunları elde etme şansınız olacak! Bunu yapmak için “Al!” butonuna tıklamanız gerekiyor! Sadece “Al!” butonuna tıklayan ilk üç kullanıcı resmi alacaktır! =)

# Rating command.
@bot.command()
async def rating(ctx):
    res = manager.get_rating()
    res = [f'| @{x[0]:<11} | {x[1]:<11}|\n{"_"*26}' for x in res]
    res = '\n'.join(res)
    res = f'|USER_NAME |COUNT_PRIZE|\n{"_"*26}\n' + res
    await ctx.send(f"```\n{res}\n```")

# Scheduled task to send images
@tasks.loop(minutes=1)
async def send_message():
    for user_id in manager.get_users():
        prize = manager.get_random_prize()
        if not prize:
            print("No available prizes, skipping this round.") # Kullanılabilir ödül yok, bu tur atlanıyor.
            continue # skip sending for this user if no prize is left

        prize_id, img = prize[:2]
        manager.hide_img(img)
        user = await bot.fetch_user(user_id)
        if user:
            await send_image(user, f'hidden_img/{img}', prize_id)
        manager.mark_prize_used(prize_id)

async def send_image(user, image_path, prize_id):
    with open(image_path, 'rb') as img:
        file = discord.File(img)
        button = discord.ui.Button(label="Claim!", custom_id=str(prize_id)) # Al! -> Claim!
        view = discord.ui.View()
        view.add_item(button)
        await user.send(file=file, view=view)

@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data['custom_id']
        user_id = interaction.user.id

        if manager.get_winners_count(custom_id) < 3:
            res = manager.add_winner(user_id, custom_id)
            if res:
                img = manager.get_prize_img(custom_id)
                with open(f'img/{img}', 'rb') as photo:
                    file = discord.File(photo)
                    await interaction.response.send_message(file=file, content="Congratulations, you claimed the image!") # Tebrikler, resmi aldınız!
            else:
                await interaction.response.send_message(content="You already own this image!", ephemeral=True) # Bu resme zaten sahipsiniz!
        else:
            await interaction.response.send_message(content="Unfortunately, someone else has already claimed this image...", ephemeral=True) # Maalesef, bu resmi bir başkası çoktan aldı...

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!') # olarak giriş yapıldı!
    if not send_message.is_running():
        send_message.start()

#------------------------------------- Photo And Video ----------------------------------------------------------------------------------
os.makedirs("photoandvideo", exist_ok=True)

@bot.event
async def on_ready():
    init_db()
    print(f"🤖 {bot.user} is active!") # aktivdir!

# ===================== MODAL class ===================== # MODAL sinfi

class VideoNameModal(discord.ui.Modal, title="Name the Video"): # Videoya ad ver
    def __init__(self, user_id, file_path):
        super().__init__()
        self.user_id = user_id
        self.file_path = file_path

    video_name = discord.ui.TextInput(
        label="Video Name", # Videonun adı
        placeholder="E.g.: My video test", # Məsələn: Mənim video testim
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        save_file(self.user_id, "video", self.file_path, self.video_name.value)
        await interaction.response.send_message(
            f"✅ Video saved: **{self.video_name.value}**", # Video yadda saxlanıldı:
            ephemeral=True
        )

# ============ TAKE PHOTO (WITH MODAL) ============ # ŞƏKİL ÇƏKMƏ (MODALLI)

class PhotoNameModal(discord.ui.Modal, title="Name the Photo"): # Şəklə ad ver
    def __init__(self, user_id, file_path):
        super().__init__()
        self.user_id = user_id
        self.file_path = file_path

    photo_name = discord.ui.TextInput(
        label="Photo Name", # Şəklin adı
        placeholder="E.g.: My photo", # Məsələn: Mənim şəkilim
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        save_file(self.user_id, "photo", self.file_path, self.photo_name.value)
        await interaction.response.send_message(
            f"✅ Photo saved: **{self.photo_name.value}**", # Şəkil yadda saxlanıldı:
            ephemeral=True
        )


class SavePhotoView(discord.ui.View):
    def __init__(self, user_id, file_path):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.file_path = file_path

    @discord.ui.button(label="📄 Name and Save", style=discord.ButtonStyle.primary) # Ad ver və yadda saxla
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This photo does not belong to you.", ephemeral=True) # Bu şəkil sənə aid deyil.
            return
        modal = PhotoNameModal(self.user_id, self.file_path)
        await interaction.response.send_modal(modal)


@bot.command()
async def photo(ctx):
    await ctx.send("📸 Taking photo...") # Şəkil çəkilir...

    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    if not ret:
        await ctx.send("❌ Camera could not be opened!") # Kamera açılmadı!
        return

    filename = f"photoandvideo/photo_{ctx.author.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    cv2.imwrite(filename, frame)
    cam.release()

    await ctx.send(
        "✅ Photo taken! Name it using the button below:", # Şəkil çəkildi! Aşağıdakı düymə ilə ad ver:
        file=discord.File(filename),
        view=SavePhotoView(ctx.author.id, os.path.abspath(filename))
    )
# ===================== BUTTON class ===================== # BUTTON sinfi

class SaveVideoView(discord.ui.View):
    def __init__(self, user_id, file_path):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.file_path = file_path

    @discord.ui.button(label="📄 Name and Save", style=discord.ButtonStyle.primary) # Ad ver və yadda saxla
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This video does not belong to you.", ephemeral=True) # Bu video sənə aid deyil.
            return
        modal = VideoNameModal(self.user_id, self.file_path)
        await interaction.response.send_modal(modal)

# ===================== !video COMMAND ===================== # !video KOMANDASI

@bot.command()
async def video(ctx, seconds: int = 5):
    if seconds <= 0:
        await ctx.send("⚠️ Video duration must be at least 1 second.") # Video müddəti ən azı 1 saniyə olmalıdır.
        return

    await ctx.send(f"🎥 Taking a {seconds} second video...") # saniyəlik video çəkilir...

    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        await ctx.send("❌ Camera could not be opened.") # Kamera açıla bilmədi.
        return

    width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = 20

    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    avi_filename = f"photoandvideo/temp_video_{ctx.author.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.avi"
    out = cv2.VideoWriter(avi_filename, fourcc, fps, (width, height))

    start_time = time.time()
    frame_count = 0

    while (time.time() - start_time) < seconds:
        ret, frame = cam.read()
        if not ret:
            break
        out.write(frame)
        frame_count += 1
        cv2.waitKey(1)

    cam.release()
    out.release()

    if frame_count == 0:
        await ctx.send("⚠️ Video could not be recorded.") # Video çəkilə bilmədi.
        return

    # FFMPEG MP4 conversion
    mp4_filename = avi_filename.replace(".avi", ".mp4")
    try:
        subprocess.run([
            "ffmpeg", "-i", avi_filename, "-c:v", "libx264",
            "-an", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-movflags", "faststart", "-y", mp4_filename
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        await ctx.send(f"❌ Error: {e}") # Xəta:
        return
    finally:
        if os.path.exists(avi_filename):
            os.remove(avi_filename)

    await ctx.send(
        "✅ Video taken! Name it using the button below:", # Video çəkildi! Aşağıdakı düymə ilə ad ver:
        file=discord.File(mp4_filename),
        view=SaveVideoView(ctx.author.id, os.path.abspath(mp4_filename))
    )

# ===================== !videoshow =====================

@bot.command()
async def videoshow(ctx):
    files = get_user_files(ctx.author.id, "video")
    if not files:
        await ctx.send("🎞 No videos found.") # Heç bir video tapılmadı.
        return

    options = [
        discord.SelectOption(label=(f[2] if f[2] else f"Video {f[0]}"), value=str(f[0]))
        for f in files[:10]
    ]

    select = discord.ui.Select(placeholder="Which video should I show?", options=options) # Hansı videonu göstərim?

    async def select_callback(interaction: discord.Interaction):
        file_id = int(select.values[0])
        filename = [f[1] for f in files if f[0] == file_id][0]
        await interaction.response.send_message(file=discord.File(filename))

    select.callback = select_callback
    view = discord.ui.View()
    view.add_item(select)
    await ctx.send("🎞 Video list:", view=view) # Videolar siyahısı:

#============================== Photoshow ==============================================
@bot.command()
async def photoshow(ctx):
    photos = get_user_files(ctx.author.id, "photo")
    if not photos:
        await ctx.send("🖼 No photos found.") # Heç bir şəkil tapılmadı.
        return

    options = [
        discord.SelectOption(label=(p[2] if p[2] else f"📷 Photo {p[0]}"), value=str(p[0])) # Şəkil -> Photo
        for p in photos[:10]
    ]

    select = discord.ui.Select(placeholder="Which photo should I show?", options=options) # Hansı şəkli göstərim?

    async def select_callback(interaction: discord.Interaction):
        photo_id = int(select.values[0])
        filename = [p[1] for p in photos if p[0] == photo_id][0]
        await interaction.response.send_message(file=discord.File(filename))

    select.callback = select_callback
    view = discord.ui.View()
    view.add_item(select)
    await ctx.send("🖼 Photo list:", view=view) # Şəkillər siyahısı:

#------------------------------------------------------------------------------------------------------------------------------------------
bot.run(token)
