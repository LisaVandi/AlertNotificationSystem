import pika
import json
import logging

logger = logging.getLogger(__name__)

def send_json_to_microservice(alert_data):
    try:
        # RabbitMQ connection parameters
        rabbitmq_host = 'localhost'  # or the IP/hostname of the RabbitMQ server
        rabbitmq_queue = 'alerts_queue'  # the name of the queue to use

        # 1. Connect to the broker
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
        channel = connection.channel()

        # 2. Declare (or check) the queue
        channel.queue_declare(queue=rabbitmq_queue, durable=True)

        # 3. Convert and publish the message
        message = json.dumps(alert_data)
        channel.basic_publish(
            exchange='',
            routing_key=rabbitmq_queue,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,  # makes the message persistent
            )
        )

        logger.info("✅ Message published to RabbitMQ.")
        connection.close()

    except Exception as e:
        logger.error(f"❌ Error while sending to microservice via RabbitMQ: {e}")
