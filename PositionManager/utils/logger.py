# === config/logger.py ===

import os
import logging

log_dir = 'PositionManager/logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

def setup_logger():
    logger = logging.getLogger("PositionManager")
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', "%H:%M:%S")

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        file_handler = logging.FileHandler(os.path.join(log_dir, 'positionManager.log'), mode='a')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger

logger = setup_logger()