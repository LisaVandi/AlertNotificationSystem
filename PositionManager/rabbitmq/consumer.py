import json
import pika
import time
import threading
from PositionManager.db.db_manager import DBManager
from PositionManager.utils.logger import logger
import yaml

class PositionManagerConsumer:
    """
    A consumer class that listens for messages from a RabbitMQ queue, processes position data,
    and communicates with a PostgreSQL database to upsert current and historical positions.
    
    The class aggregates and sends position data periodically to an external system, as well as
    evacuation data for users in danger due to specific emergency events.

    Attributes:
        db_manager (DBManager): Instance of the DBManager class to interact with the database.
        config (dict): Configuration data loaded from the provided config file.
        dispatch_threshold (int): The threshold number of messages to process before dispatching data.
        dispatch_interval (int): The time interval (in seconds) for dispatching data periodically.
        processed_count (int): A counter for tracking the number of processed messages.
        last_dispatch_time (float): Timestamp of the last data dispatch time.
        connection (pika.BlockingConnection): The connection object to interact with RabbitMQ.
        channel (pika.channel.Channel): The RabbitMQ channel to consume messages from.
    """
    
    def __init__(self, config_file):
        """
        Initializes the PositionManagerConsumer instance by loading the configuration, 
        setting up the database manager, and establishing the RabbitMQ connection.
        
        Args:
            config_file (str): Path to the YAML configuration file.
        """
        self.db_manager = DBManager()
        self.config = self.load_config(config_file)
        self.dispatch_threshold = self.config.get('dispatch_threshold', 10)
        self.dispatch_interval = self.config.get('dispatch_interval', 10)  # Time interval in seconds
        self.processed_count = 0
        self.last_dispatch_time = time.time()
        self.last_event = None

        # Establish connection to RabbitMQ
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        # Declare a queue for receiving position data
        self.channel.queue_declare(queue='position_queue', durable=True)
        self.channel.basic_consume(queue='position_queue', on_message_callback=self.process_message, auto_ack=True)

        # Start a separate thread for periodic data flush
        threading.Thread(target=self.periodic_flush, daemon=True).start()

    def load_config(self, config_file):
        """
        Loads the configuration data from the provided YAML file.

        Args:
            config_file (str): Path to the YAML configuration file.

        Returns:
            dict: The loaded configuration data.
        """
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config

    def periodic_flush(self):
        """
        Periodically flushes the aggregated data if the dispatch threshold is met or the dispatch interval has passed.
        Sends the aggregated position data and evacuation data to the appropriate RabbitMQ queues.
        """
        while True:
            time.sleep(1)
            now = time.time()
            if self.processed_count > 0 and (now - self.last_dispatch_time) >= self.dispatch_interval:
                logger.info("Triggered periodic flush.")
                self.send_aggregated_data()
                self.processed_count = 0
                self.last_dispatch_time = now

    def process_message(self, ch, method, properties, body):
        """
        Processes a single message from the RabbitMQ queue, extracting position data,
        calculating the danger level, and upserting the data into the database.

        Args:
            ch (pika.channel.Channel): The channel object for the RabbitMQ connection.
            method (pika.spec.Basic.Deliver): The delivery method of the message.
            properties (pika.spec.BasicProperties): The properties of the message.
            body (bytes): The message body containing the position data.
        """
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
            
            # Calculate the danger level based on the event and position
            danger = self.calculate_danger(event, x, y, z, node_id)
            
            # Upsert current position and insert historical position into the database
            self.db_manager.upsert_current_position(user_id, x, y, z, node_id, danger)
            self.db_manager.insert_historical_position(user_id, x, y, z, node_id, danger)
            
            # Increment the processed message count
            self.processed_count += 1

            # If threshold reached, send the aggregated data
            if self.processed_count >= self.dispatch_threshold:
                self.send_aggregated_data()
                self.processed_count = 0  # Reset the counter

        except Exception as e:
            logger.error(f"Failed to process message: {e}")

    def calculate_danger(self, event, x, y, z, node_id):
        """
        Calculates whether a user is in danger based on the event type and their position.

        Args:
            event (str): The type of emergency event.
            x (float): The x-coordinate of the user.
            y (float): The y-coordinate of the user.
            z (float): The z-coordinate (floor level) of the user.

        Returns:
            bool: True if the user is in danger, False otherwise.
        """
        if event not in self.config['emergencies']:
            logger.warning(f"Unknown event type: {event}")
            return False  # Default to no danger if event is unknown

        event_config = self.config['emergencies'][event]

        if event_config['type'] == 'all':
            return True  # Evacuate all users for this event

        if event_config['type'] == 'floor':
            danger_floors = event_config.get('danger_floors', [])
            floor_level = self.db_manager.get_floor_level_by_node(node_id)
            if floor_level is None:
                logger.warning(f"Could not find floor level for node_id {node_id}")
                return False
            return floor_level in danger_floors

        if event_config['type'] == 'zone':
            # For zone-based events, evacuate users within a specific area
            danger_zone = event_config.get('danger_zone', {})
            return danger_zone['x1'] <= x <= danger_zone['x2'] and \
                   danger_zone['y1'] <= y <= danger_zone['y2'] and \
                   danger_zone['z1'] <= z <= danger_zone['z2']
        
        return False

    def send_aggregated_data(self):
        """
        Sends the aggregated data of dangerous nodes to the map manager queue,
        and evacuation data for users in danger to the evacuation paths queue.
        """
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

        # Send evacuation data for users in danger
        evacuation_data = self.get_evacuation_data()

        # Log del messaggio aggregato
        logger.info(f"Aggregated data being sent to map_manager_queue:\n{json.dumps(evacuation_data, indent=2)}")

        if evacuation_data:
            self.channel.basic_publish(
                exchange='',
                routing_key='evacuation_paths_queue',
                body=json.dumps(evacuation_data),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info("Sent evacuation data to evacuation_paths_queue.")
        else:
            # If no users are in danger, send a stop message to the evacuation queue
            self.channel.basic_publish(
                exchange='',
                routing_key='evacuation_paths_queue',
                body=json.dumps({"msgType": "Stop"}),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info("Sent stop message to evacuation_paths_queue.")

    def aggregate_current_positions(self):
        """
        Aggregates the current positions of users in danger by node ID.

        Returns:
            dict: A dictionary containing aggregated data by node ID with associated user IDs.
        """
        aggregated_data = {}
        try:
            with self.db_manager.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT node_id, user_id
                    FROM current_position
                    WHERE danger = TRUE;
                """)
                rows = cursor.fetchall()

                for row in rows:
                    node_id, user_id = row
                    if node_id not in aggregated_data:
                        aggregated_data[node_id] = {"node_id": node_id, "user_ids": []}
                    aggregated_data[node_id]["user_ids"].append(user_id)

        except Exception as e:
            logger.error(f"Failed to aggregate current positions: {e}")

        return {"dangerous_nodes": list(aggregated_data.values())}

    def get_evacuation_data(self):
        """
        Retrieves evacuation paths for users in danger based on their node ID.

        Returns:
            list: A list of dictionaries containing user IDs and their corresponding evacuation paths.
        """
        evacuation_data = []
        try:
            with self.db_manager.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT user_id, node_id
                    FROM current_position
                    WHERE danger = TRUE;
                """)
                rows = cursor.fetchall()

                for row in rows:
                    user_id, node_id = row
                    cursor.execute("""
                        SELECT evacuation_path
                        FROM nodes
                        WHERE node_id = %s;
                    """, (node_id,))
                    evacuation_path = cursor.fetchone()
                    if evacuation_path:
                        evacuation_data.append({
                            "user_id": user_id,
                            "evacuation_path": evacuation_path[0]
                        })

        except Exception as e:
            logger.error(f"Failed to get evacuation data: {e}")

        return evacuation_data if evacuation_data else None

    def start_consuming(self):
        """
        Starts the consumer to begin listening for messages from the RabbitMQ queue.
        """
        logger.info("PositionManagerConsumer started.")
        self.channel.start_consuming()


if __name__ == "__main__":
    consumer = PositionManagerConsumer(config_file='PositionManager/config/config.yaml')
    consumer.start_consuming()
