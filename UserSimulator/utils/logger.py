import os
import logging

# Check if the logs/ directory exists, and create it if it doesn't.
# This ensures that we have a dedicated directory for storing log files.
log_dir = 'UserSimulator/logs'
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir)  # Creates the logs directory if it does not exist.

# Function to configure and set up the logger for the application.
# The logger will handle different levels of logging and store the logs in both the console and a file.
def setup_logger():
    """
    This function configures and returns a logger for the UserSimulator application. 
    It sets up two logging handlers:
    1. Console handler - Logs messages to the console.
    2. File handler - Logs messages to a file in the 'logs' directory.

    It also ensures that the logger is configured with the appropriate log levels and formatters.
    """

    # Get the logger instance for the "UserSimulator" application.
    # If it doesn't exist, it will be created.
    logger = logging.getLogger("UserSimulator")
    
    # Check if the logger has any existing handlers. If no handlers exist, configure new ones.
    if not logger.hasHandlers():
        # Set the global logging level to DEBUG.
        # This ensures that all messages from DEBUG level and above will be captured.
        logger.setLevel(logging.DEBUG)

        # Define a log message format that includes the time, log level, and the actual message.
        # The timestamp is formatted as HH:MM:SS.
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', "%H:%M:%S")
        
        # Console handler:
        # This handler will output logs to the console.
        # We set its level to INFO, so only INFO and higher severity messages will be shown in the console.
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)  # Console output will only show INFO level and higher
        console_handler.setFormatter(formatter)  # Apply the formatter to the console handler
        
        # File handler:
        # This handler will write logs to a file located at 'UserSimulator/logs/simulation.log'.
        # We set its level to DEBUG, meaning that all messages from DEBUG and higher severity will be written to the log file.
        file_handler = logging.FileHandler(os.path.join(log_dir, 'simulation.log'), mode='a')
        file_handler.setLevel(logging.DEBUG)  # File output will capture DEBUG level and higher
        file_handler.setFormatter(formatter)  # Apply the same formatter to the file handler
        
        # Add the handlers to the logger.
        # The logger will now log messages to both the console and the file.
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    # Return the configured logger.
    return logger

# Call the setup_logger function to configure and retrieve the logger instance.
# This ensures that the logger is only set up once when the module is imported.
logger = setup_logger()

# Example usage of the logger:
# This is an info-level log message to indicate a successful connection to RabbitMQ.
# This message will be printed in the console and written to the log file.
logger.info("RabbitMQ connected successfully.")
