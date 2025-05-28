import pytest
from unittest.mock import MagicMock, patch
from NotificationCenter.app.config.settings import ALERT_QUEUE
from NotificationCenter.app.handlers.alert_consumer import AlertConsumer
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler

@pytest.fixture
def mock_rabbitmq_handler():
    return MagicMock(spec=RabbitMQHandler)

@pytest.fixture
def alert_consumer(mock_rabbitmq_handler):
    return AlertConsumer(rabbitmq_handler=mock_rabbitmq_handler)

def test_alert_consumer_initialization(mock_rabbitmq_handler):
    consumer = AlertConsumer(rabbitmq_handler=mock_rabbitmq_handler)
    assert consumer.rabbitmq == mock_rabbitmq_handler

def test_start_consuming(alert_consumer, mock_rabbitmq_handler):
    alert_consumer.start_consuming()
    mock_rabbitmq_handler.consume_messages.assert_called_once_with(
        queue_name=ALERT_QUEUE,
        callback=alert_consumer.process_alert
    )

def test_process_alert_valid(alert_consumer, mock_rabbitmq_handler):
    alert_data = {
        "id": "123",
        "msgType": "Alert",
        "type": "fire",
        "severity": "high",
        "area": "zone1"
    }
    with patch("NotificationCenter.app.handlers.alert_consumer.send_alert_to_user_simulator") as mock_user_simulator:
        
        alert_consumer.process_alert(alert_data)
        
        mock_user_simulator.assert_called_once_with(mock_rabbitmq_handler, alert_data)
