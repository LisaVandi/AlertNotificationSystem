from core.simulator import UserSimulator
from core.controller import SimulatorController
from messaging.consumer import UserSimulatorConsumer
from config.config_loader import load_config

def main():
    config = load_config()

    simulator = UserSimulator(config)
    controller = SimulatorController(simulator, config)

    consumer = UserSimulatorConsumer(
        rabbitmq_url=config['rabbitmq']['url'],
        queue_name=config['rabbitmq']['consume_queue'],
        callback=controller.handle_message
    )

    consumer.start_consuming()

if __name__ == "__main__":
    main()
