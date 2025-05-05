import pytest
from unittest.mock import MagicMock, patch
from NotificationCenter.app.handlers.alert_smister_to_user_simulator import send_alert_to_user_simulator
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import USER_SIMULATOR_QUEUE

@patch("NotificationCenter.app.handlers.alert_smister_to_user_simulator.logger")
def test_send_alert_to_user_simulator_success(mock_logger):
    # Arrange
    rabbitmq_handler = MagicMock(spec=RabbitMQHandler)
    message = {"key": "value"}

    with patch("NotificationCenter.app.handlers.alert_smister_to_user_simulator.USER_SIMULATOR_QUEUE", USER_SIMULATOR_QUEUE):
        # Act
        send_alert_to_user_simulator(rabbitmq_handler, message)

        # Assert
        rabbitmq_handler.send_message.assert_called_once_with(
            exchange="",
            routing_key=USER_SIMULATOR_QUEUE,
            message=message
        )
        mock_logger.info.assert_called_once_with("Alert forwarded to User Simulator")

@patch("NotificationCenter.app.handlers.alert_smister_to_user_simulator.logger")
def test_send_alert_to_user_simulator_failure(mock_logger):
    # Arrange
    rabbitmq_handler = MagicMock(spec=RabbitMQHandler)
    rabbitmq_handler.send_message.side_effect = Exception("Test exception")
    message = {"key": "value"}
    
    with patch("NotificationCenter.app.handlers.alert_smister_to_user_simulator.USER_SIMULATOR_QUEUE", USER_SIMULATOR_QUEUE):
        # Act & Assert
        with pytest.raises(Exception, match="Test exception"):
            send_alert_to_user_simulator(rabbitmq_handler, message)

        rabbitmq_handler.send_message.assert_called_once_with(
            exchange="",
            routing_key=USER_SIMULATOR_QUEUE,
            message=message
        )
        mock_logger.error.assert_called_once_with("Failed to forward alert to User Simulator: Test exception")