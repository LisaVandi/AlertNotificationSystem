import pytest
from unittest.mock import MagicMock, patch
from NotificationCenter.app.handlers.position_request import request_positions
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import POSITION_REQUEST_QUEUE

@patch("NotificationCenter.app.handlers.position_request.logger")
def test_request_positions_success(mock_logger):
    # Arrange
    rabbitmq_handler = MagicMock(spec=RabbitMQHandler)
    alert_id = "test_alert_id"

    # Act
    with patch("NotificationCenter.app.handlers.position_request.POSITION_REQUEST_QUEUE", POSITION_REQUEST_QUEUE):
        request_positions(rabbitmq_handler, alert_id)

    # Assert
    rabbitmq_handler.send_message.assert_called_once_with(
        exchange="",
        routing_key=POSITION_REQUEST_QUEUE,
        message={"alert_id": alert_id, "request": "get_positions"}
    )
    mock_logger.info.assert_called_once_with(f"Position request sent for alert {alert_id}")

@patch("NotificationCenter.app.handlers.position_request.logger")
def test_request_positions_failure(mock_logger):
    # Arrange
    rabbitmq_handler = MagicMock(spec=RabbitMQHandler)
    rabbitmq_handler.send_message.side_effect = Exception("Test exception")
    alert_id = "test_alert_id"
    POSITION_REQUEST_QUEUE = "test_queue"

    # Act & Assert
    with patch("NotificationCenter.app.handlers.position_request.POSITION_REQUEST_QUEUE", POSITION_REQUEST_QUEUE):
        with pytest.raises(Exception, match="Test exception"):
            request_positions(rabbitmq_handler, alert_id)

    rabbitmq_handler.send_message.assert_called_once_with(
        exchange="",
        routing_key=POSITION_REQUEST_QUEUE,
        message={"alert_id": alert_id, "request": "get_positions"}
    )
    mock_logger.error.assert_called_once_with("Failed to send position request: Test exception")