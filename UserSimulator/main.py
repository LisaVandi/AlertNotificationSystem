from messaging.consumer import UserSimulatorConsumer
from core.controller import SimulatorController
from core.simulator import UserSimulator
from utils.logger import logger

RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"
QUEUE_NAME = "user_simulator_queue"

if __name__ == "__main__":
    try:
        simulator = UserSimulator()
        controller = SimulatorController(simulator)
        consumer = UserSimulatorConsumer(
            rabbitmq_url=RABBITMQ_URL,
            queue_name=QUEUE_NAME,
            callback=controller.handle_message
        )
        consumer.start_consuming()
    except KeyboardInterrupt:
        logger.info("🔻 Simulator stopped manually.")
