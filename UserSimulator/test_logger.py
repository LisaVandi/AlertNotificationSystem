import os
import logging

log_dir = 'UserSimulator/logs'
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("UserSimulatorTest")
if not logger.hasHandlers():
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', "%H:%M:%S")
    file_handler = logging.FileHandler(os.path.join(log_dir, 'simulation.log'), mode='a')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

logger.info("Test log message")
logger.debug("Debug test message")
