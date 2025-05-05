from utils.logger import logger

class SimulatorController:
    def __init__(self, simulator):
        self.simulator = simulator

    def handle_message(self, message: dict):
        msg_type = message.get("msgType")

        if msg_type in ["Alert", "Update"]:
            logger.info("▶️ Starting simulation for alert.")
            self.simulator.start_simulation(message)
        elif msg_type == "Cancel":
            logger.info("⛔ Stopping simulation.")
            self.simulator.stop_simulation(message)
        else:
            logger.warning(f"⚠️ Unknown message type: {msg_type}")
