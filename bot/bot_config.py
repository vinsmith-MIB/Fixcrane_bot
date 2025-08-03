import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "fixed_crane_db"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "acfy0ver"),
    "host": os.getenv("POSTGRES_HOST", "db"),  # Penting: default ke 'db' untuk Docker
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
}

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
