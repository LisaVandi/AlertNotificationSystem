import os
import logging

# Crea la cartella logs/ se non esiste
log_dir = 'AlertManager/logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Funzione per configurare il logger
def setup_logger():
    # Definisci un nome per il logger, se non specificato
    logger_name = "AlertManager"
    log_file = "alertmanager.log"
    
    # Crea o ottieni il logger
    logger = logging.getLogger(logger_name)
    
    # Se il logger non ha già handler, configura i nuovi handler
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)

        # Formatter per la formattazione dei messaggi di log
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', "%H:%M:%S")
        
        # Console handler (INFO)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # File handler (DEBUG)
        file_handler = logging.FileHandler(os.path.join(log_dir, log_file), mode='a')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Aggiungi i handler al logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger

# Se vuoi usarlo direttamente in logger.py (non obbligatorio)
if __name__ == "__main__":
    logger = setup_logger()
    logger.info("Logger initialized from logger.py")
