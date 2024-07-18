import discord
from discord.ext import commands
import pymongo
import os
import pokebase

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
            # Add more fields as needed
        }
        return move_data
    except ValueError:
        return None

# Run the bot
bot.run(os.environ.get('DISCORD_BOT_TOKEN'))  # Retrieve Discord bot token from environment variables
