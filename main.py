import discord
from discord.ext import commands
import pymongo
import os
import requests

# MongoDB connection
mongo_uri = os.environ.get('MONGODB_URI')  # Retrieve MongoDB URI from Heroku config vars
mongo_client = pymongo.MongoClient(mongo_uri)
db = mongo_client.get_default_database()  # Use the default database provided in the URI
collection = db["moves"]  # Replace with your collection name

# Discord bot setup
bot = commands.Bot(command_prefix='/')  # Change the prefix as desired

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
        move_data = get_move_data(move_name)
        if move_data:
            validated_moves.append(move_data['name'])
        else:
            await ctx.send(f"Move '{move_name}' not found. Please enter valid move names.")
            return
    
    # Update user's registered moves
    user_data["registered_moves"] = validated_moves
    collection.update_one({"discord_id": str(ctx.author.id)}, {"$set": user_data}, upsert=True)
    
    await ctx.send(f"Moves registered successfully for {ctx.author.mention}.")

def get_move_data(move_name):
    url = f"https://pokeapi.co/api/v2/move/{move_name}/"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Run the bot
bot.run(os.environ.get('DISCORD_BOT_TOKEN'))  # Retrieve Discord bot token from Heroku config vars
