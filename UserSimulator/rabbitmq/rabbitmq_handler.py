import pika
import json
import numpy as np
import time
import traceback
from UserSimulator.utils.logger import logger

class RabbitMQHandler:
    def __init__(self, config, simulator):
        self.config = config
        self.simulator = simulator
        self.connection = None
        self.channel = None

    def connect(self):
        try:
            credentials = pika.PlainCredentials(
                self.config.rabbitmq.get("username", "guest"),
                self.config.rabbitmq.get("password", "guest")
            )
            parameters = pika.ConnectionParameters(
                host=self.config.rabbitmq.get("host", "localhost"),
                port=self.config.rabbitmq.get("port", 5672),
                credentials=credentials,
                heartbeat=600,  # Aggiungi heartbeat
                blocked_connection_timeout=300  # Timeout per connessioni bloccate
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Aumenta il prefetch count
            self.channel.basic_qos(prefetch_count=1)

            # Dichiara le code con tutti i parametri necessari
            self.channel.queue_declare(
                queue=self.config.rabbitmq.get("user_simulator_queue", "user_simulator_queue"),
                durable=True,
                arguments={'x-queue-type': 'classic'}  # o 'quorum' per maggiore affidabilità
            )
            self.channel.queue_declare(
                queue=self.config.rabbitmq.get("evacuation_paths_queue", "evacuation_paths_queue"),
                durable=True,
                arguments={'x-queue-type': 'classic'}
            )
            self.channel.queue_declare(
                queue=self.config.rabbitmq.get("position_queue", "position_queue"),
                durable=True,
                arguments={'x-queue-type': 'classic'}
            )

            # Pulisci le code prima di consumare per evitare messaggi residui
            self.channel.queue_purge(
                queue=self.config.rabbitmq.get("user_simulator_queue", "user_simulator_queue")
            )
            logger.info("User simulator queue purged before consuming.")

            self.channel.queue_purge(
                queue=self.config.rabbitmq.get("evacuation_paths_queue", "evacuation_paths_queue")
            )
            logger.info("Evacuation paths queue purged before consuming.")

            # Configura i consumer con auto_ack=False per maggiore affidabilità
            self.channel.basic_consume(
                queue=self.config.rabbitmq.get("user_simulator_queue", "user_simulator_queue"),
                on_message_callback=self.on_alert,
                auto_ack=False  # Cambiato da True a False
            )
            self.channel.basic_consume(
                queue=self.config.rabbitmq.get("evacuation_paths_queue", "evacuation_paths_queue"),
                on_message_callback=self.on_evacuation_path,
                auto_ack=False  # Cambiato da True a False
            )

            logger.info(f"Connected to RabbitMQ and consuming from: "
                    f"{self.config.rabbitmq.get('user_simulator_queue', 'user_simulator_queue')} and "
                    f"{self.config.rabbitmq.get('evacuation_paths_queue', 'evacuation_paths_queue')}")
        except Exception as e:
            logger.error(f"Failed to connect RabbitMQ: {e}")
            raise

    def on_alert(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            msg_type = message.get("msgType", "").lower()

            if msg_type == "alert":
                logger.info("Received ALERT message.")
                self.simulator.handle_alert(message)

            elif msg_type == "Stop":
                logger.info("Received STOP message.")
                self.simulator.handle_stop()

            else:
                logger.warning(f"Unknown msgType received: {msg_type}")

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError:
            logger.error("Invalid JSON message received")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


    def on_evacuation_path(self, ch, method, properties, body):
        try:
            logger.info(f"Evacuation path message body: {body}")
            data = json.loads(body)

            if isinstance(data, dict) and data.get("msgType", "").lower() == "stop":
                logger.info("Received STOP message in evacuation_path queue.")
                self.simulator.handle_stop()
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # ▸ 1. Il payload deve essere una lista di dict
            if not isinstance(data, list):
                logger.warning("Expected a list of evacuation paths, got something else.")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # ▸ 2. Utenti per cui è arrivato un percorso
            received_user_ids = set()
            for item in data:
                user_id = int(item.get("user_id"))
                received_user_ids.add(user_id)

                path = item.get("evacuation_path", [])
                user = self.simulator.users.get(user_id)
                if user:
                    user.set_evacuation_path(path)          # assegna / aggiorna il path
                else:
                    logger.warning(f"User ID {user_id} not found in simulator")

            # ▸ 3. Chi NON è nella lista ma era ancora “in attesa”/“allerta” ⇒ salvo
            for uid, usr in self.simulator.users.items():
                if uid not in received_user_ids and usr.state in ("allerta", "in_attesa_percorso"):
                    usr.mark_as_salvo()
                    logger.info(f"User {uid} marked as SALVO (no longer present in paths)")

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"Failed to process evacuation path message: {e}", exc_info=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


    def check_connection(self):
        try:
            if not self.connection or self.connection.is_closed:
                logger.warning("RabbitMQ connection is closed, reconnecting...")
                self.connect()
                return False
            return True
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False


    def publish_position(self, position_data):
        try:
            msg = json.dumps(position_data)
            self.channel.basic_publish(
                exchange='',
                routing_key=self.config.rabbitmq.get("position_queue", "position_queue"),  # usa config
                body=msg,
                properties=pika.BasicProperties(delivery_mode=2)  # rende il messaggio persistente
            )
            logger.debug(f"Published position for user {position_data.get('user_id', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to publish position message: {e}")


    def close(self):
        if self.channel:
            self.channel.close()
        if self.connection:
            self.connection.close()
        logger.info("RabbitMQ connection closed")

    def start(self):
        logger.info("Starting RabbitMQ consuming loop")
        while True:
            try:
                if not self.check_connection():
                    logger.info("Connection not valid, reconnecting...")
                    self.connect()
                    self.add_consumers()  # <- aggiungi questo metodo separato!
                
                logger.info("Starting consuming...")
                self.channel.start_consuming()
            
            except pika.exceptions.ConnectionClosedByBroker:
                logger.warning("Connection closed by broker, reconnecting...")
                time.sleep(5)
            except pika.exceptions.AMQPChannelError as err:
                logger.error(f"Channel error: {err}, recreating channel...")
                time.sleep(5)
            except pika.exceptions.AMQPConnectionError:
                logger.error("Connection was closed, reconnecting...")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error in consuming loop: {e}", exc_info=True)
                time.sleep(5)

    def add_consumers(self):
    # Registra i consumer solo qui
        self.channel.basic_consume(
            queue=self.config.rabbitmq.get("user_simulator_queue", "user_simulator_queue"),
            on_message_callback=self.on_alert,
            auto_ack=False
        )
        self.channel.basic_consume(
            queue=self.config.rabbitmq.get("evacuation_paths_queue", "evacuation_paths_queue"),
            on_message_callback=self.on_evacuation_path,
            auto_ack=False
        )
        logger.info("RabbitMQ consumers registered.")
