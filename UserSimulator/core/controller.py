import time
from core.simulator import simulate_user_positions
from messaging.producer import PositionProducer
from config.config_loader import load_yaml_config

class SimulationController:
    def __init__(self, config_path):
        self.config = load_yaml_config()
        self.producer = PositionProducer()
        self.running = False

    def handle_command(self, command: str, payload: dict):
        if command == "send_position":
            self.running = True
            self._simulate_loop(payload.get("num_users", 10), payload.get("interval", 5))
        elif command == "stop":
            self.running = False

    def _simulate_loop(self, num_users: int, interval: int):
        while self.running:
            positions = simulate_user_positions(self.config, num_users)
            self.producer.send_positions(positions)
            time.sleep(interval)
