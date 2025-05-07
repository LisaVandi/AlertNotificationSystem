import random
import json
import pika
import logging
from db.db_connection import get_nodes_by_area  # Importa la funzione per recuperare i nodi

# Logger setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class UserSimulator:
    def __init__(self, config):
        self.num_users = config["num_users"]
        self.time_slots = config["time_slots"]

    def get_area_nodes(self, area):
        """Recupera i nodi associati a un'area dal database."""
        return get_nodes_by_area(area)
    

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
                    # Distribuisci gli utenti tra i nodi di quest'area
                    for _ in range(num_users_in_area):
                        node_id = random.choice(area_nodes)
                        position = {"area": area, "node_id": node_id}
                        positions_for_slot.append(position)
            
                        # Logga la posizione simulata per ogni utente
                        logger.info(f"Simulated position: {positions_for_slot[-1]}")

            all_positions.append({
                "time_slot": time_slot["name"],
                "positions": positions_for_slot
            })

         # Logga tutte le posizioni prima di restituirle
        logger.info(f"All simulated positions: {json.dumps(all_positions, indent=2)}")
        
        return all_positions
