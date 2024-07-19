import discord
from discord.ext import commands
import os
import pokebase
import pymongo
import math

# MongoDB connection
mongo_uri = os.environ.get('MONGODB_URI')  # Retrieve MongoDB URI from environment variables
mongo_client = pymongo.MongoClient(mongo_uri)
db = mongo_client.get_default_database("discord_bot")  # Use the default database provided in the URI
collection = db["moves"]  # Collection to store registered moves

# Discord bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='$', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command(name='registermoves')
async def register_moves(ctx, move1, move2, move3, move4):
    moves_to_register = [move1.lower(), move2.lower(), move3.lower(), move4.lower()]

    # Ensure exactly 4 moves are provided
    if len(moves_to_register) != 4:
        await ctx.send('Please provide exactly 4 moves to register.')
        return

    # Connect to MongoDB and find or create user
    user_data = collection.find_one({"discord_id": str(ctx.author.id)})
    if not user_data:
        user_data = {
            "discord_id": str(ctx.author.id),
            "username": str(ctx.author),
            "registered_moves": []
        }

    # Validate moves and register them
    validated_moves = []
    for move_name in moves_to_register:
        move_data = await get_move_data(move_name)
        if move_data:
            validated_moves.append(move_data['name'])
        else:
            await ctx.send(f"Move '{move_name}' not found. Please enter valid move names.")
            return

    # Update user's registered moves
    user_data["registered_moves"] = validated_moves
    collection.update_one({"discord_id": str(ctx.author.id)}, {"$set": user_data}, upsert=True)

    await ctx.send(f"Moves registered successfully for {ctx.author.mention}.")

@bot.command(name='viewmoves')
async def view_moves(ctx):
    # Retrieve user's registered moves from MongoDB
    user_data = collection.find_one({"discord_id": str(ctx.author.id)})
    if not user_data or not user_data.get('registered_moves'):
        await ctx.send(f"You haven't registered any moves yet, {ctx.author.mention}.")
        return

    registered_moves = user_data['registered_moves']
    
    # Format move names: capitalize each word properly and replace underscores with spaces
    formatted_moves = []
    for move in registered_moves:
        parts = move.split('_')
        capitalized_parts = [part.capitalize() for part in parts]
        formatted_move = ' '.join(capitalized_parts)
        formatted_moves.append(formatted_move)
    
    # Create an embed for displaying registered moves
    embed = discord.Embed(title=f"{ctx.author}'s Registered Moves", color=discord.Color.green())
    for index, move_name in enumerate(formatted_moves):
        embed.add_field(name=f"Move {index+1}", value=move_name, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='replacemoves')
async def replace_moves(ctx, move1, move2, move3, move4):
    moves_to_replace = [move1.lower(), move2.lower(), move3.lower(), move4.lower()]

    # Ensure exactly 4 moves are provided
    if len(moves_to_replace) != 4:
        await ctx.send('Please provide exactly 4 moves to replace.')
        return

    # Validate moves
    validated_moves = []
    for move_name in moves_to_replace:
        move_data = await get_move_data(move_name)
        if move_data:
            validated_moves.append(move_data['name'])
        else:
            await ctx.send(f"Move '{move_name}' not found. Please enter valid move names.")
            return

    # Update user's registered moves
    user_data = {
        "discord_id": str(ctx.author.id),
        "username": str(ctx.author),
        "registered_moves": validated_moves
    }
    collection.update_one({"discord_id": str(ctx.author.id)}, {"$set": user_data}, upsert=True)

    await ctx.send(f"Moves replaced successfully for {ctx.author.mention}.")

@bot.command(name='moveinfo')
async def move_info(ctx, move_name):
    try:
        move = pokebase.move(move_name.lower())
    except ValueError:
        await ctx.send(f"Move '{move_name}' not found. Please enter a valid move name.")
        return

    # Fetch move details
    move_name = move.name.capitalize()
    pp = move.pp if move.pp is not None else "N/A"
    accuracy = move.accuracy if move.accuracy is not None else "N/A"
    power = move.power if move.power is not None else "N/A"
    move_category = move.damage_class.name.capitalize()

    # Determine move description
    if move.effect_entries:
        move_desc = move.effect_entries[0].short_effect
    else:
        move_desc = "No description available."

    # Create an embed for move details
    embed = discord.Embed(title=f"Move Info: {move_name}",
                          description=move_desc,
                          color=discord.Color.blue())
    embed.add_field(name="PP", value=pp, inline=True)
    embed.add_field(name="Accuracy", value=accuracy, inline=True)
    embed.add_field(name="Power", value=power, inline=True)
    embed.add_field(name="Category", value=move_category, inline=False)

    await ctx.send(embed=embed)
    
@bot.command(name='ttmove')
async def tt_move(ctx, move_name):
    try:
        move = pokebase.move(move_name.lower())
    except ValueError:
        await ctx.send(f"Move '{move_name}' not found. Please enter a valid move name.")
        return

    # Initialize ep_cost with a default value of 0
    ep_cost = 0

    # Determine move category and description
    if move.name.lower() in ['dragon-rage', 'sonic-boom', 'night-shade', 'seismic-toss']:  # Add more moves if needed
        converted_damage = "This move deals static damage equal to the user's level."
        move_category = "Basic"
    elif move.damage_class.name == 'status':
        # Fetch the move description from Pokebase
        move_desc = move.effect_entries[0].short_effect if move.effect_entries else "No description available."
        converted_damage = move_desc
        move_category = "Status"
        # Calculate dungeon usage based on max PP
        if move.pp and move.pp >= 60:
            ep_cost = "This move can be used 3 times in a dungeon."
        elif move.pp and move.pp >= 30:
            ep_cost = "This move can be used 2 times in a dungeon."
        else:
            ep_cost = "This move can be used 1 time in a dungeon."
    elif move.damage_class.name in ['physical', 'special']:
        if move.power is not None and move.power > 0:
            d = 'd' + str(math.ceil(move.power / 10))
            converted_damage = f"({d}) + ATK" if move.damage_class.name == 'physical' else f"({d}) + Sp.ATK"
            move_category = "Standard"
            # Calculate EP (Energy Points) cost based on move's base power
            if move.power and move.power > 90:
                ep_cost = 5
            elif move.power and move.power >= 70:
                ep_cost = 2
            elif move.power and move.power >= 1:
                ep_cost = 1
            else:
                ep_cost = 0  # Set EP cost to 0 for Basic moves and moves with no power
        else:
            converted_damage = "This move deals static damage equal to the user's level."
            move_category = "Basic"
    else:
        converted_damage = "This move deals static damage equal to the user's level."
        move_category = "Basic"

    # Determine if move is Multi-Hit
    additional_info = ""
    if move.effect_entries:
        for effect in move.effect_entries:
            if 'hits' in effect.short_effect.lower():
                move_category = "Multi-Hit"
                additional_info = "Roll a d4 + 1 to determine how many hits landed."
                ep_cost = 2  # Set EP cost specifically for Multi-Hit moves
                break

    # Create an embed for move details
    embed = discord.Embed(title=f"Table Top Converted Version: {move.name.capitalize()}",
                          color=discord.Color.orange())
    embed.add_field(name="Table Top Formula", value=converted_damage, inline=False)
    if move_category == "Status":
        embed.add_field(name="Dungeon Usage", value=ep_cost, inline=False)
    else:
        embed.add_field(name="EP Cost", value=f"{ep_cost} EP", inline=False)
    embed.add_field(name="Move Category", value=move_category, inline=False)
    if move_category == "Multi-Hit":
        embed.add_field(name="Additional Info", value=additional_info, inline=False)

    await ctx.send(embed=embed)
    
@bot.command(name='helpmenu')
async def help_menu(ctx):
    # Create an embed for the help menu
    embed = discord.Embed(title="Command Menu", description="List of available commands:", color=discord.Color.gold())

    # Add fields for each command with brief descriptions
    embed.add_field(name="$registermoves move1 move2 move3 move4", value="Registers 4 moves to your profile.", inline=False)
    embed.add_field(name="$viewmoves", value="Displays your registered moves.", inline=False)
    embed.add_field(name="$replacemoves move1 move2 move3 move4", value="Replaces your registered moves with new ones.", inline=False)
    embed.add_field(name="$moveinfo move-name", value="Shows details (PP, accuracy, power, category) of a specific move. If your move is separated by a space, type it with a -.", inline=False)
    embed.add_field(name="$ttmove move-name", value="Displays the Table Top converted version of a move (damage formula, EP cost, type, etc.). If your move is separated by a space, type it with a -.", inline=False)
    embed.add_field(name="$helpmenu", value="Displays this command menu.", inline=False)

    await ctx.send(embed=embed)

async def get_move_data(move_name):
    try:
        move = pokebase.move(move_name.lower())
        move_type = move.type.name if hasattr(move, 'type') and move.type else 'Unknown'
        move_data = {
            'name': move.name,
            'type': move_type,
            'power': move.power if hasattr(move, 'power') and move.power else 0,
            'accuracy': move.accuracy if hasattr(move, 'accuracy') and move.accuracy else 0,
            'pp': move.pp if hasattr(move, 'pp') and move.pp else 0,
            'damage_class': move.damage_class.name if hasattr(move, 'damage_class') and move.damage_class else 'Unknown',
            'effect_entries': move.effect_entries if hasattr(move, 'effect_entries') else None
            # Add more fields as needed
        }
        return move_data
    except ValueError:
        return None

# Run the bot
bot.run(os.environ.get('DISCORD_BOT_TOKEN'))  # Retrieve Discord bot token from environment variables
