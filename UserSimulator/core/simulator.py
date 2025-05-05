from utils.logger import logger

class UserSimulator:
    def __init__(self):
        self.running = False

    def start_simulation(self, alert_data: dict):
        self.running = True
        logger.info(f"🟢 Simulating user positions for alert {alert_data.get('identifier')}")

        # TODO: implementa logica per leggere mappa, generare posizioni ecc.

    def stop_simulation(self, stop_data: dict):
        if self.running:
            self.running = False
            logger.info("🛑 Simulation stopped.")
        else:
            logger.info("🔇 No simulation running to stop.")
