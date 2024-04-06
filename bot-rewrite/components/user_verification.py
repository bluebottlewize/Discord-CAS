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