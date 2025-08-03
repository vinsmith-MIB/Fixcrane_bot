from database.db_manager import DBManager
from services.maintenance_service import MaintenanceService
from bot.telegram_bot import TelegramBot
from utils.config import TELEGRAM_TOKEN, DB_PATH
from telegram.error import NetworkError
import asyncio
import time

from utils.logger import setup_logger

setup_logger()



def main():
    db_manager = DBManager(DB_PATH)
    maintenance_service = MaintenanceService(db_manager)
    bot = TelegramBot(TELEGRAM_TOKEN, maintenance_service)

    while True:
        try:
            bot.run()
        except NetworkError as e:
            print(f"NetworkError: {e}")
        except Exception as e:
            print(f"Terjadi error lain: {e}")
        finally:
            print("Restart ulang dalam 19 detik...")
            time.sleep(10)
            # Buat event loop baru
            asyncio.set_event_loop(asyncio.new_event_loop())

if __name__ == '__main__':
    main()
