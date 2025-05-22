import unittest
from unittest.mock import patch, MagicMock, ANY
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler

class TestRabbitMQHandlerInit(unittest.TestCase):

    @patch('NotificationCenter.app.services.rabbitmq_handler.setup_logging')
    @patch('NotificationCenter.app.services.rabbitmq_handler.pika.ConnectionParameters')
    @patch('NotificationCenter.app.services.rabbitmq_handler.RabbitMQHandler._connect')
    def test_init_with_default_params(self, mock_connect, mock_connection_params, mock_setup_logging):
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        handler = RabbitMQHandler()

        mock_setup_logging.assert_called_once_with(
            "rabbitmq_handler", 
            "NotificationCenter/logs/rabbitmqHandler.log"
        )
        mock_connection_params.assert_called_once_with(
            host='localhost',
            port=5672,
            credentials=None,
            heartbeat=600,
            blocked_connection_timeout=300,
            connection_attempts=3,
            retry_delay=5
        )
        mock_connect.assert_called_once()
        self.assertEqual(handler._connection, None)
        self.assertEqual(handler._channel, None)

    @patch('NotificationCenter.app.services.rabbitmq_handler.setup_logging')
    @patch('NotificationCenter.app.services.rabbitmq_handler.pika.ConnectionParameters')
    @patch('NotificationCenter.app.services.rabbitmq_handler.RabbitMQHandler._connect')
    @patch('pika.PlainCredentials')
    def test_init_with_custom_params(self, mock_plain_creds, mock_connect, 
                                   mock_connection_params, mock_setup_logging):
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        username = "user"
        password = "pass"
        
        creds_mock = MagicMock()
        mock_plain_creds.return_value = creds_mock

        handler = RabbitMQHandler(host="custom_host", port=1234, 
                                username=username, password=password)

        mock_setup_logging.assert_called_once_with(
            "rabbitmq_handler", 
            "NotificationCenter/logs/rabbitmqHandler.log"
        )
        
        mock_plain_creds.assert_called_once_with(username, password)
        
        mock_connection_params.assert_called_once_with(
            host='custom_host',
            port=1234,
            credentials=creds_mock,
            heartbeat=600,
            blocked_connection_timeout=300,
            connection_attempts=3,
            retry_delay=5
        )
        
        mock_connect.assert_called_once()
        self.assertEqual(handler._connection, None)
        self.assertEqual(handler._channel, None)

if __name__ == '__main__':
    unittest.main()