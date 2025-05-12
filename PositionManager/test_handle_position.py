# === test_handle_position.py ===

from core.position_handler import handle_position

# Monkey patch della funzione publish_message per stampare invece di inviare
import core.messaging

def mock_publish_message(queue_name, message):
    import json
    print(f"\n[MESSAGE QUEUE: {queue_name}]")
    print(json.dumps(message, indent=2))

core.messaging.publish_message = mock_publish_message

# Dati di test
test_input = {
    "users_positions": [
        {
            "time_slot": "2025-05-12T10:00:00Z",
            "positions": [
                {
                    "user_id": "u1",
                    "x": 10,
                    "y": 20,
                    "z": 0,
                    "node_id": "N1"
                },
                {
                    "user_id": "u2",
                    "x": 11,
                    "y": 21,
                    "z": 0,
                    "node_id": "N1"
                },
                {
                    "user_id": "u3",
                    "x": 50,
                    "y": 60,
                    "z": 1,
                    "node_id": "N2"
                },
                {
                    "user_id": "u4",
                    "x": 100,
                    "y": 200,
                    "z": 2,
                    "node_id": "SAFE_NODE"
                }
            ]
        }
    ]
}

# Mock di is_user_in_danger e get_evacuation_path per testare senza logica esterna
import core.danger_detector
import utils.db_utils

core.danger_detector.is_user_in_danger = lambda pos: pos["node_id"] != "SAFE_NODE"
utils.db_utils.get_evacuation_path = lambda node_id: [f"{node_id}->Exit"]

# Esegui il test
handle_position(test_input)
