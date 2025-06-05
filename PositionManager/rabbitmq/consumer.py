import json
import pika
import time
import threading
from PositionManager.db.db_manager import DBManager
from PositionManager.utils.logger import logger
from PositionManager.utils.config_loader import ConfigLoader
import yaml

class PositionManagerConsumer:
    def __init__(self, config_file):
        self.db_manager = DBManager()
        self.config_loader = ConfigLoader(config_file)
        self.dispatch_threshold = self.config_loader.threshold
        self.dispatch_interval = self.config_loader.config.get('dispatch_interval', 10)
        self.processed_count = 0
        self.last_dispatch_time = time.time()
        self.last_event = None

        # Connessione RabbitMQ
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        # Code
        self.channel.queue_declare(queue='position_queue', durable=True)
        self.channel.queue_declare(queue='ack_paths_computed', durable=True)

        # Consumi
        self.channel.basic_consume(queue='position_queue', on_message_callback=self.process_message, auto_ack=True)
        self.channel.basic_consume(queue='ack_paths_computed', on_message_callback=self.process_ack_message, auto_ack=True)

        # Thread per periodic flush
        threading.Thread(target=self.periodic_flush, daemon=True).start()
        threading.Thread(target=self.start_ack_consumer, daemon=True).start()

    def periodic_flush(self):
        while True:
            time.sleep(1)
            now = time.time()
            if self.processed_count > 0 and (now - self.last_dispatch_time) >= self.dispatch_interval:
                logger.info("Triggered periodic flush.")
                self.send_aggregated_data(only_to_map_manager=True)  # invia solo a map_manager_queue
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
            
            node_type = self.db_manager.get_node_type(node_id)
            floor_level = self.db_manager.get_floor_level_by_node(node_id)

            danger = self.config_loader.is_user_in_danger(
                event,
                {"x": x, "y": y, "z": z},
                node_type=node_type,
                floor_level=floor_level
            )

            self.db_manager.upsert_current_position(user_id, x, y, z, node_id, danger)
            self.db_manager.insert_historical_position(user_id, x, y, z, node_id, danger)

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
            return  # NON invia ancora i percorsi

        evacuation_data = self.get_evacuation_data()

        logger.info(f"Evacuation data being sent:\n{json.dumps(evacuation_data, indent=2) if evacuation_data else 'STOP message'}")
        if evacuation_data:
            self.channel.basic_publish(
                exchange='',
                routing_key='evacuation_paths_queue',
                body=json.dumps(evacuation_data),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info("Sent evacuation data to evacuation_paths_queue.")
        else:
            self.channel.basic_publish(
                exchange='',
                routing_key='evacuation_paths_queue',
                body=json.dumps({"msgType": "Stop"}),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info("Sent stop message to evacuation_paths_queue.")

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
            if msg.get("msgType") == "paths_ready":
                logger.info("Received 'paths_ready' message. Dispatching evacuation paths.")
                self.send_aggregated_data(only_to_map_manager=False)
            else:
                logger.warning(f"Ignored unknown ack message type: {msg}")
        except Exception as e:
            logger.error(f"Failed to process ack message: {e}")

    def start_ack_consumer(self):
        logger.info("Started listening to ack_paths_computed queue for path readiness.")
        while True:
            try:
                self.connection.process_data_events(time_limit=1)
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in ack_paths_computed consumer loop: {e}")

    def start_consuming(self):
        logger.info("PositionManagerConsumer started.")
        self.channel.start_consuming()


if __name__ == "__main__":
    consumer = PositionManagerConsumer(config_file='PositionManager/config/config.yaml')
    consumer.start_consuming()
