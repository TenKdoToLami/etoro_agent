import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent adding handlers multiple times if instantiated multiple times
    if not logger.handlers:
        log_file = Path(__file__).parent / "trades.log"
        
        # 10 MB max size, 2 backups
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=2)
        stream_handler = logging.StreamHandler(sys.stdout)
        
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        
    return logger
