import unittest
import sys
import os
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'core')))

from core.simulator import UserSimulator

class TestUserSimulator(unittest.TestCase):

    @patch('core.simulator.load_config')
    @patch('core.simulator.PositionProducer')
    @patch('core.simulator.create_connection')
    def test_simulation(self, mock_create_connection, MockPositionProducer, mock_load_config):
        # Mock config to return 100 users and time_slots
        mock_load_config.return_value = {
            "num_users": 100,
            "time_slots": [
                {
                    "start": "00:00",
                    "end": "23:59",
                    "distribution": {"aule": 0.5, "corridoi": 0.3, "punti_ristoro": 0.2}
                }
            ]
        }

        # Mock DB and cursor
        mock_cursor = MagicMock()
        mock_db = MagicMock()
        mock_db.cursor.return_value = mock_cursor
        mock_db.close = MagicMock()
        mock_create_connection.return_value = mock_db

        # Mock DB response for node query
        mock_cursor.fetchall.return_value = [
            (1, 0, 100, 0, 100, 0, 10, None, None, 'classroom'),
            (2, 0, 100, 0, 100, 0, 10, None, None, 'corridor'),
            (3, 0, 100, 0, 100, 0, 10, None, None, 'canteen')
        ]

        # Mock producer
        mock_producer = MockPositionProducer.return_value
        mock_producer.send_positions = MagicMock()

        simulator = UserSimulator()
        simulator.store_position = MagicMock()

        alert_data = {
            "identifier": "test_alert",
            "msgType": "Start",
            "evacuation_paths": {}
        }

        simulator.start_simulation(alert_data)
        time.sleep(1.5)  # consente al thread di fare almeno un ciclo
        simulator.stop_simulation({})

        self.assertTrue(simulator.running is False)
        self.assertEqual(len(simulator.users), 100)
        simulator.store_position.assert_called()

    @patch('core.simulator.load_config')
    @patch('core.simulator.PositionProducer')
    @patch('core.simulator.create_connection')
    def test_update_positions(self, mock_create_connection, MockPositionProducer, mock_load_config):
        # Config con 10 utenti
        mock_load_config.return_value = {
            "num_users": 10,
            "time_slots": []
        }

        mock_cursor = MagicMock()
        mock_db = MagicMock()
        mock_db.cursor.return_value = mock_cursor
        mock_create_connection.return_value = mock_db

        mock_producer = MockPositionProducer.return_value
        mock_producer.send_positions = MagicMock()

        simulator = UserSimulator()
        simulator.store_position = MagicMock()
        simulator.get_node_by_id = MagicMock(return_value=(1, 0, 100, 0, 100, 0, 10))
        simulator.users = {i: 1 for i in range(1, 11)}  # 10 utenti

        simulator.update_idle_positions()
        self.assertEqual(simulator.store_position.call_count, 10)

if __name__ == '__main__':
    unittest.main()
