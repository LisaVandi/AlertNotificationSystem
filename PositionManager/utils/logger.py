import os
import logging

# Directory for storing log files
log_dir = 'PositionManager/logs'

# If the log directory doesn't exist, create it
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

def setup_logger():
    """
    Sets up and configures the logger for the PositionManager.

    The logger will log messages to both the console and a log file:
    - Console logs are at the INFO level.
    - File logs are at the DEBUG level.
    
    Returns:
        logger (logging.Logger): The configured logger instance.
    """
    # Create a logger instance with the name "PositionManager"
    logger = logging.getLogger("PositionManager")

    # Check if the logger already has handlers to prevent duplicate logs
    if not logger.hasHandlers():
        # Set the log level to DEBUG, so all messages of level DEBUG and above are captured
        logger.setLevel(logging.DEBUG)

        # Define the log format
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', "%H:%M:%S")

        # Set up console logging: Log to the console with INFO level
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)  # Display INFO and higher level logs in the console
        console_handler.setFormatter(formatter)

        # Set up file logging: Log to a file with DEBUG level
        file_handler = logging.FileHandler(os.path.join(log_dir, 'positionManager.log'), mode='w')
        file_handler.setLevel(logging.DEBUG)  # Log DEBUG and higher level messages in the file
        file_handler.setFormatter(formatter)

        # Add both handlers to the logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger

# Initialize the logger
logger = setup_logger()
