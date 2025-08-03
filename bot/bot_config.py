import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "dbname": "fixed_crane_db",
    "user": "postgres",
    "password": "acfy0ver",
    "host": "localhost",
    "port": 5432
}
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

