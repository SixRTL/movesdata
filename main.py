@bot.command(name='ttmove')
async def tt_move(ctx, move_name):
    try:
        move = pokebase.move(move_name.lower())
    except ValueError:
        await ctx.send(f"Move '{move_name}' not found. Please enter a valid move name.")
        return

    # Determine move category and description
    if move.damage_class.name == 'physical':
        d = 'd' + str(math.ceil(move.power / 10)) if move.power else 'd0'
        converted_damage = f"({d}) + ATK"
        move_category = "Standard"
    elif move.damage_class.name == 'special':
        d = 'd' + str(math.ceil(move.power / 10)) if move.power else 'd0'
        converted_damage = f"({d}) + Sp.ATK"
        move_category = "Standard"
    elif move.damage_class.name == 'status':
        converted_damage = "This move is non-damaging and provides a status effect."
        move_category = "Status"
    elif move.name.lower() == 'dragon-rage':
        converted_damage = "This move deals a fixed amount of damage."
        move_category = "Basic"
    elif move.damage_class.name == 'basic' or move.power in [0, None]:
        converted_damage = "This move deals static damage equal to the user's level."
        move_category = "Basic"
    else:
        converted_damage = "Unknown"
        move_category = "Unknown"

    # Calculate EP (Energy Points) cost based on move's base power
    if move.power and move.power > 90:
        ep_cost = 5
    elif move.power and move.power >= 70:
        ep_cost = 2
    elif move.power and move.power >= 1:
        ep_cost = 1
    else:
        ep_cost = 0  # Set EP cost to 0 for Basic moves and moves with no power

    # Determine if move is Multi-Hit
    additional_info = ""
    if move.effect_entries:
        for effect in move.effect_entries:
            if 'hits' in effect.short_effect.lower():
                move_category = "Multi-Hit"
                additional_info = "Roll a d4 + 1 to determine how many hits landed."
                ep_cost = f"2({additional_info})"
                break

    # Create an embed for move details
    embed = discord.Embed(title=f"Table Top Converted Version: {move.name.capitalize()}",
                          color=discord.Color.orange())
    embed.add_field(name="Table Top Formula", value=converted_damage, inline=False)
    embed.add_field(name="EP Cost", value=f"{ep_cost} EP", inline=False)
    embed.add_field(name="Move Category", value=move_category, inline=False)
    if move_category == "Multi-Hit":
        embed.add_field(name="Additional Info", value=additional_info, inline=False)

    await ctx.send(embed=embed)
