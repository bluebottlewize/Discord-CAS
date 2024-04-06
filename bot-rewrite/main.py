"""
The CAS bot is defined here. Utility methods for verification, fetching details, roles, nicknames
etc. are defined, as well the bot commands and a main routine.

This module defines the following functions.

- `get_users_from_discordid()`: Find users from DB given user ID
- `is_verified()`: If a user is present in DB or not
- `get_realname_from_discordid()`: Get a user's real name from their Discord ID.
- `send_link()`: Send link for reattempting authentication.
- `get_config()`: Gives the config object for a given server.
- `create_roles_if_missing()`: Adds missing roles to a server.
- `assign_role()`: Adds specified roles to the given user post-verification.
- `delete_role()`: Removes specified roles from the given user post-verification.
- `set_nickname()`: Sets nickname of the given user to real name if server specifies.
- `post_verification()`: Handle role add/delete and nickname set post-verification of given user.
- `verify_user()`: Implements `.verify`.
- `backend_info()`: Logs server details for debug purposes
- `is_academic()`: Checks if server is for academic use.
- `query()`: Returns user details, uses Discord ID to find in DB.
- `query_error()`: Replies eror message if server is not academic.
- `roll()`: Returns user details, uses roll number to find in DB.
- `roll_error()`: Replies eror message if server is not academic.
- `on_ready()`: Logs a message when the bot joins a server.
- `main()`: Reads server config, loads DB and starts bot.

"""
import sys
import asyncio
import platform

import discord
from discord.ext import commands
from discord.utils import get

from pymongo import MongoClient, database

from config_verification import read_and_validate_config
from components.variables import Variables


TOKEN = Variables.DISCORD_TOKEN
MONGO_DATABASE = Variables.MONGO_DATABASE
MONGO_URI = Variables.MONGO_URI
BASE_URL = Variables.MONGO_DATABASE
SERVER_CONFIG = Variables.SERVER_CONFIG


class CasBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        intents = discord.Intents.none()
        intents.messages = True
        intents.guilds = True
        intents.members = True
        intents.message_content = True

        super().__init__(command_prefix=".", intents=intents)

    async def setup_hook(self) -> None:
        # Register the persistent view for listening here.
        # Note that this does not send the view to any message.
        # In order to do this you need to first send a message with the View, which is shown below.
        # If you have the message_id you can also pass it as a keyword argument, but for this example
        # we don't have one.
        self.add_view(VerifyButton())
        # For dynamic items, we must register the classes instead of the views.
        # self.add_dynamic_items(DynamicButton)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')


bot = CasBot()


# bot = commands.Bot(command_prefix=".", intents=intents)
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
    return True if get_users_from_discordid(user_id) else False


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
    return None


def get_first_channel_with_permission(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            return channel

    return None


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

    if server_config is None:
        await ctx.send(
                "This server is not authorized to work with CAS-bot. Read the instructions to invite the bot in the project README"
                )
        await ctx.guild.leave()
        return

    await assign_role(ctx.guild, user, server_config)
    await delete_role(ctx.guild, user, server_config)

    try:
        await set_nickname(user, server_config)
    except: # pylint: disable=bare-except
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
    """For debugging server info; sends details of the server."""
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
    server_config = get_config(str(ctx.guild.id))

    if server_config is None:
        return False
    return server_config.get("is_academic", False)



@bot.command(name="query")
@commands.check(is_academic)
async def query(
    ctx: commands.Context,
    identifier: discord.User,
):
    """
    First checks if the server is an academic one. If so, finds the user who invoked the
    command (by Discord ID) in the DB. If present, replies with their name, email and
    roll number. Otherwise replies telling the user they are not registed with CAS.
    """
    user = db.users.find_one({"discordId": str(identifier.id)})
    if user:
        await ctx.reply(
            f"Name: {user['name']}\nEmail: {user['email']}\nRoll Number: {user['rollno']}"
        )
    else:
        await ctx.reply(f"{identifier} is not registered with IIIT-CAS.")


@query.error
async def query_error(ctx, error):
    """
    For the `query` command, if the server is not academic, replies with error message.
    """
    if isinstance(error, commands.CheckFailure):
        await ctx.reply("This server is not for academic purposes.")


@bot.command(name="roll")
@commands.check(is_academic)
async def roll(
    ctx: commands.Context,
    identifier: int,
):
    """
     First checks if the server is an academic one. If so, finds the user who invoked the
    command in the DB. If present, replies with their name, email and
    roll number. Otherwise replies telling the user they are not registed with CAS.

    Same as the `query` command, except this searches by roll number instead of Discord ID.
    """
    user = db.users.find_one({"rollno": str(identifier)})
    if user:
        await ctx.reply(
            f"Name: {user['name']}\nEmail: {user['email']}\nRoll Number: {user['rollno']}"
        )
    else:
        await ctx.reply(f"{identifier} is not registered with IIIT-CAS.")


@roll.error
async def roll_error(ctx, error):
    """
    For the `roll` command, if the server is not academic, replies with error message.
    """
    if isinstance(error, commands.CheckFailure):
        await ctx.reply("This server is not for academic purposes.")


@bot.event
async def on_guild_join(guild):
    server_id = str(guild.id)
    server_config = get_config(server_id)

    welcome_message = "CAS-bot has joined this server"

    channel = get(guild.text_channels, name='cas-verification')
    if channel is None:
        channel = await guild.create_text_channel('cas-verification')

    # first_channel = get_first_channel_with_permission(guild)

    if not server_config:
        welcome_message = "This server is not authorized to work with CAS-bot. Read the instructions to invite the bot in the project README."
        if channel:
            await channel.send(welcome_message)
        await guild.leave()
        return

    if channel:
        await channel.send(welcome_message, view=VerifyButton())


@bot.event
async def on_ready():
    """This is executed when the bot connects to a server."""
    print(f"{bot.user.name} has connected to Discord!")


class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Button", custom_id="verify")
    async def gray_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await bot.get_context(interaction.message)
        await ctx.invoke(bot.get_command("verify"))
        await interaction.response.send_message(content="This is an edited button response!")


def main():
    """
    First it checks if each server has a valid configuration. If not, it exits with an error.
    Otherwise, It iniates a client for a MongoDB instance and fetches the database from there,
    setting the global variable `db`. Then it starts the bot.
    """
    # global db # pylint: disable=global-statement

    if not read_and_validate_config(SERVER_CONFIG, "../server_config.ini"):
        sys.exit(1)

    # mongo_client = MongoClient(
    #    f"{MONGO_URI}/{MONGO_DATABASE}?retryWrites=true&w=majority"
    # )
    # db = mongo_client.get_database(MONGO_DATABASE)

    bot.run(TOKEN)


if __name__ == "__main__":
    main()
