import os
import logging

# Create the 'logs/' folder if it doesn't exist already
log_dir = 'AlertManager/logs'  # Define the log directory path
if not os.path.exists(log_dir):  # Check if the directory exists
    os.makedirs(log_dir)  # Create the directory if it doesn't exist

# Function to set up the logger
def setup_logger():
    """Sets up the logger with both console and file handlers."""
    
    # Define a logger name and log file name
    logger_name = "AlertManager"  # Name for the logger instance
    log_file = "alertmanager.log"  # Name of the log file

    # Create or get the logger instance
    logger = logging.getLogger(logger_name)

    # If the logger doesn't already have handlers (i.e., it hasn't been configured before), set up the handlers
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)  # Set the logging level to DEBUG for detailed logging

        # Formatter for the log messages: include time, log level, and message
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', "%H:%M:%S")
        
        # Console handler for logging INFO and above levels to the terminal
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)  # Only log INFO and above to the console
        console_handler.setFormatter(formatter)  # Apply the formatter to the console handler
        
        # File handler for logging DEBUG and above levels to a file
        file_handler = logging.FileHandler(os.path.join(log_dir, log_file), mode='a')  # Open file in append mode
        file_handler.setLevel(logging.DEBUG)  # Log DEBUG and above to the file
        file_handler.setFormatter(formatter)  # Apply the formatter to the file handler
        
        # Add the console and file handlers to the logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger  # Return the configured logger

# If the script is run directly (not imported), initialize the logger and log an info message
if __name__ == "__main__":
    logger = setup_logger()  # Set up the logger
    logger.info("Logger initialized from logger.py")  # Log an informational message
