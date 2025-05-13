import pika
from UserSimulator.utils.logger import logger  # Importa il logger

def get_rabbitmq_channel():
    """Crea una connessione e un canale RabbitMQ"""
    try:
        logger.info("Tentativo di connessione a RabbitMQ...")
        
        # Crea una connessione a RabbitMQ
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        
        # Crea un canale
        channel = connection.channel()
        
        logger.info("Connessione a RabbitMQ riuscita e canale creato.")
        
        return channel, connection
    
    except Exception as e:
        # Logga l'errore in caso di fallimento
        logger.error(f"Errore nella connessione a RabbitMQ: {e}")
        return None, None
