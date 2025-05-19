import pika
from UserSimulator.utils.logger import logger  # Import the centralized logger utility


def get_rabbitmq_channel():
    """
    Establishes a connection to RabbitMQ and creates a communication channel.

    Returns:
        tuple: (channel, connection) if successful, otherwise (None, None).
    """
    try:
        logger.info("Attempting to connect to RabbitMQ...")

        # Establish a blocking connection to the RabbitMQ server
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))

        # Create a new channel from the connection
        channel = connection.channel()

        logger.info("Successfully connected to RabbitMQ and created a channel.")

        return channel, connection

    except Exception as e:
        # Log the error if the connection or channel creation fails
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        return None, None
