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

        # Call the method to process the stop message
        self.consumer.process_alerted_user(stop_message)

        # Assert that the send_alert_to_user_simulator method is called with the stop message
        self.mock_rabbitmq_handler.send_message.assert_called_once_with(
            exchange="",
            routing_key=USER_SIMULATOR_QUEUE,
            message=stop_message
        )

    def test_process_evacuations_adds_msgType(self):
        """Test that an evacuation message gets 'msgType':'Evacuation' added before forwarding"""
        evacuation_message = {
            "user_id": "u1",
            "evacuation_path": ["N1->Exit"]
        }
        
        original_message = evacuation_message.copy()

        # Call the method to process the evacuation path
        self.consumer.process_alerted_user(evacuation_message)

        self.mock_rabbitmq_handler.send_message.assert_called_once()

        # Extract the actual call arguments
        kwargs = self.mock_rabbitmq_handler.send_message.call_args.kwargs

        sent_message = kwargs.get("message", {})

        # Assert that msgType was added and equals "Evacuation"
        self.assertIn("msgType", sent_message)
        self.assertEqual(sent_message["msgType"], "Evacuation")

        self.assertEqual(sent_message["evacuation_path"], original_message["evacuation_path"])

    def test_no_evacuations_message(self):
        """Test that no evacuation path is forwarded if 'evacuation_path' is not present in the message"""
        non_evacuations_message = {
            "user_id": "u1",
            "msgType": "Alert"
        }

        # Call the method to process the message without evacuation path
        self.consumer.process_alerted_user(non_evacuations_message)

        # Assert that send_evacuation_path_to_user_simulator is NOT called
        self.mock_rabbitmq_handler.send_message.assert_not_called()
