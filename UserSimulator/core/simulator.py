import random
import threading
import time
from datetime import datetime

import sys
sys.path.append('C:/Users/digre/AlertNotificationSystem2/UserSimulator')


from config.config_loader import load_config
from messaging.producer import PositionProducer
from utils.logger import logger
from db.db_connection import create_connection

class UserSimulator:
    def __init__(self):
        self.running = False
        config = load_config()  # Carica tutto il file YAML
        self.config = config
        self.db_conn = create_connection()
        # Prende il numero di utenti e i time slot dalla configurazione
        self.num_users = self.config.get("num_users", 100)  # default a 100 se non presente
        self.time_slots = self.config.get("time_slots", [])

        # Inizializza le posizioni o altra logica necessaria
        self.users = self._initialize_users()

    def _initialize_users(self):
        return {i: None for i in range(1, self.num_users + 1)}


    def start_simulation(self, alert_data: dict):
        if self.running:
            logger.info("🔁 Simulation already running.")
            return

        self.running = True
        logger.info(f"🟢 Starting simulation for alert {alert_data.get('identifier')}")

        thread = threading.Thread(target=self.simulation_loop, args=(alert_data,))
        thread.start()

    def stop_simulation(self, stop_data: dict):
        if self.running:
            self.running = False
            logger.info("🛑 Simulation stopped.")
        else:
            logger.info("🔇 No simulation running to stop.")

    def simulation_loop(self, alert_data):
        try:
            self.generate_initial_positions()
            while self.running:
                if "evacuation_paths" in alert_data:
                    self.load_paths(alert_data["evacuation_paths"])
                    self.simulate_movements()
                else:
                    self.update_idle_positions()
                time.sleep(5)  # Simulazione ogni 5 secondi
        except Exception as e:
            logger.error(f"❌ Error during simulation loop: {str(e)}")
        finally:
            self.db_conn.close()

    def generate_initial_positions(self):
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT * FROM nodes")
        nodes = cursor.fetchall()

        current_distribution = self.get_current_distribution()

        weighted_nodes = []
        for node in nodes:
            node_id = node[0]
            node_type = node[9]
            weight = current_distribution.get(node_type, 0)
            if weight > 0:
                weighted_nodes.extend([node] * int(weight * 100))

        for user_id in range(1, self.num_users + 1):
            node = random.choice(weighted_nodes)
            self.users[user_id] = node[0]  # node_id
            x = random.randint(node[1], node[2])
            y = random.randint(node[3], node[4])
            z = random.randint(node[5], node[6])

            self.store_position(user_id, node[0], x, y, z, "idle", danger="no")
        logger.info("✅ Initial user positions generated.")

    def update_idle_positions(self):
        for user_id, node_id in self.users.items():
            node = self.get_node_by_id(node_id)
            x = random.randint(node[1], node[2])
            y = random.randint(node[3], node[4])
            z = random.randint(node[5], node[6])
            self.store_position(user_id, node_id, x, y, z, "idle", danger="no")

    def load_paths(self, evacuation_paths: dict):
        for user_id, path in evacuation_paths.items():
            self.paths[int(user_id)] = path  # [(node_id, arc_id), ...]
        logger.info(f"📦 Loaded evacuation paths for users: {list(self.paths.keys())}")

    def simulate_movements(self):
        for user_id in list(self.paths.keys()):
            if not self.paths[user_id]:
                continue

            next_step = self.paths[user_id].pop(0)
            node_id = next_step[0]
            node = self.get_node_by_id(node_id)
            x = random.randint(node[1], node[2])
            y = random.randint(node[3], node[4])
            z = random.randint(node[5], node[6])

            self.users[user_id] = node_id
            self.store_position(user_id, node_id, x, y, z, "moving", danger="no")

    def get_node_by_id(self, node_id):
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT * FROM nodes WHERE node_id = %s", (node_id,))
        return cursor.fetchone()

    def get_current_distribution(self):
        now = datetime.now().time()
        for slot in self.config['time_slots']:
            start = datetime.strptime(slot['start'], "%H:%M").time()
            end = datetime.strptime(slot['end'], "%H:%M").time()
            if start <= now <= end:
                return slot['distribution']
        return {}

    def store_position(self, user_id, node_id, x, y, z, position_type, danger="no"):
        cursor = self.db_conn.cursor()
        # Update current position
        cursor.execute("""
            INSERT INTO current_position (user_id, x, y, z)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET x = EXCLUDED.x, y = EXCLUDED.y, z = EXCLUDED.z;
        """, (user_id, x, y, z))

        # Historical position
        cursor.execute("""
            INSERT INTO user_historical_position (user_id, x, y, z, node_id, position_type, danger)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, node_id) DO NOTHING;
        """, (user_id, x, y, z, node_id, position_type, danger))

        self.db_conn.commit()
        self.producer.send_positions([{
            "user_id": user_id,
            "x": x,
            "y": y,
            "z": z,
            "node_id": node_id,
            "position_type": position_type,
            "danger": danger
        }])
