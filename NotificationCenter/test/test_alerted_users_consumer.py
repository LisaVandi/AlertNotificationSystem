import unittest
from unittest.mock import MagicMock
from NotificationCenter.app.handlers.alerted_users_consumer import AlertedUsersConsumer
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import USER_SIMULATOR_QUEUE, EVACUATION_PATHS_QUEUE


class TestAlertedUsersConsumer(unittest.TestCase):
    def setUp(self):
        """Create a mock RabbitMQ handler for testing"""
        self.mock_rabbitmq_handler = MagicMock(spec=RabbitMQHandler)
        self.consumer = AlertedUsersConsumer(self.mock_rabbitmq_handler)

    def test_process_stop_message(self):
        """Test that a stop message is correctly forwarded to the User Simulator"""
        stop_message = {
            "msgType": "Stop",
            "id": "u1",
            "description": "Stop alert request from Position Manager"
        }

        self.consumer.process_alerted_user(stop_message)

        self.mock_rabbitmq_handler.send_message.assert_called_once_with(
            exchange="",
            routing_key=USER_SIMULATOR_QUEUE,
            message=stop_message
        )

    def test_process_evacuations_adds_msgType(self):
        evacuation_message = {
            "user_id": "u1",
            "evacuation_path": ["N1->Exit"]
        }
        
        original_message = evacuation_message.copy()

        self.consumer.process_alerted_user(evacuation_message)
        self.mock_rabbitmq_handler.send_message.assert_called_once()

        kwargs = self.mock_rabbitmq_handler.send_message.call_args.kwargs

        sent_message = kwargs.get("message", {})

        self.assertIn("msgType", sent_message)
        self.assertEqual(sent_message["msgType"], "Evacuation")

        self.assertEqual(sent_message["evacuation_path"], original_message["evacuation_path"])

    def test_no_evacuations_message(self):
        """Test that no evacuation path is forwarded if 'evacuation_path' is not present in the message"""
        non_evacuations_message = {
            "user_id": "u1",
            "msgType": "Alert"
        }

        self.consumer.process_alerted_user(non_evacuations_message)
        self.mock_rabbitmq_handler.send_message.assert_not_called()
