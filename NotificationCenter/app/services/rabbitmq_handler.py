"""
Robust RabbitMQ Handler with improved connection management and error handling.
"""
import pika
import json
import time
from typing import Callable, Any, Dict
from NotificationCenter.app.config.logging import setup_logging, flush_logs, close_logging

class RabbitMQHandler:
    def __init__(self, host: str = 'localhost', port: int = 5672, 
                 username: str = None, password: str = None):
        self.logger = setup_logging("rabbitmq_handler", "NotificationCenter/logs/rabbitmqHandler.log")
        self._connection_params = pika.ConnectionParameters(
            host=host,
            port=port,
            credentials=pika.PlainCredentials(username, password) if username else None,
            heartbeat=600,
            blocked_connection_timeout=300,
            connection_attempts=3,
            retry_delay=5
        )
        self._connection = None
        self._channel = None
        self._connect()

    def _connect(self):
        """Establish connection with retry logic"""
        attempts = 0
        max_attempts = 3
        
        while attempts < max_attempts:
            try:
                self._connection = pika.BlockingConnection(self._connection_params)
                self._channel = self._connection.channel()
                self.logger.info("RabbitMQ connection established")
                return
            except Exception as e:
                attempts += 1
                self.logger.warning(f"Connection attempt {attempts} failed: {str(e)}")
                if attempts == max_attempts:
                    self.logger.error("Max connection attempts reached")
                    raise
                time.sleep(2 ** attempts)  # Exponential backoff

    def declare_queue(self, queue_name: str, durable: bool = True):
        """Declare a queue with error handling"""
        try:
            self._channel.queue_declare(
                queue=queue_name,
                durable=durable
            )
            self.logger.info(f"Declared queue: {queue_name}")
        except Exception as e:
            self.logger.error(f"Failed to declare queue {queue_name}: {str(e)}")
            self._reconnect()
            raise

    def send_message(self, exchange: str = '', routing_key: str = '', 
                    message: Dict[str, Any] = None, persistent: bool = True):
        """Send message with connection recovery"""
        try:
            if not self.is_connected():
                self.logger.warning("Connection not active, reconnecting...")
                self._reconnect()

            self._channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2 if persistent else 1,
                    content_type='application/json'
                )
            )
            self.logger.debug(f"Message sent to {routing_key}")
        except Exception as e:
            self.logger.error(f"Failed to send message: {str(e)}")
            self._reconnect()
            raise

    def consume_messages(self, queue_name: str, callback: Callable[[Dict[str, Any]], None], 
                        prefetch_count: int = 1):
        """Start consuming messages from a queue"""
        try:
            self._channel.basic_qos(prefetch_count=prefetch_count)
            
            def wrapped_callback(ch, method, properties, body):
                try:
                    msg = json.loads(body)
                    callback(msg)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except json.JSONDecodeError:
                    self.logger.error("Invalid JSON message")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                except Exception as e:
                    self.logger.error(f"Message processing failed: {str(e)}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

            self._channel.basic_consume(
                queue=queue_name,
                on_message_callback=wrapped_callback,
                auto_ack=False
            )
            self.logger.info(f"Started consuming from {queue_name}")
            self._channel.start_consuming()
        except Exception as e:
            self.logger.error(f"Failed to start consumer: {str(e)}")
            raise

    def is_connected(self) -> bool:
        """Check if connection is active"""
        return (self._connection and self._connection.is_open and 
                self._channel and not self._channel.is_closed)

    def _reconnect(self):
        """Reconnect to RabbitMQ"""
        self.close()
        self._connect()

    def close(self):
        """Cleanly close connections"""
        try:
            if self._channel and self._channel.is_open:
                self._channel.close()
            if self._connection and self._connection.is_open:
                self._connection.close()
            self.logger.info("RabbitMQ connection closed")
        except Exception as e:
            self.logger.error(f"Error closing connection: {str(e)}")
        finally:
            flush_logs(self.logger)
            close_logging(self.logger)