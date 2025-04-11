"""
RabbitMQ Handler for sending and receiving messages.
Si occupa della gestione della connessione e della comunicazione con RabbitMQ.
"""
import pika
import json
import logging
from typing import Callable, Any, Dict

class RabbitMQHandler:
    
    def __init__(self, host: str = 'localhost', port: int = 5672, 
                 username: str = None, password: str = None):
        """
            Initializes the RabbitMQ handler with the specified connection parameters.
            Args:
                host (str): The hostname or IP address of the RabbitMQ server. Defaults to 'localhost'.
                port (int): The port number of the RabbitMQ server. Defaults to 5672.
                username (str, optional): The username for RabbitMQ authentication. Defaults to None.
                password (str, optional): The password for RabbitMQ authentication. Defaults to None.
            Attributes:
                _connection_params (pika.ConnectionParameters): The connection parameters for RabbitMQ.
                _connection (pika.BlockingConnection): The connection to the RabbitMQ server.
                _channel (pika.channel.Channel): The channel for communication with RabbitMQ.
                logger (logging.Logger): Logger instance for logging messages.
        """
        self._connection_params = pika.ConnectionParameters(
            host=host,
            port=port,
            credentials=pika.PlainCredentials(username, password) if username else None,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        self._connection = None
        self._channel = None
        self._connect()
        
        # Configurazione logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _connect(self):
        """
        Establishes a connection to the RabbitMQ server and initializes a channel.

        This method attempts to create a blocking connection to RabbitMQ using the
        provided connection parameters. If the connection is successful, it also
        initializes a channel for communication. Logs the connection status.
        """
        try:
            self._connection = pika.BlockingConnection(self._connection_params)
            self._channel = self._connection.channel()
            self.logger.info("Connessione a RabbitMQ stabilita")
        
            
        except pika.exceptions.AMQPConnectionError as e:
            self.logger.error(f"Errore di connessione: {e}")
            raise

    def declare_queue(self, queue_name: str, durable: bool = True):
        try:
            return self._channel.queue_declare(
                queue=queue_name,
                durable=durable
            )
        except pika.exceptions.ChannelClosed as e:
            self.logger.error(f"Errore dichiarazione coda: {e}")
            raise

    def declare_exchange(self, exchange_name: str, exchange_type: str = 'topic'):
        self._channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=exchange_type,
            durable=True
        )

    def bind_queue(self, queue_name: str, exchange_name: str, routing_key: str):
        self._channel.queue_bind(
            queue=queue_name,
            exchange=exchange_name,
            routing_key=routing_key
        )

    def send_message(self, exchange: str = '', routing_key: str = '', 
                    message: Dict[str, Any] = None, persistent: bool = True):
        """
            Sends a message to a RabbitMQ exchange with the specified routing key.
            Args:
                exchange (str): The name of the RabbitMQ exchange to publish the message to. Defaults to an empty string.
                routing_key (str): The routing key to use for the message. Defaults to an empty string.
                message (Dict[str, Any]): The message to send, represented as a dictionary. Defaults to None.
                persistent (bool): Whether the message should be persistent (saved to disk by RabbitMQ). 
                            Defaults to True.
            Raises:
                pika.exceptions.UnroutableError: If the message cannot be routed to any queue.
                pika.exceptions.AMQPError: If an error occurs during the message publishing process.
        
        """
        try:
            self._channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2 if persistent else 1,
                    content_type='application/json'
                )
            )
            self.logger.debug(f"Messaggio inviato a {exchange}/{routing_key}: {message}")
        except pika.exceptions.UnroutableError:
            self.logger.error("Messaggio non routabile")
            raise
        except pika.exceptions.AMQPError as e:
            self.logger.error(f"Errore durante l'invio: {e}")
            self._reconnect()
            raise

    def consume_messages(self, queue_name: str, callback: Callable[[Dict[str, Any]], None], 
                        prefetch_count: int = 1):
        """
            Consumes messages from a specified RabbitMQ queue and processes them using a callback function.
            Args:
                queue_name (str): The name of the RabbitMQ queue to consume messages from.
                callback (Callable[[Dict[str, Any]], None]): A function to process the consumed messages. 
                    It should accept a dictionary representing the message content.
                prefetch_count (int, optional): The maximum number of messages to prefetch from the queue. 
                    Defaults to 1.
            Behavior:
                - Messages are consumed from the specified queue.
                - Each message is passed to the provided callback function for processing.
                - If the message is successfully processed, it is acknowledged (ACK).
                - If the message cannot be parsed as JSON, it is negatively acknowledged (NACK) 
                    and not requeued.
                - If an exception occurs during processing, the message is negatively acknowledged (NACK) 
                    and requeued for further attempts.
            Logging:
                - Logs an error if a message is not valid JSON.
                - Logs an error if an exception occurs during message processing.
                - Logs when the consumer starts listening on the queue.
                - Logs when message consumption is interrupted.
            Raises:
                KeyboardInterrupt: If the message consumption is interrupted manually.
        """
        self._channel.basic_qos(prefetch_count=prefetch_count)
        
        def wrapped_callback(ch, method, properties, body):
            try:
                msg = json.loads(body)
                callback(msg)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except json.JSONDecodeError:
                self.logger.error("Messaggio JSON non valido")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except Exception as e:
                self.logger.error(f"Errore elaborazione messaggio: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        self._channel.basic_consume(
            queue=queue_name,
            on_message_callback=wrapped_callback,
            auto_ack=False
        )
        
        self.logger.info(f"In ascolto su {queue_name}...")
        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            self.logger.info("Interruzione ricezione messaggi")
            self.close()

    def _reconnect(self):
        self.close()
        self._connect()

    def close(self):
        if self._connection and self._connection.is_open:
            self._connection.close()
        self.logger.info("Connessione RabbitMQ chiusa")