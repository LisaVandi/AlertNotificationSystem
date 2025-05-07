import logging

# Configurazione del logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Crea un handler che stampa i log sulla console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Crea un formatter per i messaggi di log
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Aggiungi il handler al logger
logger.addHandler(console_handler)
