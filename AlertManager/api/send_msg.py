import pika
import json
import logging

logger = logging.getLogger(__name__)

def send_json_to_microservice(alert_data):
    try:
        # Parametri di connessione RabbitMQ
        rabbitmq_host = 'localhost'  # oppure l'IP/hostname del server RabbitMQ
        rabbitmq_queue = 'alerts_queue'  # nome della coda da usare

        # 1. Connessione al broker
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
        channel = connection.channel()

        # 2. Dichiara (o verifica) la coda
        channel.queue_declare(queue=rabbitmq_queue, durable=True)

        # 3. Converte e pubblica il messaggio
        message = json.dumps(alert_data)
        channel.basic_publish(
            exchange='',
            routing_key=rabbitmq_queue,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,  # rende il messaggio persistente
            )
        )

        logger.info("✅ Messaggio pubblicato su RabbitMQ.")
        connection.close()

    except Exception as e:
        logger.error(f"❌ Errore durante l'invio al microservizio tramite RabbitMQ: {e}")
