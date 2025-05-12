# === test_handle_position_standalone.py ===

def mock_is_user_in_danger(user_position):
    return user_position["node_id"] != "SAFE_NODE"

def mock_get_evacuation_path(node_id):
    return [f"{node_id}->Exit"]

def mock_publish_message(queue_name, message):
    import json
    print(f"\n[MESSAGE QUEUE: {queue_name}]")
    print(json.dumps(message, indent=2))


def handle_position(data):
    try:
        node_to_users = {}

        if "users_positions" in data:
            for time_slot_data in data["users_positions"]:
                for position in time_slot_data.get("positions", []):
                    user_id = position.get("user_id")
                    x = position.get("x")
                    y = position.get("y")
                    z = position.get("z")
                    node_id = position.get("node_id")

                    if not all([user_id, x is not None, y is not None, z is not None, node_id]):
                        continue

                    user_position = {
                        "user_id": user_id,
                        "x": x,
                        "y": y,
                        "z": z,
                        "node_id": node_id
                    }

                    danger = mock_is_user_in_danger(user_position)

                    if danger:
                        node_to_users.setdefault(node_id, []).append(user_id)
                        evacuation_path = mock_get_evacuation_path(node_id)
                        mock_publish_message("alerted_users_queue", {
                            "user_id": user_id,
                            "evacuation_path": evacuation_path
                        })

        # Aggregated message for MapManager
        if node_to_users:
            aggregated_message = {
                "dangerous_nodes": [
                    {"node_id": node_id, "user_ids": user_ids}
                    for node_id, user_ids in node_to_users.items()
                ]
            }
            mock_publish_message("map_manager_queue", aggregated_message)

    except Exception as e:
        print(f"Errore: {e}")


# === ESECUZIONE DEL TEST ===

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

handle_position(test_input)
