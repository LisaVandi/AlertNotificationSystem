import pytest
from unittest.mock import MagicMock, patch
from NotificationCenter.app.handlers.alert_smister_to_map_manager import send_alert_to_map_manager
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import MAP_MANAGER_QUEUE

@patch("NotificationCenter.app.handlers.alert_smister_to_map_manager.logger")
@patch("NotificationCenter.app.handlers.alert_smister_to_map_manager.flush_logs")
def test_send_alert_to_map_manager_success(mock_flush_logs, mock_logger):
    # Arrange
    rabbitmq_handler = MagicMock(spec=RabbitMQHandler)
    message = {"alert": "test alert"}
    
    # Act
    send_alert_to_map_manager(rabbitmq_handler, message)
    
    # Assert
    rabbitmq_handler.send_message.assert_called_once_with(
        exchange="",
        routing_key=MAP_MANAGER_QUEUE,  
        message=message
    )
    mock_logger.debug.assert_called_once_with(f"Sending alert to Map Manager: {message}")
    mock_logger.info.assert_called_once_with("Alert forwarded to Map Manager")
    mock_flush_logs.assert_called_once_with(mock_logger)

@patch("NotificationCenter.app.handlers.alert_smister_to_map_manager.logger")
@patch("NotificationCenter.app.handlers.alert_smister_to_map_manager.flush_logs")
def test_send_alert_to_map_manager_failure(mock_flush_logs, mock_logger):
    # Arrange
    rabbitmq_handler = MagicMock(spec=RabbitMQHandler)
    rabbitmq_handler.send_message.side_effect = Exception("Test exception")
    message = {"alert": "test alert"}
    
    # Act & Assert
    with pytest.raises(Exception, match="Test exception"):
        send_alert_to_map_manager(rabbitmq_handler, message)
    
    rabbitmq_handler.send_message.assert_called_once_with(
        exchange="",
        routing_key=MAP_MANAGER_QUEUE,  
        message=message
    )
    mock_logger.debug.assert_called_once_with(f"Sending alert to Map Manager: {message}")
    mock_logger.error.assert_called_once_with("Failed to forward alert to Map Manager: Test exception")
    mock_flush_logs.assert_called_with(mock_logger)