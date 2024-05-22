const express = require("express");

const config = require("./utils/config");
const logger = require("./utils/logger");

const app = express();

app.use(
  express.json({
    verify: (req, res, buf, encoding) => {
      if (buf && buf.length) {
        req.rawBody = buf.toString(encoding || "utf8");
      }
    },
  }),
);

app.get(`${config.SUBPATH}/test`, (req, res) => {
  res.send("Hello World!");
});

app.post(`${config.SUBPATH}/webhooks/update`, async (req, res) => {
  res.send("This endpoint has been removed.");
});

app.get(`${config.SUBPATH}/`, (req, res) => {
  res.redirect(`${config.SUBPATH}/discord`);
});

app.get(`${config.SUBPATH}/discord`, (req, res) => {
  // this endpoint has been removed, redirect to /cas endpoint which spits the
  // error message
  res.redirect(`${config.SUBPATH}/cas`);
});

app.get(`${config.SUBPATH}/discord/invite`, (req, res) => {
  let redirect_uri = `${config.BASE_URL}/bot`;
  res.redirect(
    `https://discord.com/oauth2/authorize?client_id=${config.DISCORD_CLIENT_ID}&permissions=275347671040&redirect_uri=${redirect_uri}&response_type=code&scope=bot`,
  );
});

async function makeQuery(code, redirect_uri) {
  const creds = btoa(`${config.DISCORD_CLIENT_ID}:${config.DISCORD_SECRET}`);

  const data = {
    grant_type: "authorization_code",
    code: code,
    redirect_uri,
  };

  const _encode = (obj) => {
    let string = "";

    for (const [key, value] of Object.entries(obj)) {
      if (!value) continue;
      string += `&${encodeURIComponent(key)}=${encodeURIComponent(value)}`;
    }
    return string.substring(1);
  };

  const params = _encode(data);

  const response = await fetch("https://discordapp.com/api/oauth2/token", {
    method: "POST",
    headers: {
      Authorization: `Basic ${creds}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: params,
  });

  return await response.json();
}

app.get(`${config.SUBPATH}/discord/callback`, async (req, res) => {
  // this endpoint has been removed, redirect to /cas endpoint which spits the
  // error message
  res.redirect(`${config.SUBPATH}/cas`);
});

app.get(`${config.SUBPATH}/bot`, async (req, res) => {
  if (!req.query.code || !req.query.guild_id) {
    res.send("You are not discord :angry:", 400);
    return;
  }

  const code = req.query.code;
  const redirect_uri = `${config.BASE_URL}/bot`;
  const responseJson = await makeQuery(code, redirect_uri);
  if (responseJson && responseJson.access_token) {
    res.send("Added successfully!");
  } else {
    logger.error(responseJson);
    res.send("Unkown error occured");
  }
});

const CAS = require("cas");

const cas = new CAS({
  base_url: config.CAS_LINK,
  service: config.BASE_URL,
  version: 2.0,
});

app.get(`${config.SUBPATH}/cas`, async (req, res) => {
  if (!req.query.token) {
    res.send(
      "Your verification link is invalid (may be expired or used already).\n"
      + "Please run /verify again and use the new link", 400);
    return;
  }

  await cas.authenticate(
    req,
    res,
    async (err, status, username, extended) => {
      if (err) {
        res.send("Some error occured with the CAS server :pensive:", 500);
      } else {
        if (!status) {
          /* TODO: Identify what status false means */
          res.send("Status false?", 500);
        }

        let rollno;
        try {
          rollno = extended.attributes.rollno[0];
        } catch (e) {
          rollno = "not-existent";
          logger.info("User roll number does not exist");
        }

        let name = extended.attributes.name[0];
        name = name
          .split(" ")
          .map((val) => val[0].toUpperCase() + val.substring(1))
          .join(" ");

        let form_data = new FormData();
        form_data.append('name', name);
        form_data.append('rollno', rollno);
        form_data.append('email', extended.attributes["e-mail"][0]);

        fetch(`http://${config.BOT_PRIVATE_IP}/${req.query.token}`, {
          method: "POST",
          body: form_data,
        }).then(response => {
          if (response.ok) {
            res.send("You have successfully verified with the CAS login!");
          } else if (response.status === 404) {
            res.send(
              "Your verification link expired!\n"
              + "Please run /verify again and use the new link",
              400
            );
          } else {
            throw new Error(response.status);
          }
        })
          .catch(err => {
            res.send("Internal server error", 500);
            logger.error(`Error in /cas fetch: ${err}`);
          });
      }
    }
  );
});

module.exports = app;
