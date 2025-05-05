import json
import pika
from app.core.controller import SimulationController

def start_consumer(controller: SimulationController, queue_name: str, host: str = "localhost"):
    def callback(ch, method, properties, body):
        try:
            message = json.loads(body)
            command = message.get("command")
            payload = message.get("payload", {})
            controller.handle_command(command, payload)
        except Exception as e:
            print(f"Error processing message: {e}")

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
    print(" [*] Waiting for commands...")
    channel.start_consuming()
