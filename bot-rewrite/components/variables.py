import os
from dotenv import load_dotenv
from configparser import ConfigParser

load_dotenv()

class Variables:
    MONGO_URI = os.getenv('MONGO_URI')
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    TOKEN = os.getenv("DISCORD_TOKEN")
    MONGO_DATABASE = os.getenv("MONGO_DATABASE")
    BASE_URL = os.getenv("BASE_URL")
    SERVER_CONFIG = ConfigParser()