from app.core.controller import SimulationController
from app.messaging.consumer import start_consumer

def main():
    controller = SimulationController("app/config/settings.yaml")
    start_consumer(controller, queue_name="user_command_queue")

if __name__ == "__main__":
    main()
