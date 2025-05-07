import json
from messaging.producer import UserSimulatorProducer
from core.simulator import UserSimulator
from utils.logger import logger

class SimulatorController:
    def __init__(self, simulator, config):
        self.simulator = simulator
        self.producer = UserSimulatorProducer(
            rabbitmq_url=config['rabbitmq']['url'],
            queue_name=config['rabbitmq']['publish_queue']
        )

    def handle_message(self, message: dict):
        """Gestisce i messaggi ricevuti dal NotificationCenter."""
        try:
            msg_type = message.get("msgType")
            
            if msg_type in ["Alert", "Update"]:
                logger.info(f"Processing positions for {msg_type} alert.")
                
                # Aggiungi un log per vedere se la simulazione viene chiamata
                logger.info("Simulating user positions...")

                # Simula le posizioni e logga l'esito
                positions = self.simulator.simulate_positions()

                # Logga le posizioni generate prima di inviarle
                logger.info(f"Generated positions: {json.dumps(positions, indent=2)}")
                
                # Logga la posizione totale per ogni time slot
                for slot in positions:
                    logger.info(f"Time slot: {slot['time_slot']} - Users: {len(slot['positions'])}")
                    logger.debug(f"Positions: {json.dumps(slot['positions'], indent=2)}")
                
                # Invia le posizioni
                self.producer.send_positions(positions)

            elif msg_type == "Cancel":
                logger.info("Stopping simulation as per 'Cancel' message.")
                self.simulator.stop_simulation()

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
