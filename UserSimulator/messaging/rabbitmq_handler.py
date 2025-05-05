import pika

class RabbitMQHandler:
    def __init__(self, host='localhost'):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        self.channel = self.connection.channel()

    def declare_queue(self, queue_name: str):
        self.channel.queue_declare(queue=queue_name, durable=True)

    def publish(self, queue_name: str, message: str):
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=message,
            properties=pika.BasicProperties(delivery_mode=2)
        )

    def consume(self, queue_name: str, callback):
        self.channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
        self.channel.start_consuming()

    def close(self):
        self.connection.close()
