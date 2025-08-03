import os
import dotenv

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

DB_PATH = {
    "dbname": "fixed_crane_db",
    "user": "postgres",
    "password": "acfy0ver",
    "host": "localhost",
    "port": 5432
}