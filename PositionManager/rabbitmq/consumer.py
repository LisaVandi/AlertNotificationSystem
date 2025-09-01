import json
import pika
import time
import threading
import os
from PositionManager.db.db_manager import DBManager
from PositionManager.utils.logger import logger


class PositionManagerConsumer:
    def __init__(self, config_file=None):
        self.db_manager = DBManager()
        self.dispatch_threshold = 100
        self.dispatch_interval = 10
        self.processed_count = 0
        self.last_dispatch_time = time.time()
        self.last_event = None
        self._stop_sent = False

        # ---- PATCH: connessione RabbitMQ parametrizzata ----
        creds = pika.PlainCredentials(
            os.getenv("RABBITMQ_USER", "guest"),
            os.getenv("RABBITMQ_PASSWORD", "guest")
        )
        params = pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", "localhost"),
            port=int(os.getenv("RABBITMQ_PORT", "5672")),
            credentials=creds,
            heartbeat=30,
            blocked_connection_timeout=300
        )

        # Connessione principale per position_queue
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='position_queue', durable=True)
        self.channel.queue_declare(queue='map_manager_queue', durable=True)
        self.channel.queue_declare(queue='alerted_users_queue', durable=True)

        # Seconda connessione per ack_evacuation_computed
        self.ack_connection = pika.BlockingConnection(params)
        self.ack_channel = self.ack_connection.channel()
        self.ack_channel.queue_declare(queue='ack_evacuation_computed', durable=True)

        # Consumers
        self.channel.basic_consume(
            queue='position_queue',
            on_message_callback=self.process_message,
            auto_ack=True
        )

        # Thread separati
        threading.Thread(target=self.periodic_flush, daemon=True).start()
        threading.Thread(target=self.start_ack_consumer, daemon=True).start()

    # ---- PATCH: flush periodico anche senza nuove posizioni ----
    def periodic_flush(self):
        while True:
            time.sleep(1)
            now = time.time()
            if (now - self.last_dispatch_time) >= self.dispatch_interval:
                if not self.db_manager.is_everyone_safe():
                    logger.info("Periodic flush: danger detected, sending to MapManager.")
                    self.send_aggregated_data(only_to_map_manager=True)
                    self.processed_count = 0
                self.last_dispatch_time = now

    def process_message(self, ch, method, properties, body):
        try:
            logger.info(f"Received raw message:\n{json.dumps(json.loads(body), indent=2)}")
            message = json.loads(body)
            event = message.get("event")
            self.last_event = event
            user_id = message.get("user_id")
            x = message.get("x")
            y = message.get("y")
            z = message.get("z")
            node_id = message.get("node_id")

            # Ottieni la label safe del nodo direttamente dal db
            node_safe = self.db_manager.is_node_safe(node_id)

            # L'utente è in pericolo solo se il nodo non è sicuro
            danger = not node_safe

            if danger and self._stop_sent:
                logger.info("New user in danger detected — resetting STOP flag.")
                self._stop_sent = False

            # Aggiorna la posizione corrente e quella storica nel db
            self.db_manager.upsert_current_position(user_id, x, y, z, node_id, danger)
            self.db_manager.insert_historical_position(user_id, x, y, z, node_id, danger)

            safe = self.db_manager.is_everyone_safe()
            logger.info(f"is_everyone_safe = {safe}, _stop_sent = {getattr(self, '_stop_sent', False)}")

            if safe and not getattr(self, "_stop_sent", False):
                self.send_stop_message()
                logger.info("Send Stop message")
                self._stop_sent = True

            self.processed_count += 1
            if self.processed_count >= self.dispatch_threshold:
                self.send_aggregated_data(only_to_map_manager=True)
                self.processed_count = 0

        except Exception as e:
            logger.error(f"Failed to process message: {e}")

    def send_aggregated_data(self, only_to_map_manager=False):
        aggregated_data = self.aggregate_current_positions()
        aggregated_data["event"] = self.last_event

        logger.info(f"Aggregated data being sent to map_manager_queue:\n{json.dumps(aggregated_data, indent=2)}")
        self.channel.basic_publish(
            exchange='',
            routing_key='map_manager_queue',
            body=json.dumps(aggregated_data),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        logger.info("Sent aggregated data to map_manager_queue.")

        if only_to_map_manager:
            return

        evacuation_data = self.db_manager.get_aggregated_evacuation_data()

        logger.info(
            f"Evacuation data being sent:\n{json.dumps(evacuation_data, indent=2) if evacuation_data else 'STOP message'}"
        )
        if evacuation_data:
            self.channel.basic_publish(
                exchange='',
                routing_key='alerted_users_queue',
                body=json.dumps(evacuation_data),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info("Sent evacuation data to alerted_users_queue.")
        else:
            self.send_stop_message()

    def aggregate_current_positions(self):
        aggregated_data = {}
        try:
            with self.db_manager.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT node_id, user_id
                    FROM current_position
                    WHERE danger = TRUE;
                """)
                rows = cursor.fetchall()
                for node_id, user_id in rows:
                    if node_id not in aggregated_data:
                        aggregated_data[node_id] = {"node_id": node_id, "user_ids": []}
                    aggregated_data[node_id]["user_ids"].append(user_id)
        except Exception as e:
            logger.error(f"Failed to aggregate current positions: {e}")
        return {"dangerous_nodes": list(aggregated_data.values())}

    def get_evacuation_data(self):
        evacuation_data = []
        try:
            with self.db_manager.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT node_id, array_agg(user_id)
                    FROM current_position
                    WHERE danger = TRUE
                    GROUP BY node_id;
                """)
                rows = cursor.fetchall()
                for node_id, user_ids in rows:
                    cursor.execute("""
                        SELECT evacuation_path
                        FROM nodes
                        WHERE node_id = %s;
                    """, (node_id,))
                    evacuation_path = cursor.fetchone()
                    if evacuation_path:
                        path = evacuation_path[0]
                        for user_id in user_ids:
                            evacuation_data.append({
                                "user_id": user_id,
                                "evacuation_path": path
                            })
        except Exception as e:
            logger.error(f"Failed to get evacuation data: {e}")
        return evacuation_data if evacuation_data else None

    def process_ack_message(self, ch, method, properties, body):
        try:
            msg = json.loads(body)
            if msg.get("msg_type") == "paths_ready":
                logger.info("Received 'paths_ready' message.")
                if not self.db_manager.is_everyone_safe():
                    evacuation_data = self.db_manager.get_aggregated_evacuation_data()
                    self.send_evacuation_data(evacuation_data)
                else:
                    self.send_stop_message()
            else:
                logger.warning(f"Ignored unknown ack message type: {msg}")
        except Exception as e:
            logger.error(f"Failed to process ack message: {e}")

    def start_ack_consumer(self):
        logger.info("Started listening to ack_evacuation_computed queue for path readiness.")
        self.ack_channel.basic_consume(
            queue='ack_evacuation_computed',
            on_message_callback=self.process_ack_message,
            auto_ack=True
        )
        try:
            self.ack_channel.start_consuming()
        except Exception as e:
            logger.error(f"Error in ack_evacuation_computed consumer loop: {e}")

    def start_consuming(self):
        logger.info("PositionManagerConsumer started.")
        self.channel.start_consuming()

    def send_evacuation_data(self, evacuation_data=None):
        try:
            if evacuation_data is None:
                evacuation_data = self.db_manager.get_aggregated_evacuation_data()

            if not evacuation_data:
                logger.info("No evacuation data available, sending STOP message.")
                self.send_stop_message()
                return

            logger.info(f"Evacuation data being sent:\n{json.dumps(evacuation_data, indent=2)}")

            self.channel.basic_publish(
                exchange='',
                routing_key='alerted_users_queue',
                body=json.dumps(evacuation_data),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info("Sent aggregated evacuation data to alerted_users_queue.")

        except Exception as e:
            logger.error(f"Failed to send evacuation data: {e}")

    def send_stop_message(self):
        try:
            self.channel.basic_publish(
                exchange='',
                routing_key='alerted_users_queue',
                body=json.dumps({"msgType": "Stop"}),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info("Sent stop message to alerted_users_queue.")
        except Exception as e:
            logger.error(f"Failed to send stop message: {e}")


if __name__ == "__main__":
    consumer = PositionManagerConsumer()
    consumer.start_consuming()
