import pika
import json
import sys
import os
from utils.logger import logger  # Import the centralized logger utility

# Add the main folder (AlertNotificationSystem2) to sys.path for correct module resolution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from UserSimulator.rabbitmq.rabbitmq_manager import get_rabbitmq_channel
from UserSimulator.simulation.user_simulator import simulate_user_movement

def listen_for_events():
    """
    Listens for events from RabbitMQ queues and triggers the simulation when requested.
    
    This function listens for messages from two RabbitMQ queues:
    - 'user_simulator_queue': For receiving user simulation requests.
    - 'evacuation_paths_queue': For receiving user evacuation paths.

    The corresponding simulation methods are triggered upon receiving valid messages.
    """
    try:
        # Establish connection and get the RabbitMQ channel
        channel, _ = get_rabbitmq_channel()

        # Declare the queues with durability to ensure messages are not lost
        channel.queue_declare(queue="user_simulator_queue", durable=True)
        channel.queue_declare(queue="evacuation_paths_queue", durable=True)

        logger.info("Waiting for events...")

        def callback(ch, method, properties, body):
            """
            Callback function to process messages received from the queues.
            
            This function will be called each time a message is received on either of the queues.
            It will decode the message and trigger the simulation logic based on the content.
            """
            try:
                # Parse the message body (expected to be a JSON string)
                msg = json.loads(body)
                logger.info(f"Message received: {msg}")
                
                # Check the message type and trigger appropriate simulation actions
                simulate_user_movement(msg)

            except Exception as e:
                # Log any errors encountered while processing the message
                logger.error(f"Error processing message: {e}")

        # Begin consuming messages from the two queues
        channel.basic_consume(queue="user_simulator_queue", on_message_callback=callback, auto_ack=True)
        channel.basic_consume(queue="evacuation_paths_queue", on_message_callback=callback, auto_ack=True)

        logger.info('Waiting for events... Press CTRL+C to exit.')
        # Start processing the incoming messages
        channel.start_consuming()

    except KeyboardInterrupt:
        # Handle graceful shutdown when interrupted by user (CTRL+C)
        logger.info("Event listener interrupted.")
        sys.exit(0)

# Entry point for the script
if __name__ == '__main__':
    listen_for_events()
