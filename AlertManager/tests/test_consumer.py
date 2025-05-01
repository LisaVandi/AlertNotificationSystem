import pika
import json

def callback(ch, method, properties, body):
    message = json.loads(body)
    print("Message received:", message)

def listen_to_queue():
    rabbitmq_host = 'localhost'
    rabbitmq_queue = 'alerts_queue'

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
    channel = connection.channel()

    channel.queue_declare(queue=rabbitmq_queue, durable=True)

    channel.basic_consume(queue=rabbitmq_queue, on_message_callback=callback, auto_ack=True)

    print("🔄 Listening on the queue. Press CTRL+C to stop.")
    channel.start_consuming()

if __name__ == "__main__":
    listen_to_queue()
