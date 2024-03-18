const PORT = process.env.PORT;
const BASE_URL = process.env.BASE_URL;

const ATLAS_URL = `${process.env.MONGO_URI}/${process.env.MONGO_DATABASE}`;

const DISCORD_CLIENT_ID = process.env.DISCORD_CLIENT_ID;
const DISCORD_SECRET = process.env.DISCORD_SECRET;
const DISCORD_REDIRECT = `${BASE_URL}/discord/callback`;

// GitHub Webhook Secret Token
const GITHUB_SECRET = process.env.GITHUB_SECRET;

// secret for express middleware
const SECRET = process.env.SECRET;

// link to authenticate for CAS from
const CAS_LINK = process.env.CAS_LINK;

module.exports = {
  SECRET,
  CAS_LINK,
  PORT,
  BASE_URL,
  ATLAS_URL,
  DISCORD_CLIENT_ID,
  DISCORD_SECRET,
  DISCORD_REDIRECT,
  GITHUB_SECRET
}
