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

@bot.command(name='movestatus')
async def move_status(ctx, *, move_name):
    try:
        # Replace hyphens with spaces and capitalize each word properly
        formatted_move_name = move_name.replace('-', ' ').title()
        
        move = pokebase.move(formatted_move_name.lower())
        
        # Validate move data
        if not move:
            raise ValueError
        
        # Format move details
        move_type = move.type.name.capitalize() if move.type else 'Unknown'
        move_power = move.power if move.power is not None else 'Unknown'
        move_accuracy = move.accuracy if move.accuracy is not None else 'Unknown'
        move_pp = move.pp if move.pp is not None else 'Unknown'
        move_category = move.damage_class.name.capitalize() if move.damage_class else 'Unknown'

        # Create an embed for move details
        embed = discord.Embed(title=f"Move Details: {formatted_move_name}", color=discord.Color.blue())
        embed.add_field(name="Type", value=move_type, inline=True)
        embed.add_field(name="Power", value=move_power, inline=True)
        embed.add_field(name="Accuracy", value=move_accuracy, inline=True)
        embed.add_field(name="PP", value=move_pp, inline=True)
        embed.add_field(name="Category", value=move_category, inline=True)

        await ctx.send(embed=embed)

    except ValueError:
        await ctx.send(f"Move '{move_name}' not found. Please enter a valid move name.")

@bot.command(name='ttmove')
async def tt_move(ctx, move_name):
    try:
        move = pokebase.move(move_name.lower())
    except ValueError:
        await ctx.send(f"Move '{move_name}' not found. Please enter a valid move name.")
        return

    # Calculate Table Top (D&D converted) version
    if move.damage_class.name == 'physical':
        d = 'd' + str(math.ceil(move.power / 10))
        converted_damage = f"({d}) + ATK"
    elif move.damage_class.name == 'special':
        d = 'd' + str(math.ceil(move.power / 10))
        converted_damage = f"({d}) + Sp.ATK"
    else:
        converted_damage = "This move is not a damaging move."

    # Calculate EP (Energy Points) cost based on move's base power
    if move.power > 90:
        ep_cost = 5
    elif move.power >= 70:
        ep_cost = 2
    else:
        ep_cost = 1

    # Determine if move is Multi-Hit
    if move.effect_entries:
        for effect in move.effect_entries:
            if 'hits' in effect.short_effect.lower():
                move_type = "Multi-Hit"
                break
        else:
            move_type = "Standard"
    else:
        move_type = "Unknown"

    # Create an embed for Table Top (D&D converted) version with EP cost and type
    embed = discord.Embed(title=f"Table Top Converted Version: {move.name.capitalize()}", color=discord.Color.orange())
    embed.add_field(name="Table Top Formula", value=converted_damage, inline=False)
    embed.add_field(name="EP Cost", value=f"{ep_cost} EP", inline=False)
    embed.add_field(name="Move Type", value=move_type, inline=False)

    await ctx.send(embed=embed)

@bot.command(name='helpmenu')
async def help_menu(ctx):
    # Create an embed for the help menu
    embed = discord.Embed(title="Command Menu", description="List of available commands:", color=discord.Color.gold())

    # Add fields for each command with brief descriptions
    embed.add_field(name="$registermoves move1 move2 move3 move4", value="Registers 4 moves to your profile.", inline=False)
    embed.add_field(name="$viewmoves", value="Displays your registered moves.", inline=False)
    embed.add_field(name="$replacemoves move1 move2 move3 move4", value="Replaces your registered moves with new ones.", inline=False)
    embed.add_field(name="$movestatus move_name", value="Shows details (PP, accuracy, power, category) of a specific move.", inline=False)
    embed.add_field(name="$ttmove move_name", value="Displays the Table Top converted version of a move (damage formula, EP cost, and type).", inline=False)
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
