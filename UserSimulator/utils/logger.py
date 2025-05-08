import os
import logging

# Crea la cartella logs/ se non esiste
log_dir = 'UserSimulator/logs'
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Funzione per configurare il logger
def setup_logger():
    # Ottieni il logger
    logger = logging.getLogger("UserSimulator")
    
    # Verifica se il logger è già configurato, altrimenti imposta i nuovi handler
    if not logger.hasHandlers():
        # Imposta il livello del logger
        logger.setLevel(logging.DEBUG)

        # Crea il formatter
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', "%H:%M:%S")
        
        # Console handler (livello INFO)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # File handler (livello DEBUG)
        file_handler = logging.FileHandler(os.path.join(log_dir, 'simulation.log'), mode='a')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Aggiungi i handler al logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger

# Configura il logger una sola volta
logger = setup_logger()

# Esempio di utilizzo del logger
logger.info("RabbitMQ connected successfully.")
