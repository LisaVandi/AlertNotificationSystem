import json
import pika
from PositionManager.db.db_manager import DBManager
from PositionManager.utils.logger import logger
import yaml

class PositionManagerConsumer:
    def __init__(self, config_file):
        self.db_manager = DBManager()
        self.config = self.load_config(config_file)
        self.dispatch_threshold = self.config.get('dispatch_threshold', 10)
        self.processed_count = 0

        # Connessione a RabbitMQ
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        self.channel.queue_declare(queue='position_queue', durable=True)
        self.channel.basic_consume(queue='position_queue', on_message_callback=self.process_message, auto_ack=True)

    def load_config(self, config_file):
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config

    def process_message(self, ch, method, properties, body):
        try:
            logger.info(f"Received raw message:\n{json.dumps(json.loads(body), indent=2)}")
            
            message = json.loads(body)
            event = message.get("event")
            user_id = message.get("user_id")
            x = message.get("x")
            y = message.get("y")
            z = message.get("z")
            node_id = message.get("node_id")
            
            # Verifica il tipo di evento e calcola il pericolo
            danger = self.calculate_danger(event, x, y, z)
            
            # Effettua l'upsert nel database
            self.db_manager.upsert_current_position(user_id, x, y, z, node_id, danger)
            
            # Conta i messaggi processati
            self.processed_count += 1

            # Se abbiamo raggiunto il threshold, invia i dati aggregati
            if self.processed_count >= self.dispatch_threshold:
                self.send_aggregated_data()
                self.processed_count = 0  # Resetta il contatore

        except Exception as e:
            logger.error(f"Failed to process message: {e}")

    def calculate_danger(self, event, x, y, z):
        """Calcola il pericolo in base al tipo di evento e alla posizione."""
        if event not in self.config['emergencies']:
            logger.warning(f"Unknown event type: {event}")
            return False  # Pericolo di default è False

        event_config = self.config['emergencies'][event]

        if event_config['type'] == 'all':
            return True  # Evacuare tutti

        if event_config['type'] == 'floor':
            # Se è un evento di tipo 'floor', evacuare utenti in base al piano (z)
            danger_floors = event_config.get('danger_floors', [])
            return z in danger_floors

        if event_config['type'] == 'zone':
            # Se è un evento di tipo 'zone', evacuare utenti all'interno di un'area specifica
            danger_zone = event_config.get('danger_zone', {})
            return danger_zone['x1'] <= x <= danger_zone['x2'] and \
                   danger_zone['y1'] <= y <= danger_zone['y2'] and \
                   danger_zone['z1'] <= z <= danger_zone['z2']
        
        return False

    def send_aggregated_data(self):
        """Invia i dati aggregati a map_manager_queue."""
        aggregated_data = self.aggregate_current_positions()
        self.channel.basic_publish(
            exchange='',
            routing_key='map_manager_queue',
            body=json.dumps(aggregated_data),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        logger.info("Sent aggregated data to map_manager_queue.")

        # Invia i dati di evacuazione per gli utenti in pericolo
        evacuation_data = self.get_evacuation_data()
        if evacuation_data:
            self.channel.basic_publish(
                exchange='',
                routing_key='evacuation_paths_queue',
                body=json.dumps(evacuation_data),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info("Sent evacuation data to evacuation_paths_queue.")
        else:
            # Se nessun utente in pericolo, invia un messaggio di stop
            self.channel.basic_publish(
                exchange='',
                routing_key='evacuation_paths_queue',
                body=json.dumps({"msgType": "Stop"}),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info("Sent stop message to evacuation_paths_queue.")

    def aggregate_current_positions(self):
        """Aggrega le informazioni sulla base dei nodi e invia il risultato."""
        aggregated_data = {}
        try:
            with self.db_manager.map_manager_conn.cursor() as cursor:
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
        """Recupera i dati di evacuazione per gli utenti in pericolo."""
        evacuation_data = []
        try:
            with self.db_manager.map_manager_conn.cursor() as cursor:
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
        """Avvia il consumer e inizia a ricevere i messaggi dalla coda."""
        logger.info("PositionManagerConsumer started.")
        self.channel.start_consuming()


if __name__ == "__main__":
    consumer = PositionManagerConsumer(config_file='PositionManager/config/config.yaml')
    consumer.start_consuming()
