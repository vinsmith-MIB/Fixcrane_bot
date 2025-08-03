# utils/logger.py
import logging

def setup_logger():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename="bot_debug.log",
        filemode="w",
        encoding="utf-16"
    )
