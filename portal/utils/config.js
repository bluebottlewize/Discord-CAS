const PROTOCOL = process.env.PROTOCOL;
const HOST = process.env.HOST;

const PORT = process.env.PORT ? process.env.PORT : "80";
const _PORT_AS_SUFFIX = process.env.PORT ? `:${PORT}` : "";

const SUBPATH = process.env.SUBPATH;

const BASE_URL = `${PROTOCOL}://${HOST}${_PORT_AS_SUFFIX}${SUBPATH}`;

const ATLAS_URL = `${process.env.MONGO_URI}/${process.env.MONGO_DATABASE}`;

const DISCORD_CLIENT_ID = process.env.DISCORD_CLIENT_ID;
const DISCORD_SECRET = process.env.DISCORD_SECRET;

// secret for express middleware
const SECRET = process.env.SECRET;

// link to authenticate for CAS from
const CAS_LINK = process.env.CAS_LINK;

module.exports = {
  SECRET,
  CAS_LINK,
  PORT,
  SUBPATH,
  BASE_URL,
  ATLAS_URL,
  DISCORD_CLIENT_ID,
  DISCORD_SECRET,
};
