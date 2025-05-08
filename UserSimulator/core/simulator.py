import random
import json
import pika
import logging
from db.db_connection import get_nodes_by_area
from utils.logger import logger

class UserSimulator:
    def __init__(self, config):
        self.num_users = config["num_users"]
        self.time_slots = config["time_slots"]
        self.user_id_counter = 1  # ID univoco che parte da 1
        self.generated_user_ids = []  # Per tenere traccia degli ID assegnati

    def get_area_nodes(self, area):
        """Recupera i nodi associati a un'area dal database."""
        return get_nodes_by_area(area)

    def generate_user_id(self):
        """Genera un ID utente intero univoco senza usare il DB."""
        user_id = self.user_id_counter
        self.user_id_counter += 1
        self.generated_user_ids.append(user_id)
        return user_id

    def send_to_rabbitmq(self, user_id, x, y, z, node_id):
        """Invia la posizione dell'utente a RabbitMQ."""
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()

        message = {
            'user_id': user_id,
            'x': x,
            'y': y,
            'z': z,
            'node_id': node_id
        }

        channel.basic_publish(
            exchange='',
            routing_key='user_positions',
            body=json.dumps(message)
        )

        #logger.debug(f"Sent message for user {user_id}: position x={x}, y={y}, z={z}, node={node_id}")
        connection.close()

    def simulate_positions(self):
        """Simula la distribuzione degli utenti per ogni intervallo di tempo."""
        all_positions = []

        for time_slot in self.time_slots:
            users_for_slot = int(self.num_users * sum(time_slot["distribution"].values()))
            positions_for_slot = []

            for area, percentage in time_slot["distribution"].items():
                num_users_in_area = int(users_for_slot * percentage)
                area_nodes = self.get_area_nodes(area)

                if area_nodes:
                    for _ in range(num_users_in_area):
                        node = random.choice(area_nodes)
                        x = random.randint(node['x1'], node['x2'])
                        y = random.randint(node['y1'], node['y2'])
                        z = random.randint(node['z1'], node['z2'])

                        user_id = self.generate_user_id()

                        self.send_to_rabbitmq(user_id, x, y, z, node['node_id'])

                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"Simulated position for user {user_id}: {x}, {y}, {z}, node {node['node_id']}")

                        position = {
                            "area": area,
                            "node_id": node['node_id'],
                            "user_id": user_id,
                            "x": x,
                            "y": y,
                            "z": z
                        }
                        positions_for_slot.append(position)

            all_positions.append({
                "time_slot": time_slot["name"],
                "positions": positions_for_slot
            })

        return all_positions

    def get_current_node(self, user_id):
        """Stub temporaneo: simula che l'utente sia in un nodo casuale."""
        # In futuro dovrai recuperare da memoria locale o messaggi ricevuti
        return {
            "area": "classroom"  # valore fittizio
        }

    def simulate_movements(self, user_ids, time_slot):
        """Simula gli spostamenti degli utenti in un dato intervallo di tempo."""
        all_positions = []

        for user_id in user_ids:
            current_node = self.get_current_node(user_id)

            if current_node:
                area_nodes = self.get_area_nodes(current_node['area'])
                next_node = random.choice(area_nodes)

                x = random.randint(next_node['x1'], next_node['x2'])
                y = random.randint(next_node['y1'], next_node['y2'])
                z = random.randint(next_node['z1'], next_node['z2'])

                self.send_to_rabbitmq(user_id, x, y, z, next_node['node_id'])

                logger.info(f"User {user_id} moved to new position: {x}, {y}, {z}, node {next_node['node_id']}")

                all_positions.append({
                    "user_id": user_id,
                    "new_position": {
                        "x": x,
                        "y": y,
                        "z": z,
                        "node_id": next_node['node_id']
                    },
                    "time_slot": time_slot
                })

        return all_positions
