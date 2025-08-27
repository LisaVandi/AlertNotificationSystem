import logging
import os

def setup_logging(logger_name: str, log_file: str) -> logging.Logger:
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')  
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    logger.addHandler(handler)
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
        if isinstance(handler, logging.FileHandler):
            handler.close()
            handler.stream = open(handler.baseFilename, handler.mode)

def close_logging(logger: logging.Logger):
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)