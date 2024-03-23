import os
import sys
import asyncio
from configparser import ConfigParser
import platform
from dotenv import load_dotenv

import discord
from discord.ext import commands

from pymongo import MongoClient, database

from config_verification import read_and_validate_config

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
MONGO_DATABASE = os.getenv("MONGO_DATABASE")
MONGO_URI = os.getenv("MONGO_URI")
BASE_URL = os.getenv("BASE_URL")
SERVER_CONFIG = ConfigParser()

bot = commands.Bot(command_prefix=".")
db: database.Database = None  # assigned in main function


def get_users_from_discordid(user_id):
    """
    Finds users from the database, given their ID and returns
    a list containing those users.
    """
    users = list(db.users.find({"discordId": str(user_id)}))
    return users


def is_verified(user_id):
    """Checks if any user with the given ID exists in the DB or not."""
    return len(get_users_from_discordid(user_id)) == 0


def get_realname_from_discordid(user_id):
    """Returns the real name of the first user who matches the given ID."""
    users = get_users_from_discordid(user_id)
    assert users
    return users[0]["name"]


async def send_link(ctx):
    """Sends the base url for users to reattempt sign-in."""
    await ctx.send(f"<{BASE_URL}>\nSign in through our portal, and try again.")


def get_config(server_id: str):
    """Returns the configuration object for a given Discord server (given server ID)
    if it is present in the server config file."""
    for section in SERVER_CONFIG.sections():
        section_obj = SERVER_CONFIG[section]
        if section_obj["serverid"] == server_id:
            return section_obj

    print(f"Server id {server_id} not found in server config")
    sys.exit(1)


async def create_roles_if_missing(guild, req_guild_roles):
    """Creates roles for the given guild if they are missing."""
    for role in req_guild_roles:
        roles_present = guild.roles
        role_names = [role.name for role in roles_present]

        if role not in role_names:
            await guild.create_role(name=role)


async def assign_role(guild, user, server_config):
    """For a given guild, user and server confg object, creates roles in the guild if missing,
    and then assigns the guild's roles to the user post-verification.
    """
    req_roles = server_config["grantroles"].strip().split(",")

    await create_roles_if_missing(guild, req_roles)

    assign_roles = [role for role in guild.roles if role.name in req_roles]

    await user.add_roles(*assign_roles)


async def delete_role(guild, user, server_config):
    """
    For a given guild, user and server config object, remove roles that the server specified
    to be deleted post-verification.
    """
    config_remove_roles = server_config["deleteroles"].strip().split(",")
    to_remove_roles = [role for role in guild.roles if role.name in config_remove_roles]

    # if the user does not have that role, this does not crash
    await user.remove_roles(*to_remove_roles)


async def set_nickname(user, server_config):
    """If the server wants users to have their actual names as server nicknames,
    set the given user's nickname to their name fetched from the database.
    """
    if server_config["setrealname"] == "no":
        return

    realname = get_realname_from_discordid(user.id)
    await user.edit(nick=realname)


async def post_verification(ctx, user):
    """
    For the Discord context and the given user, assign roles to be added post-verification
    and remove roles to be deleted post verification as specified in the serve's config object.
    """
    server_id = str(ctx.guild.id)
    server_config = get_config(server_id)

    await assign_role(ctx.guild, user, server_config)
    await delete_role(ctx.guild, user, server_config)

    try:
        await set_nickname(user, server_config)
    except:
        await ctx.send("Bot should have a role higher than you to change your nickname")

    await ctx.send(f"<@{user.id}> has been CAS-verified!")


@bot.command(name="verify")
async def verify_user(ctx):
    """
    Runs when the user types `.verify` in the server. First tries to find the user in the DB.
    If present, performs post-verification actions. If not verified, Sends the link to authenticate
    and waits for a minute. xits if the user still is not found after that and
    tells user to run `.verify` again.
    """
    author = ctx.message.author
    user_id = author.id

    for i in range(2):
        verification = is_verified(user_id)

        if verification:
            await post_verification(ctx, author)
            break
        if i == 0:
            await send_link(ctx)
            await asyncio.sleep(60)
        else:
            await ctx.send(
                f"Sorry <@{user_id}>, could not auto-detect your verification. \
                    Please run `.verify` again."
            )

@bot.command(name="backend_info")
async def backend_info(ctx):
    uname = platform.uname()
    await ctx.send(
        f"Here are the server details:\n"
        f"system: {uname.system}\n"
        f"node: {uname.node}\n"
        f"release: {uname.release}\n"
        f"version: {uname.version}\n"
        f"machine: {uname.machine}"
    )

def is_academic(ctx: commands.Context):
    """Checks if the server is an academic server."""
    return get_config(str(ctx.guild.id)).get("is_academic", False)


@bot.command(name="query")
@commands.check(is_academic)
async def query(
    ctx: commands.Context,
    identifier: discord.User,
):
    user = db.users.find_one({"discordId": str(identifier.id)})
    if user:
        await ctx.reply(
            f"Name: {user['name']}\nEmail: {user['email']}\nRoll Number: {user['rollno']}"
        )
    else:
        await ctx.reply(f"{identifier} is not registered with IIIT-CAS.")


@query.error
async def query_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.reply("This server is not for academic purposes.")


@bot.command(name="roll")
@commands.check(is_academic)
async def roll(
    ctx: commands.Context,
    identifier: int,
):
    user = db.users.find_one({"rollno": str(identifier)})
    if user:
        await ctx.reply(
            f"Name: {user['name']}\nEmail: {user['email']}\nRoll Number: {user['rollno']}"
        )
    else:
        await ctx.reply(f"{identifier} is not registered with IIIT-CAS.")


@roll.error
async def roll_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.reply("This server is not for academic purposes.")


@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!")


def main():
    global db

    if not read_and_validate_config(SERVER_CONFIG, "server_config.ini"):
        sys.exit(1)

    mongo_client = MongoClient(
        f"{MONGO_URI}/{MONGO_DATABASE}?retryWrites=true&w=majority"
    )
    db = mongo_client.get_database(MONGO_DATABASE)

    bot.run(TOKEN)


if __name__ == "__main__":
    main()
