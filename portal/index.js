const config = require("./utils/config");
const app = require("./app");
const logger = require("./utils/logger");
require("dotenv").config();

app.listen(config.PORT, () => {
  logger.info(`Server running on ${config.BASE_URL}`);
});
