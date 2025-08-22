# import pika
# import json
# import time
# from typing import Callable, Any, Dict
# from NotificationCenter.app.config.logging import setup_logging, flush_logs, close_logging


# class RabbitMQHandler:
#     def __init__(self, host: str = 'localhost', port: int = 5672, 
#                  username: str = None, password: str = None):
#         self.logger = setup_logging("rabbitmq_handler", "NotificationCenter/logs/rabbitmq_handler.log")
#         self._connection_params = pika.ConnectionParameters(
#             host=host,
#             port=port,
#             credentials=pika.PlainCredentials(username, password) if username else None,
#             heartbeat=600,
#             blocked_connection_timeout=300,
#             connection_attempts=3,
#             retry_delay=5
#         )
#         self._connection = None
#         self._channel = None
#         self._connect()

#     def _connect(self):
#         """Establish connection with retry logic"""
#         attempts = 0
#         max_attempts = 3
        
#         while attempts < max_attempts:
#             try:
#                 self._connection = pika.BlockingConnection(self._connection_params)
#                 self._channel = self._connection.channel()
#                 self.logger.info("RabbitMQ connection established")
#                 return
#             except Exception as e:
#                 attempts += 1
#                 self.logger.warning(f"Connection attempt {attempts} failed: {str(e)}")
#                 if attempts == max_attempts:
#                     self.logger.error("Max connection attempts reached")
#                     raise
#                 time.sleep(2 ** attempts)  # Exponential backoff

#     def declare_queue(self, queue_name: str, durable: bool = True):
#         """Declare a queue with error handling"""
#         try:
#             self._channel.queue_declare(
#                 queue=queue_name,
#                 durable=durable
#             )
#             self.logger.info(f"Declared queue: {queue_name}")
#         except Exception as e:
#             self.logger.error(f"Failed to declare queue {queue_name}: {str(e)}")
#             self._reconnect()
#             raise

#     def send_message(self, exchange: str = '', routing_key: str = '', 
#                     message: Dict[str, Any] = None, persistent: bool = True,
#                     mandatory: bool = True):
#         """Send message with connection recovery"""
#         try:
#             if not self.is_connected():
#                 self.logger.warning("Connection not active, reconnecting...")
#                 self._reconnect()
                
#             if not hasattr(self, "_return_cb_registered"):
#                 self._channel.add_on_return_callback(self._on_message_returned)
#                 self._return_cb_registered = True

#             self._channel.basic_publish(
#                 exchange=exchange,
#                 routing_key=routing_key,
#                 body=json.dumps(message),
#                 properties=pika.BasicProperties(
#                     delivery_mode=2 if persistent else 1,
#                     content_type='application/json'
#                 ),
#                 mandatory=mandatory
#             )
#             self.logger.debug(f"Message sent to {routing_key}")
#         except Exception as e:
#             self.logger.error(f"Failed to send message: {str(e)}")
#             self._reconnect()
#             raise
        
#     def _on_message_returned(self, channel, method, properties, body):
#         self.logger.error(
#             "Message returned by broker (exchange=%s, routing_key=%s): %s",
#             method.exchange, method.routing_key, body.decode("utf-8", errors="ignore")
#         )

#     def consume_messages(self, queue_name: str, callback: Callable[[Dict[str, Any]], None], 
#                         prefetch_count: int = 1, reconnect_delay: float = 1.0):
#         """Start consuming messages from a queue"""
#         while True:
#             try:
#                 if not self.is_connected():
#                      self._reconnect()
                     
#                 self._channel.basic_qos(prefetch_count=prefetch_count)
                
#                 def wrapped_callback(ch, method, properties, body):
#                     try:
#                         msg = json.loads(body)
#                         callback(msg)
#                         ch.basic_ack(delivery_tag=method.delivery_tag)
#                     except json.JSONDecodeError:
#                         self.logger.error("Invalid JSON message")
#                         ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
#                     except Exception as e:
#                         self.logger.error(f"Message processing failed: {str(e)}")
#                         ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

#                 self._channel.basic_consume(
#                     queue=queue_name,
#                     on_message_callback=wrapped_callback,
#                     auto_ack=False
#                 )
#                 self.logger.info(f"Started consuming from {queue_name}")
#                 self._channel.start_consuming()
                
#             except KeyboardInterrupt:
#                 self.logger.info("Consumer interrupted by user, stopping...")
#                 try:
#                     if self._channel and self._channel.is_open:
#                         self._channel.stop_consuming()
#                 finally:
#                     break
                    
#             except Exception as e:
#                 self.logger.error(f"Consumer error on '{queue_name}': {e}. Reconnecting...")
#                 try:
#                     self._reconnect()
#                 except Exception as e2:
#                     self.logger.error(f"Reconnect failed: {e2}")
#                 time.sleep(reconnect_delay)
#                 continue  # Retry consuming

#     def is_connected(self) -> bool:
#         """Check if connection is active"""
#         return (self._connection and self._connection.is_open and 
#                 self._channel and not self._channel.is_closed)

#     def _reconnect(self):
#         """Reconnect to RabbitMQ"""
#         self.close()
#         self._connect()
        
#     def purge_queue(self, queue_name: str):
#         try:
#             if not self.is_connected():
#                 self._reconnect()
#             self._channel.queue_purge(queue=queue_name)
#             self.logger.info(f"Queue '{queue_name}' purged.")
#         except Exception as e:
#             self.logger.error(f"Failed to purge queue {queue_name}: {e}")

#     def close(self):
#         """Cleanly close connections"""
#         try:
#             if self._channel and self._channel.is_open:
#                 self._channel.close()
#             if self._connection and self._connection.is_open:
#                 self._connection.close()
#             self.logger.info("RabbitMQ connection closed")
#         except Exception as e:
#             self.logger.error(f"Error closing connection: {str(e)}")
#         finally:
#             flush_logs(self.logger)
#             close_logging(self.logger)

import pika
import json
import time
import threading
from typing import Callable, Any, Dict
from NotificationCenter.app.config.logging import setup_logging, flush_logs, close_logging


class RabbitMQHandler:
    def __init__(self, host: str = 'localhost', port: int = 5672,
                 username: str = None, password: str = None):
        self.logger = setup_logging("rabbitmq_handler", "NotificationCenter/logs/rabbitmq_handler.log")
        self._connection_params = pika.ConnectionParameters(
            host=host,
            port=port,
            credentials=pika.PlainCredentials(username, password) if username else None,
            heartbeat=600,
            blocked_connection_timeout=300,
            connection_attempts=3,
            retry_delay=5
        )
        self._conn = None
        self._cons_ch = None   # channel dedicato al consumo
        self._pub_ch  = None   # channel dedicato al publish
        self._pub_return_cb_set = False
        self._send_lock = threading.Lock()
        self._connect()

    # ─────────────────────────────────────────────────────────────────────────────

    def _connect(self):
        """Crea connessione + due channel separati (consume/publish)."""
        attempts = 0
        max_attempts = 3
        while attempts < max_attempts:
            try:
                self._conn = pika.BlockingConnection(self._connection_params)
                self._cons_ch = self._conn.channel()
                self._pub_ch  = self._conn.channel()
                self._pub_return_cb_set = False
                self.logger.info("RabbitMQ connection + channels established")
                return
            except Exception as e:
                attempts += 1
                self.logger.warning(f"Connection attempt {attempts} failed: {str(e)}")
                if attempts == max_attempts:
                    self.logger.error("Max connection attempts reached")
                    raise
                time.sleep(2 ** attempts)

    # ─────────────────────────────────────────────────────────────────────────────

    def declare_queue(self, queue_name: str, durable: bool = True):
        """Dichiara la coda su entrambi i channel (idempotente)."""
        try:
            for ch in (self._cons_ch, self._pub_ch):
                ch.queue_declare(queue=queue_name, durable=durable)
            self.logger.info(f"Declared queue: {queue_name}")
        except Exception as e:
            self.logger.error(f"Failed to declare queue {queue_name}: {str(e)}")
            self._reconnect()
            raise

    # ─────────────────────────────────────────────────────────────────────────────

    def send_message(self, exchange: str = '', routing_key: str = '',
                     message: Dict[str, Any] = None, persistent: bool = True,
                     mandatory: bool = True):
        """Publish sul channel dedicato, con lock e return-callback."""
        try:
            if not self.is_connected():
                self.logger.warning("Connection not active, reconnecting...")
                self._reconnect()

            if not self._pub_return_cb_set:
                self._pub_ch.add_on_return_callback(self._on_message_returned)
                self._pub_return_cb_set = True

            body = json.dumps(message)
            with self._send_lock:
                self._pub_ch.basic_publish(
                    exchange=exchange,
                    routing_key=routing_key,
                    body=body,
                    properties=pika.BasicProperties(
                        delivery_mode=2 if persistent else 1,
                        content_type='application/json'
                    ),
                    mandatory=mandatory
                )
            self.logger.debug(f"Message sent to {routing_key}")
        except Exception as e:
            self.logger.error(f"Failed to send message: {str(e)}")
            self._reconnect()
            raise

    def _on_message_returned(self, channel, method, properties, body):
        self.logger.error(
            "Message returned by broker (exchange=%s, routing_key=%s): %s",
            method.exchange, method.routing_key, body.decode("utf-8", errors="ignore")
        )

    # ─────────────────────────────────────────────────────────────────────────────

    def consume_messages(self, queue_name: str, callback: Callable[[Dict[str, Any]], None],
                         prefetch_count: int = 1, reconnect_delay: float = 1.0):
        """Consume usando il channel dedicato al consumo."""
        while True:
            try:
                if not self.is_connected():
                    self._reconnect()

                self._cons_ch.basic_qos(prefetch_count=prefetch_count)

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

                self._cons_ch.basic_consume(
                    queue=queue_name,
                    on_message_callback=wrapped_callback,
                    auto_ack=False
                )
                self.logger.info(f"Started consuming from {queue_name}")
                self._cons_ch.start_consuming()

            except KeyboardInterrupt:
                self.logger.info("Consumer interrupted by user, stopping...")
                try:
                    if self._cons_ch and self._cons_ch.is_open:
                        self._cons_ch.stop_consuming()
                finally:
                    break

            except Exception as e:
                self.logger.error(f"Consumer error on '{queue_name}': {e}. Reconnecting...")
                try:
                    self._reconnect()
                except Exception as e2:
                    self.logger.error(f"Reconnect failed: {e2}")
                time.sleep(reconnect_delay)
                continue  # retry loop

    def is_connected(self) -> bool:
        return (
            self._conn and self._conn.is_open and
            self._cons_ch and getattr(self._cons_ch, "is_open", False) and
            self._pub_ch and getattr(self._pub_ch, "is_open", False)
        )

    def _reconnect(self):
        """Ricrea connessione e channel, mantenendo la stessa API esterna."""
        self.close()
        self._connect()

    def purge_queue(self, queue_name: str):
        try:
            if not self.is_connected():
                self._reconnect()
            # purge dal channel di publish (va bene anche cons_ch)
            self._pub_ch.queue_purge(queue=queue_name)
            self.logger.info(f"Queue '{queue_name}' purged.")
        except Exception as e:
            self.logger.error(f"Failed to purge queue {queue_name}: {e}")

    def close(self):
        """Chiusura pulita di channel e connessione."""
        try:
            for ch in (self._cons_ch, self._pub_ch):
                try:
                    if ch and ch.is_open:
                        ch.close()
                except Exception:
                    pass
            if self._conn and self._conn.is_open:
                self._conn.close()
            self.logger.info("RabbitMQ connection closed")
        except Exception as e:
            self.logger.error(f"Error closing connection: {str(e)}")
        finally:
            flush_logs(self.logger)
            close_logging(self.logger)
