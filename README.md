# Discord CAS

Tool for user verification via CAS on Discord server. If your organization uses
CAS for authentication, and if you also run a Discord server whose private
contents should only be accessible to CAS authenticated users, then this is the
right tool for you.

Once a user are authenticated on any one server, they will not need to repeat
the whole signup process on another server.

## Contributions

Feel free to make a PR/issue for feature implementation/request.

Formating for python is done with Black with a 80 character limit.
Formating for javascript isnt strict as long as 80 character limit is followed.

## Privacy policy

When a user authenticates with our web portal, we store their following
information:

1. Full Name
1. Email
1. Roll number
1. DiscordID.

1,2,3 are obtained from CAS, and 4 is obtained from Discord OAuth.

This data is used strictly for authentication only, and not visible publicly.
It is only visible to the server host.

The bot does not track any interactions. If a user does not authenticate with
our portal, we store no data.

## License

MIT

## Adding the bot

1. Make a pull request to the server by editing the `server_config.ini` file per your server requirements (see subsection below for more details)
2. Create a new role for the bot, which satisfies the criteria given in the next section.
3. **After** your PR is merged, navigate to the [this URL](https://osdg.iiit.ac.in/casbot/discord/invite) to invite the bot and add it to your server. Note that you must have "Manage Server" permission on this server. (If you're new to Discord roles, read the FAQ:
   [link](https://support.discord.com/hc/en-us/articles/214836687-Role-Management-101))

### Configuration parameters

The following configuration are possible through `server_config.ini`:

1. `setrealname`: set member nickname (post verification) equal to their real name (obtained from CAS).
2. `grantroles`: a comma-separated list of roles you'd like to assign to the member post-verification. If the roles do not exist in the server, they'll be created automatically.
3. `serverid`: ID of the Discord server. See [Discord FAQ](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-). (In Discord lingo, a server is known as a guild.)
4. `deleteroles`: a comma-separated list of roles you'd like to remove from the member post-verification. For example, if new users get the `unverified` role on joining your server, you can set `deleteroles=unverified`.

`deleteroles`, `setrealname` are optional. If you don't specify a value for them, it's picked up from the `[DEFAULT]` section at the top.

#### Example usage

```
[Chess Club]
serverid=724827932778037370
setrealname=yes
grantroles=Verified,IIIT
```

### Regarding the bot role

You can create a new "Bot" role in your server and give it to our bot. This role should satisfy the following criteria:

1. The bot will only give the user role A if the bot's topmost role is above role A.
2. To change the nickname for a user, the user's highest role should be lower than the bot's highest role.
3. The bot should have read access to the channel to read `.verify` commands
4. The bot should have write access to the channel to give feedback on verification (Success/Failure).

(If you're new to Discord roles, read the FAQ: [link](https://support.discord.com/hc/en-us/articles/214836687-Role-Management-101))

### Notes

1. `.verify` might not work for server-admins. That indicates your role setup does not follow the criteria above.

If at any point you face any difficulty, please raise a new issue in this GitHub repository.

## Current deployment status

The current instance of the bot used by IIIT-H clubs is hosted by:

| Name           | Time period                | Server                  |
| -------------- | -------------------------- | ----------------------- |
| Ankith Pai     | March 19, 2024 -           | https://osdg.iiit.ac.in |
| Shamil         | 2022 - early 2024          | https://osdg.iiit.ac.in |
| Gaurang Tandon | late June 21 - 2022 ??     | ??                      |
| Vidit Jain     | April 6, 21 - late June 21 | ??                      |

This instance is intended to be used only by IIIT-H related discord servers. See the section below if you want to host the project for any other purpose.

## Hosting the project

This project is made up of two parts, the web portal and the discord bot.

The web portal does four things:

1. Authenticates you against Discord OAuth2.
2. Authenticates you against a CAS portal (feel free to change this to SAML, OAuth2, or whatever your organization prefers to use).
3. Stores this data in MongoDB.
4. Checks if the server is allowed in `server_config.ini`

You may need to change the source code corresponding to your organization's CAS attributes; specifically, the `/cas` express endpoint has settings for which attributes to fetch from the CAS server response.

### Dependencies

We use `docker` and `docker-compose`.

For instance, on an Ubuntu 22.04 server one would install them with:
`sudo apt install docker.io docker-compose`

### Setting up MongoDB

For our deployed instance, we are using MongoDB Atlas. If you don't want to use a cloud service, you could set up a mongo server instance from docker-compose, that the portal and bot containers get access to.

### Configuring secrets and parameters needed

Change the config parameters in `.env.template` and rename it to `.env`.

### Running and stopping the project

A simple `./run.sh` and `./stop.sh` starts and stops the project respectively (these commands use docker-compose and take care of both `./portal` and `./bot`, in separate containers)

### Configuring systemd unit

On a deployment server, it is useful to run above scripts in a systemd unit. Here is a sample:

```
[Unit]
Description=Runs CASBOT in /home/bots
After=docker.service
Requires=docker.service

[Service]
Environment="CASBOT_DIR=/home/bots/Discord-CAS"
Restart=always
ExecStartPre=/home/bots/Discord-CAS/stop.sh
ExecStart=/home/bots/Discord-CAS/run.sh

[Install]
WantedBy=multi-user.target
```

This file is stored in `/etc/systemd/system/casbot.service`, and assumes that the source code of the repo is in `/home/bots/Discord-CAS`.
