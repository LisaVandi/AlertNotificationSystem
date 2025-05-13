import pika
import json
import sys
import os
from utils.logger import logger  # Importa il logger

# Aggiungi la cartella principale (AlertNotificationSystem2) al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from UserSimulator.rabbitmq.rabbitmq_manager import get_rabbitmq_channel
from UserSimulator.simulation.user_simulator import simulate_user_movement

def listen_for_events():
    """Ascolta gli eventi RabbitMQ e avvia la simulazione quando richiesto"""
    try:
        channel, _ = get_rabbitmq_channel()

        # Dichiarazione delle code
        channel.queue_declare(queue="user_simulator_queue", durable=True)
        channel.queue_declare(queue="evacuation_paths_queue", durable=True)

        logger.info("In attesa di eventi...")

        def callback(ch, method, properties, body):
            """Callback per processare i messaggi ricevuti dalla coda"""
            try:
                msg = json.loads(body)
                logger.info(f"Messaggio ricevuto: {msg}")
                
                # Verifica il tipo di messaggio
                simulate_user_movement(msg)

            except Exception as e:
                # Logga eventuali errori nel trattamento del messaggio
                logger.error(f"Errore nell'elaborazione del messaggio: {e}")

        # Inizia a consumare i messaggi dalle due code
        channel.basic_consume(queue="user_simulator_queue", on_message_callback=callback, auto_ack=True)
        channel.basic_consume(queue="evacuation_paths_queue", on_message_callback=callback, auto_ack=True)

        logger.info('In attesa di eventi... Per uscire premi CTRL+C')
        channel.start_consuming()

    except KeyboardInterrupt:
        logger.info("Interruzione dell'ascolto eventi")
        sys.exit(0)

if __name__ == '__main__':
    listen_for_events()
