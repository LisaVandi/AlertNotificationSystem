import logging
import os

def setup_logging(logger_name: str, log_file: str) -> logging.Logger:
    """
    Configures a logger with the specified name to write to the specified file.
    Ensures the log directory exists and sets up the logger with a file handler.

    Args:
        logger_name (str): The name of the logger (e.g., module name).
        log_file (str): The path to the log file.

    Returns:
        logging.Logger: The configured logger instance.
    """
    # Ensure the log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create a logger with the specified name
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Configure a file handler to write to the specified file
    handler = logging.FileHandler(log_file, mode='w', encoding='utf-8') 
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    # Add the handler to the logger
    logger.addHandler(handler)

    # Prevent propagation to the root logger to avoid interference
    logger.propagate = False

    return logger

def flush_logs(logger: logging.Logger):
    """
    Forces all handlers of the specified logger to flush their buffers, ensuring logs are written to the file.

    Args:
        logger (logging.Logger): The logger whose handlers should be flushed.
    """
    for handler in logger.handlers:
        handler.flush()
        # Close and reopen the handler to ensure the file is updated
        if isinstance(handler, logging.FileHandler):
            handler.close()
            handler.stream = open(handler.baseFilename, handler.mode)

def close_logging(logger: logging.Logger):
    """
    Closes all handlers of the specified logger to release file resources.

    Args:
        logger (logging.Logger): The logger whose handlers should be closed.
    """
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)