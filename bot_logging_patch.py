import logging

# Setup logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_debug.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Patch untuk menambahkan logging ke fungsi show_graph
def add_logging_to_show_graph():
    """
    Fungsi ini akan menambahkan logging yang lebih detail ke fungsi show_graph
    """
    logger.info("Menambahkan logging untuk debugging grafik...")
    
    # Log untuk debugging
    logger.debug("Setup logging berhasil")
    logger.info("Bot siap dengan logging yang ditingkatkan")
    
    return logger

if __name__ == "__main__":
    add_logging_to_show_graph()
